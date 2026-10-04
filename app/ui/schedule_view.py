"""课程表视图：周网格、周次切换、导入入口与课程编辑。"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.schedule import week_of
from app.ui.dialogs.course_dialog import CourseDialog
from app.ui.dialogs.import_wizard import ImportWizard

DAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
GROUPS = [("上午", 1, 4), ("下午", 5, 9), ("晚", 10, 12)]


class ScheduleView(QWidget):
    def __init__(self, db, win):
        super().__init__()
        self.db = db
        self.win = win
        self.week = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- 头部 ----
        head = QWidget()
        h = QHBoxLayout(head)
        h.setContentsMargins(24, 15, 24, 13)
        left = QVBoxLayout(); left.setSpacing(2)
        title = QLabel("课程表"); title.setObjectName("PageH1")
        sub = QLabel("2025 级 · 软件工程 25-2 班 · 张嘉和")
        sub.setObjectName("PageSub")
        left.addWidget(title); left.addWidget(sub)
        h.addLayout(left); h.addStretch(1)

        self.btn_prev = QPushButton("‹"); self.btn_prev.setObjectName("ToolIcon")
        self.week_label = QLabel(); self.week_label.setFixedWidth(210)
        self.week_label.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton("›"); self.btn_next.setObjectName("ToolIcon")
        h.addWidget(self.btn_prev); h.addWidget(self.week_label); h.addWidget(self.btn_next)
        self.btn_today = QPushButton("回到本周")
        self.btn_today.clicked.connect(self.back_this_week)
        h.addWidget(self.btn_today)
        self.btn_add = QPushButton("新增课程")
        self.btn_add.setObjectName("Btn")
        self.btn_add.clicked.connect(self.add_course)
        h.addWidget(self.btn_add)
        self.btn_import = QPushButton("导入 Word 课表")
        self.btn_import.setObjectName("Primary")
        self.btn_import.clicked.connect(self.import_word)
        h.addWidget(self.btn_import)
        outer.addWidget(head)

        # ---- 横幅（未设置开学日期时） ----
        self.banner = QLabel()
        self.banner.setObjectName("Banner")
        self.banner.hide()
        banner_wrap = QWidget()
        bl = QVBoxLayout(banner_wrap)
        bl.setContentsMargins(24, 0, 24, 10)
        bl.addWidget(self.banner)
        outer.addWidget(banner_wrap)

        # ---- 表格 ----
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 0, 24, 20)
        self.table = QTableWidget(12, 9)
        self.table.setHorizontalHeaderLabels(["时段", "节次", *DAY_NAMES])
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 46)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(1, 58)
        for c in range(2, 9):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        cl.addWidget(self.table)
        outer.addWidget(content, 1)

        self.btn_prev.clicked.connect(lambda: self.shift_week(-1))
        self.btn_next.clicked.connect(lambda: self.shift_week(1))

    # ---------- 数据与周次 ----------
    def _sem_start(self):
        sem = self.db.get_meta("sem_start")
        return date.fromisoformat(sem) if sem else None

    def reload(self):
        sem = self._sem_start()
        if sem is None:
            self.banner.setText("还没设置开学日期，点“设置”填写开学第 1 周周一，才能按周显示课程。")
            self.banner.show()
            if self.week == 0:
                self.week = 1
        else:
            self.banner.hide()
            if self.week == 0:
                self.week = week_of(date.today(), sem)
        self.fill()

    def shift_week(self, delta: int):
        self.week = max(1, self.week + delta)
        self.fill()

    def back_this_week(self):
        sem = self._sem_start()
        if sem:
            self.week = week_of(date.today(), sem)
        self.fill()

    # ---------- 渲染 ----------
    def fill(self):
        sem = self._sem_start()
        w = self.week
        from datetime import timedelta
        if sem is not None:
            m0 = sem + timedelta(days=7 * (w - 1))
            m6 = m0 + timedelta(days=6)
            self.week_label.setText(
                f"第 {w} 周 · {m0.month}/{m0.day} – {m6.month}/{m6.day}"
            )
        else:
            self.week_label.setText(f"第 {w} 周")

        rows = self.db.query("SELECT * FROM courses")
        starts: dict[tuple[int, int], list] = {}
        for r in rows:
            if r["ws"] <= w <= r["we"]:
                starts.setdefault((r["day"], r["ps"]), []).append(r)

        table = self.table
        table.clearContents()
        for rr in range(12):  # 重置可能残留的跨行/跨列
            for cc in range(9):
                table.setSpan(rr, cc, 1, 1)
        covered: set[tuple[int, int]] = set()
        today_iso = date.today().isoweekday()

        for gname, gstart, gend in GROUPS:
            gitem = QTableWidgetItem(gname)
            gitem.setTextAlignment(Qt.AlignCenter)
            gitem.setFlags(gitem.flags() & ~Qt.ItemIsEditable)
            table.setItem(gstart - 1, 0, gitem)
            table.setSpan(gstart - 1, 0, gend - gstart + 1, 1)

        for p in range(1, 13):
            row_i = p - 1
            pitem = QTableWidgetItem(f"{p}\n{self._period_time(p)}")
            pitem.setTextAlignment(Qt.AlignCenter)
            pitem.setFlags(pitem.flags() & ~Qt.ItemIsEditable)
            table.setItem(row_i, 1, pitem)

            for day in range(1, 8):
                col = day + 1
                if (day, p) in covered:
                    continue
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if day == today_iso:
                    item.setBackground(QColor("#F5FAF8"))
                table.setItem(row_i, col, item)

                blocks = starts.get((day, p))
                if blocks:
                    widget = QWidget()
                    vl = QVBoxLayout(widget)
                    vl.setContentsMargins(2, 2, 2, 2)
                    vl.setSpacing(3)
                    for r in blocks:
                        vl.addWidget(self._block(r))
                        for q in range(r["ps"] + 1, r["pe"] + 1):
                            covered.add((day, q))
                    table.setCellWidget(row_i, col, widget)
                    table.setSpan(row_i, col, blocks[0]["pe"] - blocks[0]["ps"] + 1, 1)
                    table.setRowHeight(row_i, max(58, len(blocks) * 46 + 10))
                else:
                    table.setRowHeight(row_i, 58)

        hit = table.horizontalHeaderItem(today_iso + 1)
        if hit:
            hit.setBackground(QColor("#E7F2ED"))
            hit.setForeground(QColor("#1F5E4C"))

    def _period_time(self, p: int) -> str:
        r = self.db.query_one(
            "SELECT start_time FROM periods WHERE period=?", (p,)
        )
        return r["start_time"] if r else ""

    def _block(self, r) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("SesBlock")
        v = QVBoxLayout(btn)
        v.setContentsMargins(6, 5, 6, 5)
        v.setSpacing(1)
        name = QLabel(r["name"]); name.setObjectName("SesName")
        meta = QLabel(f"{r['room']} · {r['teacher']} · {r['ws']}-{r['we']}周")
        meta.setObjectName("SesMeta")
        v.addWidget(name); v.addWidget(meta)
        btn.clicked.connect(lambda: self.edit_course(r["id"]))
        return btn

    # ---------- 入口动作 ----------
    def import_word(self):
        dlg = ImportWizard(self.db, self)
        if dlg.exec():
            self.reload()
            self.win.update_counts()

    def edit_course(self, course_id: int):
        row = self.db.query_one("SELECT * FROM courses WHERE id=?", (course_id,))
        dlg = CourseDialog(self.db, row, self)
        if dlg.exec():
            self.reload()
            self.win.update_counts()

    def add_course(self):
        dlg = CourseDialog(self.db, None, self)
        if dlg.exec():
            self.reload()
            self.win.update_counts()
