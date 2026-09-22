# core/backup_manager.py
# -*- coding: utf-8 -*-
"""用户数据一键备份与恢复模块
支持全量导出/导入：
1. 生词本收藏列表（含完整韩文、释义、例句与元数据）
2. 单词已掌握状态（Mastered IDs）
3. 当前学习断点进度（册数、单元、课程、单词位置）
4. 今日学习统计与历史打卡数据
5. 个性化偏好（字体、字号、主题、快捷键开关、托盘驻留等）
"""

import json
import os
from datetime import datetime
from typing import Tuple, Dict, Any


def export_user_backup(
    file_path: str,
    vocab_book,
    vocab_manager,
    state_manager
) -> Tuple[bool, str, Dict[str, Any]]:
    """导出用户全部学习数据与设置为 JSON 备份文件"""
    try:
        # 1. 生词本列表
        starred_items = vocab_book.get_all() if vocab_book else []

        # 2. 已掌握词汇 ID 集合
        mastered_ids = list(getattr(vocab_manager, "_mastered_ids", set())) if vocab_manager else []

        # 3. 学习进度与状态
        progress_data = {
            "current_book": state_manager.get("current_book", "1") if state_manager else "1",
            "current_unit": state_manager.get("current_unit", "0") if state_manager else "0",
            "current_lesson": state_manager.get("current_lesson", "0") if state_manager else "0",
            "current_index": state_manager.get("current_index", "0") if state_manager else "0",
            "last_word_id": state_manager.get("last_word_id", "0") if state_manager else "0",
            "last_word_korean": state_manager.get("last_word_korean", "") if state_manager else "",
            "review_mode": state_manager.get("review_mode", "0") if state_manager else "0",
            "shuffle_mode": state_manager.get("shuffle_mode", "0") if state_manager else "0",
        }

        # 4. 今日学习打卡统计
        stats_data = {
            "last_study_date": state_manager.get("last_study_date", "") if state_manager else "",
            "today_viewed_words": list(state_manager.get_today_words()) if state_manager else [],
        }

        # 5. 用户偏好设置
        settings_data = {
            "theme": state_manager.get("theme", "dark") if state_manager else "dark",
            "font_scale": state_manager.get("font_scale", "1.0") if state_manager else "1.0",
            "korean_font": state_manager.get("korean_font", "Malgun Gothic") if state_manager else "Malgun Gothic",
            "shortcuts_enabled": state_manager.get("shortcuts_enabled", "0") if state_manager else "0",
            "custom_shortcuts": state_manager.get("custom_shortcuts", "") if state_manager else "",
            "minimize_to_tray": state_manager.get("minimize_to_tray", "1") if state_manager else "1",
            "autoplay_interval": state_manager.get("autoplay_interval", "0") if state_manager else "0",
            "auto_speak": state_manager.get("auto_speak", "1") if state_manager else "1",
            "compact_mode": state_manager.get("compact_mode", "0") if state_manager else "0",
            "audio_first_mode": state_manager.get("audio_first_mode", "0") if state_manager else "0",
        }

        backup_payload = {
            "app_name": "KoreanVocabCard",
            "version": "1.0.0",
            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "starred_items": starred_items,
            "mastered_ids": mastered_ids,
            "progress": progress_data,
            "stats": stats_data,
            "settings": settings_data,
        }

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, ensure_ascii=False, indent=2)

        summary = {
            "starred_count": len(starred_items),
            "mastered_count": len(mastered_ids),
            "export_time": backup_payload["export_time"],
        }
        return True, "备份导出成功！", summary

    except Exception as e:
        return False, f"备份导出失败：{str(e)}", {}


def import_user_backup(
    file_path: str,
    vocab_book,
    vocab_manager,
    state_manager
) -> Tuple[bool, str, Dict[str, Any]]:
    """从备份 JSON 文件恢复用户数据与状态"""
    if not os.path.exists(file_path):
        return False, "备份文件不存在！", {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or ("starred_items" not in data and "progress" not in data):
            return False, "非法的备份文件格式！", {}

        # 1. 恢复生词本
        starred_items = data.get("starred_items", [])
        if vocab_book is not None:
            # 清空当前生词本后重新灌入
            current_all = vocab_book.get_all()
            for w in current_all:
                if "id" in w:
                    vocab_book.remove(w["id"])
            for w in starred_items:
                vocab_book.add(w)

        # 2. 恢复已掌握词汇
        mastered_ids = data.get("mastered_ids", [])
        if vocab_manager is not None:
            vocab_manager._mastered_ids = set(str(x) for x in mastered_ids)

        # 3. 恢复学习进度与配置到 StateManager
        if state_manager is not None:
            progress = data.get("progress", {})
            for k, v in progress.items():
                state_manager.set(k, str(v))

            stats = data.get("stats", {})
            if "last_study_date" in stats:
                state_manager.set("last_study_date", str(stats["last_study_date"]))
            if "today_viewed_words" in stats:
                state_manager.set("today_viewed_words", json.dumps(stats["today_viewed_words"], ensure_ascii=False))

            settings = data.get("settings", {})
            for k, v in settings.items():
                state_manager.set(k, str(v))

        summary = {
            "starred_count": len(starred_items),
            "mastered_count": len(mastered_ids),
            "export_time": data.get("export_time", "未知"),
        }
        return True, "数据还原成功！", summary

    except Exception as e:
        return False, f"还原数据时发生错误：{str(e)}", {}
