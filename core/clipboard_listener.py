# -*- coding: utf-8 -*-
"""
clipboard_listener.py
---------------------
全局剪贴板智能划词监听 × 多引擎翻译联动管理器 (Clipboard Smart Link)
使用 Qt 原生 QClipboard 异步事件，0 阻塞、低资源开销
支持：
1. 捕获 1~60 字符内的中/韩文字符串
2. 自动在后台异步调用 TranslatorManager 获取地道多引擎秒级翻译
3. 触发 Instagram 极简悬浮微气泡联动
4. 一键持久化收录至 data/custom_vocab.json
"""

import os
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from core.translator_manager import TranslatorManager, is_korean_text, detect_direction


class ClipboardListener(QObject):
    """剪贴板智能划词监听与翻译联动管理器"""

    # 捕获并完成翻译信号: dict包含 source_text, translated_text, direction, details, is_korean
    clip_translated_captured = pyqtSignal(dict)
    korean_captured = pyqtSignal(str, dict) # 兼容历史接口
    vocab_saved = pyqtSignal(dict)          # 成功收录生词信号

    def __init__(self, vocab_manager=None, parent=None):
        super().__init__(parent)
        self._vocab_manager = vocab_manager
        self._enabled = True
        self._last_clip_text = ""
        self._seen_history: Dict[str, float] = {}  # 文本 -> 上次捕获时间戳
        self._translator = TranslatorManager(self)
        self._translator.translation_completed.connect(self._on_translation_completed)
        self._pending_raw_text = ""

        self._clipboard = QApplication.clipboard()
        if self._clipboard:
            self._clipboard.dataChanged.connect(self._on_clipboard_changed)

    def toggle_enabled(self) -> bool:
        self._enabled = not self._enabled
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def process_text(self, text: str) -> bool:
        """处理文本过滤、防抖与翻译分发，返回是否成功捕获"""
        if not self._enabled:
            return False
        if not text:
            return False
        text = text.strip()
        if not text:
            return False

        import time
        now = time.time()

        # 1. 30 秒内重复复制同一文本静默忽略
        if text in self._seen_history and (now - self._seen_history[text]) < 30.0:
            return False

        # 2. 长度限制 1 ~ 60 字符
        if len(text) < 1 or len(text) > 60:
            return False

        # 3. 过滤纯数字 / 纯标点 / 单英文字母
        if re.match(r'^\d+(\.\d+)?$', text) or re.match(r'^[^\w\s]+$', text) or re.match(r'^[a-zA-Z]$', text):
            return False

        # 4. 过滤代码变量驼峰与下划线命名 (如 getUserInfo, is_valid, const_val, void func())
        if re.match(r'^[a-zA-Z0-9_\$]+\(\)?$', text) or re.match(r'^[a-z]+[A-Z][a-zA-Z0-9]*$', text) or "def " in text or "function " in text or "const " in text:
            return False

        # 5. 必须包含有效韩文或有效中文词汇
        has_kr = bool(re.search(r'[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]', text))
        has_cn = bool(re.search(r'[\u4e00-\u9fa5]{2,}', text))  # 中文至少 2 个汉字，避免单个助字频繁误触

        if not has_kr and not has_cn:
            return False

        clean_text = re.sub(r"[\r\n\t]+", " ", text).strip()
        if not clean_text:
            return False

        self._seen_history[text] = now
        self._last_clip_text = text
        self._pending_raw_text = clean_text

        # 启动后台秒级异步翻译（首选国内免梯直连有道，自动级联降级）
        self._translator.translate_async(clean_text, engine="youdao")
        return True

    def _on_clipboard_changed(self):
        if not self._enabled or not self._clipboard:
            return

        try:
            self.process_text(self._clipboard.text())
        except Exception:
            pass

    def _on_translation_completed(self, trans_data: Dict[str, Any]):
        """后台异步翻译完成后的组装与分发"""
        if not self._pending_raw_text:
            return

        src = self._pending_raw_text
        res_text = trans_data.get("main_result", "")
        sl = trans_data.get("sl", "ko")
        details = trans_data.get("details") or {}
        is_kr = is_korean_text(src)

        # 尝试在主词库中精确查询更多详细元数据
        matched_info = {}
        if self._vocab_manager and is_kr:
            found = self._vocab_manager.find_word_by_korean(src)
            if found:
                matched_info = {
                    "korean": found.get("korean", src),
                    "meaning": found.get("meaning", found.get("chinese", res_text)),
                    "pronunciation": found.get("pronunciation", ""),
                    "pos": found.get("pos", "生词"),
                    "example_kr": found.get("example_kr", ""),
                    "example_cn": found.get("example_cn", "")
                }

        if not matched_info:
            matched_info = {
                "korean": src if is_kr else res_text,
                "meaning": res_text if is_kr else src,
                "pronunciation": details.get("pronunciation", ""),
                "pos": details.get("pos", "生词"),
                "example_kr": details.get("example_kr", ""),
                "example_cn": details.get("example_cn", "")
            }

        payload = {
            "source_text": src,
            "translated_text": res_text,
            "is_korean": is_kr,
            "direction": "🇰🇷 韩 ➔ 🇨🇳 中" if is_kr else "🇨🇳 中 ➔ 🇰🇷 韩",
            "details": matched_info
        }

        # 触发全功能联动信号
        self.clip_translated_captured.emit(payload)
        # 兼容历史接口
        self.korean_captured.emit(src, matched_info)

    def add_to_custom_vocab(self, korean: str, meaning: str = "", pronunciation: str = "") -> dict:
        """持久化存入 data/custom_vocab.json"""
        if not korean:
            return {}

        custom_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "custom_vocab.json"
        )

        data = {"title": "自定义生词本与剪贴板划词库", "updated_at": "", "words": []}
        if os.path.exists(custom_path):
            try:
                with open(custom_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        words = data.get("words", [])

        # 检查是否已存在
        clean_target = korean.strip()
        existing = next((w for w in words if w.get("korean", "").strip() == clean_target), None)

        if existing:
            if meaning and (existing.get("meaning") in ("划词收藏生词", "外部划词收藏", "") or not existing.get("meaning")):
                existing["meaning"] = meaning
            if pronunciation and not existing.get("pronunciation"):
                existing["pronunciation"] = pronunciation
            target_word = existing
        else:
            new_id = f"custom_{len(words) + 1:03d}_{datetime.now().strftime('%M%S')}"
            target_word = {
                "id": new_id,
                "korean": clean_target,
                "meaning": meaning if meaning else "外部划词收藏",
                "pronunciation": pronunciation,
                "pos": "生词",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            words.insert(0, target_word)

        data["words"] = words
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        try:
            with open(custom_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        self.vocab_saved.emit(target_word)
        return target_word

    def get_custom_words(self) -> list:
        """读取全部自定义生词"""
        custom_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "custom_vocab.json"
        )
        if not os.path.exists(custom_path):
            return []
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("words", [])
        except Exception:
            return []
