"""M7 首页聚合测试：今日课程、完成环、快速添加/勾选、临期备忘、跳转定位。"""
from datetime import date, datetime, timedelta

import pytest
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QLineEdit

from app.db import DB
from app.services.schedule import week_of
from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def win(qapp, tmp_path):
    d = DB(tmp_path / "home.db")
    w = MainWindow(db=d)
    w.show()
    qapp.processEvents()
    yield w
    d.close()


def labels(widget, name):
    return [l for l in widget.findChildren(QLabel) if l.objectName() == name]


def add_todo(db, content, done=0):
    return db.execute(
        "INSERT INTO todos(content,done,owner_date) VALUES(?,?,?)",
        (content, done, date.today().isoformat()),
    )


def add_memo(db, title, due):
    return db.execute(
        "INSERT INTO memos(title,body,due,color) VALUES(?,?,?,?)",
        (title, "", due, "#FFFFFF"),
    )


def test_today_courses(win):
    h = win.home_view
    sem = datetime(2026, 9, 7).date()
    today = date.today()
    wk = week_of(today, sem)
    h.db.execute(
        "INSERT INTO courses(name,day,ps,pe,ws,we,room,teacher)"
        " VALUES(?,?,?,?,?,?,?,?)",
        ("周日研讨课", today.isoweekday(), 9, 10, 1, 16, "逸夫楼", "王老师"),
    )
    h.reload()
    assert any(l.text() == "周日研讨课" for l in labels(h.courses_card, ""))


def test_ring_and_counts(win):
    h = win.home_view
    add_todo(h.db, "a"); add_todo(h.db, "b"); add_todo(h.db, "c", done=1)
    h.reload()
    assert h.ring.percent == 33
    assert h.ring_counts.text() == "已完成 1/3 · 未完成 2"


def test_quick_add(win):
    h = win.home_view
    edit = QLineEdit("背 30 个单词")
    h.add_todo(edit)
    row = h.db.query_one(
        "SELECT * FROM todos WHERE content=? AND owner_date=?",
        ("背 30 个单词", date.today().isoformat()),
    )
    assert row is not None


def test_check_on_home(win):
    h = win.home_view
    tid = add_todo(h.db, "作业")
    h.reload()
    cb = h.todos_card.findChild(QCheckBox)
    cb.setChecked(True)
    assert h.db.query_one("SELECT done FROM todos WHERE id=?", (tid,))["done"] == 1


def test_urgent_memos(win):
    h = win.home_view
    now = datetime.now()
    fmt = "%Y-%m-%d %H:%M"
    add_memo(h.db, "逾期", (now - timedelta(days=1)).strftime(fmt))
    add_memo(h.db, "今天", (now + timedelta(hours=2)).strftime(fmt))
    add_memo(h.db, "近两天", (now + timedelta(days=2)).strftime(fmt))
    add_memo(h.db, "远期", (now + timedelta(days=20)).strftime(fmt))
    h.reload()
    titles = [l.text() for l in labels(h.memos_card, "UrgentTitle")]
    assert titles == ["逾期", "今天", "近两天"]


def test_open_memo_jumps(win):
    h = win.home_view
    now = datetime.now()
    mid = add_memo(h.db, "定位我", (now + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"))
    h.open_memo(mid)
    assert win.stack.currentWidget() is win.memos_view
    assert win.memos_view.current_id == mid


def test_quick_buttons_navigate(win):
    h = win.home_view
    h.quick_todo()
    assert win.stack.currentWidget() is win.today_view
    h.quick_memo()
    assert win.stack.currentWidget() is win.memos_view
