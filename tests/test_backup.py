"""M8 备份与恢复测试：备份含最新数据，恢复后还原到备份时状态。"""
import sqlite3
from datetime import date

from app.db import DB
from app.services.backup import backup_to, restore_from


def test_backup_file_contains_data(tmp_path):
    d = DB(tmp_path / "a.db")
    d.execute(
        "INSERT INTO todos(content,owner_date) VALUES(?,?)",
        ("备份前任务", date.today().isoformat()),
    )
    dest = tmp_path / "bk.db"
    backup_to(d, dest)
    assert dest.exists()
    conn = sqlite3.connect(dest)
    n = conn.execute("SELECT COUNT(*) FROM todos WHERE content='备份前任务'").fetchone()[0]
    conn.close()
    assert n == 1
    d.close()


def test_restore_reverts_changes(tmp_path):
    d = DB(tmp_path / "b.db")
    d.execute(
        "INSERT INTO todos(content,owner_date) VALUES(?,?)",
        ("原始任务", date.today().isoformat()),
    )
    dest = tmp_path / "bk.db"
    backup_to(d, dest)

    d.execute(
        "INSERT INTO todos(content,owner_date) VALUES(?,?)",
        ("备份后新增", date.today().isoformat()),
    )
    assert d.query_one("SELECT id FROM todos WHERE content='备份后新增'") is not None

    restore_from(d, dest)
    assert d.query_one("SELECT id FROM todos WHERE content='原始任务'") is not None
    assert d.query_one("SELECT id FROM todos WHERE content='备份后新增'") is None
    d.close()


def test_backup_is_consistent_after_many_writes(tmp_path):
    d = DB(tmp_path / "c.db")
    for i in range(5):
        d.execute("INSERT INTO goals(title) VALUES(?)", (f"目标{i}",))
    dest = tmp_path / "bk.db"
    backup_to(d, dest)
    conn = sqlite3.connect(dest)
    n = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
    conn.close()
    assert n == 5
    d.close()
