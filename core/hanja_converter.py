# core/hanja_converter.py
"""汉字词繁体转简体转换器 (Traditional to Simplified Chinese Converter)
基于 OpenCC 标准字符集，支持全自动繁简汉字转换。
"""

import os
import json
from typing import Dict

_T2S_MAP: Dict[str, str] = {}


def _load_dict():
    global _T2S_MAP
    if _T2S_MAP:
        return
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dict_path = os.path.join(base_dir, "t2s_dict.json")
    if os.path.exists(dict_path):
        try:
            with open(dict_path, "r", encoding="utf-8") as f:
                _T2S_MAP = json.load(f)
        except Exception:
            _T2S_MAP = {}


def to_simplified(text: str) -> str:
    """将文本中的繁体汉字转换为标准简体中文"""
    if not text:
        return ""
    _load_dict()
    if not _T2S_MAP:
        return text
    return "".join(_T2S_MAP.get(ch, ch) for ch in text)


def format_hanja_origin(origin: str) -> str:
    """将汉字词源转化为规范的简体中文标签格式，如 '學校' -> '[汉字] 学校'"""
    if not origin:
        return ""
    simp = to_simplified(origin.strip())
    return f"[汉字] {simp}"
