"""
pomodoro_dialog.py
------------------
「未来的韩语卡片」- Instagram 极简毛玻璃白噪音伴学与番茄专注时钟控制面板
1. 白噪音切换与音量微调
2. 大号发光倒计时与专注/休息状态流转
3. 极简黑曜石深色毛玻璃卡片质感
"""

from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QCursor, QColor, QFont

from core.ambience_player import AmbiencePlayer, AMBIENCE_TYPES
from core.pomodoro_timer import PomodoroTimer


class PomodoroDialog(QDialog):
    """Instagram 极简毛玻璃白噪音伴学与番茄专注时钟弹窗"""

    def __init__(self, timer: PomodoroTimer, player: AmbiencePlayer, parent=None):
        super().__init__(parent)
        self._timer = timer
        self._player = player
        self._drag_pos: Optional[QPoint] = None

        self._setup_ui()
        self._connect_signals()
        self._refresh_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(360, 480)

        # 主背景容器
        self._card = QWidget(self)
        self._card.setObjectName("pomodoro_card")
        self._card.setGeometry(10, 10, 340, 460)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 220))
        shadow.setOffset(0, 4)
        self._card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # ── 顶部栏 ──
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel("专注伴学与番茄时钟")
        title_lbl.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 700; letter-spacing: 0.5px;")
        top_row.addWidget(title_lbl)

        top_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.10); color: #CBD5E1; border: none; border-radius: 12px; font-size: 11px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.65); color: #FFFFFF; }"
        )
        close_btn.clicked.connect(self.close)
        top_row.addWidget(close_btn)
        layout.addLayout(top_row)

        # ── 模块 1：本地白噪音环境音 ──
        sec1_title = QLabel("伴学白噪音")
        sec1_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        layout.addWidget(sec1_title)

        # 白噪音 4 选 1 胶囊按钮组
        self._ambience_btns = {}
        amb_layout = QHBoxLayout()
        amb_layout.setSpacing(6)

        amb_configs = [
            ("rain", "小雨"),
            ("cafe", "咖啡馆"),
            ("white", "白噪"),
            ("none", "静音"),
        ]
        for amb_type, label in amb_configs:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked, t=amb_type: self._on_ambience_selected(t))
            amb_layout.addWidget(btn)
            self._ambience_btns[amb_type] = btn
        layout.addLayout(amb_layout)

        # 音量调节滑块行
        vol_layout = QHBoxLayout()
        vol_layout.setSpacing(8)

        self._vol_label = QLabel("音量 60%")
        self._vol_label.setFixedWidth(56)
        self._vol_label.setStyleSheet("color: #CBD5E1; font-size: 11px; font-weight: 600;")
        vol_layout.addWidget(self._vol_label)

        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(int(self._player.get_volume() * 100))
        self._vol_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 4px; background: rgba(255, 255, 255, 0.18); border-radius: 2px; }"
            "QSlider::sub-page:horizontal { background: #10B981; border-radius: 2px; }"
            "QSlider::handle:horizontal { width: 14px; height: 14px; margin: -5px 0; background: #FFFFFF; border-radius: 7px; }"
        )
        self._vol_slider.valueChanged.connect(self._on_volume_changed)
        vol_layout.addWidget(self._vol_slider)
        layout.addLayout(vol_layout)

        # 分割线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: rgba(255, 255, 255, 0.12); max-height: 1px;")
        layout.addWidget(sep)

        # ── 模块 2：番茄专注时钟 ──
        sec2_title = QLabel("科学番茄时钟")
        sec2_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        layout.addWidget(sec2_title)

        # 快捷模式选择行
        mode_btn_layout = QHBoxLayout()
        mode_btn_layout.setSpacing(6)

        self._mode_focus_btn = QPushButton("25m 专注")
        self._mode_focus_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._mode_focus_btn.setFixedHeight(26)
        self._mode_focus_btn.clicked.connect(lambda: self._timer.switch_mode(PomodoroTimer.MODE_FOCUS))
        mode_btn_layout.addWidget(self._mode_focus_btn)

        self._mode_break_btn = QPushButton("5m 休息")
        self._mode_break_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._mode_break_btn.setFixedHeight(26)
        self._mode_break_btn.clicked.connect(lambda: self._timer.switch_mode(PomodoroTimer.MODE_BREAK))
        mode_btn_layout.addWidget(self._mode_break_btn)

        layout.addLayout(mode_btn_layout)

        # 核心大号倒计时显示
        self._time_display = QLabel("25:00")
        self._time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_display.setStyleSheet(
            "color: #FFFFFF; font-size: 46px; font-weight: 800; font-family: 'Segoe UI', sans-serif; letter-spacing: 2px;"
        )
        time_shadow = QGraphicsDropShadowEffect(self)
        time_shadow.setBlurRadius(16)
        time_shadow.setColor(QColor(239, 68, 68, 180))
        time_shadow.setOffset(0, 2)
        self._time_display.setGraphicsEffect(time_shadow)
        layout.addWidget(self._time_display)

        # 状态指示微胶囊
        self._status_badge = QLabel("深度专注中")
        self._status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_badge.setFixedHeight(22)
        layout.addWidget(self._status_badge, alignment=Qt.AlignmentFlag.AlignCenter)

        # 动作控制按钮
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self._start_btn = QPushButton("开始专注")
        self._start_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._start_btn.setFixedHeight(34)
        self._start_btn.clicked.connect(self._timer.toggle)
        ctrl_layout.addWidget(self._start_btn, stretch=2)

        self._reset_btn = QPushButton("重置")
        self._reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._reset_btn.setFixedHeight(34)
        self._reset_btn.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.10); color: #E2E8F0; border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 8px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.20); }"
        )
        self._reset_btn.clicked.connect(self._timer.reset)
        ctrl_layout.addWidget(self._reset_btn, stretch=1)

        self._skip_btn = QPushButton("跳过")
        self._skip_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._skip_btn.setFixedHeight(34)
        self._skip_btn.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.10); color: #E2E8F0; border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 8px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.20); }"
        )
        self._skip_btn.clicked.connect(self._timer.skip_stage)
        ctrl_layout.addWidget(self._skip_btn, stretch=1)

        layout.addLayout(ctrl_layout)

        # 弹窗整体 QSS
        self._card.setStyleSheet(
            "QWidget#pomodoro_card { "
            "  background: rgba(18, 20, 28, 0.94); "
            "  border: 1px solid rgba(255, 255, 255, 0.20); "
            "  border-radius: 16px; "
            "}"
        )

    def _connect_signals(self):
        self._timer.tick.connect(self._on_timer_tick)
        self._timer.state_changed.connect(self._on_timer_state_changed)
        self._timer.finished.connect(self._on_timer_finished)

    def _on_ambience_selected(self, amb_type: str):
        self._player.set_ambience(amb_type)
        self._update_ambience_buttons()

    def _on_volume_changed(self, val: int):
        v = val / 100.0
        self._player.set_volume(v)
        self._vol_label.setText(f"音量 {val}%")

    def _on_timer_tick(self, rem_sec: int, formatted: str, mode: str, prog: float):
        self._time_display.setText(formatted)

    def _on_timer_state_changed(self, state: str, mode: str):
        self._refresh_timer_ui()

    def _on_timer_finished(self, completed_mode: str):
        self._player.play_chime()
        self._refresh_timer_ui()

    def _update_ambience_buttons(self):
        cur = self._player.get_current_type()
        for t, btn in self._ambience_btns.items():
            if t == cur:
                btn.setStyleSheet(
                    "QPushButton { background: rgba(16, 185, 129, 0.35); color: #6EE7B7; "
                    "border: 1.5px solid #10B981; border-radius: 8px; font-size: 11px; font-weight: 700; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: rgba(255, 255, 255, 0.08); color: #CBD5E1; "
                    "border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 8px; font-size: 11px; font-weight: 500; }"
                    "QPushButton:hover { background: rgba(255, 255, 255, 0.18); color: #FFFFFF; }"
                )

    def _refresh_timer_ui(self):
        mode = self._timer.mode
        state = self._timer.state
        self._time_display.setText(self._timer.get_formatted_time())

        # 模式按钮高亮
        if mode == PomodoroTimer.MODE_FOCUS:
            self._mode_focus_btn.setStyleSheet(
                "QPushButton { background: rgba(239, 68, 68, 0.35); color: #FCA5A5; border: 1.5px solid #EF4444; border-radius: 8px; font-size: 11px; font-weight: 700; }"
            )
            self._mode_break_btn.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.08); color: #94A3B8; border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 8px; font-size: 11px; font-weight: 500; }"
            )
            effect = self._time_display.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                effect.setColor(QColor(239, 68, 68, 200))
        else:
            self._mode_focus_btn.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.08); color: #94A3B8; border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 8px; font-size: 11px; font-weight: 500; }"
            )
            self._mode_break_btn.setStyleSheet(
                "QPushButton { background: rgba(16, 185, 129, 0.35); color: #6EE7B7; border: 1.5px solid #10B981; border-radius: 8px; font-size: 11px; font-weight: 700; }"
            )
            effect = self._time_display.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                effect.setColor(QColor(16, 185, 129, 200))

        # 状态微胶囊
        if state == PomodoroTimer.STATE_RUNNING:
            if mode == PomodoroTimer.MODE_FOCUS:
                self._status_badge.setText("深度专注进行中...")
                self._status_badge.setStyleSheet(
                    "QLabel { background: rgba(239, 68, 68, 0.20); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.45); border-radius: 11px; padding: 1px 12px; font-size: 11px; font-weight: 700; }"
                )
                self._start_btn.setText("暂停专注")
                self._start_btn.setStyleSheet(
                    "QPushButton { background: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 700; font-size: 13px; }"
                    "QPushButton:hover { background: #DC2626; }"
                )
            else:
                self._status_badge.setText("惬意休息进行中...")
                self._status_badge.setStyleSheet(
                    "QLabel { background: rgba(16, 185, 129, 0.20); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.45); border-radius: 11px; padding: 1px 12px; font-size: 11px; font-weight: 700; }"
                )
                self._start_btn.setText("暂停休息")
                self._start_btn.setStyleSheet(
                    "QPushButton { background: #10B981; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 700; font-size: 13px; }"
                    "QPushButton:hover { background: #059669; }"
                )
        elif state == PomodoroTimer.STATE_PAUSED:
            self._status_badge.setText("倒计时已暂停")
            self._status_badge.setStyleSheet(
                "QLabel { background: rgba(251, 191, 36, 0.20); color: #FCD34D; border: 1px solid rgba(251, 191, 36, 0.45); border-radius: 11px; padding: 1px 12px; font-size: 11px; font-weight: 700; }"
            )
            self._start_btn.setText("继续倒计时")
            self._start_btn.setStyleSheet(
                "QPushButton { background: #F59E0B; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 700; font-size: 13px; }"
                "QPushButton:hover { background: #D97706; }"
            )
        else:
            txt = "准备开始 25m 专注" if mode == PomodoroTimer.MODE_FOCUS else "准备开始 5m 休息"
            self._status_badge.setText(txt)
            self._status_badge.setStyleSheet(
                "QLabel { background: rgba(255, 255, 255, 0.08); color: #94A3B8; border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 11px; padding: 1px 12px; font-size: 11px; font-weight: 600; }"
            )
            start_txt = "开始专注" if mode == PomodoroTimer.MODE_FOCUS else "开始休息"
            self._start_btn.setText(start_txt)
            self._start_btn.setStyleSheet(
                "QPushButton { background: #3B82F6; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 700; font-size: 13px; }"
                "QPushButton:hover { background: #2563EB; }"
            )

    def _refresh_ui(self):
        self._update_ambience_buttons()
        self._refresh_timer_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
