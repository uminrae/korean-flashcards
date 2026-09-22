# -*- coding: utf-8 -*-
"""
tests/test_interactive_modes.py
测试极简窄条模式与鼠标穿透死锁强力解除功能
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))

from ui.main_window import MainWindow

def test_minibar_and_click_through():
    app = QApplication.instance() or QApplication(sys.argv)
    
    win = MainWindow()
    win.show()
    
    print("=== 测试 1: 极简窄条模式 (Mini Bar) 切换与控件隐藏 ===")
    # 初始状态：大卡片模式
    assert not win._is_minibar, "初始状态不应是 minibar"
    assert win._toolbar.isVisible(), "大卡片模式下工具栏应可见"
    assert win._card.isVisible(), "大卡片模式下卡片应可见"
    assert win._bottom_bar_widget.isVisible(), "大卡片模式下底部状态条应可见"
    assert win._today_badge.isVisible(), "大卡片模式下今日已学徽章应可见"
    assert not win._minibar_widget.isVisible(), "大卡片模式下 Mini Bar 应隐藏"
    
    # 切换进入极简窄条模式
    win._toggle_minibar()
    assert win._is_minibar, "应进入 minibar 模式"
    assert win._minibar_widget.isVisible(), "Mini Bar 控件应可见"
    assert not win._toolbar.isVisible(), "窄条模式下工具栏必须隐藏"
    assert not win._card.isVisible(), "窄条模式下卡片必须隐藏"
    assert not win._nav_bar.isVisible(), "窄条模式下导航栏必须隐藏"
    assert not win._bottom_bar_widget.isVisible(), "窄条模式下底部栏必须隐藏"
    assert not win._today_badge.isVisible(), "窄条模式下今日已学必须隐藏（无粉框残留）"
    assert not win._size_grip.isVisible(), "窄条模式下缩放手柄必须隐藏"
    assert win.height() == win._minibar_height, f"窗口高度应为 {win._minibar_height}"
    print("✓ 极简窄条模式进入成功，所有多余控件均已彻底隐藏，无溢出与残留")

    # 切换退出极简窄条模式
    win._toggle_minibar()
    assert not win._is_minibar, "应退出 minibar 模式"
    assert not win._minibar_widget.isVisible(), "退出后 Mini Bar 应隐藏"
    assert win._toolbar.isVisible(), "退出后工具栏应恢复显示"
    assert win._card.isVisible(), "退出后卡片应恢复显示"
    assert win._bottom_bar_widget.isVisible(), "退出后底部栏应恢复显示"
    assert win._today_badge.isVisible(), "退出后今日已学徽章应恢复显示"
    assert win.height() >= 220, f"窗口高度应恢复为大卡片高度 (实际: {win.height()})"
    print("✓ 极简窄条模式退出成功，大卡片完整恢复")

    print("\n=== 测试 2: 鼠标穿透模式 (Click-Through) 与托盘强力解除 ===")
    # 初始状态
    assert not win._is_click_through, "初始不应处于穿透状态"
    flags = win.windowFlags()
    assert not (flags & Qt.WindowType.WindowTransparentForInput), "初始不应有 WindowTransparentForInput"

    # 开启穿透模式
    win._toggle_click_through()
    assert win._is_click_through, "应处于穿透状态"
    flags = win.windowFlags()
    assert (flags & Qt.WindowType.WindowTransparentForInput), "窗口 Flag 必须包含 WindowTransparentForInput"
    assert win._tray._is_click_through, "托盘状态必须同步为穿透中"
    print("✓ 鼠标穿透已开启，Flag 正确挂载")

    # 模拟用户点击系统托盘图标（触发 _on_tray_toggle_window 强力解除穿透）
    win._on_tray_toggle_window()
    assert not win._is_click_through, "点击托盘后必须强力解除穿透状态"
    flags = win.windowFlags()
    assert not (flags & Qt.WindowType.WindowTransparentForInput), "窗口 Flag 必须已移除 WindowTransparentForInput"
    assert not win._tray._is_click_through, "托盘状态必须同步为已解除"
    assert win.isVisible(), "主窗口必须处于显示置顶状态"
    print("✓ 托盘点击成功解除鼠标穿透死锁，窗口交互已恢复")

    win._is_force_exit = True
    win.close()
    print("\n🎉 全部交互模式测试通过！")

if __name__ == '__main__':
    test_minibar_and_click_through()
    os._exit(0)
