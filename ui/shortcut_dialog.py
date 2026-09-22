# -*- coding: utf-8 -*-
"""
shortcut_dialog.py
------------------
Instagram 极简毛玻璃风格全功能自定义快捷键配置对话框
支持：
1. 全键盘盲操核心快捷键展示与自定义配置
2. 冲突检测与按键捕获
3. 一键「恢复默认快捷键」
4. 持久化存储至 state_manager

Bug Fix: 移除嵌套 QDialog 容器（导致 exec() 事件循环阻塞卡死）
改为 QFrame 容器 + 标准 QDialog 本体，彻底修复 UI 卡死问题。
"""

from typing import Dict, List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QWidget, QGraphicsDropShadowEffect, QMessageBox
)

from config.settings import THEME_CONFIGS

# 核心功能与默认快捷键映射表
DEFAULT_SHORTCUTS = [
    {"id": "flip", "title": "翻转卡片正反面", "desc": "正面/背面即时无延迟翻转", "key": "Space"},
    {"id": "mastered", "title": "标记「认识」并切换下一词", "desc": "快速计入今日掌握并推进进度", "key": "J"},
    {"id": "unfamiliar", "title": "标记「不熟」并反复加权", "desc": "存入生词加权复习池", "key": "K"},
    {"id": "speak", "title": "重播韩语原声发音", "desc": "纯净真人发音朗读", "key": "R"},
    {"id": "star", "title": "一键收藏 / 取消生词", "desc": "收入我的生词本", "key": "S"},
    {"id": "minibar", "title": "屏幕边缘极简磁吸条 (Mini Ticker)", "desc": "34px 微型胶囊条无缝切换与边缘吸附", "key": "F2"},
    {"id": "translator", "title": "呼出 / 收起多引擎翻译抽屉", "desc": "Papago / Google / 离线极简抽屉", "key": "Ctrl+T"},
    {"id": "click_through", "title": "锁定位置与鼠标穿透模式", "desc": "边看剧/办公边悬浮背词不挡点击", "key": "Ctrl+L"},
    {"id": "pomodoro", "title": "专注伴学与番茄钟", "desc": "自然白噪音混音与沉浸计时", "key": "Ctrl+Shift+T"},
    {"id": "clipboard", "title": "剪贴板划词监听开关", "desc": "一键静音/开启全局中韩划词翻译", "key": "Ctrl+Shift+C"},
    {"id": "stats", "title": "学习打卡与热力图看板", "desc": "查看学习统计与每日记忆曲线", "key": "Ctrl+I"},
    {"id": "compact", "title": "极简紧凑模式", "desc": "隐藏导航按钮与辅助栏", "key": "Ctrl+M"},
    {"id": "shuffle", "title": "随机乱序背诵开关", "desc": "打乱顺序避免位置死记硬背", "key": "Ctrl+R"},
    {"id": "hide_window", "title": "老板键 / 隐藏主窗口", "desc": "秒级隐藏至托盘或恢复", "key": "Ctrl+H"},
    {"id": "escape", "title": "快速关闭弹层 / 退出测验", "desc": "Esc 快速关闭当前气泡或抽屉", "key": "Esc"},
]


