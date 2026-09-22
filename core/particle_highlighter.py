"""
particle_highlighter.py
-----------------------
韩语日常例句语法助词识别与双层色彩标注引擎：
1. 目标词高亮：暖金琥珀色 (#FCD34D) + 下划线强调 + 词干变形智能匹配
2. 语法助词高亮：淡薰衣草紫 (#D8B4FE) + 晶莹紫晶底衬 + 语法 Tooltip
"""

import html
import re
from typing import Dict, List, Tuple

# 常用韩语助词字典（多音节长助词优先匹配）
PARTICLES: List[Tuple[str, str]] = [
    # 4 字符长助词
    ("에서부터", "助词: -에서부터 (从...起/自...始)"),
    ("에게서부터", "助词: -에게서부터 (从...处起)"),
    # 3 字符助词
    ("에게서", "助词: -에게서 (从...处/人称来源)"),
    ("한테서", "助词: -한테서 (从...处/口语来源)"),
    ("으로는", "助词: -으로는 (用/朝...方向+主题强调)"),
    ("에서는", "助词: -에서는 (在...处所+主题强调)"),
    ("에서도", "助词: -에서도 (在...处所也)"),
    ("에게도", "助词: -에게도 (给...也)"),
    ("한테도", "助词: -한테도 (给...也)"),
    ("까지는", "助词: -까지는 (到...为止+限定)"),
    ("부터는", "助词: -부터는 (从...开始+限定)"),
    # 2 字符助词
    ("에서", "助词: -에서 (在...行动处所 / 从...来源)"),
    ("에게", "助词: -에게 (向/对/给... 授受对象)"),
    ("한테", "助词: -한테 (向/给... 口语对象)"),
    ("으로", "助词: -으로 (用/朝/以... 工具/方向/资格)"),
    ("부터", "助词: -부터 (从... 时间/顺序起点)"),
    ("까지", "助词: -까지 (到... 终点/界限)"),
    ("보다", "助词: -보다 (比... 比较标准)"),
    ("처럼", "助词: -처럼 (像...一样 比拟)"),
    ("같이", "助词: -같이 (像...一样)"),
    ("마다", "助词: -마다 (每...)"),
    ("조차", "助词: -조차 (连...都/甚至)"),
    ("마저", "助词: -마저 (连...都/最后剩下)"),
    ("밖에", "助词: -밖에 (除了...之外/只)"),
    ("하고", "助词: -하고 (和/同/与 并列/伴随)"),
    ("이랑", "助词: -이랑 (和/与 口语伴随)"),
    ("께서", "助词: -께서 (主格敬语)"),
    # 1 字符助词
    ("은", "助词: -은 (主题/对比助词 - 闭音节)"),
    ("는", "助词: -는 (主题/对比助词 - 开音节)"),
    ("이", "助词: -이 (主格助词 - 闭音节)"),
    ("가", "助词: -가 (主格助词 - 开音节)"),
    ("을", "助词: -을 (宾格助词 - 闭音节)"),
    ("를", "助词: -를 (宾格助词 - 开音节)"),
    ("에", "助词: -에 (在/到/于 时间/静态处所/目的地)"),
    ("로", "助词: -로 (朝/用 方向/手段 - 开音节/ㄹ收音)"),
    ("와", "助词: -와 (和/与 - 开音节)"),
    ("과", "助词: -과 (和/与 - 闭音节)"),
    ("도", "助词: -도 (也/同样/包含)"),
    ("만", "助词: -만 (只/仅仅 唯独)"),
    ("의", "助词: -의 (的 所属格)"),
    ("랑", "助词: -랑 (和/与 开音节口语)"),
]


