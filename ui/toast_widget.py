# -*- coding: utf-8 -*-
"""
toast_widget.py
---------------
软件内极简深色毛玻璃浮动 Toast 消息提示组件
替代原生 QMessageBox，完全静音、毫秒级浮现、2.5秒自动淡出，不阻断任何操作
"""

from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
import html


class ToastWidget(QWidget):
    """全局轻量半透明 Toast 气泡"""

    _instance = None

    @classmethod
    def show_toast(cls, parent: QWidget, text: str, icon: str = "✨", duration_ms: int = 2400):
        """静态便捷调用接口"""
        toast = cls(parent)
        toast.display(text, icon, duration_ms)
        return toast

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._anim = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        self._icon_label = QLabel("✨")
        self._icon_label.setStyleSheet("font-size: 14px; background: transparent;")
        layout.addWidget(self._icon_label)

        self._text_label = QLabel()
        self._text_label.setTextFormat(Qt.TextFormat.RichText)
        self._text_label.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600; background: transparent;")
        layout.addWidget(self._text_label)

        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 3)

        self.setStyleSheet(
            "ToastWidget { "
            "  background: rgba(22, 24, 30, 0.94); "
            "  border: 1px solid rgba(255, 255, 255, 0.16); "
            "  border-radius: 12px; "
            "}"
        )
        self.hide()

    def display(self, text: str, icon: str = "✨", duration_ms: int = 2400):
        self._icon_label.setText(icon)
        self._text_label.setText(text)
        self.adjustSize()

        # 居中显示于父窗口顶部靠下
        if self.parentWidget():
            pw = self.parentWidget().width()
            x = (pw - self.width()) // 2
            y = 52
            self.move(x, y)

        self.show()
        self.raise_()

        # 淡入
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(160)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

        # 延时淡出
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self):
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(200)
        self._anim.setStartValue(self._opacity_effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()
