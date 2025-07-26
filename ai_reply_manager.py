from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Literal, Tuple
from collections import deque

import httpx

try:  # 可选依赖：langdetect（保留但不再使用自动语言分支）
    from langdetect import detect
except Exception:  # noqa: BLE001
    detect = None  # fallback later

try:  # 可选依赖：openai
    from openai import OpenAI  # official sdk client
except Exception:  # noqa: BLE001
    OpenAI = None  # fallback echo

from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger(__name__)

AIMode = Literal["openai", "dify", "coze", "echo"]


# --------------------------------------------------------------------------- #
# Config data classes                                                         #
# --------------------------------------------------------------------------- #
@dataclass
class OpenAIConfig:
    base_url: str = ""
    api_key: str = ""
    model: str = ""


@dataclass
class DifyConfig:
    # Dify App API 模式
    endpoint: str = ""  # e.g. https://your.dify.host/v1
    api_key: str = ""
    user: str = "tiktok_live_user"  # Dify user field (可UI覆盖)
    inputs: dict = field(default_factory=dict)  # 传给Dify的自定义inputs
    response_mode: str = "blocking"  # Dify 推荐 blocking


@dataclass
class CozeConfig:
    endpoint: str = "https://api.coze.com/open_api/v2/chat"  # 默认
    api_key: str = ""
    bot_id: str = ""
    user_id: str = "tiktok_live_user"
    stream: bool = False


# --------------------------------------------------------------------------- #
# Qt bridge: signals emitted back to UI                                       #
# --------------------------------------------------------------------------- #
class AIReplyBridge(QObject):
    reply_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)


