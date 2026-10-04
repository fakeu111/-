"""今日计划视图：按天管理待办，含完成度、优先级、重点、编辑、顺延。"""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets import scroll_area

DAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
PRIORITY_COLOR = {"high": "#D9534F", "mid": "#E0A92E", "low": "#5B9DBF"}
PRIORITY_CYCLE = {"high": "mid", "mid": "low", "low": "high"}
PRIORITY_LABEL = {"high": "高", "mid": "中", "low": "低"}


class ClickLabel(QLabel):
    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, e):
        self.doubleClicked.emit()


class TodoRow(QFrame):
    def __init__(self, db, r, changed):
        super().__init__()
        self.db = db
        self.r = r
        self.changed = changed
        self.setObjectName("TodoRow")
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 7, 8, 7)
        h.setSpacing(9)

        self.check = QCheckBox()
        self.check.setChecked(bool(r["done"]))
        self.check.toggled.connect(self.toggle_done)
        h.addWidget(self.check)

        self.dot = QPushButton()
        self.dot.setObjectName("PriDot")
        self.dot.setFixedSize(8, 30)
        self.dot.setCursor(Qt.PointingHandCursor)
        self.dot.setToolTip(f"优先级：{PRIORITY_LABEL[r['priority']]}，点击切换")
        self.dot.setStyleSheet(f"background:{PRIORITY_COLOR[r['priority']]};border:none;border-radius:3px;")
        self.dot.clicked.connect(self.cycle_priority)
        h.addWidget(self.dot)

        self.content = ClickLabel(r["content"])
        f = self.content.font()
        if r["done"]:
            f.setStrikeOut(True)
            self.content.setStyleSheet("color:#98A09B;")
        self.content.setFont(f)
        h.addWidget(self.content, 1)
        self.content.doubleClicked.connect(self.inline_edit)

        self.star = QPushButton("★" if r["star"] else "☆")
        self.star.setObjectName("RowIcon")
        self.star.setFixedSize(30, 28)
        if r["star"]:
            self.star.setStyleSheet("color:#E0A92E;")
        self.star.clicked.connect(self.toggle_star)
        h.addWidget(self.star)

        delete = QPushButton("✕")
        delete.setObjectName("RowIcon")
        delete.setFixedSize(30, 28)
        delete.setStyleSheet("color:#B0B8B4;")
        delete.clicked.connect(self.delete)
        h.addWidget(delete)

    # ---- 操作 ----
    def toggle_done(self, v):
        self.db.execute(
            "UPDATE todos SET done=?,updated_at=datetime('now','localtime') WHERE id=?",
            (1 if v else 0, self.r["id"]),
        )
        self.changed()

    def toggle_star(self):
        self.db.execute("UPDATE todos SET star=1-star WHERE id=?", (self.r["id"],))
        self.changed()

    def cycle_priority(self):
        new = PRIORITY_CYCLE[self.r["priority"]]
        self.db.execute("UPDATE todos SET priority=? WHERE id=?", (new, self.r["id"]))
        self.changed()

    def delete(self):
        self.db.execute("DELETE FROM todos WHERE id=?", (self.r["id"],))
        self.changed()

    def inline_edit(self):
        edit = QLineEdit(self.r["content"])
        self.layout().replaceWidget(self.content, edit)
        self.content.hide()
        edit.setFocus()
        edit.selectAll()
        done = {"v": False}

        def commit():
            if done["v"]:
                return
            done["v"] = True
            text = edit.text().strip()
            if text:
                self.db.execute("UPDATE todos SET content=? WHERE id=?", (text, self.r["id"]))
            self.changed()

        edit.returnPressed.connect(commit)
        edit.focusOutEvent = lambda e: commit()


