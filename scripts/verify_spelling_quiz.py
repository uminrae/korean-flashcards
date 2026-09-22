import sys
import os
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from ui.card_widget import CardWidget, SpellingUnderlineInput
from ui.main_window import MainWindow

def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)

    try:
        app = QApplication.instance() or QApplication(sys.argv)

        log("[Test 1] Testing SpellingUnderlineInput...")
        input_box = SpellingUnderlineInput()
        input_box.shake()
        assert input_box._shake_anim is not None
        log("[OK] Input box and shake animation created.")

        log("[Test 2] Testing CardWidget spelling mode...")
        card = CardWidget()
        card.show()
        sample_word = {
            "id": 101,
            "korean": "교환학생",
            "chinese": "交换生",
            "meaning": "交换生",
            "pos": "名",
            "pronunciation": "gyohwanhaksaeng",
            "hanja": "【交換】+【學生】",
            "example_korean": "저는 교환학생입니다.",
            "example_chinese": "我是交换生。"
        }
        card.set_word(sample_word)
        card.set_spelling_mode(True)
        assert card._is_spelling_mode is True
        assert card._spelling_container.isHidden() is False
        assert card._front.isHidden() is True
        log("[OK] CardWidget spelling container layout validated.")

        log("[Test 3] Testing Tab hint...")
        card._on_spelling_hint()
        assert card._spelling_hint_count == 1
        assert "교" in card._spelling_input.placeholderText()
        log("[OK] Hint placeholder working.")

        log("[Test 4] Testing submit wrong spelling...")
        card._spelling_input.setText("한국어")
        card._on_spelling_submit()
        assert "核对未通过" in card._spelling_feedback.text()
        log("[OK] Wrong spelling caught with feedback.")

        log("[Test 5] Testing matching spelling and signals...")
        spoken_texts = []
        passed_events = []
        card.speak_requested.connect(lambda txt: spoken_texts.append(txt))
        card.spelling_passed.connect(lambda: passed_events.append(True))

        card._spelling_input.setText("교환학생")
        app.processEvents()
        assert len(spoken_texts) == 1
        assert spoken_texts[0] == "교환학생"

        start_t = time.time()
        while time.time() - start_t < 0.55:
            app.processEvents()
            time.sleep(0.05)
        assert len(passed_events) >= 1
        log("[OK] Spelling matching, auto-speaking and singleShot passed.")

        log("[Test 6] Testing CardWidget spelling mode toggle and escape...")
        card.set_spelling_mode(True)
        assert card._is_spelling_mode is True
        assert card._spelling_container.isHidden() is False
        card.set_spelling_mode(False)
        assert card._is_spelling_mode is False
        assert card._spelling_container.isHidden() is True
        log("[OK] CardWidget spelling state machine validated.")

        card.close()
        log("[SUCCESS] ALL 6 SPELLING TESTS PASSED 100%.")
        return 0
    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
        return 1
    finally:
        with open("test_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

if __name__ == "__main__":
    code = test()
    os._exit(code)
