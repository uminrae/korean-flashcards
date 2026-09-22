# -*- coding: utf-8 -*-
"""
copybook_generator.py
---------------------
「未来的韩语卡片」- 高清手写字帖生成引擎 (基于 Pillow 纯净无外部依赖渲染)
1. 生成标准 A4 @ 300 DPI (2480 x 3508) 印刷级高保真字帖
2. 支持三种字格排版格式：田字格 (tian)、米字格 (mi)、极简手账横线 (lines)
3. 打印对比度优化：黑白打印适度清晰、不晕染、浅灰描红与虚线辅助
4. 一键导出可打印多页 PDF 与平板临摹超清 PNG
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


# A4 页面标准参数 (300 DPI)
PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508

MARGIN_LEFT = 140
MARGIN_RIGHT = 140
MARGIN_TOP = 140
MARGIN_BOTTOM = 120

WORDS_PER_PAGE = 7  # 每页 7 个词，保证字格与释义空间极其舒适宽松


class CopybookGenerator:
    """A4 高清手写字帖生成器"""

    def __init__(self, font_family: Optional[str] = None):
        self._font_family = font_family
        self._font_cache = {}
        self._find_available_fonts()

    def _find_available_fonts(self):
        """寻找可用的中韩文字体文件"""
        from utils.path_helper import get_data_path

        candidates = [
            get_data_path("data/fonts/minqeoleu.ttf"),
            "assets/fonts/minqeoleu.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/arial.ttf",
        ]

        self._korean_font_path = None
        self._chinese_font_path = None

        for path in candidates:
            if os.path.exists(path):
                if not self._korean_font_path and ("minqeoleu" in path.lower() or "malgun" in path.lower()):
                    self._korean_font_path = path
                if not self._chinese_font_path and ("msyh" in path.lower() or "sim" in path.lower() or "malgun" in path.lower()):
                    self._chinese_font_path = path

        # 兜底
        if not self._korean_font_path:
            for path in candidates:
                if os.path.exists(path):
                    self._korean_font_path = path
                    break

        if not self._chinese_font_path:
            self._chinese_font_path = self._korean_font_path

    def _get_font(self, size: int, is_korean: bool = False, is_bold: bool = False) -> ImageFont.ImageFont:
        """安全加载指定字号的字体"""
        key = (size, is_korean, is_bold)
        if key in self._font_cache:
            return self._font_cache[key]

        path = self._korean_font_path if is_korean else self._chinese_font_path
        if path and os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                self._font_cache[key] = font
                return font
            except Exception:
                pass

        font = ImageFont.load_default()
        self._font_cache[key] = font
        return font

    def generate(
        self,
        words: List[Dict],
        output_path: str,
        title: str = "未来的韩语卡片 · 手写临摹字帖",
        subtitle: str = "DAILY KOREAN HANDWRITING PRACTICE",
        grid_style: str = "tian"
    ) -> List[str]:
        """
        根据给定的词汇列表生成高清 A4 字帖 (PDF 或 PNG)
        grid_style: 'tian' (田字格), 'mi' (米字格), 'lines' (极简手账横线)
        """
        if not words:
            return []

        # 过滤与标准化词汇列表
        clean_words = []
        for w in words:
            if not w or not isinstance(w, dict):
                continue
            kr = w.get("korean", "").strip()
            if not kr:
                continue
            clean_words.append(w)

        if not clean_words:
            return []

        # 分页计算
        pages_data = [
            clean_words[i:i + WORDS_PER_PAGE]
            for i in range(0, len(clean_words), WORDS_PER_PAGE)
        ]
        total_pages = len(pages_data)
        date_str = datetime.now().strftime("%Y.%m.%d")

        rendered_images: List[Image.Image] = []
        for p_idx, p_words in enumerate(pages_data, start=1):
            page_img = self._render_page(
                page_words=p_words,
                page_num=p_idx,
                total_pages=total_pages,
                title=title,
                subtitle=subtitle,
                date_str=date_str,
                grid_style=grid_style
            )
            rendered_images.append(page_img)

        # 确定导出格式与保存路径
        ext = os.path.splitext(output_path)[1].lower()
        output_files = []

        if ext == ".pdf":
            # 导出为完整多页 PDF (300 DPI 印刷级参数)
            if rendered_images:
                first_img = rendered_images[0]
                other_imgs = rendered_images[1:] if len(rendered_images) > 1 else []
                first_img.save(
                    output_path,
                    "PDF",
                    resolution=300.0,
                    save_all=True,
                    append_images=other_imgs
                )
                output_files.append(output_path)
        else:
            # 导出为超清单页/多页 PNG
            base_dir = os.path.dirname(output_path)
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            for idx, img in enumerate(rendered_images, start=1):
                if total_pages == 1:
                    p_path = output_path if ext == ".png" else os.path.join(base_dir, f"{base_name}.png")
                else:
                    p_path = os.path.join(base_dir, f"{base_name}_page_{idx:02d}.png")
                img.save(p_path, "PNG", dpi=(300, 300))
                output_files.append(p_path)

        return output_files

    def _draw_dashed_line(
        self,
        draw: ImageDraw.ImageDraw,
        pt1: Tuple[int, int],
        pt2: Tuple[int, int],
        color: str = "#CBD5E1",
        dash_len: int = 6,
        gap_len: int = 5,
        width: int = 2
    ):
        """在画布上绘制细腻的虚线"""
        x1, y1 = pt1
        x2, y2 = pt2
        dx = x2 - x1
        dy = y2 - y1
        dist = (dx * dx + dy * dy) ** 0.5
        if dist == 0:
            return

        vx = dx / dist
        vy = dy / dist
        curr = 0
        while curr < dist:
            end = min(curr + dash_len, dist)
            sx = x1 + vx * curr
            sy = y1 + vy * curr
            ex = x1 + vx * end
            ey = y1 + vy * end
            draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
            curr += dash_len + gap_len

    def _draw_grid_cell(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, style: str = "tian"):
        """
        绘制单个字格：
        - tian (田字格): 外实线 + 内十字虚线
        - mi (米字格): 外实线 + 内十字虚线 + 对角线虚线
        - lines (极简手账横线): 顶部/底部实线 + 居中基准虚线
        """
        mid_x = x + size // 2
        mid_y = y + size // 2

        if style == "mi":
            # 1. 对角线虚线 (极浅灰)
            self._draw_dashed_line(draw, (x, y), (x + size, y + size), color="#E2E8F0", dash_len=4, gap_len=6, width=1)
            self._draw_dashed_line(draw, (x + size, y), (x, y + size), color="#E2E8F0", dash_len=4, gap_len=6, width=1)
            # 2. 十字中线虚线 (标准灰)
            self._draw_dashed_line(draw, (x, mid_y), (x + size, mid_y), color="#CBD5E1", dash_len=6, gap_len=5, width=2)
            self._draw_dashed_line(draw, (mid_x, y), (mid_x, y + size), color="#CBD5E1", dash_len=6, gap_len=5, width=2)
            # 3. 外边框 (清晰实线，对比度强化)
            draw.rectangle([x, y, x + size, y + size], outline="#64748B", width=3)

        elif style == "lines":
            # 极简手账横线：顶部与底部横线 + 居中手写基准虚线
            draw.line([(x, y), (x + size, y)], fill="#64748B", width=2)
            draw.line([(x, y + size), (x + size, y + size)], fill="#64748B", width=2)
            self._draw_dashed_line(draw, (x, mid_y), (x + size, mid_y), color="#CBD5E1", dash_len=6, gap_len=5, width=2)

        else:
            # 默认：tian 田字格
            # 1. 十字中线虚线 (标准灰)
            self._draw_dashed_line(draw, (x, mid_y), (x + size, mid_y), color="#CBD5E1", dash_len=6, gap_len=5, width=2)
            self._draw_dashed_line(draw, (mid_x, y), (mid_x, y + size), color="#CBD5E1", dash_len=6, gap_len=5, width=2)
            # 2. 外边框 (清晰实线)
            draw.rectangle([x, y, x + size, y + size], outline="#64748B", width=3)

    def _render_page(
        self,
        page_words: List[Dict],
        page_num: int,
        total_pages: int,
        title: str,
        subtitle: str,
        date_str: str,
        grid_style: str = "tian"
    ) -> Image.Image:
        """渲染单页 A4 (300 DPI) 字帖"""
        img = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "#FFFFFF")
        draw = ImageDraw.Draw(img)

        # ── 1. 顶部 Header (手账风打卡栏) ──
        title_font = self._get_font(48, is_bold=True)
        sub_font = self._get_font(24)
        date_font = self._get_font(22)

        draw.text((MARGIN_LEFT, MARGIN_TOP), title, font=title_font, fill="#0F172A")
        
        style_desc = "【田字格】" if grid_style == "tian" else ("【米字格】" if grid_style == "mi" else "【极简手账横线】")
        draw.text((MARGIN_LEFT, MARGIN_TOP + 64), f"{subtitle} · {style_desc}", font=sub_font, fill="#475569")

        # 右侧打卡信息卡片
        card_w = 540
        card_h = 96
        card_x = PAGE_WIDTH - MARGIN_RIGHT - card_w
        card_y = MARGIN_TOP + 4

        draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=16, fill="#F8FAFC", outline="#CBD5E1", width=2)
        draw.text((card_x + 24, card_y + 16), f"📅 DATE:  {date_str}", font=date_font, fill="#334155")
        draw.text((card_x + 24, card_y + 54), "⏰ TIME:  __:__    🎯 SCORE:  [ ★ ★ ★ ]", font=date_font, fill="#334155")

        # 顶部分隔线
        sep_y = MARGIN_TOP + 120
        draw.line([(MARGIN_LEFT, sep_y), (PAGE_WIDTH - MARGIN_RIGHT, sep_y)], fill="#94A3B8", width=3)

        # ── 2. 主体生词行绘制 ──
        content_top = sep_y + 36
        row_height = 420
        grid_size = 148
        grid_spacing = 14
        num_grids = 6

        font_korean_trace = self._get_font(92, is_korean=True)
        font_word_title = self._get_font(34, is_korean=True, is_bold=True)
        font_pos = self._get_font(20)
        font_meaning = self._get_font(26)
        font_example = self._get_font(22)
        font_num = self._get_font(24, is_bold=True)

        for row_idx, w in enumerate(page_words):
            y_base = content_top + row_idx * row_height
            if y_base + row_height > PAGE_HEIGHT - MARGIN_BOTTOM:
                break

            # 序号徽章
            seq_num = f"{((page_num - 1) * WORDS_PER_PAGE + row_idx + 1):02d}"
            badge_w, badge_h = 56, 36
            draw.rounded_rectangle([MARGIN_LEFT, y_base + 6, MARGIN_LEFT + badge_w, y_base + 6 + badge_h], radius=8, fill="#F1F5F9", outline="#94A3B8", width=2)
            draw.text((MARGIN_LEFT + 12, y_base + 10), seq_num, font=font_num, fill="#334155")

            # 单词信息栏
            korean_raw = w.get("korean", "")
            clean_kr = re.sub(r"\(.*?\)|（.*?）", "", korean_raw).strip()
            clean_kr = clean_kr if clean_kr else korean_raw

            pron = w.get("pronunciation", "").strip()
            pos = w.get("pos", "").strip()
            meaning = w.get("chinese", w.get("meaning", "")).strip()

            info_x = MARGIN_LEFT + badge_w + 18
            draw.text((info_x, y_base + 4), clean_kr, font=font_word_title, fill="#0F172A")

            try:
                kr_bbox = font_word_title.getbbox(clean_kr)
                kr_width = kr_bbox[2] - kr_bbox[0]
            except Exception:
                kr_width = len(clean_kr) * 32

            curr_info_x = info_x + kr_width + 18

            if pron:
                draw.text((curr_info_x, y_base + 12), f"/{pron}/", font=font_pos, fill="#64748B")
                try:
                    p_bbox = font_pos.getbbox(f"/{pron}/")
                    curr_info_x += (p_bbox[2] - p_bbox[0]) + 16
                except Exception:
                    curr_info_x += len(pron) * 16 + 16

            if pos:
                draw.rounded_rectangle([curr_info_x, y_base + 8, curr_info_x + 60, y_base + 34], radius=6, fill="#E0F2FE", outline="#7DD3FC", width=1)
                draw.text((curr_info_x + 10, y_base + 10), pos[:2], font=font_pos, fill="#0369A1")
                curr_info_x += 76

            if meaning:
                draw.text((curr_info_x, y_base + 8), meaning, font=font_meaning, fill="#334155")

            # 绘制字格与预印描红字
            grid_y = y_base + 56
            kr_chars = [c for c in clean_kr if not c.isspace()]
            ex_kr = w.get("example_kr", "") or w.get("example_korean", "")
            ex_cn = w.get("example_cn", "") or w.get("example_chinese", "")

            for g_i in range(num_grids):
                gx = MARGIN_LEFT + g_i * (grid_size + grid_spacing)
                self._draw_grid_cell(draw, gx, grid_y, grid_size, style=grid_style)

                char_to_draw = ""
                char_color = "#94A3B8"

                if g_i < len(kr_chars):
                    char_to_draw = kr_chars[g_i]
                    char_color = "#94A3B8"
                elif len(kr_chars) <= 3 and g_i < len(kr_chars) * 2:
                    char_to_draw = kr_chars[g_i - len(kr_chars)]
                    char_color = "#CBD5E1"

                if char_to_draw:
                    try:
                        bbox = font_korean_trace.getbbox(char_to_draw)
                        cw = bbox[2] - bbox[0]
                        ch = bbox[3] - bbox[1]
                        cx = gx + (grid_size - cw) // 2 - bbox[0]
                        cy = grid_y + (grid_size - ch) // 2 - bbox[1]
                        draw.text((cx, cy), char_to_draw, font=font_korean_trace, fill=char_color)
                    except Exception:
                        draw.text((gx + 25, grid_y + 20), char_to_draw, font=font_korean_trace, fill=char_color)

            # 字格右侧的随堂默写卡片
            memo_x = MARGIN_LEFT + num_grids * (grid_size + grid_spacing) + 24
            memo_w = PAGE_WIDTH - MARGIN_RIGHT - memo_x
            memo_h = grid_size

            draw.rounded_rectangle([memo_x, grid_y, memo_x + memo_w, grid_y + memo_h], radius=12, fill="#F8FAFC", outline="#CBD5E1", width=2)

            if ex_kr:
                clean_ex_kr = re.sub(r"\(.*?\)|（.*?）", "", ex_kr).strip()
                draw.text((memo_x + 18, grid_y + 14), f"💬 例句: {clean_ex_kr}", font=font_example, fill="#0F172A")
                if ex_cn:
                    draw.text((memo_x + 18, grid_y + 48), f"   对照: {ex_cn}", font=font_example, fill="#475569")
                draw.text((memo_x + 18, grid_y + memo_h - 44), "✍️ 造句/默写: ________________________________________________", font=font_example, fill="#64748B")
            else:
                draw.text((memo_x + 18, grid_y + 24), "✍️ 笔画临摹要点 / 随堂默写笔记:", font=font_example, fill="#475569")
                draw.line([(memo_x + 18, grid_y + 74), (memo_x + memo_w - 20, grid_y + 74)], fill="#CBD5E1", width=2)
                draw.line([(memo_x + 18, grid_y + 114), (memo_x + memo_w - 20, grid_y + 114)], fill="#CBD5E1", width=2)

            if row_idx < len(page_words) - 1:
                row_sep_y = y_base + row_height - 12
                self._draw_dashed_line(draw, (MARGIN_LEFT, row_sep_y), (PAGE_WIDTH - MARGIN_RIGHT, row_sep_y), color="#E2E8F0", dash_len=8, gap_len=8, width=1)

        # ── 3. 底部 Footer ──
        footer_y = PAGE_HEIGHT - MARGIN_BOTTOM
        draw.line([(MARGIN_LEFT, footer_y), (PAGE_WIDTH - MARGIN_RIGHT, footer_y)], fill="#94A3B8", width=2)

        footer_font = self._get_font(20)
        draw.text((MARGIN_LEFT, footer_y + 18), "🌱 매일매일 조금씩 발전하는 나 · 每天进步一点点 ·「未来的韩语卡片」", font=footer_font, fill="#64748B")

        page_str = f"Page {page_num} of {total_pages}"
        try:
            p_bbox = footer_font.getbbox(page_str)
            pw = p_bbox[2] - p_bbox[0]
        except Exception:
            pw = 120
        draw.text((PAGE_WIDTH - MARGIN_RIGHT - pw, footer_y + 18), page_str, font=footer_font, fill="#475569")

        return img
