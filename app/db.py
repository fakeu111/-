"""SQLite 数据访问层：连接、建表、默认数据与通用增删改查。"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

from app import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS periods(
    period INTEGER PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS courses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT,
    day INTEGER,
    ps INTEGER,
    pe INTEGER,
    ws INTEGER,
    we INTEGER,
    room TEXT,
    teacher TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS todos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    priority TEXT DEFAULT 'mid',
    done INTEGER DEFAULT 0,
    star INTEGER DEFAULT 0,
    owner_date TEXT,
    sort INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS goals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    status TEXT DEFAULT 'active',
    sort INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS milestones(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    done INTEGER DEFAULT 0,
    sort INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS memos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    body TEXT,
    due TEXT,
    color TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_milestones_goal ON milestones(goal_id);
CREATE INDEX IF NOT EXISTS idx_todos_owner ON todos(owner_date);
CREATE INDEX IF NOT EXISTS idx_courses_day ON courses(day);
CREATE INDEX IF NOT EXISTS idx_memos_due ON memos(due);
"""


class DB:
    """单库连接封装，写操作立即提交。"""

    def __init__(self, path: str | Path | None = None):
        self.path = str(path) if path is not None else str(config.db_path())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        try:
            self.conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:
            pass
        self.init_schema()

    # ---------- 结构与初始化 ----------
    def init_schema(self) -> None:
        with self.conn:
            self.conn.executescript(_SCHEMA)
            self._seed_periods()

    def _seed_periods(self) -> None:
        count = self.conn.execute("SELECT COUNT(*) FROM periods").fetchone()[0]
        if count:
            return
        self.conn.executemany(
            "INSERT INTO periods(period,start_time,end_time) VALUES(?,?,?)",
            config.DEFAULT_PERIODS,
        )

    # ---------- 通用查询 ----------
    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, params).fetchone()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with self.conn:
            cur = self.conn.execute(sql, params)
            return cur.lastrowid

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> None:
        with self.conn:
            self.conn.executemany(sql, params)

    # ---------- meta ----------
    def get_meta(self, key: str, default: str | None = None) -> str | None:
        row = self.query_one("SELECT value FROM meta WHERE key=?", (key,))
        return row["value"] if row else default

    def set_meta(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )

    def tables(self) -> set[str]:
        rows = self.query("SELECT name FROM sqlite_master WHERE type='table'")
        return {r["name"] for r in rows}

    def reopen(self) -> None:
        """关闭并重新打开连接（恢复备份后使用）。"""
        try:
            self.conn.close()
        except sqlite3.Error:
            pass
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        try:
            self.conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:
            pass
        self.init_schema()

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()
