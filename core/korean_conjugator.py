# -*- coding: utf-8 -*-
"""
korean_conjugator.py
--------------------
韩语动词 / 形容词常用活用变形速查计算引擎 (Conjugation Engine)
支持规则活用及 6 大核心不规则活用（ㄷ/ㅂ/ㅡ/르/ㅅ/ㅎ/하다）
生成：
- 해요체 (非敬语口语现在时)
- 습니다체 (庄重敬语现在时)
- 았/었어요 (过去时)
- -(으)ㄹ 거예요 (将来/推测时)
- -고 (并列连接)
- -(으)면 (条件假设连接)
- -지만 (转折连接)
"""

import re
from typing import Dict, List, Optional, Tuple

# 19 个初声
CHOSUNG = [
    'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
    'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

# 21 个中声
JUNGSUNG = [
    'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ',
    'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ',
    'ㅡ', 'ㅢ', 'ㅣ'
]

# 28 个终声 (0 为无收音)
JONGSUNG = [
    '', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ',
    'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
    'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

# 阳性元音 (ㅏ, ㅗ, ㅑ, ㅘ, ㅚ, ㅛ)
POSITIVE_VOWELS = {'ㅏ', 'ㅗ', 'ㅑ', 'ㅘ', 'ㅚ', 'ㅛ'}


def decompose_hangul(char: str) -> Optional[Tuple[str, str, str]]:
    """将单个韩文字符拆解为 (初声, 中声, 终声)"""
    if not char or len(char) != 1:
        return None
    code = ord(char) - 0xAC00
    if code < 0 or code > 11171:
        return None
    jong = code % 28
    code //= 28
    jung = code % 21
    cho = code // 21
    return CHOSUNG[cho], JUNGSUNG[jung], JONGSUNG[jong]


def compose_hangul(cho: str, jung: str, jong: str = '') -> str:
    """由 (初声, 中声, 终声) 合成单个韩文字符"""
    try:
        cho_idx = CHOSUNG.index(cho)
        jung_idx = JUNGSUNG.index(jung)
        jong_idx = JONGSUNG.index(jong) if jong else 0
        code = 0xAC00 + (cho_idx * 21 + jung_idx) * 28 + jong_idx
        return chr(code)
    except (ValueError, IndexError):
        return ''


# 已知常用特殊不规则词典 (词条 -> {时态 -> 变形结果})
KNOWN_IRREGULARS = {
    # ㄷ 不规则 (듣다, 걷다, 묻다)
    "듣다": {"haeyo": "들어요", "seumnida": "듣습니다", "past": "들었어요", "future": "들을 거예요", "go": "듣고", "myeon": "들으면", "jiman": "듣지만", "rule": "ㄷ变ㄹ不规则"},
    "걷다": {"haeyo": "걸어요", "seumnida": "걷습니다", "past": "걸었어요", "future": "걸을 거예요", "go": "걷고", "myeon": "걸으면", "jiman": "걷지만", "rule": "ㄷ变ㄹ不规则"},
    "묻다": {"haeyo": "물어요", "seumnida": "묻습니다", "past": "물었어요", "future": "물을 거예요", "go": "묻고", "myeon": "물으면", "jiman": "묻지만", "rule": "ㄷ变ㄹ不规则"},

    # ㅂ 不规则 (덥다, 춥다, 맵다, 돕다, 곱다, 어렵다, 쉽다, 아름답다, 고맙다)
    "덥다": {"haeyo": "더워요", "seumnida": "덥습니다", "past": "더웠어요", "future": "더울 거예요", "go": "덥고", "myeon": "더우면", "jiman": "덥지만", "rule": "ㅂ变워不规则"},
    "춥다": {"haeyo": "추워요", "seumnida": "춥습니다", "past": "추웠어요", "future": "추울 거예요", "go": "춥고", "myeon": "추우면", "jiman": "춥지만", "rule": "ㅂ变워不规则"},
    "맵다": {"haeyo": "매워요", "seumnida": "맵습니다", "past": "매웠어요", "future": "매울 거예요", "go": "맵고", "myeon": "매우면", "jiman": "맵지만", "rule": "ㅂ变워不规则"},
    "쉽다": {"haeyo": "쉬워요", "seumnida": "쉽습니다", "past": "쉬웠어요", "future": "쉬울 거예요", "go": "쉽고", "myeon": "쉬우면", "jiman": "쉽지만", "rule": "ㅂ变워不规则"},
    "어렵다": {"haeyo": "어려워요", "seumnida": "어렵습니다", "past": "어려웠어요", "future": "어려울 거예요", "go": "어렵고", "myeon": "어려우면", "jiman": "어렵지만", "rule": "ㅂ变워不规则"},
    "돕다": {"haeyo": "도와요", "seumnida": "돕습니다", "past": "도왔어요", "future": "도울 거예요", "go": "돕고", "myeon": "도우면", "jiman": "돕지만", "rule": "ㅂ变와不规则"},
    "곱다": {"haeyo": "고와요", "seumnida": "곱습니다", "past": "고왔어요", "future": "고울 거예요", "go": "곱고", "myeon": "고우면", "jiman": "곱지만", "rule": "ㅂ变와不规则"},
    "아름답다": {"haeyo": "아름다워요", "seumnida": "아름답습니다", "past": "아름다웠어요", "future": "아름다울 거예요", "go": "아름답고", "myeon": "아름다우면", "jiman": "아름답지만", "rule": "ㅂ变워不规则"},
    "고맙다": {"haeyo": "고마워요", "seumnida": "고맙습니다", "past": "고마웠어요", "future": "고마울 거예요", "go": "고맙고", "myeon": "고마우면", "jiman": "고맙지만", "rule": "ㅂ变워不规则"},
    "무겁다": {"haeyo": "무거워요", "seumnida": "무겁습니다", "past": "무거웠어요", "future": "무거울 거예요", "go": "무겁고", "myeon": "무거우면", "jiman": "무겁지만", "rule": "ㅂ变워不规则"},
    "가볍다": {"haeyo": "가벼워요", "seumnida": "가볍습니다", "past": "가벼웠어요", "future": "가벼울 거예요", "go": "가볍고", "myeon": "가벼우면", "jiman": "가볍지만", "rule": "ㅂ变워不规则"},
    "즐겁다": {"haeyo": "즐거워요", "seumnida": "즐겁습니다", "past": "즐거웠어요", "future": "즐거울 거예요", "go": "즐겁고", "myeon": "즐거우면", "jiman": "즐겁지만", "rule": "ㅂ变워不规则"},

    # 르 不规则 (빠르다, 부르다, 모르다, 자르다, 기르다, 흐르다)
    "빠르다": {"haeyo": "빨라요", "seumnida": "빠릅니다", "past": "빨랐어요", "future": "빠를 거예요", "go": "빠르고", "myeon": "빠르면", "jiman": "빠르지만", "rule": "르变ㄹ라不规则"},
    "부르다": {"haeyo": "불러요", "seumnida": "부릅니다", "past": "불렀어요", "future": "부를 거예요", "go": "부르고", "myeon": "부르면", "jiman": "부르지만", "rule": "르变ㄹ러不规则"},
    "모르다": {"haeyo": "몰라요", "seumnida": "모릅니다", "past": "몰랐어요", "future": "모를 거예요", "go": "모르고", "myeon": "모르면", "jiman": "모르지만", "rule": "르变ㄹ라不规则"},
    "자르다": {"haeyo": "잘라요", "seumnida": "자릅니다", "past": "잘랐어요", "future": "자를 거예요", "go": "자르고", "myeon": "자르면", "jiman": "자르지만", "rule": "르变ㄹ라不规则"},
    "기르다": {"haeyo": "길러요", "seumnida": "기릅니다", "past": "길렀어요", "future": "기를 거예요", "go": "기르고", "myeon": "기르면", "jiman": "기르지만", "rule": "르变ㄹ러不规则"},
    "다르다": {"haeyo": "달라요", "seumnida": "다릅니다", "past": "달랐어요", "future": "다를 거예요", "go": "다르고", "myeon": "다르면", "jiman": "다르지만", "rule": "르变ㄹ라不规则"},

    # ㅅ 不规则 (낫다, 짓다, 붓다, 잇다)
    "낫다": {"haeyo": "나아요", "seumnida": "낫습니다", "past": "나았어요", "future": "나을 거예요", "go": "낫고", "myeon": "나으면", "jiman": "낫지만", "rule": "ㅅ脱落不规则"},
    "짓다": {"haeyo": "지어요", "seumnida": "짓습니다", "past": "지었어요", "future": "지을 거예요", "go": "짓고", "myeon": "지으면", "jiman": "짓지만", "rule": "ㅅ脱落不规则"},

    # ㅎ 不规则 (그렇다, 이렇다, 저렇다, 파랗다, 빨갛다, 노랗다)
    "그렇다": {"haeyo": "그래요", "seumnida": "그렇습니다", "past": "Channel", "past": "Channel", "past": "그랬어요", "future": "그럴 거예요", "go": "그렇고", "myeon": "그러면", "jiman": "그렇지만", "rule": "ㅎ变ㅐ不规则"},
    "이렇다": {"haeyo": "이래요", "seumnida": "이렇습니다", "past": "이랬어요", "future": "이럴 거예요", "go": "이렇고", "myeon": "이러면", "jiman": "이렇지만", "rule": "ㅎ变ㅐ不规则"},
    "저렇다": {"haeyo": "저래요", "seumnida": "저렇습니다", "past": "저랬어요", "future": "저럴 거예요", "go": "저렇고", "myeon": "저러면", "jiman": "저렇지만", "rule": "ㅎ变ㅐ不规则"},
    "어떻다": {"haeyo": "어때요", "seumnida": "어떻습니다", "past": "어땠어요", "future": "어떨 거예요", "go": "어떻고", "myeon": "어쩌면", "jiman": "어떻지만", "rule": "ㅎ变ㅐ不规则"},
}


def conjugate_korean_word(word: str) -> Optional[Dict[str, str]]:
    """
    智能分析并生成韩语动词/形容词的常用活用变形
    返回字典包含：
    - 'haeyo': 口语非敬语 (해요체)
    - 'seumnida': 庄重敬语 (습니다체)
    - 'past': 过去时 (았/었어요)
    - 'future': 将来/推测时 (-(으)ㄹ 거예요)
    - 'go': 并列 (-고)
    - 'myeon': 条件假设 (-(으)면)
    - 'jiman': 转折 (-지만)
    - 'rule_note': 规则或不规则类型说明
    """
    if not word or not word.endswith("다"):
        return None

    clean_kr = re.sub(r"\(.*?\)|（.*?）", "", word).strip()
    if clean_kr in KNOWN_IRREGULARS:
        res = dict(KNOWN_IRREGULARS[clean_kr])
        res["base"] = clean_kr
        return res

    stem = clean_kr[:-1] # 词干
    if not stem:
        return None

    last_char = stem[-1]
    decomp = decompose_hangul(last_char)
    if not decomp:
        return None

    cho, jung, jong = decomp
    has_jong = bool(jong)

    # 1. 습니다체 / ㅂ니다체
    if has_jong:
        if jong == 'ㄹ':
            # ㄹ 脱落收音：살다 -> 삽니다, 알다 -> 압니다
            prefix = stem[:-1]
            seumnida = prefix + compose_hangul(cho, jung, 'ㅂ') + "니다"
        else:
            seumnida = stem + "습니다"
    else:
        seumnida = stem[:-1] + compose_hangul(cho, jung, 'ㅂ') + "니다"

    # 2. -고 / -지만
    go_form = stem + "고"
    jiman_form = stem + "지만"

    # 3. -(으)면
    if not has_jong or jong == 'ㄹ':
        myeon_form = stem + "면"
    else:
        myeon_form = stem + "으면"

    # 4. -(으)ㄹ 거예요
    if not has_jong:
        future_form = stem[:-1] + compose_hangul(cho, jung, 'ㄹ') + " 거예요"
    elif jong == 'ㄹ':
        future_form = stem + " 거예요"
    else:
        future_form = stem + "을 거예요"

    # 5. 해요체 与 过去时 核心变化 (ㅏ/ㅗ -> 아, 其余 -> 어, 하다 -> 해, ㅡ 脱落)
    rule_note = "规则活用"

    if clean_kr.endswith("하다"):
        # 하다 动词/形容词 (하다 -> 해요 / 했어요)
        prefix = stem[:-1]
        haeyo_form = prefix + "해요"
        past_form = prefix + "했어요"

    elif not has_jong and jung == 'ㅡ':
        # ㅡ 脱落 (如 크다 -> 커요; 바쁘다 -> 바빠요)
        rule_note = "ㅡ脱落活用"
        if len(stem) >= 2:
            prev_decomp = decompose_hangul(stem[-2])
            is_prev_pos = prev_decomp[1] in POSITIVE_VOWELS if prev_decomp else False
        else:
            is_prev_pos = False

        target_vowel = 'ㅏ' if is_prev_pos else 'ㅓ'
        haeyo_stem = stem[:-1] + compose_hangul(cho, target_vowel, '')
        haeyo_form = haeyo_stem + "요"
        past_form = stem[:-1] + compose_hangul(cho, target_vowel, 'ㅆ') + "어요"

    elif not has_jong and jung == 'ㅏ':
        # 가다 -> 가요 / 갔어요
        haeyo_form = stem + "요"
        past_form = stem[:-1] + compose_hangul(cho, jung, 'ㅆ') + "어요"

    elif not has_jong and jung == 'ㅓ':
        # 서다 -> 서요 / 섰어요
        haeyo_form = stem + "요"
        past_form = stem[:-1] + compose_hangul(cho, jung, 'ㅆ') + "어요"

    elif not has_jong and jung == 'ㅗ':
        # 보다 -> 봐요 / 봤어요
        haeyo_stem = stem[:-1] + compose_hangul(cho, 'ㅘ', '')
        haeyo_form = haeyo_stem + "요"
        past_form = stem[:-1] + compose_hangul(cho, 'ㅘ', 'ㅆ') + "어요"

    elif not has_jong and jung == 'ㅜ':
        # 주다 -> 줘요 / 줬어요, 배우다 -> 배워요
        haeyo_stem = stem[:-1] + compose_hangul(cho, 'ㅝ', '')
        haeyo_form = haeyo_stem + "요"
        past_form = stem[:-1] + compose_hangul(cho, 'ㅝ', 'ㅆ') + "어요"

    elif not has_jong and jung == 'ㅣ':
        # 마시다 -> 마셔요 / 마셨어요
        haeyo_stem = stem[:-1] + compose_hangul(cho, 'ㅕ', '')
        haeyo_form = haeyo_stem + "요"
        past_form = stem[:-1] + compose_hangul(cho, 'ㅕ', 'ㅆ') + "어요"

    elif not has_jong and jung == 'ㅐ':
        # 보내다 -> 보내요 / 보냈어요
        haeyo_form = stem + "요"
        past_form = stem[:-1] + compose_hangul(cho, jung, 'ㅆ') + "어요"

    else:
        # 有收音情况：判断元音阳性/阴性
        if jung in POSITIVE_VOWELS:
            haeyo_form = stem + "아요"
            past_form = stem + "았어요"
        else:
            haeyo_form = stem + "어요"
            past_form = stem + "었어요"

    return {
        "base": clean_kr,
        "haeyo": haeyo_form,
        "seumnida": seumnida,
        "past": past_form,
        "future": future_form,
        "go": go_form,
        "myeon": myeon_form,
        "jiman": jiman_form,
        "rule": rule_note
    }


def get_conjugation_capsules(word: str) -> List[Dict[str, str]]:
    """
    返回用于 UI 渲染的常用活用胶囊列表：
    [
        {"title": "口语", "kr": "가요", "tag": "해요체", "desc": "非敬语口语现在时"},
        {"title": "敬语", "kr": "갑니다", "tag": "습니다체", "desc": "庄重敬语现在时"},
        {"title": "过去", "kr": "갔어요", "tag": "았/었어요", "desc": "过去完成时"},
        {"title": "将来", "kr": "갈 거예요", "tag": "-(으)ㄹ 거예요", "desc": "将来与推测时"},
        {"title": "条件", "kr": "가면", "tag": "-(으)면", "desc": "如果...假设条件"}
    ]
    """
    conj = conjugate_korean_word(word)
    if not conj:
        return []

    return [
        {"title": "口语", "kr": conj.get("haeyo", ""), "tag": "해요체", "desc": "日常口语"},
        {"title": "敬语", "kr": conj.get("seumnida", ""), "tag": "습니다체", "desc": "庄重敬语"},
        {"title": "过去", "kr": conj.get("past", ""), "tag": "过去时", "desc": "已完成动作"},
        {"title": "将来", "kr": conj.get("future", ""), "tag": "将来时", "desc": "计划与推测"},
        {"title": "并列", "kr": conj.get("go", ""), "tag": "-고", "desc": "顺承并列"},
        {"title": "条件", "kr": conj.get("myeon", ""), "tag": "-(으)면", "desc": "如果...假设"},
        {"title": "转折", "kr": conj.get("jiman", ""), "tag": "-지만", "desc": "虽然...但是"}
    ]
