"""真实平台截图：窗口闪现约 3 秒，自动截图并自行退出（不依赖人工关闭）。"""
import sys
from pathlib import Path

from PySide6.QtCore import QTimer

from app.db import DB
from app.main import create_app
from app.ui.main_window import MainWindow

db_path = sys.argv[1] if len(sys.argv) > 1 else "demo_data.db"
out_dir = Path(__file__).parent

app = create_app([])
w = MainWindow(db=DB(db_path))
w.resize(1320, 840)
w.show()
w.show_view("schedule")


def grab_schedule():
    w.grab().save(str(out_dir / "_real_schedule.png"))


def to_home():
    w.show_view("home")


def grab_home():
    w.grab().save(str(out_dir / "_real_home.png"))


QTimer.singleShot(1400, grab_schedule)
QTimer.singleShot(1700, to_home)
QTimer.singleShot(2600, grab_home)
QTimer.singleShot(3200, app.quit)

app.exec()
print("real shots saved")
