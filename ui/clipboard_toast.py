# -*- coding: utf-8 -*-
"""
clipboard_toast.py
------------------
Instagram 风格剪贴板划词翻译联动悬浮微气泡 (Clipboard Smart Toast)
功能：
1. 捕获中韩文字后 150ms 平滑淡入
2. 展示原文、双语翻译与语种方向徽章
3. 快捷联动操作条：
   - 🔊 发音
   - ➕ 收入生词本 (自动写入 custom_vocab.json)
   - 🔍 深入翻译 (呼出完整翻译抽屉)
   - ✕ 忽略 / 4 秒无操作自动渐隐淡出
"""

import html
from typing import Dict, Any, Optional
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QApplication
)


class ClipboardToast(QWidget):
    """剪贴板划词双语翻译与多引擎联动悬浮微气泡"""

    add_requested = pyqtSignal(str, str, str)       # korean, meaning, pronunciation
    speak_requested = pyqtSignal(str)                # text to speak
    translate_requested = pyqtSignal(str)            # 深入翻译请求 (text)

    def __init__(self, parent=None):
        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._current_source = ""
        self._current_target = ""
        self._current_korean = ""
        self._current_meaning = ""
        self._current_pron = ""

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._anim: Optional[QPropertyAnimation] = None

        # 8 秒无操作自动淡出
        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.setSingleShot(True)
        self._auto_close_timer.setInterval(8000)
        self._auto_close_timer.timeout.connect(self.fade_out)

        self._setup_ui()

    def enterEvent(self, event):
        """鼠标移入气泡：暂停消失倒计时 (Hover to Pause) 并保持不透明"""
        self._auto_close_timer.stop()
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._opacity_effect.setOpacity(1.0)
        super().enterEvent(event)

    def mousePressEvent(self, event):
        """鼠标点击气泡内部：保持显示，杜绝点击意外消失"""
        self._auto_close_timer.stop()
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._opacity_effect.setOpacity(1.0)
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        """鼠标移出气泡：等待 3 秒后平滑渐隐淡出"""
        self._auto_close_timer.setInterval(3000)
        self._auto_close_timer.start()
        super().leaveEvent(event)

    def _setup_ui(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 220))
        shadow.setOffset(0, 4)

        self._container = QWidget(self)
        self._container.setObjectName("clip_container")
        self._container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # 1. 顶部 Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel("划词智能互译")
        self._title_label.setObjectName("clip_title")
        header.addWidget(self._title_label)

        self._badge_label = QLabel("韩 ➔ 中")
        self._badge_label.setObjectName("clip_badge")
        header.addWidget(self._badge_label)
        header.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("clip_close")
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.clicked.connect(self.fade_out)
        header.addWidget(self._close_btn)

        layout.addLayout(header)

        # 2. 原文与翻译内容区
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)

        self._kr_label = QLabel()
        self._kr_label.setObjectName("clip_kr")
        self._kr_label.setWordWrap(True)
        self._kr_label.setTextFormat(Qt.TextFormat.RichText)
        text_layout.addWidget(self._kr_label)

        self._info_label = QLabel()
        self._info_label.setObjectName("clip_info")
        self._info_label.setWordWrap(True)
        self._info_label.setTextFormat(Qt.TextFormat.RichText)
        text_layout.addWidget(self._info_label)

        layout.addLayout(text_layout)

        # 3. 快捷动作栏 (Action Bar)
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 4, 0, 0)
        action_layout.setSpacing(6)

        # 发音
        self._speak_btn = QPushButton("发音")
        self._speak_btn.setObjectName("clip_speak")
        self._speak_btn.setFixedHeight(26)
        self._speak_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._speak_btn.clicked.connect(self._on_speak_clicked)
        action_layout.addWidget(self._speak_btn)

        # 收入生词本
        self._add_btn = QPushButton("收入生词")
        self._add_btn.setObjectName("clip_add")
        self._add_btn.setFixedHeight(26)
        self._add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._add_btn.clicked.connect(self._on_add_clicked)
        action_layout.addWidget(self._add_btn)

        # 深入翻译
        self._trans_btn = QPushButton("深入翻译")
        self._trans_btn.setObjectName("clip_trans")
        self._trans_btn.setFixedHeight(26)
        self._trans_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._trans_btn.clicked.connect(self._on_deep_translate_clicked)
        action_layout.addWidget(self._trans_btn)

        layout.addLayout(action_layout)

        self._apply_styles()

    def _apply_styles(self):
        self._container.setStyleSheet(
            "QWidget#clip_container { "
            "  background: rgba(26, 29, 36, 0.95); "
            "  border: 1px solid rgba(255, 255, 255, 0.16); "
            "  border-radius: 16px; "
            "}"
        )
        self._title_label.setStyleSheet(
            "QLabel#clip_title { color: #A0A5B5; font-size: 11px; font-weight: 700; }"
        )
        self._badge_label.setStyleSheet(
            "QLabel#clip_badge { background: rgba(46, 204, 113, 0.20); color: #2ECC71; border: 1px solid rgba(46, 204, 113, 0.40); border-radius: 8px; padding: 1px 6px; font-size: 10px; font-weight: bold; }"
        )
        self._close_btn.setStyleSheet(
            "QPushButton#clip_close { background: transparent; color: #64748B; border: none; font-size: 11px; font-weight: bold; }"
            "QPushButton#clip_close:hover { color: #FFFFFF; background: rgba(235, 87, 87, 0.70); border-radius: 10px; }"
        )
        self._kr_label.setStyleSheet(
            "QLabel#clip_kr { color: #FFFFFF; font-size: 14px; font-weight: 700; }"
        )
        self._info_label.setStyleSheet(
            "QLabel#clip_info { color: #38BDF8; font-size: 12px; font-weight: 500; }"
        )

        btn_common = (
            "QPushButton { background: rgba(255, 255, 255, 0.08); color: #E2E8F0; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; font-size: 11px; font-weight: 600; padding: 0 8px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.18); color: #FFFFFF; border-color: rgba(255, 255, 255, 0.28); }"
        )
        self._speak_btn.setStyleSheet(btn_common)
        self._trans_btn.setStyleSheet(btn_common)

        self._add_btn.setStyleSheet(
            "QPushButton#clip_add { background: rgba(46, 204, 113, 0.22); color: #2ECC71; border: 1px solid rgba(46, 204, 113, 0.50); border-radius: 8px; font-size: 11px; font-weight: 700; padding: 0 8px; }"
            "QPushButton#clip_add:hover { background: rgba(46, 204, 113, 0.40); color: #FFFFFF; }"
        )

    def show_clip_data(self, clip_payload: Dict[str, Any]):
        """展示划词翻译数据 (清洗非法乱码并显示)"""
        import re
        raw_src = str(clip_payload.get("source_text", ""))
        raw_target = str(clip_payload.get("translated_text", ""))
        direction = clip_payload.get("direction", "🇰🇷 ➔ 🇨🇳")
        is_kr = clip_payload.get("is_korean", True)
        details = clip_payload.get("details", {})

        # 清洗 UTF-8 替换符与异常控制字符
        src = re.sub(r'[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw_src).strip()
        target = re.sub(r'[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw_target).strip()

        if not src:
            return

        self._current_source = src
        self._current_target = target
        self._current_korean = src if is_kr else target
        self._current_meaning = target if is_kr else src
        self._current_pron = details.get("pronunciation", "")

        self._badge_label.setText(direction)
        self._kr_label.setText(f"<div style='line-height: 1.3;'>{html.escape(src)}</div>")
        self._info_label.setText(f"<div style='line-height: 1.3;'>{html.escape(target)}</div>")

        # 重置添加按钮状态
        self._add_btn.setText("收入生词")
        self._add_btn.setEnabled(True)

        self.adjustSize()
        self._position_toast()
        self.fade_in()

    def show_clip(self, korean: str, word_info: Optional[Dict] = None):
        """兼容历史单向韩文展示"""
        info = word_info or {}
        meaning = info.get("meaning", "划词收藏生词")
        payload = {
            "source_text": korean,
            "translated_text": meaning,
            "is_korean": True,
            "direction": "🇰🇷 ➔ 🇨🇳",
            "details": info
        }
        self.show_clip_data(payload)

    def _position_toast(self):
        """将微气泡放置在屏幕右下角"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.right() - self.width() - 24
        y = geo.bottom() - self.height() - 24
        self.move(x, y)

    def fade_in(self):
        self.show()
        self.raise_()
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._auto_close_timer.setInterval(8000)
        self._opacity_effect.setOpacity(0.0)
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setDuration(150)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.start()
        self._auto_close_timer.start()

    def fade_out(self):
        self._auto_close_timer.stop()
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setDuration(150)
        self._anim.setStartValue(self._opacity_effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._anim.finished.connect(self._on_fade_out_finished)
        self._anim.start()

    def _on_fade_out_finished(self):
        if self._opacity_effect.opacity() <= 0.05:
            self.hide()

    def _on_speak_clicked(self):
        self._auto_close_timer.setInterval(8000)
        self._auto_close_timer.start()
        text_to_speak = self._current_korean or self._current_source
        if text_to_speak:
            self.speak_requested.emit(text_to_speak)

    def _on_add_clicked(self):
        self.add_requested.emit(self._current_korean, self._current_meaning, self._current_pron)
        self._add_btn.setText("✓ 已收入")
        self._add_btn.setEnabled(False)
        self._auto_close_timer.setInterval(3000)
        self._auto_close_timer.start()

    def _on_deep_translate_clicked(self):
        """请求展开完整翻译抽屉"""
        self.fade_out()
        self.translate_requested.emit(self._current_source)
