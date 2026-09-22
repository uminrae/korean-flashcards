# -*- coding: utf-8 -*-
"""
verify_translator_drawer.py
---------------------------
自动化测试套件：验证多引擎极简翻译抽屉 (Translation Drawer)
1. 双向自动语种检测 (ko <-> zh-CN)
2. 本地离线词典毫秒级匹配 (Offline Dictionary)
3. 多引擎智能翻译 (Papago / Google / Offline / All Compare)
4. Instagram 极简毛玻璃抽屉 UI、Pill Tabs 切换与一键收词
"""

import sys
import os
import json
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from core.translator_manager import (
    is_korean_text, detect_direction, OfflineDictEngine,
    translate_google, translate_papago, TranslationWorker
)
from ui.translation_dialog import TranslationDialog


def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 验证双向语种检测
        log("[Test 1] Testing Language Detection & Direction...")
        assert is_korean_text("안녕하세요"), "未能正确识别韩文文本"
        assert not is_korean_text("你好，今天天气真好"), "中文文本被误判为韩文"
        
        sl1, tl1 = detect_direction("감사합니다")
        assert sl1 == "ko" and tl1 == "zh-CN", f"韩转中检测错误: {sl1}->{tl1}"

        sl2, tl2 = detect_direction("谢谢你的帮助")
        assert sl2 == "zh-CN" and tl2 == "ko", f"中转韩检测错误: {sl2}->{tl2}"
        log("  ✓ Bidirectional language direction detection verified.")

        # [Test 2] 验证本地离线词典毫秒级匹配
        log("\n[Test 2] Testing Local Offline Dictionary Engine...")
        offline_dict = OfflineDictEngine()
        
        # 2.1 韩语查中文
        res1 = offline_dict.lookup("학교")
        assert res1["success"], "离线词典未找到 '학교'"
        assert "学校" in res1["text"], f"离线词典释义错误: {res1}"
        log(f"  ✓ Offline KR->CN lookup (학교 -> {res1['text']}) verified.")

        # 2.2 中文查韩文
        res2 = offline_dict.lookup("老师")
        assert res2["success"], "离线词典未找到 '老师' 对应的韩文"
        log(f"  ✓ Offline CN->KR reverse lookup (老师 -> {res2['text']}) verified.")

        # [Test 3] 验证多引擎核心翻译逻辑与异步工作线程
        log("\n[Test 3] Testing Translation Worker Async Execution...")
        worker = TranslationWorker("사랑해", engine="offline")
        res_container = []
        worker.result_ready.connect(lambda d: res_container.append(d))
        worker.run()  # 直接在主线程执行 run 验证数据构造

        assert len(res_container) == 1, "Worker 未发出结果信号"
        res_data = res_container[0]
        assert res_data["status"] == "success"
        assert res_data["query"] == "사랑해"
        assert res_data["sl"] == "ko"
        log("  ✓ TranslationWorker synchronous execution verified.")

        # [Test 4] 验证 TranslationDialog 极简抽屉 UI 与交互
        log("\n[Test 4] Testing TranslationDialog UI & Pill Tabs...")
        class DummyTTS:
            def speak(self, text): pass

        dialog = TranslationDialog(tts_engine=DummyTTS())
        
        # 4.1 Pill Tabs 切换
        dialog._on_engine_tab_clicked("google")
        assert dialog._current_engine == "google"
        assert dialog._engine_buttons["google"].isChecked()

        dialog._on_engine_tab_clicked("all")
        assert dialog._current_engine == "all"
        assert dialog._engine_buttons["all"].isChecked()
        log("  ✓ Engine Pill Tabs toggling verified.")

        # 4.2 模拟翻译结果渲染 (单引擎)
        mock_data_single = {
            "status": "success",
            "query": "꿈을 꾸다",
            "engine": "papago",
            "main_result": "做梦",
            "details": {
                "success": True,
                "pos": "动词",
                "pronunciation": "kkumeul kkuda",
                "example_kr": "어젯밤에 좋은 꿈을 꿨어요.",
                "example_cn": "昨晚做了一个好梦。"
            }
        }
        dialog._on_translation_completed(mock_data_single)
        assert not dialog._main_result_card.isHidden()
        assert not dialog._dict_detail_card.isHidden()
        log("  ✓ Single engine result & rich dictionary card rendered.")

        # 4.3 模拟多引擎对照模式渲染
        mock_data_all = {
            "status": "success",
            "query": "설레다",
            "engine": "all",
            "data": {
                "youdao": {"success": True, "text": "心动 / 激动"},
                "papago": {"success": True, "text": "心动 / 激动"},
                "google": {"success": True, "text": "心潮澎湃"},
                "offline": {"success": True, "pos": "动词", "text": "心动"}
            }
        }
        dialog._on_translation_completed(mock_data_all)
        assert dialog._main_result_card.isHidden()
        assert not dialog._compare_container.isHidden()
        assert dialog._compare_layout.count() == 4
        log("  ✓ Multi-engine comparison 4-card view rendered.")

        # 4.4 验证一键收入生词本
        dialog._input_edit.setPlainText("두근거리다")
        dialog._last_result_data = {
            "main_result": "扑通扑通跳",
            "details": {"pronunciation": "dugeungeorida"}
        }
        added_list = []
        dialog.word_added_to_custom.connect(lambda kr, cn, pr: added_list.append((kr, cn, pr)))
        dialog._add_to_custom_vocab()
        assert len(added_list) == 1
        assert added_list[0][0] == "두근거리다"
        log("  ✓ One-click save to custom vocab book verified.")

        dialog._debounce_timer.stop()
        dialog.close()
        dialog.deleteLater()

        log("\n[SUCCESS] ALL TRANSLATION DRAWER TESTS PASSED 100%.")
        return 0

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
        return 1
    finally:
        with open("test_translator_drawer.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))


if __name__ == "__main__":
    code = test()
    sys.exit(code)
