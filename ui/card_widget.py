# ui/card_widget.py
"""卡片翻转组件：正面（韩语）和背面（中文释义+例句）
功能：
- 汉字词统一转换为「简体中文」展示（如 [汉字] 学校、[汉字] 韩国）
- 字号缩放全局联动支持（100% / 120% / 140% / 160% 等比缩放）
- 汉字词（Hanja）与外来词（Loanword）词源标注（[汉字] 学校 / [外来] Coffee / 固有词自动隐藏）
- 瞬时秒翻（0 延迟、0 阻塞）：纯本地 UI 控件 show/hide 切换，彻底移除 GraphicsEffect 开销
- 发音彻底解耦：点击卡片翻转完全静音，仅手动点击右上角 🔊 喇叭图标触发发音
- 实际读音（Pronunciation）、搭配/助词（Collocation）智能展示
- 单击即时翻面 与 拖拽移动窗口 互斥判定
"""

import re
import html
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame, QLineEdit, QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QPoint, pyqtSignal, QEvent, QPropertyAnimation, QEasingCurve, QTimer
)
from PyQt6.QtGui import QFont, QCursor, QColor
from typing import Dict, Optional

from ui.phonetic_tooltip import PhoneticTooltip

from config.settings import (
    COLORS, POS_COLORS,
    FONT_KOREAN_SIZE, FONT_CHINESE_SIZE, FONT_EXAMPLE_SIZE, FONT_POS_SIZE
)
from core.hanja_converter import format_hanja_origin, to_simplified
from core.hanja_family import get_hanja_breakdown, get_hanja_family_words
from core.particle_highlighter import highlight_sentence_with_particles
from core.pronunciation_rules import analyze_pronunciation
from core.korean_conjugator import get_conjugation_capsules, conjugate_korean_word


class SpellingUnderlineInput(QLineEdit):
    """Instagram 极简发光下划线输入框，支持韩文打字、Tab首字提示、Esc退出与错误弹性抖动"""

    tab_pressed = pyqtSignal()
    escape_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shake_anim: Optional[QPropertyAnimation] = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            self.tab_pressed.emit()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def shake(self):
        """左右轻微弹性抖动动画 (Shake Animation)"""
        if self._shake_anim and self._shake_anim.state() == QPropertyAnimation.State.Running:
            self._shake_anim.stop()

        orig_pos = self.pos()
        self._shake_anim = QPropertyAnimation(self, b"pos")
        self._shake_anim.setDuration(320)
        self._shake_anim.setEasingCurve(QEasingCurve.Type.OutBounce)

        self._shake_anim.setKeyValueAt(0.0, orig_pos)
        self._shake_anim.setKeyValueAt(0.2, orig_pos + QPoint(-8, 0))
        self._shake_anim.setKeyValueAt(0.4, orig_pos + QPoint(8, 0))
        self._shake_anim.setKeyValueAt(0.6, orig_pos + QPoint(-5, 0))
        self._shake_anim.setKeyValueAt(0.8, orig_pos + QPoint(5, 0))
        self._shake_anim.setKeyValueAt(1.0, orig_pos)

        self._shake_anim.start()


def highlight_target_word(sentence: str, word: Dict, theme: str = "dark") -> str:
    """在韩文例句中智能高亮当前单词或其词干变形"""
    if not sentence or not word:
        return html.escape(sentence) if sentence else ""

    escaped_sentence = html.escape(sentence)
    korean_raw = word.get("korean", "").strip()
    clean_kr = re.sub(r"\(.*?\)|（.*?）", "", korean_raw).strip()
    if not clean_kr:
        return escaped_sentence

    candidates = set()
    candidates.add(clean_kr)

    # 1. 动词/形容词词干与常用变形推导
    if clean_kr.endswith("하다"):
        root = clean_kr[:-2]  # 如 공부, 운동, 사랑
        if root:
            candidates.add(root)
            candidates.add(root + "하")
            candidates.add(root + "해")
            candidates.add(root + "했")
            candidates.add(root + "합")
            candidates.add(root + "할")
    elif clean_kr.endswith("다") and len(clean_kr) >= 2:
        stem = clean_kr[:-1]  # 如 먹, 배우, 좋, 예쁘, 가, 오
        candidates.add(stem)

        # 常见元音缩合与过去式/活用变形
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

    # 按长度降序排序，优先匹配最长词素
    sorted_cands = sorted(filter(lambda x: len(x) >= 1, candidates), key=len, reverse=True)
    if not sorted_cands:
        return escaped_sentence

    # 高亮颜色（莫兰迪温润金/珊瑚红 + 下划线强调）
    if theme == "dark":
        hl_style = "color: #FFD166; font-weight: 700; text-decoration: underline;"
    else:
        hl_style = "color: #C0392B; font-weight: 700; text-decoration: underline;"

    # 构建正则
    pattern_parts = [re.escape(html.escape(c)) for c in sorted_cands]
    regex = re.compile(f"({'|'.join(pattern_parts)})")

    # 替换首个或全部出现的匹配项
    highlighted = regex.sub(f'<span style="{hl_style}">\\1</span>', escaped_sentence, count=1)
    return highlighted


def get_collocation_hint(word: Dict) -> str:
    """提取或智能推导韩语词汇的固定搭配与常用助词提示"""
    if not word:
        return ""
    if word.get("collocation"):
        return word["collocation"]

    kr = word.get("korean", "").strip()
    pos = word.get("pos", "").strip()

    # 1. 直接从韩文短语中提取已知助词模式
    particles = [
        ("을/를", "~을/를"),
        ("을 ", "~을/를"),
        ("를 ", "~을/를"),
        ("이/가", "~이/가"),
        ("이 ", "~이/가"),
        ("가 ", "~이/가"),
        ("에 ", "~에"),
        ("에서 ", "~에서"),
        ("에게 ", "~에게/한테"),
        ("한테 ", "~에게/한테"),
        ("과/와", "~과/와"),
        ("과 ", "~과/와"),
        ("와 ", "~과/와"),
        ("으로/로", "~으로/로"),
        ("으로 ", "~으로/로"),
        ("로 ", "~으로/로"),
        ("보다 ", "~보다"),
    ]
    for p_pat, p_val in particles:
        if p_pat in kr:
            return f"搭配助词: {p_val}"

    # 2. 根据动词/形容词特性推导常见助词模式
    if pos == "动词":
        if any(kr.endswith(x) for x in ["가다", "오다", "다니다", "도착하다", "떠나다", "출발하다", "들어가다", "올라가다", "내려가다"]):
            return "常用搭配: ~에 / ~에서 (场所/移动)"
        elif any(kr.endswith(x) for x in ["되다", "아니다", "필요하다", "생기다", "나다", "걸리다"]):
            return "常用搭配: ~이/가 (主格/状态)"
        elif any(kr.endswith(x) for x in ["사귀다", "어울리다", "싸우다", "결혼하다", "약혼하다", "헤어지다"]):
            return "常用搭配: ~과/와 (伴随对象)"
        elif any(kr.endswith(x) for x in ["주다", "보내다", "전화하다", "묻다", "말하다", "가르치다", "빌려주다"]):
            return "常用搭配: ~에게/한테 (授受对象)"
        elif any(kr.endswith(x) for x in ["좋아하다", "싫어하다", "먹다", "마시다", "보다", "읽다", "쓰다", "만들다", "사다", "팔다", "배우다", "잡다", "찾다"]):
            return "常用搭配: ~을/를 (宾格受事)"

    elif pos == "形容词":
        if any(kr.endswith(x) for x in ["좋다", "싫다", "많다", "적다", "크다", "작다", "예쁘다", "멋있다", "어렵다", "쉽다", "맛있다", "맛없다", "바쁘다", "아프다"]):
            return "常用搭配: ~이/가 (主格评价)"
        elif any(kr.endswith(x) for x in ["같다", "다르다", "비슷하다"]):
            return "常用搭配: ~과/와 / ~보다 (比较/差异)"

    return ""


def make_interactive_lyric_html(text: str, theme: str = "dark") -> str:
    """将歌词按韩文词块分词并包裹超链接，支持点击点查与悬停微光"""
    if not text:
        return ""
    words = re.findall(r"([가-힣a-zA-Z0-9]+|[^\s가-힣a-zA-Z0-9]+|\s+)", text)
    parts = []
    for chunk in words:
        if re.search(r"[가-힣]", chunk):
            parts.append(
                f"<a href='word:{chunk}' style='text-decoration: none; color: #FFFFFF; "
                f"border-bottom: 1.5px dashed rgba(56, 189, 248, 0.45); padding: 0 1px;'>{html.escape(chunk)}</a>"
            )
        else:
            parts.append(html.escape(chunk))
    return "".join(parts)


