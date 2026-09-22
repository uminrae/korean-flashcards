"""
statistics_manager.py
---------------------
「未来的韩语卡片」- 学习足迹与打卡统计引擎 (基于 SQLite 持久化)
1. 记录每日背词、掌握与复习时间戳
2. 计算连续坚持天数 (Streak)、累计掌握词汇与生词消灭率
3. 输出近 60 天热力图活跃度矩阵数据 (Level 0~4)
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


from contextlib import contextmanager


class StatisticsManager:
    """学习足迹与打卡统计管理器"""

    def __init__(self, db_path: str = "config/korean_cards.db"):
        from utils.path_helper import get_data_path
        if not os.path.isabs(db_path):
            db_path = get_data_path(db_path)
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_study_stats (
                    date           TEXT PRIMARY KEY,
                    word_count     INTEGER DEFAULT 0,
                    mastered_count INTEGER DEFAULT 0,
                    review_count   INTEGER DEFAULT 0,
                    updated_at     TEXT
                )
            """)
            conn.commit()

    def record_study_activity(self, date_str: Optional[str] = None, words_delta: int = 1, mastered_delta: int = 0):
        """记录指定日期的学习活动（默认今日）"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._connect() as conn:
            row = conn.execute(
                "SELECT word_count, mastered_count FROM daily_study_stats WHERE date = ?",
                (date_str,)
            ).fetchone()

            if row:
                cur_words, cur_mast = row
                conn.execute(
                    """UPDATE daily_study_stats 
                       SET word_count = ?, mastered_count = ?, updated_at = ? 
                       WHERE date = ?""",
                    (cur_words + words_delta, cur_mast + mastered_delta, now_time, date_str)
                )
            else:
                conn.execute(
                    """INSERT INTO daily_study_stats 
                       (date, word_count, mastered_count, review_count, updated_at) 
                       VALUES (?, ?, ?, 0, ?)""",
                    (date_str, max(0, words_delta), max(0, mastered_delta), now_time)
                )
            conn.commit()

    def sync_today_count(self, count: int, date_str: Optional[str] = None):
        """精准同步指定日期的去重词数"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._connect() as conn:
            row = conn.execute(
                "SELECT mastered_count FROM daily_study_stats WHERE date = ?",
                (date_str,)
            ).fetchone()

            if row:
                conn.execute(
                    "UPDATE daily_study_stats SET word_count = ?, updated_at = ? WHERE date = ?",
                    (count, now_time, date_str)
                )
            else:
                conn.execute(
                    "INSERT INTO daily_study_stats (date, word_count, mastered_count, review_count, updated_at) VALUES (?, ?, 0, 0, ?)",
                    (date_str, count, now_time)
                )
            conn.commit()

    def get_heatmap_data(self, days: int = 60) -> List[Dict[str, Any]]:
        """
        获取近 N 天（默认 60 天）的热力图打卡矩阵数据
        返回列表，每个元素包含：date, word_count, mastered_count, level (0~4)
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        records_map = {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT date, word_count, mastered_count FROM daily_study_stats WHERE date >= ? AND date <= ?",
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            ).fetchall()
            for r in rows:
                records_map[r[0]] = {
                    "word_count": r[1],
                    "mastered_count": r[2]
                }

        result = []
        curr = start_date
        while curr <= end_date:
            d_str = curr.strftime("%Y-%m-%d")
            data = records_map.get(d_str, {"word_count": 0, "mastered_count": 0})
            cnt = data["word_count"]

            # 计算活跃度等级 Level 0~4
            if cnt <= 0:
                level = 0
            elif cnt <= 5:
                level = 1
            elif cnt <= 15:
                level = 2
            elif cnt <= 30:
                level = 3
            else:
                level = 4

            result.append({
                "date": d_str,
                "word_count": cnt,
                "mastered_count": data["mastered_count"],
                "level": level,
                "weekday": curr.weekday(), # 0=周一, 6=周日
            })
            curr += timedelta(days=1)

        return result

    def get_streak_days(self) -> int:
        """
        计算连续坚持学习天数（Streak Days）
        如果今天已有学习记录，从今天往前回溯；若今天尚未学习但昨天有，从昨天往前回溯
        """
        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")
        yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT date, word_count FROM daily_study_stats WHERE word_count > 0 ORDER BY date DESC"
            ).fetchall()

        if not rows:
            return 0

        active_dates = {r[0] for r in rows if r[1] > 0}

        # 检查起点
        if today_str in active_dates:
            check_date = today
        elif yesterday_str in active_dates:
            check_date = today - timedelta(days=1)
        else:
            return 0

        streak = 0
        while check_date.strftime("%Y-%m-%d") in active_dates:
            streak += 1
            check_date -= timedelta(days=1)

        return streak

    def get_summary_metrics(self) -> Dict[str, Any]:
        """
        获取打卡看板核心汇总指标：
        1. streak_days: 连续坚持天数
        2. total_mastered: 累计掌握词汇
        3. total_unfamiliar: 待攻克生词
        4. elimination_rate: 生词消灭率 (%)
        5. total_study_days: 累计打卡总天数
        """
        streak = self.get_streak_days()

        with self._connect() as conn:
            # 累计打卡天数
            total_days_row = conn.execute(
                "SELECT COUNT(*) FROM daily_study_stats WHERE word_count > 0"
            ).fetchone()
            total_study_days = total_days_row[0] if total_days_row else 0

            # 掌握词汇与不熟悉词汇
            try:
                mast_row = conn.execute(
                    "SELECT COUNT(*) FROM word_study_records WHERE status = 'mastered'"
                ).fetchone()
                total_mastered = mast_row[0] if mast_row else 0

                unfam_row = conn.execute(
                    "SELECT COUNT(*) FROM word_study_records WHERE status = 'unfamiliar'"
                ).fetchone()
                total_unfamiliar = unfam_row[0] if unfam_row else 0
            except Exception:
                total_mastered = 0
                total_unfamiliar = 0

        # 生词消灭率 = 掌握数 / (掌握数 + 生词数) * 100
        total_eval = total_mastered + total_unfamiliar
        if total_eval > 0:
            elimination_rate = round((total_mastered / total_eval) * 100, 1)
        elif total_mastered > 0:
            elimination_rate = 100.0
        else:
            elimination_rate = 0.0

        return {
            "streak_days": streak,
            "total_mastered": total_mastered,
            "total_unfamiliar": total_unfamiliar,
            "elimination_rate": elimination_rate,
            "total_study_days": total_study_days,
        }
