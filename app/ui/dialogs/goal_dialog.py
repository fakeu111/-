"""长期计划 新建/编辑 对话框：标题、起止日期、里程碑（每行一条）。"""
from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class GoalDialog(QDialog):
    def __init__(self, db, goal=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.goal = goal
        self.setWindowTitle("编辑长期计划" if goal else "新建长期计划")
        self.setMinimumSize(440, 460)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.title = QLineEdit(goal["title"] if goal else "")
        form.addRow("计划标题", self.title)

        self.start = QDateEdit()
        self.end = QDateEdit()
        for w in (self.start, self.end):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
        if goal:
            self.start.setDate(QDate.fromString(goal["start_date"], "yyyy-MM-dd"))
            self.end.setDate(QDate.fromString(goal["end_date"], "yyyy-MM-dd"))
        else:
            self.start.setDate(QDate.currentDate())
            self.end.setDate(QDate.currentDate().addDays(30))
        form.addRow("开始日期", self.start)
        form.addRow("目标完成日期", self.end)
        root.addLayout(form)

        self.milestones = QPlainTextEdit()
        self.milestones.setPlaceholderText("里程碑，每行一条，例如：\n完成开题报告\n写完第三章")
        if goal:
            ms = db.query(
                "SELECT content FROM milestones WHERE goal_id=? ORDER BY sort",
                (goal["id"],),
            )
            self.milestones.setPlainText("\n".join(m["content"] for m in ms))
        root.addWidget(self.milestones, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _lines(self):
        return [
            ln.strip()
            for ln in self.milestones.toPlainText().splitlines()
            if ln.strip()
        ]

    def _save(self):
        title = self.title.text().strip()
        if not title:
            return
        s = self.start.date().toString("yyyy-MM-dd")
        e = self.end.date().toString("yyyy-MM-dd")
        lines = self._lines()

        if self.goal:
            gid = self.goal["id"]
            self.db.execute(
                "UPDATE goals SET title=?,start_date=?,end_date=?,"
                "updated_at=datetime('now','localtime') WHERE id=?",
                (title, s, e, gid),
            )
            existing = {
                m["content"]: m["id"]
                for m in self.db.query(
                    "SELECT id,content FROM milestones WHERE goal_id=?", (gid,)
                )
            }
            keep = set()
            for i, line in enumerate(lines):
                if line in existing:
                    mid = existing[line]
                    self.db.execute(
                        "UPDATE milestones SET sort=? WHERE id=?", (i, mid)
                    )
                    keep.add(mid)
                else:
                    self.db.execute(
                        "INSERT INTO milestones(goal_id,content,done,sort)"
                        " VALUES(?,?,0,?)", (gid, line, i)
                    )
            for cid in set(existing.values()) - keep:
                self.db.execute("DELETE FROM milestones WHERE id=?", (cid,))
        else:
            gid = self.db.execute(
                "INSERT INTO goals(title,start_date,end_date) VALUES(?,?,?)",
                (title, s, e),
            )
            for i, line in enumerate(lines):
                self.db.execute(
                    "INSERT INTO milestones(goal_id,content,done,sort)"
                    " VALUES(?,?,0,?)", (gid, line, i)
                )
        self.accept()
