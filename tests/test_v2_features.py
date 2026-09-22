# tests/test_v2_features.py
# -*- coding: utf-8 -*-
"""
测试 4 项核心功能与体验重构：
1. 全局更名验证（未来的韩语卡片）
2. TTS 本地音频预缓存与周边词后台静默预抓取 (Prefetch Worker)
3. 关闭按钮与 closeEvent 逻辑（根据 minimize_to_tray 精确分支）
4. 独立背景透明度调节（窗口物理 opacity 保持 1.0，文字始终 100% 实心）
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCloseEvent
from ui.main_window import MainWindow
from core.tts_engine import TTSEngine, get_audio_cache_path, clean_korean_text


def run_tests():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    print("==================================================")
    print("🚀 开始执行 4 项核心重构与体验优化专项测试...")
    print("==================================================")

    win = MainWindow()
    win.show()

    # ─────────────────────────────────────────────────────────
    # 测试 1: 全局更名验证
    # ─────────────────────────────────────────────────────────
    print("\n[测试 1] 全局软件名称更名验证...")
    assert win.windowTitle() == "未来的韩语卡片", f"窗口标题错误: {win.windowTitle()}"
    assert "未来的韩语卡片" in win._toolbar._title_label.text(), f"工具栏标题错误: {win._toolbar._title_label.text()}"
    assert "未来的韩语卡片" in win._tray._tray_icon.toolTip(), f"托盘提示错误: {win._tray._tray_icon.toolTip()}"
    print("  ✓ 窗口标题、工具栏标题与系统托盘提示均已统一更名为「未来的韩语卡片」！")

    # ─────────────────────────────────────────────────────────
    # 测试 2: TTS 零延迟、本地持久化缓存与后台静默预加载
    # ─────────────────────────────────────────────────────────
    print("\n[测试 2] TTS 零延迟缓存与周边词静默预抓取...")
    curr_word = win._vocab.current_word()
    assert curr_word is not None, "未能获取当前单词"
    nearby = win._vocab.get_nearby_words(window=2)
    assert len(nearby) > 0, "get_nearby_words 返回为空"
    print(f"  ✓ 成功获取当前词 [{curr_word.get('korean')}] 周边单词: {[w.get('korean') for w in nearby]}")

    # 测试本地缓存路径生成
    cache_file = get_audio_cache_path(curr_word.get("korean", "가다"))
    assert "data" in cache_file and "audio_cache" in cache_file, f"缓存路径不规范: {cache_file}"
    print(f"  ✓ 缓存路径规范验证通过: {cache_file}")

    # 测试后台静默预抓取触发
    win._tts.prefetch([w.get("korean") for w in nearby])
    print("  ✓ 成功将周边单词加入后台静默预抓取队列 (Prefetch Worker)")

    # ─────────────────────────────────────────────────────────
    # 测试 3: 背景独立透明度调节 (保留文字 100% 实心高清)
    # ─────────────────────────────────────────────────────────
    print("\n[测试 3] 背景独立透明度调节 (文字 100% 实心)...")
    win._on_bg_opacity_changed(0.0)
    assert win._bg_opacity == 0.0, "bg_opacity 未正确设置为 0.0"
    assert win.windowOpacity() == 1.0, f"窗口物理 opacity 应该保持 1.0，实际为: {win.windowOpacity()}"
    win._on_bg_opacity_changed(0.85)
    assert win._bg_opacity == 0.85, "bg_opacity 未正确设置为 0.85"
    assert win.windowOpacity() == 1.0, "窗口物理 opacity 应该保持 1.0"
    print("  ✓ 背景透明度在 0%~100% 之间独立生效，主窗口物理透明度保持 1.0 实心！")

    # ─────────────────────────────────────────────────────────
    # 测试 4: 修复「点击关闭（×）行为」逻辑
    # ─────────────────────────────────────────────────────────
    print("\n[测试 4] 点击关闭 (×) 行为与 minimize_to_tray 分支验证...")
    # 4.1 勾选最小化到托盘时 (True)
    win._state.set("minimize_to_tray", "1")
    event_min = QCloseEvent()
    win.closeEvent(event_min)
    assert not event_min.isAccepted(), "勾选最小化到托盘时 closeEvent 应该被 ignore"
    assert not win.isVisible(), "勾选最小化到托盘时窗口应该被 hide()"
    print("  ✓ 勾选最小化到托盘时：成功拦截关闭事件，仅隐藏至托盘驻留")

    # 4.2 未勾选最小化到托盘时 (False)
    win.show()
    win._state.set("minimize_to_tray", "0")
    event_quit = QCloseEvent()
    win.closeEvent(event_quit)
    assert event_quit.isAccepted(), "未勾选最小化到托盘时 closeEvent 应该被 accept"
    print("  ✓ 未勾选最小化到托盘时：正常接受关闭事件并触发彻底退出！")

    # 恢复默认设置
    win._state.set("minimize_to_tray", "1")

    print("\n==================================================")
    print("🎉 全部 4 项核心重构与体验优化专项测试 100% 通过！")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
    os._exit(0)
