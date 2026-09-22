# -*- coding: utf-8 -*-
"""
verify_conjugator_clipboard_idle.py
-----------------------------------
自动化测试套件：验证 i-dle 全曲库金句、剪贴板划词翻译联动与谓词活用变形
1. 动词/形容词常用活用变形引擎 (Conjugation Engine)
2. 全局剪贴板划词中韩双语秒级翻译与持久化收录 (Clipboard Smart Link)
3. i-dle 全专全曲目专属歌词金句库 (i-dle Full Album Discography & Solo/OST)
4. Instagram 极简悬浮微气泡联动与深入翻译抽屉
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
from core.korean_conjugator import conjugate_korean_word, get_conjugation_capsules
from core.clipboard_listener import ClipboardListener
from core.vocab_manager import VocabManager
from ui.card_widget import CardWidget
from ui.clipboard_toast import ClipboardToast


def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 验证 KoreanConjugator 谓词活用变形引擎
        log("[Test 1] Testing KoreanConjugator Engine...")
        
        # 1.1 规则动词/形容词: 가다
        conj_ga = conjugate_korean_word("가다")
        assert conj_ga["haeyo"] == "가요"
        assert conj_ga["seumnida"] == "갑니다"
        assert conj_ga["past"] == "갔어요"
        assert conj_ga["future"] == "갈 거예요"
        assert conj_ga["go"] == "가고"
        assert conj_ga["myeon"] == "가면"
        log("  ✓ Regular verb (가다) conjugations verified.")

        # 1.2 ㄷ 不规则动词: 듣다 -> 들어요, 듣습니다, 들었어요, 들을 거예요
        conj_deut = conjugate_korean_word("듣다")
        assert conj_deut["haeyo"] == "들어요"
        assert conj_deut["seumnida"] == "듣습니다"
        assert conj_deut["past"] == "들었어요"
        assert conj_deut["future"] == "들을 거예요"
        assert conj_deut["myeon"] == "들으면"
        log("  ✓ ㄷ-irregular verb (듣다) conjugations verified.")

        # 1.3 ㅂ 不规则形容词: 춥다 -> 추워요, 춥습니다, 추웠어요, 추울 거예요
        conj_chup = conjugate_korean_word("춥다")
        assert conj_chup["haeyo"] == "추워요"
        assert conj_chup["seumnida"] == "춥습니다"
        assert conj_chup["past"] == "추웠어요"
        assert conj_chup["future"] == "추울 거예요"
        log("  ✓ ㅂ-irregular adjective (춥다) conjugations verified.")

        # 1.4 르 不规则: 모르다 -> 몰라요, 모릅니다, 몰랐어요
        conj_mol = conjugate_korean_word("모르다")
        assert conj_mol["haeyo"] == "몰라요"
        assert conj_mol["past"] == "몰랐어요"
        log("  ✓ 르-irregular verb (모르다) conjugations verified.")

        # 1.5 하다 动词/形容词: 공부하다 -> 공부해요, 공부합니다, 공부했어요, 공부할 거예요
        conj_gong = conjugate_korean_word("공부하다")
        assert conj_gong["haeyo"] == "공부해요"
        assert conj_gong["seumnida"] == "공부합니다"
        assert conj_gong["past"] == "공부했어요"
        assert conj_gong["future"] == "공부할 거예요"
        log("  ✓ 하다-verb (공부하다) conjugations verified.")

        # [Test 2] 验证全局剪贴板划词监听与持久化生词本
        log("\n[Test 2] Testing ClipboardListener and Custom Vocab persistence...")
        vm = VocabManager()
        vm.load()
        clip_listener = ClipboardListener(vocab_manager=vm)
        
        test_kr = "두근거리다"
        test_meaning = "心跳扑通扑通"
        saved = clip_listener.add_to_custom_vocab(test_kr, test_meaning, "dugeungeorida")
        assert saved.get("korean") == test_kr
        
        custom_list = clip_listener.get_custom_words()
        assert any(w.get("korean") == test_kr for w in custom_list)
        log("  ✓ Custom word successfully persisted in data/custom_vocab.json.")

        # [Test 3] 验证 i-dle 全专全曲目专属歌词金句库
        log("\n[Test 3] Testing i-dle discography lyrics database (70+ Songs)...")
        idle_words = vm.load_idle_lyrics()
        assert len(idle_words) >= 50, f"i-dle 全专歌词收录条目不足: {len(idle_words)}"
        
        # 查找 TOMBOY 经典金句条目
        tomboy_word = next((w for w in idle_words if "TOMBOY" in w.get("song_title", "") or "미친 연" in w.get("korean", "")), None)
        assert tomboy_word is not None, "未找到 TOMBOY 经典金句条目"
        assert "i-dle" in tomboy_word.get("artist", "")
        assert tomboy_word.get("grammar_notes"), "TOMBOY 应包含核心语法点注解"
        
        # 查找 Solo 曲 (如 Miyeon Drive 或 YUQI FREAK)
        drive_word = next((w for w in idle_words if "Drive" in w.get("song_title", "") or "曺薇娟" in w.get("artist", "")), None)
        assert drive_word is not None, "未找到曺薇娟 Miyeon 《Drive》 官方 Solo 曲目"
        
        freak_word = next((w for w in idle_words if "FREAK" in w.get("song_title", "") or "宋雨琦" in w.get("artist", "")), None)
        assert freak_word is not None, "未找到宋雨琦 YUQI 《FREAK》 官方 Solo 曲目"

        log(f"  ✓ i-dle full discography database verified: loaded {len(idle_words)} quotes (Group & Solo).")

        # [Test 4] 验证 VocabManager 动态多册数过滤与查找
        log("\n[Test 4] Testing VocabManager book switching (-2, -3)...")
        books = vm.get_books()
        book_ids = [b[0] for b in books]
        assert -2 in book_ids, "应当包含 -2 剪贴板自定义词库"
        assert -3 in book_ids, "应当包含 -3 i-dle 专属全曲库"
        
        # 验证名称规范统一为 i-dle
        idle_book_name = next(b[1] for b in books if b[0] == -3)
        assert "i-dle" in idle_book_name.lower() and "(g)" not in idle_book_name.lower()
        log(f"  ✓ Book -3 standardized title: '{idle_book_name}'")

        # 切换到自定义词库
        vm.apply_filter(book=-2)
        assert len(vm.filtered_words) > 0, "自定义词库过滤后词数不应为空"
        
        # 切换到 i-dle 歌词全曲库
        vm.apply_filter(book=-3)
        assert len(vm.filtered_words) >= 50, "i-dle 歌词库过滤后词数不应为空"
        
        # 验证按专辑二级联动
        units = vm.get_units(-3)
        assert len(units) >= 5, f"i-dle 专辑数不足: {len(units)}"
        log(f"  ✓ i-dle Album categories verified: {len(units)} albums available.")

        # 跨库定位
        found_quote = vm.find_word_by_korean(tomboy_word["korean"])
        assert found_quote is not None, "应当能在跨库检索中找到 i-dle 歌词"
        log("  ✓ VocabManager book filtering and cross-lookup verified.")

        # [Test 5] 验证 CardWidget 活用变形卡片与 i-dle 歌词视图渲染
        log("\n[Test 5] Testing CardWidget UI rendering for Conjugation & i-dle...")
        card = CardWidget()
        
        # 5.1 谓词自动生成常用活用变形卡片
        card.set_word({"korean": "듣다", "meaning": "听", "pos": "动词"})
        assert not card._conjugation_box.isHidden(), "动词 듣다 背面应当展示常用活用变形卡片"
        assert card._conj_capsules_layout.count() >= 5, "常用活用变形胶囊数量应当 >= 5"
        log("  ✓ Conjugation Box widget rendered correctly on verb back.")

        # 5.2 i-dle 歌词排版与语法注解
        card.set_word(tomboy_word)
        assert card._example_title_label.text() == "📝 核心语法与关键词拆解"
        assert not card._example_box.isHidden()
        log("  ✓ i-dle Lyric Penmanship view and grammar notes rendered correctly.")

        # [Test 6] 验证 ClipboardToast 双语智能联动微气泡
        log("\n[Test 6] Testing ClipboardToast UI & Actions...")
        toast = ClipboardToast()
        mock_payload = {
            "source_text": "사랑스럽다",
            "translated_text": "可爱 / 惹人喜爱",
            "direction": "🇰🇷 韩 ➔ 🇨🇳 中",
            "is_korean": True,
            "details": {"pronunciation": "sarangseureopda"}
        }
        toast.show_clip_data(mock_payload)
        assert not toast.isHidden()
        assert "사랑스럽다" in toast._kr_label.text()
        assert "可爱" in toast._info_label.text()
        
        # 验证深入翻译信号
        deep_trans_received = []
        toast.translate_requested.connect(lambda q: deep_trans_received.append(q))
        toast._on_deep_translate_clicked()
        assert len(deep_trans_received) == 1 and deep_trans_received[0] == "사랑스럽다"
        log("  ✓ ClipboardToast displayed, dual-language rendered, and deep translation link verified.")
        
        toast._auto_close_timer.stop()
        toast.close()
        toast.deleteLater()

        log("\n[SUCCESS] ALL ADVANCED i-dle & CLIPBOARD SMART LINK TESTS PASSED 100%.")
        return 0

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
        return 1
    finally:
        with open("test_conjugator_clipboard_idle.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))


if __name__ == "__main__":
    code = test()
    sys.exit(code)
