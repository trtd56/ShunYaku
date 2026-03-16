from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def load_app_icon() -> QIcon:
    icon_path = Path(__file__).resolve().parents[2] / "icon.png"
    if not icon_path.exists():
        return QIcon()

    source = QPixmap(str(icon_path))
    if source.isNull():
        return QIcon()

    canvas_size = 1024
    canvas = QPixmap(canvas_size, canvas_size)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    tile_rect = QRectF(80, 80, canvas_size - 160, canvas_size - 160)
    tile_path = QPainterPath()
    tile_path.addRoundedRect(tile_rect, 220, 220)

    painter.fillPath(tile_path, QColor("#F6F1E8"))
    painter.setPen(QPen(QColor(16, 20, 24, 28), 10))
    painter.drawPath(tile_path)

    icon_image = source.scaled(
        840,
        840,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    image_x = int((canvas_size - icon_image.width()) / 2)
    image_y = int((canvas_size - icon_image.height()) / 2)
    painter.drawPixmap(image_x, image_y, icon_image)
    painter.end()

    return QIcon(canvas)