class CardWidget(QWidget):
    """翻转卡片组件，纯本地毫秒级秒翻，单击与拖拽互斥，发音完全解耦，支持字号比例缩放与拼写测验"""

    speak_requested = pyqtSignal(str)    # 仅由手动点击喇叭触发
    flip_done = pyqtSignal(bool)         # 翻转完成（True=背面）
    spelling_passed = pyqtSignal()       # 拼写正确通过信号
    spelling_exit_requested = pyqtSignal() # 请求退出拼写模式
    antonym_jump_requested = pyqtSignal(str) # 点击反义词标签请求跳转 (韩文原型)
    lyric_word_clicked = pyqtSignal(str)     # 点击歌词中的单词请求点查

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_back = False
        self._is_spelling_mode = False
        self._is_audio_first = False
        self._is_audio_first_revealed = False
        self._word: Optional[Dict] = None
        self._theme = "dark"
        self._compact = False
        self._korean_font_family = "Malgun Gothic"
        self._font_scale: float = 1.0
        self._all_words: list = []
        self._hanja_family_expanded: bool = False
        self._hanja_family_data: list = []
        self._current_hanja_breakdown: str = ""
        self._spelling_hint_count: int = 0
        self._is_spelling_submitting: bool = False

        # 拖拽与单击互斥状态
        self._press_pos: Optional[QPoint] = None
        self._drag_start_window_pos: Optional[QPoint] = None
        self._is_dragging: bool = False
        self._phonetic_tooltip: Optional[PhoneticTooltip] = None

        self._setup_ui()
        self._install_click_filters()

    def set_all_words(self, words: list):
        """注入全局词库用于汉字同根衍生词关联检索"""
        self._all_words = list(words) if words else []

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # 主布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 16, 20, 16)
        self._layout.setSpacing(8)

        # 辅助阴影生成函数
        def _make_shadow(blur=14, alpha=230, dy=1):
            sh = QGraphicsDropShadowEffect(self)
            sh.setBlurRadius(blur)
            sh.setColor(QColor(0, 0, 0, alpha))
            sh.setOffset(0, dy)
            return sh

        # ═════════════════════════════════════════════════════
        # ── 正面（Front） ──
        # ═════════════════════════════════════════════════════
        self._front = QWidget(self)
        front_layout = QVBoxLayout(self._front)
        front_layout.setContentsMargins(0, 0, 0, 0)
        front_layout.setSpacing(8)

        # 顶部行：词性标签 + 弹性伸缩 + 手动发音按钮
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self._pos_label = QLabel()
        self._pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self._pos_label)

        # 📖 所属单元/课程出处标签（Instagram 极简半透磨砂蓝药丸）
        self._source_badge = QLabel()
        self._source_badge.setObjectName("source_badge")
        self._source_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self._source_badge)

        top_row.addStretch()

        # 💡 韩语音变规则标签 (Instagram 极简低饱和浅紫药丸)
        self._mutation_badge = QPushButton()
        self._mutation_badge.setObjectName("mutation_badge")
        self._mutation_badge.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._mutation_badge.setToolTip("点击查看音变规则解析")
        self._mutation_badge.clicked.connect(self._show_mutation_info)
        self._mutation_badge.hide()
        top_row.addWidget(self._mutation_badge)

        # 🔊 独立手动发音按钮（Instagram 极简半透胶囊）
        self._speak_btn = QPushButton("🔊")
        self._speak_btn.setFixedSize(32, 32)
        self._speak_btn.setToolTip("播放发音 (手动点击)")
        self._speak_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._speak_btn.clicked.connect(self._on_speak)
        top_row.addWidget(self._speak_btn)

        front_layout.addLayout(top_row)

        # 韩语单词 — 弹性高度，禁止截断，配备高质量立体外发光文字阴影
        self._korean_label = QLabel()
        self._korean_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._korean_label.setWordWrap(True)
        self._korean_label.setTextFormat(Qt.TextFormat.RichText)
        self._korean_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._korean_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding
        )
        self._korean_label.setMinimumHeight(64)
        self._korean_label.setGraphicsEffect(_make_shadow(blur=18, alpha=245, dy=2))
        front_layout.addWidget(self._korean_label, stretch=1)

        # 实际读音/音变提示（Pronunciation，配备高对比文字投影）
        self._pron_label = QLabel()
        self._pron_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pron_label.setGraphicsEffect(_make_shadow(blur=8, alpha=240, dy=1))
        front_layout.addWidget(self._pron_label)

        # 点击提示（精致高对比胶囊药丸）
        self._hint_label = QLabel("点击卡片翻转查看释义")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setObjectName("hint_label")
        front_layout.addWidget(self._hint_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ═════════════════════════════════════════════════════
        # ── 背面（Back）带超薄极简弹性滚动区域 ──
        # ═════════════════════════════════════════════════════
        self._back_scroll = QScrollArea(self)
        self._back_scroll.setObjectName("back_scroll")
        self._back_scroll.setWidgetResizable(True)
        self._back_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._back_scroll.viewport().setAutoFillBackground(False)
        self._back_scroll.viewport().setStyleSheet("background: transparent;")
        self._back_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._back_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._back = QWidget()
        self._back.setObjectName("back_widget")
        self._back.setAutoFillBackground(False)
        self._back.setStyleSheet("background: transparent;")
        self._back_scroll.setWidget(self._back)

        back_layout = QVBoxLayout(self._back)
        back_layout.setContentsMargins(0, 2, 4, 2)
        back_layout.setSpacing(8)

        # 中文释义（配备高对比立体文字投影）
        self._chinese_label = QLabel()
        self._chinese_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chinese_label.setWordWrap(True)
        self._chinese_label.setGraphicsEffect(_make_shadow(blur=12, alpha=240, dy=1))
        back_layout.addWidget(self._chinese_label)

        # 学习增强信息行（词源标注: [汉字] 简体 / [外来] 原词 + 常用搭配/助词提示）
        self._back_meta_widget = QWidget(self._back)
        back_meta_layout = QHBoxLayout(self._back_meta_widget)
        back_meta_layout.setContentsMargins(0, 2, 0, 2)
        back_meta_layout.setSpacing(8)
        back_meta_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 词源胶囊标签（[汉字] 简体中文 或 [外来] English，固有词自动隐藏）
        self._origin_badge = QLabel()
        self._origin_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._origin_badge.hide()
        back_meta_layout.addWidget(self._origin_badge)

        self._collocation_badge = QLabel()
        self._collocation_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._collocation_badge.hide()
        back_meta_layout.addWidget(self._collocation_badge)

        # 反义词交互胶囊药丸（↔ 反义词 (释义)，点击可直接跳转到该词）
        self._antonym_btn = QPushButton()
        self._antonym_btn.setObjectName("antonym_btn")
        self._antonym_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._antonym_btn.clicked.connect(self._on_antonym_clicked)
        self._antonym_btn.hide()
        back_meta_layout.addWidget(self._antonym_btn)

        # 易混近义词辨析胶囊按钮 (辨析速览，点击展开精炼对照气泡)
        self._nuance_btn = QPushButton("辨析速览")
        self._nuance_btn.setObjectName("nuance_btn")
        self._nuance_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._nuance_btn.setToolTip("点击查看与近义词的微妙语境差异")
        self._nuance_btn.clicked.connect(self._toggle_nuance_box)
        self._nuance_btn.hide()
        back_meta_layout.addWidget(self._nuance_btn)

        back_layout.addWidget(self._back_meta_widget)

        # ═════════════════════════════════════════════════════
        # ⚡ 易混近义词与语境辨析展开卡片 (Nuance Diff Box)
        # ═════════════════════════════════════════════════════
        self._nuance_box = QWidget(self._back)
        self._nuance_box.setObjectName("nuance_box")
        nuance_layout = QVBoxLayout(self._nuance_box)
        nuance_layout.setContentsMargins(10, 8, 10, 8)
        nuance_layout.setSpacing(4)

        self._nuance_text_label = QLabel()
        self._nuance_text_label.setObjectName("nuance_text_label")
        self._nuance_text_label.setWordWrap(True)
        self._nuance_text_label.setTextFormat(Qt.TextFormat.RichText)
        nuance_layout.addWidget(self._nuance_text_label)

        self._nuance_expanded: bool = False
        self._nuance_box.hide()
        back_layout.addWidget(self._nuance_box)

        # ═════════════════════════════════════════════════════
        # 汉字词词根拆解与同根衍生词卡片 (Hanja Root & Family Box)
        # ═════════════════════════════════════════════════════
        self._hanja_box = QWidget(self._back)
        self._hanja_box.setObjectName("hanja_box")
        hanja_layout = QVBoxLayout(self._hanja_box)
        hanja_layout.setContentsMargins(8, 6, 8, 6)
        hanja_layout.setSpacing(4)

        # 词根拆解胶囊按钮（点击展开/收起衍生词家族）
        self._hanja_header_btn = QPushButton()
        self._hanja_header_btn.setObjectName("hanja_header_btn")
        self._hanja_header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._hanja_header_btn.clicked.connect(self._toggle_hanja_family)
        hanja_layout.addWidget(self._hanja_header_btn)

        # 衍生词展开容器
        self._hanja_family_widget = QWidget(self._hanja_box)
        self._hanja_family_widget.setObjectName("hanja_family_widget")
        self._hanja_family_layout = QVBoxLayout(self._hanja_family_widget)
        self._hanja_family_layout.setContentsMargins(2, 2, 2, 2)
        self._hanja_family_layout.setSpacing(4)
        hanja_layout.addWidget(self._hanja_family_widget)
        self._hanja_family_widget.setVisible(False)

        self._hanja_box.hide()
        back_layout.addWidget(self._hanja_box)

        # ═════════════════════════════════════════════════════
        # 🧩 常用地道搭配语块卡片 (Collocation Box)
        # ═════════════════════════════════════════════════════
        self._collocation_box = QWidget(self._back)
        self._collocation_box.setObjectName("collocation_box")
        colloc_layout = QVBoxLayout(self._collocation_box)
        colloc_layout.setContentsMargins(10, 6, 10, 8)
        colloc_layout.setSpacing(4)

        colloc_header = QHBoxLayout()
        colloc_header.setContentsMargins(0, 0, 0, 2)
        self._colloc_title_label = QLabel("常用地道搭配")
        self._colloc_title_label.setObjectName("colloc_title_label")
        colloc_header.addWidget(self._colloc_title_label)
        colloc_header.addStretch()
        colloc_layout.addLayout(colloc_header)

        self._colloc_items_widget = QWidget(self._collocation_box)
        self._colloc_items_layout = QVBoxLayout(self._colloc_items_widget)
        self._colloc_items_layout.setContentsMargins(0, 0, 0, 0)
        self._colloc_items_layout.setSpacing(4)
        colloc_layout.addWidget(self._colloc_items_widget)

        self._collocation_box.hide()
        back_layout.addWidget(self._collocation_box)

        # ═════════════════════════════════════════════════════
        # 动词/形容词常用活用变形速查卡片 (Conjugation Box)
        # ═════════════════════════════════════════════════════
        self._conjugation_box = QWidget(self._back)
        self._conjugation_box.setObjectName("conjugation_box")
        conj_layout = QVBoxLayout(self._conjugation_box)
        conj_layout.setContentsMargins(10, 6, 10, 8)
        conj_layout.setSpacing(5)

        conj_header = QHBoxLayout()
        conj_header.setContentsMargins(0, 0, 0, 2)
        self._conj_title_label = QLabel("常用活用变形")
        self._conj_title_label.setObjectName("conj_title_label")
        conj_header.addWidget(self._conj_title_label)

        self._conj_rule_label = QLabel("")
        self._conj_rule_label.setObjectName("conj_rule_label")
        self._conj_rule_label.setStyleSheet("color: #A78BFA; font-size: 10.5px; font-weight: 600;")
        conj_header.addWidget(self._conj_rule_label)

        conj_header.addStretch()

        self._conj_toggle_btn = QPushButton("▼ 展开")
        self._conj_toggle_btn.setObjectName("conj_toggle_btn")
        self._conj_toggle_btn.setFixedSize(56, 20)
        self._conj_toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._conj_toggle_btn.setStyleSheet(
            "QPushButton#conj_toggle_btn { background: rgba(255, 255, 255, 0.08); color: #CBD5E1; "
            "border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; font-size: 10px; font-weight: bold; } "
            "QPushButton#conj_toggle_btn:hover { background: rgba(255, 255, 255, 0.18); color: #FFFFFF; }"
        )
        self._conj_toggle_btn.clicked.connect(self._toggle_conjugation)
        conj_header.addWidget(self._conj_toggle_btn)
        conj_layout.addLayout(conj_header)

        # 变形胶囊展示容器（水平滚动或流式网格）
        self._conj_capsules_widget = QWidget(self._conjugation_box)
        self._conj_capsules_layout = QHBoxLayout(self._conj_capsules_widget)
        self._conj_capsules_layout.setContentsMargins(0, 2, 0, 2)
        self._conj_capsules_layout.setSpacing(5)
        conj_layout.addWidget(self._conj_capsules_widget)

        self._conjugation_expanded = True
        self._conjugation_box.hide()
        back_layout.addWidget(self._conjugation_box)

        # 分隔线
        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        back_layout.addWidget(self._sep)

        # ═════════════════════════════════════════════════════
        # 例句专属半透明高对比卡片内衬容器 (含助词高亮与独立发音)
        # ═════════════════════════════════════════════════════
        self._example_box = QWidget(self._back)
        self._example_box.setObjectName("example_box")
        ex_layout = QVBoxLayout(self._example_box)
        ex_layout.setContentsMargins(10, 6, 10, 8)
        ex_layout.setSpacing(4)

        # 顶部微型工具栏：标题 + 朗读完整例句按钮
        ex_header = QHBoxLayout()
        ex_header.setContentsMargins(0, 0, 0, 2)

        self._example_title_label = QLabel("日常例句")
        self._example_title_label.setObjectName("example_title_label")
        ex_header.addWidget(self._example_title_label)

        ex_header.addStretch()

        self._example_speak_btn = QPushButton("读例句")
        self._example_speak_btn.setObjectName("example_speak_btn")
        self._example_speak_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._example_speak_btn.setToolTip("朗读当前完整例句")
        self._example_speak_btn.clicked.connect(self._on_speak_example)
        ex_header.addWidget(self._example_speak_btn)
        ex_layout.addLayout(ex_header)

        # 韩文例句 (助词高亮 + 宽松行距)
        self._example_korean = QLabel()
        self._example_korean.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._example_korean.setWordWrap(True)
        self._example_korean.setTextFormat(Qt.TextFormat.RichText)
        self._example_korean.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._example_korean.setGraphicsEffect(_make_shadow(blur=6, alpha=200, dy=1))
        ex_layout.addWidget(self._example_korean)

        # 中文对照
        self._example_chinese = QLabel()
        self._example_chinese.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._example_chinese.setWordWrap(True)
        self._example_chinese.setGraphicsEffect(_make_shadow(blur=4, alpha=160, dy=1))
        ex_layout.addWidget(self._example_chinese)

        back_layout.addWidget(self._example_box)

        # ═════════════════════════════════════════════════════
        # 经典歌词 / 影视台词微语境卡片 (Instagram Story 质感)
        # ═════════════════════════════════════════════════════
        self._quote_box = QWidget(self._back)
        self._quote_box.setObjectName("quote_box")
        quote_layout = QVBoxLayout(self._quote_box)
        quote_layout.setContentsMargins(10, 8, 10, 8)
        quote_layout.setSpacing(5)

        # 顶部微型工具栏：标题 + 朗读歌词台词按钮
        quote_header = QHBoxLayout()
        quote_header.setContentsMargins(0, 0, 0, 2)

        self._quote_title_label = QLabel("经典歌词语境")
        self._quote_title_label.setObjectName("quote_title_label")
        quote_header.addWidget(self._quote_title_label)

        quote_header.addStretch()

        self._quote_speak_btn = QPushButton("听原声")
        self._quote_speak_btn.setObjectName("quote_speak_btn")
        self._quote_speak_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._quote_speak_btn.setToolTip("朗读当前歌词 / 台词金句")
        self._quote_speak_btn.clicked.connect(self._on_speak_quote)
        quote_header.addWidget(self._quote_speak_btn)
        quote_layout.addLayout(quote_header)

        # 韩文原句 (斜体手写质感 + 助词高亮 + 分词点击)
        self._quote_korean = QLabel()
        self._quote_korean.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._quote_korean.setWordWrap(True)
        self._quote_korean.setTextFormat(Qt.TextFormat.RichText)
        self._quote_korean.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self._quote_korean.linkActivated.connect(self._on_lyric_word_clicked)
        self._quote_korean.setGraphicsEffect(_make_shadow(blur=6, alpha=200, dy=1))
        quote_layout.addWidget(self._quote_korean)

        # 中文翻译
        self._quote_chinese = QLabel()
        self._quote_chinese.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._quote_chinese.setWordWrap(True)
        self._quote_chinese.setGraphicsEffect(_make_shadow(blur=4, alpha=160, dy=1))
        quote_layout.addWidget(self._quote_chinese)

        # 来源标注 (来源: 歌曲名 - 歌手名 / 来源: 影视剧名)
        self._quote_source_label = QLabel()
        self._quote_source_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._quote_source_label.setObjectName("quote_source_label")
        self._quote_source_label.setGraphicsEffect(_make_shadow(blur=4, alpha=140, dy=1))
        quote_layout.addWidget(self._quote_source_label)

        self._quote_box.hide()
        back_layout.addWidget(self._quote_box)

        # ═════════════════════════════════════════════════════
        # 歌词词内点击瞬时释义与活用解析卡片 (Word Inspect Box)
        # ═════════════════════════════════════════════════════
        self._word_inspect_box = QWidget(self._back)
        self._word_inspect_box.setObjectName("word_inspect_box")
        inspect_layout = QVBoxLayout(self._word_inspect_box)
        inspect_layout.setContentsMargins(10, 8, 10, 8)
        inspect_layout.setSpacing(4)

        inspect_top = QHBoxLayout()
        inspect_top.setContentsMargins(0, 0, 0, 0)
        self._inspect_title = QLabel("歌词分词解析")
        self._inspect_title.setStyleSheet("QLabel { color: #38BDF8; font-size: 11px; font-weight: bold; }")
        inspect_top.addWidget(self._inspect_title)
        inspect_top.addStretch()

        self._inspect_speak_btn = QPushButton("发音")
        self._inspect_speak_btn.setFixedSize(36, 22)
        self._inspect_speak_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._inspect_speak_btn.clicked.connect(self._on_speak_inspected_word)
        self._inspect_speak_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.08); color: #FFFFFF; border: none; border-radius: 6px; font-size: 10px; }"
            "QPushButton:hover { background: rgba(56, 189, 248, 0.40); }"
        )
        inspect_top.addWidget(self._inspect_speak_btn)

        self._inspect_close_btn = QPushButton("✕")
        self._inspect_close_btn.setFixedSize(20, 20)
        self._inspect_close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._inspect_close_btn.clicked.connect(lambda: self._word_inspect_box.hide())
        self._inspect_close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #94A3B8; border: none; font-size: 11px; }"
            "QPushButton:hover { color: #FFFFFF; }"
        )
        inspect_top.addWidget(self._inspect_close_btn)
        inspect_layout.addLayout(inspect_top)

        self._inspect_text_lbl = QLabel()
        self._inspect_text_lbl.setWordWrap(True)
        self._inspect_text_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._inspect_text_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        inspect_layout.addWidget(self._inspect_text_lbl)

        # 活用变形微胶囊容器 (若点击词为动词/形容词)
        self._inspect_conj_layout = QHBoxLayout()
        self._inspect_conj_layout.setContentsMargins(0, 2, 0, 2)
        self._inspect_conj_layout.setSpacing(4)
        inspect_layout.addLayout(self._inspect_conj_layout)

        self._word_inspect_box.hide()
        back_layout.addWidget(self._word_inspect_box)
        back_layout.addStretch()

        # ═════════════════════════════════════════════════════
        # ── 键盘韩打拼写测验模式容器（Spelling Quiz Mode） ──
        # ═════════════════════════════════════════════════════
        self._spelling_container = QWidget(self)
        self._spelling_container.setObjectName("spelling_container")
        spelling_layout = QVBoxLayout(self._spelling_container)
        spelling_layout.setContentsMargins(12, 8, 12, 8)
        spelling_layout.setSpacing(6)

        spell_top = QHBoxLayout()
        spell_top.setContentsMargins(0, 0, 0, 0)

        self._spell_hint_btn = QPushButton("首字提示 (Tab)")
        self._spell_hint_btn.setObjectName("spell_hint_btn")
        self._spell_hint_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._spell_hint_btn.setToolTip("按 Tab 键逐字揭晓提示")
        self._spell_hint_btn.clicked.connect(self._on_spelling_hint)
        spell_top.addWidget(self._spell_hint_btn)

        spell_top.addStretch()

        self._spell_speak_btn = QPushButton("听音")
        self._spell_speak_btn.setObjectName("spell_speak_btn")
        self._spell_speak_btn.setFixedSize(68, 26)
        self._spell_speak_btn.setToolTip("听音辨词 (Ctrl+P)")
        self._spell_speak_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._spell_speak_btn.clicked.connect(self._on_speak)
        spell_top.addWidget(self._spell_speak_btn)
        spelling_layout.addLayout(spell_top)

        # 1. 提示标签：中文释义 + 词性 + 音标
        self._spelling_prompt_label = QLabel()
        self._spelling_prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spelling_prompt_label.setWordWrap(True)
        self._spelling_prompt_label.setTextFormat(Qt.TextFormat.RichText)
        self._spelling_prompt_label.setGraphicsEffect(_make_shadow(blur=10, alpha=230, dy=1))
        spelling_layout.addWidget(self._spelling_prompt_label, stretch=1)

        # 2. Instagram 极简发光下划线韩文输入框
        self._spelling_input = SpellingUnderlineInput(self._spelling_container)
        self._spelling_input.setObjectName("spelling_input")
        self._spelling_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spelling_input.setPlaceholderText("在此键盘韩打输入，即时自动核对...")
        self._spelling_input.setFixedHeight(44)
        self._spelling_input.textChanged.connect(self._on_spelling_text_changed)
        self._spelling_input.returnPressed.connect(self._on_spelling_submit)
        self._spelling_input.tab_pressed.connect(self._on_spelling_hint)
        self._spelling_input.escape_pressed.connect(self.spelling_exit_requested.emit)
        spelling_layout.addWidget(self._spelling_input)

        # 3. 校验反馈标签
        self._spelling_feedback = QLabel()
        self._spelling_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spelling_feedback.setWordWrap(True)
        self._spelling_feedback.setTextFormat(Qt.TextFormat.RichText)
        self._spelling_feedback.setFixedHeight(24)
        spelling_layout.addWidget(self._spelling_feedback)

        # 4. 底部极简小提示
        self._spelling_hint_label = QLabel("⌨️ 直接打字即时匹配 · Tab 首字提示 · Enter 提交 · Esc 退出")
        self._spelling_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spelling_hint_label.setObjectName("spelling_hint_label")
        spelling_layout.addWidget(self._spelling_hint_label)

        # 叠加三个面
        self._layout.addWidget(self._front)
        self._layout.addWidget(self._back_scroll)
        self._layout.addWidget(self._spelling_container)
        self._back_scroll.hide()
        self._spelling_container.hide()

    # ─────────────────────────────────────────────────────────
    # 瞬时秒翻与拼写模式逻辑
    # ─────────────────────────────────────────────────────────

    def flip(self):
        """瞬时秒翻：纯本地 UI 控件 show/hide 切换，完全静音、毫秒级响应"""
        if self._is_spelling_mode:
            return
        # 盲听磨耳朵模式：首次点击先揭晓正面韩文，再次点击才翻面看释义
        if self._is_audio_first and not self._is_audio_first_revealed and not self._is_back:
            self._is_audio_first_revealed = True
            self._update_display()
            return

        self._is_back = not self._is_back
        if self._is_back:
            self._front.hide()
            self._back_scroll.show()
        else:
            self._back_scroll.hide()
            self._front.show()
        self.flip_done.emit(self._is_back)

    def flip_to_front(self):
        """强制回到正面（切换单词时调用）"""
        self._is_audio_first_revealed = False
        if self._is_spelling_mode:
            return
        if self._is_back:
            self._is_back = False
            self._back_scroll.hide()
            self._front.show()

    def set_audio_first_mode(self, enabled: bool):
        """开启或退出盲听磨耳朵模式"""
        self._is_audio_first = enabled
        self._is_audio_first_revealed = False
        self._update_display()

    def set_spelling_mode(self, enabled: bool):
        """开启或退出拼写测验模式"""
        self._is_spelling_mode = enabled
        if enabled:
            self._front.hide()
            self._back_scroll.hide()
            self._spelling_container.show()
            self._update_spelling_display()
        else:
            self._spelling_container.hide()
            self.flip_to_front()
            self._update_display()

    def set_word(self, word: Dict):
        """更新显示的单词"""
        self._word = word
        self._is_audio_first_revealed = False
        if self._is_spelling_mode:
            self._update_spelling_display()
        else:
            self.flip_to_front()
            self._update_display()

    def _update_spelling_display(self):
        """刷新拼写练习模式下的提示与输入框"""
        if not self._word:
            return
        w = self._word
        meaning = w.get("meaning", w.get("chinese", ""))
        pos = w.get("pos", "")
        pron = w.get("pronunciation", "").strip()

        scale = getattr(self, "_font_scale", 1.0)
        c_size = max(16, int(20 * scale))
        p_size = max(11, int(13 * scale))

        prompt_html = f"<div style='text-align: center;'><span style='font-size: {c_size}px; font-weight: 700; color: #FFFFFF;'>{html.escape(meaning)}</span>"
        if pos:
            prompt_html += f" <span style='font-size: {p_size}px; color: #93C5FD; font-weight: 600;'>({html.escape(pos)})</span>"
        if pron:
            prompt_html += f"<br><span style='font-size: {p_size}px; font-style: italic; color: #F1F5F9; font-weight: 500;'>[{html.escape(pron)}]</span>"
        prompt_html += "</div>"

        self._spelling_prompt_label.setText(prompt_html)
        self._spelling_hint_count = 0
        self._is_spelling_submitting = False
        self._spelling_input.clear()
        self._spelling_input.setPlaceholderText("在此键盘韩打输入，即时自动核对...")
        self._spelling_feedback.clear()
        self._reset_spelling_input_style()
        self._spelling_input.setFocus()

    def _reset_spelling_input_style(self):
        """重置为 Instagram 极简发光下划线输入框"""
        scale = getattr(self, "_font_scale", 1.0)
        font_family = getattr(self, "_korean_font_family", "Malgun Gothic")
        f_size = max(18, int(22 * scale))

        self._spelling_input.setStyleSheet(
            f"QLineEdit#spelling_input {{ "
            f"  background: transparent; "
            f"  color: #FFFFFF; "
            f"  border: none; "
            f"  border-bottom: 2px solid rgba(255, 255, 255, 0.40); "
            f"  font-size: {f_size}px; "
            f"  font-weight: 700; "
            f"  letter-spacing: 2px; "
            f"  padding: 4px 8px; "
            f"  font-family: '{font_family}', 'Malgun Gothic', sans-serif; "
            f"}} "
            f"QLineEdit#spelling_input:focus {{ "
            f"  border-bottom: 2px solid #60A5FA; "
            f"}}"
        )
        self._spell_hint_btn.setStyleSheet(
            "QPushButton#spell_hint_btn { background: rgba(30, 32, 40, 0.75); color: #FCD34D; "
            "border: 1px solid rgba(252, 211, 77, 0.35); border-radius: 13px; font-size: 11px; font-weight: 600; padding: 2px 10px; }"
            "QPushButton#spell_hint_btn:hover { background: rgba(252, 211, 77, 0.20); border-color: #FCD34D; }"
        )
        self._spell_speak_btn.setStyleSheet(
            "QPushButton#spell_speak_btn { background: rgba(20, 20, 26, 0.75); color: #FFFFFF; "
            "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 13px; font-size: 11px; font-weight: 600; padding: 2px 10px; }"
            "QPushButton#spell_speak_btn:hover { background: rgba(255, 255, 255, 0.22); border-color: rgba(255, 255, 255, 0.40); }"
        )
        self._spelling_hint_label.setStyleSheet(
            "QLabel#spelling_hint_label { color: #CBD5E1; font-size: 11px; font-weight: 500; }"
        )

    def _on_spelling_text_changed(self, text: str):
        """监听键盘韩文输入，支持打字即时自动核对通过"""
        if not self._word or self._is_spelling_submitting:
            return
        user_input = text.strip()
        if not user_input:
            return

        clean_kr = re.sub(r"\(.*?\)|（.*?）", "", self._word.get("korean", "")).strip()
        if user_input == clean_kr or user_input.replace(" ", "") == clean_kr.replace(" ", ""):
            self._on_spelling_correct(clean_kr)

    def _on_spelling_correct(self, clean_kr: str):
        """拼写正确即时反馈：薄荷绿微光 + 发音 + 400ms 丝滑切词"""
        if self._is_spelling_submitting:
            return
        self._is_spelling_submitting = True

        scale = getattr(self, "_font_scale", 1.0)
        font_family = getattr(self, "_korean_font_family", "Malgun Gothic")
        f_size = max(18, int(22 * scale))

        self._spelling_input.setStyleSheet(
            f"QLineEdit#spelling_input {{ "
            f"  background: rgba(46, 204, 113, 0.12); "
            f"  color: #2ECC71; "
            f"  border: none; "
            f"  border-bottom: 2.5px solid #2ECC71; "
            f"  border-radius: 6px; "
            f"  font-size: {f_size}px; "
            f"  font-weight: 700; "
            f"  letter-spacing: 2px; "
            f"  padding: 4px 8px; "
            f"  font-family: '{font_family}', 'Malgun Gothic', sans-serif; "
            f"}}"
        )
        self._spelling_feedback.setText("<span style='color: #2ECC71; font-weight: bold;'>✓ 拼写正确！即将进入下一词...</span>")
        self.speak_requested.emit(clean_kr)
        QTimer.singleShot(400, self.spelling_passed.emit)

    def _on_spelling_submit(self):
        """用户按 Enter 回车键提交核对，错误则触发弹簧抖动与珊瑚红提示"""
        if not self._word or self._is_spelling_submitting:
            return
        user_input = self._spelling_input.text().strip()
        clean_kr = re.sub(r"\(.*?\)|（.*?）", "", self._word.get("korean", "")).strip()

        if user_input and (user_input == clean_kr or user_input.replace(" ", "") == clean_kr.replace(" ", "")):
            self._on_spelling_correct(clean_kr)
        else:
            self._spelling_input.shake()
            scale = getattr(self, "_font_scale", 1.0)
            font_family = getattr(self, "_korean_font_family", "Malgun Gothic")
            f_size = max(18, int(22 * scale))
            self._spelling_input.setStyleSheet(
                f"QLineEdit#spelling_input {{ "
                f"  background: rgba(235, 87, 87, 0.14); "
                f"  color: #EB5757; "
                f"  border: none; "
                f"  border-bottom: 2.5px solid #EB5757; "
                f"  border-radius: 6px; "
                f"  font-size: {f_size}px; "
                f"  font-weight: 700; "
                f"  letter-spacing: 2px; "
                f"  padding: 4px 8px; "
                f"  font-family: '{font_family}', 'Malgun Gothic', sans-serif; "
                f"}}"
            )
            self._spelling_feedback.setText(
                f"<span style='color: #EB5757; font-weight: bold;'>❌ 核对未通过 (按 Tab 可渐显首字提示)</span>"
            )
            QTimer.singleShot(900, self._reset_spelling_input_style)

    def _on_spelling_hint(self):
        """按 Tab 键或点击提示按钮渐显首字前缀"""
        if not self._word or self._is_spelling_submitting:
            return
        clean_kr = re.sub(r"\(.*?\)|（.*?）", "", self._word.get("korean", "")).strip()
        if not clean_kr:
            return

        self._spelling_hint_count += 1
        hint_len = min(len(clean_kr), self._spelling_hint_count)
        prefix = clean_kr[:hint_len]
        self._spelling_input.setPlaceholderText(f"힌트: {prefix}...")
        self._spelling_feedback.setText(
            f"<span style='color: #FCD34D; font-weight: 600;'>💡 首字提示: <b>{html.escape(prefix)}</b>...</span>"
        )

    def _update_display(self):
        if not self._word:
            return
        w = self._word

        # 1. 词性
        pos = w.get("pos", "")
        self._pos_label.setText(pos if pos else "—")

        # 1.5 单元与课程溯源标签 (Unit & Lesson Breadcrumb)
        unit_id = w.get("_unit")
        lesson_id = w.get("_lesson")
        lesson_name = w.get("_lesson_name", "")
        book_name = w.get("_book_name", "")
        unit_name = w.get("_unit_name", "")

        if unit_id and lesson_id:
            source_text = f"📖 第{unit_id}单元 · 第{lesson_id}课"
            self._source_badge.setText(source_text)
            full_path = f"{book_name} · {unit_name} · {lesson_name}".strip(" ·")
            self._source_badge.setToolTip(full_path if full_path else source_text)
            self._source_badge.show()
        elif lesson_id:
            source_text = f"📖 第{lesson_id}课"
            self._source_badge.setText(source_text)
            self._source_badge.setToolTip(f"{book_name} · {lesson_name}".strip(" ·"))
            self._source_badge.show()
        else:
            self._source_badge.hide()

        # 2. 韩语核心大字（纯净大方 / 盲听磨耳朵遮挡）
        korean_text = w.get("korean", "")
        clean_kr = re.sub(r"\(.*?\)", "", korean_text)
        clean_kr = re.sub(r"（.*?）", "", clean_kr).strip()

        if self._is_audio_first and not self._is_audio_first_revealed and not self._is_back:
            self._korean_label.setText("<span style='font-size: 17px; font-weight: bold; opacity: 0.85; letter-spacing: 1px;'>[ 🎧 听音猜词 · 点击揭晓 ]</span>")
            self._pron_label.hide()
            self._mutation_badge.hide()
            self._hint_label.setText("点击卡片揭晓韩文，再次点击查看释义")
        else:
            self._korean_label.setText(clean_kr if clean_kr else korean_text)
            
            # 3. 韩语音变规则与【实际读音】解析
            m_info = w.get("_mutation")
            if not m_info:
                m_info = analyze_pronunciation(clean_kr if clean_kr else korean_text, w.get("pron_kr", ""))

            pron = w.get("pronunciation", "").strip()
            if m_info and m_info.get("has_mutation"):
                r_tag = m_info.get("rule_tag", "[音变]")
                self._mutation_badge.setText(r_tag)
                self._mutation_badge.setToolTip(f"💡 {r_tag} {m_info.get('explanation', '')}\n点击查看规则解析")
                self._apply_mutation_badge_style()
                self._mutation_badge.show()

                actual_p = m_info.get("actual_pron", "")
                if pron and actual_p:
                    self._pron_label.setText(
                        f"<span style='color: #A0A5B5;'>[{pron}]</span> &nbsp;·&nbsp; "
                        f"<span style='color: #E2E8F0; font-weight: 600;'>读音: [{actual_p}]</span>"
                    )
                elif actual_p:
                    self._pron_label.setText(f"<span style='color: #E2E8F0; font-weight: 600;'>读音: [{actual_p}]</span>")
                elif pron:
                    self._pron_label.setText(f"<span style='color: #A0A5B5;'>[{pron}]</span>")
                self._pron_label.show()
            else:
                self._mutation_badge.hide()
                if pron:
                    self._pron_label.setText(f"<span style='color: #A0A5B5;'>[{pron}]</span>")
                    self._pron_label.show()
                else:
                    self._pron_label.hide()
            self._hint_label.setText("点击卡片翻转查看释义")

        # 4. 中文释义
        meaning = w.get("meaning", w.get("chinese", ""))
        self._chinese_label.setText(meaning)

        # 5. 背面词源标注（统一转换为简体中文 [汉字] / [外来] / 固有词自动隐藏）
        word_type = w.get("word_type", "").strip().lower()
        origin = w.get("origin", "")
        if not word_type or not origin:
            hanja_raw = w.get("hanja", "").strip()
            if hanja_raw:
                word_type = "hanja"
                origin = re.sub(r"[\s\-\─]+$", "", hanja_raw).strip()
            else:
                word_type = "pure"
                origin = None

        has_origin = False
        if word_type == "hanja" and origin:
            # 汉字词统一采用简体中文展示
            formatted_hanja = format_hanja_origin(origin)
            self._origin_badge.setText(formatted_hanja)
            self._apply_origin_badge_style("hanja")
            self._origin_badge.show()
            has_origin = True
        elif word_type == "loanword" and origin:
            self._origin_badge.setText(f"[外来] {origin}")
            self._apply_origin_badge_style("loanword")
            self._origin_badge.show()
            has_origin = True
        else:
            self._origin_badge.hide()

        # 6. 反义词对照胶囊 (Antonyms)
        ants = w.get("antonyms", [])
        has_antonym = False
        if ants and isinstance(ants, list) and len(ants) > 0:
            ant = ants[0]
            ant_kr = ant.get("kr", "")
            ant_cn = ant.get("cn", "")
            if ant_kr:
                label_text = f"↔ {ant_kr}" + (f" ({ant_cn})" if ant_cn else "")
                self._antonym_btn.setText(label_text)
                self._antonym_btn.setToolTip(f"点击立即跳转学习反义词 [{ant_kr}]")
                self._antonym_btn.setProperty("target_kr", ant_kr)
                self._antonym_btn.show()
                has_antonym = True
            else:
                self._antonym_btn.hide()
        else:
            self._antonym_btn.hide()

        # 6.0 易混近义词与语境辨析胶囊 (Nuance Diff)
        nuance = w.get("nuance_diff", "")
        has_nuance = bool(nuance and nuance.strip())
        if has_nuance:
            self._nuance_btn.show()
            hl_nuance = re.sub(r"(vs\s+)", r"<b style='color: #F43F5E;'>\1</b>", html.escape(nuance))
            self._nuance_text_label.setText(
                f"<div style='line-height: 1.5; font-size: 11.5px; color: #E2E8F0;'>"
                f"⚡ <b style='color: #38BDF8;'>语境辨析</b>: {hl_nuance}"
                f"</div>"
            )
            self._nuance_box.setVisible(self._nuance_expanded)
        else:
            self._nuance_btn.hide()
            self._nuance_box.hide()

        # 6.1 固定搭配与助词提示（Collocation）
        collocation = get_collocation_hint(w)
        collocs = w.get("collocations", [])
        if collocs and isinstance(collocs, list) and len(collocs) > 0:
            # 有完整搭配卡片时，隐藏顶部简易小胶囊，避免重复
            self._collocation_badge.hide()
            self._build_collocation_ui(collocs, w)
            self._collocation_box.show()
            self._sep.show()
        elif collocation:
            self._collocation_badge.setText(f"💡 {collocation}")
            self._collocation_badge.show()
            self._collocation_box.hide()
        else:
            self._collocation_badge.hide()
            self._collocation_box.hide()

        # 6.3 动词/形容词常用活用变形速查卡片 (Conjugation Engine)
        kr_base = w.get("korean", "")
        clean_kr_base = re.sub(r"\(.*?\)|（.*?）", "", kr_base).strip()
        is_predicate = clean_kr_base.endswith("다") and (w.get("pos") in ("动词", "形容词", "", "谓词") or clean_kr_base.endswith("하다"))
        if is_predicate:
            caps = get_conjugation_capsules(clean_kr_base)
            if caps:
                conj_info = conjugate_korean_word(clean_kr_base)
                rule_note = conj_info.get("rule", "") if conj_info else ""
                self._conj_rule_label.setText(f"· {rule_note}" if rule_note else "")
                self._build_conjugation_ui(caps)
                self._conjugation_box.show()
                self._sep.show()
            else:
                self._conjugation_box.hide()
        else:
            self._conjugation_box.hide()

        # 如果背面没有任何 meta 信息，隐藏容器节省空间
        has_back_meta = bool(has_origin or has_antonym or has_nuance or (collocation and not collocs))
        self._back_meta_widget.setVisible(has_back_meta)

        # 6.5 汉字词词根拆解与同根衍生词卡片
        hanja_breakdown = get_hanja_breakdown(w)
        if hanja_breakdown:
            self._current_hanja_breakdown = hanja_breakdown
            self._hanja_family_data = get_hanja_family_words(w, self._all_words)
            self._update_hanja_header_text()
            self._build_hanja_family_ui(self._hanja_family_data)
            self._apply_hanja_box_style()
            self._hanja_family_widget.setVisible(self._hanja_family_expanded)
            self._hanja_box.show()
        else:
            self._current_hanja_breakdown = ""
            self._hanja_family_data = []
            self._hanja_box.hide()

        # 7. 例句区域（助词色彩标注 + 独立发音 / i-dle 语法注解联动）
        grammar_note = w.get("grammar_notes", "")
        ex_kr = w.get("example_korean") or w.get("example_kr") or ""
        ex_cn = w.get("example_chinese") or w.get("example_cn") or ""
        if not ex_kr and w.get("examples"):
            ex_kr = w["examples"][0].get("korean", "")
            ex_cn = w["examples"][0].get("chinese", "")

        if grammar_note:
            self._example_title_label.setText("📝 核心语法与关键词拆解")
            self._example_korean.setText(f"<span style='color: #67E8F9; font-weight: 600;'>{html.escape(grammar_note)}</span>")
            self._example_chinese.setText(f"📖 歌词出处: {html.escape(w.get('source_info', ''))}")
            self._example_box.show()
            self._sep.show()
        elif ex_kr:
            self._example_title_label.setText("💬 日常例句")
            hl_kr = highlight_sentence_with_particles(ex_kr, w, self._theme)
            self._example_korean.setText(f"{hl_kr}")
            self._example_chinese.setText(f"{ex_cn}")
            self._example_box.show()
            self._sep.show()
        else:
            self._example_box.hide()
            self._sep.hide()

        # 8. 🎵 经典歌词 / 影视台词微语境卡片渲染 (Instagram Story 氛围感)
        q_kr = w.get("quote_kr") or (w.get("quote_lyric", {}).get("kr") if isinstance(w.get("quote_lyric"), dict) else "")
        q_cn = w.get("quote_cn") or (w.get("quote_lyric", {}).get("cn") if isinstance(w.get("quote_lyric"), dict) else "")
        q_src = w.get("quote_source") or w.get("source_info") or (w.get("quote_lyric", {}).get("source") if isinstance(w.get("quote_lyric"), dict) else "")
        q_type = w.get("quote_type") or (w.get("quote_lyric", {}).get("type", "song") if isinstance(w.get("quote_lyric"), dict) else "song")

        if q_kr:
            icon_title = "🎵 i-dle 专属金句" if ("IDLE" in str(q_src).upper() or w.get("is_idle_lyric")) else ("🎵 经典歌词语境" if q_type == "song" else "🎬 影视原声名台词")
            self._quote_title_label.setText(icon_title)
            hl_quote_kr = make_interactive_lyric_html(q_kr, self._theme)
            self._quote_korean.setText(f"“ {hl_quote_kr} ”")
            self._quote_chinese.setText(f"{q_cn}")
            
            source_prefix = "🎧 来源: " if q_type == "song" else "🎬 出处: "
            self._quote_source_label.setText(f"{source_prefix}{q_src}")
            self._quote_box.show()
            self._sep.show()
        else:
            self._quote_box.hide()

    def _on_lyric_word_clicked(self, link_url: str):
        """点击歌词中的单个单词，触发瞬时释义与活用解析"""
        clicked_word = link_url.replace("word:", "").strip()
        if not clicked_word:
            return

        self._inspected_current_word = clicked_word
        self.lyric_word_clicked.emit(clicked_word)

        # 1. 尝试在全局词库与离线词典中快速匹配
        meaning = "歌词原词"
        pron = ""
        pos = ""
        matched = None

        if self._all_words:
            matched = next((w for w in self._all_words if w.get("korean") == clicked_word or clicked_word in w.get("korean", "")), None)

        if matched:
            meaning = matched.get("meaning", matched.get("chinese", ""))
            pron = matched.get("pronunciation", "")
            pos = matched.get("pos", "")
        else:
            from core.translator_manager import OfflineDictEngine
            off = OfflineDictEngine()
            res = off.lookup(clicked_word)
            if res.get("success"):
                meaning = res.get("text", "")
                pron = res.get("pronunciation", "")
                pos = res.get("pos", "")

        # 2. 渲染释义文本
        meta_parts = []
        if pos: meta_parts.append(f"<span style='color: #6EE7B7;'>[{pos}]</span>")
        if pron: meta_parts.append(f"<span style='color: #E2E8F0; font-style: italic;'>/{pron}/</span>")
        meta_html = " ".join(meta_parts)

        self._inspect_text_lbl.setText(
            f"<b style='font-size: 13px; color: #FFFFFF;'>{html.escape(clicked_word)}</b> {meta_html}<br>"
            f"<span style='color: #93C5FD; font-size: 12px;'>{html.escape(meaning)}</span>"
        )

        # 3. 若为动词/形容词，生成常用活用胶囊
        while self._inspect_conj_layout.count():
            item = self._inspect_conj_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        clean_base = re.sub(r"[\s\(\)（）\-_~·/]", "", clicked_word)
        if clean_base.endswith("다") or clean_base.endswith("하다") or pos in ("动词", "形容词"):
            capsules = get_conjugation_capsules(clean_base)
            for c in capsules[:4]:
                cap_btn = QPushButton(f"{c['title']}: {c['kr']}")
                cap_btn.setFixedHeight(20)
                cap_btn.setStyleSheet(
                    "QPushButton { background: rgba(56, 189, 248, 0.15); color: #38BDF8; "
                    "border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 6px; font-size: 10px; padding: 0 4px; }"
                )
                self._inspect_conj_layout.addWidget(cap_btn)

        self._word_inspect_box.show()

    def _on_speak_inspected_word(self):
        """朗读当前选中的分词"""
        word = getattr(self, "_inspected_current_word", "")
        if word:
            self.speak_requested.emit(word)

    def _on_speak_example(self):
        """点击微型声波按钮，独立朗读完整韩文例句"""
        if not self._word:
            return
        w = self._word
        ex_kr = w.get("example_korean") or w.get("example_kr") or ""
        if not ex_kr and w.get("examples"):
            ex_kr = w["examples"][0].get("korean", "")
        if ex_kr:
            clean_sentence = re.sub(r"\(.*?\)|（.*?）", "", ex_kr).strip()
            self.speak_requested.emit(clean_sentence if clean_sentence else ex_kr)

    def _on_speak_quote(self):
        """点击微型音符按钮，独立朗读经典歌词 / 影视台词金句"""
        if not self._word:
            return
        w = self._word
        q_kr = w.get("quote_kr") or (w.get("quote_lyric", {}).get("kr") if isinstance(w.get("quote_lyric"), dict) else "")
        if q_kr:
            clean_sentence = re.sub(r"\(.*?\)|（.*?）", "", q_kr).strip()
            self.speak_requested.emit(clean_sentence if clean_sentence else q_kr)

    def _on_antonym_clicked(self):
        """点击反义词胶囊触发跨词跳转"""
        target_kr = self._antonym_btn.property("target_kr")
        if target_kr:
            self.antonym_jump_requested.emit(target_kr)

    def _build_collocation_ui(self, collocs: list, word: dict):
        """动态构建常用地道搭配胶囊卡片（包含韩文短语、助词高亮、中文释义与独立朗读按钮）"""
        while self._colloc_items_layout.count():
            item = self._colloc_items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        scale = getattr(self, "_font_scale", 1.0)
        font_family = getattr(self, "_korean_font_family", "Malgun Gothic")
        kr_size = max(12, int(13 * scale))
        cn_size = max(11, int(12 * scale))

        for c_item in collocs[:3]:
            c_kr = c_item.get("kr", "")
            c_cn = c_item.get("cn", "")
            if not c_kr:
                continue

            item_card = QWidget()
            item_card.setObjectName("colloc_item_card")
            item_layout = QHBoxLayout(item_card)
            item_layout.setContentsMargins(8, 4, 8, 4)
            item_layout.setSpacing(6)

            # 韩文短语（带助词色彩标注）
            hl_kr = highlight_sentence_with_particles(c_kr, word, self._theme)
            kr_lbl = QLabel(f"• {hl_kr}")
            kr_lbl.setTextFormat(Qt.TextFormat.RichText)
            kr_lbl.setStyleSheet(f"color: #FFFFFF; font-size: {kr_size}px; font-weight: 600; font-family: '{font_family}', sans-serif;")
            item_layout.addWidget(kr_lbl)

            if c_cn:
                cn_lbl = QLabel(f"({c_cn})")
                cn_lbl.setStyleSheet(f"color: #94A3B8; font-size: {cn_size}px; font-weight: 400;")
                item_layout.addWidget(cn_lbl)

            item_layout.addStretch()

            # 独立微型发音喇叭
            speak_btn = QPushButton("🔊")
            speak_btn.setFixedSize(22, 22)
            speak_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            speak_btn.setToolTip(f"朗读搭配: {c_kr}")
            speak_btn.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.08); color: #6EE7B7; border: 1px solid rgba(110, 231, 183, 0.30); border-radius: 11px; font-size: 10px; }"
                "QPushButton:hover { background: rgba(16, 185, 129, 0.25); border-color: #10B981; color: #FFFFFF; }"
            )
            clean_c_kr = re.sub(r"\(.*?\)|（.*?）", "", c_kr).strip()
            speak_btn.clicked.connect(lambda checked, t=clean_c_kr: self.speak_requested.emit(t))
            item_layout.addWidget(speak_btn)

            item_card.setStyleSheet(
                "QWidget#colloc_item_card { background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; }"
                "QWidget#colloc_item_card:hover { background: rgba(255, 255, 255, 0.10); border-color: rgba(255, 255, 255, 0.22); }"
            )

            self._colloc_items_layout.addWidget(item_card)

    def _toggle_nuance_box(self):
        """展开或收起易混近义词语境辨析卡片"""
        self._nuance_expanded = not self._nuance_expanded
        self._nuance_box.setVisible(self._nuance_expanded)
        self._nuance_btn.setStyleSheet(
            "QPushButton#nuance_btn { background: rgba(56, 189, 248, 0.32); color: #FFFFFF; "
            "border: 1px solid #38BDF8; border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: bold; }"
            if self._nuance_expanded else
            "QPushButton#nuance_btn { background: rgba(56, 189, 248, 0.16); color: #38BDF8; "
            "border: 1px solid rgba(56, 189, 248, 0.40); border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: bold; } "
            "QPushButton#nuance_btn:hover { background: rgba(56, 189, 248, 0.28); color: #FFFFFF; }"
        )

    def _toggle_conjugation(self):
        """展开或折叠动词/形容词常用活用变形胶囊栏"""
        self._conjugation_expanded = not self._conjugation_expanded
        self._conj_capsules_widget.setVisible(self._conjugation_expanded)
        self._conj_toggle_btn.setText("▲ 收起" if self._conjugation_expanded else "▼ 展开")

    def _build_conjugation_ui(self, capsules: list):
        """动态构建谓词常用活用变形胶囊按钮（支持即时朗读发音）"""
        while self._conj_capsules_layout.count():
            item = self._conj_capsules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        scale = getattr(self, "_font_scale", 1.0)
        font_family = getattr(self, "_korean_font_family", "Malgun Gothic")
        btn_font_size = max(10, int(11 * scale))

        for cap in capsules:
            title = cap.get("title", "")
            kr = cap.get("kr", "")
            desc = cap.get("desc", "")
            tag = cap.get("tag", "")
            if not kr:
                continue

            btn = QPushButton(f"{title}: {kr}")
            btn.setObjectName("conj_pill_btn")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setToolTip(f"💡 {tag} ({desc})\n点击即时朗读: {kr}")
            btn.setStyleSheet(
                f"QPushButton#conj_pill_btn {{ "
                f"  background: rgba(167, 139, 250, 0.14); "
                f"  color: #E2E8F0; "
                f"  border: 1px solid rgba(167, 139, 250, 0.35); "
                f"  border-radius: 9px; "
                f"  padding: 3px 7px; "
                f"  font-size: {btn_font_size}px; "
                f"  font-weight: 600; "
                f"  font-family: '{font_family}', sans-serif; "
                f"}} "
                f"QPushButton#conj_pill_btn:hover {{ "
                f"  background: rgba(167, 139, 250, 0.32); "
                f"  border-color: #A78BFA; "
                f"  color: #FFFFFF; "
                f"}}"
            )
            clean_kr = re.sub(r"\(.*?\)|（.*?）", "", kr).strip()
            btn.clicked.connect(lambda checked, t=clean_kr: self.speak_requested.emit(t))
            self._conj_capsules_layout.addWidget(btn)

        self._conj_capsules_widget.setVisible(self._conjugation_expanded)
        self._conj_toggle_btn.setText("▲ 收起" if self._conjugation_expanded else "▼ 展开")

    def _toggle_hanja_family(self):
        """点击词根拆解胶囊展开/收起同根衍生词家族"""
        if not self._hanja_family_data:
            return
        self._hanja_family_expanded = not self._hanja_family_expanded
        self._hanja_family_widget.setVisible(self._hanja_family_expanded)
        self._update_hanja_header_text()

    def _update_hanja_header_text(self):
        """更新词根胶囊标题与指示箭头"""
        breakdown = getattr(self, "_current_hanja_breakdown", "")
        if not breakdown:
            return
        if self._hanja_family_data:
            arrow = "▴ 收起拓展" if self._hanja_family_expanded else "▾ 衍生拓展"
            self._hanja_header_btn.setText(f"🌱 词根拆解: {breakdown}   {arrow}")
        else:
            self._hanja_header_btn.setText(f"🌱 词根拆解: {breakdown}")

    def _build_hanja_family_ui(self, families: list):
        """动态构建同根衍生词流式标签卡片"""
        # 清空现有子控件
        while self._hanja_family_layout.count():
            item = self._hanja_family_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        scale = getattr(self, "_font_scale", 1.0)
        badge_font_size = max(10, int(11 * scale))

        for fam in families:
            root_kr = fam.get("root_kr", "")
            root_cn = fam.get("root_cn", "")
            words = fam.get("words", [])
            if not words:
                continue

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(6)

            # 字根标签（如 • 교(交): ）
            root_lbl = QLabel(f"• {root_kr}({root_cn}):")
            root_lbl.setStyleSheet(
                f"QLabel {{ color: #FCD34D; font-size: {badge_font_size}px; font-weight: 700; }}"
            )
            row_layout.addWidget(root_lbl)

            # 衍生词药丸按钮
            for w_info in words:
                w_kr = w_info.get("korean", "")
                w_hj = w_info.get("hanja", "")
                w_cn = w_info.get("chinese", "")
                btn_text = f"{w_kr} {w_hj}".strip()

                pill_btn = QPushButton(btn_text)
                pill_btn.setObjectName("hanja_pill_btn")
                pill_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                pill_btn.setToolTip(f"🔊 点击发音: {w_kr}\n释义: {w_info.get('full_meaning', w_cn)}")
                pill_btn.setStyleSheet(
                    f"QPushButton {{ background: rgba(30, 32, 40, 0.85); color: #E2E8F0; "
                    f"border: 1px solid rgba(255, 255, 255, 0.20); border-radius: 8px; "
                    f"padding: 2px 8px; font-size: {badge_font_size}px; font-weight: 600; }}"
                    f"QPushButton:hover {{ background: rgba(59, 130, 246, 0.35); color: #93C5FD; border-color: #60A5FA; }}"
                )
                pill_btn.clicked.connect(lambda checked, kr=w_kr: self.speak_requested.emit(kr))
                row_layout.addWidget(pill_btn)

            row_layout.addStretch()
            self._hanja_family_layout.addWidget(row_widget)

    def _apply_hanja_box_style(self):
        """应用词根卡片与折叠按钮样式"""
        scale = getattr(self, "_font_scale", 1.0)
        btn_font_size = max(11, int(12 * scale))
        btn_radius = max(8, int(10 * scale))

        self._hanja_box.setStyleSheet(
            f"QWidget#hanja_box {{ "
            f"  background: rgba(18, 20, 26, 0.72); "
            f"  border: 1px solid rgba(255, 255, 255, 0.16); "
            f"  border-radius: {btn_radius + 2}px; "
            f"}}"
        )
        self._hanja_header_btn.setStyleSheet(
            f"QPushButton#hanja_header_btn {{ "
            f"  background: rgba(30, 34, 44, 0.80); "
            f"  color: #F1F5F9; "
            f"  border: 1px solid rgba(255, 255, 255, 0.22); "
            f"  border-radius: {btn_radius}px; "
            f"  padding: 4px 10px; "
            f"  font-size: {btn_font_size}px; "
            f"  font-weight: 600; "
            f"  text-align: center; "
            f"}} "
            f"QPushButton#hanja_header_btn:hover {{ "
            f"  background: rgba(59, 130, 246, 0.28); "
            f"  color: #93C5FD; "
            f"  border-color: rgba(147, 197, 253, 0.45); "
            f"}}"
        )

    def _apply_origin_badge_style(self, word_type: str):
        """根据词源类型应用高对比度半透明深色磨砂胶囊样式"""
        scale = getattr(self, "_font_scale", 1.0)
        badge_font = int(11 * scale)
        badge_pad_v = max(2, int(2 * scale))
        badge_pad_h = max(6, int(8 * scale))
        badge_radius = max(8, int(10 * scale))
        badge_base = f"border-radius: {badge_radius}px; padding: {badge_pad_v}px {badge_pad_h}px; font-size: {badge_font}px; font-weight: 600;"

        if word_type == "hanja":
            style = "background: rgba(18, 22, 30, 0.75); color: #9EC5E8; border: 1px solid rgba(158, 197, 232, 0.35);"
        elif word_type == "loanword":
            style = "background: rgba(26, 20, 32, 0.75); color: #D8BCE8; border: 1px solid rgba(216, 188, 232, 0.35);"
        else:
            style = "background: rgba(18, 20, 26, 0.75); color: #E0E6ED; border: 1px solid rgba(255, 255, 255, 0.20);"
        self._origin_badge.setStyleSheet(f"QLabel {{ {style} {badge_base} }}")

    def _apply_mutation_badge_style(self):
        """应用 Instagram 极简低饱和度浅紫/粉蓝音变药丸样式"""
        scale = getattr(self, "_font_scale", 1.0)
        font_sz = max(10, int(11 * scale))
        pad_v = max(2, int(2 * scale))
        pad_h = max(6, int(8 * scale))
        radius = max(8, int(10 * scale))

        self._mutation_badge.setStyleSheet(
            f"QPushButton#mutation_badge {{ "
            f"  background: rgba(142, 68, 173, 0.22); "
            f"  border: 1px solid rgba(168, 85, 247, 0.45); "
            f"  color: #E9D5FF; "
            f"  border-radius: {radius}px; "
            f"  padding: {pad_v}px {pad_h}px; "
            f"  font-size: {font_sz}px; "
            f"  font-weight: 700; "
            f"}} "
            f"QPushButton#mutation_badge:hover {{ "
            f"  background: rgba(168, 85, 247, 0.38); "
            f"  border-color: #C084FC; "
            f"  color: #FFFFFF; "
            f"}}"
        )

    def _show_mutation_info(self):
        """点击音变标签展示简明扼要的规则解释与实际读音说明"""
        if not self._word:
            return
        m_info = self._word.get("_mutation")
        if not m_info:
            m_info = analyze_pronunciation(self._word.get("korean", ""))

        kr_text = self._word.get("korean", "")
        clean_kr = re.sub(r"\(.*?\)|（.*?）", "", kr_text).strip()

        if not self._phonetic_tooltip:
            self._phonetic_tooltip = PhoneticTooltip(self)
        self._phonetic_tooltip.show_mutation(clean_kr if clean_kr else kr_text, m_info, self._mutation_badge)

    def _on_speak(self):
        """仅在用户明确手动点击右上角 🔊 按钮时触发发音"""
        if self._word:
            text = self._word.get("korean", "")
            self.speak_requested.emit(text)

    def on_speak_started(self, text: str = ""):
        """开始播放时的视觉高亮反馈"""
        accent = COLORS["dark_accent"] if self._theme == "dark" else COLORS["light_accent"]
        self._speak_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(82, 183, 136, 0.35); color: #52B788; border: 1.5px solid #52B788; border-radius: 16px; }}"
        )

    def on_speak_finished(self):
        """播放结束恢复默认样式"""
        self._speak_btn.setStyleSheet(
            "QPushButton { background: rgba(20, 20, 26, 0.75); color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 16px; font-size: 14px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.22); border-color: rgba(255, 255, 255, 0.40); }"
        )

    # ─────────────────────────────────────────────────────────
    # 事件过滤器：单击即时翻面 与 拖拽移动窗口 互斥判定
    # ─────────────────────────────────────────────────────────

    def _install_click_filters(self):
        """安装事件过滤器，使点击卡片任意区域均能灵敏触发单击翻面或拖拽"""
        widgets = [
            self, self._front, self._back, self._back_scroll,
            self._korean_label, self._pron_label, self._hint_label,
            self._chinese_label, self._example_box, self._example_korean, self._example_chinese,
            self._quote_box, self._quote_korean, self._quote_chinese, self._quote_source_label,
            self._collocation_box, self._pos_label, self._origin_badge,
            self._collocation_badge, self._back_meta_widget, self._sep,
            self._spelling_container, self._spelling_prompt_label,
            self._spelling_feedback, self._spelling_hint_label
        ]
        for w in widgets:
            w.installEventFilter(self)

    def eventFilter(self, obj, event):
        # 🔊 发音按钮、拼写输入框、词根折叠按钮及衍生词药丸保持独立点击行为，绝不被卡片翻转/拖拽逻辑劫持
        if obj in (self._speak_btn, self._spell_speak_btn, self._spelling_input, self._hanja_header_btn, self._hanja_box, self._hanja_family_widget) or isinstance(obj, QPushButton):
            return super().eventFilter(obj, event)

        if self._is_spelling_mode:
            # 拼写测验模式下不触发正反面翻转
            return super().eventFilter(obj, event)

        etype = event.type()
        if etype == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._press_pos = event.globalPosition().toPoint()
                win = self.window()
                if win:
                    self._drag_start_window_pos = win.pos()
                self._is_dragging = False
                return True

        elif etype == QEvent.Type.MouseMove:
            if (event.buttons() & Qt.MouseButton.LeftButton) and self._press_pos is not None:
                delta = event.globalPosition().toPoint() - self._press_pos
                if not self._is_dragging and delta.manhattanLength() >= 5:
                    self._is_dragging = True
                if self._is_dragging:
                    win = self.window()
                    if win and self._drag_start_window_pos is not None:
                        win.move(self._drag_start_window_pos + delta)
                return True

        elif etype == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
                delta = event.globalPosition().toPoint() - self._press_pos
                was_dragging = self._is_dragging or (delta.manhattanLength() >= 5)
                self._press_pos = None
                self._drag_start_window_pos = None
                self._is_dragging = False
                if not was_dragging:
                    # 单击判定成功（位移 < 5px）：瞬间翻面，完全静音！
                    self.flip()
                return True

        return super().eventFilter(obj, event)

    # ─────────────────────────────────────────────────────────
    # 样式、字号缩放与主题
    # ─────────────────────────────────────────────────────────

    def set_font_scale(self, scale: float):
        """设置卡片全局文字大小缩放比例 (如 1.0, 1.2, 1.4, 1.6)"""
        self._font_scale = max(0.6, min(1.6, scale))
        self.apply_theme(self._theme)

    def set_korean_font(self, font_family: str):
        """动态设置韩文大字显示字体"""
        self._korean_font_family = font_family
        self._korean_font = font_family
        self.apply_theme(self._theme)

    def apply_theme(self, theme: str):
        self._theme = theme
        from config.settings import THEME_CONFIGS, COLORS
        if theme == "dark":
            theme = "seoul_night"
        elif theme == "light":
            theme = "cream_latte"

        cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["seoul_night"])
        is_dark = cfg.get("is_dark", True)
        text_pri = cfg.get("text_primary", "#FFFFFF")
        text_sec = cfg.get("text_secondary", "#A0A5B5")
        korean_c = text_pri
        accent = cfg.get("accent", "#2ECC71")
        colloc_style = f"background: {accent}22; color: {accent}; border: 1px solid {accent}55;"

        scale = getattr(self, "_font_scale", 1.0)
        font_family = getattr(self, "_korean_font_family", "Malgun Gothic")

        # 动态多字长阶梯字号计算 (1~2字: 35px, 3~4字: 28px, 5字+: 23px)
        raw_kr = self._word.get("korean", "") if self._word else ""
        clean_kr_for_len = re.sub(r"[\s\(\)（）\-_~·/]", "", raw_kr)
        kr_len = len(clean_kr_for_len) if clean_kr_for_len else 2
        if kr_len <= 2:
            base_kr_size = 35
        elif kr_len <= 4:
            base_kr_size = 28
        else:
            base_kr_size = 23

        korean_size = int(base_kr_size * scale)
        chinese_size = int(FONT_CHINESE_SIZE * scale)
        example_size = int(FONT_EXAMPLE_SIZE * scale)
        pos_size = int(FONT_POS_SIZE * scale)
        pron_size = max(11, int(13 * scale))
        badge_size = max(10, int(11 * scale))
        hint_size = max(10, int(11 * scale))
        badge_radius = max(8, int(10 * scale))
        badge_pad_v = max(2, int(2 * scale))
        badge_pad_h = max(6, int(8 * scale))

        # 1. 词性标签（高对比深色磨砂药丸）
        pos_bg, pos_text_color = (
            POS_COLORS.get(self._word.get("pos", ""), POS_COLORS["default"])
            if self._word else POS_COLORS["default"]
        )
        pos_bg_style = f"background: rgba(18, 20, 26, 0.75); color: {pos_text_color}; border: 1px solid {pos_bg}66;"

        self._pos_label.setFixedHeight(max(22, int(22 * scale)))
        self._pos_label.setStyleSheet(
            f"QLabel {{ {pos_bg_style} border-radius: {badge_radius}px; "
            f"padding: 1px {int(10 * scale)}px; font-size: {pos_size}px; font-weight: 600; }}"
        )

        # 1.5 所属单元与课程溯源标签（Instagram 极简半透磨砂蓝药丸）
        self._source_badge.setFixedHeight(max(22, int(22 * scale)))
        self._source_badge.setStyleSheet(
            f"QLabel#source_badge {{ "
            f"  background: rgba(18, 20, 26, 0.75); "
            f"  color: #93C5FD; "
            f"  border: 1px solid rgba(147, 197, 253, 0.38); "
            f"  border-radius: {badge_radius}px; "
            f"  padding: 1px {int(8 * scale)}px; "
            f"  font-size: {badge_size}px; "
            f"  font-weight: 600; "
            f"}}"
        )

        # 2. 韩文大字（纯白高亮，配立体外发光）
        self._korean_label.setStyleSheet(
            f"QLabel {{ color: #FFFFFF; font-size: {korean_size}px; "
            f"font-weight: 700; letter-spacing: 2px; font-family: '{font_family}', 'Malgun Gothic', sans-serif; "
            f"padding: {int(6 * scale)}px 4px {int(8 * scale)}px 4px; line-height: 1.4; }}"
        )

        # 3. 实际读音音标（高对比浅金白，告别发灰看不清）
        self._pron_label.setStyleSheet(
            f"QLabel {{ color: #F1F5F9; font-size: {pron_size}px; font-style: italic; font-weight: 500; "
            f"font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; letter-spacing: 0.5px; }}"
        )

        # 4. 点击提示（精致高对比胶囊药丸，彻底去除 opacity 削弱）
        self._hint_label.setStyleSheet(
            f"QLabel#hint_label {{ background: rgba(18, 20, 26, 0.65); color: #E2E8F0; "
            f"border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 12px; "
            f"padding: 2px 12px; font-size: {hint_size}px; font-weight: 500; }}"
        )

        # 5. 独立发音按钮（Instagram 极简半透胶囊）
        self._speak_btn.setStyleSheet(
            "QPushButton { background: rgba(20, 20, 26, 0.75); color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 16px; font-size: 14px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.22); border-color: rgba(255, 255, 255, 0.40); }"
        )

        # 6. 中文释义（纯白高亮大字）
        self._chinese_label.setStyleSheet(
            f"QLabel {{ color: #FFFFFF; font-size: {chinese_size}px; "
            f"font-weight: 700; }}"
        )

        # 7. 搭配胶囊与反义词药丸
        badge_base = f"border-radius: {badge_radius}px; padding: {badge_pad_v}px {badge_pad_h}px; font-size: {badge_size}px; font-weight: 500;"
        colloc_style = "background: rgba(18, 24, 20, 0.75); color: #A7F3D0; border: 1px solid rgba(167, 243, 208, 0.35);"
        self._collocation_badge.setStyleSheet(f"QLabel {{ {colloc_style} {badge_base} }}")

        # 反义词交互胶囊样式（低饱和翡翠/薄荷绿发光）
        self._antonym_btn.setStyleSheet(
            f"QPushButton#antonym_btn {{ background: rgba(16, 185, 129, 0.18); color: #6EE7B7; "
            f"border: 1px solid rgba(110, 231, 183, 0.40); border-radius: {badge_radius}px; "
            f"padding: {badge_pad_v}px {badge_pad_h + 2}px; font-size: {badge_size}px; font-weight: 700; }} "
            f"QPushButton#antonym_btn:hover {{ background: rgba(16, 185, 129, 0.35); color: #FFFFFF; border-color: #10B981; }}"
        )

        # 易混近义词辨析小药丸样式
        self._nuance_btn.setStyleSheet(
            f"QPushButton#nuance_btn {{ background: rgba(56, 189, 248, 0.16); color: #38BDF8; "
            f"border: 1px solid rgba(56, 189, 248, 0.40); border-radius: {badge_radius}px; "
            f"padding: {badge_pad_v}px {badge_pad_h + 2}px; font-size: {badge_size}px; font-weight: 700; }} "
            f"QPushButton#nuance_btn:hover {{ background: rgba(56, 189, 248, 0.30); color: #FFFFFF; border-color: #38BDF8; }}"
        )

        # 语境辨析展开卡片样式
        self._nuance_box.setStyleSheet(
            "QWidget#nuance_box { background: rgba(18, 26, 36, 0.85); "
            "border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 10px; }"
        )

        # 常用地道搭配卡片样式
        self._collocation_box.setStyleSheet(
            "QWidget#collocation_box { background: rgba(20, 26, 24, 0.75); "
            "border: 1px solid rgba(110, 231, 183, 0.28); border-radius: 10px; }"
        )
        self._colloc_title_label.setStyleSheet(
            "QLabel#colloc_title_label { color: #6EE7B7; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }"
        )

        # 常用活用变形卡片样式
        self._conjugation_box.setStyleSheet(
            "QWidget#conjugation_box { background: rgba(24, 20, 32, 0.78); "
            "border: 1px solid rgba(167, 139, 250, 0.32); border-radius: 10px; }"
        )
        self._conj_title_label.setStyleSheet(
            "QLabel#conj_title_label { color: #A78BFA; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }"
        )

        # 8. 词源胶囊与词根卡片
        if self._word:
            w_type = self._word.get("word_type", "")
            if w_type in ["hanja", "loanword"]:
                self._apply_origin_badge_style(w_type)
        self._apply_hanja_box_style()

        # 8.5 背面极简超薄滚动条与容器 QSS
        self._back_scroll.setStyleSheet(
            "QScrollArea#back_scroll { background: transparent; border: none; }"
            "QScrollArea#back_scroll > QWidget > QWidget { background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 4px; margin: 2px 0 2px 0; }"
            "QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.25); min-height: 20px; border-radius: 2px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.45); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )

        # 9. 双语例句容器与文字（高对比深色磨砂底衬，彻底消灭浅色背景下的重影发虚）
        self._example_box.setStyleSheet(
            "QWidget#example_box { background: rgba(20, 20, 26, 0.75); "
            "border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 10px; }"
        )
        self._example_title_label.setStyleSheet(
            "QLabel#example_title_label { color: #94A3B8; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }"
        )
        self._example_speak_btn.setStyleSheet(
            "QPushButton#example_speak_btn { background: rgba(30, 32, 40, 0.75); color: #93C5FD; "
            "border: 1px solid rgba(147, 197, 253, 0.35); border-radius: 10px; font-size: 10px; font-weight: 600; padding: 2px 8px; }"
            "QPushButton#example_speak_btn:hover { background: rgba(147, 197, 253, 0.20); border-color: #93C5FD; }"
        )
        self._example_korean.setStyleSheet(
            f"QLabel {{ color: #FFFFFF; font-size: {example_size}px; "
            f"font-weight: 600; line-height: 1.5; font-family: '{font_family}', 'Malgun Gothic', sans-serif; }}"
        )
        self._example_chinese.setStyleSheet(
            f"QLabel {{ color: #CBD5E1; font-size: {max(11, example_size - 1)}px; font-weight: 400; line-height: 1.3; }}"
        )

        # 9.5 🎵 经典歌词 / 影视台词微语境卡片（Instagram Story 质感粉紫晶莹磨砂）
        quote_title_color = "#F472B6" if (self._word and self._word.get("quote_type") == "song") else "#A78BFA"
        self._quote_box.setStyleSheet(
            "QWidget#quote_box { background: rgba(30, 20, 38, 0.78); "
            "border: 1px solid rgba(244, 114, 182, 0.32); border-radius: 12px; }"
        )
        self._quote_title_label.setStyleSheet(
            f"QLabel#quote_title_label {{ color: {quote_title_color}; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }}"
        )
        self._quote_speak_btn.setStyleSheet(
            "QPushButton#quote_speak_btn { background: rgba(38, 24, 45, 0.75); color: #FBCFE8; "
            "border: 1px solid rgba(244, 114, 182, 0.38); border-radius: 10px; font-size: 10px; font-weight: 600; padding: 2px 8px; }"
            "QPushButton#quote_speak_btn:hover { background: rgba(244, 114, 182, 0.25); border-color: #F472B6; }"
        )
        self._quote_korean.setStyleSheet(
            f"QLabel {{ color: #FDF2F8; font-size: {example_size}px; font-style: italic; "
            f"font-weight: 600; line-height: 1.5; font-family: '{font_family}', 'Malgun Gothic', sans-serif; }}"
        )
        self._quote_chinese.setStyleSheet(
            f"QLabel {{ color: #E2E8F0; font-size: {max(11, example_size - 1)}px; font-weight: 400; line-height: 1.3; }}"
        )
        self._quote_source_label.setStyleSheet(
            "QLabel#quote_source_label { color: #F9A8D4; font-size: 10px; font-weight: 600; padding-top: 2px; }"
        )

        self._sep.setStyleSheet("background: rgba(255, 255, 255, 0.15); max-height: 1px;")

        # 10. 拼写测验模式控件样式
        self._reset_spelling_input_style()
        self._spelling_hint_label.setStyleSheet(
            f"QLabel {{ color: #E2E8F0; font-size: {hint_size}px; }}"
        )
        self._spell_speak_btn.setStyleSheet(
            "QPushButton { background: rgba(20, 20, 26, 0.75); color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 15px; font-size: 14px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.22); }"
        )

        if self._word:
            if self._is_spelling_mode:
                self._update_spelling_display()
            else:
                self._update_display()

    def set_compact(self, compact: bool):
        """极简模式：隐藏例句区域与提示"""
        self._compact = compact
        self._hint_label.setVisible(not compact)
        if compact:
            self._pron_label.hide()
            self._back_meta_widget.hide()
        else:
            if self._word and self._word.get("pronunciation"):
                self._pron_label.show()
            if self._word:
                has_meta = bool(self._origin_badge.isVisible() or get_collocation_hint(self._word))
                self._back_meta_widget.setVisible(has_meta)

        if compact and self._is_back:
            self._example_korean.hide()
            self._example_chinese.hide()
            self._sep.hide()
        elif not compact and self._word:
            examples = self._word.get("examples", [])
            vis = bool(examples)
            self._example_korean.setVisible(vis)
            self._example_chinese.setVisible(vis)
            self._sep.setVisible(vis)
