from __future__ import annotations

from math import cos, hypot, radians, sin
from pathlib import Path

from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_LINE_LOOP,
    GL_LINE_SMOOTH,
    GL_LINE_STRIP,
    GL_LINES,
    GL_MODELVIEW,
    GL_NEAREST,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_POLYGON,
    GL_PROJECTION,
    GL_QUADS,
    GL_RGBA,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TRIANGLE_FAN,
    GL_TRIANGLES,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBindTexture,
    glBlendFunc,
    glClear,
    glClearColor,
    glColor3f,
    glColor4f,
    glDeleteTextures,
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glLineWidth,
    glLoadIdentity,
    glMatrixMode,
    glPopMatrix,
    glPushMatrix,
    glRotatef,
    glScalef,
    glTexCoord2f,
    glTexImage2D,
    glTexParameteri,
    glTranslatef,
    glVertex2f,
    glViewport,
)
from OpenGL.GLU import gluOrtho2D
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18, glutBitmapCharacter
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImage
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from glsketch.domain.objects import ObjectKind, Point, SceneObject
from glsketch.domain.scene import ReferenceImage, Scene

_PRIMITIVES = {
    ObjectKind.LINE: GL_LINES,
    ObjectKind.LINE_STRIP: GL_LINE_STRIP,
    ObjectKind.LINE_LOOP: GL_LINE_LOOP,
    ObjectKind.RECTANGLE: GL_QUADS,
    ObjectKind.TRIANGLE: GL_TRIANGLES,
    ObjectKind.POLYGON: GL_POLYGON,
    ObjectKind.ELLIPSE: GL_TRIANGLE_FAN,
    ObjectKind.STAR: GL_POLYGON,
}


def _distance_to_segment(point: Point, start: Point, end: Point) -> float:
    dx, dy = end.x - start.x, end.y - start.y
    if dx == 0 and dy == 0:
        return hypot(point.x - start.x, point.y - start.y)
    amount = max(
        0.0,
        min(1.0, ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy)),
    )
    closest = Point(start.x + amount * dx, start.y + amount * dy)
    return hypot(point.x - closest.x, point.y - closest.y)


def _point_in_polygon(point: Point, vertices: list[Point]) -> bool:
    inside = False
    previous = vertices[-1] if vertices else point
    for current in vertices:
        crosses = (current.y > point.y) != (previous.y > point.y)
        if crosses:
            intersection = (previous.x - current.x) * (point.y - current.y) / (
                previous.y - current.y
            ) + current.x
            if point.x < intersection:
                inside = not inside
        previous = current
    return inside


