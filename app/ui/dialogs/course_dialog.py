"""课程详情 / 编辑 / 新增对话框。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

DAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


class CourseDialog(QDialog):
    def __init__(self, db, course=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.course = course
        self.setWindowTitle("课程详情" if course else "新增课程")
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(9)

        self.name = QLineEdit(course["name"] if course else "")
        self.code = QLineEdit(course["code"] if course else "")
        self.day = QComboBox()
        self.day.addItems(DAYS)
        if course:
            self.day.setCurrentIndex(course["day"] - 1)

        self.ps = QSpinBox(); self.ps.setRange(1, 12)
        self.pe = QSpinBox(); self.pe.setRange(1, 12)
        self.ws = QSpinBox(); self.ws.setRange(1, 30)
        self.we = QSpinBox(); self.we.setRange(1, 30)
        if course:
            self.ps.setValue(course["ps"]); self.pe.setValue(course["pe"])
            self.ws.setValue(course["ws"]); self.we.setValue(course["we"])
        else:
            self.ps.setValue(1); self.pe.setValue(2)
            self.ws.setValue(1); self.we.setValue(18)

        self.room = QLineEdit(course["room"] if course else "")
        self.teacher = QLineEdit(course["teacher"] if course else "")

        form.addRow("课程名称", self.name)
        form.addRow("课程/班号", self.code)
        form.addRow("星期", self.day)
        form.addRow("起始节", self.ps)
        form.addRow("结束节", self.pe)
        form.addRow("起始周", self.ws)
        form.addRow("结束周", self.we)
        form.addRow("教室", self.room)
        form.addRow("老师", self.teacher)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if course:
            del_btn = QPushButton("删除该安排")
            del_btn.clicked.connect(self._delete)
            buttons.addButton(del_btn, QDialogButtonBox.ActionRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _params(self):
        return (
            self.name.text().strip(),
            self.code.text().strip(),
            self.day.currentIndex() + 1,
            self.ps.value(),
            self.pe.value(),
            self.ws.value(),
            self.we.value(),
            self.room.text().strip(),
            self.teacher.text().strip(),
        )

    def _save(self):
        if not self.name.text().strip():
            return
        p = self._params()
        if self.course:
            self.db.execute(
                "UPDATE courses SET name=?,code=?,day=?,ps=?,pe=?,ws=?,we=?,"
                "room=?,teacher=?,updated_at=datetime('now','localtime') WHERE id=?",
                p + (self.course["id"],),
            )
        else:
            self.db.execute(
                "INSERT INTO courses(name,code,day,ps,pe,ws,we,room,teacher)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                p,
            )
        self.accept()

    def _delete(self):
        self.db.execute("DELETE FROM courses WHERE id=?", (self.course["id"],))
        self.accept()
