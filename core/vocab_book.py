# core/vocab_book.py
"""生词本管理（SQLite）"""

import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional


class VocabBook:
    """生词本：SQLite 存储收藏的词汇"""

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
        """初始化数据库表"""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vocab_book (
                    word_id     TEXT PRIMARY KEY,
                    korean      TEXT NOT NULL,
                    chinese     TEXT,
                    pos         TEXT,
                    added_at    TEXT NOT NULL
                )
            """)
            conn.commit()

    def add(self, word: Dict) -> bool:
        """添加单词到生词本，返回是否成功"""
        try:
            word_id = str(word.get("id") or word.get("word_id") or "")
            if not word_id:
                return False
            chinese = word.get("chinese", word.get("meaning", ""))
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO vocab_book
                       (word_id, korean, chinese, pos, added_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        word_id,
                        word.get("korean", ""),
                        chinese,
                        word.get("pos", ""),
                        word.get("added_at") or datetime.now().isoformat(),
                    )
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[VocabBook] 添加失败: {e}")
            return False

    def remove(self, word_id: str) -> bool:
        """从生词本删除"""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM vocab_book WHERE word_id = ?", (str(word_id),))
                conn.commit()
            return True
        except Exception as e:
            print(f"[VocabBook] 删除失败: {e}")
            return False

    def is_starred(self, word_id: str) -> bool:
        """检查是否已收藏"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM vocab_book WHERE word_id = ?", (str(word_id),)
            ).fetchone()
        return row is not None

    def toggle(self, word: Dict) -> bool:
        """切换收藏状态，返回操作后的状态（True=已收藏）"""
        word_id = str(word.get("id") or word.get("word_id") or "")
        if self.is_starred(word_id):
            self.remove(word_id)
            return False
        else:
            self.add(word)
            return True

    def get_all_ids(self) -> List[str]:
        """获取所有收藏词的 ID"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT word_id FROM vocab_book ORDER BY added_at DESC"
            ).fetchall()
        return [r[0] for r in rows]

    def get_all(self) -> List[Dict]:
        """获取所有收藏词的基本信息"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT word_id, korean, chinese, pos, added_at FROM vocab_book ORDER BY added_at DESC"
            ).fetchall()
        return [
            {
                "id": r[0],
                "word_id": r[0],
                "korean": r[1],
                "chinese": r[2],
                "meaning": r[2],
                "pos": r[3],
                "added_at": r[4],
            }
            for r in rows
        ]

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM vocab_book").fetchone()
        return row[0] if row else 0
