import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QTextBrowser,
    QRadioButton, QStackedWidget, QTextEdit, QSlider, QSpinBox, QDoubleSpinBox,
    QCheckBox, QListWidget, QFrame, QMessageBox, QComboBox, QProgressBar
)
from PyQt6.QtCore import Qt, QSize

class TikTokAILiveApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok AI 直播程序")
        self.setGeometry(100, 100, 1000, 700) # 初始窗口大小

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # 1. TikTok 直播间评论模块
        self.tiktok_tab = self.create_tiktok_tab()
        self.tab_widget.addTab(self.tiktok_tab, "TikTok 直播间")

        # 2. AI 回复模块
        self.ai_reply_tab = self.create_ai_reply_tab()
        self.tab_widget.addTab(self.ai_reply_tab, "AI 回复")

        # 3. TTS 语音生成设置模块
        self.tts_settings_tab = self.create_tts_settings_tab()
        self.tab_widget.addTab(self.tts_settings_tab, "TTS 语音设置")

        # 4. 批量文案 TTS 生成语音模块
        self.batch_tts_tab = self.create_batch_tts_tab()
        self.tab_widget.addTab(self.batch_tts_tab, "批量语音生成")

        # 5. 音频输出 API 模块 (新添加)
        self.audio_output_api_tab = self.create_audio_output_api_tab()
        self.tab_widget.addTab(self.audio_output_api_tab, "音频输出 API")

        # Initial setup for dynamic elements
        self.setup_initial_dynamic_states()

    def setup_initial_dynamic_states(self):
        # AI Reply Tab - Initial model selection
        self.rb_openai_model.setChecked(True)
        self.ai_model_stacked_widget.setCurrentIndex(0) # OpenAI page

        # TTS Settings Tab - Initial mode selection
        self.rb_tts_mode_pretrained.setChecked(True)
        self.tts_mode_stacked_widget.setCurrentIndex(0) # Pretrained voice page

        # Disable "Stop Monitoring" initially in TikTok tab
        self.btn_stop_monitor.setEnabled(False)

        # Disable speed adjustment if streaming is default (as per previous choice '否')
        self.rb_stream_no.setChecked(True)
        self.spinbox_speed.setEnabled(True)

        # Initialize the state of the new "Enable" checkboxes
        self.cb_enable_ai_reply.setChecked(True)
        self.cb_enable_tts_settings.setChecked(True)
        self.cb_enable_batch_tts.setChecked(True)
        # Ensure initial state for the new Audio Output API checkbox
        if hasattr(self, 'cb_enable_audio_output'):
            self.cb_enable_audio_output.setChecked(True)


    def create_tiktok_tab(self):
        tab = QWidget()
        # The main layout for the tab, which will hold the top and bottom split frames
        main_tab_layout = QVBoxLayout(tab)

        # Top Area Frame for connection and status
        top_area_frame = QFrame()
        top_area_layout = QVBoxLayout(top_area_frame)
        conn_group = QGroupBox("直播间连接与状态")
        conn_layout = QVBoxLayout(conn_group)

        # Horizontal layout for URL input and labels
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("直播间地址:"))
        self.tiktok_url_input = QLineEdit()
        self.tiktok_url_input.setPlaceholderText("请输入直播间ID或URL")
        self.tiktok_url_input.setText("") # Default empty string
        url_layout.addWidget(self.tiktok_url_input)
        conn_layout.addLayout(url_layout)

        # Horizontal layout for buttons
        btn_layout = QHBoxLayout()
        self.btn_start_monitor = QPushButton("开始监控")
        self.btn_stop_monitor = QPushButton("停止监控")
        self.btn_start_monitor.setEnabled(True) # Default state
        self.btn_stop_monitor.setEnabled(False) # Default state
        btn_layout.addWidget(self.btn_start_monitor)
        btn_layout.addWidget(self.btn_stop_monitor)
        conn_layout.addLayout(btn_layout)
        top_area_layout.addWidget(conn_group) # Add the group box to its layout
        main_tab_layout.addWidget(top_area_frame) # Add the top frame to the tab's main layout

        # Bottom Split Frame for comments and AI replies
        bottom_split_frame = QFrame()
        bottom_split_layout = QHBoxLayout(bottom_split_frame)

        # Comment Display Group
        comment_container_group = QGroupBox("评论展示")
        comment_container_layout = QVBoxLayout(comment_container_group)
        self.comment_display_box = QTextBrowser()
        self.comment_display_box.setReadOnly(True)
        comment_container_layout.addWidget(self.comment_display_box)
        bottom_split_layout.addWidget(comment_container_group, 2) # 2/3 width

        # AI Reply Display Group
        ai_reply_container_group = QGroupBox("AI 回复展示")
        ai_reply_container_layout = QVBoxLayout(ai_reply_container_group)
        self.ai_reply_label = QLabel("AI: ")
        self.ai_reply_label.setStyleSheet("font-weight: bold; color: blue;")
        self.ai_reply_label.setWordWrap(True)
        ai_reply_container_layout.addWidget(self.ai_reply_label)
        bottom_split_layout.addWidget(ai_reply_container_group, 1) # 1/3 width

        main_tab_layout.addWidget(bottom_split_frame) # Add the bottom frame to the tab's main layout

        return tab


    def create_ai_reply_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # --- New: Enable/Disable Checkbox for AI Reply Tab ---
        self.cb_enable_ai_reply = QCheckBox("开启 AI 回复功能")
        layout.addWidget(self.cb_enable_ai_reply)
        # --- End New ---

        # AI Model Selection
        self.model_selection_group = QGroupBox("AI 模型选择")
        model_selection_layout = QHBoxLayout(self.model_selection_group)
        self.rb_openai_model = QRadioButton("OpenAI 模型")
        self.rb_coze_agent = QRadioButton("Coze Agent")
        self.rb_dify_model = QRadioButton("dify")
        self.rb_openai_model.setChecked(True) # Default selected
        model_selection_layout.addWidget(self.rb_openai_model)
        model_selection_layout.addWidget(self.rb_coze_agent)
        model_selection_layout.addWidget(self.rb_dify_model)
        model_selection_layout.addStretch() # Push radio buttons to left
        layout.addWidget(self.model_selection_group)

        # Model Interface Settings (Dynamic)
        self.interface_settings_group = QGroupBox("模型接口设置")
        interface_layout = QVBoxLayout(self.interface_settings_group)
        self.ai_model_stacked_widget = QStackedWidget()

        # OpenAI Page
        openai_page = QWidget()
        openai_layout = QGridLayout(openai_page)
        openai_layout.addWidget(QLabel("OpenAI API 地址:"), 0, 0)
        self.openai_api_url_input = QLineEdit()
        self.openai_api_url_input.setPlaceholderText("https://api.openai.com/v1")
        openai_layout.addWidget(self.openai_api_url_input, 0, 1)
        openai_layout.addWidget(QLabel("OpenAI API Key:"), 1, 0)
        self.openai_api_key_input = QLineEdit()
        self.openai_api_key_input.setPlaceholderText("sk-xxxxxxxxxxxx")
        self.openai_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        openai_layout.addWidget(self.openai_api_key_input, 1, 1)
        openai_layout.addWidget(QLabel("OpenAI API 模型:"), 2, 0)
        self.openai_api_model_input = QLineEdit()
        self.openai_api_model_input.setPlaceholderText("gpt-3.5-turbo")
        openai_layout.addWidget(self.openai_api_model_input, 2, 1)
        self.ai_model_stacked_widget.addWidget(openai_page)

        # Coze Agent Page
        coze_page = QWidget()
        coze_layout = QGridLayout(coze_page)
        coze_layout.addWidget(QLabel("Base URL:"), 0, 0)
        self.coze_base_url_input = QLineEdit()
        self.coze_base_url_input.setPlaceholderText("xxxxxxxxxxx")
        coze_layout.addWidget(self.coze_base_url_input, 0, 1)
        coze_layout.addWidget(QLabel("API Key:"), 1, 0)
        self.coze_api_key_input = QLineEdit()
        self.coze_api_key_input.setPlaceholderText("xxxxxxxxxxx")
        self.coze_api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        coze_layout.addWidget(self.coze_api_key_input, 1, 1)
        coze_layout.addWidget(QLabel("Agent ID:"), 2, 0)
        self.coze_agent_id_input = QLineEdit()
        self.coze_agent_id_input.setPlaceholderText("xxxxxxxxxxx")
        coze_layout.addWidget(self.coze_agent_id_input, 2, 1)
        self.ai_model_stacked_widget.addWidget(coze_page)

        # Dify Page
        dify_page = QWidget()
        dify_layout = QGridLayout(dify_page)
        dify_layout.addWidget(QLabel("Base URL:"), 0, 0)
        self.dify_base_url_input = QLineEdit()
        self.dify_base_url_input.setPlaceholderText("xxxxxxx")
        dify_layout.addWidget(self.dify_base_url_input, 0, 1)
        dify_layout.addWidget(QLabel("API Key:"), 1, 0)
        self.dify_api_key_input = QLineEdit()
        self.dify_api_key_input.setPlaceholderText("xxxxxxx")
        self.dify_api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        dify_layout.addWidget(self.dify_api_key_input, 1, 1)
        dify_layout.addWidget(QLabel("Agent ID:"), 2, 0)
        self.dify_agent_id_input = QLineEdit()
        self.dify_agent_id_input.setPlaceholderText("xxxxxxx")
        dify_layout.addWidget(self.dify_agent_id_input, 2, 1)
        self.ai_model_stacked_widget.addWidget(dify_page)

        interface_layout.addWidget(self.ai_model_stacked_widget)
        layout.addWidget(self.interface_settings_group)

        # Connect radio buttons to stacked widget
        self.rb_openai_model.toggled.connect(lambda: self.ai_model_stacked_widget.setCurrentIndex(0))
        self.rb_coze_agent.toggled.connect(lambda: self.ai_model_stacked_widget.setCurrentIndex(1))
        self.rb_dify_model.toggled.connect(lambda: self.ai_model_stacked_widget.setCurrentIndex(2))


        # OpenAI Prompt Settings
        self.prompt_group = QGroupBox("OpenAI 接口提示词设置")
        prompt_layout = QVBoxLayout(self.prompt_group)
        self.openai_prompt_text = QTextEdit()
        self.openai_prompt_text.setPlaceholderText("你是一个热情的直播间助手...")
        self.openai_prompt_text.setText("你是一个热情的直播间助手...") # Default prompt
        prompt_layout.addWidget(self.openai_prompt_text)
        layout.addWidget(self.prompt_group)

        # Comment Fetch Frequency
        self.freq_group = QGroupBox("获取最新评论频率")
        freq_layout = QHBoxLayout(self.freq_group)
        self.freq_slider = QSlider(Qt.Orientation.Horizontal)
        self.freq_slider.setRange(1, 120)
        self.freq_slider.setValue(5) # Default value
        self.freq_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.freq_slider.setTickInterval(5)
        self.freq_label = QLabel(f"{self.freq_slider.value()} 秒")
        self.freq_slider.valueChanged.connect(lambda value: self.freq_label.setText(f"{value} 秒"))
        freq_layout.addWidget(self.freq_slider)
        freq_layout.addWidget(self.freq_label)
        layout.addWidget(self.freq_group)

        # Save/Clear Buttons
        self.btn_save_ai_config = QPushButton("保存配置")
        self.btn_clear_ai_config = QPushButton("清空配置")
        btn_layout = QHBoxLayout() # Moved inside to be part of the controlled widgets
        btn_layout.addWidget(self.btn_save_ai_config)
        btn_layout.addWidget(self.btn_clear_ai_config)
        layout.addLayout(btn_layout)

        layout.addStretch() # Push content to top

        # Connect the enable checkbox to toggle the state of other widgets
        self.cb_enable_ai_reply.toggled.connect(self.toggle_ai_reply_widgets)
        # Ensure initial state is applied
        self.toggle_ai_reply_widgets(self.cb_enable_ai_reply.isChecked())

        return tab

    def toggle_ai_reply_widgets(self, enabled):
        self.model_selection_group.setEnabled(enabled)
        self.interface_settings_group.setEnabled(enabled)
        self.prompt_group.setEnabled(enabled)
        self.freq_group.setEnabled(enabled)
        self.btn_save_ai_config.setEnabled(enabled)
        self.btn_clear_ai_config.setEnabled(enabled)


    def create_tts_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # --- New: Enable/Disable Checkbox for TTS Settings Tab ---
        self.cb_enable_tts_settings = QCheckBox("开启 TTS 语音功能")
        layout.addWidget(self.cb_enable_tts_settings)
        # --- End New ---

        # Inference Mode Selection
        self.mode_group = QGroupBox("推理模式选择")
        mode_layout = QHBoxLayout(self.mode_group)
        self.rb_tts_mode_pretrained = QRadioButton("预训练音色")
        self.rb_tts_mode_nl_control = QRadioButton("自然语言控制")
        self.rb_tts_mode_3s_clone = QRadioButton("3s 极速复刻")
        self.rb_tts_mode_cross_lang = QRadioButton("跨语种复刻")
        self.rb_tts_mode_pretrained.setChecked(True) # Default selected
        mode_layout.addWidget(self.rb_tts_mode_pretrained)
        mode_layout.addWidget(self.rb_tts_mode_nl_control)
        mode_layout.addWidget(self.rb_tts_mode_3s_clone)
        mode_layout.addWidget(self.rb_tts_mode_cross_lang)
        mode_layout.addStretch()
        layout.addWidget(self.mode_group)

        # Dynamic Configuration Area (QStackedWidget)
        self.dynamic_config_group = QGroupBox("模式配置")
        dynamic_config_layout = QVBoxLayout(self.dynamic_config_group)
        self.tts_mode_stacked_widget = QStackedWidget()

        # Pretrained Voice Page
        pretrained_page = QWidget()
        pretrained_layout = QVBoxLayout(pretrained_page)
        self.dropdown_pretrained_voice = QComboBox()
        # You'll populate this from CosyVoice API /refresh_sft_spk
        self.dropdown_pretrained_voice.addItem("请选择")
        pretrained_layout.addWidget(self.dropdown_pretrained_voice)
        pretrained_layout.setAlignment(self.dropdown_pretrained_voice, Qt.AlignmentFlag.AlignCenter)
        self.tts_mode_stacked_widget.addWidget(pretrained_page)

        # Natural Language Control Page
        nl_control_page = QWidget()
        nl_control_layout = QVBoxLayout(nl_control_page)
        self.tts_prompt_text_nl = QTextEdit()
        self.tts_prompt_text_nl.setPlaceholderText("请输入描述音色的文本...")
        nl_control_layout.addWidget(self.tts_prompt_text_nl)
        self.tts_mode_stacked_widget.addWidget(nl_control_page)

        # 3s Fast Clone Page
        clone_page = QWidget()
        clone_layout = QVBoxLayout(clone_page)
        clone_layout.addWidget(QLabel("选择参考音频列表:"))
        self.dropdown_ref_audio = QComboBox()
        # Populate from CosyVoice API /refresh_prompt_wav
        self.dropdown_ref_audio.addItem("请选择参考音频或者自己上传")
        clone_layout.addWidget(self.dropdown_ref_audio)

        audio_input_layout = QHBoxLayout()
        self.btn_upload_prompt_wav = QPushButton("上传 Prompt 音频")
        self.btn_record_prompt_wav = QPushButton("录制 Prompt 音频")
        audio_input_layout.addWidget(self.btn_upload_prompt_wav)
        audio_input_layout.addWidget(self.btn_record_prompt_wav)
        clone_layout.addLayout(audio_input_layout)

        self.tts_prompt_text_clone = QTextEdit()
        self.tts_prompt_text_clone.setPlaceholderText("输入 prompt 文本 (可识别)")
        clone_layout.addWidget(self.tts_prompt_text_clone)

        self.tts_instruct_text = QTextEdit()
        self.tts_instruct_text.setPlaceholderText("输入 instruct 文本")
        clone_layout.addWidget(self.tts_instruct_text)

        self.tts_mode_stacked_widget.addWidget(clone_page)

        # Cross-language Clone Page (Placeholder)
        cross_lang_page = QWidget()
        cross_lang_layout = QVBoxLayout(cross_lang_page)
        cross_lang_layout.addWidget(QLabel("跨语种复刻模式配置 (待定)"))
        self.tts_mode_stacked_widget.addWidget(cross_lang_page)

        dynamic_config_layout.addWidget(self.tts_mode_stacked_widget)
        layout.addWidget(self.dynamic_config_group)

        # Connect TTS mode radio buttons to stacked widget
        self.rb_tts_mode_pretrained.toggled.connect(lambda: self.tts_mode_stacked_widget.setCurrentIndex(0))
        self.rb_tts_mode_nl_control.toggled.connect(lambda: self.tts_mode_stacked_widget.setCurrentIndex(1))
        self.rb_tts_mode_3s_clone.toggled.connect(lambda: self.tts_mode_stacked_widget.setCurrentIndex(2))
        self.rb_tts_mode_cross_lang.toggled.connect(lambda: self.tts_mode_stacked_widget.setCurrentIndex(3))

        # General TTS Settings
        self.general_settings_group = QGroupBox("通用设置")
        general_settings_layout = QGridLayout(self.general_settings_group)
        general_settings_layout.addWidget(QLabel("随机推理种子:"), 0, 0)
        self.spinbox_random_seed = QSpinBox()
        self.spinbox_random_seed.setRange(0, 99999999) # Example range
        self.spinbox_random_seed.setValue(0) # Default value
        general_settings_layout.addWidget(self.spinbox_random_seed, 0, 1)
        self.btn_generate_random_seed = QPushButton("生成随机种子")
        general_settings_layout.addWidget(self.btn_generate_random_seed, 0, 2)

        general_settings_layout.addWidget(QLabel("是否流式推理:"), 1, 0)
        stream_layout = QHBoxLayout()
        self.rb_stream_yes = QRadioButton("是")
        self.rb_stream_no = QRadioButton("否")
        self.rb_stream_no.setChecked(True) # Default selected
        stream_layout.addWidget(self.rb_stream_yes)
        stream_layout.addWidget(self.rb_stream_no)
        general_settings_layout.addLayout(stream_layout, 1, 1, 1, 2) # Span 2 columns

        general_settings_layout.addWidget(QLabel("速度调节 (仅非流式):"), 2, 0)
        self.spinbox_speed = QDoubleSpinBox()
        self.spinbox_speed.setRange(0.5, 2.0) # Range 0.5-2.0
        self.spinbox_speed.setSingleStep(0.1)
        self.spinbox_speed.setValue(1.0) # Default value
        general_settings_layout.addWidget(self.spinbox_speed, 2, 1)

        # Connect stream radio buttons to speed spinbox enabled state
        self.rb_stream_yes.toggled.connect(lambda checked: self.spinbox_speed.setEnabled(not checked))
        self.rb_stream_no.toggled.connect(lambda checked: self.spinbox_speed.setEnabled(checked))

        layout.addWidget(self.general_settings_group)

        # Test Area
        self.test_group = QGroupBox("测试区")
        test_layout = QVBoxLayout(self.test_group)
        self.tts_test_text = QTextEdit()
        self.tts_test_text.setPlaceholderText("请输入要合成的文本...")
        test_layout.addWidget(self.tts_test_text)

        test_buttons_layout = QHBoxLayout()
        self.btn_generate_audio = QPushButton("生成音频")
        self.btn_play_audio = QPushButton("播放音频")
        self.btn_stop_audio = QPushButton("停止播放")
        test_buttons_layout.addWidget(self.btn_generate_audio)
        test_buttons_layout.addWidget(self.btn_play_audio)
        test_buttons_layout.addWidget(self.btn_stop_audio)
        test_layout.addLayout(test_buttons_layout)
        layout.addWidget(self.test_group)

        # Save/Clear Buttons
        self.btn_save_tts_config = QPushButton("保存配置")
        self.btn_clear_tts_config = QPushButton("清空配置")
        btn_layout = QHBoxLayout() # Moved inside to be part of the controlled widgets
        btn_layout.addWidget(self.btn_save_tts_config)
        btn_layout.addWidget(self.btn_clear_tts_config)
        layout.addLayout(btn_layout)

        layout.addStretch() # Push content to top

        # Connect the enable checkbox to toggle the state of other widgets
        self.cb_enable_tts_settings.toggled.connect(self.toggle_tts_settings_widgets)
        # Ensure initial state is applied
        self.toggle_tts_settings_widgets(self.cb_enable_tts_settings.isChecked())

        return tab

    def toggle_tts_settings_widgets(self, enabled):
        self.mode_group.setEnabled(enabled)
        self.dynamic_config_group.setEnabled(enabled)
        self.general_settings_group.setEnabled(enabled)
        self.test_group.setEnabled(enabled)
        self.btn_save_tts_config.setEnabled(enabled)
        self.btn_clear_tts_config.setEnabled(enabled)


    def create_batch_tts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # --- New: Enable/Disable Checkbox for Batch TTS Tab ---
        self.cb_enable_batch_tts = QCheckBox("开启批量语音生成功能")
        layout.addWidget(self.cb_enable_batch_tts)
        # --- End New ---

        # Document Management
        self.doc_manage_group = QGroupBox("文案管理")
        doc_manage_layout = QVBoxLayout(self.doc_manage_group) # Vertical layout for buttons
        self.btn_import_txt = QPushButton("导入本地 TXT 文档")
        self.btn_delete_selected_doc = QPushButton("删除选定文档")
        self.btn_clear_all_docs = QPushButton("清除所有文档")
        doc_manage_layout.addWidget(self.btn_import_txt)
        doc_manage_layout.addWidget(self.btn_delete_selected_doc)
        doc_manage_layout.addWidget(self.btn_clear_all_docs)
        layout.addWidget(self.doc_manage_group)

        # Document List
        self.doc_list_group = QGroupBox("文案列表")
        doc_list_layout = QVBoxLayout(self.doc_list_group)
        self.doc_list_widget = QListWidget()
        self.doc_list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection) # Allow multi-selection
        doc_list_layout.addWidget(self.doc_list_widget)
        layout.addWidget(self.doc_list_group)

        # Document Content Display
        self.doc_content_group = QGroupBox("文档内容展示")
        doc_content_layout = QVBoxLayout(self.doc_content_group)
        self.doc_content_display = QTextEdit()
        self.doc_content_display.setReadOnly(True) # Read-only
        self.doc_content_display.setText("") # Default empty
        doc_content_layout.addWidget(self.doc_content_display)
        layout.addWidget(self.doc_content_group)

        # Connect doc_list_widget selection to doc_content_display
        self.doc_list_widget.currentItemChanged.connect(self.display_selected_doc_content)

        # Playback Settings
        self.playback_group = QGroupBox("播放设置")
        playback_layout = QVBoxLayout(self.playback_group)
        self.cb_loop_playback = QCheckBox("文档顺序循环播放")
        self.cb_loop_playback.setChecked(True) # Default selected
        playback_layout.addWidget(self.cb_loop_playback)
        layout.addWidget(self.playback_group)

        # Document Sorting
        self.sort_group = QGroupBox("文档排序")
        sort_layout = QVBoxLayout(self.sort_group) # Vertical for the group
        move_buttons_layout = QHBoxLayout()
        self.btn_move_up = QPushButton("上移")
        self.btn_move_down = QPushButton("下移")
        move_buttons_layout.addWidget(self.btn_move_up)
        move_buttons_layout.addWidget(self.btn_move_down)
        sort_layout.addLayout(move_buttons_layout) # First row

        sort_type_buttons_layout = QHBoxLayout()
        self.btn_sort_by_name = QPushButton("按名称排序")
        self.btn_sort_by_import_time = QPushButton("按导入时间排序")
        sort_type_buttons_layout.addWidget(self.btn_sort_by_name)
        sort_type_buttons_layout.addWidget(self.btn_sort_by_import_time)
        sort_layout.addLayout(sort_type_buttons_layout) # Second row
        layout.addWidget(self.sort_group)

        # Batch Generation Control
        self.batch_control_group = QGroupBox("批量生成控制")
        batch_control_layout = QVBoxLayout(self.batch_control_group)

        gen_buttons_layout = QHBoxLayout()
        self.btn_start_batch_gen = QPushButton("开始批量生成")
        self.btn_stop_batch_gen = QPushButton("停止生成")
        gen_buttons_layout.addWidget(self.btn_start_batch_gen)
        gen_buttons_layout.addWidget(self.btn_stop_batch_gen)
        batch_control_layout.addLayout(gen_buttons_layout)

        batch_control_layout.addWidget(QLabel("进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0) # Initial value
        batch_control_layout.addWidget(self.progress_bar)

        batch_control_layout.addWidget(QLabel("状态/日志:"))
        self.batch_status_display = QTextBrowser() # Changed to QTextBrowser for more detailed logs
        self.batch_status_display.setReadOnly(True)
        self.batch_status_display.setText("等待操作...")
        batch_control_layout.addWidget(self.batch_status_display)

        layout.addWidget(self.batch_control_group)

        layout.addStretch() # Push content to top

        # Connect the enable checkbox to toggle the state of other widgets
        self.cb_enable_batch_tts.toggled.connect(self.toggle_batch_tts_widgets)
        # Ensure initial state is applied
        self.toggle_batch_tts_widgets(self.cb_enable_batch_tts.isChecked())

        return tab

    def toggle_batch_tts_widgets(self, enabled):
        self.doc_manage_group.setEnabled(enabled)
        self.doc_list_group.setEnabled(enabled)
        self.doc_content_group.setEnabled(enabled)
        self.playback_group.setEnabled(enabled)
        self.sort_group.setEnabled(enabled)
        self.batch_control_group.setEnabled(enabled)

    def create_audio_output_api_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # "开启/关闭" Checkbox
        self.cb_enable_audio_output = QCheckBox("开启/关闭 音频输出")
        layout.addWidget(self.cb_enable_audio_output)

        # "音频输出api" Label and "音频输出api框" QLineEdit
        api_group = QGroupBox("音频输出 API 设置")
        api_layout = QGridLayout(api_group)
        api_layout.addWidget(QLabel("音频输出 API 地址:"), 0, 0)
        self.audio_output_api_input = QLineEdit()
        self.audio_output_api_input.setPlaceholderText("请输入音频输出 API 地址")
        api_layout.addWidget(self.audio_output_api_input, 0, 1)
        layout.addWidget(api_group)

        layout.addStretch() # Push content to top

        return tab


    # Helper method to display content of selected document in batch TTS tab
    def display_selected_doc_content(self, current_item, previous_item):
        if current_item:
            # This is a placeholder. In a real app, you'd store the full content
            # or path of the document with the QListWidgetItem
            # For now, it just displays the item's text.
            self.doc_content_display.setText(f"文档内容: {current_item.text()}")
        else:
            self.doc_content_display.setText("")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TikTokAILiveApp()
    window.show()
    sys.exit(app.exec())