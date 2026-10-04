"""主窗口：左侧导航 + 右侧 QStackedWidget。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.db import DB
from app.ui.goals_view import GoalsView
from app.ui.home_view import HomeView
from app.ui.memos_view import MemosView
from app.ui.schedule_view import ScheduleView
from app.ui.settings_dialog import SettingsDialog
from app.ui.today_view import TodayView


def _resource(name: str) -> str:
    from app import config

    return str(config.resource_path(name))


class MainWindow(QMainWindow):
    # key, 显示名, 图标
    VIEWS = [
        ("home", "首页", "home.svg"),
        ("schedule", "课程表", "calendar.svg"),
        ("today", "今日计划", "check.svg"),
        ("goals", "长期计划", "target.svg"),
        ("memos", "备忘录", "memo.svg"),
    ]

    def __init__(self, db: DB | None = None):
        super().__init__()
        self.db = db or DB()
        self.setWindowTitle("学习桌面")
        self.resize(1180, 780)

        central = QWidget()
        central.setObjectName("Central")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.stack.setObjectName("Stack")
        self.placeholders: dict[str, QWidget] = {}
        for key, label, _ in self.VIEWS:
            page = QWidget()
            lay = QVBoxLayout(page)
            tip = QLabel(f"「{label}」页面")
            tip.setObjectName("EmptyText")
            tip.setAlignment(Qt.AlignCenter)
            lay.addWidget(tip)
            self.stack.addWidget(page)
            self.placeholders[key] = page
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)

        self.home_view = HomeView(self.db, self)
        self.replace_page("home", self.home_view)

        self.schedule_view = ScheduleView(self.db, self)
        self.replace_page("schedule", self.schedule_view)
        self.schedule_view.reload()

        self.today_view = TodayView(self.db, self)
        self.replace_page("today", self.today_view)

        self.goals_view = GoalsView(self.db, self)
        self.replace_page("goals", self.goals_view)

        self.memos_view = MemosView(self.db, self)
        self.replace_page("memos", self.memos_view)

        self.show_view("home")
        self.update_counts()

    # ---------- 侧边栏 ----------
    def _build_sidebar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(206)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(11, 12, 11, 13)
        lay.setSpacing(3)

        title = QLabel("工作区")
        title.setObjectName("SidebarLabel")
        lay.addWidget(title)

        self.nav_buttons: dict[str, QPushButton] = {}
        self.count_labels: dict[str, QLabel] = {}
        for key, label, icon in self.VIEWS:
            btn = self._nav_row(icon, label, key)
            lay.addWidget(btn)
            self.nav_buttons[key] = btn

        lay.addStretch(1)

        settings_btn = QPushButton()
        settings_btn.setObjectName("NavItem")
        settings_btn.setMinimumHeight(38)
        sl = QHBoxLayout(settings_btn)
        sl.setContentsMargins(10, 8, 10, 8)
        sl.setSpacing(9)
        sicon = QLabel()
        sicon.setPixmap(QIcon(_resource("settings.svg")).pixmap(18, 18))
        stext = QLabel("设置")
        stext.setObjectName("NavText")
        sl.addWidget(sicon)
        sl.addWidget(stext)
        settings_btn.clicked.connect(self.open_settings)
        lay.addWidget(settings_btn)

        return bar

    def _nav_row(self, icon_file: str, text: str, key: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("NavItem")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(38)
        h = QHBoxLayout(btn)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(9)

        icon = QLabel()
        icon.setPixmap(QIcon(_resource(icon_file)).pixmap(QSize(18, 18)))
        label = QLabel(text)
        label.setObjectName("NavText")
        count = QLabel("0")
        count.setObjectName("NavCount")
        count.setAlignment(Qt.AlignCenter)
        count.setFixedHeight(18)
        count.hide()

        h.addWidget(icon)
        h.addWidget(label)
        h.addStretch(1)
        h.addWidget(count)
        self.count_labels[key] = count

        btn.clicked.connect(lambda: self.show_view(key))
        return btn

    # ---------- 视图切换 ----------
    def navigate(self, key: str) -> None:
        self.show_view(key)

    def show_view(self, key: str) -> None:
        index = next(i for i, (k, *_rest) in enumerate(self.VIEWS) if k == key)
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)
        self.stack.setCurrentIndex(index)

    def replace_page(self, key: str, widget: QWidget) -> None:
        """用正式视图替换占位页。"""
        index = next(i for i, (k, *_rest) in enumerate(self.VIEWS) if k == key)
        self.stack.removeWidget(self.placeholders[key])
        self.stack.insertWidget(index, widget)
        self.placeholders[key] = widget

    # ---------- 角标 ----------
    def update_counts(self) -> None:
        todo_n = self.db.query_one("SELECT COUNT(*) c FROM todos WHERE done=0")["c"]
        goal_n = self.db.query_one("SELECT COUNT(*) c FROM goals WHERE status='active'")["c"]
        memo_n = self.db.query_one(
            "SELECT COUNT(*) c FROM memos WHERE due IS NOT NULL AND date(due) <= date('now','+1 day')"
        )["c"]
        self._set_count("today", todo_n)
        self._set_count("goals", goal_n)
        self._set_count("memos", memo_n)

    def _set_count(self, key: str, n: int) -> None:
        lab = self.count_labels[key]
        lab.setText(str(n))
        lab.setVisible(n > 0)

    # ---------- 设置 ----------
    def open_settings(self) -> None:
        dlg = SettingsDialog(self.db, self)
        if dlg.exec():
            self.refresh_all()

    def refresh_all(self) -> None:
        """设置变更或数据写入后统一刷新各视图。"""
        self.home_view.reload()
        self.schedule_view.reload()
        self.today_view.reload()
        self.goals_view.reload()
        self.memos_view.reload()
        self.update_counts()
