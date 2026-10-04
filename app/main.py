"""程序入口：启动学习桌面主窗口。"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication


def load_style(app: QApplication) -> None:
    from app import config

    app.setStyleSheet(config.qss_path().read_text(encoding="utf-8"))


def create_app(argv=None) -> QApplication:
    """返回当前 QApplication；若已存在则复用，避免重复创建。新实例会加载样式。"""
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    if not QApplication.instance().styleSheet():
        load_style(app)
    return app


def main(argv=None) -> int:
    app = create_app(argv)
    from app.ui.main_window import MainWindow

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
