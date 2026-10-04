"""M2 导航测试：页面数量、点击切换、角标计数。"""
import pytest
from PySide6.QtWidgets import QApplication

from app.db import DB
from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def win(qapp, tmp_path):
    d = DB(tmp_path / "nav.db")
    w = MainWindow(db=d)
    w.show()
    qapp.processEvents()
    yield w
    d.close()


def test_stack_has_five_pages(win):
    assert win.stack.count() == 5


def test_click_nav_switches(win):
    for i, (key, *_rest) in enumerate(MainWindow.VIEWS):
        win.nav_buttons[key].click()
        assert win.stack.currentIndex() == i
        assert win.nav_buttons[key].isChecked()


def test_counts_update(win):
    win.db.execute(
        "INSERT INTO todos(content,owner_date,done) VALUES(?,?,?)", ("作业", "2026-10-04", 0)
    )
    win.db.execute("INSERT INTO goals(title,status) VALUES(?,?)", ("目标", "active"))
    win.update_counts()
    assert win.count_labels["today"].text() == "1"
    assert win.count_labels["goals"].text() == "1"
    assert win.count_labels["today"].isVisible()
