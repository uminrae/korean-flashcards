# -*- coding: utf-8 -*-
# ui/settings_dialog.py
"""设置与外部词库导入/导出面板
功能：
1. 卡片 1：键盘与快捷键（极简滑动开关 + 自定义全功能快捷键胶囊按钮）
2. 卡片 2：字体与视觉风格（韩文字体、文字缩放、Instagram 磨砂预设主题）
3. 卡片 3：科学加权复习（单次复习词数 10/20/30/50 选择与轨迹池状态）
4. 卡片 4：词库与数据管理（外部词表批量导入、生词本导出、开机自启、全量数据备份还原）
"""

import os
import csv
from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFileDialog, QFrame, QTextEdit,
    QMessageBox, QCheckBox, QSizePolicy, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase, QKeySequence, QCursor

from config.settings import COLORS, FONT_KOREAN_SIZE, DEFAULT_SHORTCUTS, SHORTCUT_LABELS, THEME_CONFIGS
from core.vocab_importer import import_custom_vocab
from core.autostart import is_autostart_enabled, set_autostart_enabled
from core.backup_manager import export_user_backup, import_user_backup
from core.font_manager import get_available_korean_fonts, import_font_file
from ui.shortcut_dialog import ShortcutDialog


class SettingsDialog(QDialog):
    """设置与外部词库导入/导出弹窗（Instagram 极简卡片化纯文本排版）"""

    font_changed = pyqtSignal(str)              # 字体更改信号 (font_family)
    font_scale_changed = pyqtSignal(float)      # 字号缩放比例更改信号 (1.0, 1.2, 1.4, 1.6)
    theme_changed = pyqtSignal(str)             # 主题风格更改信号
    vocab_imported = pyqtSignal(str)            # 导入成功信号 (book_name)
    shortcuts_toggled = pyqtSignal(bool)        # 快捷键启用状态更改信号
    shortcuts_mapping_changed = pyqtSignal(dict)# 自定义快捷键映射改变信号
    minimize_to_tray_toggled = pyqtSignal(bool) # 最小化到托盘状态信号
    autostart_toggled = pyqtSignal(bool)        # 开机自启状态信号
    backup_restored = pyqtSignal()              # 备份恢复成功信号

    def __init__(
        self,
        current_font: str = "Malgun Gothic",
        current_scale: float = 1.0,
        shortcuts_enabled: bool = False,
        minimize_to_tray: bool = True,
        vocab_manager=None,
        vocab_book=None,
        state_manager=None,
        theme: str = "dark",
        parent=None
    ):
        super().__init__(parent)
        self._current_font = current_font
        self._current_scale = float(current_scale)
        self._shortcuts_enabled = shortcuts_enabled
        self._minimize_to_tray = minimize_to_tray
        self._vocab_manager = vocab_manager
        self._vocab_book = vocab_book
        self._state_manager = state_manager
        self._theme = theme
        self._selected_file_path = ""
        self._custom_shortcuts = self._state_manager.get_shortcuts() if self._state_manager else dict(DEFAULT_SHORTCUTS)
        self._shortcut_edits = {}
        self._clear_btns = []

        self.setWindowTitle("设置与偏好")
        self.resize(520, 760)
        self.setMinimumSize(480, 580)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self._setup_ui()
        self.apply_theme(theme)

    def _create_card(self, title_text: str) -> tuple[QFrame, QVBoxLayout]:
        """创建 Instagram 风格的独立磨砂圆角容器卡片"""
        card = QFrame()
        card.setObjectName("settings_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        header = QLabel(title_text)
        header.setObjectName("card_title")
        card_layout.addWidget(header)

        return card, card_layout

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── 对话框顶部主标题 ──
        top_bar = QHBoxLayout()
        title = QLabel("设置与偏好")
        title.setObjectName("dialog_main_title")
        top_bar.addWidget(title)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        # ── 滚动区域支撑所有设置项 ──
        scroll = QScrollArea(self)
        scroll.setObjectName("settings_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        scroll.viewport().setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setObjectName("settings_scroll_content")
        scroll_content.setAutoFillBackground(False)
        scroll_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(4, 4, 10, 4)
        layout.setSpacing(12)

        # ═════════════════════════════════════════════════════
        # 卡片 1：键盘与快捷键 (Custom Keyboard Shortcuts)
        # ═════════════════════════════════════════════════════
        card_kb, kb_layout = self._create_card("键盘与快捷键")

        self._shortcuts_checkbox = QCheckBox("启用键盘快捷键 (开启后支持 Space/J/K/F2/Ctrl+T 全键盘盲操)")
        self._shortcuts_checkbox.setChecked(self._shortcuts_enabled)
        self._shortcuts_checkbox.toggled.connect(self._on_shortcuts_toggled)
        kb_layout.addWidget(self._shortcuts_checkbox)

        # 胶囊按钮入口
        btn_row = QHBoxLayout()
        self._open_shortcuts_btn = QPushButton("自定义全功能快捷键...")
        self._open_shortcuts_btn.setObjectName("capsule_btn")
        self._open_shortcuts_btn.setFixedHeight(34)
        self._open_shortcuts_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._open_shortcuts_btn.clicked.connect(self._open_shortcut_dialog)
        btn_row.addWidget(self._open_shortcuts_btn)
        kb_layout.addLayout(btn_row)

        kb_hint = QLabel("提示：支持为翻转、认识/不熟、原声朗读、收藏生词、Mini Ticker 磁吸条、多引擎翻译等 15 项功能独立录制单键或组合键。")
        kb_hint.setObjectName("card_hint")
        kb_hint.setWordWrap(True)
        kb_layout.addWidget(kb_hint)

        layout.addWidget(card_kb)

        # ═════════════════════════════════════════════════════
        # 卡片 2：字体与视觉风格 (Font & Appearance)
        # ═════════════════════════════════════════════════════
        card_font, font_layout = self._create_card("字体与视觉风格")

        # 韩文字体选择行
        font_row = QHBoxLayout()
        font_label = QLabel("韩文字体:")
        font_label.setFixedWidth(70)
        font_label.setObjectName("field_label")
        font_row.addWidget(font_label)

        self._font_combo = QComboBox()
        self._font_combo.setFixedHeight(30)
        self._font_list = get_available_korean_fonts()

        selected_idx = 0
        for idx, (d_name, fam) in enumerate(self._font_list):
            self._font_combo.addItem(d_name, userData=fam)
            if fam.lower() == self._current_font.lower():
                selected_idx = idx

        self._font_combo.setCurrentIndex(selected_idx)
        self._font_combo.currentIndexChanged.connect(self._on_font_changed)
        font_row.addWidget(self._font_combo, stretch=1)

        self._import_font_btn = QPushButton("导入外部字体")
        self._import_font_btn.setFixedHeight(30)
        self._import_font_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._import_font_btn.setToolTip("选择并导入本地 .ttf / .otf 字体文件")
        self._import_font_btn.clicked.connect(self._on_import_font_clicked)
        font_row.addWidget(self._import_font_btn)

        font_layout.addLayout(font_row)

        # 卡片文字大小缩放选择行
        scale_row = QHBoxLayout()
        scale_label = QLabel("文字大小:")
        scale_label.setFixedWidth(70)
        scale_label.setObjectName("field_label")
        scale_row.addWidget(scale_label)

        self._scale_combo = QComboBox()
        self._scale_combo.setFixedHeight(30)
        self._scale_options = [
            ("标准 (100%)", 1.0),
            ("中等放大 (120%)", 1.2),
            ("超大字号 (140%)", 1.4),
            ("巨型特大 (160%)", 1.6),
        ]
        selected_scale_idx = 0
        for idx, (label_text, scale_val) in enumerate(self._scale_options):
            self._scale_combo.addItem(label_text, userData=scale_val)
            if abs(scale_val - self._current_scale) < 0.05:
                selected_scale_idx = idx

        self._scale_combo.setCurrentIndex(selected_scale_idx)
        self._scale_combo.currentIndexChanged.connect(self._on_scale_changed)
        scale_row.addWidget(self._scale_combo, stretch=1)
        font_layout.addLayout(scale_row)

        # 主题风格预设行
        theme_row = QHBoxLayout()
        theme_label = QLabel("主题风格:")
        theme_label.setFixedWidth(70)
        theme_label.setObjectName("field_label")
        theme_row.addWidget(theme_label)

        self._theme_combo = QComboBox()
        self._theme_combo.setFixedHeight(30)
        self._theme_options = [
            ("首尔夜色 (深黑磨砂)", "seoul_night"),
            ("奶油拿铁 (极简米白)", "cream_latte"),
            ("抹茶薄荷 (墨绿翠光)", "matcha_mint"),
            ("暗夜紫罗兰 (暗熏紫粉)", "night_violet"),
        ]
        cur_theme = getattr(self, "_theme", "seoul_night")
        if cur_theme == "dark":
            cur_theme = "seoul_night"
        elif cur_theme == "light":
            cur_theme = "cream_latte"

        selected_theme_idx = 0
        for idx, (t_text, t_id) in enumerate(self._theme_options):
            self._theme_combo.addItem(t_text, userData=t_id)
            if t_id == cur_theme:
                selected_theme_idx = idx

        self._theme_combo.setCurrentIndex(selected_theme_idx)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        theme_row.addWidget(self._theme_combo, stretch=1)
        font_layout.addLayout(theme_row)

        # 实时预览区域
        self._preview_label = QLabel("안녕하세요! 한국어 학습 [汉字: 学校]")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setFixedHeight(46)
        self._preview_label.setObjectName("preview_box")
        self._update_preview()
        font_layout.addWidget(self._preview_label)

        layout.addWidget(card_font)

        # ═════════════════════════════════════════════════════
        # 卡片 3：科学加权复习 (Weighted Review Settings)
        # ═════════════════════════════════════════════════════
        card_review, review_layout = self._create_card("科学加权复习")

        # 单次复习词数
        batch_row = QHBoxLayout()
        batch_label = QLabel("单次复习词数:")
        batch_label.setFixedWidth(90)
        batch_label.setObjectName("field_label")
        batch_row.addWidget(batch_label)

        self._batch_combo = QComboBox()
        self._batch_combo.setFixedHeight(30)
        batch_options = [10, 20, 30, 50]
        cur_batch = self._state_manager.get_review_batch_size() if self._state_manager else 20
        cur_batch_idx = 1
        for idx, num in enumerate(batch_options):
            self._batch_combo.addItem(f"{num} 词 / 轮", userData=num)
            if num == cur_batch:
                cur_batch_idx = idx
        self._batch_combo.setCurrentIndex(cur_batch_idx)
        self._batch_combo.currentIndexChanged.connect(self._on_review_batch_changed)
        batch_row.addWidget(self._batch_combo, stretch=1)
        review_layout.addLayout(batch_row)

        # 统计数据标签
        stats = self._state_manager.get_study_status_counts() if self._state_manager else {"total_studied": 0, "unfamiliar": 0, "mastered": 0}
        stats_info = (
            f"学习轨迹池: 已学 {stats.get('total_studied', 0)} 词 "
            f"(不熟突击 {stats.get('unfamiliar', 0)} | 已掌握 {stats.get('mastered', 0)})"
        )
        self._study_stats_lbl = QLabel(stats_info)
        self._study_stats_lbl.setObjectName("stats_label")
        review_layout.addWidget(self._study_stats_lbl)

        layout.addWidget(card_review)

        # ═════════════════════════════════════════════════════
        # 卡片 4：词库与数据管理 (Vocab & Data Management)
        # ═════════════════════════════════════════════════════
        card_vocab, vocab_layout = self._create_card("词库与数据管理")

        # 格式说明
        hint_label = QLabel("外部导入格式：CSV / TXT（每行：韩文,释义,例句）或 JSON 词表")
        hint_label.setObjectName("card_hint")
        vocab_layout.addWidget(hint_label)

        # 文件选择行
        file_row = QHBoxLayout()
        self._file_path_edit = QLineEdit()
        self._file_path_edit.setPlaceholderText("请选择 .csv, .txt 或 .json 词库文件...")
        self._file_path_edit.setReadOnly(True)
        file_row.addWidget(self._file_path_edit)

        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.setFixedSize(65, 30)
        self._browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._browse_btn.clicked.connect(self._on_browse_file)
        file_row.addWidget(self._browse_btn)
        vocab_layout.addLayout(file_row)

        # 自定义书名行
        name_row = QHBoxLayout()
        name_label = QLabel("导入词书名称:")
        name_label.setObjectName("field_label")
        name_row.addWidget(name_label)

        self._book_name_edit = QLineEdit()
        self._book_name_edit.setPlaceholderText("留空则自动以文件名命名")
        name_row.addWidget(self._book_name_edit)
        vocab_layout.addLayout(name_row)

        # 导入执行按钮
        self._import_btn = QPushButton("开始批量导入并归档")
        self._import_btn.setFixedHeight(32)
        self._import_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._import_btn.clicked.connect(self._on_import_clicked)
        vocab_layout.addWidget(self._import_btn)

        # 导入状态消息标签
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("QLabel { font-size: 11px; font-weight: 600; }")
        vocab_layout.addWidget(self._status_label)

        # 分割线
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setObjectName("card_sep")
        vocab_layout.addWidget(sep1)

        # 导出生词本按钮
        self._export_btn = QPushButton("导出生词本 (CSV / Anki 兼容)")
        self._export_btn.setFixedHeight(32)
        self._export_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._export_btn.setToolTip("将所有收藏的生词导出为标准 UTF-8 with BOM CSV 文件，可直接导入 Excel、Anki 等")
        self._export_btn.clicked.connect(self._on_export_vocab_clicked)
        vocab_layout.addWidget(self._export_btn)

        # 分割线
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setObjectName("card_sep")
        vocab_layout.addWidget(sep2)

        # 系统行为设置
        self._minimize_tray_checkbox = QCheckBox("点击关闭按钮 (✕) 时最小化到系统托盘 (推荐)")
        self._minimize_tray_checkbox.setChecked(self._minimize_to_tray)
        self._minimize_tray_checkbox.toggled.connect(self._on_minimize_tray_toggled)
        vocab_layout.addWidget(self._minimize_tray_checkbox)

        self._autostart_checkbox = QCheckBox("开机时自动启动并最小化到托盘 (Windows)")
        self._autostart_checkbox.setChecked(is_autostart_enabled())
        self._autostart_checkbox.toggled.connect(self._on_autostart_toggled)
        vocab_layout.addWidget(self._autostart_checkbox)

        # 数据备份与恢复
        backup_btn_row = QHBoxLayout()
        backup_btn_row.setSpacing(10)

        self._export_backup_btn = QPushButton("全量备份数据")
        self._export_backup_btn.setFixedHeight(32)
        self._export_backup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._export_backup_btn.setToolTip("将生词本、已掌握词汇、学习断点及个性化设置打包导出为 JSON 备份文件")
        self._export_backup_btn.clicked.connect(self._on_export_backup_clicked)
        backup_btn_row.addWidget(self._export_backup_btn)

        self._import_backup_btn = QPushButton("导入恢复备份")
        self._import_backup_btn.setFixedHeight(32)
        self._import_backup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._import_backup_btn.setToolTip("选择已有的 JSON 备份文件，一键还原所有学习记录与设置")
        self._import_backup_btn.clicked.connect(self._on_import_backup_clicked)
        backup_btn_row.addWidget(self._import_backup_btn)

        vocab_layout.addLayout(backup_btn_row)

        layout.addWidget(card_vocab)
        layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # ── 底部完成按钮 ──
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self._close_btn = QPushButton("完成")
        self._close_btn.setFixedSize(80, 32)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(self._close_btn)
        main_layout.addLayout(bottom_row)

    # ─────────────────────────────────────────────────────────
    # 自定义快捷键录制与清空逻辑
    # ─────────────────────────────────────────────────────────

    def _on_key_sequence_changed(self, key_id: str, seq):
        if isinstance(seq, str):
            key_str = seq
        else:
            key_str = seq.toString() if hasattr(seq, "toString") else str(seq)
        self._custom_shortcuts[key_id] = key_str
        if self._state_manager:
            self._state_manager.save_shortcuts(self._custom_shortcuts)
        self.shortcuts_mapping_changed.emit(self._custom_shortcuts)

    def _on_clear_shortcut(self, key_id: str):
        """单独清空/解绑某一动作的快捷键"""
        if key_id in self._shortcut_edits:
            self._shortcut_edits[key_id].clear()
        self._custom_shortcuts[key_id] = ""
        if self._state_manager:
            self._state_manager.save_shortcuts(self._custom_shortcuts)
        self.shortcuts_mapping_changed.emit(self._custom_shortcuts)

    def _on_reset_shortcuts_clicked(self):
        """一键恢复全部预设默认快捷键"""
        self._custom_shortcuts = dict(DEFAULT_SHORTCUTS)
        for key_id, default_key in DEFAULT_SHORTCUTS.items():
            if key_id in self._shortcut_edits:
                self._shortcut_edits[key_id].setKeySequence(QKeySequence(default_key))
        if self._state_manager:
            self._state_manager.save_shortcuts(self._custom_shortcuts)
        self.shortcuts_mapping_changed.emit(self._custom_shortcuts)

    def _on_review_batch_changed(self, idx: int):
        """单次智能复习词数改变"""
        val = self._batch_combo.currentData()
        if val and self._state_manager:
            self._state_manager.set_review_batch_size(val)

    # ─────────────────────────────────────────────────────────
    # 数据备份与还原逻辑
    # ─────────────────────────────────────────────────────────

    def _on_export_backup_clicked(self):
        default_filename = f"korean_vocab_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存数据备份文件",
            default_filename,
            "JSON 备份文件 (*.json);;所有文件 (*.*)"
        )
        if not file_path:
            return

        success, msg, summary = export_user_backup(
            file_path=file_path,
            vocab_book=self._vocab_book,
            vocab_manager=self._vocab_manager,
            state_manager=self._state_manager
        )
        if success:
            QMessageBox.information(
                self,
                "备份成功",
                f"数据已成功备份至：\n{file_path}\n\n"
                f"• 生词本词汇数：{summary.get('starred_count', 0)} 个\n"
                f"• 已掌握词汇数：{summary.get('mastered_count', 0)} 个\n"
                f"• 备份生成时间：{summary.get('export_time', '')}"
            )
        else:
            QMessageBox.critical(self, "备份失败", msg)

    def _on_import_backup_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据备份文件进行还原",
            "",
            "JSON 备份文件 (*.json);;所有文件 (*.*)"
        )
        if not file_path:
            return

        reply = QMessageBox.question(
            self,
            "确认恢复备份",
            "导入备份将同步恢复生词本、已掌握词汇库以及所有学习进度与偏好设置。\n\n是否确认继续恢复？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, msg, summary = import_user_backup(
            file_path=file_path,
            vocab_book=self._vocab_book,
            vocab_manager=self._vocab_manager,
            state_manager=self._state_manager
        )
        if success:
            QMessageBox.information(
                self,
                "恢复成功",
                f"备份数据已成功还原！\n\n"
                f"• 恢复生词本词汇：{summary.get('starred_count', 0)} 个\n"
                f"• 恢复已掌握词汇：{summary.get('mastered_count', 0)} 个\n"
                f"• 备份源创建时间：{summary.get('export_time', '')}\n\n"
                f"点击完成即可刷新卡片与学习进度。"
            )
            self.backup_restored.emit()
        else:
            QMessageBox.critical(self, "恢复失败", msg)

    # ─────────────────────────────────────────────────────────
    # 托盘与开机自启逻辑
    # ─────────────────────────────────────────────────────────

    def _on_minimize_tray_toggled(self, checked: bool):
        self._minimize_to_tray = checked
        self.minimize_to_tray_toggled.emit(checked)

    def _on_autostart_toggled(self, checked: bool):
        success = set_autostart_enabled(checked)
        if not success:
            QMessageBox.warning(self, "设置失败", "无法修改 Windows 开机自启注册表，请检查权限。")
            self._autostart_checkbox.blockSignals(True)
            self._autostart_checkbox.setChecked(is_autostart_enabled())
            self._autostart_checkbox.blockSignals(False)
        else:
            self.autostart_toggled.emit(checked)

    # ─────────────────────────────────────────────────────────
    # 快捷键总控逻辑
    # ─────────────────────────────────────────────────────────

    def _on_shortcuts_toggled(self, checked: bool):
        self._shortcuts_enabled = checked
        self.shortcuts_toggled.emit(checked)

    def _open_shortcut_dialog(self):
        """弹出独立全功能自定义快捷键配置对话框"""
        dlg = ShortcutDialog(
            current_shortcuts=self._custom_shortcuts,
            current_theme=getattr(self, "_theme", "seoul_night"),
            parent=self
        )
        def _on_saved(mapping: dict):
            self._custom_shortcuts = mapping
            self.shortcuts_mapping_changed.emit(mapping)
        dlg.shortcuts_saved.connect(_on_saved)
        dlg.exec()

    # ─────────────────────────────────────────────────────────
    # 字体与字号切换逻辑
    # ─────────────────────────────────────────────────────────

    def _on_font_changed(self, idx: int):
        family = self._font_combo.itemData(idx)
        if family:
            self._current_font = family
            self._update_preview()
            self.font_changed.emit(family)

    def _on_scale_changed(self, idx: int):
        scale = self._scale_combo.itemData(idx)
        if scale:
            self._current_scale = float(scale)
            self._update_preview()
            self.font_scale_changed.emit(self._current_scale)

    def _update_preview(self):
        font_size = int(14 * self._current_scale)
        self._preview_label.setFont(QFont(self._current_font, font_size, QFont.Weight.Bold))

    def _on_import_font_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择本地韩文字体文件进行导入",
            "",
            "字体文件 (*.ttf *.otf *.ttc);;所有文件 (*.*)"
        )
        if not file_path:
            return

        success, family_name, msg = import_font_file(file_path)
        if success and family_name:
            QMessageBox.information(
                self,
                "字体导入成功",
                f"成功导入并载入外部字体：\n\n• 字体名称：{family_name}\n• 保存位置：data/fonts/{os.path.basename(file_path)}\n\n该字体已自动设为当前主卡片字体！"
            )
            # 刷新字体下拉选项并选中新字体
            self._font_list = get_available_korean_fonts()
            self._font_combo.blockSignals(True)
            self._font_combo.clear()
            selected_idx = 0
            for idx, (d_name, fam) in enumerate(self._font_list):
                self._font_combo.addItem(d_name, userData=fam)
                if fam == family_name:
                    selected_idx = idx
            self._font_combo.setCurrentIndex(selected_idx)
            self._font_combo.blockSignals(False)

            self._current_font = family_name
            if self._state_manager:
                self._state_manager.set("korean_font", family_name)
            self._update_preview()
            self.font_changed.emit(family_name)
        else:
            QMessageBox.warning(self, "字体导入失败", msg)

    # ─────────────────────────────────────────────────────────
    # 词库导入逻辑
    # ─────────────────────────────────────────────────────────

    def _on_browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择外部词库文件",
            "",
            "词库文件 (*.csv *.txt *.json);;CSV 文件 (*.csv);;文本文件 (*.txt);;JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if file_path:
            self._selected_file_path = file_path
            self._file_path_edit.setText(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            if not self._book_name_edit.text():
                self._book_name_edit.setText(f"自定义: {base_name}")

    def _on_import_clicked(self):
        file_path = self._file_path_edit.text().strip()
        if not file_path or not os.path.exists(file_path):
            self._status_label.setText("请先选择有效的词库文件！")
            self._status_label.setStyleSheet("QLabel { color: #EF4444; font-size: 12px; }")
            return

        book_name = self._book_name_edit.text().strip()
        success, count, title, msg = import_custom_vocab(
            file_path=file_path,
            custom_book_name=book_name if book_name else None
        )

        if success:
            self._status_label.setText(f"{msg}")
            self._status_label.setStyleSheet("QLabel { color: #2ECC71; font-size: 12px; }")
            self.vocab_imported.emit(title)
            QMessageBox.information(self, "导入成功", msg)
        else:
            self._status_label.setText(f"导入失败: {msg}")
            self._status_label.setStyleSheet("QLabel { color: #EF4444; font-size: 12px; }")

    # ─────────────────────────────────────────────────────────
    # 导出生词本逻辑 (CSV / Anki 兼容 / UTF-8 with BOM)
    # ─────────────────────────────────────────────────────────

    def _on_export_vocab_clicked(self):
        if not self._vocab_book or self._vocab_book.count() == 0:
            QMessageBox.information(
                self,
                "生词本为空",
                "当前生词本中暂无收藏的词汇，无需导出。\n可在背诵卡片界面点击收藏按钮或按 S/K 键将生词加入生词本。"
            )
            return

        default_filename = f"Korean_Vocab_Starred_{datetime.now().strftime('%Y%m%d')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出我的生词本",
            default_filename,
            "CSV 电子表格 (*.csv);;所有文件 (*.*)"
        )
        if not file_path:
            return

        word_map = {}
        if self._vocab_manager and hasattr(self._vocab_manager, "all_words"):
            word_map = {str(w["id"]): w for w in self._vocab_manager.all_words}

        starred_ids = self._vocab_book.get_all_ids()
        rows = []
        for wid in starred_ids:
            w = word_map.get(str(wid))
            if w:
                korean = w.get("korean", "")
                origin = w.get("origin", "") or w.get("hanja", "") or ""
                if origin and w.get("word_type") == "hanja":
                    try:
                        from core.hanja_converter import format_hanja_origin
                        origin = format_hanja_origin(origin)
                    except Exception:
                        origin = f"[汉字] {origin}"
                elif origin and w.get("word_type") == "loanword":
                    origin = f"[外来] {origin}"
                pos = w.get("pos", "")
                pron = w.get("pronunciation", "")
                meaning = w.get("meaning", w.get("chinese", ""))
                ex_kr = w.get("example_kr", "")
                ex_cn = w.get("example_cn", "")
                if not ex_kr and w.get("examples"):
                    ex_kr = w["examples"][0].get("korean", "")
                    ex_cn = w["examples"][0].get("chinese", "")
                rows.append([korean, origin, pos, pron, meaning, ex_kr, ex_cn])
            else:
                # 兼容生词本独立记录
                item = next((it for it in self._vocab_book.get_all() if str(it.get("word_id")) == str(wid)), None)
                if item:
                    rows.append([item.get("korean", ""), "", item.get("pos", ""), "", item.get("chinese", ""), "", ""])

        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["韩文", "汉字/词源", "词性", "发音", "中文释义", "韩文例句", "中文翻译"])
                writer.writerows(rows)

            QMessageBox.information(
                self,
                "导出成功",
                f"成功导出 {len(rows)} 个生词！\n保存路径：\n{file_path}\n\n该文件采用 UTF-8 with BOM 编码，完美兼容 Excel、Anki 及各类背诵工具！"
            )
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"写入文件时发生错误：\n{e}")

    def _on_theme_combo_changed(self, index: int):
        theme_id = self._theme_combo.itemData(index)
        if theme_id:
            self._theme = theme_id
            if self._state_manager:
                self._state_manager.set("theme", theme_id)
            self.apply_theme(theme_id)
            self.theme_changed.emit(theme_id)

    # ─────────────────────────────────────────────────────────
    # 主题样式 (Instagram / iOS 纯粹极简暗色美学)
    # ─────────────────────────────────────────────────────────

    def apply_theme(self, theme: str):
        self._theme = theme
        if theme == "dark":
            theme = "seoul_night"
        elif theme == "light":
            theme = "cream_latte"

        cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["seoul_night"])
        is_dark = cfg.get("is_dark", True)
        bg = f"rgb({cfg['bg_color'][0]}, {cfg['bg_color'][1]}, {cfg['bg_color'][2]})"
        card_bg = cfg.get("card_bg", "#161922")
        input_bg = cfg.get("input_bg", "#1F2330")
        text = cfg.get("text_primary", "#FFFFFF")
        text_sec = cfg.get("text_secondary", "#94A3B8")
        accent = cfg.get("accent", "#2ECC71")
        border = cfg.get("border", "rgba(255, 255, 255, 0.10)")

        self.setStyleSheet(
            f"QDialog {{ background: {bg}; color: {text}; }}"
            f"QLabel#dialog_main_title {{ color: {text}; font-size: 16px; font-weight: 700; }}"
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}"
            f"QWidget#settings_scroll_content {{ background: transparent; }}"
            f"QFrame#settings_card {{ background: {card_bg}; border: 1px solid {border}; border-radius: 12px; }}"
            f"QLabel#card_title {{ color: {text}; font-size: 13px; font-weight: 700; background: transparent; }}"
            f"QLabel#card_hint {{ color: {text_sec}; font-size: 11px; line-height: 1.4; background: transparent; }}"
            f"QLabel#field_label {{ color: {text}; font-size: 12px; font-weight: 500; background: transparent; }}"
            f"QLabel#stats_label {{ color: {text_sec}; font-size: 11px; background: transparent; }}"
            f"QFrame#card_sep {{ background: {border}; max-height: 1px; border: none; }}"
            f"QScrollBar:vertical {{ background: rgba(255, 255, 255, 0.05); width: 8px; margin: 0; border-radius: 4px; }}"
            f"QScrollBar::handle:vertical {{ background: rgba(255, 255, 255, 0.32); border-radius: 4px; min-height: 28px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 0.52); }}"
            f"QScrollBar::handle:vertical:pressed {{ background: {accent}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; border: none; }}"
            f"QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{ background: none; border: none; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; border: none; }}"
            f"QCheckBox {{ color: {text}; font-size: 12px; spacing: 8px; background: transparent; }}"
            f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {border}; background: {input_bg}; }}"
            f"QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}"
            f"QLineEdit {{ background: {input_bg}; color: {text}; border: 1px solid {border}; "
            f"border-radius: 8px; padding: 4px 10px; font-size: 12px; }}"
            f"QLineEdit:focus {{ border-color: {accent}; }}"
            f"QComboBox {{ background: {input_bg}; color: {text}; border: 1px solid {border}; "
            f"border-radius: 8px; padding: 4px 10px; font-size: 12px; }}"
            f"QComboBox:focus {{ border-color: {accent}; }}"
            f"QComboBox QAbstractItemView {{ background: {card_bg}; color: {text}; border: 1px solid {border}; selection-background-color: {accent}44; selection-color: {text}; }}"
            f"QLabel#preview_box {{ background: {input_bg}; color: {text}; border-radius: 8px; border: 1px dashed {border}; padding: 6px; }}"
            f"QPushButton#capsule_btn {{ background: {accent}18; color: {accent}; "
            f"border: 1px solid {accent}55; border-radius: 10px; font-size: 12px; font-weight: 600; }}"
            f"QPushButton#capsule_btn:hover {{ background: {accent}30; border-color: {accent}; }}"
            f"QPushButton {{ background: {input_bg}; color: {text}; border: 1px solid {border}; "
            f"border-radius: 8px; font-size: 12px; font-weight: 500; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: rgba(255, 255, 255, 0.12); color: {text}; border-color: rgba(255, 255, 255, 0.22); }}"
        )
        self._import_btn.setStyleSheet(
            f"QPushButton {{ background: {accent}; color: #FFFFFF; border: none; "
            f"border-radius: 8px; font-size: 12px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: {accent}CC; }}"
        )
        self._close_btn.setStyleSheet(
            f"QPushButton {{ background: {input_bg}; color: {text}; border: 1px solid {border}; "
            f"border-radius: 8px; font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {accent}; color: #FFFFFF; border-color: {accent}; }}"
        )
