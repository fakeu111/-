from PySide6.QtWidgets import QApplication, QLabel

from app.db import DB
from app.main import create_app
from app.ui.main_window import MainWindow

app = create_app([])
w = MainWindow(db=DB("geo_tmp.db"))
w.resize(1320, 840)
w.show()
for _ in range(12):
    app.processEvents()

for key, btn in w.nav_buttons.items():
    print(key, "btn h=", btn.height(), "sizeHint h=", btn.sizeHint().height())
    for l in btn.findChildren(QLabel):
        print("   lab", l.objectName(), "y=", l.y(), "h=", l.height(),
              "sizeHint=", l.sizeHint().height(), repr(l.text()[:8]))
