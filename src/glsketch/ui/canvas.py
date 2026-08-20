from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from glsketch.domain.objects import ObjectKind, Point, SceneObject
from glsketch.domain.scene import Scene


def _qt_point(point: Point) -> QPointF:
    return QPointF(point.x, -point.y)


class CanvasView(QGraphicsView):
    object_created = Signal(object)
    model_changed = Signal()
    object_selected = Signal(str)
    cursor_position = Signal(float, float)

    def __init__(self, model: Scene, parent=None) -> None:
        super().__init__(parent)
        self.model = model
        self.graphics = QGraphicsScene(self)
        self.setScene(self.graphics)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(model.canvas.background))
        self.setMouseTracking(True)
        self._tool = "select"
        self._start: QPointF | None = None
        self._pan_start: QPointF | None = None
        self._items: dict[str, QGraphicsItem] = {}
        self.graphics.selectionChanged.connect(self._selection_changed)
        self.refresh()

    def set_tool(self, tool: str) -> None:
        self._tool = tool
        self.setDragMode(
            QGraphicsView.DragMode.RubberBandDrag
            if tool == "select"
            else QGraphicsView.DragMode.NoDrag
        )

    def set_model(self, model: Scene) -> None:
        self.model = model
        self.setBackgroundBrush(QColor(model.canvas.background))
        self.refresh()

    def refresh(self, select_id: str | None = None) -> None:
        selected = select_id or self.selected_object_id()
        self.graphics.clear()
        self._items.clear()
        c = self.model.canvas
        self.graphics.setSceneRect(QRectF(c.left, -c.top, c.right - c.left, c.top - c.bottom))
        self._add_reference_images()
        for index, obj in enumerate(self.model.objects):
            if not obj.visible:
                continue
            item = self._item_for(obj)
            item.setZValue(index)
            item.setData(0, obj.id)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not obj.locked)
            item.setToolTip(f"{obj.name}\n{obj.kind.value}")
            self.graphics.addItem(item)
            self._items[obj.id] = item
            if obj.id == selected:
                item.setSelected(True)
        if not self.transform().m11():
            self.fitInView(self.graphics.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _add_reference_images(self) -> None:
        from PySide6.QtGui import QPixmap

        for reference in self.model.reference_images:
            if not reference.visible:
                continue
            pixmap = QPixmap(reference.path)
            if pixmap.isNull():
                continue
            item = QGraphicsPixmapItem(pixmap)
            item.setOpacity(reference.opacity)
            item.setPos(reference.x, -(reference.y + reference.height))
            item.setScale(reference.width / max(1, pixmap.width()))
            item.setZValue(-1000)
            item.setToolTip("Imagem de referência — não será exportada como geometria")
            self.graphics.addItem(item)

    def _item_for(self, obj: SceneObject) -> QGraphicsItem:
        fill = QBrush(QColor(obj.fill_color.to_hex()))
        pen = QPen(QColor(obj.stroke_color.to_hex()), obj.stroke_width)
        if obj.kind == ObjectKind.LINE and len(obj.vertices) >= 2:
            item: QGraphicsItem = QGraphicsLineItem(
                obj.vertices[0].x,
                -obj.vertices[0].y,
                obj.vertices[1].x,
                -obj.vertices[1].y,
            )
            item.setPen(pen)
        elif obj.kind == ObjectKind.TEXT:
            item = QGraphicsSimpleTextItem(obj.text)
            item.setBrush(fill)
            if obj.vertices:
                item.setPos(_qt_point(obj.vertices[0]))
        elif obj.kind == ObjectKind.ELLIPSE:
            path = QPainterPath()
            points = [_qt_point(point) for point in obj.vertices]
            if points:
                path.moveTo(points[0])
                for point in points[1:]:
                    path.lineTo(point)
                path.closeSubpath()
            item = QGraphicsPathItem(path)
            item.setBrush(fill)
            item.setPen(pen)
        else:
            polygon = QPolygonF([_qt_point(point) for point in obj.vertices])
            item = QGraphicsPolygonItem(polygon)
            if obj.kind in {ObjectKind.LINE_STRIP, ObjectKind.LINE_LOOP}:
                item.setBrush(Qt.BrushStyle.NoBrush)
            else:
                item.setBrush(fill)
            item.setPen(pen)
        item.setTransformOriginPoint(item.boundingRect().center())
        item.setRotation(-obj.rotation)
        transform = item.transform()
        transform.scale(obj.scale_x, obj.scale_y)
        item.setTransform(transform)
        return item

    def selected_object_id(self) -> str | None:
        selected = self.graphics.selectedItems()
        return str(selected[0].data(0)) if selected and selected[0].data(0) else None

    def select_object(self, object_id: str) -> None:
        item = self._items.get(object_id)
        if item is not None:
            self.graphics.clearSelection()
            item.setSelected(True)
            self.ensureVisible(item)

    def _selection_changed(self) -> None:
        object_id = self.selected_object_id()
        if object_id:
            self.object_selected.emit(object_id)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        super().drawBackground(painter, rect)
        c = self.model.canvas
        if not c.show_grid or c.grid_size <= 0:
            return
        painter.save()
        painter.setPen(QPen(QColor("#DDE3EA"), 0))
        left = int(rect.left() // c.grid_size) * c.grid_size
        top = int(rect.top() // c.grid_size) * c.grid_size
        x = left
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += c.grid_size
        y = top
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += c.grid_size
        painter.setPen(QPen(QColor("#94A3B8"), 0))
        painter.drawLine(QPointF(c.left, 0), QPointF(c.right, 0))
        painter.drawLine(QPointF(0, -c.bottom), QPointF(0, -c.top))
        painter.restore()

    def _model_point(self, event) -> Point:
        scene_point = self.mapToScene(event.position().toPoint())
        x, y = scene_point.x(), -scene_point.y()
        if self.model.canvas.snap_to_grid and self.model.canvas.grid_size > 0:
            size = self.model.canvas.grid_size
            x, y = round(x / size) * size, round(y / size) * size
        return Point(float(x), float(y))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if self._tool != "select" and event.button() == Qt.MouseButton.LeftButton:
            self._start = self.mapToScene(event.position().toPoint())
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        point = self.mapToScene(event.position().toPoint())
        self.cursor_position.emit(point.x(), -point.y())
        if self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = None
            self.unsetCursor()
            return
        if self._tool != "select" and self._start is not None:
            start = Point(self._start.x(), -self._start.y())
            end = self._model_point(event)
            if start != end:
                factory = {
                    "rectangle": lambda: SceneObject.rectangle(start, end),
                    "triangle": lambda: SceneObject.triangle(start, end),
                    "line": lambda: SceneObject.create(ObjectKind.LINE, [start, end]),
                    "ellipse": lambda: SceneObject.ellipse(start, end),
                }.get(self._tool)
                if factory:
                    self.object_created.emit(factory())
            self._start = None
            return
        super().mouseReleaseEvent(event)
        moved = False
        for item in self.graphics.selectedItems():
            if item.pos() == QPointF(0, 0):
                continue
            obj = self.model.find(str(item.data(0)))
            if obj and not obj.locked:
                obj.vertices = [
                    Point(p.x + item.pos().x(), p.y - item.pos().y()) for p in obj.vertices
                ]
                item.setPos(0, 0)
                moved = True
        if moved:
            self.model_changed.emit()
            self.refresh()

    def wheelEvent(self, event) -> None:  # noqa: N802
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
