"""课程表周次计算与按日筛选（纯函数，便于测试）。"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable


def _day_start(x: date) -> date:
    return date(x.year, x.month, x.day)


def week_of(target: date, sem_start: date) -> int:
    """返回 target 是第几教学周（周一为一周开始；第 1 周从 sem_start 周一起）。"""
    days = (_day_start(target) - _day_start(sem_start)).days
    return days // 7 + 1


def monday_of_week(week: int, sem_start: date) -> date:
    return _day_start(sem_start) + timedelta(days=7 * (week - 1))


def week_date_range(week: int, sem_start: date) -> tuple[date, date]:
    mon = monday_of_week(week, sem_start)
    return mon, mon + timedelta(days=6)


def courses_in_week(courses: Iterable[dict[str, Any]], week: int) -> list[dict[str, Any]]:
    return [c for c in courses if c["ws"] <= week <= c["we"]]


def classes_on(
    courses: Iterable[dict[str, Any]], target: date, sem_start: date
) -> list[dict[str, Any]]:
    """返回 target 当天的课（isoweekday：周一=1…周日=7），并按节次排序。"""
    day = target.isoweekday()
    week = week_of(target, sem_start)
    result = [
        c
        for c in courses
        if c["day"] == day and c["ws"] <= week <= c["we"]
    ]
    return sorted(result, key=lambda c: c["ps"])
