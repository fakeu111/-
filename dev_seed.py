"""开发辅助：用样例课表生成一份演示数据库（供界面核对，不影响正式库）。"""
import sys
from pathlib import Path

from app.db import DB
from app.services.schedule_parser import parse_docx

out = sys.argv[1] if len(sys.argv) > 1 else "demo_data.db"
src = Path(__file__).parent / "tests" / "fixtures" / "学生课表.docx"

db = DB(out)
courses, remarks = parse_docx(src)
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
print(f"seeded {len(courses)} sessions, {remarks} remark courses -> {out}")
