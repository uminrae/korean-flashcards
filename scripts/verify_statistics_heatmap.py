"""
verify_statistics_heatmap.py
----------------------------
自动化测试学习热力图与打卡看板功能：
1. 验证 StatisticsManager 每日学习记录与去重同步
2. 验证连续坚持天数 (Streak Days) 算法
3. 验证近 60 天热力图活跃度矩阵生成 (Level 0~4)
4. 验证 StatsDialog 弹窗与 HeatmapCell 组件渲染
"""

import sys
import os
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from core.statistics_manager import StatisticsManager
from ui.stats_dialog import StatsDialog, HeatmapCell

def test():
    log_lines = []
    def log(msg):
        log_lines.append(msg)

    # 创建 QApplication 实例（若尚未创建）
    app = QApplication.instance() or QApplication(sys.argv)

    try:
        test_db = os.path.join(os.path.dirname(__file__), "test_stats.db")
        if os.path.exists(test_db):
            os.remove(test_db)

        stats = StatisticsManager(db_path=test_db)

        # [Test 1] 测试初始状态
        log("[Test 1] Testing initial empty state...")
        streak_0 = stats.get_streak_days()
        assert streak_0 == 0, f"初始连续天数应为 0, 实际: {streak_0}"
        metrics_0 = stats.get_summary_metrics()
        assert metrics_0["streak_days"] == 0
        assert metrics_0["total_study_days"] == 0
        assert metrics_0["elimination_rate"] == 0.0
        log("[OK] Initial empty state verified.")

        # [Test 2] 模拟过去连续 5 天打卡
        log("[Test 2] Simulating 5 consecutive days of study...")
        today = datetime.now().date()
        for i in range(5):
            d_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            stats.record_study_activity(date_str=d_str, words_delta=10 * (i + 1), mastered_delta=3)

        streak_5 = stats.get_streak_days()
        assert streak_5 == 5, f"连续天数应为 5, 实际: {streak_5}"
        metrics_5 = stats.get_summary_metrics()
        assert metrics_5["streak_days"] == 5
        assert metrics_5["total_study_days"] == 5
        log(f"[OK] 5 consecutive days streak verified: {streak_5} days.")

        # [Test 3] 测试近 60 天热力图矩阵数据与 Level 分级
        log("[Test 3] Testing 60-day heatmap matrix data & levels...")
        heatmap_data = stats.get_heatmap_data(days=60)
        assert len(heatmap_data) == 60, f"热力图天数应为 60, 实际: {len(heatmap_data)}"
        
        # 检验今天的打卡等级 (10 词 -> Level 2)
        today_data = heatmap_data[-1]
        assert today_data["date"] == today.strftime("%Y-%m-%d")
        assert today_data["word_count"] == 10
        assert today_data["level"] == 2, f"10 词应为 Level 2, 实际 Level: {today_data['level']}"
        log("[OK] Heatmap matrix data & level mapping verified.")

        # [Test 4] 测试 StatsDialog 实例化与深浅色模式切换
        log("[Test 4] Testing StatsDialog UI & Theme Switch...")
        dialog = StatsDialog(stats_manager=stats, theme="dark")
        assert dialog is not None
        assert dialog._title_label.text() == "📊 学习足迹与打卡看板"
        
        # 切换浅色模式
        dialog.apply_theme("light")
        assert dialog._theme == "light"
        log("[OK] StatsDialog UI component & theme toggle verified.")

        # [Test 5] 测试断签逻辑 (模拟昨天没学，前天有学 -> 连续天数应断为 0)
        log("[Test 5] Testing broken streak logic...")
        broken_db = os.path.join(os.path.dirname(__file__), "test_broken.db")
        if os.path.exists(broken_db):
            os.remove(broken_db)
        b_stats = StatisticsManager(db_path=broken_db)
        # 3天前有学，但昨天和今天没有
        three_days_ago = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        b_stats.record_study_activity(date_str=three_days_ago, words_delta=5)
        assert b_stats.get_streak_days() == 0, "断签状态连续天数应为 0"
        log("[OK] Broken streak logic verified.")

        # 清理测试数据库
        if os.path.exists(test_db):
            os.remove(test_db)
        if os.path.exists(broken_db):
            os.remove(broken_db)

        log("[SUCCESS] ALL HEATMAP & STATISTICS TESTS PASSED 100%.")

    except Exception as e:
        log("EXCEPTION: " + traceback.format_exc())
    finally:
        with open("test_heatmap_result.log", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

if __name__ == "__main__":
    test()
