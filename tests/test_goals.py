"""M5 长期计划测试：进度随勾选、自动完成状态、加到今日、状态筛选、编辑保留、删除级联。"""
import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QCheckBox

from app.db import DB
from app.ui.dialogs.goal_dialog import GoalDialog
from app.ui.goals_view import GoalCard, GoalsView, recompute_status
from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def win(qapp, tmp_path):
    d = DB(tmp_path / "goals.db")
    w = MainWindow(db=d)
    w.show()
    qapp.processEvents()
    yield w
    d.close()


def make_goal(db, title, lines, s="2026-09-01", e="2026-12-31"):
    dlg = GoalDialog(db, None)
    dlg.title.setText(title)
    dlg.start.setDate(QDate.fromString(s, "yyyy-MM-dd"))
    dlg.end.setDate(QDate.fromString(e, "yyyy-MM-dd"))
    dlg.milestones.setPlainText("\n".join(lines))
    dlg._save()


def cards(v) -> list[GoalCard]:
    return v.findChildren(GoalCard)


def test_progress_updates_on_check(win):
    gv = win.goals_view
    make_goal(gv.db, "考研", ["数学", "英语", "专业课"])
    gv.reload()
    assert cards(gv)[0].pct_label.text() == "0/3 · 0%"

    cbs = cards(gv)[0].findChildren(QCheckBox)
    cbs[0].setChecked(True)  # 触发勾选 → 重建
    assert cards(gv)[0].pct_label.text() == "1/3 · 33%"


def test_all_done_sets_status(win):
    gv = win.goals_view
    make_goal(gv.db, "证书", ["报名", "考试"])
    gv.reload()
    gid = cards(gv)[0].goal["id"]
    gv.db.execute("UPDATE milestones SET done=1 WHERE goal_id=?", (gid,))
    recompute_status(gv.db, gid)
    gv.reload()
    c = cards(gv)[0]
    assert c.pct_label.text() == "2/2 · 100%"
    assert c.status_combo.currentData() == "done"


def test_add_next_to_today(win):
    gv = win.goals_view
    make_goal(gv.db, "项目", ["立项", "中期", "结题"])
    gv.reload()
    cards(gv)[0].add_to_today()
    r = gv.db.query_one(
        "SELECT content FROM todos WHERE content LIKE ?", ("%【项目】%",)
    )
    assert r is not None and r["content"] == "【项目】立项"


def test_status_filter(win):
    gv = win.goals_view
    make_goal(gv.db, "保留", ["a"])
    make_goal(gv.db, "放弃", ["b"])
    gv.reload()
    drop_card = next(c for c in cards(gv) if c.goal["title"] == "放弃")
    drop_card.status_combo.setCurrentIndex(3)  # 已放弃
    gv.set_filter("dropped")
    assert len(cards(gv)) == 1 and cards(gv)[0].goal["title"] == "放弃"
    gv.set_filter("active")
    assert {c.goal["title"] for c in cards(gv)} == {"保留"}


def test_edit_preserves_milestone_done(win):
    gv = win.goals_view
    make_goal(gv.db, "比赛", ["初赛", "决赛"])
    gv.reload()
    goal = cards(gv)[0].goal
    gid = goal["id"]
    gv.db.execute(
        "UPDATE milestones SET done=1 WHERE goal_id=? AND content=?", (gid, "初赛")
    )
    dlg = GoalDialog(gv.db, goal)
    dlg.title.setText("比赛改")
    dlg._save()
    gv.reload()
    done = gv.db.query_one(
        "SELECT COUNT(*) c FROM milestones WHERE goal_id=? AND done=1", (gid,)
    )["c"]
    total = gv.db.query_one(
        "SELECT COUNT(*) c FROM milestones WHERE goal_id=?", (gid,)
    )["c"]
    assert (done, total) == (1, 2)


def test_delete_goal_cascades(win):
    gv = win.goals_view
    make_goal(gv.db, "待删", ["x", "y"])
    gv.reload()
    gid = cards(gv)[0].goal["id"]
    cards(gv)[0].delete()
    assert gv.db.query_one("SELECT id FROM goals WHERE id=?", (gid,)) is None
    assert gv.db.query_one(
        "SELECT COUNT(*) c FROM milestones WHERE goal_id=?", (gid,)
    )["c"] == 0
