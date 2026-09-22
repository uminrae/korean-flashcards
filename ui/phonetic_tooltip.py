# -*- coding: utf-8 -*-
"""
phonetic_tooltip.py
-------------------
Instagram / macOS 极简无边框半透明音变解析气泡卡片
取代传统系统 QMessageBox，150ms 优雅淡入，完全静音，支持点击外部或 ESC 自动淡出
"""

from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui import QColor, QCursor, QKeyEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
import html


class PhoneticTooltip(QWidget):
    """极简半透明磨砂音变规则解析气泡卡片"""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._anim: QPropertyAnimation = None
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._setup_ui()

    def _setup_ui(self):
        # 整体卡片阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 4)

        # 外层包装容器
        self._container = QWidget(self)
        self._container.setObjectName("tooltip_container")
        self._container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.addWidget(self._container)

        card_layout = QVBoxLayout(self._container)
        card_layout.setContentsMargins(16, 12, 16, 14)
        card_layout.setSpacing(8)

        # 1. 顶部标题栏
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 2)

        self._title_label = QLabel("⚡ 音变解析")
        self._title_label.setObjectName("tooltip_title")
        header.addWidget(self._title_label)

        header.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("tooltip_close_btn")
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.clicked.connect(self.fade_out)
        header.addWidget(self._close_btn)

        card_layout.addLayout(header)

        # 2. 内容区域
        self._content_label = QLabel()
        self._content_label.setObjectName("tooltip_content")
        self._content_label.setWordWrap(True)
        self._content_label.setTextFormat(Qt.TextFormat.RichText)
        card_layout.addWidget(self._content_label)

        # 3. 底部小提示
        self._hint_label = QLabel("点击外部或按 ESC 即可关闭")
        self._hint_label.setObjectName("tooltip_hint")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        card_layout.addWidget(self._hint_label)

        self._apply_styles()

    def _apply_styles(self):
        self._container.setStyleSheet(
            "QWidget#tooltip_container { "
            "  background: rgba(26, 29, 36, 0.96); "
            "  border: 1px solid rgba(255, 255, 255, 0.14); "
            "  border-radius: 14px; "
            "}"
        )
        self._title_label.setStyleSheet(
            "QLabel#tooltip_title { color: #A78BFA; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; }"
        )
        self._close_btn.setStyleSheet(
            "QPushButton#tooltip_close_btn { background: rgba(255, 255, 255, 0.08); color: #94A3B8; "
            "border: none; border-radius: 10px; font-size: 11px; font-weight: bold; } "
            "QPushButton#tooltip_close_btn:hover { background: rgba(235, 87, 87, 0.85); color: #FFFFFF; }"
        )
        self._content_label.setStyleSheet(
            "QLabel#tooltip_content { color: #E2E8F0; font-size: 12px; line-height: 1.5; }"
        )
        self._hint_label.setStyleSheet(
            "QLabel#tooltip_hint { color: #64748B; font-size: 10px; font-weight: 500; padding-top: 2px; }"
        )

    def show_mutation(self, korean: str, mutation_info: dict, target_widget: QWidget = None):
        """显示音变规则气泡并根据目标控件精准定位"""
        if not mutation_info:
            return

        r_tag = mutation_info.get("rule_tag", "[音变]")
        r_name = mutation_info.get("rule_name", "音变")
        actual_p = mutation_info.get("actual_pron", korean)
        explanation = mutation_info.get("explanation", "实际发音与韩文字形存在音变规则变化。")

        self._title_label.setText(f"⚡ 音变解析 · {html.escape(r_tag)}")

        content_html = (
            f"<div style='line-height: 1.6; font-size: 12px;'>"
            f"📝 <b>书写形态</b>: <span style='color: #FFFFFF; font-weight: 600;'>{html.escape(korean)}</span><br>"
            f"🗣️ <b>标准读音</b>: <span style='color: #2ECC71; font-weight: 700; font-size: 13px;'>[{html.escape(actual_p)}]</span><br>"
            f"📖 <b>音变原理</b>:<br>"
            f"<span style='color: #CBD5E1; font-size: 11.5px;'>{html.escape(explanation)}</span>"
            f"</div>"
        )
        self._content_label.setText(content_html)
        self.adjustSize()

        # 计算弹出位置
        if target_widget and target_widget.isVisible():
            global_pos = target_widget.mapToGlobal(QPoint(0, target_widget.height() + 6))
            # 居中对齐目标控件
            x = global_pos.x() + (target_widget.width() - self.width()) // 2
            y = global_pos.y()
            self.move(x, y)
        else:
            cursor_pos = QCursor.pos()
            self.move(cursor_pos.x() - self.width() // 2, cursor_pos.y() + 10)

        self.fade_in()

    def fade_in(self):
        """150ms 丝滑淡入动画"""
        self.show()
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(150)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def fade_out(self):
        """120ms 丝滑淡出动画"""
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(120)
        self._anim.setStartValue(self._opacity_effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self.hide)
        self._anim.start()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.fade_out()
            event.accept()
            return
        super().keyPressEvent(event)
