from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

INK = QColor("#172033")
BLUE = QColor("#3b82f6")
BLUE_SOFT = QColor("#bfdbfe")
PURPLE = QColor("#8b5cf6")
AMBER = QColor("#f59e0b")


def _star_points(cx: float, cy: float, outer: float, inner: float) -> QPolygonF:
    return QPolygonF(
        [
            QPointF(
                cx
                + math.cos(-math.pi / 2 + index * math.pi / 5)
                * (outer if index % 2 == 0 else inner),
                cy
                + math.sin(-math.pi / 2 + index * math.pi / 5)
                * (outer if index % 2 == 0 else inner),
            )
            for index in range(10)
        ]
    )


def tool_icon(name: str, size: int = 40) -> QIcon:
    """Return a crisp, dependency-free vector icon for the drawing palette."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(
        QPen(INK, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    )
    painter.setBrush(BLUE_SOFT)

    if name == "select":
        path = QPainterPath(QPointF(9, 6))
        path.lineTo(29, 23)
        path.lineTo(20, 24)
        path.lineTo(25, 34)
        path.lineTo(20, 36)
        path.lineTo(15, 26)
        path.lineTo(9, 33)
        path.closeSubpath()
        painter.setBrush(QColor("#ffffff"))
        painter.drawPath(path)
    elif name == "line":
        painter.drawLine(QPointF(7, 32), QPointF(33, 8))
        painter.setBrush(BLUE)
        painter.drawEllipse(QPointF(7, 32), 2.8, 2.8)
        painter.drawEllipse(QPointF(33, 8), 2.8, 2.8)
    elif name in {"rectangle", "square"}:
        rect = QRectF(7, 9 if name == "rectangle" else 7, 26, 22 if name == "rectangle" else 26)
        painter.drawRoundedRect(rect, 2, 2)
    elif name == "triangle":
        painter.drawPolygon(QPolygonF([QPointF(20, 6), QPointF(34, 33), QPointF(6, 33)]))
    elif name == "ellipse":
        painter.drawEllipse(QRectF(5, 9, 30, 22))
    elif name == "star":
        painter.setBrush(QColor("#fde68a"))
        painter.drawPolygon(_star_points(20, 20, 16, 7.5))
    elif name == "pencil":
        painter.setBrush(QColor("#fde68a"))
        painter.save()
        painter.translate(20, 20)
        painter.rotate(-42)
        painter.drawRoundedRect(QRectF(-4, -15, 8, 26), 2, 2)
        painter.setBrush(QColor("#f5d0c5"))
        painter.drawPolygon(QPolygonF([QPointF(-4, 11), QPointF(4, 11), QPointF(0, 17)]))
        painter.restore()
    elif name in {"polygon", "line_loop"}:
        painter.setBrush(BLUE_SOFT if name == "polygon" else Qt.BrushStyle.NoBrush)
        painter.drawPolygon(
            QPolygonF(
                [QPointF(7, 23), QPointF(14, 7), QPointF(32, 11), QPointF(35, 27), QPointF(20, 34)]
            )
        )
    elif name == "line_strip":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(
            QPolygonF([QPointF(5, 29), QPointF(13, 12), QPointF(23, 28), QPointF(35, 8)])
        )
        painter.setBrush(PURPLE)
        for point in (QPointF(5, 29), QPointF(13, 12), QPointF(23, 28), QPointF(35, 8)):
            painter.drawEllipse(point, 2.3, 2.3)
    elif name == "text":
        painter.setPen(QPen(INK, 3.0))
        painter.drawLine(QPointF(8, 8), QPointF(32, 8))
        painter.drawLine(QPointF(20, 8), QPointF(20, 33))
        painter.drawLine(QPointF(14, 33), QPointF(26, 33))
    else:
        painter.setBrush(AMBER)
        painter.drawEllipse(QRectF(8, 8, 24, 24))

    painter.end()
    return QIcon(pixmap)
