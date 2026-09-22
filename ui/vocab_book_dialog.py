# ui/vocab_book_dialog.py
"""生词本弹窗：显示所有收藏词汇，支持删除和进入复习模式"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Dict, Callable

from config.settings import COLORS, POS_COLORS, FONT_POS_SIZE


class VocabItemWidget(QFrame):
    """生词本中单个词条组件"""

    remove_clicked = pyqtSignal(str)   # word_id

    def __init__(self, item: Dict, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._word_id = item["word_id"]
        self._theme = theme
        self._setup_ui(item)
        self.apply_theme(theme)

    def _setup_ui(self, item: Dict):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 词性
        pos = item.get("pos", "")
        pos_bg, _ = POS_COLORS.get(pos, POS_COLORS["default"])
        self._pos_label = QLabel(pos or "—")
        self._pos_label.setFixedWidth(52)
        self._pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pos_label.setStyleSheet(
            f"QLabel {{ background: {pos_bg}44; color: {pos_bg}; border-radius: 8px; "
            f"padding: 2px 4px; font-size: {FONT_POS_SIZE}px; font-weight: 600; }}"
        )
        layout.addWidget(self._pos_label)

        # 韩语 + 中文
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        self._korean = QLabel(item.get("korean", ""))
        self._korean.setStyleSheet("QLabel { font-size: 16px; font-weight: 700; }")
        text_col.addWidget(self._korean)

        self._chinese = QLabel(item.get("chinese", ""))
        self._chinese.setStyleSheet("QLabel { font-size: 12px; }")
        text_col.addWidget(self._chinese)

        layout.addLayout(text_col, stretch=1)

        # 删除按钮
        self._del_btn = QPushButton("✕")
        self._del_btn.setFixedSize(26, 26)
        self._del_btn.setToolTip("从生词本删除")
        self._del_btn.clicked.connect(lambda: self.remove_clicked.emit(self._word_id))
        layout.addWidget(self._del_btn)

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def apply_theme(self, theme: str):
        from config.settings import THEME_CONFIGS
        if theme == "dark": theme = "seoul_night"
        elif theme == "light": theme = "cream_latte"
        cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["seoul_night"])

        card_bg = cfg.get("card_bg", "#161922")
        text = cfg.get("text_primary", "#FFFFFF")
        text_sec = cfg.get("text_secondary", "#94A3B8")
        border = cfg.get("border", "rgba(255, 255, 255, 0.10)")

        self.setStyleSheet(
            f"VocabItemWidget, QFrame {{ background: {card_bg}; border-radius: 10px; "
            f"border: 1px solid {border}; }}"
        )
        self._korean.setStyleSheet(
            f"QLabel {{ color: {text}; font-size: 16px; font-weight: 700; background: transparent; border: none; }}"
        )
        self._chinese.setStyleSheet(
            f"QLabel {{ color: {text_sec}; font-size: 12px; background: transparent; border: none; }}"
        )
        self._del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {text_sec}; border: none; "
            f"border-radius: 6px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: #C47A7A55; color: #FFAAAA; }}"
        )


class VocabBookDialog(QDialog):
    """生词本弹窗"""

    review_requested = pyqtSignal()   # 请求进入复习模式
    export_requested = pyqtSignal()   # 请求导出字帖

    def __init__(self, items_or_vocab_book: Any, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        if hasattr(items_or_vocab_book, "get_all"):
            self._items = items_or_vocab_book.get_all()
        elif isinstance(items_or_vocab_book, list):
            self._items = list(items_or_vocab_book)
        else:
            self._items = []
        self._removed_ids: List[str] = []

        self.setWindowTitle("我的生词本")
        self.setFixedSize(380, 500)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self._setup_ui()
        self.apply_theme(theme)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题栏
        title_row = QHBoxLayout()
        self._title = QLabel(f"我的生词本 ({len(self._items)} 个)")
        self._title.setStyleSheet("QLabel { font-size: 16px; font-weight: 700; }")
        title_row.addWidget(self._title)
        title_row.addStretch()

        self._export_btn = QPushButton("导出字帖")
        self._export_btn.setFixedHeight(28)
        self._export_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._export_btn.setEnabled(len(self._items) > 0)
        self._export_btn.clicked.connect(self._on_export)
        title_row.addWidget(self._export_btn)

        layout.addLayout(title_row)

        # 复习按钮
        self._review_btn = QPushButton("进入复习模式")
        self._review_btn.setFixedHeight(38)
        self._review_btn.setEnabled(len(self._items) > 0)
        self._review_btn.clicked.connect(self._on_review)
        layout.addWidget(self._review_btn)

        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # 词汇列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        scroll.viewport().setStyleSheet("background: transparent;")

        self._list_widget = QWidget()
        self._list_widget.setAutoFillBackground(False)
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)

        if not self._items:
            empty = QLabel("生词本为空\n学习时点击收藏单词")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("QLabel { font-size: 14px; opacity: 0.6; }")
            self._list_layout.addWidget(empty)
        else:
            for item in self._items:
                w = VocabItemWidget(item, self._theme)
                w.remove_clicked.connect(self._on_remove)
                self._list_layout.addWidget(w)

        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        layout.addWidget(scroll)

    def _on_remove(self, word_id: str):
        self._removed_ids.append(word_id)
        # 从 UI 中移除
        for i in range(self._list_layout.count()):
            w = self._list_layout.itemAt(i).widget()
            if isinstance(w, VocabItemWidget) and w._word_id == word_id:
                w.setVisible(False)
                break
        remaining = len(self._items) - len(self._removed_ids)
        self._title.setText(f"我的生词本 ({remaining} 个)")
        self._review_btn.setEnabled(remaining > 0)

    def _on_review(self):
        self.review_requested.emit()
        self.accept()

    def _on_export(self):
        self.export_requested.emit()

    def get_removed_ids(self) -> List[str]:
        return self._removed_ids

    def apply_theme(self, theme: str):
        from config.settings import THEME_CONFIGS
        if theme == "dark": theme = "seoul_night"
        elif theme == "light": theme = "cream_latte"
        cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["seoul_night"])

        bg = f"rgb({cfg['bg_color'][0]}, {cfg['bg_color'][1]}, {cfg['bg_color'][2]})"
        text = cfg.get("text_primary", "#FFFFFF")
        accent = cfg.get("accent", "#2ECC71")
        border = cfg.get("border", "rgba(255, 255, 255, 0.10)")

        self.setStyleSheet(
            f"QDialog {{ background: {bg}; }}"
            f"QLabel {{ color: {text}; }}"
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget {{ background: transparent; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}"
            f"QScrollBar:vertical {{ background: rgba(255, 255, 255, 0.05); width: 8px; margin: 0; border-radius: 4px; }}"
            f"QScrollBar::handle:vertical {{ background: rgba(255, 255, 255, 0.32); border-radius: 4px; min-height: 28px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 0.52); }}"
            f"QScrollBar::handle:vertical:pressed {{ background: {accent}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; border: none; }}"
            f"QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{ background: none; border: none; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; border: none; }}"
        )
        self._export_btn.setStyleSheet(
            f"QPushButton {{ background: {accent}22; color: {accent}; "
            f"border: 1px solid {accent}55; border-radius: 8px; font-size: 11px; font-weight: 600; padding: 2px 10px; }}"
            f"QPushButton:hover {{ background: {accent}44; color: #FFFFFF; }}"
            f"QPushButton:disabled {{ background: {border}; color: {text}44; border-color: transparent; }}"
        )
        self._review_btn.setStyleSheet(
            f"QPushButton {{ background: {accent}; color: white; border: none; "
            f"border-radius: 10px; font-size: 14px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {accent}CC; }}"
            f"QPushButton:disabled {{ background: {border}; color: {text}66; }}"
        )

        for i in range(self._list_layout.count()):
            w = self._list_layout.itemAt(i).widget()
            if isinstance(w, VocabItemWidget):
                w.apply_theme(theme)
