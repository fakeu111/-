"""M4 今日计划测试：添加、完成度、优先级、重点、内联编辑、顺延、日期切换、删除。"""
from datetime import date

import pytest
from PySide6.QtWidgets import QApplication, QLineEdit

from app.db import DB
from app.ui.main_window import MainWindow
from app.ui.today_view import TodoRow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def win(qapp, tmp_path):
    d = DB(tmp_path / "today.db")
    w = MainWindow(db=d)
    w.show()
    qapp.processEvents()
    yield w
    d.close()


def _row(v, text):
    for r in v.findChildren(TodoRow):
        if r.r["content"] == text:
            return r
    raise AssertionError(f"row {text} not found")


def _add(v, text, pri_idx=1):
    v.input.setText(text)
    v.pri_combo.setCurrentIndex(pri_idx)
    v.add()


def test_add_shows_and_priority(win):
    v = win.today_view
    _add(v, "作业A", 0)
    row = _row(v, "作业A")
    assert row.r["priority"] == "high"
    assert "0 / 1" in v.stat_big.text()


def test_complete_updates_progress(win):
    v = win.today_view
    _add(v, "B"); _add(v, "C")
    _row(v, "B").check.setChecked(True)
    assert "1 / 2" in v.stat_big.text()
    assert v.bar.value() == 50


def test_cycle_priority_and_star(win):
    v = win.today_view
    _add(v, "D")
    _row(v, "D").dot.click()
    assert v.db.query_one("SELECT priority FROM todos WHERE content=?", ("D",))["priority"] == "low"
    _row(v, "D").star.click()
    assert v.db.query_one("SELECT star FROM todos WHERE content=?", ("D",))["star"] == 1


def test_inline_edit(win):
    v = win.today_view
    _add(v, "E")
    row = _row(v, "E")
    row.inline_edit()
    ed = row.findChildren(QLineEdit)[0]
    ed.setText("改后的E")
    ed.returnPressed.emit()
    assert v.db.query_one("SELECT content FROM todos WHERE content=?", ("改后的E",)) is not None


def test_delete(win):
    v = win.today_view
    _add(v, "X")
    _row(v, "X").delete()
    assert v.db.query_one("SELECT id FROM todos WHERE content=?", ("X",)) is None


def test_postpone_unfinished(win):
    v = win.today_view
    v.view_date = date(2026, 10, 4)
    v.db.execute(
        "INSERT INTO todos(content,owner_date,done) VALUES(?,?,?)",
        ("顺延项", "2026-10-04", 0),
    )
    v.reload()
    v.postpone()
    r = v.db.query_one("SELECT owner_date FROM todos WHERE content=?", ("顺延项",))
    assert r["owner_date"] == "2026-10-05"
    left = v.db.query_one(
        "SELECT COUNT(*) c FROM todos WHERE owner_date=? AND done=0",
        ("2026-10-04",),
    )["c"]
    assert left == 0


def test_date_navigation(win):
    v = win.today_view
    v.view_date = date(2026, 10, 4)
    v.shift(1)
    assert v.view_date == date(2026, 10, 5)
    v.back_today()
    assert v.view_date == date.today()
