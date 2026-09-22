# -*- coding: utf-8 -*-
"""
verify_nuance_theme_backup.py
-----------------------------
自动化测试套件：验证 3 大全新特性
1. 易混近义词与语境辨析模块 (Synonym & Nuance Diff)
2. 多套 Instagram 极简磨砂质感主题预设 (4 Theme Presets)
3. 学习数据本地备份与外部词库批量导入 (Data Sync & Vocab Import)
"""

import sys
import os
import json
import tempfile
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from config.settings import THEME_CONFIGS
from core.vocab_manager import VocabManager
from core.state_manager import StateManager
from core.vocab_book import VocabBook
from core.backup_manager import export_user_backup, import_user_backup
from core.vocab_importer import parse_csv_or_txt, import_custom_vocab
from ui.card_widget import CardWidget
from ui.toolbar_widget import ToolbarWidget


def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 验证易混近义词与语境辨析模块 (Nuance Diff)
        log("[Test 1] Testing Synonym & Nuance Diff module...")
        vm = VocabManager()
        vm.load()

        # 查找带有 nuance_diff 的词
        nuance_words = [w for w in vm.all_words if w.get("nuance_diff")]
        assert len(nuance_words) >= 10, f"带有 nuance_diff 的词汇数量不足: {len(nuance_words)}"
        
        sample_w = next(w for w in nuance_words if "공부하다" in w["korean"] or "보다" in w["korean"] or "크다" in w["korean"])
        log(f"  ✓ Found nuance diff word: {sample_w['korean']} -> {sample_w['nuance_diff']}")

        card = CardWidget()
        card.set_word(sample_w)
        
        assert not card._nuance_btn.isHidden(), "带 nuance_diff 的词背面应展示 _nuance_btn"
        assert "语境辨析" in card._nuance_text_label.text()
        
        # 测试点击展开
        card._toggle_nuance_box()
        assert not card._nuance_box.isHidden(), "点击后 _nuance_box 应当处于展开可见状态"
        card._toggle_nuance_box()
        assert card._nuance_box.isHidden(), "再次点击后 _nuance_box 应当处于折叠隐藏状态"
        log("  ✓ Nuance Diff UI button and expandable box verified.")

        # [Test 2] 验证 4 大 Instagram 磨砂质感主题预设
        log("\n[Test 2] Testing 4 Instagram Theme Presets...")
        required_themes = ["seoul_night", "cream_latte", "matcha_mint", "night_violet"]
        toolbar = ToolbarWidget()
        
        for t_id in required_themes:
            assert t_id in THEME_CONFIGS, f"缺失主题配置: {t_id}"
            cfg = THEME_CONFIGS[t_id]
            assert "bg_color" in cfg and "accent" in cfg and "name" in cfg
            
            # 动态应用主题到 Card 和 Toolbar
            card.apply_theme(t_id)
            toolbar.apply_theme(t_id)
            assert card._theme == t_id
            assert toolbar._theme == t_id
            log(f"  ✓ Theme '{t_id}' ({cfg['name']}) verified: accent={cfg['accent']}")

        log("  ✓ Dynamic theme switching across all UI components verified.")

        # [Test 3] 验证用户学习数据一键备份与恢复
        log("\n[Test 3] Testing User Data Backup & Restore...")
        tmp_backup_file = os.path.join(tempfile.gettempdir(), "test_korean_backup.json")
        if os.path.exists(tmp_backup_file):
            os.remove(tmp_backup_file)

        vb = VocabBook()
        vb.add({"id": "test_01", "korean": "행복", "chinese": "幸福"})
        vm._mastered_ids.add("1_1_01")
        sm = StateManager()
        sm.set("current_book", "2")
        sm.set("theme", "matcha_mint")

        # 导出备份
        ok, msg, summary = export_user_backup(tmp_backup_file, vb, vm, sm)
        assert ok, f"导出备份失败: {msg}"
        assert os.path.exists(tmp_backup_file), "备份文件未成功创建"
        log(f"  ✓ Exported backup file: {summary}")

        # 校验 JSON 结构
        with open(tmp_backup_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "starred_items" in data and "mastered_ids" in data and "progress" in data
        assert data["settings"]["theme"] == "matcha_mint"

        # 模拟导入恢复
        ok, msg, restore_summary = import_user_backup(tmp_backup_file, vb, vm, sm)
        assert ok, f"导入恢复失败: {msg}"
        assert restore_summary["mastered_count"] >= 1
        log(f"  ✓ Restored backup successfully: {restore_summary}")

        if os.path.exists(tmp_backup_file):
            os.remove(tmp_backup_file)

        # [Test 4] 验证外部词库批量导入解析 (CSV / TXT)
        log("\n[Test 4] Testing External Vocab Batch Importer...")
        tmp_csv = os.path.join(tempfile.gettempdir(), "custom_test_vocab.csv")
        csv_content = (
            "韩文,音标,词性,中文释义,例句\n"
            "설레다,seolleda,动词,心动 / 激动,마음이 설레요.\n"
            "반짝거리다,banjjakgeorida,动词,闪闪发光,별이 반짝거린다.\n"
            "포근하다,pogeunhada,形容词,温暖 / 舒适,날씨가 포근해요.\n"
        )
        with open(tmp_csv, "w", encoding="utf-8-sig") as f:
            f.write(csv_content)

        parsed_words = parse_csv_or_txt(tmp_csv)
        assert len(parsed_words) == 3, f"解析词汇数量不匹配: {len(parsed_words)}"
        assert parsed_words[0]["korean"] == "설레다"
        assert parsed_words[0]["meaning"] == "心动 / 激动"
        log(f"  ✓ Parsed {len(parsed_words)} words from CSV file.")

        ok, count, b_title, msg = import_custom_vocab(tmp_csv, custom_book_name="测试导入词书")
        assert ok, f"词库批量导入失败: {msg}"
        assert count == 3
        log(f"  ✓ Imported and archived custom vocab book: {count} words ({b_title}).")

        if os.path.exists(tmp_csv):
            os.remove(tmp_csv)

        log("\n[SUCCESS] ALL 3 NEW MAJOR FEATURE TESTS PASSED 100%.")
        return 0

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
        return 1
    finally:
        with open("test_nuance_theme_backup.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))


if __name__ == "__main__":
    code = test()
    sys.exit(code)
