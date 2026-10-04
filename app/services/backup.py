"""本地数据库备份与恢复：检查点后复制文件；恢复时关闭连接、清理 WAL、重连。"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path


def backup_to(db, dest) -> str:
    db.commit()
    try:
        db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.DatabaseError:
        pass
    shutil.copy2(db.path, dest)
    return str(dest)


def restore_from(db, src) -> None:
    db.conn.close()
    for ext in ("-wal", "-shm"):
        p = Path(db.path + ext)
        if p.exists():
            p.unlink()
    shutil.copy2(src, db.path)
    db.reopen()
