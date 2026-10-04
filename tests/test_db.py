"""M1 数据库层测试：建表、默认作息、各表 CRUD、外键级联与重开持久化。"""
import pytest

from app.db import DB


@pytest.fixture()
def db(tmp_path):
    d = DB(tmp_path / "studydesk.db")
    yield d
    d.close()


def test_tables_created(db):
    assert {
        "meta", "periods", "courses", "todos", "goals", "milestones", "memos"
    }.issubset(db.tables())


def test_default_periods_seeded(db):
    rows = db.query("SELECT * FROM periods ORDER BY period")
    assert len(rows) == 12
    assert (rows[0]["start_time"], rows[0]["end_time"]) == ("08:00", "08:45")
    assert rows[11]["period"] == 12


def test_seed_periods_idempotent(tmp_path):
    path = tmp_path / "p.db"
    DB(path).close()
    d = DB(path)
    assert len(d.query("SELECT * FROM periods")) == 12
    d.close()


def test_courses_crud(db):
    cid = db.execute(
        "INSERT INTO courses(name,code,day,ps,pe,ws,we,room,teacher)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        ("马克思主义基本原理", "030", 4, 1, 2, 1, 10, "敬亭学堂303", "阳银银"),
    )
    row = db.query_one("SELECT * FROM courses WHERE id=?", (cid,))
    assert row["name"] == "马克思主义基本原理" and row["day"] == 4
    db.execute("UPDATE courses SET room=? WHERE id=?", ("敬亭学堂305", cid))
    assert db.query_one("SELECT room FROM courses WHERE id=?", (cid,))["room"] == "敬亭学堂305"
    db.execute("DELETE FROM courses WHERE id=?", (cid,))
    assert db.query_one("SELECT * FROM courses WHERE id=?", (cid,)) is None


def test_todos_defaults_and_crud(db):
    tid = db.execute("INSERT INTO todos(content,owner_date) VALUES(?,?)", ("背单词 50 个", "2026-10-04"))
    row = db.query_one("SELECT * FROM todos WHERE id=?", (tid,))
    assert row["priority"] == "mid" and row["done"] == 0 and row["star"] == 0
    db.execute("UPDATE todos SET done=1 WHERE id=?", (tid,))
    assert db.query_one("SELECT done FROM todos WHERE id=?", (tid,))["done"] == 1


def test_goals_milestones_cascade(db):
    gid = db.execute(
        "INSERT INTO goals(title,start_date,end_date) VALUES(?,?,?)",
        ("通过英语四级", "2026-10-08", "2026-12-12"),
    )
    db.executemany(
        "INSERT INTO milestones(goal_id,content,sort) VALUES(?,?,?)",
        [(gid, "背核心词", 0), (gid, "真题模考", 1)],
    )
    assert len(db.query("SELECT * FROM milestones WHERE goal_id=?", (gid,))) == 2
    db.execute("DELETE FROM goals WHERE id=?", (gid,))
    assert len(db.query("SELECT * FROM milestones WHERE goal_id=?", (gid,))) == 0


def test_memos_null_due(db):
    mid = db.execute(
        "INSERT INTO memos(title,body,due,color) VALUES(?,?,?,?)",
        ("借书", "图书馆三楼", None, "#3B7BB0"),
    )
    row = db.query_one("SELECT * FROM memos WHERE id=?", (mid,))
    assert row["due"] is None and row["color"] == "#3B7BB0"


def test_meta_get_set(db):
    assert db.get_meta("sem_start") is None
    db.set_meta("sem_start", "2026-09-07")
    assert db.get_meta("sem_start") == "2026-09-07"
    db.set_meta("sem_start", "2026-09-08")
    assert db.get_meta("sem_start") == "2026-09-08"


def test_persistence_after_reopen(tmp_path):
    path = tmp_path / "persist.db"
    d = DB(path)
    d.execute("INSERT INTO courses(name,day,ps,pe,ws,we) VALUES(?,?,?,?,?,?)", ("离散数学", 1, 7, 8, 1, 6))
    d.execute("INSERT INTO todos(content,owner_date,done) VALUES(?,?,?)", ("作业", "2026-10-04", 1))
    d.execute("INSERT INTO memos(title,body) VALUES(?,?)", ("标题", "正文"))
    d.close()

    d2 = DB(path)
    assert len(d2.query("SELECT * FROM courses")) == 1
    assert d2.query_one("SELECT content FROM todos")["content"] == "作业"
    assert d2.query_one("SELECT body FROM memos")["body"] == "正文"
    d2.close()
