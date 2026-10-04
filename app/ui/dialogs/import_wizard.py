"""导入 Word 课表的三步向导：选择文件 → 核对预览 → 完成。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QDialog,
    QHBoxLayout,
    QMessageBox,
)

from app.services.schedule_parser import parse_docx

DAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


class ImportWizard(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.file_path: str | None = None
        self.courses: list = []
        self.remarks = 0
        self.setWindowTitle("导入 Word 课表")
        self.setMinimumSize(520, 460)

        root = QVBoxLayout(self)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page1())
        self.stack.addWidget(self._page2())
        self.stack.addWidget(self._page3())
        root.addWidget(self.stack)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("上一步")
        self.next_btn = QPushButton("开始解析")
        self.cancel_btn = QPushButton("取消")
        nav.addWidget(self.back_btn)
        nav.addStretch(1)
        nav.addWidget(self.cancel_btn)
        nav.addWidget(self.next_btn)
        root.addLayout(nav)

        self.back_btn.clicked.connect(self._back)
        self.next_btn.clicked.connect(self._next)
        self.cancel_btn.clicked.connect(self.reject)
        self._update_nav()

    # ---------- 三个页面 ----------
    def _page1(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("选择从教务系统导出的课表 Word（.docx）："))
        pick = QPushButton("浏览…")
        pick.setMaximumWidth(120)
        pick.clicked.connect(self._pick_file)
        lay.addWidget(pick)
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet("color:#828C88;")
        lay.addWidget(self.file_label)
        hint = QLabel("解析完全在本机进行，文件不会被上传。")
        hint.setStyleSheet("color:#828C88;font-size:12px;")
        lay.addWidget(hint)
        lay.addStretch(1)
        return w

    def _page2(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.summary = QLabel()
        lay.addWidget(self.summary)
        self.sample = QListWidget()
        lay.addWidget(self.sample, 1)
        self.mode_over = QRadioButton("覆盖当前课表（推荐）")
        self.mode_merge = QRadioButton("与现有课表合并")
        self.mode_over.setChecked(True)
        lay.addWidget(self.mode_over)
        lay.addWidget(self.mode_merge)
        return w

    def _page3(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.done_label = QLabel()
        self.done_label.setStyleSheet("font-size:15px;")
        lay.addWidget(self.done_label)
        lay.addStretch(1)
        return w

    # ---------- 动作 ----------
    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择课表 Word", "", "Word 文档 (*.docx)"
        )
        if path:
            self.file_path = path
            self.file_label.setText(path)
            self.file_label.setStyleSheet("color:#1F2A2E;")
            self._update_nav()

    def _back(self):
        if self.stack.currentIndex() > 0:
            self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
            self._update_nav()

    def _next(self):
        i = self.stack.currentIndex()
        if i == 0:
            if not self.file_path:
                QMessageBox.warning(self, "提示", "请先选择课表文件。")
                return
            try:
                self.courses, self.remarks = parse_docx(self.file_path)
            except Exception as e:  # 解析失败：可读提示，不继续
                QMessageBox.warning(self, "解析失败", f"无法识别该文件：\n{e}")
                return
            self._fill_preview()
            self.stack.setCurrentIndex(1)
        elif i == 1:
            self._write_courses()
            self.done_label.setText(
                f"导入完成：{len({c['name'] for c in self.courses})} 门课、"
                f"{len(self.courses)} 个上课安排。"
            )
            self.stack.setCurrentIndex(2)
        elif i == 2:
            self.accept()
        self._update_nav()

    def _fill_preview(self):
        unique = len({c["name"] for c in self.courses})
        self.summary.setText(
            f"识别完成：{unique} 门课程、{len(self.courses)} 个上课安排，"
            f"另有 {self.remarks} 门备注课程。请核对："
        )
        self.sample.clear()
        for c in self.courses[:10]:
            item = QListWidgetItem(
                f"{DAYS[c['day']-1]} 第{c['ps']}-{c['pe']}节  "
                f"{c['name']}  {c['room']}  {c['teacher']}"
            )
            self.sample.addItem(item)

    def _write_courses(self):
        if self.mode_over.isChecked():
            self.db.execute("DELETE FROM courses")
        self.db.executemany(
            "INSERT INTO courses(name,code,day,ps,pe,ws,we,room,teacher)"
            " VALUES(:name,:code,:day,:ps,:pe,:ws,:we,:room,:teacher)",
            [
                {
                    "name": c["name"], "code": c["code"], "day": c["day"],
                    "ps": c["ps"], "pe": c["pe"], "ws": c["ws"], "we": c["we"],
                    "room": c["room"], "teacher": c["teacher"],
                }
                for c in self.courses
            ],
        )

    def _update_nav(self):
        i = self.stack.currentIndex()
        self.back_btn.setEnabled(i > 0)
        self.next_btn.setText(
            ["开始解析", "确认导入", "完成"][i]
        )
