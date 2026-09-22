# core/hanja_family.py
# -*- coding: utf-8 -*-
"""
韩语汉字词词根拆解与同根词联想拓展引擎 (Hanja Root & Family Engine)
功能：
1. 汉字词智能字根拆解 (如 '교환학생' -> '【交换】 + 【学生】')
2. 汉字字根知识库映射 (如 '교' -> '交/校/教', '학' -> '学')
3. 动态从词库中检索包含相同字根的高频同根词，输出衍生词家族
"""

import re
from typing import List, Dict, Optional
from core.hanja_converter import to_simplified

# 常用韩语高频汉字音字根含义映射表
COMMON_HANJA_ROOTS = {
    "학": "学",
    "교": "交/校/教",
    "생": "生",
    "행": "行/幸",
    "국": "国",
    "원": "院/员/元",
    "식": "食/式",
    "실": "室",
    "화": "话/化/花",
    "동": "动/同/东",
    "사": "社/事/使/思",
    "문": "文/门/问",
    "차": "车/差",
    "수": "水/手/数",
    "인": "人/引/印",
    "어": "语",
    "전": "电/前/全/传",
    "기": "气/机/期/记",
    "소": "所/消/小",
    "가": "家/可/歌/价",
    "관": "馆/观/关",
    "정": "正/情/定/政",
    "공": "公/工/空/共",
    "대": "大/对/代/台",
    "방": "房/方/放",
    "입": "入/立",
    "출": "出",
    "회": "会/回",
    "시": "市/时/示/视",
    "의": "意/医/义/议",
    "통": "通/统",
    "환": "换/欢/环",
    "약": "药/约",
    "복": "服/福/复",
    "신": "新/信/身/神",
    "역": "站/役/历",
    "도": "度/道/图/都",
    "계": "计/界/系",
    "자": "字/自/子",
    "무": "务/无/武",
    "상": "商/相/上/常",
    "운": "运/云",
    "체": "体/替",
    "심": "心/深",
    "명": "名/明/命",
    "주": "主/住/周/注",
    "음": "音/饮",
    "료": "料/疗",
    "금": "金/今/禁",
    "품": "品",
}


def get_hanja_breakdown(word_dict: Dict) -> Optional[str]:
    """
    根据当前单词字典返回优雅规范的词根拆解字符串
    例如：
      - '교환학생' (hanja: '交換學生') -> '【交换】 · 【学生】'
      - '학교' (hanja: '學校') -> '【学校】'
    """
    if not word_dict:
        return None

    word_type = word_dict.get("word_type", "")
    hanja = word_dict.get("hanja") or word_dict.get("origin") or ""
    korean = word_dict.get("korean", "")

    # 清理括号
    clean_kr = re.sub(r"\(.*?\)|（.*?）", "", korean).strip()
    clean_hj = re.sub(r"\(.*?\)|（.*?）", "", hanja).strip() if hanja else ""

    if not clean_hj and word_type != "hanja":
        return None

    if not clean_hj:
        return None

    # 转为标准简体汉字
    simp_hj = to_simplified(clean_hj)

    # 如果是 4 字以上的复合汉字词，按双音节智能分段（如 交换 + 学生）
    if len(clean_kr) == 4 and len(simp_hj) == 4:
        return f"【{simp_hj[:2]}】 · 【{simp_hj[2:]}】"
    elif len(clean_kr) == 6 and len(simp_hj) == 6:
        return f"【{simp_hj[:2]}】 · 【{simp_hj[2:4]}】 · 【{simp_hj[4:]}】"
    else:
        return f"【{simp_hj}】"


def get_hanja_family_words(word_dict: Dict, all_words: List[Dict]) -> List[Dict]:
    """
    获取当前汉字词各字根的同根衍生词家族
    返回结构：
    [
      {
        "root_kr": "교",
        "root_cn": "交/校/教",
        "words": [
          {"korean": "교통", "hanja": "交通", "chinese": "交通"},
          {"korean": "교육", "hanja": "教育", "chinese": "教育"}
        ]
      }, ...
    ]
    """
    if not word_dict:
        return []

    hanja = word_dict.get("hanja") or word_dict.get("origin") or ""
    korean = word_dict.get("korean", "")
    clean_kr = re.sub(r"\(.*?\)|（.*?）", "", korean).strip()
    clean_hj = re.sub(r"\(.*?\)|（.*?）", "", hanja).strip() if hanja else ""

    if not clean_hj and word_dict.get("word_type") != "hanja":
        return []

    # 提取汉字词各字音
    syllables = [ch for ch in clean_kr if '\uac00' <= ch <= '\ud7a3']
    if not syllables:
        return []

    result = []
    seen_roots = set()

    for syl in syllables:
        if syl in seen_roots:
            continue
        seen_roots.add(syl)

        root_meaning = COMMON_HANJA_ROOTS.get(syl, "")
        
        # 从词库中检索包含该字根的衍生汉字词
        matched_words = []
        seen_words = {clean_kr}

        for w in all_words:
            w_kr = re.sub(r"\(.*?\)|（.*?）", "", w.get("korean", "")).strip()
            w_hj = w.get("hanja") or w.get("origin") or ""
            w_type = w.get("word_type", "")

            # 必须是汉字词、长度2~4字、包含该字音且未重复
            if w_kr not in seen_words and (w_hj or w_type == "hanja") and 2 <= len(w_kr) <= 4:
                if syl in w_kr:
                    seen_words.add(w_kr)
                    simp_w_hj = to_simplified(w_hj) if w_hj else ""
                    meaning = w.get("meaning") or w.get("chinese") or ""
                    clean_meaning = meaning.split("/")[0].split("（")[0].split("(")[0].strip()
                    
                    matched_words.append({
                        "korean": w_kr,
                        "hanja": simp_w_hj,
                        "chinese": clean_meaning,
                        "full_meaning": meaning
                    })
                    if len(matched_words) >= 4:
                        break

        if matched_words:
            result.append({
                "root_kr": syl,
                "root_cn": root_meaning if root_meaning else "汉字根",
                "words": matched_words
            })

    return result
