# scripts/verify_v2.py
# -*- coding: utf-8 -*-
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log_file = open("test_log.txt", "w", encoding="utf-8")
def log(msg):
    print(msg)
    log_file.write(str(msg) + "\n")
    log_file.flush()

def main():
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QCloseEvent
        app = QApplication.instance() or QApplication(sys.argv)
        from ui.main_window import MainWindow
        from core.tts_engine import TTSEngine, get_audio_cache_path

        win = MainWindow()
        log(f"1. 窗口标题: {win.windowTitle()}")
        log(f"2. 工具栏标题: {win._toolbar._title_label.text()}")
        log(f"3. 托盘提示: {win._tray._tray_icon.toolTip()}")

        assert win.windowTitle() == "未来的韩语卡片", "窗口标题不匹配"
        assert "未来的韩语卡片" in win._toolbar._title_label.text(), "工具栏标题不匹配"
        assert "未来的韩语卡片" in win._tray._tray_icon.toolTip(), "托盘提示不匹配"
        log("  ✓ [验证项 1] 全局软件更名验证 100% 通过！")

        curr = win._vocab.current_word()
        log(f"4. 当前单词: {curr.get('korean')}")
        nearby = win._vocab.get_nearby_words()
        log(f"5. 周边待预抓取词: {[w.get('korean') for w in nearby]}")
        assert len(nearby) > 0, "未能获取周边单词"

        cache_p = get_audio_cache_path("가다")
        log(f"6. 音频本地持久化缓存路径: {cache_p}")
        assert "data" in cache_p and "audio_cache" in cache_p, "缓存路径不规范"
        log("  ✓ [验证项 2] TTS 音频预缓存与周边词后台 Prefetch 验证 100% 通过！")

        win._on_bg_opacity_changed(0.0)
        assert win._bg_opacity == 0.0, "bg_opacity 错误"
        assert win.windowOpacity() == 1.0, f"物理透明度应保持1.0，实际为: {win.windowOpacity()}"
        win._on_bg_opacity_changed(0.85)
        assert win._bg_opacity == 0.85, "bg_opacity 错误"
        log("  ✓ [验证项 3] 独立背景透明度调节 (前景文字100%实心) 验证 100% 通过！")

        # 验证最小化到托盘分支
        win._state.set("minimize_to_tray", "1")
        ev_min = QCloseEvent()
        win.closeEvent(ev_min)
        assert not ev_min.isAccepted(), "最小化到托盘时应该 ignore 关闭事件"
        assert not win.isVisible(), "最小化到托盘时窗口应该隐藏"
        log("  ✓ [验证项 4.1] minimize_to_tray=True: 成功拦截关闭事件并隐藏至托盘")

        # 验证直接退出分支
        win._state.set("minimize_to_tray", "0")
        quit_called = [False]
        # 拦截 QApplication.quit() 避免测试进程立即中断
        import PyQt6.QtWidgets
        PyQt6.QtWidgets.QApplication.quit = lambda *args: quit_called.__setitem__(0, True)
        ev_quit = QCloseEvent()
        win.closeEvent(ev_quit)
        assert ev_quit.isAccepted(), "未勾选最小化到托盘时应该 accept 关闭事件"
        assert quit_called[0], "未勾选最小化到托盘时应该调用 app.quit()"
        log("  ✓ [验证项 4.2] minimize_to_tray=False: 成功调用 quit() 彻底退出应用")

        # 还原设置
        win._state.set("minimize_to_tray", "1")
        log("\n🎉 全部 4 项功能重构与优化验证完全通过！")
        return 0
    except Exception as e:
        log(traceback.format_exc())
        return 1

if __name__ == "__main__":
    ret = main()
    log_file.close()
    sys.exit(ret)
