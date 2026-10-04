"""共用 UI 控件：徽章、卡片标题、空状态等。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

_PILL_NAME = {
    "overdue": "PillOverdue",
    "today": "PillToday",
    "soon": "PillSoon",
    "none": "PillNone",
}


def pill(text: str, kind: str = "none") -> QLabel:
    lab = QLabel(text)
    lab.setObjectName(_PILL_NAME.get(kind, "PillNone"))
    lab.setProperty("class", "Pill")
    lab.setAlignment(Qt.AlignCenter)
    return lab


def empty_state(message: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lab = QLabel(message)
    lab.setObjectName("EmptyText")
    lab.setAlignment(Qt.AlignCenter)
    lay.addWidget(lab)
    return w


def page_header(title: str, sub: str = "", right: QWidget | None = None) -> QWidget:
    """统一的页面标题栏：左标题/副标题，右侧操作区。"""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    left = QVBoxLayout()
    left.setSpacing(3)
    h1 = QLabel(title)
    h1.setObjectName("PageH1")
    left.addWidget(h1)
    if sub:
        s = QLabel(sub)
        s.setObjectName("PageSub")
        left.addWidget(s)
    lay.addLayout(left)
    lay.addStretch(1)
    if right is not None:
        lay.addWidget(right)
    return w


def scroll_area(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setAttribute(Qt.WA_StyledBackground, True)
    area.setStyleSheet("background: transparent;")
    area.setWidget(widget)
    return area
