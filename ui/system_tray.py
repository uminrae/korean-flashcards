# ui/system_tray.py
# -*- coding: utf-8 -*-
"""系统托盘（System Tray）驻留管理模块
功能：
1. 驻留系统右下角托盘，提供精美定制韩语应用图标与气泡通知
2. 托盘右键上下文菜单：【强力解除/开启鼠标穿透】、【极简窄条切换】、【显示/隐藏主卡片】、【偏好设置...】、【退出程序】
3. 单击/双击托盘图标一键切换主窗口显示与隐藏（处于穿透模式时自动强制解除穿透并置顶唤起）
"""

import os
import sys

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from config.settings import COLORS
from utils.path_helper import get_resource_path


def create_default_tray_icon() -> QIcon:
    """优先加载 assets/app_icon.ico 或 assets/app_icon.png，若无则动态绘制精致托盘图标"""
    ico_path = get_resource_path(os.path.join("assets", "app_icon.ico"))
    if os.path.exists(ico_path):
        return QIcon(ico_path)

    png_path = get_resource_path(os.path.join("assets", "app_icon.png"))
    if os.path.exists(png_path):
        return QIcon(png_path)

    # 动态绘制备选图标
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 1. 圆润莫兰迪青蓝背景
    painter.setBrush(QColor("#4A7A96"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 16, 16)

    # 2. 居中绘制韩文 "한" (Han)
    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Malgun Gothic", 28, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "한")
    painter.end()

    return QIcon(pixmap)


class AppSystemTray(QObject):
    """系统托盘驻留管理"""

    toggle_window_requested = pyqtSignal()
    toggle_click_through_requested = pyqtSignal()
    toggle_minibar_requested = pyqtSignal()
    toggle_clip_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    exit_app_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = "dark"
        self._is_window_visible = True
        self._is_click_through = False
        self._is_minibar = False

        self._tray_icon = QSystemTrayIcon(parent if parent else self)
        self._icon = create_default_tray_icon()
        self._tray_icon.setIcon(self._icon)
        self._tray_icon.setToolTip("🇰🇷 未来的韩语卡片 (双击或单击切换显示)")

        self._setup_menu()
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _setup_menu(self):
        self._menu = QMenu()
        self._apply_menu_theme(self._theme)

        # 1. 穿透模式开关（置顶，支持强力解除穿透）
        self._action_click_through = self._menu.addAction("鼠标穿透模式 (Ctrl+L)")
        self._action_click_through.triggered.connect(self.toggle_click_through_requested.emit)

        # 2. 极简磁吸条模式开关 (Mini Ticker)
        self._action_minibar = self._menu.addAction("屏幕边缘极简磁吸条 (F2)")
        self._action_minibar.triggered.connect(self.toggle_minibar_requested.emit)

        # 3. 剪贴板划词监听开关
        self._action_clip = self._menu.addAction("剪贴板划词监听 (Ctrl+Shift+C)")
        self._action_clip.setCheckable(True)
        self._action_clip.setChecked(True)
        self._action_clip.triggered.connect(self.toggle_clip_requested.emit)

        self._menu.addSeparator()

        # 4. 显示/隐藏主卡片
        self._action_toggle = self._menu.addAction("隐藏主卡片 (Ctrl+H)")
        self._action_toggle.triggered.connect(self.toggle_window_requested.emit)

        # 5. 偏好设置
        self._action_settings = self._menu.addAction("偏好设置与词库管理 (Ctrl+,)")
        self._action_settings.triggered.connect(self.open_settings_requested.emit)

        self._menu.addSeparator()

        # 6. 退出程序
        self._action_exit = self._menu.addAction("退出程序")
        self._action_exit.triggered.connect(self.exit_app_requested.emit)

        self._tray_icon.setContextMenu(self._menu)

    def _apply_menu_theme(self, theme: str):
        c = COLORS
        if theme == "dark":
            bg = c["dark_card"]
            text = c["dark_text_primary"]
            border = c["dark_border"]
            accent = c["dark_accent"]
        else:
            bg = c["light_card"]
            text = c["light_text_primary"]
            border = c["light_border"]
            accent = c["light_accent"]

        self._menu.setStyleSheet(f"""
            QMenu {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px;
                font-size: 12px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {accent}55;
                color: {text};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {border};
                margin: 4px 6px;
            }}
        """)

    def apply_theme(self, theme: str):
        self._theme = theme
        self._apply_menu_theme(theme)

    def update_action_text(self, is_window_visible: bool):
        """根据当前主窗口可见状态更新菜单文本"""
        self._is_window_visible = is_window_visible
        if is_window_visible:
            self._action_toggle.setText("隐藏主卡片 (Ctrl+H)")
        else:
            self._action_toggle.setText("显示主卡片 (Ctrl+H)")

    def update_click_through_state(self, is_click_through: bool):
        """根据鼠标穿透状态动态更新托盘菜单与提示语"""
        self._is_click_through = is_click_through
        if is_click_through:
            self._action_click_through.setText("退出鼠标穿透 (恢复正常交互)")
            self._tray_icon.setToolTip("未来的韩语卡片 [鼠标穿透锁定中 - 单击托盘解除]")
        else:
            self._action_click_through.setText("开启鼠标穿透 (Ctrl+L)")
            self._tray_icon.setToolTip("未来的韩语卡片 (双击或单击切换显示)")

    def update_minibar_state(self, is_minibar: bool):
        """根据极简窄条状态更新托盘菜单文本"""
        self._is_minibar = is_minibar
        if is_minibar:
            self._action_minibar.setText("还原大卡片模式 (F2)")
        else:
            self._action_minibar.setText("屏幕边缘极简磁吸条 (F2)")


    def show(self):
        self._tray_icon.show()

    def hide(self):
        self._tray_icon.hide()

    def is_visible(self) -> bool:
        return self._tray_icon.isVisible()

    def show_message(self, title: str, message: str, msecs: int = 3000):
        """弹出系统托盘气泡通知"""
        if self._tray_icon.isSystemTrayAvailable():
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, msecs)

    def _on_tray_activated(self, reason):
        # 单击或双击托盘图标切换窗口显示（由 MainWindow 处理穿透兜底与显示切换）
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick
        ):
            self.toggle_window_requested.emit()