def _get_word_candidates(word: Dict) -> List[str]:
    """生成目标词及其常见活用变体列表（按长度降序）"""
    if not word:
        return []
    korean_raw = word.get("korean", "").strip()
    clean_kr = re.sub(r"\(.*?\)|（.*?）", "", korean_raw).strip()
    if not clean_kr:
        return []

    candidates = set()
    candidates.add(clean_kr)

    # 1. -하다 动词/形容词词干
    if clean_kr.endswith("하다"):
        root = clean_kr[:-2]
        if root:
            candidates.add(root)
            candidates.add(root + "하")
            candidates.add(root + "해")
            candidates.add(root + "했")
            candidates.add(root + "합")
            candidates.add(root + "할")
    elif clean_kr.endswith("다") and len(clean_kr) >= 2:
        stem = clean_kr[:-1]
        candidates.add(stem)

        # 常用活用变体推导
        if stem.endswith("아") or stem == "가":
            candidates.add("갔")
            candidates.add("가요")
            candidates.add("갑니다")
        elif stem.endswith("오") or stem == "오":
            candidates.add("와")
            candidates.add("왔")
            candidates.add("와요")
            candidates.add("옵니다")
        elif stem.endswith("보"):
            candidates.add("봐")
            candidates.add("봤")
            candidates.add("봐요")
            candidates.add("봅니다")
        elif stem.endswith("되"):
            candidates.add("돼")
            candidates.add("됐")
            candidates.add("돼요")
            candidates.add("됩니다")
        elif stem.endswith("주"):
            candidates.add("줘")
            candidates.add("줬")
            candidates.add("줘요")
            candidates.add("줍니다")
        elif stem.endswith("마시"):
            candidates.add("마셔")
            candidates.add("마셨")
        elif stem.endswith("쓰"):
            candidates.add("써")
            candidates.add("썼")
        elif stem.endswith("사"):
            candidates.add("샀")
        elif stem.endswith("배우"):
            candidates.add("배워")
            candidates.add("배웠")
        elif stem.endswith("만나"):
            candidates.add("만났")
            candidates.add("만나요")
        elif stem.endswith("크"):
            candidates.add("커")
            candidates.add("컸")
        elif stem.endswith("예쁘"):
            candidates.add("예뻐")
            candidates.add("예뻤")
        elif stem.endswith("바쁘"):
            candidates.add("바빠")
            candidates.add("바빴")
        elif stem.endswith("아프"):
            candidates.add("아파")
            candidates.add("아팠")
        elif stem.endswith("어렵"):
            candidates.add("어려워")
            candidates.add("어려웠")
        elif stem.endswith("쉽"):
            candidates.add("쉬워")
            candidates.add("쉬웠")
        elif stem.endswith("알"):
            candidates.add("압니다")
            candidates.add("알아요")
            candidates.add("알았")
        elif stem.endswith("살"):
            candidates.add("삽니다")
            candidates.add("살아요")
            candidates.add("살았")

    return sorted(filter(lambda x: len(x) >= 1, candidates), key=len, reverse=True)


def highlight_sentence_with_particles(sentence: str, word: Dict, theme: str = "dark") -> str:
    """
    在韩文例句中对目标词和语法助词进行双层色彩标注：
    - 目标单词：暖金琥珀色 (#FCD34D / #C0392B) + 下划线 + 加粗
    - 语法助词：淡薰衣草紫 (#D8B4FE) + 晶莹紫晶底色 + 悬停 Tooltip
    """
    if not sentence:
        return ""

    escaped_sentence = html.escape(sentence)

    # 1. 保护目标词（用安全占位符包裹）
    cands = _get_word_candidates(word)
    protected_sentence = escaped_sentence

    if cands:
        pattern_parts = [re.escape(html.escape(c)) for c in cands]
        target_regex = re.compile(f"({'|'.join(pattern_parts)})")
        protected_sentence = target_regex.sub(r"@@TARGET_START@@\1@@TARGET_END@@", protected_sentence, count=1)

    # 2. 按语块（Eojeol）分析并识别助词后缀
    # 以空格和标点分隔处理各个词块
    tokens = re.split(r"(\s+|[.,!?~\"'()]+)", protected_sentence)
    new_tokens = []

    for token in tokens:
        # 如果是空白符、纯标点或者整个词块就是目标词，保持原样
        if not token or re.match(r"^(\s+|[.,!?~\"'()]+)$", token) or "@@TARGET_START@@" in token:
            new_tokens.append(token)
            continue

        matched_particle = None
        matched_desc = ""

        # 尝试匹配词块末尾的最长助词
        for p_str, p_desc in PARTICLES:
            p_escaped = html.escape(p_str)
            if token.endswith(p_escaped) and len(token) > len(p_escaped):
                # 确保前缀至少有 1 个韩文字符且不是纯标点
                stem = token[:-len(p_escaped)]
                if stem and not stem.endswith("@"):
                    matched_particle = p_escaped
                    matched_desc = p_desc
                    break

        if matched_particle:
            stem = token[:-len(matched_particle)]
            highlighted_particle = (
                f'@@PARTICLE_START:{html.escape(matched_desc)}@@{matched_particle}@@PARTICLE_END@@'
            )
            new_tokens.append(stem + highlighted_particle)
        else:
            new_tokens.append(token)

    result = "".join(new_tokens)

    # 3. 渲染 HTML 标签样式
    # 目标词高亮样式
    if theme == "dark":
        target_style = "color: #FCD34D; font-weight: 700; text-decoration: underline;"
        particle_style = "color: #D8B4FE; background: rgba(192, 132, 252, 0.18); border-radius: 3px; padding: 0 2px; font-weight: 600;"
    else:
        target_style = "color: #B45309; font-weight: 700; text-decoration: underline;"
        particle_style = "color: #7C3AED; background: rgba(124, 58, 237, 0.12); border-radius: 3px; padding: 0 2px; font-weight: 600;"

    result = re.sub(
        r"@@TARGET_START@@(.*?)@@TARGET_END@@",
        f'<span style="{target_style}">\\1</span>',
        result
    )

    result = re.sub(
        r"@@PARTICLE_START:(.*?)@@(.*?)@@PARTICLE_END@@",
        f'<span style="{particle_style}" title="\\1">\\2</span>',
        result
    )

    return result
