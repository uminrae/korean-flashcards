# core/state_manager.py
"""状态持久化（SQLite）：保存窗口位置、透明度、当前进度与今日已学统计"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Any, Optional, Set


from config.settings import DEFAULT_SHORTCUTS


class StateManager:
    """键值对持久化，基于 SQLite"""

    DEFAULTS = {
        "current_book":       "1",
        "current_unit":       "0",
        "current_lesson":     "0",
        "current_index":      "0",
        "review_mode":        "0",
        "window_x":           "100",
        "window_y":           "100",
        "window_width":       "380",
        "window_height":      "300",
        "opacity":            "0.92",
        "compact_mode":       "0",
        "theme":              "dark",
        "shortcuts_enabled":  "0",  # 默认禁用所有快捷键（纯鼠标防冲突模式）
        "custom_shortcuts":   json.dumps(DEFAULT_SHORTCUTS), # 自定义按键映射
        "korean_font":        "Malgun Gothic",
        "font_scale":         "1.0",        # 卡片文字大小缩放 (1.0, 1.2, 1.4, 1.6)
        "shuffle_mode":       "0",
        "autoplay_interval":  "0",
        "auto_speak":         "1",
        "last_word_id":       "0",
        "last_word_korean":   "",
        "last_study_date":    "",
        "today_viewed_words": "[]",
        "minimize_to_tray":   "1",  # 默认关闭时最小化到系统托盘
        "autostart":          "0",  # 开机自启状态
        "audio_first_mode":   "0",  # 盲听磨耳朵模式
        "review_batch_size":  "20", # 智能复习单次默认词数
    }

    def __init__(self, db_path: str = "config/korean_cards.db"):
        from utils.path_helper import get_data_path
        if not os.path.isabs(db_path):
            db_path = get_data_path(db_path)
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_state (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS word_study_records (
                    word_id TEXT PRIMARY KEY,
                    korean TEXT,
                    status TEXT,
                    seen_count INTEGER DEFAULT 1,
                    unfamiliar_count INTEGER DEFAULT 0,
                    mastered_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 写入默认值（仅当 key 不存在时）
            for k, v in self.DEFAULTS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO app_state (key, value) VALUES (?, ?)",
                    (k, v)
                )
            conn.commit()

    def get(self, key: str, default: Any = None) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_state WHERE key = ?", (key,)
            ).fetchone()
        if row:
            return row[0]
        return self.DEFAULTS.get(key, default)

    def set(self, key: str, value: Any):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
                (key, str(value))
            )
            conn.commit()

    def set_many(self, mapping: dict):
        """单事务批量保存多个配置键值对，彻底消除多次磁盘 fsync 延迟"""
        if not mapping:
            return
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
                [(str(k), str(v)) for k, v in mapping.items()]
            )
            conn.commit()

    def get_window_pos(self) -> tuple[int, int]:
        x = self.get_int("window_x", 100)
        y = self.get_int("window_y", 100)
        return (x, y)

    def set_window_pos(self, x: int, y: int):
        self.set("window_x", x)
        self.set("window_y", y)

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self.get(key, "1" if default else "0") == "1"

    def save_window_state(self, x: int, y: int, width: int, height: int,
                          opacity: float, compact: bool, theme: str):
        """一次性保存窗口状态（含尺寸）"""
        self.set("window_x",      x)
        self.set("window_y",      y)
        self.set("window_width",  width)
        self.set("window_height", height)
        self.set("opacity",       opacity)
        self.set("compact_mode",  "1" if compact else "0")
        self.set("theme",         theme)

    def save_progress(self, book: int, unit: int, lesson: int, index: int,
                      word_id: Any = 0, word_korean: str = "",
                      review_mode: bool = False):
        """保存学习进度与具体断点位置（含词书、单元、课程、索引及单词标识）"""
        self.set("current_book", str(book))
        self.set("last_book", str(book))
        self.set("current_unit", str(unit))
        self.set("last_unit", str(unit))
        self.set("current_lesson", str(lesson))
        self.set("last_lesson", str(lesson))
        self.set("current_index", str(index))
        self.set("last_card_index", str(index))
        if word_id:
            self.set("last_word_id", str(word_id))
        if word_korean:
            self.set("last_word_korean", str(word_korean))
        self.set("review_mode", "1" if review_mode else "0")

    # ─────────────────────────────────────────────────────────
    # 今日背诵计数与跨天去重统计
    # ─────────────────────────────────────────────────────────

    def get_today_words(self) -> Set[str]:
        """获取今天已学的单词集合（去重，跨天自动重置为 0）"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        last_date = self.get("last_study_date", "")
        if last_date != today_str:
            self.set("last_study_date", today_str)
            self.set("today_viewed_words", "[]")
            return set()
        try:
            raw = self.get("today_viewed_words", "[]")
            return set(json.loads(raw))
        except Exception:
            return set()

    def record_study_word(self, word_korean: str) -> int:
        """记录今天浏览/学习过的单词（按韩语原词唯一去重），返回今日已学总数"""
        if not word_korean or word_korean in ["⭐ 生词本为空", "empty_vocab", "empty_hint"]:
            return len(self.get_today_words())
        today_str = datetime.now().strftime("%Y-%m-%d")
        words = self.get_today_words()
        if word_korean not in words:
            words.add(word_korean)
            self.set("last_study_date", today_str)
            self.set("today_viewed_words", json.dumps(list(words), ensure_ascii=False))
            try:
                from core.statistics_manager import StatisticsManager
                stats = StatisticsManager(self.db_path)
                stats.sync_today_count(len(words), today_str)
            except Exception as e:
                pass
        return len(words)

    def get_today_count(self) -> int:
        """获取今日已学不重复单词数"""
        return len(self.get_today_words())

    # ─────────────────────────────────────────────────────────
    # 自定义快捷键读写
    # ─────────────────────────────────────────────────────────

    def get_shortcuts(self) -> dict:
        """获取当前配置的自定义快捷键映射字典"""
        raw = self.get("custom_shortcuts", "")
        result = dict(DEFAULT_SHORTCUTS)
        if raw:
            try:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    result.update(loaded)
            except Exception:
                pass
        return result

    def save_shortcuts(self, shortcuts: dict):
        """保存自定义快捷键映射字典"""
        if isinstance(shortcuts, dict):
            self.set("custom_shortcuts", json.dumps(shortcuts, ensure_ascii=False))

    # ─────────────────────────────────────────────────────────
    # 单词学习轨迹与加权复习状态
    # ─────────────────────────────────────────────────────────

    def record_word_action(self, word_id: Any, korean: str, action: str):
        """
        记录单词的学习行为：
        action: 'seen' (浏览/已学), 'unfamiliar' (不熟/生词), 'mastered' (已掌握)
        """
        if not word_id or str(word_id) in ["empty_vocab", "empty_hint", "0"]:
            return
        wid_str = str(word_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status, seen_count, unfamiliar_count, mastered_count FROM word_study_records WHERE word_id = ?",
                (wid_str,)
            ).fetchone()

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if row:
                cur_status, seen_c, unfam_c, mast_c = row
                if action == "unfamiliar":
                    conn.execute(
                        """UPDATE word_study_records SET 
                           status = 'unfamiliar', 
                           unfamiliar_count = ?, 
                           seen_count = ?,
                           last_updated = ? 
                           WHERE word_id = ?""",
                        (unfam_c + 1, seen_c + 1, now_str, wid_str)
                    )
                elif action == "mastered":
                    conn.execute(
                        """UPDATE word_study_records SET 
                           status = 'mastered', 
                           mastered_count = ?, 
                           seen_count = ?,
                           last_updated = ? 
                           WHERE word_id = ?""",
                        (mast_c + 1, seen_c + 1, now_str, wid_str)
                    )
                else: # 'seen'
                    conn.execute(
                        """UPDATE word_study_records SET 
                           seen_count = ?, 
                           last_updated = ? 
                           WHERE word_id = ?""",
                        (seen_c + 1, now_str, wid_str)
                    )
            else:
                initial_status = action if action in ["unfamiliar", "mastered"] else "seen"
                unfam_c = 1 if action == "unfamiliar" else 0
                mast_c = 1 if action == "mastered" else 0
                conn.execute(
                    """INSERT INTO word_study_records 
                       (word_id, korean, status, seen_count, unfamiliar_count, mastered_count, last_updated) 
                       VALUES (?, ?, ?, 1, ?, ?, ?)""",
                    (wid_str, korean, initial_status, unfam_c, mast_c, now_str)
                )
            conn.commit()

        if action == "mastered":
            try:
                from core.statistics_manager import StatisticsManager
                stats = StatisticsManager(self.db_path)
                stats.record_study_activity(words_delta=0, mastered_delta=1)
            except Exception:
                pass

    def get_word_study_status(self, word_id: Any) -> str:
        """获取指定单词的学习状态 ('unfamiliar', 'mastered', 'seen', 或 'new')"""
        if not word_id:
            return "new"
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM word_study_records WHERE word_id = ?",
                (str(word_id),)
            ).fetchone()
        return row[0] if row else "new"

    def get_all_study_records(self) -> dict:
        """获取所有单词的学习记录字典 {word_id: {'status': str, 'seen_count': int, ...}}"""
        result = {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT word_id, korean, status, seen_count, unfamiliar_count, mastered_count, last_updated FROM word_study_records"
            ).fetchall()
        for r in rows:
            result[r[0]] = {
                "word_id": r[0],
                "korean": r[1],
                "status": r[2],
                "seen_count": r[3],
                "unfamiliar_count": r[4],
                "mastered_count": r[5],
                "last_updated": r[6],
            }
        return result

    def get_study_status_counts(self) -> dict:
        """获取词汇学习状态汇总统计"""
        with self._connect() as conn:
            unfam = conn.execute("SELECT COUNT(*) FROM word_study_records WHERE status = 'unfamiliar'").fetchone()[0]
            mast = conn.execute("SELECT COUNT(*) FROM word_study_records WHERE status = 'mastered'").fetchone()[0]
            seen = conn.execute("SELECT COUNT(*) FROM word_study_records WHERE status = 'seen'").fetchone()[0]
        return {
            "unfamiliar": unfam,
            "mastered": mast,
            "seen": seen,
            "total_studied": unfam + mast + seen,
        }

    def get_review_batch_size(self) -> int:
        return self.get_int("review_batch_size", 20)

    def set_review_batch_size(self, size: int):
        self.set("review_batch_size", str(max(5, min(100, size))))
