"""
stats_dialog.py
---------------
「未来的韩语卡片」- 学习热力图打卡看板弹窗 (Instagram 极简毛玻璃卡片)
1. 展示三大核心指标卡片：连续坚持天数、累计掌握词汇、生词消灭率
2. 近 60 天打卡活跃度热力图方块矩阵 (Heatmap View)
3. 纯净无边框质感与深浅色模式自动适配
"""

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QToolTip
)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QCursor, QFont
from typing import List, Dict, Any, Optional

from config.settings import COLORS
from core.statistics_manager import StatisticsManager


class HeatmapCell(QWidget):
    """单个热力图方块单元"""

    def __init__(self, data: Dict[str, Any], theme: str = "dark", parent=None):
        super().__init__(parent)
        self._data = data
        self._theme = theme
        self.setFixedSize(22, 22)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        d_str = data.get("date", "")
        cnt = data.get("word_count", 0)
        mast = data.get("mastered_count", 0)
        weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        wk = weekday_map[data.get("weekday", 0)] if 0 <= data.get("weekday", 0) < 7 else ""

        tooltip_txt = f"📅 {d_str} ({wk})\n📖 学习背词: {cnt} 词"
        if mast > 0:
            tooltip_txt += f"\n⭐ 掌握词汇: {mast} 词"
        if cnt == 0:
            tooltip_txt += "\n💤 今日未打卡"
        self.setToolTip(tooltip_txt)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        level = self._data.get("level", 0)

        if self._theme == "dark":
            colors = [
                QColor(39, 39, 42, 180),        # Level 0: 未打卡深灰
                QColor(16, 185, 129, 70),       # Level 1: 浅绿
                QColor(16, 185, 129, 140),      # Level 2: 中绿
                QColor(16, 185, 129, 210),      # Level 3: 翠绿
                QColor(52, 211, 153, 255),      # Level 4: 高亮荧光绿
            ]
            border_col = QColor(255, 255, 255, 25)
        else:
            colors = [
                QColor(226, 232, 240, 255),     # Level 0
                QColor(167, 243, 208, 255),     # Level 1
                QColor(110, 231, 183, 255),     # Level 2
                QColor(16, 185, 129, 255),      # Level 3
                QColor(5, 150, 105, 255),       # Level 4
            ]
            border_col = QColor(0, 0, 0, 15)

        bg_col = colors[min(level, 4)]
        painter.setBrush(QBrush(bg_col))
        painter.setPen(QPen(border_col, 1))
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 4, 4)


