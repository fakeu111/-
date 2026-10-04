"""全局配置：路径、常量与默认作息时间。"""
import os
import sys
from pathlib import Path

APP_NAME = "学习桌面"


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    """打包后数据解压目录（PyInstaller）；开发时为工程根目录。"""
    if frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def resource_path(name: str) -> Path:
    return bundle_dir() / "resources" / name


def qss_path() -> Path:
    if frozen():
        return bundle_dir() / "app" / "ui" / "style.qss"
    return Path(__file__).resolve().parent / "ui" / "style.qss"


def app_data_dir() -> Path:
    """返回本机应用数据目录并确保其存在（默认 %LOCALAPPDATA%\\学习桌面）。"""
    base = os.environ.get("LOCALAPPDATA")
    p = Path(base) / APP_NAME if base else Path.home() / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    """返回 SQLite 数据库文件路径。可用环境变量 STUDYDESK_DB 覆盖（测试用）。"""
    env = os.environ.get("STUDYDESK_DB")
    return Path(env) if env else app_data_dir() / "data.db"


# 每节课的默认上课/下课时刻（可在设置中修改）
DEFAULT_PERIODS = [
    (1, "08:00", "08:45"),
    (2, "08:55", "09:40"),
    (3, "10:00", "10:45"),
    (4, "10:55", "11:40"),
    (5, "14:00", "14:45"),
    (6, "14:55", "15:40"),
    (7, "16:00", "16:45"),
    (8, "16:55", "17:40"),
    (9, "17:55", "18:40"),
    (10, "19:30", "20:15"),
    (11, "20:25", "21:10"),
    (12, "21:20", "22:05"),
]

DAY_FULL = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
