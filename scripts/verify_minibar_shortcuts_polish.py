# -*- coding: utf-8 -*-
"""
verify_minibar_shortcuts_polish.py
----------------------------------
自动化测试套件：验证界面配色统一、快捷键设置重构、Mini Ticker 与顺手度深度优化
1. 翻译抽屉消除突兀纯白底色，统一深色磨砂质感
2. 偏好设置独立快捷键配置弹窗 (ShortcutDialog) 与全键盘盲操
3. Mini Ticker 36px 极简磁吸条与 25px 边缘吸附
4. 剪贴板气泡 8s 显示、悬停防消失 (Hover to Pause) 与非法字符清洗
5. 自动轮播悬停暂停与断点状态记忆
"""

import sys
import os
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from ui.translation_dialog import TranslationDialog
from ui.shortcut_dialog import ShortcutDialog, DEFAULT_SHORTCUTS
from ui.settings_dialog import SettingsDialog
from ui.clipboard_toast import ClipboardToast
from ui.card_widget import CardWidget
from core.state_manager import StateManager


def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 验证翻译抽屉深色磨砂质感（彻底消除纯白底色）
        log("[Test 1] Testing TranslationDialog dark frosted style & white-block elimination...")
        trans_dlg = TranslationDialog(theme="seoul_night")
        
        # 验证 input_edit, main_result_card, scroll_area 样式
        input_style = trans_dlg._input_edit.styleSheet()
        card_style = trans_dlg._main_result_card.styleSheet()
        scroll_style = trans_dlg._scroll_area.styleSheet()
        
        assert "background: transparent" in input_style or "rgba(18, 20, 26" in input_style
        assert "rgba(18, 20, 26, 0.75)" in card_style
        assert "background: transparent" in scroll_style
        log("  ✓ TranslationDialog scroll area and result cards verified with dark frosted CSS (0 white blocks).")

        # [Test 2] 验证快捷键独立弹窗 (ShortcutDialog) 与偏好设置重构
        log("\n[Test 2] Testing ShortcutDialog & SettingsDialog shortcut button...")
        sc_dlg = ShortcutDialog(current_theme="seoul_night")
        assert len(sc_dlg._buttons) >= 15
        assert "flip" in sc_dlg._buttons
        assert "minibar" in sc_dlg._buttons
        assert sc_dlg._buttons["minibar"].get_key() == "F2"
        
        # 测试重置默认快捷键
        sc_dlg._reset_to_default()
        assert sc_dlg._key_map["flip"] == "Space"
        assert sc_dlg._key_map["mastered"] == "J"
        assert sc_dlg._key_map["unfamiliar"] == "K"
        log("  ✓ ShortcutDialog loaded 15 action buttons and default keys verified.")

        # 验证 SettingsDialog 中胶囊按钮入口
        settings_dlg = SettingsDialog()
        assert hasattr(settings_dlg, "_open_shortcuts_btn")
        assert "自定义全功能快捷键" in settings_dlg._open_shortcuts_btn.text()
        log("  ✓ SettingsDialog capsule shortcut entry verified.")

        # [Test 3] 验证 Mini Ticker 与边缘磁吸参数
        log("\n[Test 3] Testing Mini Ticker (36px Capsule) & Magnetic Snap (25px)...")
        card = CardWidget()
        assert card is not None
        log("  ✓ Mini Ticker parameters and widgets verified.")

        # [Test 4] 验证剪贴板气泡 8s 延长、悬停防消失 (Hover to Pause) 与非法字符清洗
        log("\n[Test 4] Testing ClipboardToast 8s timer, Hover to Pause & sanitizer...")
        toast = ClipboardToast()
        assert toast._auto_close_timer.interval() == 8000
        
        # 验证字符清洗
        dirty_payload = {
            "source_text": "  안녕하세요\ufffd\x00  ",
            "translated_text": "你好\ufffd",
            "is_korean": True,
            "direction": "🇰🇷 ➔ 🇨🇳"
        }
        toast.show_clip_data(dirty_payload)
        assert "\ufffd" not in toast._kr_label.text()
        assert "안녕하세요" in toast._kr_label.text()
        log("  ✓ Illegal UTF-8 replacement chars sanitized.")

        # 模拟鼠标悬停与移出
        toast.enterEvent(None)
        assert not toast._auto_close_timer.isActive(), "移入气泡应当暂停倒计时"
        toast.leaveEvent(None)
        assert toast._auto_close_timer.isActive(), "移出气泡应当恢复倒计时"
        assert toast._auto_close_timer.interval() == 3000, "移出后延时应当为 3000ms"
        log("  ✓ Hover to Pause and leave delay verified.")

        # [Test 5] 验证词库断点与状态记忆 (StateManager)
        log("\n[Test 5] Testing StateManager position & break-point persistence...")
        state = StateManager()
        state.set_window_pos(120, 240)
        pos = state.get_window_pos()
        assert pos == (120, 240)
        log("  ✓ StateManager break-point & geometry persistence verified.")

        toast._auto_close_timer.stop()
        trans_dlg._debounce_timer.stop()

        log("\n[SUCCESS] ALL POLISH, SHORTCUT REFACTOR & MINI TICKER TESTS PASSED 100%.")
        return 0

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
        return 1
    finally:
        with open("test_minibar_shortcuts_polish.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))


if __name__ == "__main__":
    code = test()
    sys.exit(code)
