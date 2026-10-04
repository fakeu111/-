"""长期计划视图：计划卡片、里程碑进度、状态筛选、加到今日。"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.dialogs.goal_dialog import GoalDialog
from app.ui.widgets import scroll_area

STATUS = [("todo", "未开始"), ("active", "进行中"), ("done", "已完成"), ("dropped", "已放弃")]
FILTERS = [("all", "全部"), ("active", "进行中"), ("todo", "未开始"),
           ("done", "已完成"), ("dropped", "已放弃")]


def recompute_status(db, gid):
    rows = db.query("SELECT done FROM milestones WHERE goal_id=?", (gid,))
    total = len(rows)
    done = sum(r["done"] for r in rows)
    status = db.query_one("SELECT status FROM goals WHERE id=?", (gid,))["status"]
    if total and done == total and status in ("todo", "active"):
        db.execute("UPDATE goals SET status='done' WHERE id=?", (gid,))
    elif done < total and status == "done":
        db.execute("UPDATE goals SET status='active' WHERE id=?", (gid,))
    return done, total


class GoalCard(QFrame):
    def __init__(self, db, win, goal, changed):
        super().__init__()
        self.db = db
        self.win = win
        self.goal = goal
        self.changed = changed
        self.setObjectName("GoalCard")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 15, 18, 16)
        v.setSpacing(9)

        top = QHBoxLayout()
        title = QLabel(goal["title"]); title.setObjectName("GoalTitle")
        top.addWidget(title); top.addStretch(1)

        self.status_combo = QComboBox()
        self.status_combo.setObjectName("StatusCombo")
        for key, label in STATUS:
            self.status_combo.addItem(label, key)
        idx = next(i for i, (k, _l) in enumerate(STATUS) if k == goal["status"])
        self.status_combo.blockSignals(True)
        self.status_combo.setCurrentIndex(idx)
        self.status_combo.blockSignals(False)
        self.status_combo.currentIndexChanged.connect(self.change_status)
        top.addWidget(self.status_combo)

        edit = QPushButton("编辑"); edit.clicked.connect(self.edit)
        delete = QPushButton("删除")
        delete.setStyleSheet("color:#B05852;")
        delete.clicked.connect(self.delete)
        top.addWidget(edit); top.addWidget(delete)
        v.addLayout(top)

        dates = QLabel(f"{goal['start_date']}  →  {goal['end_date']}")
        dates.setObjectName("GoalDate")
        v.addWidget(dates)

        self.milestones = db.query(
            "SELECT * FROM milestones WHERE goal_id=? ORDER BY sort,id", (goal["id"],)
        )
        first_open = True
        for m in self.milestones:
            row = QFrame(); row.setObjectName("MilestoneRow")
            rh = QHBoxLayout(row)
            rh.setContentsMargins(0, 1, 0, 1)
            cb = QCheckBox()
            cb.setChecked(bool(m["done"]))
            cb.toggled.connect(lambda _x, mid=m["id"]: self.toggle_milestone(mid))
            rh.addWidget(cb)
            lab = QLabel(m["content"])
            if m["done"]:
                f = lab.font(); f.setStrikeOut(True); lab.setFont(f)
                lab.setObjectName("MilestoneDone")
            rh.addWidget(lab); rh.addStretch(1)
            if not m["done"] and first_open:
                tag = QLabel("下一步"); tag.setObjectName("NextTag")
                rh.addWidget(tag)
                first_open = False
            v.addWidget(row)

        prog = QHBoxLayout()
        self.bar = QProgressBar(); self.bar.setRange(0, 100)
        self.pct_label = QLabel()
        self.pct_label.setStyleSheet("color:#6A746F;font-size:12px;")
        prog.addWidget(self.bar, 1); prog.addWidget(self.pct_label)
        v.addLayout(prog)
        self._render_progress()

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.add_today_btn = QPushButton("把下一步加到今日")
        self.add_today_btn.setObjectName("Btn")
        self.add_today_btn.setEnabled(not first_open or any(
            not m["done"] for m in self.milestones
        ))
        self.add_today_btn.clicked.connect(self.add_to_today)
        actions.addWidget(self.add_today_btn)
        v.addLayout(actions)

    def _render_progress(self):
        total = len(self.milestones)
        done = sum(m["done"] for m in self.milestones)
        pct = round(done / total * 100) if total else 0
        self.bar.setValue(pct)
        self.pct_label.setText(f"{done}/{total} · {pct}%")

    def toggle_milestone(self, mid):
        self.db.execute("UPDATE milestones SET done=1-done WHERE id=?", (mid,))
        recompute_status(self.db, self.goal["id"])
        self.changed()

    def change_status(self):
        key = self.status_combo.currentData()
        self.db.execute("UPDATE goals SET status=? WHERE id=?", (key, self.goal["id"]))
        self.changed()

    def add_to_today(self):
        m = next((m for m in self.milestones if not m["done"]), None)
        if not m:
            return
        owner = date.today().isoformat()
        mx = self.db.query_one(
            "SELECT COALESCE(MAX(sort),0) x FROM todos WHERE owner_date=?", (owner,)
        )["x"]
        self.db.execute(
            "INSERT INTO todos(content,owner_date,sort) VALUES(?,?,?)",
            (f"【{self.goal['title']}】{m['content']}", owner, mx + 1),
        )
        self.add_today_btn.setText("已加到今日")
        self.win.update_counts()

    def edit(self):
        GoalDialog(self.db, self.goal, self).exec()
        self.changed()

    def delete(self):
        self.db.execute("DELETE FROM goals WHERE id=?", (self.goal["id"],))
        self.changed()


class GoalsView(QWidget):
    def __init__(self, db, win):
        super().__init__()
        self.db = db
        self.win = win
        self.filter = "all"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        head = QWidget()
        h = QHBoxLayout(head)
        h.setContentsMargins(24, 15, 24, 12)
        left = QVBoxLayout(); left.setSpacing(2)
        t = QLabel("长期计划"); t.setObjectName("PageH1")
        s = QLabel("把大目标拆成可勾选的里程碑，下一步自动浮现")
        s.setObjectName("PageSub")
        left.addWidget(t); left.addWidget(s)
        h.addLayout(left); h.addStretch(1)
        new = QPushButton("新建计划"); new.setObjectName("Primary")
        new.clicked.connect(self.new_goal)
        h.addWidget(new)
        outer.addWidget(head)

        bar_wrap = QWidget()
        bl = QHBoxLayout(bar_wrap)
        bl.setContentsMargins(24, 0, 24, 12)
        tabbar = QFrame(); tabbar.setObjectName("TabBar")
        tb = QHBoxLayout(tabbar)
        tb.setContentsMargins(4, 4, 4, 4)
        for key, label in FILTERS:
            b = QPushButton(label)
            b.setObjectName("Tab")
            b.setCheckable(True)
            b.setChecked(key == self.filter)
            b.clicked.connect(lambda _x, k=key: self.set_filter(k))
            tb.addWidget(b)
        bl.addWidget(tabbar); bl.addStretch(1)
        outer.addWidget(bar_wrap)

        self.cards_host = QWidget()
        self.cards_lay = QVBoxLayout(self.cards_host)
        self.cards_lay.setContentsMargins(24, 0, 24, 20)
        self.cards_lay.setSpacing(12)
        outer.addWidget(scroll_area(self.cards_host), 1)
        self.reload()

    def set_filter(self, key):
        self.filter = key
        self.reload()

    def new_goal(self):
        GoalDialog(self.db, None, self).exec()
        self.reload()
        self.win.update_counts()

    def reload(self):
        if self.filter == "all":
            rows = self.db.query(
                "SELECT * FROM goals ORDER BY CASE status WHEN 'active' THEN 0"
                " WHEN 'todo' THEN 1 ELSE 2 END, sort, id"
            )
        else:
            rows = self.db.query(
                "SELECT * FROM goals WHERE status=? ORDER BY sort,id", (self.filter,)
            )
        while self.cards_lay.count():
            w = self.cards_lay.takeAt(0).widget()
            if w:
                w.setParent(None)
        for g in rows:
            self.cards_lay.addWidget(GoalCard(self.db, self.win, g, self.reload))
        if not rows:
            lab = QLabel("这里还没有计划，点右上角“新建计划”开始。")
            lab.setStyleSheet("color:#98A09B;padding:8px;")
            self.cards_lay.addWidget(lab)
        self.cards_lay.addStretch(1)
        self._sync_tabs()

    def _sync_tabs(self):
        tabs = self.findChildren(QPushButton, "Tab")
        labels = [label for _k, label in FILTERS]
        for b in tabs:
            key = next(k for k, label in FILTERS if label == b.text())
            b.setChecked(key == self.filter)
