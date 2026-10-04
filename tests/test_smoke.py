"""M0 冒烟测试：应用入口能启动窗口并正常退出。"""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.main import main


def test_app_launches_and_quits():
    app = QApplication.instance() or QApplication([])
    # 在事件循环启动后 150ms 自动退出
    QTimer.singleShot(150, app.quit)
    rc = main()
    assert rc == 0
