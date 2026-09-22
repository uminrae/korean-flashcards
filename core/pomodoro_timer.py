"""
pomodoro_timer.py
-----------------
「未来的韩语卡片」- 番茄专注时钟状态机与倒计时引擎
1. 科学的 25 分钟深度专注 + 5 分钟惬意休息循环
2. 精确 QTimer 驱动，无阻塞异步信号更新
3. 支持开始、暂停、重置、跳过与自定义时长
"""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class PomodoroTimer(QObject):
    """番茄专注时钟管理器"""

    # 信号: (剩余秒数, 格式化时间 '24:59', 当前模式 'focus'/'break', 进度比 0.0~1.0)
    tick = pyqtSignal(int, str, str, float)
    state_changed = pyqtSignal(str, str) # (state: 'idle'/'running'/'paused', mode: 'focus'/'break')
    finished = pyqtSignal(str)           # (completed_mode: 'focus'/'break')

    MODE_FOCUS = "focus"
    MODE_BREAK = "break"

    STATE_IDLE = "idle"
    STATE_RUNNING = "running"
    STATE_PAUSED = "paused"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._focus_duration: int = 25 * 60  # 默认 25 分钟
        self._break_duration: int = 5 * 60   # 默认 5 分钟

        self._mode: str = self.MODE_FOCUS
        self._state: str = self.STATE_IDLE
        self._remaining: int = self._focus_duration
        self._total_duration: int = self._focus_duration

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

    def set_durations(self, focus_minutes: int, break_minutes: int):
        """设置专注与休息时长"""
        self._focus_duration = max(1, focus_minutes) * 60
        self._break_duration = max(1, break_minutes) * 60
        if self._state == self.STATE_IDLE:
            self.reset()

    def start(self):
        """开始或恢复倒计时"""
        if self._state == self.STATE_RUNNING:
            return
        if self._state == self.STATE_IDLE:
            self._total_duration = self._focus_duration if self._mode == self.MODE_FOCUS else self._break_duration
            self._remaining = self._total_duration

        self._state = self.STATE_RUNNING
        self._timer.start()
        self.state_changed.emit(self._state, self._mode)
        self._emit_tick()

    def pause(self):
        """暂停倒计时"""
        if self._state == self.STATE_RUNNING:
            self._timer.stop()
            self._state = self.STATE_PAUSED
            self.state_changed.emit(self._state, self._mode)

    def reset(self):
        """重置当前阶段"""
        self._timer.stop()
        self._state = self.STATE_IDLE
        self._total_duration = self._focus_duration if self._mode == self.MODE_FOCUS else self._break_duration
        self._remaining = self._total_duration
        self.state_changed.emit(self._state, self._mode)
        self._emit_tick()

    def toggle(self):
        """切换开始/暂停"""
        if self._state == self.STATE_RUNNING:
            self.pause()
        else:
            self.start()

    def switch_mode(self, mode: str):
        """手动切换到专注或休息模式"""
        if mode not in [self.MODE_FOCUS, self.MODE_BREAK]:
            return
        self._mode = mode
        self.reset()

    def skip_stage(self):
        """跳过当前阶段并自动进入下一阶段"""
        prev_mode = self._mode
        self._mode = self.MODE_BREAK if prev_mode == self.MODE_FOCUS else self.MODE_FOCUS
        self.reset()

    def _on_tick(self):
        """每秒倒计时触发"""
        if self._remaining > 0:
            self._remaining -= 1
            self._emit_tick()

        if self._remaining <= 0:
            self._timer.stop()
            completed_mode = self._mode
            # 自动切换到下一阶段
            self._mode = self.MODE_BREAK if completed_mode == self.MODE_FOCUS else self.MODE_FOCUS
            self._state = self.STATE_IDLE
            self._total_duration = self._focus_duration if self._mode == self.MODE_FOCUS else self._break_duration
            self._remaining = self._total_duration
            
            self.finished.emit(completed_mode)
            self.state_changed.emit(self._state, self._mode)
            self._emit_tick()

    def _emit_tick(self):
        """发送当前时间与进度"""
        minutes = self._remaining // 60
        seconds = self._remaining % 60
        formatted = f"{minutes:02d}:{seconds:02d}"
        progress = 1.0 - (self._remaining / self._total_duration) if self._total_duration > 0 else 0.0
        self.tick.emit(self._remaining, formatted, self._mode, progress)

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == self.STATE_RUNNING

    @property
    def remaining_seconds(self) -> int:
        return self._remaining

    def get_formatted_time(self) -> str:
        minutes = self._remaining // 60
        seconds = self._remaining % 60
        return f"{minutes:02d}:{seconds:02d}"
