# ui/translation_dialog.py
# -*- coding: utf-8 -*-
"""
Instagram 风格极简毛玻璃翻译抽屉 (Translation Drawer)
功能：
1. Naver Papago / Google / 本地离线词典 / 多引擎对照 4 种模式一键切换 (Pill Tabs)
2. 中韩双向自动语种检测 (ko <-> zh-CN)
3. 300ms 实时输入防抖异步翻译 (Debounce Worker)
4. 🔊 朗读原句/译文
5. ➕ 一键收入自定义生词本 (custom_vocab.json)
6. 📋 一键复制译文
7. Instagram 极简半透明磨砂毛玻璃排版与流畅拖拽
"""

import html
import json
import os
import re
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QApplication,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen, QBrush, QFont, QCursor

from config.settings import THEME_CONFIGS
from core.translator_manager import TranslatorManager, is_korean_text, detect_direction
from core.tts_engine import TTSEngine
from core.clipboard_listener import ClipboardListener
from ui.toast_widget import ToastWidget


class TranslationDialog(QDialog):
    """Instagram 风格极简中韩多引擎翻译抽屉"""

    word_added_to_custom = pyqtSignal(str, str, str)  # (korean, meaning, pron)

    def __init__(self, tts_engine: Optional[TTSEngine] = None, theme: str = "seoul_night", parent=None):
        super().__init__(parent)
        self._tts = tts_engine
        self._theme = theme
        self._translator = TranslatorManager(self)
        self._translator.translation_completed.connect(self._on_translation_completed)

        self._drag_pos = QPoint()
        self._current_engine = "youdao"
        self._last_result_data: Dict[str, Any] = {}

        # 输入防抖定时器 (300ms)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._do_translate)

        # 窗口基础属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(460, 520)
        self.setMinimumSize(420, 460)

        self._setup_ui()
        self.apply_theme(theme)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # ── 1. 顶部 Header 栏 ──
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 2, 4, 2)

        self._title_label = QLabel("极简中韩互译")
        self._title_label.setStyleSheet("QLabel { color: #FFFFFF; font-size: 14px; font-weight: 700; }")
        header_layout.addWidget(self._title_label)

        # 语种方向胶囊徽章
        self._direction_badge = QLabel("韩 ➔ 中")
        self._direction_badge.setObjectName("direction_badge")
        self._direction_badge.setStyleSheet(
            "QLabel#direction_badge { background: rgba(46, 204, 113, 0.18); color: #2ECC71; "
            "border: 1px solid rgba(46, 204, 113, 0.40); border-radius: 11px; padding: 2px 10px; font-size: 11px; font-weight: bold; }"
        )
        header_layout.addWidget(self._direction_badge)
        header_layout.addStretch()

        # 关闭按钮
        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.clicked.connect(self.hide)
        self._close_btn.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.08); color: #A0A5B5; border: none; border-radius: 13px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(235, 87, 87, 0.85); color: #FFFFFF; }"
        )
        header_layout.addWidget(self._close_btn)
        main_layout.addLayout(header_layout)

        # ── 2. 顶部引擎切换 Pill Tabs ──
        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(6)
        self._engine_buttons = {}

        tabs = [
            ("youdao", "有道智能 (免梯)"),
            ("papago", "Papago 地道"),
            ("google", "Google 全文"),
            ("offline", "离线词典"),
            ("all", "多引擎对照"),
        ]

        for eng_id, eng_title in tabs:
            btn = QPushButton(eng_title)
            btn.setCheckable(True)
            btn.setChecked(eng_id == "youdao")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked, eid=eng_id: self._on_engine_tab_clicked(eid))
            tab_layout.addWidget(btn)
            self._engine_buttons[eng_id] = btn

        main_layout.addLayout(tab_layout)

        # ── 3. 输入区域（半透深色圆角卡片） ──
        input_container = QWidget(self)
        input_container.setObjectName("input_container")
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(10, 8, 10, 8)
        input_layout.setSpacing(4)

        self._input_edit = QTextEdit()
        self._input_edit.setObjectName("input_edit")
        self._input_edit.setPlaceholderText("输入韩文或中文，300ms 自动实时翻译...")
        self._input_edit.setFixedHeight(75)
        self._input_edit.textChanged.connect(self._on_input_changed)
        input_layout.addWidget(self._input_edit)

        # 输入栏快捷操作（粘贴 & 清空）
        input_tools = QHBoxLayout()
        input_tools.setContentsMargins(2, 0, 2, 0)
        self._char_count_lbl = QLabel("0 字")
        self._char_count_lbl.setStyleSheet("QLabel { color: #64748B; font-size: 11px; }")
        input_tools.addWidget(self._char_count_lbl)
        input_tools.addStretch()

        self._paste_btn = QPushButton("粘贴")
        self._paste_btn.setFixedSize(56, 22)
        self._paste_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._paste_btn.clicked.connect(self._paste_from_clipboard)
        input_tools.addWidget(self._paste_btn)

        self._clear_btn = QPushButton("清空")
        self._clear_btn.setFixedSize(56, 22)
        self._clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._clear_btn.clicked.connect(self._clear_input)
        input_tools.addWidget(self._clear_btn)

        input_layout.addLayout(input_tools)
        main_layout.addWidget(input_container)

        # ── 4. 译文与结果展示区域（可滚动） ──
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("result_scroll")
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.viewport().setAutoFillBackground(False)
        self._scroll_area.viewport().setStyleSheet("background: transparent;")

        self._result_content = QWidget()
        self._result_content.setObjectName("result_content")
        self._result_content.setAutoFillBackground(False)
        self._result_content.setStyleSheet("background: transparent;")
        self._result_layout = QVBoxLayout(self._result_content)
        self._result_layout.setContentsMargins(4, 4, 4, 4)
        self._result_layout.setSpacing(8)

        # 主翻译结果卡片
        self._main_result_card = QWidget(self._result_content)
        self._main_result_card.setObjectName("main_result_card")
        main_res_layout = QVBoxLayout(self._main_result_card)
        main_res_layout.setContentsMargins(12, 10, 12, 10)
        main_res_layout.setSpacing(6)

        self._res_engine_tag = QLabel("Naver Papago 译文")
        self._res_engine_tag.setStyleSheet("QLabel { color: #2ECC71; font-size: 11px; font-weight: bold; }")
        main_res_layout.addWidget(self._res_engine_tag)

        self._result_label = QLabel("等待输入...")
        self._result_label.setObjectName("result_label")
        self._result_label.setWordWrap(True)
        self._result_label.setTextFormat(Qt.TextFormat.RichText)
        self._result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        main_res_layout.addWidget(self._result_label)

        self._result_layout.addWidget(self._main_result_card)

        # 离线词典详细卡片（词性、音标、例句）
        self._dict_detail_card = QWidget(self._result_content)
        self._dict_detail_card.setObjectName("dict_detail_card")
        dict_layout = QVBoxLayout(self._dict_detail_card)
        dict_layout.setContentsMargins(12, 10, 12, 10)
        dict_layout.setSpacing(4)

        self._dict_tag = QLabel("本地离线词典精确解析")
        self._dict_tag.setStyleSheet("QLabel { color: #38BDF8; font-size: 11px; font-weight: bold; }")
        dict_layout.addWidget(self._dict_tag)

        self._dict_content_lbl = QLabel()
        self._dict_content_lbl.setWordWrap(True)
        self._dict_content_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._dict_content_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dict_layout.addWidget(self._dict_content_lbl)

        self._dict_detail_card.hide()
        self._result_layout.addWidget(self._dict_detail_card)

        # 多引擎对照容器（在 'all' 模式下动态构建）
        self._compare_container = QWidget(self._result_content)
        self._compare_container.setObjectName("compare_container")
        self._compare_layout = QVBoxLayout(self._compare_container)
        self._compare_layout.setContentsMargins(0, 0, 0, 0)
        self._compare_layout.setSpacing(6)
        self._compare_container.hide()
        self._result_layout.addWidget(self._compare_container)

        self._result_layout.addStretch()
        self._scroll_area.setWidget(self._result_content)
        main_layout.addWidget(self._scroll_area, stretch=1)

        # ── 5. 底部快捷动作栏（Action Bar） ──
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self._speak_src_btn = QPushButton("朗读原句")
        self._speak_src_btn.setFixedHeight(30)
        self._speak_src_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._speak_src_btn.clicked.connect(self._speak_source)
        action_bar.addWidget(self._speak_src_btn)

        self._speak_res_btn = QPushButton("朗读译文")
        self._speak_res_btn.setFixedHeight(30)
        self._speak_res_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._speak_res_btn.clicked.connect(self._speak_target)
        action_bar.addWidget(self._speak_res_btn)

        self._copy_btn = QPushButton("复制译文")
        self._copy_btn.setFixedHeight(30)
        self._copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._copy_btn.clicked.connect(self._copy_result)
        action_bar.addWidget(self._copy_btn)

        self._add_vocab_btn = QPushButton("收入生词本")
        self._add_vocab_btn.setFixedHeight(30)
        self._add_vocab_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._add_vocab_btn.clicked.connect(self._add_to_custom_vocab)
        action_bar.addWidget(self._add_vocab_btn)

        main_layout.addLayout(action_bar)

    # ─────────────────────────────────────────────────────────
    # 交互与防抖逻辑
    # ─────────────────────────────────────────────────────────

    def _on_input_changed(self):
        text = self._input_edit.toPlainText().strip()
        self._char_count_lbl.setText(f"{len(text)} 字")

        if not text:
            self._direction_badge.setText("🇰🇷 韩 ➔ 🇨🇳 中")
            self._result_label.setText("<span style='color: #64748B;'>等待输入...</span>")
            self._dict_detail_card.hide()
            self._compare_container.hide()
            self._main_result_card.show()
            self._debounce_timer.stop()
            return

        # 更新方向徽章
        is_kr = is_korean_text(text)
        if is_kr:
            self._direction_badge.setText("🇰🇷 韩 ➔ 🇨🇳 中")
            self._direction_badge.setStyleSheet(
                "QLabel#direction_badge { background: rgba(46, 204, 113, 0.18); color: #2ECC71; "
                "border: 1px solid rgba(46, 204, 113, 0.40); border-radius: 11px; padding: 2px 10px; font-size: 11px; font-weight: bold; }"
            )
        else:
            self._direction_badge.setText("🇨🇳 中 ➔ 🇰🇷 韩")
            self._direction_badge.setStyleSheet(
                "QLabel#direction_badge { background: rgba(56, 189, 248, 0.18); color: #38BDF8; "
                "border: 1px solid rgba(56, 189, 248, 0.40); border-radius: 11px; padding: 2px 10px; font-size: 11px; font-weight: bold; }"
            )

        # 启动 300ms 防抖计时器
        self._debounce_timer.start()

    def _on_engine_tab_clicked(self, eng_id: str):
        self._current_engine = eng_id
        for eid, btn in self._engine_buttons.items():
            btn.setChecked(eid == eng_id)
        self._apply_engine_tab_styles()
        self._do_translate()

    def _do_translate(self):
        text = self._input_edit.toPlainText().strip()
        if not text:
            return
        self._result_label.setText("<span style='color: #94A3B8;'>⏳ 正在多引擎极速翻译中...</span>")
        self._translator.translate_async(text, engine=self._current_engine)

    def _on_translation_completed(self, data: Dict[str, Any]):
        self._last_result_data = data
        if data.get("status") == "empty":
            return

        engine = data.get("engine", "papago")
        main_res = data.get("main_result", "")
        details = data.get("details")

        if engine == "all":
            # 多引擎对照模式
            self._main_result_card.hide()
            self._dict_detail_card.hide()
            self._render_compare_results(data)
            self._compare_container.show()
        else:
            self._compare_container.hide()
            self._main_result_card.show()

            # 更新引擎标签
            tag_map = {
                "youdao": ("🟢 有道智能译文 (国内免梯直连)", "#10B981"),
                "papago": ("🟢 Naver Papago 译文", "#2ECC71"),
                "google": ("🔵 Google 智能全文译文", "#38BDF8"),
                "offline": ("⚡ 本地离线词典释义", "#F59E0B"),
            }
            tag_text, tag_color = tag_map.get(engine, ("译文", "#FFFFFF"))
            self._res_engine_tag.setText(tag_text)
            self._res_engine_tag.setStyleSheet(f"QLabel {{ color: {tag_color}; font-size: 11px; font-weight: bold; }}")

            # 渲染主结果
            self._result_label.setText(
                f"<div style='font-size: 15px; font-weight: 600; line-height: 1.5; color: #FFFFFF;'>"
                f"{html.escape(main_res)}"
                f"</div>"
            )

            # 如果离线词典有更多结构化详情（如音标、词性、例句），展示详情卡片
            if details and details.get("success"):
                pos = details.get("pos", "")
                pron = details.get("pronunciation", "")
                ex_kr = details.get("example_kr", "")
                ex_cn = details.get("example_cn", "")

                meta_parts = []
                if pos: meta_parts.append(f"<span style='color: #6EE7B7;'>[{pos}]</span>")
                if pron: meta_parts.append(f"<span style='color: #F1F5F9; font-style: italic;'>/{pron}/</span>")
                meta_html = "  ".join(meta_parts)

                ex_html = ""
                if ex_kr:
                    ex_html = (
                        f"<div style='margin-top: 4px; padding-top: 4px; border-top: 1px dashed rgba(255,255,255,0.15); font-size: 11.5px; color: #CBD5E1;'>"
                        f"<b>例</b>: {html.escape(ex_kr)}<br><span style='color: #94A3B8;'>{html.escape(ex_cn)}</span>"
                        f"</div>"
                    )

                self._dict_content_lbl.setText(f"{meta_html}{ex_html}")
                self._dict_detail_card.show()
            else:
                self._dict_detail_card.hide()

    def _render_compare_results(self, data: Dict[str, Any]):
        """渲染多引擎并排/分块对照视图"""
        while self._compare_layout.count():
            item = self._compare_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        engines_data = data.get("data", {})

        # 1. 有道智能卡片
        y_res = engines_data.get("youdao", {})
        y_card = self._create_mini_engine_card("🟢 有道智能 (国内免梯)", y_res.get("text", "无结果"), "#10B981")
        self._compare_layout.addWidget(y_card)

        # 2. Papago 卡片
        p_res = engines_data.get("papago", {})
        p_card = self._create_mini_engine_card("🟢 Naver Papago", p_res.get("text", "无结果"), "#2ECC71")
        self._compare_layout.addWidget(p_card)

        # 3. Google 卡片
        g_res = engines_data.get("google", {})
        g_card = self._create_mini_engine_card("🔵 Google Translate", g_res.get("text", "无结果"), "#38BDF8")
        self._compare_layout.addWidget(g_card)

        # 4. 离线词典卡片
        o_res = engines_data.get("offline", {})
        o_text = o_res.get("text", "未匹配")
        if o_res.get("success"):
            pos = o_res.get("pos", "")
            if pos: o_text = f"[{pos}] {o_text}"
        o_card = self._create_mini_engine_card("⚡ 本地离线词典", o_text, "#F59E0B")
        self._compare_layout.addWidget(o_card)

    def _create_mini_engine_card(self, title: str, content: str, title_color: str) -> QWidget:
        card = QWidget(self._compare_container)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"QLabel {{ color: {title_color}; font-size: 11px; font-weight: bold; }}")
        layout.addWidget(t_lbl)

        c_lbl = QLabel(content)
        c_lbl.setWordWrap(True)
        c_lbl.setStyleSheet("QLabel {{ color: #FFFFFF; font-size: 13px; font-weight: 500; line-height: 1.4; }}")
        c_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(c_lbl)

        card.setStyleSheet(
            "QWidget { background: rgba(18, 20, 26, 0.75); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 12px; padding: 4px; }"
            "QWidget:hover { background: rgba(24, 28, 38, 0.85); border-color: rgba(255, 255, 255, 0.20); }"
        )
        return card

    # ─────────────────────────────────────────────────────────
    # 动作响应
    # ─────────────────────────────────────────────────────────

    def _paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self._input_edit.setPlainText(text.strip())

    def _clear_input(self):
        self._input_edit.clear()
        self._input_edit.setFocus()

    def _get_tts(self) -> TTSEngine:
        if self._tts is None:
            self._tts = TTSEngine()
        return self._tts

    def _speak_source(self):
        text = self._input_edit.toPlainText().strip()
        if text:
            self._get_tts().speak(text)

    def _speak_target(self):
        if not self._last_result_data:
            return
        target_text = self._last_result_data.get("main_result", "")
        clean_text = re.sub(r"\(.*?\)|（.*?）|\[.*?\]", "", target_text).strip()
        if clean_text:
            self._get_tts().speak(clean_text)

    def _copy_result(self):
        if not self._last_result_data:
            return
        text = self._last_result_data.get("main_result", "")
        if text:
            QApplication.clipboard().setText(text)
            ToastWidget.show_toast(self, "📋 译文已复制到剪贴板！", icon="✨", duration_ms=1800)

    def _add_to_custom_vocab(self):
        """将当前翻译对一键加入自定义生词库 (data/custom_vocab.json)"""
        src = self._input_edit.toPlainText().strip()
        if not src:
            return

        is_kr = is_korean_text(src)
        target = self._last_result_data.get("main_result", "")

        if is_kr:
            kr = src
            cn = target
        else:
            kr = target
            cn = src

        # 音标与词性从 details 中提取
        pron = ""
        details = self._last_result_data.get("details")
        if details:
            pron = details.get("pronunciation", "")

        listener = ClipboardListener(parent=self)
        listener.add_to_custom_vocab(kr, cn, pron)

        self.word_added_to_custom.emit(kr, cn, pron)
        ToastWidget.show_toast(
            self,
            f"🎉 <b>已成功收入生词本！</b><br><span style='color: #38BDF8;'>{html.escape(kr)}</span>",
            icon="📥",
            duration_ms=2200
        )

    # ─────────────────────────────────────────────────────────
    # 主题与外观
    # ─────────────────────────────────────────────────────────

    def apply_theme(self, theme: str):
        self._theme = theme
        if theme == "dark": theme = "seoul_night"
        elif theme == "light": theme = "cream_latte"

        cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["seoul_night"])
        is_dark = cfg.get("is_dark", True)
        bg = f"rgb({cfg['bg_color'][0]}, {cfg['bg_color'][1]}, {cfg['bg_color'][2]})"
        card_bg = "rgba(18, 20, 26, 0.75)" if is_dark else "rgba(255, 255, 255, 0.95)"
        input_bg = "rgba(18, 20, 26, 0.75)" if is_dark else "rgba(0, 0, 0, 0.05)"
        text = cfg.get("text_primary", "#FFFFFF") if is_dark else "#1E293B"
        text_sec = cfg.get("text_secondary", "#94A3B8")
        accent = cfg.get("accent", "#2ECC71")
        border = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.08)"

        self.setStyleSheet(f"QDialog {{ background: {bg}; color: {text}; }}")

        # 1. 容器与卡片 QSS (彻底消除任何白底)
        self._scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; border: none; }"
            f"QScrollBar:vertical {{ background: rgba(255, 255, 255, 0.05); width: 8px; margin: 0; border-radius: 4px; }}"
            f"QScrollBar::handle:vertical {{ background: rgba(255, 255, 255, 0.32); border-radius: 4px; min-height: 28px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 0.52); }}"
            f"QScrollBar::handle:vertical:pressed {{ background: {accent}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; border: none; }}"
            f"QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{ background: none; border: none; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; border: none; }}"
        )
        self._result_content.setStyleSheet("QWidget#result_content { background: transparent; }")

        input_container_widget = self.findChild(QWidget, "input_container")
        if input_container_widget:
            input_container_widget.setStyleSheet(
                f"QWidget#input_container {{ background: {card_bg}; border: 1px solid {border}; border-radius: 12px; }}"
            )

        self._input_edit.setStyleSheet(
            f"QTextEdit#input_edit {{ background: transparent; color: {text}; border: none; font-size: 13px; font-weight: 500; selection-background-color: {accent}44; padding: 4px; }}"
        )
        self._main_result_card.setStyleSheet(
            f"QWidget#main_result_card {{ background: {card_bg}; border: 1px solid {border}; border-radius: 12px; color: {text}; padding: 6px; selection-background-color: {accent}44; }}"
        )
        self._dict_detail_card.setStyleSheet(
            f"QWidget#dict_detail_card {{ background: {input_bg}; border: 1px solid {border}; border-radius: 12px; color: {text}; padding: 6px; }}"
        )

        # 2. 快捷小按钮样式
        btn_style = (
            f"QPushButton {{ background: {input_bg}; color: {text}; border: 1px solid {border}; border-radius: 10px; font-size: 11px; font-weight: 500; }}"
            f"QPushButton:hover {{ background: {accent}35; color: {text}; border-color: {accent}; }}"
        )
        self._paste_btn.setStyleSheet(btn_style)
        self._clear_btn.setStyleSheet(btn_style)
        self._speak_src_btn.setStyleSheet(btn_style)
        self._speak_res_btn.setStyleSheet(btn_style)
        self._copy_btn.setStyleSheet(btn_style)

        # 加入生词本高亮强调按钮
        self._add_vocab_btn.setStyleSheet(
            f"QPushButton {{ background: {accent}22; color: {accent}; border: 1px solid {accent}66; border-radius: 10px; font-size: 11px; font-weight: 700; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: {accent}44; color: #FFFFFF; border-color: {accent}; }}"
        )

        self._apply_engine_tab_styles()
        self.update()

    def _apply_engine_tab_styles(self):
        """刷新 Pill Tabs 样式状态"""
        for eid, btn in self._engine_buttons.items():
            if btn.isChecked():
                btn.setStyleSheet(
                    "QPushButton { background: rgba(46, 204, 113, 0.22); color: #2ECC71; border: 1.5px solid #2ECC71; border-radius: 14px; font-size: 11px; font-weight: 700; padding: 0 8px; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: rgba(255, 255, 255, 0.06); color: #94A3B8; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 14px; font-size: 11px; font-weight: 500; padding: 0 8px; }"
                    "QPushButton:hover { background: rgba(255, 255, 255, 0.12); color: #FFFFFF; }"
                )

    # ─────────────────────────────────────────────────────────
    # 绘制与窗口拖拽
    # ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        rect_f = QRectF(self.rect().adjusted(1, 1, -1, -1))
        path.addRoundedRect(rect_f, 20, 20)

        # Instagram 极简半透明磨砂毛玻璃底色
        painter.fillPath(path, QBrush(QColor(24, 27, 34, 242)))
        painter.strokePath(path, QPen(QColor(255, 255, 255, 36), 1.5))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()
        super().mouseReleaseEvent(event)
