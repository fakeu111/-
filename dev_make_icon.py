"""生成 resources/app.ico：松绿圆角方块 + 白色勾选。"""
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap


def draw(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#2F8F73"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(size * 0.06, size * 0.06, size * 0.88, size * 0.88),
                      size * 0.2, size * 0.2)
    # 白色勾选
    path = QPainterPath()
    path.moveTo(QPointF(size * 0.26, size * 0.52))
    path.lineTo(QPointF(size * 0.44, size * 0.69))
    path.lineTo(QPointF(size * 0.74, size * 0.33))
    pen = QPen(QColor("#FFFFFF"), size * 0.11)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.drawPath(path)
    p.end()
    return pm


if __name__ == "__main__":
    app = QGuiApplication([])
    out = Path(__file__).parent / "resources" / "app.ico"
    draw(256).save(str(out), "ICO")
    print("saved", out)
