"""M6 备忘录测试：排序、分类高亮、搜索、编辑保存、颜色、截止设置/清除、删除。"""
from datetime import datetime, timedelta

import pytest
from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import QApplication, QLabel

from app.db import DB
from app.ui.main_window import MainWindow
from app.ui.memos_view import due_category


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def win(qapp, tmp_path):
    d = DB(tmp_path / "memos.db")
    w = MainWindow(db=d)
    w.show()
    qapp.processEvents()
    yield w
    d.close()


def add(db, title, body="", due=None, color="#FFFFFF"):
    return db.execute(
        "INSERT INTO memos(title,body,due,color) VALUES(?,?,?,?)",
        (title, body, due, color),
    )


def item_titles(v):
    out = []
    for i in range(v.list_lay.count()):
        w = v.list_lay.itemAt(i).widget()
        if not w:
            continue
        for l in w.findChildren(QLabel):
            if l.objectName() == "MemoItemTitle":
                out.append(l.text())
    return out


def test_sort_due_first_null_last(win):
    v = win.memos_view
    now = datetime.now()
    fmt = "%Y-%m-%d %H:%M"
    add(v.db, "无截止")
    add(v.db, "以后项", due=(now + timedelta(days=10)).strftime(fmt))
    add(v.db, "逾期项", due=(now - timedelta(days=2)).strftime(fmt))
    add(v.db, "今天项", due=(now + timedelta(minutes=20)).strftime(fmt))
    v.reload()
    assert item_titles(v) == ["逾期项", "今天项", "以后项", "无截止"]


def test_due_category_colors():
    now = datetime.now()
    fmt = "%Y-%m-%d %H:%M"
    assert due_category((now - timedelta(days=1)).strftime(fmt))[0] == "#D9534F"
    assert due_category((now + timedelta(minutes=10)).strftime(fmt))[0] == "#E0A92E"
    assert due_category((now + timedelta(days=2)).strftime(fmt))[0] == "#2F8F73"
    assert due_category(None)[0] == "#98A09B"


def test_search_filters(win):
    v = win.memos_view
    add(v.db, "会议", "周三组会记录")
    add(v.db, "购物", "牛奶 鸡蛋")
    v.search.setText("组会")
    assert item_titles(v) == ["会议"]


def test_edit_saves(win):
    v = win.memos_view
    mid = add(v.db, "旧标题")
    v.current_id = mid
    v.load_editor()
    v.title_input.setText("新标题")
    v.body.setPlainText("正文内容")
    v.save_text()
    m = v.db.query_one("SELECT * FROM memos WHERE id=?", (mid,))
    assert m["title"] == "新标题" and m["body"] == "正文内容"


def test_color_save(win):
    v = win.memos_view
    mid = add(v.db, "c")
    v.current_id = mid
    v.load_editor()
    v.save_color("#F4E3A1")
    assert v.db.query_one("SELECT color FROM memos WHERE id=?", (mid,))["color"] == "#F4E3A1"


def test_due_set_and_clear(win):
    v = win.memos_view
    mid = add(v.db, "d")
    v.current_id = mid
    v.load_editor()
    v.due_enable.setChecked(True)
    v.due_date.setDate(QDate(2026, 12, 1))
    v.due_time.setTime(QTime(20, 0))
    v.save_due()
    assert v.db.query_one("SELECT due FROM memos WHERE id=?", (mid,))["due"] == "2026-12-01 20:00"
    v.clear_due()
    assert v.db.query_one("SELECT due FROM memos WHERE id=?", (mid,))["due"] is None


def test_delete(win):
    v = win.memos_view
    mid = add(v.db, "删")
    v.current_id = mid
    v.delete_memo()
    assert v.db.query_one("SELECT id FROM memos WHERE id=?", (mid,)) is None
