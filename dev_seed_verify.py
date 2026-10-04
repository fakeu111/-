"""为 exe 持久化验证预置/核对数据。
用法：
  python dev_seed_verify.py <db> seed
  python dev_seed_verify.py <db> check
"""
import sys
from datetime import date, datetime, timedelta

from app.db import DB


def seed(path):
    d = DB(path)
    d.set_meta("sem_start", "2026-09-07")
    d.execute(
        "INSERT INTO todos(content,owner_date) VALUES(?,?)",
        ("验证待办", date.today().isoformat()),
    )
    gid = d.execute("INSERT INTO goals(title,status) VALUES(?,?)", ("验证目标", "active"))
    d.execute("INSERT INTO milestones(goal_id,content) VALUES(?,?)", (gid, "验证里程碑"))
    due = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    d.execute("INSERT INTO memos(title,body,due,color) VALUES(?,?,?,?)",
              ("验证备忘", "正文", due, "#CDE7D4"))
    d.close()
    print("seeded")


def check(path):
    d = DB(path)
    t = d.query_one("SELECT id FROM todos WHERE content='验证待办'")
    g = d.query_one("SELECT id FROM goals WHERE title='验证目标'")
    ms = d.query_one("SELECT id FROM milestones WHERE content='验证里程碑'")
    m = d.query_one("SELECT id FROM memos WHERE title='验证备忘'")
    d.close()
    ok = all([t, g, ms, m])
    print("PERSIST_OK" if ok else "PERSIST_FAIL")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    mode = sys.argv[2]
    (seed if mode == "seed" else check)(sys.argv[1])
