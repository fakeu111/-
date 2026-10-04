"""首页总览：今日课程、今日完成环、今日计划、临期备忘录；快速新增与跳转。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.schedule import classes_on
from app.ui.memos_view import due_category
from app.ui.widgets import empty_state, scroll_area

WEEK_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class Ring(QWidget):
    """完成率环形图。"""

    def __init__(self):
        super().__init__()
        self.percent = 0
        self.setFixedSize(128, 128)

    def set_percent(self, p):
        self.percent = max(0, min(100, int(round(p))))
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)
        p.setPen(QPen(QColor("#E6EAE7"), 10))
        p.drawArc(rect, 0, 360 * 16)
        if self.percent:
            p.setPen(QPen(QColor("#2F8F73"), 10, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, 90 * 16, -int(self.percent * 3.6 * 16))
        p.setPen(QColor("#1F2A2E"))
        f = p.font(); f.setPointSize(17); f.setBold(True)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, f"{self.percent}%")


class HomeView(QWidget):
    def __init__(self, db, win):
        super().__init__()
        self.db = db
        self.win = win

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 16, 22, 18)
        outer.setSpacing(14)

        # ---------- 顶部 ----------
        top = QHBoxLayout()
        tv = QVBoxLayout(); tv.setSpacing(3)
        self.date_big = QLabel(); self.date_big.setObjectName("HomeDateBig")
        self.date_sub = QLabel(); self.date_sub.setObjectName("HomeDateSub")
        tv.addWidget(self.date_big); tv.addWidget(self.date_sub)
        top.addLayout(tv)
        top.addStretch(1)
        bt = QPushButton("新建待办"); bt.setObjectName("Primary")
        bm = QPushButton("新建备忘"); bm.setObjectName("Ghost")
        bt.clicked.connect(self.quick_todo)
        bm.clicked.connect(self.quick_memo)
        top.addWidget(bt); top.addWidget(bm)
        outer.addLayout(top)

        # ---------- 第一行 ----------
        row1 = QHBoxLayout(); row1.setSpacing(14)
        self.courses_card, self.courses_body = self._card("今日课程", "查看课程表", "schedule")
        self.ring_card, self.ring_body = self._card("今日完成", None, None)
        self.ring = Ring()
        self.ring_counts = QLabel(); self.ring_counts.setAlignment(Qt.AlignCenter)
        postpone = QPushButton("未完成顺延明天"); postpone.setObjectName("Ghost")
        postpone.clicked.connect(self.postpone)
        rc = QVBoxLayout(); rc.setAlignment(Qt.AlignCenter); rc.setSpacing(8)
        rc.addWidget(self.ring, 0, Qt.AlignCenter)
        rc.addWidget(self.ring_counts, 0, Qt.AlignCenter)
        rc.addWidget(postpone, 0, Qt.AlignCenter)
        self.ring_body.addLayout(rc)
        row1.addWidget(self.courses_card, 3)
        row1.addWidget(self.ring_card, 2)
        outer.addLayout(row1)

        # ---------- 第二行 ----------
        row2 = QHBoxLayout(); row2.setSpacing(14)
        self.todos_card, self.todos_body = self._card("今日计划", "查看全部", "today")
        self.memos_card, self.memos_body = self._card("临期备忘录", "查看全部", "memos")
        row2.addWidget(self.todos_card, 1)
        row2.addWidget(self.memos_card, 1)
        outer.addLayout(row2, 1)

        self.reload()

    # ---------- 卡片骨架 ----------
    def _card(self, title, link_text, page):
        card = QFrame(); card.setObjectName("HomeCard")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 13, 16, 14)
        v.setSpacing(10)
        h = QHBoxLayout()
        t = QLabel(title); t.setObjectName("HomeCardTitle")
        h.addWidget(t); h.addStretch(1)
        if link_text:
            link = QPushButton(link_text); link.setObjectName("CardLink")
            link.setCursor(Qt.PointingHandCursor)
            link.clicked.connect(lambda: self.win.navigate(page))
            h.addWidget(link)
        v.addLayout(h)
        body = QVBoxLayout(); body.setSpacing(6)
        v.addLayout(body, 1)
        return card, body

    def _clear(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
            elif item.layout():
                self._clear(item.layout())

    # ---------- 数据 ----------
    def _sem_start(self) -> date:
        raw = self.db.get_meta("sem_start", "2026-09-07")
        return datetime.strptime(raw, "%Y-%m-%d").date()

    def reload(self):
        now = datetime.now()
        today = now.date()
        self.date_big.setText(f"{today.month}月{today.day}日 {WEEK_CN[today.weekday()]}")
        from app.services.schedule import week_of
        wk = week_of(today, self._sem_start())
        self.date_sub.setText(f"第 {wk} 教学周 · {today.year}年")

        self._build_courses(today)
        self._build_ring_and_todos(today)
        self._build_memos(now)

    def _build_courses(self, today):
        self._clear(self.courses_body)
        courses = [dict(r) for r in self.db.query("SELECT * FROM courses")]
        items = classes_on(courses, today, self._sem_start())
        if not items:
            self.courses_body.addWidget(empty_state("今天没有排课"))
            return
        for c in items:
            row = QFrame(); row.setObjectName("HomeCourseRow")
            h = QHBoxLayout(row); h.setContentsMargins(0, 3, 0, 3); h.setSpacing(10)
            pr = self.db.query_one(
                "SELECT start_time,end_time FROM periods WHERE period=?", (c["ps"],)
            )
            time_txt = f"{pr['start_time']}-{pr['end_time']}" if pr else f"第{c['ps']}节"
            tag = QLabel(f"第{c['ps']}" + (f"-{c['pe']}" if c["pe"] != c["ps"] else "") + "节")
            tag.setObjectName("CoursePeriod")
            info = QVBoxLayout(); info.setSpacing(2)
            name = QLabel(c["name"])
            name.setStyleSheet("font-size:14px;font-weight:600;color:#1F2A2E;")
            meta = QLabel(f"{time_txt}  {c['room'] or ''}  {c['teacher'] or ''}")
            meta.setStyleSheet("font-size:12px;color:#6B756F;")
            info.addWidget(name); info.addWidget(meta)
            h.addWidget(tag); h.addLayout(info, 1)
            self.courses_body.addWidget(row)
        self.courses_body.addStretch(1)

    def _todos(self, today):
        return self.db.query(
            "SELECT * FROM todos WHERE owner_date=? ORDER BY star DESC,done,sort,id",
            (today.isoformat(),),
        )

    def _build_ring_and_todos(self, today):
        self._clear(self.ring_body)
        self._clear(self.todos_body)
        rows = self._todos(today)
        total = len(rows)
        done = sum(1 for r in rows if r["done"])
        pct = done * 100 // total if total else 0
        rc = QVBoxLayout(); rc.setAlignment(Qt.AlignCenter); rc.setSpacing(8)
        rc.addWidget(self.ring, 0, Qt.AlignCenter)
        self.ring.set_percent(pct)
        self.ring_counts.setText(f"已完成 {done}/{total} · 未完成 {total - done}")
        rc.addWidget(self.ring_counts, 0, Qt.AlignCenter)
        postpone = QPushButton("未完成顺延明天"); postpone.setObjectName("Ghost")
        postpone.clicked.connect(self.postpone)
        rc.addWidget(postpone, 0, Qt.AlignCenter)
        self.ring_body.addLayout(rc)

        quick = QLineEdit()
        quick.setObjectName("HomeQuickAdd")
        quick.setPlaceholderText("添加今日待办，回车保存")
        quick.returnPressed.connect(lambda: self.add_todo(quick))
        self.todos_body.addWidget(quick)

        if not rows:
            self.todos_body.addWidget(empty_state("今天还没有待办"))
        for r in rows:
            self.todos_body.addWidget(self._todo_row(r))
        self.todos_body.addStretch(1)

    def _todo_row(self, r) -> QFrame:
        row = QFrame()
        h = QHBoxLayout(row); h.setContentsMargins(2, 2, 2, 2); h.setSpacing(8)
        cb = QCheckBox(); cb.setChecked(bool(r["done"]))
        cb.stateChanged.connect(lambda _s, rid=r["id"]: self.toggle(rid))
        lab = QLabel(("★ " if r["star"] else "") + r["content"])
        if r["done"]:
            lab.setStyleSheet("color:#98A09B;text-decoration:line-through;")
        h.addWidget(cb); h.addWidget(lab, 1)
        return row

    def _build_memos(self, now):
        self._clear(self.memos_body)
        cutoff = (now + timedelta(days=3)).replace(hour=23, minute=59)
        rows = self.db.query(
            "SELECT * FROM memos WHERE due IS NOT NULL AND due <= ?"
            " ORDER BY due",
            (cutoff.strftime("%Y-%m-%d %H:%M"),),
        )
        if not rows:
            self.memos_body.addWidget(empty_state("没有临期备忘"))
            return
        for m in rows:
            color, text = due_category(m["due"])
            btn = QPushButton()
            btn.setObjectName("UrgentItem")
            btn.setCursor(Qt.PointingHandCursor)
            h = QHBoxLayout(btn); h.setContentsMargins(2, 2, 2, 2)
            title = QLabel(m["title"] or "(无标题)"); title.setObjectName("UrgentTitle")
            badge = QLabel(text); badge.setObjectName("UrgentBadge")
            badge.setStyleSheet(f"color:{color};font-weight:600;")
            h.addWidget(title, 1); h.addWidget(badge)
            btn.clicked.connect(lambda: self.open_memo(m["id"]))
            self.memos_body.addWidget(btn)
        self.memos_body.addStretch(1)

    # ---------- 操作 ----------
    def add_todo(self, edit: QLineEdit):
        content = edit.text().strip()
        if not content:
            return
        today = date.today().isoformat()
        nxt = self.db.query_one(
            "SELECT COALESCE(MAX(sort)+1,0) AS s FROM todos WHERE owner_date=?", (today,)
        )["s"]
        self.db.execute(
            "INSERT INTO todos(content,priority,done,star,owner_date,sort)"
            " VALUES(?,?,0,0,?,?)",
            (content, "mid", today, nxt),
        )
        edit.clear()
        self.win.today_view.reload()
        self.reload()
        self.win.update_counts()

    def toggle(self, rid):
        r = self.db.query_one("SELECT done FROM todos WHERE id=?", (rid,))
        self.db.execute(
            "UPDATE todos SET done=?,updated_at=datetime('now','localtime') WHERE id=?",
            (0 if r["done"] else 1, rid),
        )
        self.win.today_view.reload()
        self.reload()
        self.win.update_counts()

    def postpone(self):
        self.win.today_view.postpone()
        self.reload()

    def quick_todo(self):
        self.win.navigate("today")
        self.win.today_view.input.setFocus()

    def quick_memo(self):
        self.win.memos_view.new_memo()
        self.win.navigate("memos")

    def open_memo(self, mid):
        self.win.memos_view.select(mid)
        self.win.navigate("memos")