class TodayView(QWidget):
    ORDER = ("CASE priority WHEN 'high' THEN 0 WHEN 'low' THEN 2 ELSE 1 END,"
             " star DESC, sort, id")

    def __init__(self, db, win):
        super().__init__()
        self.db = db
        self.win = win
        self.view_date = date.today()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 头部 + 日期导航
        head = QWidget()
        h = QHBoxLayout(head)
        h.setContentsMargins(24, 15, 24, 12)
        left = QVBoxLayout(); left.setSpacing(2)
        t = QLabel("今日计划"); t.setObjectName("PageH1")
        self.date_sub = QLabel(); self.date_sub.setObjectName("PageSub")
        left.addWidget(t); left.addWidget(self.date_sub)
        h.addLayout(left); h.addStretch(1)

        bp = QPushButton("‹"); bp.setObjectName("ToolIcon")
        self.date_label = QLabel(); self.date_label.setFixedWidth(120)
        self.date_label.setAlignment(Qt.AlignCenter)
        nx = QPushButton("›"); nx.setObjectName("ToolIcon")
        bp.clicked.connect(lambda: self.shift(-1)); nx.clicked.connect(lambda: self.shift(1))
        h.addWidget(bp); h.addWidget(self.date_label); h.addWidget(nx)
        bt = QPushButton("回到今天"); bt.clicked.connect(self.back_today)
        h.addWidget(bt)
        post = QPushButton("未完成顺延明天"); post.setObjectName("Btn")
        post.clicked.connect(self.postpone)
        h.addWidget(post)
        outer.addWidget(head)

        # 完成度卡片
        stat_wrap = QWidget()
        sl = QHBoxLayout(stat_wrap)
        sl.setContentsMargins(24, 0, 24, 12)
        card = QFrame(); card.setObjectName("StatCard")
        ch = QHBoxLayout(card); ch.setContentsMargins(18, 14, 18, 14)
        txt = QVBoxLayout()
        self.stat_big = QLabel(); self.stat_big.setObjectName("StatBig")
        self.stat_sub = QLabel(); self.stat_sub.setObjectName("StatSub")
        txt.addWidget(self.stat_big); txt.addWidget(self.stat_sub)
        ch.addLayout(txt); ch.addStretch(1)
        self.bar = QProgressBar(); self.bar.setFixedWidth(300); self.bar.setRange(0, 100)
        ch.addWidget(self.bar)
        sl.addWidget(card)
        outer.addWidget(stat_wrap)

        # 快速添加
        add_wrap = QWidget()
        al = QHBoxLayout(add_wrap)
        al.setContentsMargins(24, 0, 24, 12)
        self.input = QLineEdit()
        self.input.setObjectName("AddInput")
        self.input.setPlaceholderText("添加待办，回车保存")
        self.pri_combo = QComboBox()
        self.pri_combo.setObjectName("PriCombo")
        self.pri_combo.addItems(["高", "中", "低"])
        self.pri_combo.setCurrentIndex(1)
        add_btn = QPushButton("添加"); add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self.add)
        self.input.returnPressed.connect(self.add)
        al.addWidget(self.input, 1); al.addWidget(self.pri_combo); al.addWidget(add_btn)
        outer.addWidget(add_wrap)

        # 列表
        self.list_host = QWidget()
        self.list_lay = QVBoxLayout(self.list_host)
        self.list_lay.setContentsMargins(24, 0, 24, 20)
        self.list_lay.setSpacing(7)
        outer.addWidget(scroll_area(self.list_host), 1)

        self.reload()

    # ---------- 数据 ----------
    def reload(self):
        iso = self.view_date.isoformat()
        active = self.db.query(
            f"SELECT * FROM todos WHERE owner_date=? AND done=0 ORDER BY {self.ORDER}", (iso,)
        )
        done = self.db.query(
            f"SELECT * FROM todos WHERE owner_date=? AND done=1 ORDER BY {self.ORDER}", (iso,)
        )

        d = self.view_date
        self.date_sub.setText(
            f"{d.year}年{d.month}月{d.day}日 · {DAY_CN[d.weekday()]}"
        )
        self.date_label.setText(f"{d.month}/{d.day}")

        total = len(active) + len(done)
        pct = round(len(done) / total * 100) if total else 0
        self.stat_big.setText(f"{len(done)} / {total}")
        self.stat_sub.setText(f"完成度 {pct}%")
        self.bar.setValue(pct)

        self._clear_list()
        self._section(f"未完成（{len(active)}）")
        if active:
            for r in active:
                self.list_lay.addWidget(TodoRow(self.db, r, self.reload))
        else:
            self.list_lay.addWidget(self._hint("这一天没有未完成事项。"))
        self._section(f"已完成（{len(done)}）")
        for r in done:
            self.list_lay.addWidget(TodoRow(self.db, r, self.reload))
        self.list_lay.addStretch(1)

    def add(self):
        text = self.input.text().strip()
        if not text:
            return
        pri = ["high", "mid", "low"][self.pri_combo.currentIndex()]
        mx = self.db.query_one(
            "SELECT COALESCE(MAX(sort),0) m FROM todos WHERE owner_date=?",
            (self.view_date.isoformat(),),
        )["m"]
        self.db.execute(
            "INSERT INTO todos(content,priority,owner_date,sort) VALUES(?,?,?,?)",
            (text, pri, self.view_date.isoformat(), mx + 1),
        )
        self.input.clear()
        self.reload()
        self.win.update_counts()

    def shift(self, delta):
        self.view_date += timedelta(days=delta)
        self.reload()

    def back_today(self):
        self.view_date = date.today()
        self.reload()

    def postpone(self):
        nxt = (self.view_date + timedelta(days=1)).isoformat()
        cur = self.db.execute(
            "UPDATE todos SET owner_date=? WHERE owner_date=? AND done=0",
            (nxt, self.view_date.isoformat()),
        )
        self.reload()
        self.win.update_counts()

    # ---------- 构建辅助 ----------
    def _section(self, text):
        lab = QLabel(text)
        lab.setObjectName("SectionLabel")
        self.list_lay.addWidget(lab)

    def _hint(self, text):
        lab = QLabel(text)
        lab.setStyleSheet("color:#98A09B;font-size:12px;padding:2px 4px 6px;")
        return lab

    def _clear_list(self):
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
