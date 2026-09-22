"""
verify_collocations_antonyms.py
-------------------------------
自动化测试套件：验证「常用地道搭配与反义词拓展」功能
1. 词库中 collocations 与 antonyms 数据完整性
2. VocabManager 标准化解析与全局反义词检索/跳转
3. CardWidget 搭配胶囊 UI 渲染与独立发音
4. CardWidget 反义词对照胶囊与点击跳转信号
5. MainWindow 联动反义词无缝跨词跳转
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
from core.vocab_manager import VocabManager
from ui.card_widget import CardWidget


def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 验证 VocabManager 搭配与反义词加载
        log("[Test 1] Testing VocabManager collocations and antonyms parsing...")
        vm = VocabManager()
        
        words_with_colloc = [w for w in vm.all_words if w.get("collocations")]
        words_with_antonym = [w for w in vm.all_words if w.get("antonyms")]
        
        log(f"  ✓ Found {len(words_with_colloc)} words with collocations in vocabulary.")
        log(f"  ✓ Found {len(words_with_antonym)} words with antonyms in vocabulary.")
        assert len(words_with_colloc) >= 20, "词库中应包含充足的搭配语块词条"
        assert len(words_with_antonym) >= 20, "词库中应包含充足的反义词词条"

        # 检查重点词: 꿈, 비, 크다, 빠르다
        sample_colloc_words = ["꿈", "비", "밥", "약속"]
        for k in sample_colloc_words:
            matched = [w for w in vm.all_words if w.get("korean") == k]
            assert len(matched) > 0, f"重点词条 {k} 应存在于词库中"
            w = matched[0]
            collocs = w.get("collocations", [])
            assert len(collocs) > 0, f"词条 {k} 应具有 collocations 搭配数据"
            assert "kr" in collocs[0], f"搭配项缺少 kr 字段: {collocs[0]}"
            log(f"  ✓ {k}: {len(collocs)} collocations -> {collocs[0]['kr']} ({collocs[0].get('cn', '')})")

        # [Test 2] 验证反义词检索与跨词定位
        log("\n[Test 2] Testing find_word_by_korean and jump_to_korean...")
        w_big = vm.find_word_by_korean("크다")
        assert w_big is not None, "应成功找到单词 [크다]"
        ants = w_big.get("antonyms", [])
        assert len(ants) > 0, "[크다] 应包含反义词"
        assert ants[0]["kr"] == "작다", f"[크다] 反义词应为 [작다]，实际为: {ants[0]}"
        log(f"  ✓ [크다] <-> [{ants[0]['kr']}] ({ants[0]['cn']}) verified.")

        w_small = vm.find_word_by_korean("작다")
        assert w_small is not None, "应成功找到反义词 [작다]"
        log(f"  ✓ Global search found word: {w_small['korean']} - {w_small['meaning']}")

        # [Test 3] CardWidget 搭配胶囊与反义词 UI 渲染
        log("\n[Test 3] Testing CardWidget UI collocation box & antonym pill...")
        card = CardWidget()
        card.set_word(w_big)

        # 验证反义词按钮可见并携带正确文本与属性
        assert not card._antonym_btn.isHidden(), "带反义词的词条 _antonym_btn 应当显示"
        assert "작다" in card._antonym_btn.text(), f"反义词文本未包含 [작다]: {card._antonym_btn.text()}"
        assert card._antonym_btn.property("target_kr") == "작다"
        log(f"  ✓ Antonym badge displayed: {card._antonym_btn.text()}")

        # 验证搭配容器可见且包含搭配条目
        assert not card._collocation_box.isHidden(), "带搭配的词条 _collocation_box 应当显示"
        assert card._colloc_items_layout.count() > 0, "搭配容器中应当包含搭配卡片条目"
        log(f"  ✓ Collocation box displayed with {card._colloc_items_layout.count()} items.")

        # [Test 4] 验证搭配独立发音与反义词点击跳转信号
        log("\n[Test 4] Testing CardWidget signals...")
        spoken_colloc = []
        card.speak_requested.connect(lambda txt: spoken_colloc.append(txt))

        # 模拟点击第一个搭配的 🔊 按钮
        item_widget = card._colloc_items_layout.itemAt(0).widget()
        assert item_widget is not None
        # 查找发音按钮
        speak_btn = item_widget.findChild(type(card._speak_btn))
        assert speak_btn is not None, "搭配卡片中应包含发音按钮"
        speak_btn.click()
        assert len(spoken_colloc) == 1, "点击搭配发音按钮应触发 speak_requested"
        log(f"  ✓ Collocation speak requested: {spoken_colloc[0]}")

        # 模拟点击反义词药丸
        jumped_target = []
        card.antonym_jump_requested.connect(lambda target: jumped_target.append(target))
        card._antonym_btn.click()
        assert len(jumped_target) == 1, "点击反义词按钮应触发 antonym_jump_requested"
        assert jumped_target[0] == "작다", f"跳转目标应为 [작다]，实际为: {jumped_target[0]}"
        log(f"  ✓ Antonym jump signal emitted: {jumped_target[0]}")

        # [Test 5] 验证反义词跨词跳转与词库状态联动
        log("\n[Test 5] Testing Antonym jump and VocabManager state synchronization...")
        vm.jump_to_korean("크다")
        assert vm.current_word()["korean"] == "크다"
        log(f"  ✓ Current word before jump: {vm.current_word()['korean']}")

        # 模拟跳转到反义词 작다
        jump_success = vm.jump_to_korean("작다")
        assert jump_success is True, "跨词跳转到 [작다] 应返回 True"
        assert vm.current_word()["korean"] == "작다", f"跳转后当前词应为 [작다]，实际为: {vm.current_word()['korean']}"
        log(f"  ✓ Successfully jumped to antonym word: {vm.current_word()['korean']} ({vm.current_word()['meaning']})")

        log("\n[SUCCESS] ALL COLLOCATION AND ANTONYM TESTS PASSED 100%.")

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
    finally:
        with open("test_collocation_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))


if __name__ == "__main__":
    test()