class OpenGLCanvas(QOpenGLWidget):
    """Interactive scene adapter rendered exclusively with PyOpenGL."""

    object_created = Signal(object)
    model_changed = Signal()
    object_selected = Signal(str)
    cursor_position = Signal(float, float)
    text_requested = Signal(float, float)

    def __init__(self, model: Scene, parent=None) -> None:
        super().__init__(parent)
        self.model = model
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._tool = "select"
        self._selected_id: str | None = None
        self._start: Point | None = None
        self._hover: Point | None = None
        self._pending_points: list[Point] = []
        self._pan_start: QPointF | None = None
        self._pan_origin = (0.0, 0.0)
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._zoom = 1.0
        self._drag_data: tuple[str, Point, list[Point]] | None = None
        self._resize_data: tuple[str, list[Point]] | None = None
        self._vertex_data: tuple[str, int, list[Point]] | None = None
        self._textures: dict[str, tuple[int, int, int]] = {}

    def initializeGL(self) -> None:  # noqa: N802
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        context = self.context()
        if context:
            context.aboutToBeDestroyed.connect(self._cleanup_textures)

    def resizeGL(self, width: int, height: int) -> None:  # noqa: N802
        glViewport(0, 0, max(1, width), max(1, height))

    def paintGL(self) -> None:  # noqa: N802
        background = QColor(self.model.canvas.background)
        glClearColor(background.redF(), background.greenF(), background.blueF(), 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        left, right, bottom, top = self._view_bounds()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(left, right, bottom, top)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self._render_grid(left, right, bottom, top)
        self._render_reference_images()
        for obj in self.model.objects:
            if obj.visible:
                self._render_object(obj)
        self._render_pending()
        self._render_drag_preview()
        self._render_selection()

    def _view_bounds(self) -> tuple[float, float, float, float]:
        canvas = self.model.canvas
        span_x = (canvas.right - canvas.left) / self._zoom
        span_y = (canvas.top - canvas.bottom) / self._zoom
        widget_aspect = max(1, self.width()) / max(1, self.height())
        world_aspect = span_x / max(span_y, 1e-9)
        if widget_aspect > world_aspect:
            span_x = span_y * widget_aspect
        else:
            span_y = span_x / widget_aspect
        center_x = (canvas.left + canvas.right) / 2 + self._pan_x
        center_y = (canvas.bottom + canvas.top) / 2 + self._pan_y
        return (
            center_x - span_x / 2,
            center_x + span_x / 2,
            center_y - span_y / 2,
            center_y + span_y / 2,
        )

    def _screen_to_world(self, position: QPointF, *, snap: bool = False) -> Point:
        left, right, bottom, top = self._view_bounds()
        x = left + position.x() / max(1, self.width()) * (right - left)
        y = top - position.y() / max(1, self.height()) * (top - bottom)
        if snap and self.model.canvas.snap_to_grid and self.model.canvas.grid_size > 0:
            size = self.model.canvas.grid_size
            x, y = round(x / size) * size, round(y / size) * size
        return Point(float(x), float(y))

    def _render_grid(self, left: float, right: float, bottom: float, top: float) -> None:
        canvas = self.model.canvas
        if canvas.show_grid and canvas.grid_size > 0:
            glColor3f(0.86, 0.89, 0.92)
            glLineWidth(1.0)
            glBegin(GL_LINES)
            x = int(left // canvas.grid_size) * canvas.grid_size
            while x <= right:
                glVertex2f(x, bottom)
                glVertex2f(x, top)
                x += canvas.grid_size
            y = int(bottom // canvas.grid_size) * canvas.grid_size
            while y <= top:
                glVertex2f(left, y)
                glVertex2f(right, y)
                y += canvas.grid_size
            glEnd()
        glColor3f(0.55, 0.62, 0.70)
        glBegin(GL_LINES)
        glVertex2f(left, 0.0)
        glVertex2f(right, 0.0)
        glVertex2f(0.0, bottom)
        glVertex2f(0.0, top)
        glEnd()

    def _render_reference_images(self) -> None:
        for reference in self.model.reference_images:
            if not reference.visible:
                continue
            texture = self._texture_for(reference)
            if texture is None:
                continue
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture)
            glColor4f(1.0, 1.0, 1.0, reference.opacity)
            glBegin(GL_QUADS)
            for u, v, x, y in (
                (0.0, 0.0, reference.x, reference.y),
                (1.0, 0.0, reference.x + reference.width, reference.y),
                (1.0, 1.0, reference.x + reference.width, reference.y + reference.height),
                (0.0, 1.0, reference.x, reference.y + reference.height),
            ):
                glTexCoord2f(u, v)
                glVertex2f(x, y)
            glEnd()
            glDisable(GL_TEXTURE_2D)

    def _texture_for(self, reference: ReferenceImage) -> int | None:
        path = str(Path(reference.path).resolve())
        cached = self._textures.get(path)
        if cached:
            return cached[0]
        image = QImage(path).convertToFormat(QImage.Format.Format_RGBA8888).mirrored()
        if image.isNull():
            return None
        texture = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            image.width(),
            image.height(),
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            image.bits().tobytes(),
        )
        self._textures[path] = (texture, image.width(), image.height())
        return texture

    def _cleanup_textures(self) -> None:
        if not self._textures:
            return
        self.makeCurrent()
        glDeleteTextures([item[0] for item in self._textures.values()])
        self._textures.clear()
        self.doneCurrent()

    def _render_object(self, obj: SceneObject) -> None:
        glPushMatrix()
        glTranslatef(0.0, 0.0, 0.0)
        if obj.rotation:
            glRotatef(obj.rotation, 0.0, 0.0, 1.0)
        if obj.scale_x != 1.0 or obj.scale_y != 1.0:
            glScalef(obj.scale_x, obj.scale_y, 1.0)
        if obj.kind == ObjectKind.TEXT:
            if obj.fill_enabled:
                glColor3f(obj.fill_color.r, obj.fill_color.g, obj.fill_color.b)
                self._render_text(obj)
        else:
            line_kind = obj.kind in {ObjectKind.LINE, ObjectKind.LINE_STRIP, ObjectKind.LINE_LOOP}
            if obj.fill_enabled and not line_kind:
                glColor3f(obj.fill_color.r, obj.fill_color.g, obj.fill_color.b)
                glBegin(_PRIMITIVES[obj.kind])
                if obj.kind == ObjectKind.ELLIPSE and obj.vertices:
                    center_x = sum(point.x for point in obj.vertices) / len(obj.vertices)
                    center_y = sum(point.y for point in obj.vertices) / len(obj.vertices)
                    glVertex2f(center_x, center_y)
                for point in obj.vertices:
                    glVertex2f(point.x, point.y)
                if obj.kind == ObjectKind.ELLIPSE and obj.vertices:
                    glVertex2f(obj.vertices[0].x, obj.vertices[0].y)
                glEnd()
            if obj.stroke_enabled:
                glColor3f(obj.stroke_color.r, obj.stroke_color.g, obj.stroke_color.b)
                glLineWidth(max(1.0, obj.stroke_width))
                glBegin(_PRIMITIVES[obj.kind] if line_kind else GL_LINE_LOOP)
                for point in obj.vertices:
                    glVertex2f(point.x, point.y)
                glEnd()
        glPopMatrix()

    @staticmethod
    def _render_text(obj: SceneObject) -> None:
        if not obj.vertices:
            return
        from OpenGL.GL import glRasterPos2f

        glRasterPos2f(obj.vertices[0].x, obj.vertices[0].y)
        try:
            for character in obj.text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(character))
        except Exception:
            width = max(2.0, len(obj.text) * 1.5)
            x, y = obj.vertices[0].x, obj.vertices[0].y
            glBegin(GL_LINE_LOOP)
            glVertex2f(x, y)
            glVertex2f(x + width, y)
            glVertex2f(x + width, y + 3.0)
            glVertex2f(x, y + 3.0)
            glEnd()

    def _render_pending(self) -> None:
        if not self._pending_points:
            return
        glColor3f(0.15, 0.39, 0.92)
        glLineWidth(2.0)
        glBegin(GL_LINE_STRIP)
        for point in self._pending_points:
            glVertex2f(point.x, point.y)
        glEnd()

    def _render_drag_preview(self) -> None:
        if self._start is None or self._hover is None or self._start == self._hover:
            return
        start, end = self._start, self._hover
        factory = {
            "rectangle": lambda: SceneObject.rectangle(start, end),
            "square": lambda: SceneObject.rectangle(start, self._proportional_end(start, end)),
            "triangle": lambda: SceneObject.triangle(start, end),
            "line": lambda: SceneObject.create(ObjectKind.LINE, [start, end]),
            "ellipse": lambda: SceneObject.ellipse(start, end),
            "star": lambda: SceneObject.star(start, end),
        }.get(self._tool)
        if not factory:
            return
        obj = factory()
        glColor3f(0.11, 0.30, 0.85)
        glLineWidth(2.0)
        glBegin(GL_LINES if obj.kind == ObjectKind.LINE else GL_LINE_LOOP)
        for point in obj.vertices:
            glVertex2f(point.x, point.y)
        glEnd()

    @staticmethod
    def _proportional_end(start: Point, end: Point) -> Point:
        size = max(abs(end.x - start.x), abs(end.y - start.y))
        return Point(
            start.x + size * (1 if end.x >= start.x else -1),
            start.y + size * (1 if end.y >= start.y else -1),
        )

    def _render_selection(self) -> None:
        obj = self.model.find(self._selected_id or "")
        if not obj or not obj.vertices:
            return
        vertices = self._transformed_vertices(obj)
        left = min(point.x for point in vertices)
        right = max(point.x for point in vertices)
        bottom = min(point.y for point in vertices)
        top = max(point.y for point in vertices)
        glColor3f(0.11, 0.30, 0.85)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        for x, y in ((left, bottom), (right, bottom), (right, top), (left, top)):
            glVertex2f(x, y)
        glEnd()
        size = self._pick_tolerance() * 0.55
        for point in [*vertices, Point(right, top)]:
            glBegin(GL_QUADS)
            glVertex2f(point.x - size, point.y - size)
            glVertex2f(point.x + size, point.y - size)
            glVertex2f(point.x + size, point.y + size)
            glVertex2f(point.x - size, point.y + size)
            glEnd()

    def _transformed_vertices(self, obj: SceneObject) -> list[Point]:
        angle = radians(obj.rotation)
        return [
            Point(
                point.x * obj.scale_x * cos(angle) - point.y * obj.scale_y * sin(angle),
                point.x * obj.scale_x * sin(angle) + point.y * obj.scale_y * cos(angle),
            )
            for point in obj.vertices
        ]

    def _pick_tolerance(self) -> float:
        left, right, _bottom, _top = self._view_bounds()
        return (right - left) * 8 / max(1, self.width())

    def _hit_test(self, point: Point) -> SceneObject | None:
        tolerance = self._pick_tolerance()
        for obj in reversed(self.model.objects):
            if not obj.visible or not obj.vertices:
                continue
            vertices = self._transformed_vertices(obj)
            if obj.kind in {ObjectKind.LINE, ObjectKind.LINE_STRIP, ObjectKind.LINE_LOOP}:
                pairs = list(zip(vertices, vertices[1:], strict=False))
                if obj.kind == ObjectKind.LINE_LOOP and len(vertices) > 2:
                    pairs.append((vertices[-1], vertices[0]))
                if any(
                    _distance_to_segment(point, start, end) <= tolerance for start, end in pairs
                ):
                    return obj
            elif obj.kind == ObjectKind.TEXT:
                anchor = vertices[0]
                if hypot(point.x - anchor.x, point.y - anchor.y) <= tolerance * 3:
                    return obj
            elif _point_in_polygon(point, vertices):
                return obj
        return None

    def set_tool(self, tool: str) -> None:
        self._tool = tool
        self._pending_points.clear()
        self.update()

    def set_model(self, model: Scene) -> None:
        self.model = model
        if self._selected_id and model.find(self._selected_id) is None:
            self._selected_id = None
        self.update()

    def refresh(self, select_id: str | None = None) -> None:
        if select_id is not None:
            self._selected_id = select_id
            if self.model.find(select_id):
                self.object_selected.emit(select_id)
        self.update()

    def selected_object_id(self) -> str | None:
        return self._selected_id

    def select_object(self, object_id: str) -> None:
        if self.model.find(object_id):
            self._selected_id = object_id
            self.object_selected.emit(object_id)
            self.update()

    def fit_to_scene(self) -> None:
        self._zoom = 1.0
        self._pan_x = self._pan_y = 0.0
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        point = self._screen_to_world(event.position(), snap=True)
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = event.position()
            self._pan_origin = (self._pan_x, self._pan_y)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._tool == "text":
            self.text_requested.emit(point.x, point.y)
            return
        if self._tool == "pencil":
            self._pending_points = [point]
            return
        if self._tool in {"polygon", "line_strip", "line_loop"}:
            if not self._pending_points or point != self._pending_points[-1]:
                self._pending_points.append(point)
            self.update()
            return
        if self._tool != "select":
            self._start = point
            return
        selected = self.model.find(self._selected_id or "")
        tolerance = self._pick_tolerance()
        if selected and not selected.locked:
            for index, vertex in enumerate(self._transformed_vertices(selected)):
                if hypot(point.x - vertex.x, point.y - vertex.y) <= tolerance:
                    self._vertex_data = (selected.id, index, list(selected.vertices))
                    return
            vertices = self._transformed_vertices(selected)
            handle = Point(max(p.x for p in vertices), max(p.y for p in vertices))
            if hypot(point.x - handle.x, point.y - handle.y) <= tolerance * 1.5:
                self._resize_data = (selected.id, list(selected.vertices))
                return
        hit = self._hit_test(point)
        self._selected_id = hit.id if hit else None
        if hit:
            self.object_selected.emit(hit.id)
            if not hit.locked:
                self._drag_data = (hit.id, point, list(hit.vertices))
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        raw = self._screen_to_world(event.position())
        point = self._screen_to_world(event.position(), snap=True)
        self.cursor_position.emit(raw.x, raw.y)
        if self._tool == "pencil" and self._pending_points:
            distance = hypot(
                point.x - self._pending_points[-1].x,
                point.y - self._pending_points[-1].y,
            )
            if distance > self._pick_tolerance() / 2:
                self._pending_points.append(point)
                self.update()
            return
        if self._pan_start is not None:
            left, right, bottom, top = self._view_bounds()
            delta = event.position() - self._pan_start
            self._pan_x = self._pan_origin[0] - delta.x() / max(1, self.width()) * (right - left)
            self._pan_y = self._pan_origin[1] + delta.y() / max(1, self.height()) * (top - bottom)
            self.update()
            return
        if self._vertex_data:
            object_id, index, original = self._vertex_data
            obj = self.model.find(object_id)
            if obj:
                obj.vertices = list(original)
                obj.vertices[index] = point
                self.update()
            return
        if self._resize_data:
            object_id, original = self._resize_data
            obj = self.model.find(object_id)
            if obj:
                left = min(vertex.x for vertex in original)
                bottom = min(vertex.y for vertex in original)
                width = max(vertex.x for vertex in original) - left
                height = max(vertex.y for vertex in original) - bottom
                scale_x = max(0.01, (point.x - left) / width) if width else 1.0
                scale_y = max(0.01, (point.y - bottom) / height) if height else 1.0
                obj.vertices = [
                    Point(
                        left + (vertex.x - left) * scale_x,
                        bottom + (vertex.y - bottom) * scale_y,
                    )
                    for vertex in original
                ]
                self.update()
            return
        if self._drag_data:
            object_id, start, original = self._drag_data
            obj = self.model.find(object_id)
            if obj:
                dx, dy = point.x - start.x, point.y - start.y
                obj.vertices = [Point(vertex.x + dx, vertex.y + dy) for vertex in original]
                self.update()
            return
        if self._start is not None:
            self._hover = point
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = None
            self.unsetCursor()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._tool == "pencil" and self._pending_points:
            if len(self._pending_points) >= 2:
                self.object_created.emit(
                    SceneObject.create(ObjectKind.LINE_STRIP, self._pending_points, name="Lápis")
                )
            self._pending_points = []
            self.update()
            return
        if self._tool != "select" and self._start is not None:
            start = self._start
            end = self._screen_to_world(event.position(), snap=True)
            if self._tool == "square" or (
                self._tool == "rectangle" and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            ):
                end = self._proportional_end(start, end)
            if self._tool == "ellipse" and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                end = self._proportional_end(start, end)
            if start != end:
                factory = {
                    "rectangle": lambda: SceneObject.rectangle(start, end),
                    "square": lambda: SceneObject.rectangle(start, end, name="Quadrado"),
                    "triangle": lambda: SceneObject.triangle(start, end),
                    "line": lambda: SceneObject.create(ObjectKind.LINE, [start, end]),
                    "ellipse": lambda: SceneObject.ellipse(start, end),
                    "star": lambda: SceneObject.star(start, end),
                }.get(self._tool)
                if factory:
                    self.object_created.emit(factory())
            self._start = None
            self._hover = None
            return
        changed = any((self._drag_data, self._resize_data, self._vertex_data))
        self._drag_data = self._resize_data = self._vertex_data = None
        if changed:
            self.model_changed.emit()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if self._tool in {"polygon", "line_strip", "line_loop"}:
            self._finish_pending()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self._finish_pending()
        elif event.key() == Qt.Key.Key_Escape:
            self._pending_points.clear()
            self.update()
        else:
            super().keyPressEvent(event)

    def _finish_pending(self) -> None:
        minimum = 3 if self._tool == "polygon" else 2
        if len(self._pending_points) >= minimum:
            kind = {
                "polygon": ObjectKind.POLYGON,
                "line_strip": ObjectKind.LINE_STRIP,
                "line_loop": ObjectKind.LINE_LOOP,
            }[self._tool]
            self.object_created.emit(SceneObject.create(kind, self._pending_points))
        self._pending_points = []
        self.update()

    def wheelEvent(self, event) -> None:  # noqa: N802
        old_point = self._screen_to_world(event.position())
        self._zoom = max(
            0.2, min(20.0, self._zoom * (1.15 if event.angleDelta().y() > 0 else 1 / 1.15))
        )
        new_point = self._screen_to_world(event.position())
        self._pan_x += old_point.x - new_point.x
        self._pan_y += old_point.y - new_point.y
        self.update()


CanvasView = OpenGLCanvas
