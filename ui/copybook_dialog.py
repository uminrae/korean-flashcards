# -*- coding: utf-8 -*-
"""
copybook_dialog.py
------------------
Instagram 极简毛玻璃风格手写字帖导出样式配置对话框
支持选择「田字格 / 米字格 / 极简手账横线」与「PDF / PNG」格式
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QFileDialog, QGraphicsDropShadowEffect
)

from config.settings import THEME_CONFIGS


class CopybookExportDialog(QDialog):
    """手写字帖导出排版参数配置弹窗"""

    export_started = pyqtSignal(dict) # 包含 grid_style, file_format, save_path

    def __init__(self, words_count: int = 0, current_theme: str = "seoul_night", parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 420)
        self._words_count = words_count
        self._theme = current_theme

        self._grid_style = "tian"
        self._export_format = "pdf"

        self._setup_ui()

    def _setup_ui(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)

        self._container = QDialog(self)
        self._container.setObjectName("export_container")
        self._container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 1. 顶部 Header
        header = QHBoxLayout()
        title_lbl = QLabel("🖨 导出高清手写字帖")
        title_lbl.setObjectName("dialog_title")
        header.addWidget(title_lbl)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("dialog_close")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        layout.addLayout(header)

        desc_lbl = QLabel(f"即将为您精细排版当前 <b>{self._words_count}</b> 个词汇，支持高清晰度黑白打印与手写笔临摹。")
        desc_lbl.setObjectName("dialog_desc")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # 2. 字格排版样式选择 (田字格 / 米字格 / 手账横线)
        section1 = QLabel("📐 字格排版样式：")
        section1.setObjectName("section_title")
        layout.addWidget(section1)

        style_layout = QHBoxLayout()
        style_layout.setSpacing(10)

        self._btn_group_style = QButtonGroup(self)
        
        self._rb_tian = QRadioButton("⊞ 田字格 (标准)")
        self._rb_tian.setChecked(True)
        self._rb_mi = QRadioButton("✳ 米字格 (八向)")
        self._rb_lines = QRadioButton("≡ 极简横线")

        for idx, rb in enumerate([self._rb_tian, self._rb_mi, self._rb_lines]):
            rb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._btn_group_style.addButton(rb, idx)
            style_layout.addWidget(rb)

        layout.addLayout(style_layout)

        # 3. 导出文件类型 (PDF / PNG)
        section2 = QLabel("📄 导出文件格式：")
        section2.setObjectName("section_title")
        layout.addWidget(section2)

        format_layout = QHBoxLayout()
        format_layout.setSpacing(10)

        self._btn_group_fmt = QButtonGroup(self)
        self._rb_pdf = QRadioButton("📑 PDF 文档 (适合黑白激光打印)")
        self._rb_pdf.setChecked(True)
        self._rb_png = QRadioButton("🖼 PNG 图片 (适合平板临摹)")

        for idx, rb in enumerate([self._rb_pdf, self._rb_png]):
            rb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._btn_group_fmt.addButton(rb, idx)
            format_layout.addWidget(rb)

        layout.addLayout(format_layout)
        layout.addStretch()

        # 4. 底部动作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("✨ 选择路径并导出")
        confirm_btn.setObjectName("btn_confirm")
        confirm_btn.setFixedHeight(36)
        confirm_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        confirm_btn.clicked.connect(self._on_confirm_clicked)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

        self._apply_styles()

    def _apply_styles(self):
        cfg = THEME_CONFIGS.get(self._theme, THEME_CONFIGS.get("seoul_night", {}))
        is_dark = cfg.get("is_dark", True) if cfg else True
        bg = "rgba(24, 28, 36, 0.96)" if is_dark else "rgba(250, 250, 252, 0.96)"
        border = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.14)"
        text = "#FFFFFF" if is_dark else "#0F172A"
        sec = "#94A3B8" if is_dark else "#64748B"
        accent = cfg.get("accent", "#38BDF8") if cfg else "#38BDF8"

        self._container.setStyleSheet(
            f"QDialog#export_container {{ background: {bg}; border: 1px solid {border}; border-radius: 18px; }}"
        )
        self.setStyleSheet(
            f"QLabel#dialog_title {{ color: {text}; font-size: 16px; font-weight: 700; }}"
            f"QLabel#dialog_desc {{ color: {sec}; font-size: 12px; line-height: 1.4; }}"
            f"QLabel#section_title {{ color: {accent}; font-size: 12px; font-weight: 700; margin-top: 4px; }}"
            f"QRadioButton {{ color: {text}; font-size: 12px; font-weight: 500; spacing: 6px; }}"
            f"QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 7px; border: 1px solid {sec}; }}"
            f"QRadioButton::indicator:checked {{ background: {accent}; border: 2px solid #FFFFFF; }}"
            f"QPushButton#dialog_close {{ background: transparent; color: {sec}; border: none; font-size: 13px; }}"
            f"QPushButton#dialog_close:hover {{ color: #EF4444; }}"
            f"QPushButton#btn_cancel {{ background: rgba(255, 255, 255, 0.08); color: {text}; border: 1px solid {border}; border-radius: 10px; font-weight: 600; }}"
            f"QPushButton#btn_cancel:hover {{ background: rgba(255, 255, 255, 0.16); }}"
            f"QPushButton#btn_confirm {{ background: {accent}; color: #FFFFFF; border: none; border-radius: 10px; font-weight: 700; font-size: 13px; }}"
            f"QPushButton#btn_confirm:hover {{ opacity: 0.9; }}"
        )

    def _on_confirm_clicked(self):
        # 1. 解析字格样式
        if self._rb_mi.isChecked():
            grid_style = "mi"
        elif self._rb_lines.isChecked():
            grid_style = "lines"
        else:
            grid_style = "tian"

        # 2. 解析文件格式
        is_pdf = self._rb_pdf.isChecked()
        ext = ".pdf" if is_pdf else ".png"
        filter_str = "PDF 高清文档 (*.pdf)" if is_pdf else "PNG 超清图片 (*.png)"

        date_tag = datetime.now().strftime("%Y%m%d")
        style_name = "田字格" if grid_style == "tian" else ("米字格" if grid_style == "mi" else "手账横线")
        default_filename = f"韩语字帖_{style_name}_{date_tag}{ext}"
        default_dir = os.path.join(os.path.expanduser("~"), "Desktop", default_filename)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择字帖保存路径",
            default_dir,
            filter_str
        )

        if not save_path:
            return

        self.accept()
        self.export_started.emit({
            "grid_style": grid_style,
            "is_pdf": is_pdf,
            "save_path": save_path
        })