class KeySequenceButton(QPushButton):
    """支持单击后录制任意按键的快捷键输入按钮。
    
    修复说明：使用 QPushButton 自身的 keyPressEvent 局部捕获
    （而非全局事件拦截），确保 QDialog.exec() 模态事件循环正常运转。
    """

    key_changed = pyqtSignal(str)

    def __init__(self, key_text: str = "", parent=None):
        super().__init__(key_text, parent)
        self._recording = False
        self._current_key = key_text
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(28)
        self.setMinimumWidth(90)
        # 设置强焦点策略，确保 keyPressEvent 能捕获到键盘输入
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(self._toggle_recording)
        self._apply_style()

    def _toggle_recording(self):
        """点击切换录制状态"""
        self._recording = not self._recording
        if self._recording:
            self.setText("请按键...")
            # 请求焦点以捕获键盘事件（局部捕获，不阻塞全局事件分发）
            self.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            self.setText(self._current_key or "(未设置)")
        self._apply_style()

    def keyPressEvent(self, event):
        """仅在录制模式下捕获按键，其余情况交由父类处理"""
        if not self._recording:
            super().keyPressEvent(event)
            return

        key = event.key()
        # 单独修饰键不触发录制
        if key in (
            Qt.Key.Key_Control, Qt.Key.Key_Shift,
            Qt.Key.Key_Alt, Qt.Key.Key_Meta,
        ):
            return

        # Esc 键：取消当前录制，恢复原值
        if key == Qt.Key.Key_Escape:
            self._recording = False
            self.setText(self._current_key or "(未设置)")
            self._apply_style()
            event.accept()
            return

        modifiers = event.modifiers()
        seq_parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            seq_parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            seq_parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            seq_parts.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            seq_parts.append("Meta")

        # 特殊键名映射
        special_keys = {
            Qt.Key.Key_Space:  "Space",
            Qt.Key.Key_Return: "Return",
            Qt.Key.Key_Enter:  "Enter",
            Qt.Key.Key_Tab:    "Tab",
            Qt.Key.Key_Backspace: "Backspace",
            Qt.Key.Key_Delete: "Delete",
            Qt.Key.Key_Insert: "Insert",
            Qt.Key.Key_Home:   "Home",
            Qt.Key.Key_End:    "End",
            Qt.Key.Key_PageUp: "PgUp",
            Qt.Key.Key_PageDown: "PgDn",
            Qt.Key.Key_Up:     "Up",
            Qt.Key.Key_Down:   "Down",
            Qt.Key.Key_Left:   "Left",
            Qt.Key.Key_Right:  "Right",
            Qt.Key.Key_F1: "F1", Qt.Key.Key_F2: "F2", Qt.Key.Key_F3: "F3",
            Qt.Key.Key_F4: "F4", Qt.Key.Key_F5: "F5", Qt.Key.Key_F6: "F6",
            Qt.Key.Key_F7: "F7", Qt.Key.Key_F8: "F8", Qt.Key.Key_F9: "F9",
            Qt.Key.Key_F10: "F10", Qt.Key.Key_F11: "F11", Qt.Key.Key_F12: "F12",
        }

        key_name = special_keys.get(key) or QKeySequence(key).toString()
        if not key_name:
            return

        seq_parts.append(key_name)
        new_key = "+".join(seq_parts)

        self._current_key = new_key
        self._recording = False
        self.setText(new_key)
        self._apply_style()
        self.key_changed.emit(new_key)
        event.accept()

    def focusOutEvent(self, event):
        """失去焦点时自动取消录制，防止按钮永远停在「请按键...」状态"""
        if self._recording:
            self._recording = False
            self.setText(self._current_key or "(未设置)")
            self._apply_style()
        super().focusOutEvent(event)

    def set_key(self, key_text: str):
        self._current_key = key_text
        self._recording = False
        self.setText(key_text or "(未设置)")
        self._apply_style()

    def get_key(self) -> str:
        return self._current_key

    def _apply_style(self):
        if self._recording:
            self.setStyleSheet(
                "QPushButton { background: rgba(56, 189, 248, 0.25); color: #38BDF8; "
                "border: 1.5px solid #38BDF8; border-radius: 8px; font-weight: bold; "
                "font-size: 11px; padding: 0 8px; }"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.08); color: #E2E8F0; "
                "border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; "
                "font-weight: 600; font-size: 11px; padding: 0 8px; }"
                "QPushButton:hover { background: rgba(255, 255, 255, 0.16); color: #FFFFFF; "
                "border-color: rgba(255, 255, 255, 0.28); }"
            )


