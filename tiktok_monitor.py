"""
TikTok LIVE 评论后台监听器（线程 + asyncio loop）。

用法（典型）::
    fetcher = TikTokCommentFetcher(
        unique_id="@主播ID或直播用户名",
        comment_callback=lambda line: print(line),
        error_callback=lambda msg: print("[ERR]", msg),
    )
    fetcher.start()
    ...
    fetcher.stop()

设计要点
--------
- 独立后台线程，在线程内创建 asyncio 事件循环并运行 TikTokLiveClient。
- 连接成功、断开、评论事件均通过回调传回主线程（安全：Qt 信号包装在 UI 层）。
- stop() 会调度协程执行 `disconnect()` 并等待 `DEFAULT_DISCONNECT_GRACE` 秒；若超时强制收尾。
- 失败场景（用户名无效 / 未开播 / 网络错误）会通过 error_callback 报告。

依赖
----
    pip install TikTokLive

"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from typing import Callable, Optional

# TikTokLive 是可选依赖；若未安装则降级提示
try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent
except Exception:  # noqa: BLE001
    TikTokLiveClient = None  # type: ignore[assignment]
    CommentEvent = ConnectEvent = DisconnectEvent = object  # type: ignore

log = logging.getLogger(__name__)


class TikTokCommentFetcher:
    """后台 TikTok LIVE 评论监听线程。"""

    DEFAULT_DISCONNECT_GRACE = 5.0  # seconds to await graceful disconnect

    def __init__(
        self,
        unique_id: str,
        comment_callback: Optional[Callable[[str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
        *,
        disconnect_grace: float | None = None,
    ) -> None:
        if TikTokLiveClient is None:
            raise RuntimeError("未安装 TikTokLive 库，无法监听直播。请 pip install TikTokLive")

        self.unique_id = self._normalize_unique_id(unique_id)
        self.comment_callback = comment_callback
        self.error_callback = error_callback

        self.client = TikTokLiveClient(unique_id=self.unique_id)

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._disconnect_grace = (
            float(disconnect_grace) if disconnect_grace is not None else self.DEFAULT_DISCONNECT_GRACE
        )

        # Register TikTokLive events -----------------------------------
        self.client.on(CommentEvent)(self._on_comment)
        self.client.on(ConnectEvent)(self._on_connect)
        self.client.on(DisconnectEvent)(self._on_disconnect)

    # ------------------------------------------------------------------ #
    # TikTokLive event handlers (async)                                  #
    # ------------------------------------------------------------------ #
    async def _on_connect(self, event: ConnectEvent):  # type: ignore[name-defined]
        self._emit_info(f"Connected to @{event.unique_id} (Room ID: {self.client.room_id})")

    async def _on_disconnect(self, _event: DisconnectEvent):  # type: ignore[name-defined]
        self._emit_info("连接已断开")

    async def _on_comment(self, event: CommentEvent):  # type: ignore[name-defined]
        """收到评论事件 -> 格式化 'nickname: comment'."""
        try:
            username = event.user.nickname or event.user.unique_id or "?"
            text = event.comment or ""
            message = f"{username}: {text}"
            log.debug("Comment: %s", message)
            if self.comment_callback:
                self.comment_callback(message)
        except Exception as e:  # noqa: BLE001
            self._emit_error(f"处理评论出错: {e}")

    # ------------------------------------------------------------------ #
    # Public control API                                                 #
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """启动后台线程并连接直播间。"""
        if self._running:
            self._emit_error("监听已在运行")
            return
        self._running = True  # optimistic; will clear on failure
        self._thread = threading.Thread(target=self._run_loop, name="tiktok-fetcher", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Schedule graceful disconnect & stop the background loop/thread."""
        if not self._running:
            self._emit_error("未连接或已停止")
            return

        if self._loop is not None:
            try:
                fut = asyncio.run_coroutine_threadsafe(
                    self._graceful_disconnect_then_shutdown(self._disconnect_grace),
                    self._loop,
                )
                # quick probe to surface immediate sync errors
                try:
                    fut.result(timeout=0.1)
                except concurrent.futures.TimeoutError:
                    pass
            except Exception as e:  # noqa: BLE001
                self._emit_error(f"停止监听调度失败: {e!r}")

        if self._thread:
            self._thread.join(timeout=timeout)

        self._running = False
        self._emit_info("已停止监听")

    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------ #
    # Internal loop thread                                               #
    # ------------------------------------------------------------------ #
    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)

        try:
            # Pre-check: is user live?
            try:
                is_live = loop.run_until_complete(self.client.is_live())
            except Exception as e:  # noqa: BLE001
                self._emit_error(f"检测直播状态失败: {e}")
                return

            if not is_live:
                self._emit_error("主播当前未开播或用户名无效")
                return

            # connect() will run until disconnect
            loop.run_until_complete(
                self.client.connect(fetch_room_info=False, fetch_gift_info=False)
            )

        except Exception:  # noqa: BLE001
            log.exception("启动监听失败")
            self._emit_error("启动监听失败")
        finally:
            # Defensive cleanup
            try:
                pending = asyncio.all_tasks(loop=loop)
                for t in pending:
                    t.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:  # noqa: BLE001
                pass
            loop.close()
            self._running = False

    # ------------------------------------------------------------------ #
    # Graceful disconnect helper (runs in loop thread)                    #
    # ------------------------------------------------------------------ #
    async def _graceful_disconnect_then_shutdown(self, grace: float) -> None:
        try:
            if self.client.connected:
                try:
                    await asyncio.wait_for(self.client.disconnect(), timeout=grace)
                except asyncio.TimeoutError:
                    self._emit_error(f"停止监听超时（>{grace:.0f}s），将强制断开连接")
                except Exception as e:  # noqa: BLE001
                    self._emit_error(f"停止监听失败: {e!r}")
        finally:
            loop = asyncio.get_running_loop()
            for task in asyncio.all_tasks(loop):
                if task is not asyncio.current_task(loop):
                    task.cancel()
            await asyncio.sleep(0)  # let cancellations propagate
            loop.stop()

    # ------------------------------------------------------------------ #
    # Emit helpers                                                       #
    # ------------------------------------------------------------------ #
    def _emit_error(self, msg: str) -> None:
        log.error(msg)
        if self.error_callback:
            self.error_callback(msg)
        elif self.comment_callback:  # backward compat
            self.comment_callback(f"[⚠️] {msg}")

    def _emit_info(self, msg: str) -> None:
        log.info(msg)
        if self.comment_callback:
            self.comment_callback(f"[系统] {msg}")

    @staticmethod
    def _normalize_unique_id(uid: str) -> str:
        u = uid.strip()
        if u.startswith("@"):
            u = u[1:]
        return u
