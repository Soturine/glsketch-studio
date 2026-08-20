import ast
import inspect

from PySide6.QtOpenGLWidgets import QOpenGLWidget

from glsketch.codegen import generate_code
from glsketch.domain import Point, Scene, SceneObject
from glsketch.ui import canvas as canvas_module
from glsketch.ui.canvas import OpenGLCanvas


def test_canvas_is_qopenglwidget_without_qgraphics_renderer() -> None:
    source = inspect.getsource(canvas_module)
    assert issubclass(OpenGLCanvas, QOpenGLWidget)
    assert "QGraphics" not in source
    assert "QPainter" not in source
    for call in ("initializeGL", "resizeGL", "paintGL", "glBegin", "glVertex2f"):
        assert call in source


def test_export_uses_only_allowed_graphics_imports() -> None:
    scene = Scene(objects=[SceneObject.rectangle(Point(0, 0), Point(10, 10))])
    tree = ast.parse(generate_code(scene))
    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported_modules == {"OpenGL.GL", "OpenGL.GLU", "OpenGL.GLUT"}


def test_export_does_not_reference_forbidden_renderers() -> None:
    code = generate_code(Scene())
    forbidden = {
        "pygame",
        "turtle",
        "matplotlib",
        "PIL",
        "cairo",
        "tkinter",
        "moderngl",
        "arcade",
        "WebGL",
    }
    assert not any(name.lower() in code.lower() for name in forbidden)


def test_reference_images_are_not_exported() -> None:
    scene = Scene(objects=[SceneObject.rectangle(Point(0, 0), Point(10, 10))])
    from glsketch.domain import ReferenceImage

    scene.reference_images.append(ReferenceImage("secret-reference.png"))
    assert "secret-reference.png" not in generate_code(scene)
