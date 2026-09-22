"""
verify_pronunciation_rules.py
-----------------------------
自动化测试韩语音变规则智能解析引擎与 UI 标签渲染：
1. 验证 7 大音变规则推导 (鼻音化/连音化/激音化/流音化/紧音化/腭化/ㅎ脱落)
2. 验证无音变词汇纯净展示
3. 验证 CardWidget 中音变胶囊标签与【实际读音】渲染
"""

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from core.pronunciation_rules import analyze_pronunciation
from ui.card_widget import CardWidget

def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 7 大音变规则算法推导验证
        test_cases = [
            # 1. 鼻音化
            ("십년", "심년", "鼻音化", True),
            ("독립", "동닙", "鼻音化", True),
            ("국물", "궁물", "鼻音化", True),
            ("한국말", "한궁말", "鼻音化", True),
            ("감사합니다", "감사함니다", "鼻音化", True),

            # 2. 连音化
            ("한국어", "한구거", "连音", True),
            ("음악", "으막", "连音", True),
            ("월요일", "워료일", "连音", True),
            ("읽어", "일거", "连音化", True),

            # 3. 激音化
            ("축하", "추카", "激音化", True),
            ("입학", "이팍", "激音化", True),
            ("좋다", "조타", "激音化", True),
            ("많다", "만타", "激音化", True),
            ("어떻게", "어떠케", "激音化", True),

            # 4. 流音化
            ("신라", "실라", "流音化", True),
            ("설날", "설랄", "流音化", True),
            ("칼날", "칼랄", "流音化", True),

            # 5. 紧音化
            ("학교", "학꾜", "紧音化", True),
            ("식당", "식땅", "紧音化", True),
            ("잡지", "잡찌", "紧音化", True),

            # 6. 腭化
            ("같이", "가치", "腭化", True),
            ("굳이", "구지", "腭化", True),

            # 7. ㅎ脱落
            ("좋은", "조은", "ㅎ脱落", True),

            # 8. 无音变常规词
            ("안녕", "안녕", "", False),
            ("도서관", "도서관", "", False),
            ("사람", "사람", "", False),
        ]

        log("[Test 1] Testing phonological mutation rules...")
        for word_kr, expected_pron, expected_rule, expected_mut in test_cases:
            res = analyze_pronunciation(word_kr)
            assert res["has_mutation"] == expected_mut, (
                f"[{word_kr}] has_mutation 预期: {expected_mut}, 实际: {res['has_mutation']}"
            )
            assert res["actual_pron"] == expected_pron, (
                f"[{word_kr}] actual_pron 预期: {expected_pron}, 实际: {res['actual_pron']}"
            )
            if expected_mut:
                assert expected_rule in res["rule_name"] or expected_rule in res["rule_tag"], (
                    f"[{word_kr}] 规则标签预期包含: {expected_rule}, 实际: {res['rule_name']}"
                )
            log(f"  ✓ {word_kr} -> [{res['actual_pron']}] {res['rule_tag']}")

        log("[OK] Phonological rules verified 100%.")

        # [Test 2] CardWidget UI 渲染与显隐测试
        log("[Test 2] Testing CardWidget UI tags and pronunciation display...")
        card = CardWidget()
        
        # A. 设置音变词条：십년
        mutation_word = {
            "id": "test_01",
            "korean": "십년",
            "meaning": "十年",
            "pronunciation": "simnyeon",
            "pos": "名词"
        }
        card.set_word(mutation_word)
        assert not card._mutation_badge.isHidden(), "音变词条 _mutation_badge 应当显示"
        assert "鼻音" in card._mutation_badge.text(), f"音变标签文本错误: {card._mutation_badge.text()}"
        assert "实际读音: 심년" in card._pron_label.text(), f"实际读音未在 _pron_label 中渲染: {card._pron_label.text()}"
        log("  ✓ Mutation word UI badge & actual pronunciation verified.")

        # B. 设置无音变词条：도서관
        normal_word = {
            "id": "test_02",
            "korean": "도서관",
            "meaning": "图书馆",
            "pronunciation": "doseogwan",
            "pos": "名词"
        }
        card.set_word(normal_word)
        assert card._mutation_badge.isHidden(), "常规无音变词条 _mutation_badge 应当隐藏"
        assert "实际读音" not in card._pron_label.text(), "常规词不应展示额外实际读音标注"
        log("  ✓ Normal word pure UI display verified.")

        log("[SUCCESS] ALL PRONUNCIATION MUTATION TESTS PASSED 100%.")

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
    finally:
        with open("test_mutation_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

if __name__ == "__main__":
    test()
