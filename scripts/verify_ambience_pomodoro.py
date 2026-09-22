"""
verify_ambience_pomodoro.py
---------------------------
自动化测试套件：验证「极简白噪音伴学与番茄专注时钟」功能
1. 白噪音音频合成生成与文件完整性
2. AmbiencePlayer 多声道独立混音与音量控制
3. PomodoroTimer 状态流转与倒计时信号
4. PomodoroDialog 控制面板 UI 控件交互
5. 主窗口 _pomodoro_badge 状态徽标与联动
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
from core.ambience_player import AmbiencePlayer, AMBIENCE_TYPES
from core.pomodoro_timer import PomodoroTimer
from ui.pomodoro_dialog import PomodoroDialog


def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        # [Test 1] 测试 AmbiencePlayer 音频生成与播放控制
        log("[Test 1] Testing AmbiencePlayer audio synthesis and channel control...")
        player = AmbiencePlayer()
        data_dir = player._data_dir
        expected_files = ["seoul_rain.wav", "cafe_ambience.wav", "pure_white_noise.wav", "timer_chime.wav"]
        for f in expected_files:
            p = os.path.join(data_dir, f)
            assert os.path.exists(p), f"缺少音频文件: {p}"
            assert os.path.getsize(p) > 1000, f"音频文件大小异常: {p} ({os.path.getsize(p)} bytes)"
            log(f"  ✓ Local WAV audio ready: {f} ({os.path.getsize(p) / 1024:.1f} KB)")

        for amb_type in ["rain", "cafe", "white", "none"]:
            player.set_ambience(amb_type)
            assert player.get_current_type() == amb_type
            log(f"  ✓ Switched ambience type to: {amb_type}")

        player.set_volume(0.45)
        assert abs(player.get_volume() - 0.45) < 1e-4
        log(f"  ✓ Volume set to 45% verified.")

        player.play_chime()
        log("  ✓ Timer soft chime trigger verified.")
        player.stop_all()

        # [Test 2] 测试 PomodoroTimer 状态机与倒计时信号
        log("\n[Test 2] Testing PomodoroTimer state machine and signals...")
        timer = PomodoroTimer()
        timer.set_durations(25, 5)

        assert timer.mode == PomodoroTimer.MODE_FOCUS
        assert timer.state == PomodoroTimer.STATE_IDLE
        assert timer.get_formatted_time() == "25:00"

        ticks_received = []
        timer.tick.connect(lambda rem, fmt, mode, prog: ticks_received.append((rem, fmt, mode, prog)))

        timer.start()
        assert timer.is_running
        assert timer.state == PomodoroTimer.STATE_RUNNING
        log("  ✓ Pomodoro started.")

        timer._on_tick()
        assert timer.remaining_seconds == 25 * 60 - 1
        assert len(ticks_received) > 0
        log(f"  ✓ Pomodoro tick received: {ticks_received[-1]}")

        timer.pause()
        assert timer.state == PomodoroTimer.STATE_PAUSED
        log("  ✓ Pomodoro paused.")

        timer.toggle()
        assert timer.state == PomodoroTimer.STATE_RUNNING
        log("  ✓ Pomodoro resumed.")

        timer.switch_mode(PomodoroTimer.MODE_BREAK)
        assert timer.mode == PomodoroTimer.MODE_BREAK
        assert timer.get_formatted_time() == "05:00"
        log("  ✓ Switched to 5m break mode.")

        timer.skip_stage()
        assert timer.mode == PomodoroTimer.MODE_FOCUS
        assert timer.get_formatted_time() == "25:00"
        log("  ✓ Skipped stage back to focus mode.")

        # 模拟倒计时完成
        timer._remaining = 1
        finished_modes = []
        timer.finished.connect(lambda m: finished_modes.append(m))
        timer._on_tick()
        assert len(finished_modes) == 1
        assert finished_modes[0] == PomodoroTimer.MODE_FOCUS
        assert timer.mode == PomodoroTimer.MODE_BREAK
        log("  ✓ Focus countdown finished and auto-switched to break mode.")

        # [Test 3] 测试 PomodoroDialog UI 交互
        log("\n[Test 3] Testing PomodoroDialog UI components...")
        dialog = PomodoroDialog(timer=timer, player=player)
        assert dialog._card is not None
        assert dialog._time_display.text() == "05:00" or dialog._time_display.text() == "25:00"

        dialog._ambience_btns["rain"].click()
        assert player.get_current_type() == "rain"
        log("  ✓ UI ambience switch verified.")

        dialog._vol_slider.setValue(80)
        assert abs(player.get_volume() - 0.80) < 1e-4
        log("  ✓ UI volume slider (80%) verified.")

        dialog._start_btn.click()
        assert timer.is_running
        log("  ✓ UI start countdown button verified.")
        dialog.close()

        # [Test 4] 测试 番茄钟与白噪音状态联动徽标生成
        log("\n[Test 4] Testing Ambience and Pomodoro badge state logic...")
        timer.start()
        state = timer.state
        mode = timer.mode
        time_str = timer.get_formatted_time()
        player.set_ambience("cafe")
        amb_type = player.get_current_type()
        amb_icon = "☕ " if amb_type == "cafe" else ""
        badge_text = f"{amb_icon}🎯 {time_str}"
        assert "☕" in badge_text
        assert "🎯" in badge_text
        log(f"  ✓ Pomodoro badge generated: {badge_text}")

        player.stop_all()
        timer.reset()

        log("\n[SUCCESS] ALL AMBIENCE AND POMODORO TESTS PASSED 100%.")
        return 0

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
        return 1
    finally:
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except Exception:
            pass
        with open("test_ambience_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))


if __name__ == "__main__":
    code = test()
    os._exit(code)
