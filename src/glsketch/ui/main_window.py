from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from glsketch.codegen import ExportOptions, generate_code
from glsketch.domain.objects import Color, SceneObject
from glsketch.domain.scene import Scene
from glsketch.persistence import load_project, save_project
from glsketch.ui.canvas import CanvasView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.scene_model = Scene()
        self.project_path: Path | None = None
        self.dirty = False
        self.setWindowTitle("GLSketch Studio — Projeto sem título")
        self.resize(1440, 900)
        self._actions: dict[str, QAction] = {}
        self._build_ui()
        self._build_actions()
        self._refresh_all()
        self.statusBar().showMessage("Pronto — escolha uma forma e desenhe no canvas")

    def _build_ui(self) -> None:
        self.canvas = CanvasView(self.scene_model)
        self.canvas.object_created.connect(self._add_object)
        self.canvas.model_changed.connect(self._model_changed)
        self.canvas.object_selected.connect(self._select_object)
        self.canvas.cursor_position.connect(
            lambda x, y: self.statusBar().showMessage(f"OpenGL: x={x:.2f}, y={y:.2f}")
        )

        self.tools = QListWidget()
        for label, value, shortcut in (
            ("Selecionar", "select", "V"),
            ("Linha", "line", "L"),
            ("Retângulo", "rectangle", "R"),
            ("Triângulo", "triangle", "T"),
            ("Elipse", "ellipse", "E"),
        ):
            self.tools.addItem(f"{label}   {shortcut}")
            self.tools.item(self.tools.count() - 1).setData(Qt.ItemDataRole.UserRole, value)
        self.tools.setCurrentRow(0)
        self.tools.currentItemChanged.connect(
            lambda current, _previous: self.canvas.set_tool(current.data(Qt.ItemDataRole.UserRole))
        )

        self.layers = QListWidget()
        self.layers.currentItemChanged.connect(self._layer_selected)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Ferramentas"))
        left_layout.addWidget(self.tools)
        left_layout.addWidget(QLabel("Camadas"))
        left_layout.addWidget(self.layers, 1)

        self.code = QPlainTextEdit()
        self.code.setReadOnly(True)
        self.code.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = self.code.font()
        font.setFamilies(["Cascadia Code", "Consolas", "monospace"])
        font.setPointSize(10)
        self.code.setFont(font)
        self.diagnostics = QLabel("Sem problemas")
        self.diagnostics.setWordWrap(True)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Código OpenGL — gerado em tempo real"))
        right_layout.addWidget(self.code, 1)
        right_layout.addWidget(QLabel("Problemas"))
        right_layout.addWidget(self.diagnostics)

        self.name_edit = QLineEdit()
        self.fill_button = QPushButton("Escolher cor…")
        self.fill_button.clicked.connect(self._choose_color)
        self.name_edit.editingFinished.connect(self._apply_properties)
        self.properties = QWidget()
        form = QFormLayout(self.properties)
        form.addRow("Nome", self.name_edit)
        form.addRow("Fill", self.fill_button)

        center = QSplitter(Qt.Orientation.Vertical)
        center.addWidget(self.canvas)
        center.addWidget(self.properties)
        center.setSizes([760, 120])
        root = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(left)
        root.addWidget(center)
        root.addWidget(right)
        root.setSizes([190, 800, 450])
        self.setCentralWidget(root)

    def _action(self, text: str, slot, shortcut: str | None = None) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        self._actions[text] = action
        return action

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&Arquivo")
        for action in (
            self._action("Novo", self.new_project, "Ctrl+N"),
            self._action("Abrir…", self.open_project, "Ctrl+O"),
            self._action("Salvar", self.save, "Ctrl+S"),
            self._action("Salvar como…", self.save_as, "Ctrl+Shift+S"),
            self._action("Exportar Python…", self.export_python, "Ctrl+E"),
            self._action("Preview OpenGL", self.preview),
        ):
            file_menu.addAction(action)
        edit_menu = self.menuBar().addMenu("&Editar")
        edit_menu.addAction(self._action("Duplicar", self.duplicate, "Ctrl+D"))
        edit_menu.addAction(self._action("Excluir", self.delete_selected, "Delete"))
        view_menu = self.menuBar().addMenu("&Exibir")
        view_menu.addAction(self._action("Ajustar canvas", self.fit_canvas, "Ctrl+0"))
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        for name in ("Novo", "Abrir…", "Salvar", "Exportar Python…", "Preview OpenGL"):
            toolbar.addAction(self._actions[name])

    def _add_object(self, obj: SceneObject) -> None:
        self.scene_model.add(obj)
        self._model_changed(select_id=obj.id)

    def _model_changed(self, select_id: str | None = None) -> None:
        self.dirty = True
        self._refresh_all(select_id)

    def _refresh_all(self, select_id: str | None = None) -> None:
        self.canvas.refresh(select_id)
        self.code.setPlainText(generate_code(self.scene_model))
        current = select_id or self.canvas.selected_object_id()
        self.layers.blockSignals(True)
        self.layers.clear()
        for obj in reversed(self.scene_model.objects):
            self.layers.addItem(("🔒 " if obj.locked else "") + obj.name)
            self.layers.item(self.layers.count() - 1).setData(Qt.ItemDataRole.UserRole, obj.id)
            if obj.id == current:
                self.layers.setCurrentRow(self.layers.count() - 1)
        self.layers.blockSignals(False)
        self._update_title()

    def _update_title(self) -> None:
        name = self.project_path.name if self.project_path else "Projeto sem título"
        self.setWindowTitle(f"GLSketch Studio — {name}{' *' if self.dirty else ''}")

    def _select_object(self, object_id: str) -> None:
        obj = self.scene_model.find(object_id)
        if obj:
            self.name_edit.setText(obj.name)
            self.fill_button.setStyleSheet(f"background: {obj.fill_color.to_hex()}")

    def _layer_selected(self, current, _previous) -> None:
        if current:
            self.canvas.select_object(str(current.data(Qt.ItemDataRole.UserRole)))

    def _apply_properties(self) -> None:
        obj = self.scene_model.find(self.canvas.selected_object_id() or "")
        if obj and self.name_edit.text().strip() and obj.name != self.name_edit.text().strip():
            obj.name = self.name_edit.text().strip()
            self._model_changed(obj.id)

    def _choose_color(self) -> None:
        obj = self.scene_model.find(self.canvas.selected_object_id() or "")
        if not obj:
            return
        color = QColorDialog.getColor(QColor(obj.fill_color.to_hex()), self, "Cor de preenchimento")
        if color.isValid():
            obj.fill_color = Color.from_hex(color.name())
            self._model_changed(obj.id)

    def delete_selected(self) -> None:
        object_id = self.canvas.selected_object_id()
        if object_id:
            self.scene_model.remove(object_id)
            self._model_changed()

    def duplicate(self) -> None:
        obj = self.scene_model.find(self.canvas.selected_object_id() or "")
        if obj:
            copy = obj.duplicate()
            self.scene_model.add(copy)
            self._model_changed(copy.id)

    def fit_canvas(self) -> None:
        self.canvas.fitInView(self.canvas.graphics.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        result = QMessageBox.question(
            self,
            "Alterações não salvas",
            "Descartar as alterações não salvas?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Discard

    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        self.scene_model = Scene()
        self.canvas.set_model(self.scene_model)
        self.project_path = None
        self.dirty = False
        self._refresh_all()

    def open_project(self) -> None:
        if not self._confirm_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Abrir projeto", "", "GLSketch (*.glsketch)"
        )
        if not filename:
            return
        try:
            self.scene_model = load_project(filename)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Não foi possível abrir", str(error))
            return
        self.canvas.set_model(self.scene_model)
        self.project_path = Path(filename)
        self.dirty = False
        self._refresh_all()

    def save(self) -> bool:
        return self._save_to(self.project_path) if self.project_path else self.save_as()

    def save_as(self) -> bool:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salvar projeto", "", "GLSketch (*.glsketch)"
        )
        return self._save_to(Path(filename)) if filename else False

    def _save_to(self, path: Path | None) -> bool:
        if path is None:
            return False
        try:
            self.project_path = save_project(self.scene_model, path)
        except OSError as error:
            QMessageBox.critical(self, "Não foi possível salvar", str(error))
            return False
        self.dirty = False
        self._update_title()
        self.statusBar().showMessage(f"Salvo em {self.project_path}", 5000)
        return True

    def export_python(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportar Python", "desenho.py", "Python (*.py)"
        )
        if not filename:
            return
        try:
            Path(filename).write_text(
                generate_code(self.scene_model, ExportOptions(markers=False)), encoding="utf-8"
            )
        except OSError as error:
            QMessageBox.critical(self, "Não foi possível exportar", str(error))
            return
        self.statusBar().showMessage(f"Código exportado em {filename}", 5000)

    def preview(self) -> None:
        preview_dir = Path(tempfile.mkdtemp(prefix="glsketch-preview-"))
        script = preview_dir / "preview.py"
        script.write_text(
            generate_code(self.scene_model, ExportOptions(markers=False)), encoding="utf-8"
        )
        try:
            subprocess.Popen([sys.executable, str(script)], cwd=preview_dir)  # noqa: S603
        except OSError as error:
            QMessageBox.critical(self, "Preview indisponível", str(error))

    def closeEvent(self, event) -> None:  # noqa: N802
        event.accept() if self._confirm_discard() else event.ignore()
