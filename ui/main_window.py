# ui/main_window.py
"""主窗口：无边框悬浮卡片，集成工具栏、卡片和底部导航
功能：
- 弹性布局 / QSizeGrip缩放 / 边缘拖拽缩放 / 尺寸记忆
- 三级联动筛选（册 -> 单元 -> 课程）
- 随机乱序背诵模式（Shuffle）
- 自动轮播伴学（Auto Play: 5s / 10s / 15s + 自动发音/静音）
- 掌握度快速标记（J 认识 / K 不熟悉加入生词本）
- 单击即时翻面与拖拽互斥
"""

import os
import sys

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSizePolicy, QSizeGrip, QMenu,
    QApplication, QGraphicsDropShadowEffect, QFileDialog
)
from PyQt6.QtCore import (
    Qt, QPoint, QRect, QTimer, pyqtSignal,
    QEasingCurve, QSize, QRectF, QEvent
)
from PyQt6.QtGui import (
    QPainter, QColor, QPainterPath, QBrush, QPen,
    QShortcut, QKeySequence, QFont, QCursor, QAction, QIcon
)

from ui.toast_widget import ToastWidget
from ui.clipboard_toast import ClipboardToast
from ui.translation_dialog import TranslationDialog
from core.clipboard_listener import ClipboardListener

from config.settings import (
    COLORS, THEME_CONFIGS, WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, WINDOW_BORDER_RADIUS
)
from core.vocab_manager import VocabManager
from core.tts_engine import TTSEngine
from core.vocab_book import VocabBook
from core.state_manager import StateManager
from core.boss_key import BossKeyManager
from core.font_manager import load_custom_fonts
from core.copybook_generator import CopybookGenerator
from core.statistics_manager import StatisticsManager
from core.ambience_player import AmbiencePlayer
from core.pomodoro_timer import PomodoroTimer
from ui.card_widget import CardWidget
from ui.toolbar_widget import ToolbarWidget
from ui.vocab_book_dialog import VocabBookDialog
from ui.settings_dialog import SettingsDialog
from ui.stats_dialog import StatsDialog
from ui.pomodoro_dialog import PomodoroDialog
from ui.system_tray import AppSystemTray
from ui.copybook_dialog import CopybookExportDialog


# ─── 边缘缩放区域宽度（像素） ────────────────────────────────────
RESIZE_MARGIN = 8


