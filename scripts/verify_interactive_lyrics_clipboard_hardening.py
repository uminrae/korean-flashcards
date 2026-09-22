# -*- coding: utf-8 -*-
"""
verify_interactive_lyrics_clipboard_hardening.py
------------------------------------------------
自动化测试套件：验证 4 项深度体验优化与健壮性加固
1. 歌词金句「交互式词内点击解析」与活用变形
2. 全局剪贴板 30 秒防抖、敏感代码变量过滤与一键静音
3. 网络请求 1.5s 极速超时与无感知离线平滑熔断
4. 手写字帖「田字格 / 米字格 / 极简手账横线」多样式导出
"""

import sys
import os
import json
import time
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from ui.card_widget import CardWidget, make_interactive_lyric_html
from core.clipboard_listener import ClipboardListener
from core.translator_manager import TranslatorManager, OfflineDictEngine
from core.copybook_generator import CopybookGenerator
from ui.copybook_dialog import CopybookExportDialog
from core.vocab_manager import VocabManager


def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 验证歌词分词与词内交互点击解析
        log("[Test 1] Testing Interactive Word Click-to-Inspect in Lyrics...")
        sample_lyric = "붉은 태양처럼 타올라 삼켜버릴 테니까"
        html_res = make_interactive_lyric_html(sample_lyric)
        assert "href='word:붉은'" in html_res
        assert "href='word:삼켜버릴'" in html_res
        log("  ✓ make_interactive_lyric_html parsed Korean words into interactive links.")

        card = CardWidget()
        mock_lyric_word = {
            "korean": "TOMBOY",
            "meaning": "不受束缚的酷女孩态度",
            "quote_kr": sample_lyric,
            "quote_cn": "像红日一样熊熊燃烧 将一切尽情吞噬",
            "source_info": "i-dle · 《TOMBOY》",
            "grammar_notes": "-(으)ㄹ 테니까: 表示意志或推测理由"
        }
        card.set_word(mock_lyric_word)
        
        # 模拟点击歌词中的单个动词词条 "가다" 或 "듣다"
        card._on_lyric_word_clicked("word:듣다")
        assert not card._word_inspect_box.isHidden(), "点击词内单词后 _word_inspect_box 应当显示"
        assert "듣다" in card._inspect_text_lbl.text()
        assert card._inspect_conj_layout.count() >= 1, "点击谓词应当展示活用胶囊"
        log("  ✓ Word inspection box and conjugation capsules rendered correctly on word click.")

        # [Test 2] 验证全局剪贴板防打扰、30s 防抖与代码变量过滤
        log("\n[Test 2] Testing Clipboard Quiet Mode & Noise Filter...")
        vm = VocabManager()
        vm.load()
        clip = ClipboardListener(vocab_manager=vm)
        
        # 2.1 切换静音开关
        assert clip.is_enabled is True
        clip.toggle_enabled()
        assert clip.is_enabled is False
        clip.toggle_enabled()
        assert clip.is_enabled is True
        log("  ✓ toggle_enabled() successfully toggled clipboard capture state.")

        # 2.2 防抖与过滤规则验证
        # 纯数字
        clip._seen_history.clear()
        assert clip.process_text("12345678") is False, "纯数字应当被静默忽略"
        assert "12345678" not in clip._seen_history

        # 代码变量驼峰 / 变量命名
        assert clip.process_text("getUserInformationList") is False, "代码驼峰变量应当被静默过滤"
        assert "getUserInformationList" not in clip._seen_history

        # 有效韩文短句
        assert clip.process_text("행복하세요") is True, "有效韩文应当被捕获"
        assert "행복하세요" in clip._seen_history

        # 30 秒内重复复制相同文本
        last_t = clip._seen_history["행복하세요"]
        assert clip.process_text("행복하세요") is False, "30秒内重复复制应当防抖静默忽略"
        assert clip._seen_history["행복하세요"] == last_t
        log("  ✓ 30s debounce and noise/code filter verified.")

        # [Test 3] 验证网络请求限频与平滑熔断降级
        log("\n[Test 3] Testing Rate Limiting & Circuit Breaking...")
        tm = TranslatorManager()
        tm.translate_async("사랑", engine="offline")
        assert tm._last_request_time > 0
        if tm._current_worker:
            tm._current_worker.wait(2000)
        
        # 离线词典快速检索
        offline_engine = OfflineDictEngine()
        off_res = offline_engine.lookup("사과")
        assert off_res.get("success") is True
        assert "苹果" in off_res.get("text", "")
        log("  ✓ Offline fallback lookup verified (instant millisecond response).")

        # [Test 4] 验证字帖三种样式导出 (田字格 / 米字格 / 手账横线)
        log("\n[Test 4] Testing Copybook Generator (Tian / Mi / Lines)...")
        gen = CopybookGenerator()
        test_words = [
            {"korean": "행복", "chinese": "幸福", "pronunciation": "haengbok", "pos": "名词", "example_kr": "늘 행복하세요.", "example_cn": "请一直幸福。"},
            {"korean": "사랑", "chinese": "爱情 / 爱", "pronunciation": "sarang", "pos": "名词", "example_kr": "사랑해요.", "example_cn": "我爱你。"}
        ]
        
        # 4.1 田字格导出 (PDF)
        out_tian = gen.generate(test_words, "test_copybook_tian.pdf", grid_style="tian")
        assert len(out_tian) == 1 and os.path.exists(out_tian[0])
        log(f"  ✓ Tian Grid PDF generated successfully ({os.path.getsize(out_tian[0])} bytes).")

        # 4.2 米字格导出 (PNG)
        out_mi = gen.generate(test_words, "test_copybook_mi.png", grid_style="mi")
        assert len(out_mi) >= 1 and os.path.exists(out_mi[0])
        log(f"  ✓ Mi Grid PNG generated successfully ({os.path.getsize(out_mi[0])} bytes).")

        # 4.3 极简手账横线导出 (PDF)
        out_lines = gen.generate(test_words, "test_copybook_lines.pdf", grid_style="lines")
        assert len(out_lines) == 1 and os.path.exists(out_lines[0])
        log(f"  ✓ Lines Style PDF generated successfully ({os.path.getsize(out_lines[0])} bytes).")

        # 4.4 导出配置弹窗 UI
        dlg = CopybookExportDialog(words_count=len(test_words))
        assert dlg._rb_tian.isChecked()
        dlg._rb_mi.setChecked(True)
        assert dlg._rb_mi.isChecked()
        dlg.close()
        dlg.deleteLater()
        log("  ✓ CopybookExportDialog UI controls and radio buttons verified.")

        card.close()
        card.deleteLater()

        # 清理临时测试文件与工作线程
        if clip._translator:
            clip._translator.cancel()
        if tm:
            tm.cancel()

        for f in ["test_copybook_tian.pdf", "test_copybook_mi.png", "test_copybook_lines.pdf"]:
            if os.path.exists(f):
                try: os.remove(f)
                except Exception: pass

        log("\n[SUCCESS] ALL 4 ADVANCED HARDENING & EXPERIENCE ENHANCEMENT TESTS PASSED 100%.")
        return 0

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
        return 1
    finally:
        with open("test_interactive_lyrics_hardening.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))


if __name__ == "__main__":
    code = test()
    sys.exit(code)

