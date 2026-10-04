"""设置对话框：开学日期、作息时间、数据位置（备份/恢复在 M8 增补）。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
)

from app import config
from app.services.backup import backup_to, restore_from


class SettingsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("设置")
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        sem = db.get_meta("sem_start")
        qd = QDate.fromString(sem, "yyyy-MM-dd") if sem else QDate(2026, 9, 7)
        self.sem_edit = QDateEdit(qd)
        self.sem_edit.setCalendarPopup(True)
        self.sem_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("开学第 1 周周一", self.sem_edit)
        root.addLayout(form)

        root.addWidget(QLabel("作息时间（每节上/下课时刻）"))
        self.ptable = QTableWidget(12, 3)
        self.ptable.setHorizontalHeaderLabels(["节次", "上课", "下课"])
        self.ptable.verticalHeader().setVisible(False)
        for c in range(3):
            self.ptable.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.Stretch
            )
        rows = db.query("SELECT * FROM periods ORDER BY period")
        self.times: list[tuple[QTimeEdit, QTimeEdit]] = []
        for i, r in enumerate(rows):
            period_item = QTableWidgetItem(f"第{r['period']}节")
            period_item.setFlags(period_item.flags() & ~Qt.ItemIsEditable)
            self.ptable.setItem(i, 0, period_item)
            st = QTimeEdit(QTime.fromString(r["start_time"], "HH:mm"))
            et = QTimeEdit(QTime.fromString(r["end_time"], "HH:mm"))
            for w in (st, et):
                w.setDisplayFormat("HH:mm")
            self.ptable.setCellWidget(i, 1, st)
            self.ptable.setCellWidget(i, 2, et)
            self.times.append((st, et))
        root.addWidget(self.ptable)

        root.addWidget(QLabel("备份与恢复"))
        br = QHBoxLayout()
        bk = QPushButton("立即备份"); bk.setObjectName("Ghost")
        rs = QPushButton("从备份恢复"); rs.setObjectName("Ghost")
        bk.clicked.connect(self.do_backup)
        rs.clicked.connect(self.do_restore)
        br.addWidget(bk); br.addWidget(rs); br.addStretch(1)
        root.addLayout(br)

        loc = QLineEdit(str(config.db_path()))
        loc.setReadOnly(True)
        loc_form = QFormLayout()
        loc_form.addRow("数据保存位置", loc)
        root.addLayout(loc_form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def do_backup(self) -> None:
        default = f"学习桌面-backup-{datetime.now():%Y%m%d}.db"
        path, _ = QFileDialog.getSaveFileName(
            self, "备份数据", str(Path.home() / default), "SQLite 数据库 (*.db)"
        )
        if not path:
            return
        backup_to(self.db, path)
        QMessageBox.information(self, "备份完成", f"数据已备份到：\n{path}")

    def do_restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", str(Path.home()), "SQLite 数据库 (*.db)"
        )
        if not path:
            return
        if QMessageBox.question(
            self, "确认恢复",
            "恢复将覆盖当前所有数据，且无法撤销。确定继续？",
        ) != QMessageBox.StandardButton.Yes:
            return
        restore_from(self.db, path)
        parent = self.parent()
        if hasattr(parent, "refresh_all"):
            parent.refresh_all()
        QMessageBox.information(self, "恢复完成", "数据已恢复到备份时的状态。")

    def _save(self) -> None:
        self.db.set_meta(
            "sem_start", self.sem_edit.date().toString("yyyy-MM-dd")
        )
        for p, (st, et) in enumerate(self.times, start=1):
            self.db.execute(
                "UPDATE periods SET start_time=?, end_time=? WHERE period=?",
                (st.text(), et.text(), p),
            )
        self.accept()