class StatsDialog(QDialog):
    """Instagram 极简毛玻璃打卡看板弹窗"""

    def __init__(self, stats_manager: Optional[StatisticsManager] = None, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._stats = stats_manager or StatisticsManager()
        self._theme = theme
        self.setWindowTitle("学习足迹与打卡看板")
        self.setFixedSize(480, 430)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None

        self._setup_ui()
        self.apply_theme(theme)

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        # 核心毛玻璃内衬卡片
        self._card = QWidget(self)
        self._card.setObjectName("stats_card")
        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(14)
        root_layout.addWidget(self._card)

        # ── 1. 顶部 Header ──
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel("学习足迹与打卡看板")
        self._title_label.setObjectName("stats_title")
        header.addWidget(self._title_label)

        header.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("stats_close_btn")
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.clicked.connect(self.accept)
        header.addWidget(self._close_btn)
        layout.addLayout(header)

        # ── 2. 三大核心量化指标卡片 ──
        metrics = self._stats.get_summary_metrics()
        streak = metrics.get("streak_days", 0)
        mastered = metrics.get("total_mastered", 0)
        elim_rate = metrics.get("elimination_rate", 0.0)

        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 2, 0, 2)
        cards_row.setSpacing(10)

        # 卡片 1: 连续打卡
        self._streak_box = self._create_metric_box(
            "连续打卡",
            f"{streak} 天",
            f"累计 {metrics.get('total_study_days', 0)} 天",
            "#F59E0B",
            "streak_box"
        )
        cards_row.addWidget(self._streak_box)

        # 卡片 2: 累计掌握
        self._mast_box = self._create_metric_box(
            "累计掌握",
            f"{mastered} 词",
            "词库记忆沉淀",
            "#10B981",
            "mast_box"
        )
        cards_row.addWidget(self._mast_box)

        # 卡片 3: 生词消灭率
        self._rate_box = self._create_metric_box(
            "生词消灭率",
            f"{elim_rate}%",
            f"待攻克 {metrics.get('total_unfamiliar', 0)} 词",
            "#38BDF8",
            "rate_box"
        )
        cards_row.addWidget(self._rate_box)
        layout.addLayout(cards_row)

        # ── 3. 近 60 天活跃度热力图看板 ──
        self._heatmap_container = QWidget()
        self._heatmap_container.setObjectName("heatmap_container")
        hm_layout = QVBoxLayout(self._heatmap_container)
        hm_layout.setContentsMargins(14, 12, 14, 12)
        hm_layout.setSpacing(10)

        # 热力图标题行
        hm_title_row = QHBoxLayout()
        self._hm_title = QLabel("近 60 天背词活跃度矩阵")
        self._hm_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #E2E8F0;")
        hm_title_row.addWidget(self._hm_title)
        hm_title_row.addStretch()

        self._hm_tip = QLabel("每日坚持 · 滴水穿石")
        self._hm_tip.setStyleSheet("font-size: 11px; color: #94A3B8;")
        hm_title_row.addWidget(self._hm_tip)
        hm_layout.addLayout(hm_title_row)

        # 热力图网格 (6 行 × 10 列 = 60 天)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setSpacing(5)

        heatmap_data = self._stats.get_heatmap_data(days=60)
        cols = 10
        for i, day_data in enumerate(heatmap_data):
            r = i // cols
            c = i % cols
            cell = HeatmapCell(day_data, theme=self._theme, parent=grid_widget)
            grid.addWidget(cell, r, c)

        hm_layout.addWidget(grid_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 底部图例栏
        legend_row = QHBoxLayout()
        legend_row.setContentsMargins(0, 0, 0, 0)
        legend_row.addStretch()

        legend_lbl_less = QLabel("少")
        legend_lbl_less.setStyleSheet("font-size: 10px; color: #94A3B8;")
        legend_row.addWidget(legend_lbl_less)

        for lvl in range(5):
            sample_cell = HeatmapCell({"level": lvl, "date": "图例", "word_count": lvl * 8}, theme=self._theme)
            sample_cell.setFixedSize(14, 14)
            legend_row.addWidget(sample_cell)

        legend_lbl_more = QLabel("多")
        legend_lbl_more.setStyleSheet("font-size: 10px; color: #94A3B8;")
        legend_row.addWidget(legend_lbl_more)
        hm_layout.addLayout(legend_row)

        layout.addWidget(self._heatmap_container)

        # ── 4. 底部治愈手账语录 ──
        self._quote_label = QLabel("✨ 매일매일 조금씩 발전하는 나 · 每一天的微小累积都在构筑未来的韩语直觉")
        self._quote_label.setObjectName("stats_quote")
        self._quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._quote_label)

    def _create_metric_box(self, title: str, main_val: str, sub_val: str, accent_color: str, obj_name: str) -> QWidget:
        """构建单个指标卡片"""
        box = QWidget()
        box.setObjectName(obj_name)
        b_layout = QVBoxLayout(box)
        b_layout.setContentsMargins(10, 10, 10, 10)
        b_layout.setSpacing(3)
        b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8;")
        b_layout.addWidget(t_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        v_lbl = QLabel(main_val)
        v_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {accent_color}; letter-spacing: 0.5px;")
        b_layout.addWidget(v_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        s_lbl = QLabel(sub_val)
        s_lbl.setStyleSheet("font-size: 10px; color: #64748B;")
        b_layout.addWidget(s_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        return box

    def apply_theme(self, theme: str):
        self._theme = theme
        from config.settings import THEME_CONFIGS
        if theme == "dark": theme = "seoul_night"
        elif theme == "light": theme = "cream_latte"
        cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["seoul_night"])
        is_dark = cfg.get("is_dark", True)

        bg = f"rgb({cfg['bg_color'][0]}, {cfg['bg_color'][1]}, {cfg['bg_color'][2]})"
        card_bg = cfg.get("card_bg", "#161922")
        input_bg = cfg.get("input_bg", "#1F2330")
        text_primary = cfg.get("text_primary", "#FFFFFF")
        text_sec = cfg.get("text_secondary", "#94A3B8")
        border = cfg.get("border", "rgba(255, 255, 255, 0.10)")
        close_hover = "rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.08)"

        self._card.setStyleSheet(
            f"QWidget#stats_card {{ background: {bg}; border: 1.5px solid {border}; border-radius: 16px; }}"
        )
        self._title_label.setStyleSheet(
            f"QLabel#stats_title {{ color: {text_primary}; font-size: 15px; font-weight: 700; }}"
        )
        self._close_btn.setStyleSheet(
            f"QPushButton#stats_close_btn {{ background: transparent; color: {text_sec}; border: none; border-radius: 13px; font-size: 13px; }}"
            f"QPushButton#stats_close_btn:hover {{ background: {close_hover}; color: {text_primary}; }}"
        )
        box_style = (
            f"QWidget {{ background: {card_bg}; border: 1px solid {border}; border-radius: 10px; }}"
        )
        self._streak_box.setStyleSheet(box_style)
        self._mast_box.setStyleSheet(box_style)
        self._rate_box.setStyleSheet(box_style)

        self._heatmap_container.setStyleSheet(
            f"QWidget#heatmap_container {{ background: {input_bg}; border: 1px solid {border}; border-radius: 12px; }}"
        )
        self._quote_label.setStyleSheet(
            f"QLabel#stats_quote {{ color: {text_sec}; font-size: 11px; font-style: italic; }}"
        )

    # ─────────────────────────────────────────────────────────
    # 无边框窗口拖拽支持
    # ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
