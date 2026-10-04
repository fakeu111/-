"""备忘录视图：左侧列表+搜索，右侧编辑器；截止时间与颜色，逾期/临期高亮。"""
from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets import scroll_area

SWATCHES = ["#FFFFFF", "#F4E3A1", "#CDE7D4", "#CDE0F2", "#F2D2DC", "#DED2F0"]


def due_category(due: str | None):
    """返回 (颜色, 文案)。"""
    if not due:
        return "#98A09B", "无截止"
    d = datetime.strptime(due, "%Y-%m-%d %H:%M")
    now = datetime.now()
    if d < now:
        return "#D9534F", f"逾期 · {d.month}/{d.day} {d:%H:%M}"
    if d.date() == now.date():
        return "#E0A92E", f"今天 {d:%H:%M}"
    if d.date() <= (now + timedelta(days=3)).date():
        days = (d.date() - now.date()).days
        return "#2F8F73", f"{days}天后 · {d.month}/{d.day}"
    return "#8A948F", f"{d.month}/{d.day} {d:%H:%M}"


class MemosView(QWidget):
    def __init__(self, db, win):
        super().__init__()
        self.db = db
        self.win = win
        self.current_id: int | None = None
        self.loading = True

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)

        # ---------- 左：列表 ----------
        left = QFrame(); left.setObjectName("MemoLeft")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(10, 12, 10, 12)
        lv.setSpacing(9)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("MemoSearch")
        self.search.setPlaceholderText("搜索标题或正文")
        self.search.textChanged.connect(self.reload)
        new = QPushButton("新建"); new.setObjectName("Primary")
        new.clicked.connect(self.new_memo)
        top.addWidget(self.search, 1); top.addWidget(new)
        lv.addLayout(top)

        self.list_host = QWidget()
        self.list_lay = QVBoxLayout(self.list_host)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(2)
        lv.addWidget(scroll_area(self.list_host), 1)
        splitter.addWidget(left)

        # ---------- 右：编辑器 ----------
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(24, 16, 24, 18)
        rv.setSpacing(10)

        tool = QHBoxLayout()
        self.swatch_btns = []
        for c in SWATCHES:
            b = QPushButton()
            b.setObjectName("Swatch")
            b.setFixedSize(24, 24)
            b.setStyleSheet(
                f"background:{c};" + ("border:1px solid #D8DDDA;" if c == "#FFFFFF" else "")
            )
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _x, col=c: self.save_color(col))
            self.swatch_btns.append((b, c))
            tool.addWidget(b)
        tool.addStretch(1)

        self.due_enable = QCheckBox("截止")
        self.due_date = QDateEdit(); self.due_date.setCalendarPopup(True)
        self.due_date.setDisplayFormat("yyyy-MM-dd")
        self.due_time = QTimeEdit(); self.due_time.setDisplayFormat("HH:mm")
        for w in (self.due_date, self.due_time):
            w.setObjectName("MemoDate")
        clear = QPushButton("清除截止")
        clear.clicked.connect(self.clear_due)
        self.due_enable.toggled.connect(self.save_due)
        self.due_date.dateChanged.connect(self.save_due)
        self.due_time.timeChanged.connect(self.save_due)
        tool.addWidget(self.due_enable)
        tool.addWidget(self.due_date); tool.addWidget(self.due_time)
        tool.addWidget(clear)
        rv.addLayout(tool)

        self.title_input = QLineEdit()
        self.title_input.setObjectName("MemoTitleInput")
        self.title_input.setPlaceholderText("备忘录标题")
        self.title_input.textEdited.connect(self.save_text)
        rv.addWidget(self.title_input)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color:#E2E6E4;")
        rv.addWidget(line)

        self.body = QPlainTextEdit()
        self.body.setObjectName("MemoBody")
        self.body.setPlaceholderText("在这里写正文…")
        self.body.textChanged.connect(self.save_text)
        rv.addWidget(self.body, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        delete = QPushButton("删除此备忘录")
        delete.setStyleSheet("color:#B05852;")
        delete.clicked.connect(self.delete_memo)
        bottom.addWidget(delete)
        rv.addLayout(bottom)

        splitter.addWidget(right)
        splitter.setSizes([300, 860])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter)

        self.reload()

    # ---------- 列表 ----------
    def _rows(self):
        kw = self.search.text().strip()
        if kw:
            like = f"%{kw}%"
            return self.db.query(
                "SELECT * FROM memos WHERE title LIKE ? OR body LIKE ?"
                " ORDER BY CASE WHEN due IS NULL THEN 1 ELSE 0 END, due",
                (like, like),
            )
        return self.db.query(
            "SELECT * FROM memos ORDER BY CASE WHEN due IS NULL THEN 1 ELSE 0 END, due"
        )

    def reload(self):
        rows = self._rows()
        while self.list_lay.count():
            w = self.list_lay.takeAt(0).widget()
            if w:
                w.setParent(None)
        for m in rows:
            self.list_lay.addWidget(self._item(m))
        self.list_lay.addStretch(1)

        ids = [m["id"] for m in rows]
        if self.current_id not in ids:
            self.current_id = ids[0] if ids else None
        self.load_editor()

    def _item(self, m) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("MemoItem")
        btn.setCheckable(True)
        btn.setChecked(m["id"] == self.current_id)
        v = QVBoxLayout(btn)
        v.setContentsMargins(2, 2, 2, 2)
        v.setSpacing(3)
        title = QLabel(m["title"] or "(无标题)")
        title.setObjectName("MemoItemTitle")
        color, due_text = due_category(m["due"])
        dh = QHBoxLayout(); dh.setSpacing(6)
        dot = QFrame(); dot.setFixedSize(7, 7)
        dot.setStyleSheet(f"background:{color};border-radius:3px;")
        due = QLabel(due_text)
        due.setObjectName("MemoItemDue")
        due.setStyleSheet(f"color:{color};")
        dh.addWidget(dot); dh.addWidget(due); dh.addStretch(1)
        v.addWidget(title); v.addLayout(dh)
        btn.clicked.connect(lambda: self.select(m["id"]))
        return btn

    def select(self, mid):
        self.current_id = mid
        self.reload()

    # ---------- 编辑器 ----------
    def _memo(self):
        if self.current_id is None:
            return None
        return self.db.query_one(
            "SELECT * FROM memos WHERE id=?", (self.current_id,)
        )

    def load_editor(self):
        self.loading = True
        m = self._memo()
        enabled = m is not None
        for w in (self.title_input, self.body, self.due_date, self.due_time,
                  self.due_enable):
            w.setEnabled(enabled)
        if not m:
            self.title_input.clear(); self.body.setPlainText("")
            self.loading = False
            return

        self.title_input.setText(m["title"] or "")
        self.body.setPlainText(m["body"] or "")
        for b, c in self.swatch_btns:
            b.setChecked((m["color"] or "#FFFFFF") == c)

        if m["due"]:
            d = datetime.strptime(m["due"], "%Y-%m-%d %H:%M")
            self.due_enable.setChecked(True)
            self.due_date.setDate(QDateTime.fromString(m["due"], "yyyy-MM-dd HH:mm").date())
            self.due_time.setTime(QDateTime.fromString(m["due"], "yyyy-MM-dd HH:mm").time())
        else:
            self.due_enable.setChecked(False)
        self.loading = False

    # ---------- 保存 ----------
    def save_text(self):
        if self.loading or self.current_id is None:
            return
        self.db.execute(
            "UPDATE memos SET title=?,body=?,"
            "updated_at=datetime('now','localtime') WHERE id=?",
            (self.title_input.text(), self.body.toPlainText(), self.current_id),
        )
        self._reload_list_only()

    def save_color(self, color):
        if self.current_id is None:
            return
        self.db.execute("UPDATE memos SET color=? WHERE id=?", (color, self.current_id))
        self.load_editor()
        self._reload_list_only()

    def save_due(self, *_a):
        if self.loading or self.current_id is None:
            return
        if self.due_enable.isChecked():
            due = (
                self.due_date.date().toString("yyyy-MM-dd") + " "
                + self.due_time.time().toString("HH:mm")
            )
        else:
            due = None
        self.db.execute("UPDATE memos SET due=? WHERE id=?", (due, self.current_id))
        self._reload_list_only()
        self.win.update_counts()

    def clear_due(self):
        self.due_enable.setChecked(False)
        self.save_due()

    # ---------- 新建 / 删除 ----------
    def new_memo(self):
        now = datetime.now()
        default_due = now.replace(hour=21, minute=0, second=0, microsecond=0)
        gid = self.db.execute(
            "INSERT INTO memos(title,body,due,color) VALUES(?,?,?,?)",
            ("无标题", "", default_due.strftime("%Y-%m-%d %H:%M"), "#FFFFFF"),
        )
        self.current_id = gid
        self.reload()
        self.title_input.selectAll(); self.title_input.setFocus()
        self.win.update_counts()

    def delete_memo(self):
        if self.current_id is None:
            return
        self.db.execute("DELETE FROM memos WHERE id=?", (self.current_id,))
        self.current_id = None
        self.reload()
        self.win.update_counts()

    def _reload_list_only(self):
        rows = self._rows()
        while self.list_lay.count():
            w = self.list_lay.takeAt(0).widget()
            if w:
                w.setParent(None)
        for m in rows:
            self.list_lay.addWidget(self._item(m))
        self.list_lay.addStretch(1)
