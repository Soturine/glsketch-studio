import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from glsketch.domain import Point, SceneObject
from glsketch.ui.canvas import OpenGLCanvas
from glsketch.ui.main_window import MainWindow


def _window() -> MainWindow:
    _app = QApplication.instance() or QApplication([])
    return MainWindow()


def test_ui_scene_to_code_and_code_to_scene() -> None:
    window = _window()
    rectangle = SceneObject.rectangle(Point(10, 10), Point(40, 30))
    window._add_object(rectangle)
    assert isinstance(window.canvas, OpenGLCanvas)
    assert "glBegin(GL_QUADS)" in window.code.toPlainText()
    edited = window.code.toPlainText().replace(
        "glColor3f(0.18, 0.55, 0.96)", "glColor3f(0.0, 1.0, 0.0)", 1
    )
    window.code.setPlainText(edited)
    window._apply_code_edit()
    assert window.scene_model.objects[0].fill_color.g == 1.0
    window.dirty = False
    window.close()


def test_ui_invalid_code_keeps_last_scene() -> None:
    window = _window()
    window._add_object(SceneObject.rectangle(Point(0, 0), Point(10, 10)))
    stable = window.scene_model.to_dict()
    window.code.setPlainText("glColor3f(1.0,")
    window._apply_code_edit()
    assert window.scene_model.to_dict() == stable
    assert "ERROR" in window.diagnostics.text()
    window.dirty = False
    window.close()
