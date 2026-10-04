"""M3 周次计算与按日筛选测试。"""
from datetime import date
from pathlib import Path

from app.services import schedule
from app.services.schedule_parser import parse_docx

COURSES, _ = parse_docx(Path(__file__).parent / "fixtures" / "学生课表.docx")
SEM = date(2026, 9, 7)


def test_week_of():
    assert schedule.week_of(date(2026, 9, 7), SEM) == 1
    assert schedule.week_of(date(2026, 10, 4), SEM) == 4


def test_monday_of_week():
    assert schedule.monday_of_week(1, SEM) == SEM


def test_week_date_range():
    mon, sun = schedule.week_date_range(4, SEM)
    assert mon == date(2026, 9, 28) and sun == date(2026, 10, 4)


def test_classes_thursday_week4():
    names = {c["name"] for c in schedule.classes_on(COURSES, date(2026, 10, 1), SEM)}
    assert names == {"马克思主义基本原理", "程序设计基础", "大学体育（3）"}
    assert "概率论与数理统计" not in names


def test_classes_sunday_empty():
    assert schedule.classes_on(COURSES, date(2026, 10, 4), SEM) == []


def test_courses_in_week11():
    names = {c["name"] for c in schedule.courses_in_week(COURSES, 11)}
    assert "概率论与数理统计" in names
    assert "Java程序设计" not in names