class MainWindow(QMainWindow):
    """主悬浮窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── 预加载自定义外部字体 ──
        load_custom_fonts()

        # ── 核心模块 ──
        self._vocab = VocabManager()
        self._tts = TTSEngine()
        self._vocab_book = VocabBook()
        self._state = StateManager()
        self._theme = self._state.get("theme", "dark")
        self._compact = self._state.get_bool("compact_mode", False)
        self._review_mode = self._state.get_bool("review_mode", False)

        # 系统托盘与关闭行为（默认关闭时最小化到托盘驻留）
        self._minimize_to_tray = self._state.get_bool("minimize_to_tray", True)
        self._is_force_exit = False

        # 快捷键总控状态（默认禁用，纯鼠标防冲突模式）
        self._shortcuts_enabled = self._state.get_bool("shortcuts_enabled", False)
        self._custom_shortcuts = self._state.get_shortcuts()
        self._shortcuts = []
        self._is_spelling_mode = False
        self._is_audio_first = self._state.get_bool("audio_first_mode", False)

        # 自动轮播与发音控制
        self._autoplay_interval = self._state.get_int("autoplay_interval", 0)
        self._auto_speak = self._state.get_bool("auto_speak", True)
        self._korean_font = self._state.get("korean_font", "Malgun Gothic")
        self._font_scale = self._state.get_float("font_scale", 1.0)
        self._stats_manager = StatisticsManager(self._state.db_path)
        self._autoplay_timer = QTimer(self)
        self._autoplay_timer.timeout.connect(self._on_autoplay_tick)

        # 鼠标穿透/锁定模式状态
        self._is_click_through = False

        # 极简窄条/边缘挂件模式状态与独立尺寸记忆 (Mini Ticker)
        self._is_minibar = False
        self._minibar_height = 36        # 边缘挂件模式固定高度 (36px 超薄圆角)
        self._normal_size = None         # 进入窄条前的尺寸快照

        # 系统托盘驻留
        self._tray = AppSystemTray(self)
        self._tray.toggle_window_requested.connect(self._on_tray_toggle_window)
        self._tray.toggle_click_through_requested.connect(self._toggle_click_through)
        self._tray.toggle_minibar_requested.connect(self._toggle_minibar)
        self._tray.toggle_clip_requested.connect(self._toggle_clipboard_capture)
        self._tray.open_settings_requested.connect(self._open_settings)
        self._tray.exit_app_requested.connect(self._exit_app_completely)
        self._tray.show()

        # 系统级全局老板键 (Ctrl + ~)
        self._boss_key = BossKeyManager(self)
        self._boss_key.triggered.connect(self.toggle_visibility)
        self._boss_key.start()

        # 拖拽移动/缩放状态
        self._drag_pos: QPoint = QPoint()
        self._resize_dir: str = ""          # 缩放方向
        self._resize_start_geom: QRect = QRect()
        self._resize_start_cursor: QPoint = QPoint()

        # ── 窗口属性 ──
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # ── 设置窗口标题与图标 ──
        self.setWindowTitle("未来的韩语卡片")
        from utils.path_helper import get_resource_path
        ico_path = get_resource_path(os.path.join("assets", "app_icon.ico"))
        if not os.path.exists(ico_path):
            ico_path = get_resource_path(os.path.join("assets", "app_icon.png"))
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

        # ── 还原窗口尺寸 ──
        saved_w = self._state.get_int("window_width", WINDOW_DEFAULT_WIDTH)
        saved_h = self._state.get_int("window_height", WINDOW_DEFAULT_HEIGHT)
        self.resize(max(saved_w, WINDOW_MIN_WIDTH), max(saved_h, WINDOW_MIN_HEIGHT))

        # ── 还原位置 ──
        x = self._state.get_int("window_x", 100)
        y = self._state.get_int("window_y", 100)
        self.move(x, y)

        # ── 还原背景透明度 (保持窗口本身 1.0 实心，仅背景着色应用 Alpha) ──
        self._bg_opacity = self._state.get_float("bg_opacity", self._state.get_float("opacity", 0.92))
        self.setWindowOpacity(1.0)

        # ── 🎯 加权智能复习模式状态与 2 秒停留已学计时器 ──
        self._is_weighted_review: bool = False
        self._review_target_count: int = self._state.get_review_batch_size()
        self._review_mastered_count: int = 0
        self._review_unfamiliar_count: int = 0
        self._saved_normal_state: dict = {}

        self._seen_timer = QTimer(self)
        self._seen_timer.setSingleShot(True)
        self._seen_timer.timeout.connect(self._on_seen_timeout)

        # ── 🎧 专注伴学与番茄钟引擎 ──
        self._ambience_player = AmbiencePlayer()
        self._pomodoro_timer = PomodoroTimer(self)
        self._pomodoro_timer.tick.connect(self._on_pomodoro_tick)
        self._pomodoro_timer.state_changed.connect(self._on_pomodoro_state_changed)
        self._pomodoro_timer.finished.connect(self._on_pomodoro_finished)
        self._pomodoro_dialog: Optional[PomodoroDialog] = None

        # ── 📋 全局剪贴板智能划词监听与微气泡 ──
        self._clip_listener = ClipboardListener(vocab_manager=self._vocab, parent=self)
        self._clip_toast = ClipboardToast(None)
        self._clip_listener.clip_translated_captured.connect(self._on_clip_translated_captured)
        self._clip_toast.add_requested.connect(self._on_clip_word_add)
        self._clip_toast.speak_requested.connect(self._tts.speak)
        self._clip_toast.translate_requested.connect(self._on_clip_deep_translate)

        # ── 🔍 极简中韩智能翻译抽屉 ──
        self._translation_dialog: Optional[TranslationDialog] = None

        # ── 构建 UI ──
        self._setup_ui()
        self._setup_shortcuts()

        # ── 应用主题与字体 ──
        self._card.set_korean_font(self._korean_font)
        self.apply_theme(self._theme)

        # ── 还原透明度滑块值 ──
        self._toolbar.set_opacity_value(self._bg_opacity)

        # ── 还原筛选与断点进度 ──
        self._restore_filter()

        # ── 还原极简模式 ──
        if self._compact:
            self._toolbar._toggle_compact()

        # ── 还原盲听磨耳朵模式 ──
        self._toolbar.set_audio_first_state(self._is_audio_first)
        self._card.set_audio_first_mode(self._is_audio_first)

        # ── 还原轮播 ──
        if self._autoplay_interval > 0:
            self._toolbar.set_autoplay_interval(self._autoplay_interval)
            self._autoplay_timer.start(self._autoplay_interval * 1000)

        self._toolbar.set_autospeak_state(self._auto_speak)

        # ── 更新卡片显示 ──
        self._show_current_word()

    # ─────────────────────────────────────────────────────────
    # UI 构建
    # ─────────────────────────────────────────────────────────

    def _setup_ui(self):
        # 中心容器
        self._container = QWidget(self)
        self._container.setObjectName("container")
        self._container.setMouseTracking(True)
        self.setCentralWidget(self._container)

        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 工具栏（固定高度区域）──
        self._toolbar = ToolbarWidget(self._container)
        self._toolbar.book_changed.connect(self._on_book_changed)
        self._toolbar.unit_changed.connect(self._on_unit_changed)
        self._toolbar.lesson_changed.connect(self._on_lesson_changed)
        self._toolbar.shuffle_toggled.connect(self._on_shuffle_toggled)
        self._toolbar.autoplay_interval_changed.connect(self._on_autoplay_interval_changed)
        self._toolbar.autospeak_toggled.connect(self._on_autospeak_toggled)
        self._toolbar.audio_first_toggled.connect(self._on_audio_first_toggled)
        self._toolbar.spelling_toggled.connect(self._on_spelling_toggled)
        self._toolbar.compact_toggled.connect(self._on_compact_toggled)
        self._toolbar.theme_toggled.connect(self.apply_theme)
        self._toolbar.click_through_toggled.connect(self._on_click_through_toggled)
        self._toolbar.minibar_toggled.connect(self._on_minibar_toggled)
        self._toolbar.vocab_book_clicked.connect(self._open_vocab_book)
        self._toolbar.export_copybook_clicked.connect(self._export_copybook)
        self._toolbar.stats_clicked.connect(self._open_stats_dialog)
        self._toolbar.pomodoro_clicked.connect(self._open_pomodoro_dialog)
        self._toolbar.translate_clicked.connect(self._open_translator)
        self._toolbar.settings_clicked.connect(self._open_settings)
        self._toolbar.opacity_changed.connect(self._on_bg_opacity_changed)
        self._toolbar.close_clicked.connect(self.close)
        self._toolbar.exit_clicked.connect(self._exit_app_completely)
        self._toolbar.speak_current_requested.connect(self._speak_current)
        self._toolbar.start_weighted_review_requested.connect(self.start_weighted_review)
        self._toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self._toolbar)

        # ── 卡片区（弹性自适应，stretch=1 占满剩余空间）──
        self._card = CardWidget(self._container)
        self._card.set_font_scale(self._font_scale)
        self._card.set_korean_font(self._korean_font)
        self._card.speak_requested.connect(self._tts.speak)
        self._card.spelling_passed.connect(self._on_spelling_passed)
        self._card.spelling_exit_requested.connect(self._exit_spelling_mode)
        self._card.antonym_jump_requested.connect(self._on_antonym_jump_requested)
        self._tts.started.connect(self._card.on_speak_started)
        self._tts.finished.connect(self._card.on_speak_finished)
        self._card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(self._card, stretch=1)

        # ── 底部导航与掌握度工具栏 ──
        self._nav_bar = QWidget(self._container)
        self._nav_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        nav_layout = QHBoxLayout(self._nav_bar)
        nav_layout.setContentsMargins(14, 4, 14, 6)
        nav_layout.setSpacing(8)

        # 掌握度快捷操作: 不熟悉 (K)
        self._unfamiliar_btn = QPushButton("✗ 不熟 (K)")
        self._unfamiliar_btn.setFixedHeight(32)
        self._unfamiliar_btn.setToolTip("不熟悉 (K): 收藏到生词本并翻面查看释义")
        self._unfamiliar_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._unfamiliar_btn.clicked.connect(self._mark_unfamiliar)
        nav_layout.addWidget(self._unfamiliar_btn)

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedSize(32, 32)
        self._prev_btn.setToolTip("上一个 (←)")
        self._prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._prev_btn.clicked.connect(self._prev_word)
        nav_layout.addWidget(self._prev_btn)

        self._progress_label = QLabel("1 / 1")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        prog_shadow = QGraphicsDropShadowEffect(self)
        prog_shadow.setBlurRadius(8)
        prog_shadow.setColor(QColor(0, 0, 0, 220))
        prog_shadow.setOffset(0, 1)
        self._progress_label.setGraphicsEffect(prog_shadow)
        nav_layout.addWidget(self._progress_label)

        self._star_btn = QPushButton("☆")
        self._star_btn.setFixedSize(32, 32)
        self._star_btn.setToolTip("收藏到生词本 (Ctrl+S / S)")
        self._star_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._star_btn.clicked.connect(self._toggle_star)
        nav_layout.addWidget(self._star_btn)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedSize(32, 32)
        self._next_btn.setToolTip("下一个 (→)")
        self._next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._next_btn.clicked.connect(self._next_word)
        nav_layout.addWidget(self._next_btn)

        # 掌握度快捷操作: 认识 (J)
        self._mastered_btn = QPushButton("✓ 认识 (J)")
        self._mastered_btn.setFixedHeight(32)
        self._mastered_btn.setToolTip("已掌握 (J): 标记掌握并跳到下一个词")
        self._mastered_btn.clicked.connect(self._mark_mastered)
        nav_layout.addWidget(self._mastered_btn)

        main_layout.addWidget(self._nav_bar)

        # ── 复习模式标签 ──
        self._review_badge = QLabel("生词本复习模式")
        self._review_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._review_badge.setFixedHeight(22)
        self._review_badge.setVisible(False)
        main_layout.addWidget(self._review_badge)

        # ── 底部状态行（包装在 QWidget 容器中，便于整体控制与安全隐藏）──
        self._bottom_bar_widget = QWidget(self._container)
        self._bottom_bar_widget.setObjectName("bottom_bar_widget")
        bottom_bar = QHBoxLayout(self._bottom_bar_widget)
        bottom_bar.setContentsMargins(8, 2, 8, 4)
        bottom_bar.setSpacing(10)

        # 今日已学去重计数微小胶囊徽章
        self._today_badge = QLabel("今日已学: 0")
        self._today_badge.setObjectName("today_badge")
        self._today_badge.setToolTip("今日实际浏览学习的不重复韩语单词总数（每日 0 点自动重置）")
        bottom_bar.addWidget(self._today_badge, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        # 极简番茄专注呼吸微徽章
        self._pomodoro_badge = QPushButton("伴学时钟")
        self._pomodoro_badge.setObjectName("pomodoro_badge")
        self._pomodoro_badge.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._pomodoro_badge.setToolTip("点击打开专注伴学与番茄时钟面板 (Ctrl+T)")
        self._pomodoro_badge.clicked.connect(self._open_pomodoro_dialog)
        self._update_pomodoro_badge_style()
        bottom_bar.addWidget(self._pomodoro_badge, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        bottom_bar.addStretch(1)

        # QSizeGrip — 右下角缩放手柄
        self._size_grip = QSizeGrip(self)
        self._size_grip.setFixedSize(18, 18)
        self._size_grip.setToolTip("拖拽调整窗口大小")
        bottom_bar.addWidget(self._size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(self._bottom_bar_widget)

        # ── Mini Bar 窄条单行显示区（默认隐藏）──
        self._minibar_widget = QWidget(self._container)
        self._minibar_widget.setObjectName("minibar_widget")
        self._minibar_widget.setVisible(False)
        self._minibar_widget.setFixedHeight(self._minibar_height)
        minibar_layout = QHBoxLayout(self._minibar_widget)
        minibar_layout.setContentsMargins(14, 0, 8, 0)
        minibar_layout.setSpacing(6)

        # 韩文+发音+释义单行文本（垂直居中对齐，支持穿透拖拽）
        self._minibar_label = QLabel("")
        self._minibar_label.setObjectName("minibar_label")
        self._minibar_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._minibar_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        mb_shadow = QGraphicsDropShadowEffect(self)
        mb_shadow.setBlurRadius(14)
        mb_shadow.setColor(QColor(0, 0, 0, 240))
        mb_shadow.setOffset(0, 1)
        self._minibar_label.setGraphicsEffect(mb_shadow)
        minibar_layout.addWidget(self._minibar_label, stretch=1)

        # Mini Bar 上的快捷操作按钮
        _mb_prev = QPushButton("◀")
        _mb_prev.setFixedSize(26, 26)
        _mb_prev.setToolTip("上一个 (←)")
        _mb_prev.clicked.connect(self._prev_word)
        minibar_layout.addWidget(_mb_prev)

        _mb_next = QPushButton("▶")
        _mb_next.setFixedSize(26, 26)
        _mb_next.setToolTip("下一个 (→)")
        _mb_next.clicked.connect(self._next_word)
        minibar_layout.addWidget(_mb_next)

        _mb_speak = QPushButton("读")
        _mb_speak.setFixedSize(26, 26)
        _mb_speak.setToolTip("发音 (V)")
        _mb_speak.clicked.connect(self._speak_current)
        minibar_layout.addWidget(_mb_speak)

        _mb_restore = QPushButton("卡")
        _mb_restore.setFixedSize(26, 26)
        _mb_restore.setToolTip("还原完整卡片 (Ctrl+B)")
        _mb_restore.clicked.connect(self._toggle_minibar)
        minibar_layout.addWidget(_mb_restore)

        self._minibar_btns = [_mb_prev, _mb_next, _mb_speak, _mb_restore]

        main_layout.addWidget(self._minibar_widget)

        # ── 初始化下拉与全量词库引用 ──
        self._card.set_all_words(self._vocab.all_words)
        self._toolbar.populate_books(self._vocab.get_books())

    def _setup_shortcuts(self):
        """根据自定义配置动态绑定全局快捷键并纳入总控管理"""
        for sc in self._shortcuts:
            sc.setEnabled(False)
            sc.deleteLater()
        self._shortcuts.clear()

        sc_map = self._custom_shortcuts or {}

        # 1. 动态可配置动作
        action_bindings = [
            ("flip", self._on_space),
            ("prev", self._prev_word),
            ("next", self._next_word),
            ("audio", self._speak_current),
            ("mark_mastered", self._mark_mastered),
            ("mark_unfamiliar", self._mark_unfamiliar),
        ]

        for action_name, handler in action_bindings:
            key_str = sc_map.get(action_name, "").strip()
            if key_str:
                try:
                    sc = QShortcut(QKeySequence(key_str), self, activated=handler)
                    self._shortcuts.append(sc)
                except Exception:
                    pass

        # 2. 全键盘盲操核心快捷键（Space / Enter / J / K / R / V / S / F2 / Ctrl+T / Ctrl+L / Esc 等）
        core_blind_shortcuts = [
            ("Return", self._on_space),
            ("Enter", self._on_space),
            ("J", self._mark_mastered),
            ("K", self._mark_unfamiliar),
            ("R", self._speak_current),
            ("V", self._speak_current),
            ("S", self._toggle_star),
            ("Ctrl+S", self._toggle_star),
            ("F2", self._toggle_minibar),
            ("Ctrl+B", self._toggle_minibar),
            ("Ctrl+T", self._open_translator),
            ("Ctrl+F", self._open_translator),
            ("Ctrl+L", self._toggle_click_through),
            ("Ctrl+Shift+T", self._open_pomodoro_dialog),
            ("Ctrl+Shift+C", self._toggle_clipboard_capture),
            ("Ctrl+M", self._toolbar._toggle_compact),
            ("Ctrl+R", self._toggle_shuffle),
            ("Ctrl+A", self._cycle_autoplay),
            ("Ctrl+H", self.toggle_visibility),
            ("Ctrl+P", self._speak_current),
            ("Ctrl+I", self._open_stats_dialog),
            ("Ctrl+,", self._open_settings),
            (Qt.Key.Key_Escape, self._on_escape_pressed),
        ]
        for key, handler in core_blind_shortcuts:
            try:
                sc = QShortcut(QKeySequence(key), self, activated=handler)
                self._shortcuts.append(sc)
            except Exception:
                pass

        self.set_shortcuts_enabled(self._shortcuts_enabled)
        self._update_button_tooltips()

    def _update_button_tooltips(self):
        """根据当前快捷键配置动态刷新界面按钮提示文字与标签"""
        sc = self._custom_shortcuts or {}
        prev_k = sc.get("prev", "")
        next_k = sc.get("next", "")
        mastered_k = sc.get("mark_mastered", "")
        unfamiliar_k = sc.get("mark_unfamiliar", "")

        self._prev_btn.setToolTip(f"上一个 ({prev_k})" if prev_k else "上一个")
        self._next_btn.setToolTip(f"下一个 ({next_k})" if next_k else "下一个")
        self._mastered_btn.setText(f"✓ 认识 ({mastered_k})" if mastered_k else "✓ 认识")
        self._mastered_btn.setToolTip(f"已掌握 ({mastered_k}): 标记掌握并跳到下一个词" if mastered_k else "已掌握: 标记掌握并跳到下一个词")
        self._unfamiliar_btn.setText(f"✗ 不熟 ({unfamiliar_k})" if unfamiliar_k else "✗ 不熟")
        self._unfamiliar_btn.setToolTip(f"不熟悉 ({unfamiliar_k}): 收藏到生词本并翻面查看释义" if unfamiliar_k else "不熟悉: 收藏到生词本并翻面查看释义")

    def set_shortcuts_enabled(self, enabled: bool):
        """全局/局部快捷键总控开关：一键启用或禁用所有快捷键"""
        self._shortcuts_enabled = enabled
        for sc in self._shortcuts:
            sc.setEnabled(enabled)
        self._state.set("shortcuts_enabled", "1" if enabled else "0")

    def keyPressEvent(self, event):
        """键盘按键拦截总控：若禁用则完全忽略按键，绝不影响其他操作"""
        if not self._shortcuts_enabled:
            event.ignore()
            return
        super().keyPressEvent(event)

    # ─────────────────────────────────────────────────────────
    # 词汇导航与掌握度
    # ─────────────────────────────────────────────────────────

    def _on_bg_opacity_changed(self, opacity: float):
        """背景独立透明度调节（前景文字与控件始终保持 100% 实心）"""
        self._bg_opacity = max(0.0, min(1.0, opacity))
        self._state.set("bg_opacity", f"{self._bg_opacity:.2f}")
        self._state.set("opacity", f"{self._bg_opacity:.2f}")
        self.update()

    def _on_seen_timeout(self):
        """当前单词停留展示超过 2 秒，自动标记为已学"""
        word = self._vocab.current_word()
        if word and str(word.get("id")) not in ["empty_vocab", "empty_hint", "0"]:
            self._state.record_word_action(word.get("id"), word.get("korean", ""), "seen")

    def _show_current_word(self):
        word = self._vocab.current_word()
        if word:
            self._card.set_word(word)
            self._update_star_state(word)

            # 启动 2 秒停留已学计时器
            self._seen_timer.start(2000)

            # 智能复习中进度指示
            if self._is_weighted_review:
                cur_idx = self._vocab.current_index + 1
                tot = self._vocab.total()
                self._progress_label.setText(f"{cur_idx} / {tot}")
                self._review_badge.setText(f"加权智能复习中 ({cur_idx}/{tot})")
                self._review_badge.setVisible(True)
            else:
                self._progress_label.setText(self._vocab.progress_text())
                if not self._review_mode:
                    self._review_badge.setVisible(False)

            # 记录今日已学不重复单词
            today_count = self._state.record_study_word(word.get("korean", ""))
            self._today_badge.setText(f"今日已学: {today_count}")

            # 后台静默预抓取周边词条音频 (N-1, N+1, N+2)，实现毫秒级零延迟秒播
            nearby_words = self._vocab.get_nearby_words(window=2)
            if nearby_words:
                self._tts.prefetch([w.get("korean", "") for w in nearby_words])

            # 盲听磨耳朵模式：切词时自动播放该词音频，让用户先听音猜测
            if self._is_audio_first and not self._is_spelling_mode:
                self._tts.speak(word.get("korean", ""))
        else:
            if self._review_mode or self._is_weighted_review:
                empty_card = {
                    "id": "empty_vocab",
                    "korean": "生词本为空",
                    "meaning": "学习时点击 ☆ 收藏生词或按 K 记入生词本",
                    "pos": "提示",
                    "word_type": "pure",
                    "examples": [{
                        "korean": "단어를 복습해 보세요!",
                        "chinese": "快去在教材中收藏一些生词来复习吧！"
                    }]
                }
                self._card.set_word(empty_card)
                self._star_btn.setText("☆")
                self._progress_label.setText("0 / 0")
            else:
                self._progress_label.setText(self._vocab.progress_text())
            today_count = self._state.get_today_count()
            self._today_badge.setText(f"今日已学: {today_count}")
        self._save_current_state()
        # Mini Bar 模式下同步刷新单行内容
        if self._is_minibar:
            self._update_minibar_text()

    def _save_current_state(self):
        """单事务毫秒级极速保存当前学习断点进度与窗口状态（<1ms）"""
        curr_word = self._vocab.current_word()
        word_id = curr_word.get("id", 0) if curr_word else 0
        word_kr = curr_word.get("korean", "") if curr_word else ""

        pos = self.pos()
        state_dict = {
            "window_x": pos.x(),
            "window_y": pos.y(),
            "window_width": self.width(),
            "window_height": self.height(),
            "opacity": getattr(self, "_bg_opacity", 0.92),
            "compact_mode": "1" if self._compact else "0",
            "theme": self._theme,
            "current_book": str(self._vocab._current_book),
            "last_book": str(self._vocab._current_book),
            "current_unit": str(getattr(self._vocab, "_current_unit", 0)),
            "last_unit": str(getattr(self._vocab, "_current_unit", 0)),
            "current_lesson": str(self._vocab._current_lesson),
            "last_lesson": str(self._vocab._current_lesson),
            "current_index": str(self._vocab.current_index),
            "last_card_index": str(self._vocab.current_index),
            "review_mode": "1" if self._review_mode else "0",
            "shuffle_mode": "1" if self._vocab.is_shuffle else "0",
            "autoplay_interval": str(self._autoplay_interval),
            "auto_speak": "1" if self._auto_speak else "0",
            "shortcuts_enabled": "1" if self._shortcuts_enabled else "0",
            "font_scale": str(self._font_scale),
            "korean_font": self._korean_font,
            "minimize_to_tray": "1" if self._minimize_to_tray else "0",
            "audio_first_mode": "1" if self._is_audio_first else "0",
        }
        if word_id:
            state_dict["last_word_id"] = str(word_id)
        if word_kr:
            state_dict["last_word_korean"] = str(word_kr)

        self._state.set_many(state_dict)

    def _reset_autoplay_timer(self):
        """用户交互时重置轮播倒计时，留足阅读时间"""
        if self._autoplay_timer.isActive() and self._autoplay_interval > 0:
            self._autoplay_timer.start(self._autoplay_interval * 1000)

    def _next_word(self):
        self._reset_autoplay_timer()
        if self._is_weighted_review and self._vocab.current_index >= self._vocab.total() - 1:
            self._finish_weighted_review()
            return
        self._vocab.next_word()
        self._show_current_word()

    def _prev_word(self):
        self._reset_autoplay_timer()
        self._vocab.prev_word()
        self._show_current_word()

    def _mark_mastered(self):
        """标记当前单词已掌握并跳至下一词 (J)"""
        self._reset_autoplay_timer()
        word = self._vocab.current_word()
        if word and str(word.get("id")) not in ["empty_vocab", "empty_hint", "0"]:
            self._vocab.mark_mastered(word["id"])
            self._state.record_word_action(word["id"], word.get("korean", ""), "mastered")
            if self._is_weighted_review:
                self._review_mastered_count += 1

        if self._is_weighted_review and self._vocab.current_index >= self._vocab.total() - 1:
            self._finish_weighted_review()
            return

        self._vocab.next_word()
        self._show_current_word()

    def _mark_unfamiliar(self):
        """标记不熟悉：加入生词本并翻面查看释义 (K)"""
        self._reset_autoplay_timer()
        word = self._vocab.current_word()
        if word and str(word.get("id")) not in ["empty_vocab", "empty_hint", "0"]:
            if not self._vocab_book.is_starred(word["id"]):
                self._vocab_book.add(word)
            self._apply_star_style(True)
            self._state.record_word_action(word["id"], word.get("korean", ""), "unfamiliar")
            if self._is_weighted_review:
                self._review_unfamiliar_count += 1
            if not self._card._is_back:
                self._card.flip()

    def _on_space(self):
        if getattr(self, "_is_spelling_mode", False):
            return
        self._reset_autoplay_timer()
        word = self._vocab.current_word()
        if word and str(word.get("id")) not in ["empty_vocab", "empty_hint", "0"]:
            self._state.record_word_action(word["id"], word.get("korean", ""), "seen")
        self._card.flip()

    # ─────────────────────────────────────────────────────────
    # 🎯 科学加权智能复习模式状态机
    # ─────────────────────────────────────────────────────────

    def start_weighted_review(self, count: int = 20):
        """启动科学加权智能复习模式"""
        if not self._is_weighted_review:
            # 记录进入复习前的常规状态
            self._saved_normal_state = {
                "book": self._vocab._current_book,
                "unit": getattr(self._vocab, "_current_unit", 0),
                "lesson": self._vocab._current_lesson,
                "index": self._vocab.current_index,
            }

        self._is_weighted_review = True
        self._review_target_count = count
        self._review_mastered_count = 0
        self._review_unfamiliar_count = 0

        # 生成加权复习题集
        batch_words = self._vocab.generate_weighted_review_batch(count, self._state)
        if not batch_words:
            return

        self._vocab.apply_review_batch(batch_words)
        self._review_badge.setText(f"🎯 加权智能复习中 (1/{len(batch_words)})")
        self._review_badge.setVisible(True)
        self._show_current_word()

    def _finish_weighted_review(self):
        """本轮复习完成，弹出结算轻弹窗"""
        from ui.review_summary_dialog import ReviewSummaryDialog
        total = self._vocab.total()
        unfam = self._review_unfamiliar_count
        mast = self._review_mastered_count
        # 若有未标记项，默认算入掌握
        if mast + unfam < total:
            mast = total - unfam

        dialog = ReviewSummaryDialog(
            total_count=total,
            mastered_count=mast,
            unfamiliar_count=unfam,
            theme=self._theme,
            parent=self
        )
        dialog.restart_requested.connect(lambda: self.start_weighted_review(self._review_target_count))
        result = dialog.exec()
        if result == ReviewSummaryDialog.DialogCode.Accepted and not dialog._btn_restart.signalsBlocked():
            # 用户点击返回常规学习模式
            self.exit_weighted_review()

    def exit_weighted_review(self):
        """退出加权智能复习模式，平滑恢复常规模式与上次断点"""
        self._is_weighted_review = False
        self._review_badge.setVisible(False)
        saved = getattr(self, "_saved_normal_state", {})
        if saved:
            b = saved.get("book", 1)
            u = saved.get("unit", 0)
            l = saved.get("lesson", 0)
            idx = saved.get("index", 0)
            self._vocab.apply_filter(book=b, unit=u, lesson=l)
            self._vocab.jump_to(idx)
        self._show_current_word()

    def _on_spelling_toggled(self, enabled: bool):
        """开启或退出键盘韩打拼写练习测验模式 (T)"""
        self._is_spelling_mode = enabled
        self._card.set_spelling_mode(enabled)
        self._toolbar.set_spelling_state(enabled)
        if enabled:
            self._autoplay_timer.stop()
            self._card._spelling_input.setFocus()
        else:
            if self._autoplay_interval > 0:
                self._autoplay_timer.start(self._autoplay_interval * 1000)
            self._show_current_word()

    def _exit_spelling_mode(self):
        """退出拼写练习模式，恢复常规正面卡片"""
        if getattr(self, "_is_spelling_mode", False):
            self._on_spelling_toggled(False)

    def _on_shortcut_spelling(self):
        """快捷键 T 触发拼写模式切换"""
        self._on_spelling_toggled(not getattr(self, "_is_spelling_mode", False))

    def _on_spelling_passed(self):
        """拼写正确核对通过：自动记录掌握并切至下一词"""
        word = self._vocab.current_word()
        if word and str(word.get("id")) not in ["empty_vocab", "empty_hint", "0"]:
            self._state.record_word_action(word["id"], word.get("korean", ""), "mastered")
            if self._is_weighted_review:
                self._review_mastered_count += 1

        if self._is_weighted_review and self._vocab.current_index >= self._vocab.total() - 1:
            self._finish_weighted_review()
            return

        self._vocab.next_word()
        self._show_current_word()

    def _on_escape_pressed(self):
        """Esc 按键：1. 退出穿透模式；2. 退出窄条模式；3. 退出拼写测验模式；4. 退出加权复习；5. 最小化或关闭"""
        if getattr(self, "_is_click_through", False):
            self._toggle_click_through()
            return
        if getattr(self, "_is_minibar", False):
            self._toggle_minibar()
            return
        if getattr(self, "_is_spelling_mode", False):
            self._exit_spelling_mode()
            return
        if getattr(self, "_is_weighted_review", False):
            self.exit_weighted_review()
            return
        self.close()

    def _speak_current(self):
        """手动请求播放当前词发音"""
        word = self._vocab.current_word()
        if word:
            self._tts.speak(word.get("korean", ""))

    # ─────────────────────────────────────────────────────────
    # 随机乱序 & 自动轮播伴学
    # ─────────────────────────────────────────────────────────

    def _on_shuffle_toggled(self, enabled: bool):
        self._vocab.set_shuffle(enabled)
        self._show_current_word()

    def _toggle_shuffle(self):
        self._toolbar._on_shuffle_clicked()

    def _on_autoplay_interval_changed(self, seconds: int):
        self._autoplay_interval = seconds
        if seconds > 0:
            self._autoplay_timer.start(seconds * 1000)
            if self._auto_speak:
                self._speak_current()
        else:
            self._autoplay_timer.stop()

    def _cycle_autoplay(self):
        self._toolbar._on_autoplay_clicked()

    def _on_autospeak_toggled(self, enabled: bool):
        self._auto_speak = enabled

    def _on_autoplay_tick(self):
        """自动轮播计时器触发"""
        self._vocab.next_word()
        self._show_current_word()
        if self._auto_speak:
            self._speak_current()

    # ─────────────────────────────────────────────────────────
    # 三级联动筛选逻辑（册 -> 单元 -> 课程）
    # ─────────────────────────────────────────────────────────

    def _on_book_changed(self, book: int):
        if book == -1:
            self._enter_vocab_book_mode()
            return

        if self._review_mode:
            self._exit_review_mode()

        self._toolbar._unit_combo.setEnabled(True)
        self._toolbar._lesson_combo.setEnabled(True)
        self._vocab.apply_filter(book=book, unit=0, lesson=0)
        units = self._vocab.get_units(book)
        self._toolbar.populate_units(units)
        lessons = self._vocab.get_lessons(book, 0)
        self._toolbar.populate_lessons(lessons)
        self._show_current_word()

    def _on_unit_changed(self, unit: int):
        if self._review_mode:
            self._exit_review_mode()
        book = self._vocab._current_book
        self._vocab.apply_filter(book=book, unit=unit, lesson=0)
        lessons = self._vocab.get_lessons(book, unit)
        self._toolbar.populate_lessons(lessons)
        self._show_current_word()

    def _on_lesson_changed(self, lesson: int):
        if self._review_mode:
            self._exit_review_mode()
        book = self._vocab._current_book
        unit = getattr(self._vocab, "_current_unit", 0)
        self._vocab.apply_filter(book=book, unit=unit, lesson=lesson)
        self._show_current_word()

    def _restore_filter(self):
        """程序启动时精准恢复上次的筛选条件与具体卡片断点"""
        book        = self._state.get_int("current_book",   1)  # 默认第1册
        unit        = self._state.get_int("current_unit",   0)
        lesson      = self._state.get_int("current_lesson", 0)
        index       = self._state.get_int("current_index",  0)
        last_wid    = self._state.get("last_word_id",       "")
        last_wkr    = self._state.get("last_word_korean",   "")
        is_shuffle  = self._state.get_bool("shuffle_mode",  False)

        # 1. 填充并选择册数
        books = self._vocab.get_books()
        self._toolbar.populate_books(books)
        self._toolbar.set_book_index(book)

        if book == -1 or self._review_mode:
            self._enter_vocab_book_mode()
        else:
            # 2. 填充并选择单元
            units = self._vocab.get_units(book)
            self._toolbar.populate_units(units)
            self._toolbar.set_unit_index(unit)

            # 3. 填充并选择课程
            lessons = self._vocab.get_lessons(book, unit)
            self._toolbar.populate_lessons(lessons)
            self._toolbar.set_lesson_index(lesson)

            self._vocab.apply_filter(book=book, unit=unit, lesson=lesson)

        # 4. 还原乱序状态
        if is_shuffle:
            self._vocab.set_shuffle(True)
            self._toolbar.set_shuffle_state(True)

        # 5. 精准恢复到上次停留的具体单词位置 (优先根据 ID / 韩文定位，次之根据 index)
        restored = False
        if last_wid and last_wid != "0":
            restored = self._vocab.jump_to_word(word_id=last_wid)
        if not restored and last_wkr:
            restored = self._vocab.jump_to_word(korean=last_wkr)
        if not restored:
            self._vocab.jump_to(index)

    # ─────────────────────────────────────────────────────────
    # 生词本与待复习专属模式
    # ─────────────────────────────────────────────────────────

    def _apply_star_style(self, is_starred: bool):
        """动态切换收藏按钮外观（未收藏中性灰白 ☆ / 已收藏金色柔光 ★）"""
        if is_starred:
            self._star_btn.setText("★")
            self._star_btn.setStyleSheet(
                "QPushButton { background: rgba(241, 196, 15, 0.16); color: #F1C40F; "
                "border: 1px solid rgba(241, 196, 15, 0.45); font-size: 15px; border-radius: 16px; }"
                "QPushButton:hover { background: rgba(241, 196, 15, 0.28); border-color: #F1C40F; color: #FFFFFF; }"
            )
        else:
            self._star_btn.setText("☆")
            self._star_btn.setStyleSheet(
                "QPushButton { background: rgba(20, 20, 26, 0.78); color: #A0A5B5; "
                "border: 1px solid rgba(255, 255, 255, 0.22); font-size: 15px; border-radius: 16px; }"
                "QPushButton:hover { background: rgba(255, 255, 255, 0.16); color: #FFFFFF; border-color: rgba(255, 255, 255, 0.40); }"
            )

    def _update_star_state(self, word: Dict):
        if not word:
            self._apply_star_style(False)
            return
        is_starred = self._vocab_book.is_starred(word["id"])
        self._apply_star_style(is_starred)

    def _toggle_star(self):
        word = self._vocab.current_word()
        if not word or word.get("id") == "empty_vocab":
            return
        is_now_starred = self._vocab_book.toggle(word)
        self._apply_star_style(is_now_starred)
        # 平滑过渡：在生词本模式下取消标星时保留当前卡片展示，避免突然跳变

    def _open_vocab_book(self):
        items = self._vocab_book.get_all()
        dialog = VocabBookDialog(items, theme=self._theme, parent=self)
        dialog.review_requested.connect(self._enter_vocab_book_mode)
        dialog.export_requested.connect(self._export_copybook)
        result = dialog.exec()
        for wid in dialog.get_removed_ids():
            self._vocab_book.remove(wid)
        if self._review_mode:
            self._enter_vocab_book_mode()

    def _export_copybook(self):
        """一键导出高清手写临摹字帖 (支持田字格/米字格/极简手账横线与PDF/PNG)"""
        # 1. 优先提取当前生词本中收藏的词汇
        words_to_export = self._vocab_book.get_all()
        export_title = "未来的韩语卡片 · 生词临摹字帖"
        sub_desc = f"我的生词本 · 共 {len(words_to_export)} 词"

        # 如果生词本为空，则导出当前课程/单元正在学习的词汇列表
        if not words_to_export:
            current_words = getattr(self._vocab, "_filtered_words", [])
            if current_words:
                words_to_export = list(current_words)
                export_title = "未来的韩语卡片 · 随堂临摹字帖"
                sub_desc = f"当前课程 · 随堂生词临摹 (共 {len(words_to_export)} 词)"
            else:
                ToastWidget.show_toast(self, "当前生词本与学习列表为空，暂无生词可导出。<br>请先点击 ⭐ 收藏若干生词！", icon="⚠️")
                return

        # 2. 弹出 Instagram 极简毛玻璃字帖导出排版对话框
        dlg = CopybookExportDialog(
            words_count=len(words_to_export),
            current_theme=self._theme,
            parent=self
        )

        def _do_generate(export_info: dict):
            grid_style = export_info.get("grid_style", "tian")
            save_path = export_info.get("save_path", "")
            if not save_path:
                return

            try:
                generator = CopybookGenerator(font_family=self._korean_font)
                out_files = generator.generate(
                    words=words_to_export,
                    output_path=save_path,
                    title=export_title,
                    subtitle=sub_desc,
                    grid_style=grid_style
                )

                if not out_files:
                    raise RuntimeError("未生成任何文件")

                first_file = out_files[0]
                ToastWidget.show_toast(
                    self,
                    f"🎉 <b>A4 字帖已成功生成！</b><br><span style='color:#94A3B8; font-size:11px;'>已保存至: {os.path.basename(first_file)}</span>",
                    icon="📄",
                    duration_ms=3000
                )
            except Exception as e:
                ToastWidget.show_toast(self, f"❌ 生成手写字帖失败: {str(e)}", icon="⚠️", duration_ms=3000)

        dlg.export_started.connect(_do_generate)
        dlg.exec()

    def _open_stats_dialog(self):
        """打开学习热力图打卡看板弹窗"""
        dialog = StatsDialog(stats_manager=self._stats_manager, theme=self._theme, parent=self)
        dialog.exec()

    def _open_pomodoro_dialog(self):
        """打开专注伴学与番茄时钟控制面板"""
        if self._pomodoro_dialog is None:
            self._pomodoro_dialog = PomodoroDialog(
                timer=self._pomodoro_timer,
                player=self._ambience_player,
                parent=self
            )
        self._pomodoro_dialog.show()
        self._pomodoro_dialog.raise_()
        self._pomodoro_dialog.activateWindow()

    def _on_pomodoro_tick(self, rem_sec: int, formatted: str, mode: str, prog: float):
        """番茄钟每秒倒计时更新状态徽标"""
        self._update_pomodoro_badge_text()

    def _on_pomodoro_state_changed(self, state: str, mode: str):
        """番茄钟状态或阶段改变更新徽标"""
        self._update_pomodoro_badge_text()
        self._update_pomodoro_badge_style()

    def _on_pomodoro_finished(self, completed_mode: str):
        """番茄钟单阶段倒计时结束（轻量 Toast 提醒 + 专属磬音，绝不触发系统叮咚声）"""
        self._ambience_player.play_chime()
        self._update_pomodoro_badge_text()
        self._update_pomodoro_badge_style()

        stage_name = "25分钟专注阶段" if completed_mode == PomodoroTimer.MODE_FOCUS else "5分钟休息阶段"
        next_stage = "惬意休息 5 分钟" if completed_mode == PomodoroTimer.MODE_FOCUS else "深度专注 25 分钟"
        
        ToastWidget.show_toast(
            self,
            f"🎉 <b>{stage_name}已圆满完成！</b><br><span style='color: #94A3B8; font-size: 11px;'>接下来进入: {next_stage}</span>",
            icon="🔔",
            duration_ms=3500
        )

    def _update_pomodoro_badge_text(self):
        """更新底部伴学时钟徽标文本"""
        if not hasattr(self, "_pomodoro_badge"):
            return
        state = self._pomodoro_timer.state
        mode = self._pomodoro_timer.mode
        time_str = self._pomodoro_timer.get_formatted_time()
        amb_type = self._ambience_player.get_current_type()

        amb_icon = ""
        if amb_type == "rain": amb_icon = "🌧️ "
        elif amb_type == "cafe": amb_icon = "☕ "
        elif amb_type == "white": amb_icon = "🌊 "

        if state == PomodoroTimer.STATE_RUNNING:
            prefix = "🎯" if mode == PomodoroTimer.MODE_FOCUS else "☕"
            self._pomodoro_badge.setText(f"{amb_icon}{prefix} {time_str}")
        elif state == PomodoroTimer.STATE_PAUSED:
            self._pomodoro_badge.setText(f"{amb_icon}⏸ {time_str}")
        else:
            if amb_type != "none":
                self._pomodoro_badge.setText(f"{amb_icon}伴学中")
            else:
                self._pomodoro_badge.setText("🎧 伴学时钟")

    def _update_pomodoro_badge_style(self):
        """更新底部伴学时钟徽标的 Instagram 极简发光样式"""
        if not hasattr(self, "_pomodoro_badge"):
            return
        state = self._pomodoro_timer.state
        mode = self._pomodoro_timer.mode
        amb_type = self._ambience_player.get_current_type()

        if state == PomodoroTimer.STATE_RUNNING:
            if mode == PomodoroTimer.MODE_FOCUS:
                style = "background: rgba(239, 68, 68, 0.22); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.45);"
            else:
                style = "background: rgba(16, 185, 129, 0.22); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.45);"
        elif state == PomodoroTimer.STATE_PAUSED:
            style = "background: rgba(251, 191, 36, 0.22); color: #FCD34D; border: 1px solid rgba(251, 191, 36, 0.45);"
        elif amb_type != "none":
            style = "background: rgba(59, 130, 246, 0.22); color: #93C5FD; border: 1px solid rgba(59, 130, 246, 0.45);"
        else:
            style = "background: rgba(255, 255, 255, 0.08); color: #CBD5E1; border: 1px solid rgba(255, 255, 255, 0.16);"

        self._pomodoro_badge.setStyleSheet(
            f"QPushButton#pomodoro_badge {{ {style} border-radius: 9px; padding: 1px 8px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton#pomodoro_badge:hover {{ background: rgba(255, 255, 255, 0.20); color: #FFFFFF; }}"
        )

    def _on_antonym_jump_requested(self, target_kr: str):
        """点击反义词标签平滑跳转到目标单词"""
        if not target_kr:
            return

        # 1. 尝试在当前筛选列表中直接跳转
        if self._vocab.jump_to_korean(target_kr):
            self._show_current_word()
            return

        # 2. 若当前列表中未找到（如在不同册数或单元），查找全量词库
        target_word = self._vocab.find_word_by_korean(target_kr)
        if target_word:
            target_book = target_word.get("_book", target_word.get("book", 1))
            target_unit = target_word.get("_unit", target_word.get("unit", 0))
            target_lesson = target_word.get("_lesson", target_word.get("lesson", 0))

            # 切换到对应的册、单元、课程
            self._toolbar.set_book_index(target_book)
            self._on_book_changed(target_book)
            if target_unit > 0:
                self._toolbar.set_unit_index(target_unit)
                self._on_unit_changed(target_unit)
            if target_lesson > 0:
                self._toolbar.set_lesson_index(target_lesson)
                self._on_lesson_changed(target_lesson)

            self._vocab.jump_to_korean(target_kr)
            self._show_current_word()

    def _enter_vocab_book_mode(self):
        """进入生词本待复习专属过滤模式"""
        self._review_mode = True
        self._review_badge.setVisible(True)
        self._toolbar.set_book_index(-1)

        # 单元与课程下拉框显示为「全部生词」并临时禁用
        self._toolbar._unit_combo.blockSignals(True)
        self._toolbar._unit_combo.clear()
        self._toolbar._unit_combo.addItem("全部生词", 0)
        self._toolbar._unit_combo.setEnabled(False)
        self._toolbar._unit_combo.blockSignals(False)

        self._toolbar._lesson_combo.blockSignals(True)
        self._toolbar._lesson_combo.clear()
        self._toolbar._lesson_combo.addItem("全部生词", 0)
        self._toolbar._lesson_combo.setEnabled(False)
        self._toolbar._lesson_combo.blockSignals(False)

        ids = self._vocab_book.get_all_ids()
        self._vocab.apply_filter(book=-1, word_ids=ids)
        self._show_current_word()

    def _enter_review_mode(self):
        self._enter_vocab_book_mode()

    def _exit_review_mode(self):
        self._review_mode = False
        self._review_badge.setVisible(False)
        self._toolbar._unit_combo.setEnabled(True)
        self._toolbar._lesson_combo.setEnabled(True)

    def _open_settings(self):
        dialog = SettingsDialog(
            current_font=self._korean_font,
            current_scale=self._font_scale,
            shortcuts_enabled=self._shortcuts_enabled,
            minimize_to_tray=self._minimize_to_tray,
            vocab_manager=self._vocab,
            vocab_book=self._vocab_book,
            state_manager=self._state,
            theme=self._theme,
            parent=self
        )
        dialog.font_changed.connect(self._on_font_changed)
        dialog.font_scale_changed.connect(self._on_font_scale_changed)
        dialog.theme_changed.connect(self.apply_theme)
        dialog.shortcuts_toggled.connect(self.set_shortcuts_enabled)
        dialog.shortcuts_mapping_changed.connect(self._on_shortcuts_mapping_changed)
        dialog.minimize_to_tray_toggled.connect(self._on_minimize_tray_toggled)
        dialog.autostart_toggled.connect(self._on_autostart_toggled)
        dialog.backup_restored.connect(self._on_backup_restored)
        dialog.vocab_imported.connect(self._on_vocab_imported)
        dialog.exec()

    def _on_shortcuts_mapping_changed(self, new_shortcuts: dict):
        """实时更新自定义快捷键绑定与按钮提示"""
        self._custom_shortcuts = dict(new_shortcuts)
        self._setup_shortcuts()

    def _on_audio_first_toggled(self, enabled: bool):
        """盲听磨耳朵模式切换"""
        self._is_audio_first = enabled
        self._card.set_audio_first_mode(enabled)
        self._state.set("audio_first_mode", "1" if enabled else "0")
        if enabled and not getattr(self, "_is_spelling_mode", False):
            curr = self._vocab.current_word()
            if curr:
                self._tts.speak(curr.get("korean", ""))


    def _on_backup_restored(self):
        """从备份文件恢复后，全量刷新界面、词库进度与偏好设置"""
        self._theme = self._state.get("theme", "dark")
        self._korean_font = self._state.get("korean_font", "Malgun Gothic")
        self._font_scale = self._state.get_float("font_scale", 1.0)
        self._shortcuts_enabled = self._state.get_bool("shortcuts_enabled", False)
        self._custom_shortcuts = self._state.get_shortcuts()
        self._setup_shortcuts()
        self._minimize_to_tray = self._state.get_bool("minimize_to_tray", True)
        self._is_audio_first = self._state.get_bool("audio_first_mode", False)

        # 刷新卡片与工具栏状态
        self._card.set_korean_font(self._korean_font)
        self._card.set_font_scale(self._font_scale)
        self._card.set_audio_first_mode(self._is_audio_first)
        self._toolbar.set_audio_first_state(self._is_audio_first)
        self.apply_theme(self._theme)

        # 恢复词库断点进度
        b = self._state.get_int("current_book", 1)
        u = self._state.get_int("current_unit", 0)
        l = self._state.get_int("current_lesson", 0)
        idx = self._state.get_int("current_index", 0)

        self._vocab.set_book(b)
        self._vocab.set_unit(u)
        self._vocab.set_lesson(l)
        self._vocab.jump_to_index(idx)

        self._toolbar.set_book(b)
        self._toolbar.set_unit(u)
        self._toolbar.set_lesson(l)
        self._show_current_word()

    def _on_minimize_tray_toggled(self, enabled: bool):
        self._minimize_to_tray = enabled
        self._state.set("minimize_to_tray", "1" if enabled else "0")

    def _on_autostart_toggled(self, enabled: bool):
        self._state.set("autostart", "1" if enabled else "0")

    def contextMenuEvent(self, event):
        """右键菜单：Instagram / iOS 纯粹极简排版驱动菜单"""
        menu = QMenu(self)

        # ── 视图与模式 ──
        menu.addSection("视图与模式")

        action_shortcuts = menu.addAction("启用键盘快捷键")
        action_shortcuts.setCheckable(True)
        action_shortcuts.setChecked(self._shortcuts_enabled)
        action_shortcuts.toggled.connect(self.set_shortcuts_enabled)

        action_minibar = menu.addAction("屏幕边缘极简磁吸条\tF2")
        action_minibar.setCheckable(True)
        action_minibar.setChecked(self._is_minibar)
        action_minibar.triggered.connect(self._toggle_minibar)

        action_click_through = menu.addAction("鼠标穿透模式\tCtrl+L")
        action_click_through.setCheckable(True)
        action_click_through.setChecked(self._is_click_through)
        action_click_through.triggered.connect(self._toggle_click_through)

        # 主题风格子菜单
        theme_menu = menu.addMenu("主题风格")
        theme_names = {
            "seoul_night": "首尔夜色 (深黑磨砂)",
            "cream_latte": "奶油拿铁 (极简米白)",
            "matcha_mint": "抹茶薄荷 (墨绿翠光)",
            "night_violet": "暗夜紫罗兰 (暗熏紫粉)",
        }
        for t_id, t_cfg in THEME_CONFIGS.items():
            display_name = theme_names.get(t_id, t_cfg.get("name", t_id))
            t_action = theme_menu.addAction(display_name)
            t_action.setCheckable(True)
            t_action.setChecked(self._theme == t_id or (self._theme == "dark" and t_id == "seoul_night") or (self._theme == "light" and t_id == "cream_latte"))
            t_action.triggered.connect(lambda checked, tid=t_id, tname=display_name: self._switch_theme(tid, tname))

        menu.addSeparator()

        # ── 学习与工具 ──
        menu.addSection("学习与工具")

        action_trans = menu.addAction("极简中韩互译\tCtrl+T")
        action_trans.triggered.connect(self._open_translator)

        action_vocab = menu.addAction("我的生词本\tCtrl+S")
        action_vocab.triggered.connect(self._open_vocab_book)

        action_stats = menu.addAction("学习足迹与打卡\tCtrl+I")
        action_stats.triggered.connect(self._open_stats_dialog)

        action_pomodoro = menu.addAction("专注伴学与番茄钟\tCtrl+Shift+T")
        action_pomodoro.triggered.connect(self._open_pomodoro_dialog)

        action_shuffle = menu.addAction("随机乱序背诵\tCtrl+R")
        action_shuffle.setCheckable(True)
        action_shuffle.setChecked(self._vocab.is_shuffle)
        action_shuffle.toggled.connect(self._toolbar.set_shuffle_state)
        action_shuffle.toggled.connect(self._on_shuffle_toggled)

        action_clip = menu.addAction("剪贴板划词监听\tCtrl+Shift+C")
        action_clip.setCheckable(True)
        action_clip.setChecked(self._clip_listener.is_enabled)
        action_clip.triggered.connect(self._toggle_clipboard_capture)

        menu.addSeparator()

        # ── 系统 ──
        menu.addSection("系统")

        action_settings = menu.addAction("偏好设置与词库管理\tCtrl+,")
        action_settings.triggered.connect(self._open_settings)

        action_close = menu.addAction("隐藏窗口\tCtrl+H")
        action_close.triggered.connect(self.toggle_visibility)

        # 样式与主题匹配
        cfg = THEME_CONFIGS.get(self._theme, THEME_CONFIGS.get("seoul_night"))
        is_dark = cfg.get("is_dark", True) if cfg else True
        bg = "rgba(20, 24, 32, 0.98)" if is_dark else "rgba(250, 250, 252, 0.98)"
        text = "#E2E8F0" if is_dark else "#1E293B"
        border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        hover_bg = "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.05)"

        menu_qss = f"""
            QMenu {{
                background: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 6px;
            }}
            QMenu::section {{
                color: #64748B;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 14px 4px 14px;
            }}
            QMenu::item {{
                background: transparent;
                color: {text};
                font-size: 12px;
                padding: 6px 20px 6px 14px;
                border-radius: 6px;
                margin: 1px 2px;
            }}
            QMenu::item:selected {{
                background: {hover_bg};
                color: {text};
            }}
            QMenu::separator {{
                height: 1px;
                background: {border};
                margin: 4px 8px;
            }}
        """
        menu.setStyleSheet(menu_qss)
        if theme_menu:
            theme_menu.setStyleSheet(menu_qss)

        menu.exec(event.globalPos())

    def _toggle_clipboard_capture(self):
        """一键开启/暂停全局剪贴板划词捕获"""
        enabled = self._clip_listener.toggle_enabled()
        status_text = "已开启" if enabled else "已暂停"
        ToastWidget.show_toast(self, f"剪贴板划词监听：<b>{status_text}</b>", icon="", duration_ms=2000)


    def _open_translator(self):
        """呼出或收起 Instagram 风格极简中韩翻译抽屉"""
        if self._translation_dialog is None:
            self._translation_dialog = TranslationDialog(tts_engine=self._tts, theme=self._theme, parent=self)
            self._translation_dialog.word_added_to_custom.connect(self._on_custom_word_added_from_translator)

        if self._translation_dialog.isVisible():
            self._translation_dialog.hide()
        else:
            # 智能计算对齐位置（优先放置在主窗口右侧）
            card_geo = self.geometry()
            screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

            target_x = card_geo.right() + 12
            target_y = card_geo.top()
            if target_x + 460 > screen_geo.right():
                target_x = max(screen_geo.left() + 20, card_geo.left() - 460 - 12)

            self._translation_dialog.move(target_x, target_y)
            self._translation_dialog.show()
            self._translation_dialog.raise_()
            self._translation_dialog.activateWindow()

    def _on_custom_word_added_from_translator(self, kr: str, cn: str, pron: str):
        """翻译抽屉一键收词回调"""
        self._vocab.load()
        if self._current_book == -2:
            self._on_book_changed(-2)

    def _on_clip_translated_captured(self, payload: dict):
        """剪贴板划词秒级翻译完成回调，展示微气泡"""
        self._clip_toast.show_clip_data(payload)

    def _on_clip_deep_translate(self, query: str):
        """从剪贴板微气泡一键展开完整翻译抽屉并自动填入查询"""
        self._open_translator()
        if self._translation_dialog and query:
            self._translation_dialog._input_edit.setPlainText(query)

    def _on_clip_word_add(self, korean: str, meaning: str, pron: str):
        """剪贴板微气泡一键收录生词本"""
        self._clip_listener.add_to_custom_vocab(korean, meaning, pron)
        self._vocab.load()
        if self._current_book == -2:
            self._on_book_changed(-2)
        ToastWidget.show_toast(
            self,
            f"🎉 <b>已成功收入生词本！</b><br><span style='color: #38BDF8;'>{html.escape(korean)}</span>",
            icon="📥",
            duration_ms=2000
        )

    def _switch_theme(self, theme_id: str, theme_name: str):
        """即时无缝切换主题风格并弹出轻量 Toast 提示"""
        self.apply_theme(theme_id)
        ToastWidget.show_toast(self, f"🎨 已切换至主题：<b>{theme_name}</b>", icon="✨", duration_ms=2000)

    def _on_font_changed(self, font_family: str):
        self._korean_font = font_family
        self._card.set_korean_font(font_family)
        self._state.set("korean_font", font_family)

    def _on_font_scale_changed(self, scale: float):
        self._font_scale = scale
        self._card.set_font_scale(scale)
        self._state.set("font_scale", str(scale))

    def _on_vocab_imported(self, book_title: str):
        """外部词库导入成功后，重新加载词库并动态刷新三级下拉框"""
        self._vocab.load()
        books = self._vocab.get_books()
        self._toolbar.populate_books(books)
        
        # 自动切换到新导入的词书
        for b_id, b_name in books:
            if b_name == book_title:
                self._toolbar.set_book_index(b_id)
                self._on_book_changed(b_id)
                break

    # ─────────────────────────────────────────────────────────
    # 主题 & 模式
    # ─────────────────────────────────────────────────────────

    def apply_theme(self, theme: str):
        if theme == "dark":
            theme = "seoul_night"
        elif theme == "light":
            theme = "cream_latte"

        self._theme = theme
        self._state.set("theme", theme)

        cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["seoul_night"])
        bg_rgb = cfg.get("bg_color", (18, 20, 26))
        card_bg = cfg.get("card_bg", "#161922")
        input_bg = cfg.get("input_bg", "#1F2330")
        is_dark = cfg.get("is_dark", True)
        accent = cfg.get("accent", "#2ECC71")
        text = cfg.get("text_primary", "#FFFFFF")
        text_sec = cfg.get("text_secondary", "#94A3B8")
        border = cfg.get("border", "rgba(255, 255, 255, 0.10)")

        self._bg_color = QColor(*bg_rgb)
        self._border_color = QColor(255, 255, 255, 36) if is_dark else QColor(0, 0, 0, 32)

        self._container.setStyleSheet(
            "QWidget#container { background: transparent; }"
        )

        # 底部翻页按钮（高对比深色磨砂圆形胶囊）
        nav_btn_style = (
            f"QPushButton {{ background: {input_bg}; color: {text}; "
            f"border: 1px solid {border}; border-radius: 16px; font-size: 13px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {accent}35; border-color: {accent}; color: #FFFFFF; }}"
        )
        self._prev_btn.setStyleSheet(nav_btn_style)
        self._next_btn.setStyleSheet(nav_btn_style)

        # 认识 / 不熟悉 掌握度 Instagram 风格高对比胶囊药丸（极速辨识）
        self._mastered_btn.setStyleSheet(
            f"QPushButton {{ background: {input_bg}; color: {accent}; "
            f"border: 1.5px solid {accent}; border-radius: 16px; font-size: 11px; font-weight: 700; padding: 2px 14px; }}"
            f"QPushButton:hover {{ background: {accent}35; color: #FFFFFF; border-color: {accent}; }}"
        )
        self._unfamiliar_btn.setStyleSheet(
            f"QPushButton {{ background: {input_bg}; color: #FF6B6B; "
            f"border: 1.5px solid rgba(255, 107, 107, 0.65); border-radius: 16px; font-size: 11px; font-weight: 700; padding: 2px 14px; }}"
            f"QPushButton:hover {{ background: rgba(255, 107, 107, 0.28); color: #FFFFFF; border-color: #FF6B6B; }}"
        )

        # 收藏按钮（黄星高亮 / 银白待藏）
        word = self._vocab.current_word()
        is_starred = self._vocab_book.is_starred(word["id"]) if word else False
        self._apply_star_style(is_starred)

        self._progress_label.setStyleSheet(
            f"QLabel {{ color: {text}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; }}"
        )
        self._review_badge.setStyleSheet(
            f"QLabel {{ color: #FFD166; font-size: 11px; "
            f"font-weight: 600; background: {input_bg}; "
            f"border: 1px solid rgba(255, 209, 102, 0.35); "
            f"border-radius: 10px; padding: 2px 8px; }}"
        )

        # 今日已学徽章样式（高对比半透黑底药丸）
        today_badge_style = (
            f"QLabel#today_badge {{ "
            f"  background: {input_bg}; "
            f"  color: #FFAA88; "
            f"  border: 1px solid rgba(255, 170, 136, 0.35); "
            f"  border-radius: 10px; "
            f"  padding: 2px 8px; "
            f"  font-size: 11px; "
            f"  font-weight: 600; "
            f"}}"
        )
        self._today_badge.setStyleSheet(today_badge_style)

        # 全局 Instagram / iOS 毛玻璃 QMenu 菜单样式
        menu_bg = card_bg if is_dark else "rgba(250, 250, 252, 0.98)"
        menu_border = border

        menu_qss = (
            f"QMenu {{ background: {menu_bg}; color: {text}; border: 1px solid {menu_border}; "
            f"border-radius: 12px; padding: 6px 4px; }}"
            f"QMenu::item {{ padding: 7px 22px 7px 12px; border-radius: 7px; font-size: 12px; font-weight: 500; margin: 1px 3px; }}"
            f"QMenu::item:selected {{ background: {accent}55; color: #FFFFFF; }}"
            f"QMenu::item:disabled {{ color: {text_sec}; font-size: 11px; font-weight: 700; padding-top: 8px; padding-bottom: 2px; }}"
            f"QMenu::separator {{ height: 1px; background: {menu_border}; margin: 4px 8px; }}"
        )
        self.setStyleSheet(menu_qss)

        # SizeGrip 样式
        self._size_grip.setStyleSheet(
            f"QSizeGrip {{ background: transparent; image: none; "
            f"width: 18px; height: 18px; }}"
        )

        self._toolbar.apply_theme(theme)
        self._card.apply_theme(theme)
        if hasattr(self, "_tray"):
            self._tray.apply_theme(theme)

        # ── Mini Bar 研条样式 ──
        if hasattr(self, "_minibar_label"):
            self._minibar_label.setStyleSheet(
                f"QLabel#minibar_label {{ color: {text}; font-size: 14px; font-weight: 600; "
                f"font-family: '{self._korean_font}', 'Malgun Gothic', sans-serif; letter-spacing: 0.3px; }}"
            )
            btn_style = (
                f"QPushButton {{ background: {input_bg}; color: {text}; border: 1px solid {border}; "
                f"border-radius: 7px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {accent}55; color: #FFFFFF; border-color: {accent}; }}"
            )
            for btn in self._minibar_btns:
                btn.setStyleSheet(btn_style)

        self.update()

    def _on_compact_toggled(self, compact: bool):
        """Compact 极简模式（隐藏下半部分）"""
        if self._is_minibar:
            # 窄条模式下不响应 compact 信号，避免冲突
            return
        self._compact = compact
        self._card.set_compact(compact)
        self._nav_bar.setVisible(not compact)

    # ─────────────────────────────────────────────────────
    # 🔒 鼠标穿透 / 锁定模式 (Click-Through Mode)
    # ─────────────────────────────────────────────────────

    def _toggle_click_through(self):
        """Ctrl+L 快捷键入口：切换穿透模式"""
        self._toolbar._on_click_through_clicked()

    def _on_click_through_toggled(self, enabled: bool):
        """切换窗口鼠标穿透属性"""
        self._is_click_through = enabled

        current_flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        if enabled:
            # 开启穿透：窗口层级提升，输入事件屏蔽，背景透明度设为半透明
            self.setWindowFlags(current_flags | Qt.WindowType.WindowTransparentForInput)
            self._bg_opacity = 0.50
            self._toolbar.set_opacity_value(0.50)
            if hasattr(self, "_tray"):
                self._tray.show_message(
                    "🔒 鼠标穿透已开启",
                    "鼠标现可穿透卡片直接操作下方软件。\n随时右键或单击系统托盘图标即可立即解除穿透！"
                )
        else:
            # 退出穿透：恢复正常窗口属性与用户自定义背景透明度
            self.setWindowFlags(current_flags)
            prev_opacity = self._state.get_float("bg_opacity", self._state.get_float("opacity", 0.92))
            self._bg_opacity = prev_opacity
            self.setWindowOpacity(1.0)
            self._toolbar.set_opacity_value(prev_opacity)

        self.show()   # setWindowFlags 后必须重新调用 show() 挂载窗口 Flag
        self.activateWindow()
        self.raise_()
        self.update()
        self._state.set("click_through_mode", "1" if enabled else "0")

        # 同步工具栏与托盘状态
        self._toolbar.set_click_through_state(enabled)
        if hasattr(self, "_tray"):
            self._tray.update_click_through_state(enabled)

    # ─────────────────────────────────────────────────────
    # 📏 极简窄条 / 状态栏模式 (Mini Bar Mode)
    # ─────────────────────────────────────────────────────

    def _toggle_minibar(self):
        """F2 快捷键入口：切换屏幕边缘极简磁吸条形态"""
        self._toolbar._on_minibar_clicked()

    def toggle_minibar_mode(self, enabled: bool):
        """对外暴露的 Mini Ticker 极简磁吸条模式切换入口"""
        self._on_minibar_toggled(enabled)

    def _on_minibar_toggled(self, enabled: bool):
        """切换极简窄条模式"""
        self._is_minibar = enabled

        if enabled:
            # ― 1. 快照当前大卡片尺寸 ―
            self._normal_size = self.size()
            self._state.set("minibar_normal_width",  self.width())
            self._state.set("minibar_normal_height", self.height())

            # ― 2. 严格隐藏大卡片模式下的所有 UI 控件，彻底清除错位与粉框残留 ―
            self._toolbar.hide()
            self._card.hide()
            self._nav_bar.hide()
            self._review_badge.hide()
            self._bottom_bar_widget.hide()
            self._today_badge.hide()
            self._size_grip.hide()

            # ― 3. 展示 Mini Bar 并刷新内容 ―
            self._minibar_widget.show()
            self._update_minibar_text()

            # ― 4. 尺寸严格收缩为超薄单行窄条，宽度保持、高度固定为 40px ―
            current_w = max(self.width(), WINDOW_MIN_WIDTH)
            self.setMinimumSize(WINDOW_MIN_WIDTH, self._minibar_height)
            self.setMaximumSize(16777215, self._minibar_height)
            self.resize(current_w, self._minibar_height)

        else:
            # ― 1. 隐藏 Mini Bar ―
            self._minibar_widget.hide()

            # ― 2. 解除窗口最大高度限制，恢复正常窗口最小尺寸 ―
            self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
            self.setMaximumSize(16777215, 16777215)

            # ― 3. 恢复大卡片模式下的所有 UI 控件显示 ―
            self._toolbar.show()
            self._card.show()
            self._nav_bar.setVisible(not self._compact)
            self._review_badge.setVisible(self._review_mode)
            self._bottom_bar_widget.show()
            self._today_badge.show()
            self._size_grip.show()

            # ― 4. 还原为大卡片原始尺寸 ―
            if self._normal_size and self._normal_size.height() >= WINDOW_MIN_HEIGHT:
                target_w = max(self._normal_size.width(), WINDOW_MIN_WIDTH)
                target_h = max(self._normal_size.height(), WINDOW_MIN_HEIGHT)
                self.resize(target_w, target_h)
            else:
                saved_w = self._state.get_int("minibar_normal_width",  WINDOW_DEFAULT_WIDTH)
                saved_h = self._state.get_int("minibar_normal_height", WINDOW_DEFAULT_HEIGHT)
                self.resize(max(saved_w, WINDOW_MIN_WIDTH), max(saved_h, WINDOW_MIN_HEIGHT))

        # 同步更新工具栏与托盘状态
        self._toolbar.set_minibar_state(enabled)
        if hasattr(self, "_tray"):
            self._tray.update_minibar_state(enabled)
        self._state.set("minibar_mode", "1" if enabled else "0")
        self.update()

    def _update_minibar_text(self):
        """刷新 Mini Bar 单行显示内容：韩文 [发音] - 释义"""
        word = self._vocab.current_word()
        if not word:
            self._minibar_label.setText("🇰🇷 未来的韩语卡片（无当前单词）")
            return
        korean   = word.get("korean", "")
        pron     = word.get("pronunciation", "")
        meaning  = word.get("meaning", "")
        text = korean
        if pron:
            text += f"  [{pron}]"
        if meaning:
            text += f"  —  {meaning}"
        self._minibar_label.setText(text)

    # ─────────────────────────────────────────────────────────
    # 窗口绘制（RGBA 独立背景着色，文字 100% 实心高清）
    # ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        rect_f = QRectF(self.rect().adjusted(1, 1, -1, -1))
        path.addRoundedRect(rect_f, WINDOW_BORDER_RADIUS, WINDOW_BORDER_RADIUS)

        # 关键修复：当 bg_opacity 为 0% 时，依然以 alpha=1 绘制极微底色，防止 Windows DWM 将其当成穿透孔洞丢弃鼠标点击与翻转
        bg_alpha = max(1, int(self._bg_opacity * 255))
        border_alpha = int(min(self._bg_opacity * 1.25, 1.0) * 255) if self._bg_opacity > 0.02 else 0

        bg_col = QColor(self._bg_color)
        bg_col.setAlpha(bg_alpha)
        painter.fillPath(path, QBrush(bg_col))

        if border_alpha > 0:
            border_col = QColor(self._border_color)
            border_col.setAlpha(border_alpha)
            painter.strokePath(path, QPen(border_col, 1.5))

    # ─────────────────────────────────────────────────────────
    # 窗口移动与边缘缩放
    # ─────────────────────────────────────────────────────────

    def _get_resize_direction(self, pos: QPoint) -> str:
        """根据鼠标位置返回缩放方向代码"""
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        m = RESIZE_MARGIN

        on_left = x <= m
        on_right = x >= w - m
        on_top = y <= m
        on_bottom = y >= h - m

        if on_right and on_bottom:  return "se"
        if on_left  and on_bottom:  return "sw"
        if on_right and on_top:     return "ne"
        if on_left  and on_top:     return "nw"
        if on_right:                return "e"
        if on_bottom:               return "s"
        if on_left:                 return "w"
        if on_top:                  return "n"
        return ""

    _CURSOR_MAP = {
        "e":  Qt.CursorShape.SizeHorCursor,
        "w":  Qt.CursorShape.SizeHorCursor,
        "s":  Qt.CursorShape.SizeVerCursor,
        "n":  Qt.CursorShape.SizeVerCursor,
        "se": Qt.CursorShape.SizeFDiagCursor,
        "nw": Qt.CursorShape.SizeFDiagCursor,
        "sw": Qt.CursorShape.SizeBDiagCursor,
        "ne": Qt.CursorShape.SizeBDiagCursor,
    }

    # ─────────────────────────────────────────────────────────
    # 鼠标事件（拖拽移动 + 边缘缩放）
    # ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            local_pos = event.position().toPoint()
            self._resize_dir = self._get_resize_direction(local_pos)

            if self._resize_dir:
                # 缩放模式
                self._resize_start_geom   = self.geometry()
                self._resize_start_cursor = event.globalPosition().toPoint()
            elif self._toolbar.geometry().contains(local_pos) or (self._is_minibar and self._minibar_widget.geometry().contains(local_pos)):
                # 工具栏或 Mini Bar 拖拽移动模式
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            else:
                self._drag_pos = QPoint()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        local_pos = event.position().toPoint()

        if event.buttons() == Qt.MouseButton.LeftButton:
            if self._resize_dir:
                # ── 执行缩放 ──
                delta   = event.globalPosition().toPoint() - self._resize_start_cursor
                geom    = QRect(self._resize_start_geom)
                dx, dy  = delta.x(), delta.y()
                d       = self._resize_dir

                new_x = geom.x()
                new_y = geom.y()
                new_w = geom.width()
                new_h = geom.height()

                if self._is_minibar:
                    new_h = self._minibar_height
                    if "e" in d:  new_w = max(geom.width()  + dx, WINDOW_MIN_WIDTH)
                    if "w" in d:
                        new_w = max(geom.width() - dx, WINDOW_MIN_WIDTH)
                        new_x = geom.right() - new_w
                else:
                    if "e" in d:  new_w = max(geom.width()  + dx, WINDOW_MIN_WIDTH)
                    if "s" in d:  new_h = max(geom.height() + dy, WINDOW_MIN_HEIGHT)
                    if "w" in d:
                        new_w = max(geom.width() - dx, WINDOW_MIN_WIDTH)
                        new_x = geom.right() - new_w
                    if "n" in d:
                        new_h = max(geom.height() - dy, WINDOW_MIN_HEIGHT)
                        new_y = geom.bottom() - new_h

                self.setGeometry(new_x, new_y, new_w, new_h)

            elif not self._drag_pos.isNull():
                # ── 执行拖拽移动 ──
                self.move(event.globalPosition().toPoint() - self._drag_pos)
        else:
            # 悬停时更新光标形状
            d = self._get_resize_direction(local_pos)
            if d:
                self.setCursor(QCursor(self._CURSOR_MAP[d]))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        """双击 Mini Ticker 微型条快速恢复为主大卡片形态"""
        if self._is_minibar:
            self.toggle_minibar_mode(False)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos    = QPoint()
        self._resize_dir  = ""
        # 释放后重置光标
        local_pos = event.position().toPoint()
        d = self._get_resize_direction(local_pos)
        self.setCursor(QCursor(self._CURSOR_MAP.get(d, Qt.CursorShape.ArrowCursor)))
        # 屏幕边缘极简磁吸吸附
        self._snap_to_screen_edges()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        """鼠标移入卡片：若开启了自动轮播则暂停倒计时 (Hover to Pause)"""
        if self._autoplay_interval > 0 and self._autoplay_timer.isActive():
            self._autoplay_timer.stop()
            self._autoplay_paused_by_hover = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标移出卡片：恢复自动轮播计时"""
        if getattr(self, "_autoplay_paused_by_hover", False) and self._autoplay_interval > 0:
            self._autoplay_timer.start(self._autoplay_interval * 1000)
            self._autoplay_paused_by_hover = False
        super().leaveEvent(event)

    def _snap_to_screen_edges(self):
        """屏幕边缘极简磁吸算法：当拖动靠近屏幕边缘 20px 内时自动平滑吸附"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        cur = self.geometry()
        new_x = cur.x()
        new_y = cur.y()
        snap_dist = 25

        # 顶部磁吸
        if abs(cur.top() - geo.top()) <= snap_dist:
            new_y = geo.top()
        # 底部磁吸
        elif abs(cur.bottom() - geo.bottom()) <= snap_dist:
            new_y = geo.bottom() - cur.height() + 1

        # 左侧磁吸
        if abs(cur.left() - geo.left()) <= snap_dist:
            new_x = geo.left()
        # 右侧磁吸
        elif abs(cur.right() - geo.right()) <= snap_dist:
            new_x = geo.right() - cur.width() + 1

        if new_x != cur.x() or new_y != cur.y():
            self.move(new_x, new_y)

    def _on_korean_captured(self, korean: str, info: dict):
        """剪贴板划词捕获回调：展示 Instagram 风格悬浮微气泡"""
        if self.isVisible() and hasattr(self, "_clip_toast"):
            self._clip_toast.show_clip(korean, info, anchor_window=self)

    def _on_clip_word_add(self, korean: str, meaning: str, pron: str):
        """一键收录外部生词回调"""
        self._clip_listener.add_to_custom_vocab(korean, meaning, pron)
        ToastWidget.show_toast(
            self,
            f"🎉 <b>已成功收入自定义生词本！</b><br><span style='color: #38BDF8;'>{html.escape(korean)}</span>",
            icon="📥",
            duration_ms=2500
        )
        if self._current_book == -2:
            self._on_book_changed(-2)

    # ─────────────────────────────────────────────────────────
    # 隐藏/显示（Ctrl+H 与 托盘联动）
    # ─────────────────────────────────────────────────────────

    def _on_tray_toggle_window(self):
        """托盘单击/双击：若处于鼠标穿透状态，强力解除穿透并置顶唤起；否则切换显示/隐藏"""
        if self._is_click_through:
            self._on_click_through_toggled(False)
            self._toolbar.set_click_through_state(False)
            if hasattr(self, "_tray"):
                self._tray.update_click_through_state(False)
                self._tray.show_message("韩语悬浮卡片", "已解除鼠标穿透模式，恢复正常交互")
            self.show()
            self.activateWindow()
            self.raise_()
            return

        self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
            if hasattr(self, "_tray"):
                self._tray.update_action_text(False)
        else:
            self.show()
            self.activateWindow()
            self.raise_()
            if hasattr(self, "_tray"):
                self._tray.update_action_text(True)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_tray"):
            self._tray.update_action_text(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "_tray"):
            self._tray.update_action_text(False)

    # ─────────────────────────────────────────────────────────
    # 关闭与退出策略（支持托盘驻留拦截）
    # ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        # 1. 强制退出标志触发（如托盘菜单退出项或更多菜单退出项）
        if getattr(self, "_is_force_exit", False):
            self._exit_app_completely()
            event.accept()
            return

        # 2. 动态读取当前配置中的 minimize_to_tray 偏好
        minimize_to_tray = self._state.get_bool("minimize_to_tray", True)
        if minimize_to_tray:
            # 必须第一时间瞬间隐藏窗口（0ms 视觉秒关）
            self.hide()
            if hasattr(self, "_tray"):
                self._tray.update_action_text(False)
            try:
                self._save_current_state()
            except Exception:
                pass
            event.ignore()
        else:
            self._exit_app_completely()
            event.accept()

    def _exit_app_completely(self):
        """从托盘菜单或明确退出指令彻底退出程序（0ms 瞬时秒关）"""
        self._is_force_exit = True
        # 1. 第一时间立即完全隐藏窗口与托盘，给用户 0ms 的纯粹秒关体验
        self.hide()
        if hasattr(self, "_tray"):
            self._tray.hide()
        if hasattr(self, "_clip_toast"):
            self._clip_toast.hide()

        # 2. 毫秒级单事务持久化当前断点进度
        try:
            self._save_current_state()
        except Exception:
            pass

        # 3. 停止简单计时器
        try:
            self._autoplay_timer.stop()
            if hasattr(self, "_seen_timer"):
                self._seen_timer.stop()
            if hasattr(self, "_boss_key"):
                self._boss_key.stop()
        except Exception:
            pass

        # 4. 强制瞬时终止进程，杜绝任何外部音频驱动与网络线程挂起等待
        import os
        os._exit(0)

    def eventFilter(self, obj, event):
        """事件过滤器：支持点击左下角今日已学徽章打开打卡看板"""
        if obj == getattr(self, "_today_badge", None):
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._open_stats_dialog()
                return True
        return super().eventFilter(obj, event)