# --------------------------------------------------------------------------- #
# Manager                                                                      #
# --------------------------------------------------------------------------- #
class AIReplyManager:
    """Collect comments & periodically generate AI replies."""

    def __init__(self, bridge: Optional[AIReplyBridge] = None) -> None:
        self.mode: AIMode = "echo"  # default safe mode
        self.openai_cfg = OpenAIConfig()
        self.dify_cfg = DifyConfig()
        self.coze_cfg = CozeConfig()

        self._enabled = False
        self._keyword_mode = False
        self._keywords: List[str] = []
        self._max_batch = 1  # 每周期处理的最大评论条数（当前仅用1条）
        self._custom_system_prompt = ""  # 自定义系统提示词

        self._comment_q: Deque[Tuple[float, str]] = deque(maxlen=5000)
        self._lock = threading.Lock()

        self._worker_active = False  # 防止重入

        self.bridge = bridge or AIReplyBridge()

    # ------------------------------------------------------------------ #
    # Configuration API (called from UI)                                  #
    # ------------------------------------------------------------------ #
    def set_mode(self, mode: AIMode) -> None:
        if mode not in ("openai", "dify", "coze", "echo"):
            mode = "echo"
        self.mode = mode
        log.info("AIReplyManager mode set to %s", mode)

    def config_openai(self, base_url: str, api_key: str, model: str) -> None:
        self.openai_cfg = OpenAIConfig(base_url=base_url.strip(), api_key=api_key.strip(), model=model.strip())

    def config_dify(self, endpoint: str, api_key: str, user: str = "tiktok_live_user") -> None:
        self.dify_cfg = DifyConfig(endpoint=endpoint.strip(), api_key=api_key.strip(), user=user.strip() or "tiktok_live_user")

    def config_coze(self, api_key: str, bot_id: str, user_id: str = "tiktok_live_user", endpoint: str | None = None) -> None:
        if endpoint:
            self.coze_cfg.endpoint = endpoint.strip()
        self.coze_cfg.api_key = api_key.strip()
        self.coze_cfg.bot_id = bot_id.strip()
        self.coze_cfg.user_id = user_id.strip() or "tiktok_live_user"

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        log.info("AIReplyManager enabled=%s", self._enabled)

    def set_keyword_mode(self, enabled: bool, keywords: List[str] | None = None) -> None:
        self._keyword_mode = bool(enabled)
        if keywords is not None:
            self._keywords = [k.strip() for k in keywords if k.strip()]
        log.info("Keyword mode=%s keywords=%s", self._keyword_mode, self._keywords)

    def set_max_batch(self, n: int) -> None:
        self._max_batch = max(1, int(n))

    def set_custom_prompt(self, prompt: str) -> None:
        """设置自定义系统提示词"""
        self._custom_system_prompt = prompt.strip()
        log.info("自定义系统提示词已设置: %s", self._custom_system_prompt)

    # ------------------------------------------------------------------ #
    # 管理：清空待处理评论（暂停 AI 回复时使用）                           #
    # ------------------------------------------------------------------ #
    def clear_pending_comments(self) -> None:
        """清空内部评论队列，丢弃暂存评论。"""
        with self._lock:
            self._comment_q.clear()
        log.debug("AIReplyManager: comment queue cleared.")

    # ------------------------------------------------------------------ #
    # Comment ingestion                                                   #
    # ------------------------------------------------------------------ #
    def add_comment(self, comment_line: str) -> None:
        """Push a comment line from UI (e.g. "user: text").
        过滤系统消息（以 '[' 开头）。"""
        if not comment_line or comment_line.startswith("["):
            return
        ts = time.time()
        with self._lock:
            self._comment_q.append((ts, comment_line))

    # ------------------------------------------------------------------ #
    # Periodic cycle (call from QTimer)                                  #
    # ------------------------------------------------------------------ #
    def cycle(self) -> None:
        if not self._enabled:
            return
        if self._worker_active:
            return  # 上一次请求未完成

        # 取出待处理评论
        items: List[str] = []
        with self._lock:
            while self._comment_q and len(items) < self._max_batch:
                _ts, line = self._comment_q.pop()  # 最新优先
                if self._accept_line(line):
                    items.append(line)
        if not items:
            return

        # 当前策略：只对最新 1 条生成回复
        comment_text = items[0]
        self._start_worker(comment_text)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #
    def _accept_line(self, line: str) -> bool:
        if not self._keyword_mode:
            return True
        lower = line.lower()
        return any(k.lower() in lower for k in self._keywords)

    def _extract_comment_text(self, line: str) -> str:
        # assume "username: comment"; split once
        parts = line.split(":", 1)
        if len(parts) == 2:
            return parts[1].strip()
        return line.strip()

    # 保留 langdetect 但不再依赖它做 prompt 选择
    def _detect_lang(self, text: str) -> str:  # noqa: D401
        """Retained for backward compat; returns 'zh' if any CJK found; else 'en'."""
        if detect is not None:
            try:
                code = detect(text)
                if code.startswith("zh"):
                    return "zh"
                return "en"
            except Exception:  # noqa: BLE001
                pass
        for ch in text:
            if "\u4e00" <= ch <= "\u9fff":
                return "zh"
        return "en"

    def _build_prompts(self, text: str) -> tuple[str, str]:
        """
        构造提示词（支持自定义系统提示词）
        """
        # 使用自定义提示词（如果设置），否则使用默认
        system_prompt = self._custom_system_prompt or (
            "你是一个直播间互动小助手。"
            "请始终使用与观众评论相同的语言进行简短、自然、友好的回复；"
            "不要翻译或切换到其它语言，除非观众明确要求你翻译或改用其它语言。"
            "Reply in the same language as the viewer comment. "
            "Do NOT translate or change language unless explicitly asked. "
            "Keep replies to 1 concise sentence."
        )
        user_prompt = f"观众评论：{text}"
        return system_prompt, user_prompt

    # ------------------------------------------------------------------ #
    # Worker thread dispatch                                             #
    # ------------------------------------------------------------------ #
    def _start_worker(self, comment_line: str) -> None:
        self._worker_active = True
        t = threading.Thread(target=self._worker_run, args=(comment_line,), daemon=True)
        t.start()

    def _worker_run(self, comment_line: str) -> None:
        try:
            text = self._extract_comment_text(comment_line)
            system_prompt, user_prompt = self._build_prompts(text)

            if self.mode == "openai":
                reply = self._call_openai(system_prompt, user_prompt)
            elif self.mode == "dify":
                reply = self._call_dify_agent(text)
            elif self.mode == "coze":
                reply = self._call_coze_agent(text)
            else:  # echo fallback
                reply = f"AI(Echo): {text}"

            if not reply:
                reply = "[AI] （无回复）"
            self.bridge.reply_signal.emit(reply)
        except Exception as e:  # noqa: BLE001
            log.exception("AI reply worker failed")
            self.bridge.error_signal.emit(f"AI 回复失败: {e}")
        finally:
            self._worker_active = False

    # ------------------------------------------------------------------ #
    # Backend calls                                                      #
    # ------------------------------------------------------------------ #
    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        cfg = self.openai_cfg
        if not (cfg.base_url and cfg.api_key and cfg.model and OpenAI is not None):
            # 缺配置 -> Echo 原评论（从 user_prompt 截取）
            return f"AI(Echo): {user_prompt.replace('观众评论：', '').strip()}"
        try:
            client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
            resp = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=200,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:  # noqa: BLE001
            return f"[AI错误] OpenAI 调用失败: {e}"

    def _call_dify_agent(self, text: str) -> str:
        cfg = self.dify_cfg
        if not (cfg.endpoint and cfg.api_key):
            return f"AI(Echo): {text}"
        url = cfg.endpoint.rstrip("/") + "/chat-messages"
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": cfg.inputs,
            "query": text,
            "response_mode": cfg.response_mode,
            "user": cfg.user,
        }
        try:
            with httpx.Client(timeout=30.0) as cli:
                r = cli.post(url, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
            answer = data.get("answer") or data.get("data", {}).get("answer")
            if answer:
                return answer.strip()
            return f"[AI警告] Dify 无可用 answer 字段: {data!r}"
        except Exception as e:  # noqa: BLE001
            return f"[AI错误] Dify 调用失败: {e}"

    def _call_coze_agent(self, text: str) -> str:
        cfg = self.coze_cfg
        if not (cfg.api_key and cfg.bot_id):
            return f"AI(Echo): {text}"
        url = cfg.endpoint
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "bot_id": cfg.bot_id,
            "user_id": cfg.user_id,
            "query": text,
            "stream": cfg.stream,
        }
        try:
            with httpx.Client(timeout=30.0) as cli:
                r = cli.post(url, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
            messages = data.get("data", {}).get("messages") or data.get("messages")
            if isinstance(messages, list) and messages:
                for msg in reversed(messages):
                    content = msg.get("content")
                    if isinstance(content, list):
                        for c in content:
                            if c.get("type") == "text" and c.get("text"):
                                return c["text"].strip()
                    elif isinstance(content, str) and content.strip():
                        return content.strip()
            return f"[AI警告] Coze 无可用文本: {data!r}"
        except Exception as e:  # noqa: BLE001
            return f"[AI错误] Coze 调用失败: {e}"
