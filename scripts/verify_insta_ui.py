# scripts/verify_insta_ui.py
# -*- coding: utf-8 -*-
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run():
    with open("verify_result.txt", "w", encoding="utf-8") as out:
        try:
            out.write("1. Initializing QApplication...\n")
            from PyQt6.QtWidgets import QApplication, QGraphicsDropShadowEffect
            app = QApplication.instance() or QApplication(sys.argv)

            out.write("2. Creating MainWindow...\n")
            from ui.main_window import MainWindow
            win = MainWindow()
            win.show()

            out.write("3. Checking Toolbar and Menu...\n")
            tb = win._toolbar
            assert hasattr(tb, "_more_btn"), "缺少「⋯」更多按钮"
            assert hasattr(tb, "_close_btn"), "缺少「✕」关闭按钮"
            assert hasattr(tb, "_menu"), "缺少 Instagram 风格 QMenu 菜单"
            assert hasattr(tb, "_action_shuffle"), "菜单缺少随机乱序项"
            assert hasattr(tb, "_autoplay_submenu"), "菜单缺少自动轮播子菜单"
            assert hasattr(tb, "_action_audio_first"), "菜单缺少纯听力模式项"
            assert hasattr(tb, "_action_spelling"), "菜单缺少拼写练习模式项"
            assert hasattr(tb, "_action_minibar"), "菜单缺少极简窄条项"
            assert hasattr(tb, "_action_click_through"), "菜单缺少鼠标穿透项"
            assert hasattr(tb, "_action_settings"), "菜单缺少偏好设置项"

            out.write("4. Checking CardWidget Shadows...\n")
            card = win._card
            assert isinstance(card._korean_label.graphicsEffect(), QGraphicsDropShadowEffect), "韩语大字缺少文字阴影"
            assert isinstance(card._pron_label.graphicsEffect(), QGraphicsDropShadowEffect), "读音音标缺少文字阴影"
            assert isinstance(card._chinese_label.graphicsEffect(), QGraphicsDropShadowEffect), "中文释义缺少文字阴影"
            assert isinstance(card._example_korean.graphicsEffect(), QGraphicsDropShadowEffect), "韩文例句缺少文字阴影"
            assert isinstance(card._example_chinese.graphicsEffect(), QGraphicsDropShadowEffect), "中文例句缺少文字阴影"
            assert isinstance(win._minibar_label.graphicsEffect(), QGraphicsDropShadowEffect), "Mini Bar 缺少文字阴影"

            out.write("5. Testing 0% opacity HUD mode...\n")
            win._on_bg_opacity_changed(0.0)
            assert win._bg_opacity == 0.0
            app.processEvents()
            win._next_word()
            app.processEvents()
            win._on_space()
            app.processEvents()
            win._prev_word()
            app.processEvents()

            out.write("6. Testing Action Triggers...\n")
            tb._action_shuffle.trigger()
            app.processEvents()
            tb._action_audio_first.trigger()
            app.processEvents()
            tb._action_minibar.trigger()
            app.processEvents()
            assert win._is_minibar is True
            tb._action_minibar.trigger()
            app.processEvents()
            assert win._is_minibar is False

            out.write("7. Done!\n")
            win._is_force_exit = True
            win.close()
            out.write("SUCCESS: ALL TESTS PASSED 100%\n")
            os._exit(0)
        except Exception as e:
            out.write("EXCEPTION OCCURRED:\n")
            traceback.print_exc(file=out)

if __name__ == "__main__":
    run()
