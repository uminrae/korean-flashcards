# core/boss_key.py
# -*- coding: utf-8 -*-
"""Windows 全局老板键（Boss Key）模块
支持系统级全局热键（默认 Ctrl + ~），无论焦点在任何应用，按下时均能瞬间隐藏/呼出主悬浮窗
"""

import sys
from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal, QCoreApplication


class NativeBossKeyEventFilter(QAbstractNativeEventFilter):
    """Windows 原生全局消息过滤器，拦截 WM_HOTKEY 消息"""

    def __init__(self, hotkey_id: int, callback):
        super().__init__()
        self._hotkey_id = hotkey_id
        self._callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
            try:
                import ctypes
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(message.__int__())
                if msg.message == 0x0312:  # WM_HOTKEY
                    if msg.wParam == self._hotkey_id:
                        self._callback()
                        return True, 0
            except Exception:
                pass
        return False, 0


class BossKeyManager(QObject):
    """全局老板键管理器"""

    triggered = pyqtSignal()

    WM_HOTKEY = 0x0312
    MOD_CONTROL = 0x0002
    MOD_NOREPEAT = 0x4000
    VK_OEM_3 = 0xC0  # ~ ` 键
    HOTKEY_ID = 9527

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_registered = False
        self._filter = None

    def start(self) -> bool:
        """注册系统全局老板键 (Ctrl + ~)"""
        if not sys.platform.startswith("win"):
            return False
        if self._is_registered:
            return True

        try:
            import ctypes
            user32 = ctypes.windll.user32
            # 注册 Ctrl + ~ (VK_OEM_3)
            res = user32.RegisterHotKey(
                None,
                self.HOTKEY_ID,
                self.MOD_CONTROL | self.MOD_NOREPEAT,
                self.VK_OEM_3
            )
            if res:
                self._is_registered = True
                self._filter = NativeBossKeyEventFilter(self.HOTKEY_ID, self._on_triggered)
                app = QCoreApplication.instance()
                if app:
                    app.installNativeEventFilter(self._filter)
                return True
            return False
        except Exception:
            return False

    def stop(self):
        """注销全局热键"""
        if self._is_registered and sys.platform.startswith("win"):
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.UnregisterHotKey(None, self.HOTKEY_ID)
                if self._filter:
                    app = QCoreApplication.instance()
                    if app:
                        app.removeNativeEventFilter(self._filter)
                    self._filter = None
                self._is_registered = False
            except Exception:
                pass

    def _on_triggered(self):
        self.triggered.emit()
