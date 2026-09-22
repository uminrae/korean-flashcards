# ui/review_summary_dialog.py
# -*- coding: utf-8 -*-
"""
加权智能复习结算轻弹窗 (Review Summary Dialog)
- Instagram / iOS 极简高级感视觉风格
- 呈现复习总量、认识掌握数、仍需强化数与掌握率百分比
- 支持「🔄 再来一轮」与「📖 返回常规学习」
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush

from config.settings import COLORS, WINDOW_BORDER_RADIUS


class ReviewSummaryDialog(QDialog):
    """智能复习结算弹窗"""

    restart_requested = pyqtSignal()   # 触发再来一轮复习信号

    def __init__(
        self,
        total_count: int,
        mastered_count: int,
        unfamiliar_count: int,
        theme: str = "dark",
        parent=None
    ):
        super().__init__(parent)
        self.total_count = total_count
        self.mastered_count = mastered_count
        self.unfamiliar_count = unfamiliar_count
        self._theme = theme

        self.setWindowTitle("🎉 智能复习完成")
        self.setFixedSize(360, 380)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 24, 20, 20)
        main_layout.setSpacing(16)

        # 1. 顶部祝贺徽章与标题
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge_icon = QLabel("🎉")
        badge_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_icon.setStyleSheet("QLabel { font-size: 38px; }")
        header_layout.addWidget(badge_icon)

        title = QLabel("本轮智能复习已完成！")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("QLabel { color: #FFFFFF; font-size: 17px; font-weight: 700; }")
        header_layout.addWidget(title)

        subtitle = QLabel("科学加权记忆 · 温故而知新")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("QLabel { color: #94A3B8; font-size: 11px; }")
        header_layout.addWidget(subtitle)

        main_layout.addLayout(header_layout)

        # 2. 核心数据仪表卡片
        stats_box = QFrame()
        stats_box.setStyleSheet(
            "QFrame { background: rgba(255, 255, 255, 0.05); "
            "border: 1px solid rgba(255, 255, 255, 0.12); "
            "border-radius: 12px; padding: 12px; }"
        )
        stats_layout = QGridLayout(stats_box)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(10)

        # 本轮复习总数
        lbl_tot_title = QLabel("📚 复习总量")
        lbl_tot_title.setStyleSheet("QLabel { color: #CBD5E1; font-size: 12px; }")
        lbl_tot_val = QLabel(f"{self.total_count} 词")
        lbl_tot_val.setStyleSheet("QLabel { color: #60A5FA; font-size: 14px; font-weight: 700; }")
        stats_layout.addWidget(lbl_tot_title, 0, 0)
        stats_layout.addWidget(lbl_tot_val, 0, 1, Qt.AlignmentFlag.AlignRight)

        # 认识掌握
        lbl_mas_title = QLabel("✅ 认识掌握")
        lbl_mas_title.setStyleSheet("QLabel { color: #CBD5E1; font-size: 12px; }")
        lbl_mas_val = QLabel(f"{self.mastered_count} 词")
        lbl_mas_val.setStyleSheet("QLabel { color: #34D399; font-size: 14px; font-weight: 700; }")
        stats_layout.addWidget(lbl_mas_title, 1, 0)
        stats_layout.addWidget(lbl_mas_val, 1, 1, Qt.AlignmentFlag.AlignRight)

        # 仍需强化
        lbl_unf_title = QLabel("❌ 仍需强化")
        lbl_unf_title.setStyleSheet("QLabel { color: #CBD5E1; font-size: 12px; }")
        lbl_unf_val = QLabel(f"{self.unfamiliar_count} 词")
        lbl_unf_val.setStyleSheet("QLabel { color: #F87171; font-size: 14px; font-weight: 700; }")
        stats_layout.addWidget(lbl_unf_title, 2, 0)
        stats_layout.addWidget(lbl_unf_val, 2, 1, Qt.AlignmentFlag.AlignRight)

        # 掌握率计算
        accuracy = (self.mastered_count / self.total_count * 100) if self.total_count > 0 else 0
        lbl_acc_title = QLabel("📈 掌握正确率")
        lbl_acc_title.setStyleSheet("QLabel { color: #CBD5E1; font-size: 12px; font-weight: 600; }")
        lbl_acc_val = QLabel(f"{accuracy:.0f}%")
        lbl_acc_val.setStyleSheet("QLabel { color: #FBBF24; font-size: 15px; font-weight: 800; }")
        stats_layout.addWidget(lbl_acc_title, 3, 0)
        stats_layout.addWidget(lbl_acc_val, 3, 1, Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(stats_box)

        # 3. 底部操作按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        # 再来一轮
        self._btn_restart = QPushButton("🔄 再来一轮智能复习")
        self._btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_restart.setFixedHeight(36)
        self._btn_restart.setStyleSheet(
            "QPushButton { background: #3B82F6; color: #FFFFFF; border: none; "
            "border-radius: 10px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background: #2563EB; }"
        )
        self._btn_restart.clicked.connect(self._on_restart)
        btn_layout.addWidget(self._btn_restart)

        # 返回常规学习
        self._btn_close = QPushButton("📖 返回常规学习模式")
        self._btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_close.setFixedHeight(34)
        self._btn_close.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.08); color: #E2E8F0; "
            "border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 10px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.16); color: #FFFFFF; }"
        )
        self._btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self._btn_close)

        main_layout.addLayout(btn_layout)

    def _on_restart(self):
        self.restart_requested.emit()
        self.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)

        # 磨砂深灰底色与外边框
        bg_col = QColor(18, 20, 26, 242)
        border_col = QColor(255, 255, 255, 38)

        painter.fillPath(path, QBrush(bg_col))
        painter.strokePath(path, QPen(border_col, 1.2))
