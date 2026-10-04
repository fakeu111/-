"""M3 课表解析测试：数量、字段完整性与关键课程信息。"""
from pathlib import Path

from app.services.schedule_parser import parse_docx

FIXTURE = Path(__file__).parent / "fixtures" / "学生课表.docx"


def test_parse_counts():
    courses, remarks = parse_docx(FIXTURE)
    assert len(courses) == 25
    assert len({c["name"] for c in courses}) == 12
    assert remarks == 3


def test_required_fields_present():
    courses, _ = parse_docx(FIXTURE)
    for c in courses:
        for k in ("name", "code", "day", "ps", "pe", "ws", "we", "room", "teacher"):
            assert k in c and c[k] not in (None, "")


def test_thursday_morning_marx():
    courses, _ = parse_docx(FIXTURE)
    ma = [
        c
        for c in courses
        if c["name"] == "马克思主义基本原理" and c["day"] == 4 and c["ps"] == 1
    ]
    assert len(ma) == 1
    c = ma[0]
    assert (c["ws"], c["we"], c["room"], c["teacher"]) == (
        1, 10, "敬亭学堂303", "阳银银",
    )


def test_friday_electric_two_ranges():
    courses, _ = parse_docx(FIXTURE)
    ec = [
        c
        for c in courses
        if c["name"] == "电工与电子技术B" and c["day"] == 5 and c["ps"] == 1
    ]
    pairs = sorted((c["ws"], c["we"], c["teacher"]) for c in ec)
    assert pairs == [(10, 15, "李春华"), (16, 17, "姜兆能")]


def test_monday_discrete_two_teachers():
    courses, _ = parse_docx(FIXTURE)
    ds = sorted(
        (c for c in courses if c["name"] == "离散数学" and c["day"] == 1 and c["ps"] == 7),
        key=lambda c: c["ws"],
    )
    assert [(d["ws"], d["teacher"]) for d in ds] == [(1, "王晓华"), (7, "杨娟")]
