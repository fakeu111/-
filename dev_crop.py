from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

app = QApplication([])
p = QPixmap("_real_schedule.png")
c = p.copy(28, 58, 150, 40)
c = c.scaled(c.width() * 4, c.height() * 4, Qt.IgnoreAspectRatio, Qt.FastTransformation)
c.save("_navrow_big.png")
print("ok")
