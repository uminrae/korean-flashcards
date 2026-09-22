#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩语悬浮背单词学习卡片
内置延世韩国语词库 + edge-tts 真人发音
"""

import sys
import os
import ctypes

# 确保工作目录为项目根目录（打包成 exe 后也有效）
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

# 1. 设置 Windows 独立进程 AppUserModelID，确保任务栏独立显示精美应用图标
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("future.korean.flashcards.v1")
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase, QIcon

from utils.path_helper import get_resource_path


def main():
    # 高 DPI 与高分屏清晰度支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("未来的韩语卡片")
    app.setApplicationDisplayName("未来的韩语卡片")
    app.setApplicationVersion("1.1.0")
    app.setQuitOnLastWindowClosed(False)  # 由 MainWindow.closeEvent 统一控制关闭与托盘驻留

    # 2. 设置全局应用图标
    icon_path = get_resource_path(os.path.join("assets", "app_icon.ico"))
    if not os.path.exists(icon_path):
        icon_path = get_resource_path(os.path.join("assets", "app_icon.png"))
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    # 3. 设置全局字体（优先使用系统中存在的字体）
    preferred_fonts = ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei", "Arial"]
    for font_name in preferred_fonts:
        if font_name in QFontDatabase.families():
            app.setFont(QFont(font_name, 10))
            break

    # 4. 自动加载 data/fonts/ 与 assets/fonts/ 下的所有外部自定义字体
    from core.font_manager import load_custom_fonts
    load_custom_fonts()

    # 5. 导入并启动主窗口
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
