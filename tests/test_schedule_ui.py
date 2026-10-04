"""M3 界面测试：周网格渲染、周导航、课程增删、设置保存、未配置横幅。"""
from pathlib import Path

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QLabel

from app.db import DB
from app.services.schedule_parser import parse_docx
from app.ui.dialogs.course_dialog import CourseDialog
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog

FIXTURE = Path(__file__).parent / "fixtures" / "学生课表.docx"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _seed(db):
    courses, _ = parse_docx(FIXTURE)
    db.execute("DELETE FROM courses")
    db.executemany(
        "INSERT INTO courses(name,code,day,ps,pe,ws,we,room,teacher)"
        " VALUES(:name,:code,:day,:ps,:pe,:ws,:we,:room,:teacher)",
        [
            {
                "name": c["name"], "code": c["code"], "day": c["day"],
                "ps": c["ps"], "pe": c["pe"], "ws": c["ws"], "we": c["we"],
                "room": c["room"], "teacher": c["teacher"],
            }
            for c in courses
        ],
    )
    db.set_meta("sem_start", "2026-09-07")


@pytest.fixture()
def win(qapp, tmp_path):
    d = DB(tmp_path / "ui.db")
    _seed(d)
    w = MainWindow(db=d)
    w.show()
    qapp.processEvents()
    yield w
    d.close()


def test_week4_thursday_cell_has_marx(win):
    sv = win.schedule_view
    sv.week = 4
    sv.fill()
    cell = sv.table.cellWidget(0, 5)  # 第1节、星期四(col=5)
    assert cell is not None
    names = [
        l.text() for l in cell.findChildren(QLabel) if l.objectName() == "SesName"
    ]
    assert "马克思主义基本原理" in names


def test_week_navigation(win):
    sv = win.schedule_view
    sv.week = 4
    sv.shift_week(1)
    assert sv.week == 5 and "第 5 周" in sv.week_label.text()
    sv.shift_week(-2)
    assert sv.week == 3


def test_course_add_and_delete(win):
    d = win.db
    dlg = CourseDialog(d)
    dlg.name.setText("测试课")
    dlg.ps.setValue(3); dlg.pe.setValue(4)
    dlg.ws.setValue(1); dlg.we.setValue(8)
    dlg.room.setText("教室"); dlg.teacher.setText("老师")
    dlg._save()
    row = d.query_one("SELECT * FROM courses WHERE name=?", ("测试课",))
    assert row is not None and row["day"] == 1

    CourseDialog(d, row)._delete()
    assert d.query_one("SELECT * FROM courses WHERE name=?", ("测试课",)) is None


def test_settings_saves_sem(win):
    dlg = SettingsDialog(win.db)
    dlg.sem_edit.setDate(QDate(2026, 9, 7))
    dlg._save()
    assert win.db.get_meta("sem_start") == "2026-09-07"


def test_banner_when_sem_missing(qapp, tmp_path):
    d = DB(tmp_path / "nosem.db")
    w = MainWindow(db=d)
    w.show()
    qapp.processEvents()
    assert not w.schedule_view.banner.isHidden()
    d.close()
