# config/settings.py
# 全局配置常量

# ─── 窗口设置 ────────────────────────────────────────────────
WINDOW_DEFAULT_WIDTH = 380
WINDOW_DEFAULT_HEIGHT = 300
WINDOW_MIN_WIDTH = 320
WINDOW_MIN_HEIGHT = 220
WINDOW_DEFAULT_X = 100
WINDOW_DEFAULT_Y = 100
WINDOW_DEFAULT_OPACITY = 0.92
WINDOW_BORDER_RADIUS = 18

# ─── TTS 设置 ────────────────────────────────────────────────
TTS_VOICE_PRIMARY = "ko-KR-SunHiNeural"
TTS_VOICE_SECONDARY = "ko-KR-InJoonNeural"
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

# ─── 4 大 Instagram 极简磨砂质感主题预设 ───────────────────────
THEME_CONFIGS = {
    "seoul_night": {
        "id": "seoul_night",
        "name": "首尔夜色 (深黑磨砂)",
        "bg_color": (18, 20, 26),
        "card_bg": "#161922",
        "input_bg": "#1F2330",
        "text_primary": "#FFFFFF",
        "text_secondary": "#94A3B8",
        "accent": "#2ECC71",
        "border": "rgba(255, 255, 255, 0.10)",
        "is_dark": True
    },
    "cream_latte": {
        "id": "cream_latte",
        "name": "奶油拿铁 (极简米白)",
        "bg_color": (245, 245, 248),
        "card_bg": "#FFFFFF",
        "input_bg": "#ECEEF2",
        "text_primary": "#1E293B",
        "text_secondary": "#64748B",
        "accent": "#C79A78",
        "border": "rgba(0, 0, 0, 0.08)",
        "is_dark": False
    },
    "matcha_mint": {
        "id": "matcha_mint",
        "name": "抹茶薄荷 (墨绿翠光)",
        "bg_color": (15, 26, 22),
        "card_bg": "#14221C",
        "input_bg": "#1C2E26",
        "text_primary": "#ECFDF5",
        "text_secondary": "#A7F3D0",
        "accent": "#10B981",
        "border": "rgba(16, 185, 129, 0.22)",
        "is_dark": True
    },
    "night_violet": {
        "id": "night_violet",
        "name": "暗夜紫罗兰 (暗熏紫粉)",
        "bg_color": (24, 18, 34),
        "card_bg": "#1F172C",
        "input_bg": "#2C213E",
        "text_primary": "#FDF4FF",
        "text_secondary": "#E9D5FF",
        "accent": "#E879F9",
        "border": "rgba(232, 121, 249, 0.22)",
        "is_dark": True
    }
}

# ─── 莫兰迪色系调色板 ────────────────────────────────────────
COLORS = {
    # 深色主题
    "dark_bg": "#1A1D24",
    "dark_card": "#22252E",
    "dark_card_back": "#1E222A",
    "dark_text_primary": "#FFFFFF",
    "dark_text_secondary": "#A0A5B5",
    "dark_text_korean": "#FFFFFF",
    "dark_accent": "#2ECC71",      # 首尔夜色薄荷绿
    "dark_accent2": "#FD79A8",
    "dark_border": "rgba(255, 255, 255, 0.14)",
    "dark_highlight": "#27AE60",

    # 浅色主题
    "light_bg": "#F5F5F7",
    "light_card": "#FFFFFF",
    "light_card_back": "#FAFAF7",
    "light_text_primary": "#2C3E50",
    "light_text_secondary": "#64748B",
    "light_text_korean": "#1E293B",
    "light_accent": "#C79A78",
    "light_accent2": "#8A6E70",
    "light_border": "rgba(0, 0, 0, 0.12)",
    "light_highlight": "#E2E8F0",

    # 通用
    "star_active": "#F1C40F",
    "star_inactive": "#A0A5B5",
    "danger": "#F43F5E",
    "success": "#2ECC71",
}

# ─── 词性颜色映射（支持韩文键 & 中文键）────────────────────────
POS_COLORS = {
    # 韩文词性键
    "명사":    ("#6B8FAB", "#D0E4F0"),
    "동사":    ("#8BAB6B", "#D8EFC0"),
    "형용사":  ("#AB8B6B", "#F0DEC0"),
    "부사":    ("#9B6BAB", "#E8D0F0"),
    "감탄사":  ("#AB6B8B", "#F0D0E0"),
    "대명사":  ("#6BABAB", "#C0EEEE"),
    "표현":    ("#AB9B6B", "#F0E8C0"),
    # 中文词性键（词库标准化格式）
    "名词":   ("#6B8FAB", "#D0E4F0"),
    "动词":   ("#8BAB6B", "#D8EFC0"),
    "形容词": ("#AB8B6B", "#F0DEC0"),
    "副词":   ("#9B6BAB", "#E8D0F0"),
    "感叹词": ("#AB6B8B", "#F0D0E0"),
    "代词":   ("#6BABAB", "#C0EEEE"),
    "表达":   ("#AB9B6B", "#F0E8C0"),
    "default": ("#888888", "#DDDDDD"),
}

# ─── 字体设置 ────────────────────────────────────────────────
FONT_KOREAN_SIZE = 32
FONT_CHINESE_SIZE = 18
FONT_EXAMPLE_SIZE = 13
FONT_POS_SIZE = 11
FONT_SMALL = 11

# ─── 默认快捷键映射 ──────────────────────────────────────────
DEFAULT_SHORTCUTS = {
    "flip": "Space",
    "prev": "Left",
    "next": "Right",
    "audio": "V",
    "mark_mastered": "J",
    "mark_unfamiliar": "K",
}

SHORTCUT_LABELS = {
    "flip": "翻转卡片 (正/反面)",
    "prev": "切换上一个单词",
    "next": "切换下一个单词",
    "audio": "朗读韩语发音",
    "mark_mastered": "标记为掌握 (下一个)",
    "mark_unfamiliar": "标记为不熟 (加入生词本)",
}

# ─── 数据库 ─────────────────────────────────────────────────
DB_FILE = "config/korean_cards.db"

# ─── 音频缓存 ────────────────────────────────────────────────
AUDIO_CACHE_DIR = "audio/cache"
