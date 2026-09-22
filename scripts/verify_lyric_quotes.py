"""
verify_lyric_quotes.py
----------------------
自动化测试「歌词 / 影视台词微语境扩展」功能：
1. 验证词库与 VocabManager 数据标准化兼容
2. 验证 CardWidget 中 Instagram Story 质感歌词卡片的渲染与自适应显隐
3. 验证独立发音按钮行为
"""

import sys
import os
import re
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from core.vocab_manager import VocabManager
from ui.card_widget import CardWidget

def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 词库加载与歌词数据解析
        log("[Test 1] Testing VocabManager quote_lyric loading...")
        vm = VocabManager()
        quote_words = [w for w in vm.all_words if w.get("quote_kr") or w.get("quote_lyric")]
        log(f"  ✓ Found {len(quote_words)} words with quote_lyric in vocabulary.")
        assert len(quote_words) > 0, "词库中应包含带歌词/台词语境的词条"

        # 检查重点词汇: 안녕, 기억하다, 친구
        sample_keys = ["안녕", "기억하다", "친구"]
        for k in sample_keys:
            matched = [w for w in quote_words if w.get("korean") == k]
            assert len(matched) > 0, f"重点词条 {k} 应具有歌词/台词语境"
            w = matched[0]
            assert bool(w.get("quote_kr")), f"词条 {k} 的 quote_kr 为空"
            assert bool(w.get("quote_cn")), f"词条 {k} 的 quote_cn 为空"
            assert bool(w.get("quote_source")), f"词条 {k} 的 quote_source 为空"
            log(f"  ✓ {k}: “{w['quote_kr']}” ({w['quote_source']})")

        # [Test 2] CardWidget UI 渲染与自适应显隐
        log("[Test 2] Testing CardWidget UI quote_box display and visibility...")
        card = CardWidget()

        # A. 设置带歌词的词条
        song_word = {
            "id": "test_quote_01",
            "korean": "별",
            "meaning": "星星",
            "pronunciation": "byeol",
            "pos": "名词",
            "quote_kr": "가장 깊은 밤에 더 빛나는 별빛",
            "quote_cn": "在最深沉的夜空中更加耀眼的星光",
            "quote_source": "소우주 (Mikrokosmos) - BTS",
            "quote_type": "song"
        }
        card.set_word(song_word)
        assert not card._quote_box.isHidden(), "带歌词的词条 _quote_box 应当显示"
        clean_render_kr = re.sub(r"<[^>]+>", "", card._quote_korean.text())
        assert "가장 깊은 밤" in clean_render_kr, f"歌词原句未正确渲染: {clean_render_kr}"
        assert "在最深沉" in card._quote_chinese.text(), "歌词中文翻译未正确渲染"
        assert "Mikrokosmos" in card._quote_source_label.text(), "来源标签未正确渲染"
        assert "🎵" in card._quote_title_label.text(), "歌曲类型标题图标应为 🎵"
        log("  ✓ Song quote UI display verified.")

        # B. 设置带影视台词的词条
        drama_word = {
            "id": "test_quote_02",
            "korean": "기억",
            "meaning": "记忆",
            "pronunciation": "gieok",
            "pos": "名词",
            "quote_kr": "너와 함께한 시간 모두 눈부셨다.",
            "quote_cn": "与你共度的所有时光都无比耀眼。",
            "quote_source": "tvN 《孤单又灿烂的神-鬼怪》",
            "quote_type": "drama"
        }
        card.set_word(drama_word)
        assert not card._quote_box.isHidden(), "带台词的词条 _quote_box 应当显示"
        clean_drama_kr = re.sub(r"<[^>]+>", "", card._quote_korean.text())
        assert "눈부셨다" in clean_drama_kr, f"台词原句未正确渲染: {clean_drama_kr}"
        assert "鬼怪" in card._quote_source_label.text(), "影视剧来源未正确渲染"
        assert "🎬" in card._quote_title_label.text(), "影视剧类型标题图标应为 🎬"
        log("  ✓ Drama quote UI display verified.")

        # C. 设置不带歌词的普通词条
        plain_word = {
            "id": "test_quote_03",
            "korean": "사과",
            "meaning": "苹果",
            "pronunciation": "sagwa",
            "pos": "名词"
        }
        card.set_word(plain_word)
        assert card._quote_box.isHidden(), "无歌词的词条 _quote_box 应当隐藏"
        log("  ✓ Plain word quote_box auto-collapse verified.")

        # [Test 3] 独立发音信号测试
        log("[Test 3] Testing quote speak trigger...")
        spoken_text = []
        card.speak_requested.connect(lambda txt: spoken_text.append(txt))
        card.set_word(song_word)
        card._on_speak_quote()
        assert len(spoken_text) == 1, "点击朗读歌词应触发 speak_requested"
        assert "가장 깊은 밤에 더 빛나는 별빛" in spoken_text[0], f"朗读文本不匹配: {spoken_text[0]}"
        log(f"  ✓ Quote speak emitted: {spoken_text[0]}")

        log("[SUCCESS] ALL LYRIC QUOTE TESTS PASSED 100%.")

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
    finally:
        with open("test_lyric_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

if __name__ == "__main__":
    test()
