"""
pronunciation_rules.py
----------------------
「未来的韩语卡片」- 韩语音变规则智能解析引擎
支持 7 大经典音变规则：
1. 连音化 (연음화 / Liaison)
2. 鼻音化 (비음화 / Nasalization)
3. 激音化 (격음화 / Aspiration)
4. 流音化 (유음화 / Lateralization)
5. 紧音化 (된소리화 / Tensification)
6. 腭化 (구개음화 / Palatalization)
7. ㅎ脱落 (ㅎ-deletion)
"""

import re
from typing import Dict, Any, List, Tuple, Optional

# Unicode 韩文字符范围
HANGUL_BASE = 0xAC00
HANGUL_END = 0xD7A3

CHOSUNG = [
    'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ',
    'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

JUNGSUNG = [
    'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ',
    'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'
]

JONGSUNG = [
    '', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ',
    'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
    'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

# 代表收音映射 (7 代表收音: ㄱ, ㄴ, ㄷ, ㄹ, ㅁ, ㅂ, ㅇ)
REP_JONG = {
    '': '',
    'ㄱ': 'ㄱ', 'ㄲ': 'ㄱ', 'ㅋ': 'ㄱ', 'ㄳ': 'ㄱ', 'ㄺ': 'ㄱ',
    'ㄴ': 'ㄴ', 'ㄵ': 'ㄴ', 'ㄶ': 'ㄴ',
    'ㄷ': 'ㄷ', 'ㅅ': 'ㄷ', 'ㅆ': 'ㄷ', 'ㅈ': 'ㄷ', 'ㅊ': 'ㄷ', 'ㅌ': 'ㄷ', 'ㅎ': 'ㄷ',
    'ㄹ': 'ㄹ', 'ㄼ': 'ㄹ', 'ㄽ': 'ㄹ', 'ㄾ': 'ㄹ', 'ㅀ': 'ㄹ',
    'ㅁ': 'ㅁ', 'ㄻ': 'ㅁ',
    'ㅂ': 'ㅂ', 'ㅍ': 'ㅂ', 'ㄿ': 'ㅂ', 'ㅄ': 'ㅂ',
    'ㅇ': 'ㅇ'
}

# 松音到紧音映射
TENSIFICATION_MAP = {
    'ㄱ': 'ㄲ',
    'ㄷ': 'ㄸ',
    'ㅂ': 'ㅃ',
    'ㅅ': 'ㅆ',
    'ㅈ': 'ㅉ'
}

# 平音与 ㅎ 结合成激音映射
ASPIRATION_MAP = {
    'ㄱ': 'ㅋ', 'ㅋ': 'ㅋ',
    'ㄷ': 'ㅌ', 'ㅌ': 'ㅌ',
    'ㅂ': 'ㅍ', 'ㅍ': 'ㅍ',
    'ㅈ': 'ㅊ', 'ㅊ': 'ㅊ'
}

# 双收音拆分 (左收音, 右移初声)
DOUBLE_JONG_SPLIT = {
    'ㄳ': ('ㄱ', 'ㅅ'),
    'ㄵ': ('ㄴ', 'ㅈ'),
    'ㄶ': ('ㄴ', 'ㅎ'),
    'ㄺ': ('ㄹ', 'ㄱ'),
    'ㄻ': ('ㄹ', 'ㅁ'),
    'ㄼ': ('ㄹ', 'ㅂ'),
    'ㄽ': ('ㄹ', 'ㅅ'),
    'ㄾ': ('ㄹ', 'ㅌ'),
    'ㄿ': ('ㄹ', 'ㅍ'),
    'ㅀ': ('ㄹ', 'ㅎ'),
    'ㅄ': ('ㅂ', 'ㅅ'),
}

# 常见特例/高频词发音覆盖字典
SPECIAL_PRON_MAP = {
    "맛있다": ("마시따", "连音与紧音", "收音 ㅅ 移入后字元音并诱发后字紧音"),
    "멋있다": ("머시따", "连音与紧音", "收音 ㅅ 移入后字元音并诱发后字紧音"),
    "깻잎": ("깬닙", "ㄴ添加与鼻音化", "合成词添加 ㄴ 并诱发收音鼻音化"),
    "나뭇잎": ("나무닙", "ㄴ添加与鼻音化", "合成词添加 ㄴ 并诱发收音鼻音化"),
    "못하다": ("모타다", "激音化", "收音 ㅅ(ㄷ) 与 ㅎ 结合发为激音 ㅌ"),
    "어떻게": ("어떠케", "激音化", "收音 ㅎ 与 后字 ㄱ 结合发为激音 ㅋ"),
    "그렇지": ("그러치", "激音化", "收音 ㅎ 与 后字 ㅈ 结合发为激音 ㅊ"),
    "좋다": ("조타", "激音化", "收音 ㅎ 与 后字 ㄷ 结合发为激音 ㅌ"),
    "많다": ("만타", "激音化", "收音 ㄶ 与 后字 ㄷ 结合发为激音 ㅌ"),
    "싫다": ("실타", "激音化", "收音 ㅀ 与 后字 ㄷ 结合发为激音 ㅌ"),
    "괜찮다": ("괜찬타", "激音化", "收音 ㄶ 与 后字 ㄷ 结合发为激音 ㅌ"),
    "감사합니다": ("감사함니다", "鼻音化", "收音 ㅂ 遇到 ㄴ 时转化为 ㅁ 发音"),
    "고맙습니다": ("고맙씀니다", "紧音与鼻音", "收音 ㅂ 遇到 ㄴ 时转化为 ㅁ 并产生紧音"),
    "있습니다": ("익씀니다", "紧音与鼻音", "收音 ㅆ 遇 ㅂ 紧音化，遇 ㄴ 鼻音化"),
}


def is_hangul_syllable(ch: str) -> bool:
    """判断单个字符是否为完整韩文音节"""
    if not ch or len(ch) != 1:
        return False
    return HANGUL_BASE <= ord(ch) <= HANGUL_END


def decompose_char(ch: str) -> Optional[Tuple[str, str, str]]:
    """将单个韩文字符拆解为 (初声, 中声, 终声/收音)"""
    if not is_hangul_syllable(ch):
        return None
    code = ord(ch) - HANGUL_BASE
    cho_idx = code // 588
    jung_idx = (code % 588) // 28
    jong_idx = code % 28
    return (CHOSUNG[cho_idx], JUNGSUNG[jung_idx], JONGSUNG[jong_idx])


def compose_char(cho: str, jung: str, jong: str = '') -> str:
    """将 (初声, 中声, 终声) 组合为单个韩文字符"""
    if cho not in CHOSUNG or jung not in JUNGSUNG or jong not in JONGSUNG:
        return ''
    cho_idx = CHOSUNG.index(cho)
    jung_idx = JUNGSUNG.index(jung)
    jong_idx = JONGSUNG.index(jong)
    code = HANGUL_BASE + (cho_idx * 588) + (jung_idx * 28) + jong_idx
    return chr(code)


def derive_pronunciation(korean_text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    根据韩文书写文本推导实际读音与触发的音变规则列表
    返回: (actual_pronunciation, [(rule_name, explanation), ...])
    """
    clean_kr = re.sub(r"\(.*?\)|（.*?）", "", korean_text).strip()
    if not clean_kr:
        return clean_kr, []

    # 1. 检查特殊人工校准发音表
    if clean_kr in SPECIAL_PRON_MAP:
        pron, r_name, r_exp = SPECIAL_PRON_MAP[clean_kr]
        return pron, [(r_name, r_exp)]

    chars = list(clean_kr)
    n = len(chars)
    rules_triggered = []

    # 将字符拆解为音节三元组列表 [ [cho, jung, jong], ... ]
    syllables = []
    for ch in chars:
        if is_hangul_syllable(ch):
            syllables.append(list(decompose_char(ch)))
        else:
            syllables.append(ch)

    # 遍历音节间相互作用 (i -> i+1)
    for i in range(n - 1):
        if not isinstance(syllables[i], list) or not isinstance(syllables[i + 1], list):
            continue

        c1 = syllables[i]
        c2 = syllables[i + 1]
        j1 = c1[2] # 前字收音
        c2_cho = c2[0] # 后字初声
        c2_jung = c2[1] # 后字元音

        if not j1:
            continue

        rep1 = REP_JONG.get(j1, j1)

        # ── 1. 腭化 (Palatalization / 구개음화) ──
        # 收音 ㄷ/ㅌ 遇到 '이' 开头 (元音为 ㅣ) 转化为 ㅈ/ㅊ
        if j1 in ['ㄷ', 'ㅌ'] and c2_cho == 'ㅇ' and c2_jung in ['ㅣ', 'ㅕ', 'ㅛ', 'ㅠ', 'ㅑ']:
            target_cho = 'ㅈ' if j1 == 'ㄷ' else 'ㅊ'
            c1[2] = ''
            c2[0] = target_cho
            rules_triggered.append(("腭化", f"收音 {j1} 遇到后字 'ㅣ' 元音转化为 {target_cho} 发音"))
            continue

        # ── 2. 激音化 / 送气化 (Aspiration / 격음화) ──
        # A: 收音 (ㄱ, ㄷ, ㅂ, ㅈ) + 初声 ㅎ -> 合并为激音 (ㅋ, ㅌ, ㅍ, ㅊ)
        if rep1 in ASPIRATION_MAP and c2_cho == 'ㅎ':
            target_cho = ASPIRATION_MAP[rep1]
            c1[2] = ''
            c2[0] = target_cho
            rules_triggered.append(("激音化", f"收音 {j1} 与初声 ㅎ 结合发为激音 {target_cho}"))
            continue

        # B: 收音 ㅎ (ㄶ, ㅀ) + 初声 (ㄱ, ㄷ, ㅂ, ㅈ) -> 初声激音化
        if j1 in ['ㅎ', 'ㄶ', 'ㅀ'] and c2_cho in ASPIRATION_MAP:
            target_cho = ASPIRATION_MAP[c2_cho]
            if j1 == 'ㄶ': c1[2] = 'ㄴ'
            elif j1 == 'ㅀ': c1[2] = 'ㄹ'
            else: c1[2] = ''
            c2[0] = target_cho
            rules_triggered.append(("激音化", f"收音 {j1} 与初声 {c2_cho} 结合发为激音 {target_cho}"))
            continue

        # ── 3. ㅎ脱落 (h-deletion) ──
        # 收音 ㅎ 遇到元音 (ㅇ) -> ㅎ 音脱落
        if j1 in ['ㅎ', 'ㄶ', 'ㅀ'] and c2_cho == 'ㅇ':
            if j1 == 'ㅎ':
                c1[2] = ''
                rules_triggered.append(("ㅎ脱落", "收音 ㅎ 遇到后字元音时脱落不发音"))
            elif j1 == 'ㄶ':
                c1[2] = ''
                c2[0] = 'ㄴ'
                rules_triggered.append(("连音化", "收音 ㄶ 中的 ㄴ 移入后字元音连读"))
            elif j1 == 'ㅀ':
                c1[2] = ''
                c2[0] = 'ㄹ'
                rules_triggered.append(("连音化", "收音 ㅀ 中的 ㄹ 移入后字元音连读"))
            continue

        # ── 4. 流音化 (Lateralization / 유음화) ──
        # ㄴ + ㄹ -> ㄹ + ㄹ 或 ㄹ + ㄴ -> ㄹ + ㄹ
        if rep1 == 'ㄴ' and c2_cho == 'ㄹ':
            c1[2] = 'ㄹ'
            rules_triggered.append(("流音化", "辅音 ㄴ 遇到流音 ㄹ 时转化为 ㄹ"))
            continue
        elif rep1 == 'ㄹ' and c2_cho == 'ㄴ':
            c2[0] = 'ㄹ'
            rules_triggered.append(("流音化", "辅音 ㄴ 遇到流音 ㄹ 时同化为 ㄹ"))
            continue

        # ── 5. 鼻音化 (Nasalization / 비음화) ──
        # A: 收音 (ㄱ/ㄷ/ㅂ) 遇到 ㄴ/ㅁ -> 分别变为 ㅇ/ㄴ/ㅁ
        if rep1 == 'ㄱ' and c2_cho in ['ㄴ', 'ㅁ']:
            c1[2] = 'ㅇ'
            rules_triggered.append(("鼻音化", f"收音 {j1} 遇到鼻音 {c2_cho} 转化为 ㅇ 发音"))
            continue
        elif rep1 == 'ㄷ' and c2_cho in ['ㄴ', 'ㅁ']:
            c1[2] = 'ㄴ'
            rules_triggered.append(("鼻音化", f"收音 {j1} 遇到鼻音 {c2_cho} 转化为 ㄴ 发音"))
            continue
        elif rep1 == 'ㅂ' and c2_cho in ['ㄴ', 'ㅁ']:
            c1[2] = 'ㅁ'
            rules_triggered.append(("鼻音化", f"收音 {j1} 遇到鼻音 {c2_cho} 转化为 ㅁ 发音"))
            continue

        # B: 辅音 (ㅁ/ㅇ/ㄱ/ㅂ) 遇到 初声 ㄹ -> ㄹ 变为 ㄴ, 进而若前为 ㄱ/ㅂ 则鼻音化
        if rep1 in ['ㅁ', 'ㅇ', 'ㄱ', 'ㅂ'] and c2_cho == 'ㄹ':
            c2[0] = 'ㄴ'
            if rep1 == 'ㄱ':
                c1[2] = 'ㅇ'
                rules_triggered.append(("鼻音化", "收音 ㄱ 遇到 ㄹ 时，初声转为 ㄴ 且收音转化为 ㅇ"))
            elif rep1 == 'ㅂ':
                c1[2] = 'ㅁ'
                rules_triggered.append(("鼻音化", "收音 ㅂ 遇到 ㄹ 时，初声转为 ㄴ 且收音转化为 ㅁ"))
            else:
                rules_triggered.append(("鼻音化", f"收音 {j1} 后的流音 ㄹ 转化为鼻音 ㄴ"))
            continue

        # ── 6. 连音化 (Liaison / 연음화) ──
        # 收音遇到后字元音 (ㅇ) -> 移至后字初声
        if j1 != 'ㅇ' and c2_cho == 'ㅇ':
            if j1 in DOUBLE_JONG_SPLIT:
                left_j, right_cho = DOUBLE_JONG_SPLIT[j1]
                c1[2] = left_j
                c2[0] = 'ㅆ' if right_cho == 'ㅅ' else right_cho
                rules_triggered.append(("连音化", f"双收音 {j1} 的第二收音移至后字初声连读"))
            else:
                c1[2] = ''
                # 收音 ㅅ 连音读 ㅆ 还是 ㅅ
                c2[0] = j1
                rules_triggered.append(("连音", f"收音 {j1} 移至后字元音初声连读"))
            continue

        # ── 7. 紧音化 / 硬音化 (Tensification / 된소리화) ──
        # 代表收音 (ㄱ, ㄷ, ㅂ) + 松音 (ㄱ, ㄷ, ㅂ, ㅅ, ㅈ) -> 变为紧音 (ㄲ, ㄸ, ㅃ, ㅆ, ㅉ)
        if rep1 in ['ㄱ', 'ㄷ', 'ㅂ'] and c2_cho in TENSIFICATION_MAP:
            tens_cho = TENSIFICATION_MAP[c2_cho]
            c2[0] = tens_cho
            rules_triggered.append(("紧音化", f"收音 {j1} 后面的松音 {c2_cho} 转化为紧音 {tens_cho}"))
            continue

    # 重新组装韩文字符串
    out_chars = []
    for item in syllables:
        if isinstance(item, list):
            composed = compose_char(item[0], item[1], item[2])
            out_chars.append(composed if composed else '?')
        else:
            out_chars.append(str(item))

    actual_pron = "".join(out_chars)
    return actual_pron, rules_triggered


def analyze_pronunciation(word_korean: str, custom_pron: str = "") -> Dict[str, Any]:
    """
    对外综合音变分析接口
    返回结构:
    {
        "has_mutation": bool,        # 是否存在发音与字形差异
        "clean_korean": str,        # 纯净原词 (如 "십년")
        "actual_pron": str,         # 实际韩文读音 (如 "심년")
        "rule_name": str,           # 音变规则主标签 (如 "鼻音化")
        "rule_tag": str,            # 展示标签 (如 "[鼻音化]")
        "explanation": str,         # 1 句简明语法规则解释
        "all_rules": list           # 触发的所有音变规则 [(name, desc), ...]
    }
    """
    if not word_korean:
        return {
            "has_mutation": False,
            "clean_korean": "",
            "actual_pron": "",
            "rule_name": "",
            "rule_tag": "",
            "explanation": "",
            "all_rules": []
        }

    clean_kr = re.sub(r"\(.*?\)|（.*?）", "", word_korean).strip()
    actual_pron, rules = derive_pronunciation(clean_kr)

    # 如果有外部显式指定的实际读音且不同于原词
    if custom_pron and custom_pron.strip() and custom_pron.strip() != clean_kr:
        actual_pron = custom_pron.strip()

    has_mutation = (actual_pron != clean_kr) and bool(actual_pron)

    rule_name = rules[0][0] if rules else ("音变" if has_mutation else "")
    explanation = rules[0][1] if rules else ("实际发音与书写字形存在音变差异" if has_mutation else "")

    return {
        "has_mutation": has_mutation,
        "clean_korean": clean_kr,
        "actual_pron": actual_pron,
        "rule_name": rule_name,
        "rule_tag": f"[{rule_name}]" if rule_name else "",
        "explanation": explanation,
        "all_rules": rules
    }
