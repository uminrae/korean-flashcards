"""
run_all_tests.py
----------------
一键执行全部 8 大核心功能自动化测试套件
"""

import subprocess
import sys
import os

TEST_SCRIPTS = [
    "verify_minibar_shortcuts_polish.py",
    "verify_interactive_lyrics_clipboard_hardening.py",
    "verify_translator_drawer.py",
    "verify_nuance_theme_backup.py",
    "verify_conjugator_clipboard_idle.py",
    "verify_ui_v11.py",
    "verify_collocations_antonyms.py",
    "verify_ambience_pomodoro.py",
    "verify_lyric_quotes.py",
    "verify_pronunciation_rules.py",
    "verify_sentence_particles.py",
    "verify_spelling_quiz.py",
    "verify_copybook_generator.py",
    "verify_statistics_heatmap.py",
]

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    all_passed = True
    results = []

    print("══════════════════════════════════════════════════════════════")
    print(" 🚀 正在执行全部 8 大自动化测试套件...")
    print("══════════════════════════════════════════════════════════════\n")

    for script in TEST_SCRIPTS:
        script_path = os.path.join(base_dir, script)
        cmd = [sys.executable, "-X", "utf8", script_path]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode == 0:
            results.append((script, True, "PASS"))
            print(f"  ✅ [PASS] {script}")
        else:
            results.append((script, False, res.stderr or res.stdout))
            print(f"  ❌ [FAIL] {script}")
            print(res.stdout)
            print(res.stderr)
            all_passed = False

    print("\n══════════════════════════════════════════════════════════════")
    if all_passed:
        print(" 🎉 全部 8 大测试套件 100% PASS！系统稳健可靠！")
    else:
        print(" ⚠️ 存在未通过测试，请检查上方日志。")
    print("══════════════════════════════════════════════════════════════")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