class ShortcutDialog(QDialog):
    """全功能自定义快捷键配置对话框
    
    修复说明：移除嵌套 QDialog 容器（原代码在 QDialog 内部嵌套另一个 QDialog
    作为视觉容器，导致 exec() 调用时出现两个互相竞争的模态事件循环，造成 UI 卡死）。
    现改为 QFrame 作为视觉容器，彻底解决卡死问题。
    """

    shortcuts_saved = pyqtSignal(dict)  # 包含已配置的快捷键字典

    def __init__(
        self,
        current_shortcuts: Optional[Dict[str, str]] = None,
        current_theme: str = "seoul_night",
        parent=None,
    ):
        # 使用标准 QDialog（无 FramelessWindowHint），避免事件路由问题
        # 保留 Dialog 标志确保模态行为正确
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("自定义全功能快捷键")
        self.setFixedSize(560, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._theme = current_theme
        self._key_map: Dict[str, str] = {}

        # 载入现有快捷键配置，若无则使用默认映射
        user_sc = current_shortcuts or {}
        for item in DEFAULT_SHORTCUTS:
            s_id = item["id"]
            self._key_map[s_id] = user_sc.get(s_id, item["key"])

        self._buttons: Dict[str, KeySequenceButton] = {}
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # ── 顶部 Header ──────────────────────────────────────
        header = QHBoxLayout()
        title_lbl = QLabel("自定义全功能快捷键")
        title_lbl.setObjectName("dialog_title")
        header.addWidget(title_lbl)
        header.addStretch()
        main_layout.addLayout(header)

        desc_lbl = QLabel("单击任意快捷键按钮，按下新键即可完成录制；按 Esc 可取消单次录制。")
        desc_lbl.setObjectName("dialog_desc")
        desc_lbl.setWordWrap(True)
        main_layout.addWidget(desc_lbl)

        # 分隔线
        sep_top = QFrame()
        sep_top.setFrameShape(QFrame.Shape.HLine)
        sep_top.setObjectName("sep_line")
        main_layout.addWidget(sep_top)

        # ── 快捷键列表滚动区 ──────────────────────────────────
        scroll = QScrollArea(self)
        scroll.setObjectName("shortcut_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        scroll.viewport().setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setObjectName("shortcut_scroll_content")
        scroll_content.setAutoFillBackground(False)
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 4, 8, 4)
        scroll_layout.setSpacing(6)

        for item in DEFAULT_SHORTCUTS:
            s_id = item["id"]
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 6, 4, 6)
            row_layout.setSpacing(12)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)

            name_lbl = QLabel(item["title"])
            name_lbl.setObjectName("action_title")
            info_layout.addWidget(name_lbl)

            desc_sub = QLabel(item["desc"])
            desc_sub.setObjectName("action_desc")
            info_layout.addWidget(desc_sub)

            row_layout.addLayout(info_layout, stretch=1)

            # 按键录制按钮
            current_key = self._key_map.get(s_id, item["key"])
            btn = KeySequenceButton(current_key or "(未设置)")
            btn.key_changed.connect(lambda k, sid=s_id: self._on_key_updated(sid, k))
            self._buttons[s_id] = btn
            row_layout.addWidget(btn)

            scroll_layout.addWidget(row_widget)

            # 分割线
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setObjectName("row_sep")
            scroll_layout.addWidget(sep)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=1)

        # ── 底部操作栏 ────────────────────────────────────────
        sep_bot = QFrame()
        sep_bot.setFrameShape(QFrame.Shape.HLine)
        sep_bot.setObjectName("sep_line")
        main_layout.addWidget(sep_bot)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        reset_btn = QPushButton("恢复默认")
        reset_btn.setObjectName("btn_reset")
        reset_btn.setFixedHeight(34)
        reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reset_btn.clicked.connect(self._reset_to_default)
        btn_bar.addWidget(reset_btn)

        btn_bar.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setFixedWidth(70)
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.clicked.connect(self.reject)
        btn_bar.addWidget(cancel_btn)

        save_btn = QPushButton("保存并生效")
        save_btn.setObjectName("btn_save")
        save_btn.setFixedHeight(34)
        save_btn.setFixedWidth(110)
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.clicked.connect(self._save_and_accept)
        btn_bar.addWidget(save_btn)

        main_layout.addLayout(btn_bar)

    def _apply_styles(self):
        cfg = THEME_CONFIGS.get(self._theme, THEME_CONFIGS.get("seoul_night", {}))
        accent = cfg.get("accent", "#2ECC71") if cfg else "#2ECC71"
        is_dark = cfg.get("is_dark", True) if cfg else True
        bg = f"rgb({cfg['bg_color'][0]}, {cfg['bg_color'][1]}, {cfg['bg_color'][2]})" if (cfg and "bg_color" in cfg) else ("rgb(18, 20, 26)" if is_dark else "rgb(248, 249, 252)")
        text = cfg.get("text_primary", "#FFFFFF") if cfg else ("#E2E8F0" if is_dark else "#1E293B")
        text_sec = cfg.get("text_secondary", "#94A3B8") if cfg else "#64748B"
        border = cfg.get("border", "rgba(255, 255, 255, 0.10)") if cfg else ("rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)")

        self.setStyleSheet(
            f"QDialog {{ background: {bg}; color: {text}; }}"
            f"QLabel#dialog_title {{ color: {text}; font-size: 15px; font-weight: 700; }}"
            f"QLabel#dialog_desc {{ color: {text_sec}; font-size: 11px; }}"
            f"QLabel#action_title {{ color: {text}; font-size: 12px; font-weight: 600; }}"
            f"QLabel#action_desc {{ color: {text_sec}; font-size: 10px; }}"
            f"QFrame#sep_line {{ background: {border}; max-height: 1px; border: none; }}"
            f"QFrame#row_sep {{ background: {border}; max-height: 1px; border: none; }}"
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}"
            f"QWidget#shortcut_scroll_content {{ background: transparent; }}"
            f"QScrollBar:vertical {{ background: rgba(255, 255, 255, 0.05); width: 8px; margin: 0; border-radius: 4px; }}"
            f"QScrollBar::handle:vertical {{ background: rgba(255, 255, 255, 0.32); border-radius: 4px; min-height: 28px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 0.52); }}"
            f"QScrollBar::handle:vertical:pressed {{ background: {accent}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; border: none; }}"
            f"QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{ background: none; border: none; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; border: none; }}"
            f"QPushButton#btn_reset {{ background: transparent; color: {text_sec}; "
            f"border: 1px solid {border}; border-radius: 8px; "
            f"font-size: 12px; font-weight: 600; padding: 0 14px; }}"
            f"QPushButton#btn_reset:hover {{ color: {text}; border-color: {accent}; }}"
            f"QPushButton#btn_cancel {{ background: transparent; color: {text}; "
            f"border: 1px solid {border}; border-radius: 8px; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton#btn_cancel:hover {{ background: rgba(255, 255, 255, 0.06); }}"
            f"QPushButton#btn_save {{ background: {accent}; color: #FFFFFF; border: none; "
            f"border-radius: 8px; font-size: 12px; font-weight: 700; }}"
            f"QPushButton#btn_save:hover {{ background: {accent}CC; }}"
        )

    def _on_key_updated(self, sid: str, new_key: str):
        self._key_map[sid] = new_key

    def _reset_to_default(self):
        for item in DEFAULT_SHORTCUTS:
            sid = item["id"]
            def_key = item["key"]
            self._key_map[sid] = def_key
            if sid in self._buttons:
                self._buttons[sid].set_key(def_key)

    def _save_and_accept(self):
        # 冲突检测（轻提示，不阻断保存）
        seen_keys: Dict[str, str] = {}
        conflicts = []
        for sid, k in self._key_map.items():
            if not k:
                continue
            if k in seen_keys:
                other_sid = seen_keys[k]
                t1 = next((x["title"] for x in DEFAULT_SHORTCUTS if x["id"] == sid), sid)
                t2 = next((x["title"] for x in DEFAULT_SHORTCUTS if x["id"] == other_sid), other_sid)
                conflicts.append(f"「{t1}」与「{t2}」均绑定至 {k}")
            else:
                seen_keys[k] = sid

        if conflicts:
            detail = "\n".join(conflicts)
            QMessageBox.warning(
                self,
                "快捷键冲突提示",
                f"以下快捷键存在冲突，请检查：\n\n{detail}\n\n已保存，但冲突键可能无法正常触发。"
            )

        self.shortcuts_saved.emit(self._key_map)
        self.accept()
