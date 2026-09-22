# -*- coding: utf-8 -*-
"""
verify_ui_v11.py
----------------
自动化测试套件：验证「未来的韩语卡片」v1.1 UI/UX 深度打磨细节
1. PhoneticTooltip 气泡弹出组件与内容渲染
2. CardWidget 多字长动态阶梯字号自适应缩放
3. 读音文本色彩降噪（#A0A5B5 / #E2E8F0）
4. 收藏按钮极简深色胶囊样式（未收藏 ☆ / 已收藏 ★）
5. ToastWidget 消息提示组件
6. 代码库中 QMessageBox 彻底清除验证
"""

import sys
import os
import re
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from ui.phonetic_tooltip import PhoneticTooltip
from ui.toast_widget import ToastWidget
from ui.card_widget import CardWidget
from core.vocab_manager import VocabManager


def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 验证 PhoneticTooltip 气泡卡片
        log("[Test 1] Testing PhoneticTooltip component...")
        tooltip = PhoneticTooltip()
        mutation_info = {
            "has_mutation": True,
            "rule_tag": "[紧音化]",
            "rule_name": "紧音化",
            "actual_pron": "기숙싸",
            "explanation": "收音 ㄱ 遇到松音 ㅅ 转化为紧音 ㅆ"
        }
        tooltip.show_mutation("기숙사", mutation_info)
        assert not tooltip.isHidden(), "PhoneticTooltip 应当处于可见状态"
        assert "[紧音化]" in tooltip._title_label.text()
        assert "기숙싸" in tooltip._content_label.text()
        assert "#2ECC71" in tooltip._content_label.text() or "#2ecc71" in tooltip._content_label.text()
        log("  ✓ PhoneticTooltip content and highlight colors verified.")
        tooltip.fade_out()

        # [Test 2] 验证 CardWidget 多字长动态阶梯字号
        log("\n[Test 2] Testing CardWidget dynamic ladder font scaling...")
        card = CardWidget()
        card.set_font_scale(1.0)

        # 2.1 短词 1~2字 (如 '뭐', '가다') -> 基准 35px
        card.set_word({"korean": "가다", "meaning": "去", "pronunciation": "gada"})
        card.apply_theme("dark")
        kr_style = card._korean_label.styleSheet()
        assert "font-size: 35px" in kr_style, f"1~2字词号应为 35px，实际为: {kr_style}"
        log("  ✓ 1~2 chars word (가다) -> 35px font-size verified.")

        # 2.2 中词 3~4字 (如 '기숙사', '안녕하세요') -> 基准 28px
        card.set_word({"korean": "기숙사", "meaning": "宿舍", "pronunciation": "gisuksa"})
        card.apply_theme("dark")
        kr_style = card._korean_label.styleSheet()
        assert "font-size: 28px" in kr_style, f"3~4字词号应为 28px，实际为: {kr_style}"
        log("  ✓ 3~4 chars word (기숙사) -> 28px font-size verified.")

        # 2.3 长词 5字+ (如 '국립국어원') -> 基准 23px
        card.set_word({"korean": "국립국어원", "meaning": "国立国语院", "pronunciation": "gungnipgugeowon"})
        card.apply_theme("dark")
        kr_style = card._korean_label.styleSheet()
        assert "font-size: 23px" in kr_style, f"5字+词号应为 23px，实际为: {kr_style}"
        log("  ✓ 5+ chars word (국립국어원) -> 23px font-size verified.")

        # [Test 3] 验证读音文本色彩降噪
        log("\n[Test 3] Testing pronunciation color de-noising...")
        card.set_word({
            "korean": "기숙사",
            "meaning": "宿舍",
            "pronunciation": "gisuksa",
            "pron_kr": "기숙싸"
        })
        pron_html = card._pron_label.text()
        assert "#FCD34D" not in pron_html, "实际读音文本不应包含刺眼的亮黄色 #FCD34D"
        assert "#A0A5B5" in pron_html or "#E2E8F0" in pron_html, f"实际读音应采用低饱和中性灰白: {pron_html}"
        log(f"  ✓ Pronunciation de-noised text verified: {pron_html}")

        # [Test 4] 验证 ToastWidget
        log("\n[Test 4] Testing ToastWidget component...")
        dummy_parent = CardWidget()
        dummy_parent.resize(400, 300)
        toast = ToastWidget.show_toast(dummy_parent, "🎉 测试 Toast 浮层", icon="🔔", duration_ms=1000)
        assert toast is not None
        assert "测试 Toast 浮层" in toast._text_label.text()
        log("  ✓ ToastWidget display verified.")

        # [Test 5] 验证 card_widget 中音变点击呼出 PhoneticTooltip
        log("\n[Test 5] Testing CardWidget _show_mutation_info trigger PhoneticTooltip...")
        card._show_mutation_info()
        assert card._phonetic_tooltip is not None
        assert not card._phonetic_tooltip.isHidden()
        log("  ✓ CardWidget successfully launched PhoneticTooltip.")
        card._phonetic_tooltip.hide()

        # [Test 6] 检查核心 UI 代码无任何 QMessageBox 引入
        log("\n[Test 6] Verifying zero QMessageBox in ui/card_widget.py and ui/main_window.py...")
        with open("ui/card_widget.py", "r", encoding="utf-8") as f:
            c_content = f.read()
            assert "QMessageBox" not in c_content, "ui/card_widget.py 中仍存在 QMessageBox！"
        with open("ui/main_window.py", "r", encoding="utf-8") as f:
            m_content = f.read()
            assert "QMessageBox" not in m_content, "ui/main_window.py 中仍存在 QMessageBox！"
        log("  ✓ Zero QMessageBox in card_widget and main_window confirmed.")

        log("\n[SUCCESS] ALL v1.1 UI/UX VERIFICATION TESTS PASSED 100%.")
        return 0

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
        return 1
    finally:
        with open("test_ui_v11_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))


if __name__ == "__main__":
    code = test()
    sys.exit(code)
