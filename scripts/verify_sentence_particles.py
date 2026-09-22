"""
verify_sentence_particles.py
----------------------------
自动化验证「日常语境例句与助词高亮」功能：
1. 语法助词色彩识别与 Tooltip 注入
2. 目标词词干活用与双层色彩层次
3. 独立例句发音按钮与 speak_requested 信号
4. 卡片背面 QScrollArea 防溢出滚动区域
"""

import sys
import os
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from core.particle_highlighter import highlight_sentence_with_particles
from ui.card_widget import CardWidget

def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)

    try:
        app = QApplication.instance() or QApplication(sys.argv)

        log("[Test 1] Testing particle highlighter algorithm...")
        word_info = {
            "korean": "공부하다",
            "meaning": "学习"
        }
        sentence = "저는 도서관에서 한국어를 공부합니다."
        highlighted = highlight_sentence_with_particles(sentence, word_info, theme="dark")
        log(f"Result: {highlighted}")

        # 验证目标词高亮 (공부합)
        assert "#FCD34D" in highlighted, "目标词暖金高亮未生效"
        assert "공부합" in highlighted, "词干变形未成功匹配"

        # 验证助词高亮 (는, 에서, 를)
        assert "#D8B4FE" in highlighted, "助词淡紫点缀色未生效"
        assert "助词: -는" in highlighted, "主题助词 -는 未识别"
        assert "助词: -에서" in highlighted, "处所助词 -에서 未识别"
        assert "助词: -를" in highlighted, "宾格助词 -를 未识别"
        log("[OK] Particle highlighter successfully detected particles and target word.")

        log("[Test 2] Testing CardWidget example rendering and QScrollArea...")
        card = CardWidget()
        card.show()
        sample = {
            "id": "1_1_01",
            "korean": "안녕하세요",
            "meaning": "你好",
            "example_kr": "안녕하세요, 저는 김민수입니다.",
            "example_cn": "你好，我是金民秀。"
        }
        card.set_word(sample)
        card.flip() # 翻到背面

        assert card._back_scroll.isVisible() is True, "背面 QScrollArea 未显示"
        assert card._example_box.isVisible() is True, "例句卡片容器未显示"
        assert "#D8B4FE" in card._example_korean.text(), "例句中的助词高亮未渲染到 QLabel"
        log("[OK] CardWidget correctly rendered example sentence with particle highlight.")

        log("[Test 3] Testing independent example TTS speak button...")
        spoken_texts = []
        card.speak_requested.connect(lambda txt: spoken_texts.append(txt))

        # 模拟点击例句发音按钮
        card._example_speak_btn.click()
        app.processEvents()

        assert len(spoken_texts) == 1, "未触发独立例句发音"
        assert "안녕하세요, 저는 김민수입니다." in spoken_texts[0], f"发音文本异常: {spoken_texts}"
        log(f"[OK] Example TTS requested: {spoken_texts[0]}")

        card.close()
        log("[SUCCESS] ALL SENTENCE & PARTICLE HIGHLIGHT TESTS PASSED 100%.")
    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
    finally:
        with open("test_particle_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

if __name__ == "__main__":
    test()
