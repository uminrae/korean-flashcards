# ui/toolbar_widget.py
# -*- coding: utf-8 -*-
"""
顶部工具栏：Instagram / iOS 极简风格重构
功能：
- 顶部标题栏仅保留优雅标题 + Instagram 风格「⋯」更多操作按钮 + 极简「✕」关闭按钮
- 点击「⋯」弹出结构清晰、毛玻璃半透质感的全功能菜单（学习与播放、视图与外观、系统）
- 下方保留精美扁平胶囊的三级联动下拉（册/单元/课）与轻量透明度滑块
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QPushButton,
    QLabel, QSlider, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QCursor
from typing import List, Tuple

from config.settings import COLORS


class ToolbarWidget(QWidget):
    """Instagram 风格极简工具栏组件"""

    book_changed = pyqtSignal(int)
    unit_changed = pyqtSignal(int)
    lesson_changed = pyqtSignal(int)
    shuffle_toggled = pyqtSignal(bool)              # 随机乱序开关
    autoplay_interval_changed = pyqtSignal(int)     # 自动轮播间隔（秒，0=关闭）
    autospeak_toggled = pyqtSignal(bool)            # 自动朗读开关
    audio_first_toggled = pyqtSignal(bool)          # 盲听磨耳朵模式开关
    spelling_toggled = pyqtSignal(bool)             # 拼写练习测验模式开关
    compact_toggled = pyqtSignal(bool)              # True=极简
    theme_toggled = pyqtSignal(str)                 # "dark" / "light"
    click_through_toggled = pyqtSignal(bool)        # 鼠标穿透/锁定模式
    minibar_toggled = pyqtSignal(bool)              # 极简窄条模式
    vocab_book_clicked = pyqtSignal()               # 查看生词本
    export_copybook_clicked = pyqtSignal()          # 🖨 导出当前生词本字帖 (PDF/PNG)
    stats_clicked = pyqtSignal()                    # 📊 学习足迹与打卡看板
    pomodoro_clicked = pyqtSignal()                 # 🎧 专注伴学与番茄钟
    translate_clicked = pyqtSignal()                # 🔍 极简中韩翻译抽屉
    settings_clicked = pyqtSignal()                 # 设置与词库导入
    opacity_changed = pyqtSignal(float)             # 背景透明度
    close_clicked = pyqtSignal()                    # 关闭
    exit_clicked = pyqtSignal()                     # 彻底退出程序
    speak_current_requested = pyqtSignal()          # 朗读当前发音
    start_weighted_review_requested = pyqtSignal(int) # 🎯 触发加权智能复习 (词数)

    AUTOPLAY_INTERVALS = [0, 5, 10, 15]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = "dark"
        self._compact = False
        self._is_shuffle = False
        self._is_audio_first = False
        self._is_spelling = False
        self._autoplay_idx = 0      # 0=关, 1=5s, 2=10s, 3=15s
        self._auto_speak = True
        self._is_click_through = False
        self._is_minibar = False

        self._setup_ui()
        self._build_more_menu()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 4)
        layout.setSpacing(6)

        # ── 第一行：极简标题 + 「⋯」更多按钮 + 「✕」关闭按钮 ──
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        # 应用标题（优雅极简排版）
        self._title_label = QLabel("未来的韩语卡片")
        self._title_label.setObjectName("toolbar_title")
        self._title_label.setStyleSheet(
            "font-size: 13px; font-weight: 700; letter-spacing: 0.6px;"
        )
        header_row.addWidget(self._title_label)
        header_row.addStretch()

        # 极简「🔍」中韩翻译抽屉快捷入口
        self._trans_btn = QPushButton("🔍")
        self._trans_btn.setObjectName("trans_btn")
        self._trans_btn.setFixedSize(28, 28)
        self._trans_btn.setToolTip("极简中韩智能翻译抽屉 (Ctrl+T)")
        self._trans_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._trans_btn.clicked.connect(self.translate_clicked.emit)
        header_row.addWidget(self._trans_btn)

        # Instagram 风格「⋯」更多操作按钮
        self._more_btn = QPushButton("⋯")
        self._more_btn.setObjectName("more_btn")
        self._more_btn.setFixedSize(28, 28)
        self._more_btn.setToolTip("更多功能与模式设置 (Instagram 风格菜单)")
        self._more_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._more_btn.clicked.connect(self._show_more_menu)
        header_row.addWidget(self._more_btn)

        # 极简「✕」关闭按钮
        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("close_btn")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setToolTip("关闭窗口 (Ctrl+H / 托盘驻留)")
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.clicked.connect(self.close_clicked.emit)
        header_row.addWidget(self._close_btn)

        layout.addLayout(header_row)

        # ── 第二行：三级联动筛选（扁平胶囊样式）──
        self._filter_row = QWidget()
        self._filter_row.setObjectName("filter_row")
        row2 = QHBoxLayout(self._filter_row)
        row2.setContentsMargins(0, 2, 0, 2)
        row2.setSpacing(6)

        # 1. 册数
        self._book_combo = QComboBox()
        self._book_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._book_combo.setMinimumWidth(95)
        self._book_combo.setToolTip("选择教材册数")
        self._book_combo.currentIndexChanged.connect(self._on_book_changed)
        row2.addWidget(self._book_combo, stretch=3)

        # 2. 单元
        self._unit_combo = QComboBox()
        self._unit_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._unit_combo.setMinimumWidth(115)
        self._unit_combo.setToolTip("选择所属单元")
        self._unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        row2.addWidget(self._unit_combo, stretch=4)

        # 3. 课程
        self._lesson_combo = QComboBox()
        self._lesson_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._lesson_combo.setMinimumWidth(90)
        self._lesson_combo.setToolTip("选择具体课程")
        self._lesson_combo.currentIndexChanged.connect(self._on_lesson_changed)
        row2.addWidget(self._lesson_combo, stretch=3)

        layout.addWidget(self._filter_row)

        # ── 第三行：透明度滑条 ──
        self._opacity_row = QWidget()
        self._opacity_row.setObjectName("opacity_row")
        row3 = QHBoxLayout(self._opacity_row)
        row3.setContentsMargins(0, 0, 0, 0)
        row3.setSpacing(6)

        opacity_icon = QLabel("透明度")
        opacity_icon.setObjectName("opacity_title_lbl")
        opacity_icon.setStyleSheet("color: #64748B; font-size: 11px;")
        row3.addWidget(opacity_icon)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(92)
        self._opacity_slider.setToolTip("卡片背景透明度 (拉到 0% 为 HUD 纯文字悬浮桌面，字体始终 100% 高清实心)")
        self._opacity_slider.valueChanged.connect(
            lambda v: self.opacity_changed.emit(v / 100.0)
        )
        row3.addWidget(self._opacity_slider)

        self._opacity_label = QLabel("92%")
        self._opacity_label.setFixedWidth(34)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        row3.addWidget(self._opacity_label)

        layout.addWidget(self._opacity_row)

    # ─────────────────────────────────────────────────────────
    # Instagram 风格「⋯」弹出菜单构建
    # ─────────────────────────────────────────────────────────

    def _build_more_menu(self):
        """构建 Instagram 风格结构清晰、纯排版无 Emoji 的 QMenu"""
        self._menu = QMenu(self)
        self._menu.setObjectName("insta_more_menu")
        self._menu.setStyleSheet("""
            QMenu {
                background: rgba(22, 24, 30, 0.98);
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
            }
            QMenu::section {
                color: #64748B;
                font-size: 11px;
                font-weight: 700;
                padding: 8px 12px 4px 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
                margin-bottom: 4px;
                letter-spacing: 0.8px;
            }
            QMenu::item {
                background: transparent;
                color: #E2E8F0;
                padding: 7px 22px 7px 12px;
                border-radius: 6px;
                margin: 1px 2px;
            }
            QMenu::item:selected {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
            }
            QMenu::item:disabled {
                color: #64748B;
                background: transparent;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.06);
                margin: 4px 8px;
            }
        """)

        # ── 1. 学习与播放 ──
        self._menu.addSection("学习与播放")

        # 随机乱序
        self._action_shuffle = QAction("随机乱序模式\tCtrl+R", self)
        self._action_shuffle.setCheckable(True)
        self._action_shuffle.setChecked(self._is_shuffle)
        self._action_shuffle.triggered.connect(self._on_menu_shuffle_triggered)
        self._menu.addAction(self._action_shuffle)

        # 自动轮播子菜单
        self._autoplay_submenu = self._menu.addMenu("定时自动轮播伴学")
        self._autoplay_actions = []
        for sec in self.AUTOPLAY_INTERVALS:
            label = "关闭轮播" if sec == 0 else f"{sec} 秒 / 词"
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(sec == 0)
            act.setData(sec)
            act.triggered.connect(lambda checked, s=sec: self._on_menu_autoplay_selected(s))
            self._autoplay_submenu.addAction(act)
            self._autoplay_actions.append(act)

        # 自动发音
        self._action_autospeak = QAction("轮播时自动发音", self)
        self._action_autospeak.setCheckable(True)
        self._action_autospeak.setChecked(self._auto_speak)
        self._action_autospeak.triggered.connect(self._on_menu_autospeak_triggered)
        self._menu.addAction(self._action_autospeak)

        # 盲听磨耳朵模式
        self._action_audio_first = QAction("纯听力磨耳朵模式", self)
        self._action_audio_first.setCheckable(True)
        self._action_audio_first.setChecked(self._is_audio_first)
        self._action_audio_first.triggered.connect(self._on_menu_audio_first_triggered)
        self._menu.addAction(self._action_audio_first)

        # 键盘韩打拼写测验
        self._action_spelling = QAction("键盘韩打拼写练习\tT", self)
        self._action_spelling.setCheckable(True)
        self._action_spelling.setChecked(self._is_spelling)
        self._action_spelling.triggered.connect(self._on_menu_spelling_triggered)
        self._menu.addAction(self._action_spelling)

        # 科学加权智能复习
        self._review_submenu = self._menu.addMenu("开始加权智能复习")
        for count in [10, 20, 30, 50]:
            act = QAction(f"复习 {count} 词 (加权突击)", self)
            act.triggered.connect(lambda checked, c=count: self.start_weighted_review_requested.emit(c))
            self._review_submenu.addAction(act)

        # 朗读发音
        self._action_speak_now = QAction("朗读当前单词发音\tCtrl+P", self)
        self._action_speak_now.triggered.connect(self.speak_current_requested.emit)
        self._menu.addAction(self._action_speak_now)

        # 专注伴学与番茄时钟
        self._action_pomodoro = QAction("专注伴学与番茄钟\tCtrl+Shift+T", self)
        self._action_pomodoro.triggered.connect(self.pomodoro_clicked.emit)
        self._menu.addAction(self._action_pomodoro)

        self._menu.addSeparator()

        # ── 2. 视图与模式 ──
        self._menu.addSection("视图与模式")

        # 屏幕边缘极简磁吸条
        self._action_minibar = QAction("屏幕边缘极简磁吸条\tF2", self)
        self._action_minibar.setCheckable(True)
        self._action_minibar.setChecked(self._is_minibar)
        self._action_minibar.triggered.connect(self._on_menu_minibar_triggered)
        self._menu.addAction(self._action_minibar)

        # 生词本
        self._action_vocab = QAction("我的生词本\tCtrl+S", self)
        self._action_vocab.triggered.connect(self.vocab_book_clicked.emit)
        self._menu.addAction(self._action_vocab)

        # 导出生词本手写字帖
        self._action_export_copybook = QAction("导出当前生词本字帖", self)
        self._action_export_copybook.triggered.connect(self.export_copybook_clicked.emit)
        self._menu.addAction(self._action_export_copybook)

        # 学习足迹与打卡看板
        self._action_stats = QAction("学习足迹与打卡看板\tCtrl+I", self)
        self._action_stats.triggered.connect(self.stats_clicked.emit)
        self._menu.addAction(self._action_stats)

        # 主题切换
        self._action_theme = QAction("切换深色 / 浅色主题", self)
        self._action_theme.triggered.connect(self._toggle_theme)
        self._menu.addAction(self._action_theme)

        # 鼠标穿透
        self._action_click_through = QAction("鼠标穿透锁定模式\tCtrl+L", self)
        self._action_click_through.setCheckable(True)
        self._action_click_through.setChecked(self._is_click_through)
        self._action_click_through.triggered.connect(self._on_menu_click_through_triggered)
        self._menu.addAction(self._action_click_through)

        # 极简模式（收起筛选栏）
        self._action_compact = QAction("极简收起筛选栏\tCtrl+M", self)
        self._action_compact.setCheckable(True)
        self._action_compact.setChecked(self._compact)
        self._action_compact.triggered.connect(self._toggle_compact)
        self._menu.addAction(self._action_compact)

        self._menu.addSeparator()

        # ── 3. 系统 ──
        self._menu.addSection("系统")

        self._action_settings = QAction("偏好设置与词库管理\tCtrl+,", self)
        self._action_settings.triggered.connect(self.settings_clicked.emit)
        self._menu.addAction(self._action_settings)

        self._action_exit = QAction("退出程序", self)
        self._action_exit.triggered.connect(self.exit_clicked.emit)
        self._menu.addAction(self._action_exit)

    def _show_more_menu(self):
        """在「⋯」按钮下方弹出菜单"""
        btn_pos = self._more_btn.mapToGlobal(QPoint(0, self._more_btn.height() + 4))
        self._menu.exec(btn_pos)

    # ─────────────────────────────────────────────────────────
    # 菜单事件与快捷键联动
    # ─────────────────────────────────────────────────────────

    def _on_shuffle_clicked(self):
        self._is_shuffle = not self._is_shuffle
        self.set_shuffle_state(self._is_shuffle)
        self.shuffle_toggled.emit(self._is_shuffle)

    def _on_autoplay_clicked(self):
        self._autoplay_idx = (self._autoplay_idx + 1) % len(self.AUTOPLAY_INTERVALS)
        seconds = self.AUTOPLAY_INTERVALS[self._autoplay_idx]
        self.set_autoplay_interval(seconds)
        self.autoplay_interval_changed.emit(seconds)

    def _on_autospeak_clicked(self):
        self._auto_speak = not self._auto_speak
        self.set_autospeak_state(self._auto_speak)
        self.autospeak_toggled.emit(self._auto_speak)

    def _on_audio_first_clicked(self):
        self._is_audio_first = not self._is_audio_first
        self.set_audio_first_state(self._is_audio_first)
        self.audio_first_toggled.emit(self._is_audio_first)

    def _on_spelling_clicked(self):
        self._is_spelling = not self._is_spelling
        self.set_spelling_state(self._is_spelling)
        self.spelling_toggled.emit(self._is_spelling)

    def _on_minibar_clicked(self):
        self._is_minibar = not self._is_minibar
        self.set_minibar_state(self._is_minibar)
        self.minibar_toggled.emit(self._is_minibar)

    def _on_click_through_clicked(self):
        self._is_click_through = not self._is_click_through
        self.set_click_through_state(self._is_click_through)
        self.click_through_toggled.emit(self._is_click_through)

    def _on_menu_shuffle_triggered(self, checked: bool):
        self._is_shuffle = checked
        self.set_shuffle_state(checked)
        self.shuffle_toggled.emit(checked)

    def _on_menu_autoplay_selected(self, seconds: int):
        self.set_autoplay_interval(seconds)
        self.autoplay_interval_changed.emit(seconds)

    def _on_menu_autospeak_triggered(self, checked: bool):
        self._auto_speak = checked
        self.set_autospeak_state(checked)
        self.autospeak_toggled.emit(checked)

    def _on_menu_audio_first_triggered(self, checked: bool):
        self._is_audio_first = checked
        self.set_audio_first_state(checked)
        self.audio_first_toggled.emit(checked)

    def _on_menu_spelling_triggered(self, checked: bool):
        self._is_spelling = checked
        self.set_spelling_state(checked)
        self.spelling_toggled.emit(checked)

    def _on_menu_minibar_triggered(self, checked: bool):
        self._is_minibar = checked
        self.set_minibar_state(checked)
        self.minibar_toggled.emit(checked)

    def _on_menu_click_through_triggered(self, checked: bool):
        self._is_click_through = checked
        self.set_click_through_state(checked)
        self.click_through_toggled.emit(checked)

    # ─────────────────────────────────────────────────────────
    # 下拉更新与状态同步
    # ─────────────────────────────────────────────────────────

    def populate_books(self, books: List[Tuple[int, str]]):
        self._book_combo.blockSignals(True)
        self._book_combo.clear()
        for num, name in books:
            self._book_combo.addItem(name, userData=num)
        self._book_combo.blockSignals(False)

    def populate_units(self, units: List[Tuple[int, str]]):
        self._unit_combo.blockSignals(True)
        self._unit_combo.clear()
        for num, name in units:
            self._unit_combo.addItem(name, userData=num)
        self._unit_combo.blockSignals(False)

    def populate_lessons(self, lessons: List[Tuple[int, str]]):
        self._lesson_combo.blockSignals(True)
        self._lesson_combo.clear()
        for num, name in lessons:
            self._lesson_combo.addItem(name, userData=num)
        self._lesson_combo.blockSignals(False)

    def set_book_index(self, book_num: int):
        self._book_combo.blockSignals(True)
        for i in range(self._book_combo.count()):
            if self._book_combo.itemData(i) == book_num:
                self._book_combo.setCurrentIndex(i)
                break
        self._book_combo.blockSignals(False)

    def set_unit_index(self, unit_num: int):
        self._unit_combo.blockSignals(True)
        for i in range(self._unit_combo.count()):
            if self._unit_combo.itemData(i) == unit_num:
                self._unit_combo.setCurrentIndex(i)
                break
        self._unit_combo.blockSignals(False)

    def set_lesson_index(self, lesson_num: int):
        self._lesson_combo.blockSignals(True)
        for i in range(self._lesson_combo.count()):
            if self._lesson_combo.itemData(i) == lesson_num:
                self._lesson_combo.setCurrentIndex(i)
                break
        self._lesson_combo.blockSignals(False)

    def _on_book_changed(self, idx: int):
        data = self._book_combo.itemData(idx)
        if data is not None:
            self.book_changed.emit(data)

    def _on_unit_changed(self, idx: int):
        data = self._unit_combo.itemData(idx)
        if data is not None:
            self.unit_changed.emit(data)

    def _on_lesson_changed(self, idx: int):
        data = self._lesson_combo.itemData(idx)
        if data is not None:
            self.lesson_changed.emit(data)

    # ─────────────────────────────────────────────────────────
    # 外部状态更新接口（同步菜单项与按钮）
    # ─────────────────────────────────────────────────────────

    def set_shuffle_state(self, enabled: bool):
        self._is_shuffle = enabled
        if hasattr(self, "_action_shuffle"):
            self._action_shuffle.blockSignals(True)
            self._action_shuffle.setChecked(enabled)
            self._action_shuffle.blockSignals(False)

    def set_autoplay_interval(self, seconds: int):
        if seconds in self.AUTOPLAY_INTERVALS:
            self._autoplay_idx = self.AUTOPLAY_INTERVALS.index(seconds)
        else:
            self._autoplay_idx = 0
            seconds = 0

        if hasattr(self, "_autoplay_actions"):
            for act in self._autoplay_actions:
                act.blockSignals(True)
                act.setChecked(act.data() == seconds)
                act.blockSignals(False)

    def set_autospeak_state(self, enabled: bool):
        self._auto_speak = enabled
        if hasattr(self, "_action_autospeak"):
            self._action_autospeak.blockSignals(True)
            self._action_autospeak.setChecked(enabled)
            self._action_autospeak.blockSignals(False)

    def set_audio_first_state(self, enabled: bool):
        self._is_audio_first = enabled
        if hasattr(self, "_action_audio_first"):
            self._action_audio_first.blockSignals(True)
            self._action_audio_first.setChecked(enabled)
            self._action_audio_first.blockSignals(False)

    def set_spelling_state(self, enabled: bool):
        self._is_spelling = enabled
        if hasattr(self, "_action_spelling"):
            self._action_spelling.blockSignals(True)
            self._action_spelling.setChecked(enabled)
            self._action_spelling.blockSignals(False)

    def set_click_through_state(self, enabled: bool):
        self._is_click_through = enabled
        if hasattr(self, "_action_click_through"):
            self._action_click_through.blockSignals(True)
            self._action_click_through.setChecked(enabled)
            self._action_click_through.blockSignals(False)

    def set_minibar_state(self, enabled: bool):
        self._is_minibar = enabled
        if hasattr(self, "_action_minibar"):
            self._action_minibar.blockSignals(True)
            self._action_minibar.setChecked(enabled)
            self._action_minibar.blockSignals(False)

    def _toggle_compact(self):
        self._compact = not self._compact
        self._filter_row.setVisible(not self._compact)
        self._opacity_row.setVisible(not self._compact)
        if hasattr(self, "_action_compact"):
            self._action_compact.blockSignals(True)
            self._action_compact.setChecked(self._compact)
            self._action_compact.blockSignals(False)
        self.compact_toggled.emit(self._compact)

    def _toggle_theme(self):
        self._theme = "light" if self._theme == "dark" else "dark"
        self.theme_toggled.emit(self._theme)

    def set_opacity_value(self, opacity: float):
        self._opacity_slider.blockSignals(True)
        self._opacity_slider.setValue(int(opacity * 100))
        self._opacity_label.setText(f"{int(opacity * 100)}%")
        self._opacity_slider.blockSignals(False)

    # ─────────────────────────────────────────────────────────
    # 主题样式
    # ─────────────────────────────────────────────────────────

    def apply_theme(self, theme: str):
        self._theme = theme
        from config.settings import THEME_CONFIGS, COLORS
        if theme == "dark":
            theme = "seoul_night"
        elif theme == "light":
            theme = "cream_latte"

        cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["seoul_night"])
        is_dark = cfg.get("is_dark", True)
        text = cfg.get("text_primary", "#FFFFFF")
        text_sec = cfg.get("text_secondary", "#94A3B8")
        accent = cfg.get("accent", "#2ECC71")
        card_bg = cfg.get("card_bg", "#161922")
        input_bg = cfg.get("input_bg", "#1F2330")
        border = cfg.get("border", "rgba(255, 255, 255, 0.10)")

        btn_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        btn_hover = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.12)"
        combo_border = border

        self._title_label.setStyleSheet(
            f"QLabel {{ color: {text}; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; }}"
        )

        # 「🔍」翻译按钮与「⋯」更多按钮与「✕」关闭按钮
        self._trans_btn.setStyleSheet(
            f"QPushButton {{ background: {btn_bg}; color: {text}; border: none; "
            f"border-radius: 14px; font-size: 13px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {btn_hover}; }}"
        )
        self._more_btn.setStyleSheet(
            f"QPushButton {{ background: {btn_bg}; color: {text}; border: none; "
            f"border-radius: 14px; font-size: 15px; font-weight: bold; padding-bottom: 2px; }}"
            f"QPushButton:hover {{ background: {btn_hover}; }}"
        )
        self._close_btn.setStyleSheet(
            f"QPushButton {{ background: {btn_bg}; color: {text_sec}; border: none; "
            f"border-radius: 14px; font-size: 12px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: rgba(235, 87, 87, 0.85); color: #FFFFFF; }}"
        )

        # Instagram / iOS 极简 Pill Tag 标签风格下拉选择框
        combo_bg = input_bg if is_dark else "rgba(0, 0, 0, 0.05)"
        combo_popup_bg = card_bg if is_dark else "rgba(255, 255, 255, 0.98)"
        combo_style = (
            f"QComboBox {{ "
            f"  background: {combo_bg}; "
            f"  color: {text}; "
            f"  border: 1px solid {border}; "
            f"  border-radius: 12px; "
            f"  padding: 4px 10px 4px 10px; "
            f"  font-size: 11px; "
            f"  font-weight: 500; "
            f"}} "
            f"QComboBox:hover {{ "
            f"  border: 1px solid {accent}; "
            f"}} "
            f"QComboBox::drop-down {{ "
            f"  border: none; "
            f"  width: 14px; "
            f"  subcontrol-origin: padding; "
            f"  subcontrol-position: top right; "
            f"}} "
            f"QComboBox QAbstractItemView {{ "
            f"  background: {combo_popup_bg}; "
            f"  color: {text}; "
            f"  border: 1px solid {border}; "
            f"  border-radius: 10px; "
            f"  selection-background-color: {accent}44; "
            f"  selection-color: {text}; "
            f"  padding: 4px; "
            f"  outline: none; "
            f"}}"
        )
        for combo in [self._book_combo, self._unit_combo, self._lesson_combo]:
            combo.setStyleSheet(combo_style)

        # 滑块样式
        slider_style = (
            f"QSlider::groove:horizontal {{ background: {combo_border}; height: 4px; border-radius: 2px; }}"
            f"QSlider::handle:horizontal {{ background: {accent}; width: 14px; height: 14px; "
            f"border-radius: 7px; margin: -5px 0; }}"
            f"QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}"
        )
        self._opacity_slider.setStyleSheet(slider_style)
        self._opacity_label.setStyleSheet(f"QLabel {{ color: {text_sec}; font-size: 11px; font-weight: 600; }}")
