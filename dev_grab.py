"""开发辅助：在 offscreen 下渲染主窗口并截图，用于核对界面（不弹窗、不阻塞）。"""
import sys
from pathlib import Path

from app.db import DB
from app.main import create_app
from app.ui.main_window import MainWindow

db_path = sys.argv[1] if len(sys.argv) > 1 else "demo_data.db"
out_dir = Path(__file__).parent

app = create_app([])
w = MainWindow(db=DB(db_path))
w.resize(1320, 840)
w.show()


def pump(n=12):
    for _ in range(n):
        app.processEvents()


pump()
w.show_view("schedule")
pump(15)
w.grab().save(str(out_dir / "_shot_schedule.png"))

w.show_view("home")
pump(10)
w.grab().save(str(out_dir / "_shot_home.png"))
print("shots saved")
