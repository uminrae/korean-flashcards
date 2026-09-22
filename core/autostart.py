# core/autostart.py
# -*- coding: utf-8 -*-
"""Windows 开机自启动注册表管理模块
支持安全读写 HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
"""

import sys
import os

REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "KoreanVocabCard"


def is_windows() -> bool:
    """判断当前操作系统是否为 Windows"""
    return sys.platform.startswith("win")


def is_autostart_enabled() -> bool:
    """检查是否已开启开机自启动"""
    if not is_windows():
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_RUN_PATH,
            0,
            winreg.KEY_READ
        )
        try:
            val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(val)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """设置或取消开机自启动"""
    if not is_windows():
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_RUN_PATH,
            0,
            winreg.KEY_SET_VALUE
        )
        try:
            if enabled:
                # 获取准确的可执行路径
                if getattr(sys, 'frozen', False):
                    # 打包成单个 exe 的情况
                    cmd = f'"{sys.executable}"'
                else:
                    # Python 源码运行情况，优先使用 pythonw 避免弹出控制台黑框
                    py_exe = sys.executable
                    if py_exe.lower().endswith("python.exe"):
                        pyw = os.path.join(os.path.dirname(py_exe), "pythonw.exe")
                        if os.path.exists(pyw):
                            py_exe = pyw
                    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
                    cmd = f'"{py_exe}" "{main_py}"'
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False
