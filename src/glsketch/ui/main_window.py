from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from glsketch.codegen import ExportOptions, generate_code
from glsketch.commands import SceneHistory
from glsketch.domain.objects import Color, ObjectKind, Point, SceneObject
from glsketch.domain.scene import ReferenceImage, Scene
from glsketch.persistence import load_project, save_project
from glsketch.sync import ChangeOrigin, SynchronizationController
from glsketch.templates import TEMPLATE_NAMES, create_template
from glsketch.ui.canvas import CanvasView
from glsketch.ui.code_editor import CodeEditor
from glsketch.ui.dialogs import ExportDialog, PreviewDialog, ReferenceDialog
from glsketch.ui.theme import APP_STYLESHEET
from glsketch.ui.tool_icons import tool_icon


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.scene_model = Scene()
        self.project_path: Path | None = None
        self.dirty = False
        self.history = SceneHistory(self.scene_model.to_dict())
        self.sync = SynchronizationController(self.scene_model)
        self.block_ranges: dict[str, tuple[int, int]] = {}
        self._syncing_code = False
        self._tool_shortcuts: list[QShortcut] = []
        self._preview_dialogs: list[PreviewDialog] = []
        self.setWindowTitle("GLSketch Studio — Projeto sem título")
        self.setMinimumSize(1100, 700)
        self.resize(1440, 900)
        self.setStyleSheet(APP_STYLESHEET)
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
        self.canvas.text_requested.connect(self._add_text_at)

        self.tools = QListWidget()
        self.tools.setObjectName("ToolPalette")
        self.tools.setAccessibleName("Ferramentas de desenho")
        self.tools.setToolTip("Escolha uma ferramenta e desenhe diretamente no canvas OpenGL")
        for label, value, shortcut in (
            ("Selecionar", "select", "V"),
            ("Linha", "line", "L"),
            ("Retângulo", "rectangle", "R"),
            ("Quadrado", "square", "Q"),
            ("Triângulo", "triangle", "T"),
            ("Círculo / Elipse", "ellipse", "E"),
            ("Estrela", "star", "S"),
            ("Lápis livre", "pencil", "F"),
            ("Polígono", "polygon", "P"),
            ("Linha contínua", "line_strip", "I"),
            ("Contorno", "line_loop", "O"),
            ("Texto", "text", "X"),
        ):
            self.tools.addItem(label)
            item = self.tools.item(self.tools.count() - 1)
            item.setIcon(tool_icon(value))
            item.setData(Qt.ItemDataRole.UserRole, value)
            item.setToolTip(f"{label} — atalho {shortcut}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.tools.setViewMode(QListView.ViewMode.IconMode)
        self.tools.setResizeMode(QListView.ResizeMode.Adjust)
        self.tools.setMovement(QListView.Movement.Static)
        self.tools.setIconSize(QSize(38, 38))
        self.tools.setGridSize(QSize(82, 70))
        self.tools.setMinimumHeight(320)
        self.tools.setSpacing(3)
        self.tools.setWordWrap(True)
        self.tools.setCurrentRow(0)
        self.tools.currentItemChanged.connect(
            lambda current, _previous: self.canvas.set_tool(current.data(Qt.ItemDataRole.UserRole))
        )

        self.layers = QListWidget()
        self.layers.setAccessibleName("Camadas do desenho")
        self.layers.currentItemChanged.connect(self._layer_selected)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        welcome = QLabel(
            "1. Escolha uma forma.\n2. Arraste no canvas.\n3. Edite pelas alças ou pelo código."
        )
        welcome.setObjectName("WelcomeCard")
        welcome.setWordWrap(True)
        left_layout.addWidget(welcome)
        tools_heading = QLabel("Ferramentas")
        tools_heading.setObjectName("SectionHeading")
        left_layout.addWidget(tools_heading)
        left_layout.addWidget(self.tools)
        layers_heading = QLabel("Camadas")
        layers_heading.setObjectName("SectionHeading")
        left_layout.addWidget(layers_heading)
        left_layout.addWidget(self.layers, 1)

        self.code = CodeEditor()
        self.code.setLineWrapMode(CodeEditor.LineWrapMode.NoWrap)
        font = self.code.font()
        font.setFamilies(["Cascadia Code", "Consolas", "monospace"])
        font.setPointSize(10)
        self.code.setFont(font)
        self.code_timer = QTimer(self)
        self.code_timer.setSingleShot(True)
        self.code_timer.setInterval(350)
        self.code_timer.timeout.connect(self._apply_code_edit)
        self.code.textChanged.connect(self._schedule_code_sync)
        self.code.cursorPositionChanged.connect(self._code_cursor_moved)
        self.diagnostics = QLabel("Sem problemas")
        self.diagnostics.setWordWrap(True)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Código OpenGL — gerado em tempo real"))
        right_layout.addWidget(self.code, 1)
        right_layout.addWidget(QLabel("Problemas"))
        right_layout.addWidget(self.diagnostics)

        self.name_edit = QLineEdit()
        self.x_spin = self._spin()
        self.y_spin = self._spin()
        self.width_spin = self._spin(0, 10000)
        self.height_spin = self._spin(0, 10000)
        self.rotation_spin = self._spin(-360, 360)
        self.scale_x_spin = self._spin(0.01, 100, 1.0)
        self.scale_y_spin = self._spin(0.01, 100, 1.0)
        self.visible_check = QCheckBox()
        self.locked_check = QCheckBox()
        self.fill_enabled_check = QCheckBox("Preenchida")
        self.stroke_enabled_check = QCheckBox("Com borda")
        self.fill_button = QPushButton("Escolher cor…")
        self.fill_button.clicked.connect(self._choose_color)
        self.stroke_button = QPushButton("Escolher cor…")
        self.stroke_button.clicked.connect(self._choose_stroke_color)
        self.stroke_width_spin = self._spin(0.1, 100, 1.0)
        self.vertices_button = QPushButton("Editar vértices…")
        self.vertices_button.clicked.connect(self.edit_vertices)
        self.name_edit.editingFinished.connect(self._apply_properties)
        for control in (
            self.x_spin,
            self.y_spin,
            self.width_spin,
            self.height_spin,
            self.rotation_spin,
            self.scale_x_spin,
            self.scale_y_spin,
            self.stroke_width_spin,
        ):
            control.editingFinished.connect(self._apply_properties)
        self.visible_check.toggled.connect(self._apply_properties)
        self.locked_check.toggled.connect(self._apply_properties)
        self.fill_enabled_check.toggled.connect(self._apply_properties)
        self.stroke_enabled_check.toggled.connect(self._apply_properties)
        self.properties = QWidget()
        form = QFormLayout(self.properties)
        form.addRow("Nome", self.name_edit)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Largura", self.width_spin)
        form.addRow("Altura", self.height_spin)
        form.addRow("Rotação", self.rotation_spin)
        form.addRow("Escala X", self.scale_x_spin)
        form.addRow("Escala Y", self.scale_y_spin)
        form.addRow("Fill", self.fill_button)
        form.addRow("Preenchimento", self.fill_enabled_check)
        form.addRow("Stroke", self.stroke_button)
        form.addRow("Borda", self.stroke_enabled_check)
        form.addRow("Espessura", self.stroke_width_spin)
        form.addRow("Geometria", self.vertices_button)
        form.addRow("Visível", self.visible_check)
        form.addRow("Bloqueado", self.locked_check)

        center = QSplitter(Qt.Orientation.Vertical)
        center.addWidget(self.canvas)
        center.addWidget(self.properties)
        center.setSizes([760, 120])
        root = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(left)
        root.addWidget(center)
        root.addWidget(right)
        root.setSizes([220, 800, 450])
        self.setCentralWidget(root)

    @staticmethod
    def _spin(minimum: float = -10000, maximum: float = 10000, value: float = 0) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(3)
        spin.setValue(value)
        return spin

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
        edit_menu.addAction(self._action("Desfazer", self.undo, "Ctrl+Z"))
        edit_menu.addAction(self._action("Refazer", self.redo, "Ctrl+Shift+Z"))
        edit_menu.addAction(self._action("Copiar", self.copy, "Ctrl+C"))
        edit_menu.addAction(self._action("Colar", self.paste, "Ctrl+V"))
        edit_menu.addAction(self._action("Duplicar", self.duplicate, "Ctrl+D"))
        edit_menu.addAction(self._action("Excluir", self.delete_selected, "Delete"))
        edit_menu.addAction(self._action("Editar vértices…", self.edit_vertices))
        insert_menu = self.menuBar().addMenu("&Inserir")
        insert_menu.addAction(self._action("Texto…", self.add_text))
        insert_menu.addAction(self._action("Imagem de referência…", self.add_reference_image))
        insert_menu.addAction(
            self._action("Configurar imagem de referência…", self.edit_reference_image)
        )
        layer_menu = self.menuBar().addMenu("&Camada")
        layer_menu.addAction(self._action("Trazer para frente", lambda: self.move_layer(1)))
        layer_menu.addAction(self._action("Enviar para trás", lambda: self.move_layer(-1)))
        layer_menu.addAction(self._action("Levar ao topo", lambda: self.move_layer(100000)))
        layer_menu.addAction(self._action("Enviar ao fundo", lambda: self.move_layer(-100000)))
        view_menu = self.menuBar().addMenu("&Exibir")
        view_menu.addAction(self._action("Ajustar canvas", self.fit_canvas, "Ctrl+0"))
        view_menu.addAction(self._action("Alternar grade", self.toggle_grid))
        view_menu.addAction(self._action("Alternar snap", self.toggle_snap))
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(22, 22))
        self.addToolBar(toolbar)
        action_icons = {
            "Novo": QStyle.StandardPixmap.SP_FileIcon,
            "Abrir…": QStyle.StandardPixmap.SP_DialogOpenButton,
            "Salvar": QStyle.StandardPixmap.SP_DialogSaveButton,
            "Exportar Python…": QStyle.StandardPixmap.SP_ArrowDown,
            "Preview OpenGL": QStyle.StandardPixmap.SP_MediaPlay,
        }
        for name, standard_icon in action_icons.items():
            self._actions[name].setIcon(self.style().standardIcon(standard_icon))
        for name in ("Novo", "Abrir…", "Salvar", "Exportar Python…", "Preview OpenGL"):
            toolbar.addAction(self._actions[name])
        for row, key in enumerate(("V", "L", "R", "Q", "T", "E", "S", "F", "P", "I", "O", "X")):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda row=row: self.tools.setCurrentRow(row))
            self._tool_shortcuts.append(shortcut)

    def _add_object(self, obj: SceneObject) -> None:
        self.scene_model.add(obj)
        self._model_changed(select_id=obj.id)

    def _model_changed(self, select_id: str | None = None, *, checkpoint: bool = True) -> None:
        self.dirty = True
        if checkpoint:
            self.history.checkpoint(self.scene_model.to_dict())
        self._refresh_all(select_id)

    def _refresh_all(self, select_id: str | None = None) -> None:
        self.canvas.refresh(select_id)
        with self.sync.changing(ChangeOrigin.CANVAS):
            outcome = self.sync.from_scene(self.scene_model, self.code.toPlainText())
        self._set_code(outcome.code)
        self.block_ranges = outcome.block_ranges
        self._show_diagnostics(outcome.diagnostics)
        self._refresh_layers(select_id)
        self._update_title()

    def _refresh_layers(self, select_id: str | None = None) -> None:
        current = select_id or self.canvas.selected_object_id()
        self.layers.blockSignals(True)
        self.layers.clear()
        for obj in reversed(self.scene_model.objects):
            self.layers.addItem(("🔒 " if obj.locked else "") + obj.name)
            self.layers.item(self.layers.count() - 1).setData(Qt.ItemDataRole.UserRole, obj.id)
            if obj.id == current:
                self.layers.setCurrentRow(self.layers.count() - 1)
        self.layers.blockSignals(False)

    def _set_code(self, text: str) -> None:
        if self.code.toPlainText() == text:
            return
        cursor = self.code.textCursor()
        position = cursor.position()
        scroll = self.code.verticalScrollBar().value()
        self._syncing_code = True
        self.code.setPlainText(text)
        cursor.setPosition(min(position, len(text)))
        self.code.setTextCursor(cursor)
        self.code.verticalScrollBar().setValue(scroll)
        self._syncing_code = False

    def _schedule_code_sync(self) -> None:
        if not self._syncing_code:
            self.code_timer.start()

    def _apply_code_edit(self) -> None:
        with self.sync.changing(ChangeOrigin.CODE):
            outcome = self.sync.from_code(self.code.toPlainText())
        self.block_ranges = outcome.block_ranges
        self._show_diagnostics(outcome.diagnostics)
        if not outcome.applied:
            error = next((item for item in outcome.diagnostics if item.severity == "error"), None)
            if error:
                self.code.highlight_range(error.line, error.line, error=True)
            return
        self.scene_model = outcome.scene
        self.canvas.set_model(self.scene_model)
        self.history.checkpoint(self.scene_model.to_dict())
        self.dirty = True
        self._refresh_layers()
        self._update_title()

    def _show_diagnostics(self, diagnostics) -> None:
        if not diagnostics:
            self.diagnostics.setText("Sem problemas — trecho sincronizado")
            return
        self.diagnostics.setText(
            "\n".join(
                f"{item.severity.value.upper()} — linha {item.line}: {item.message}"
                for item in diagnostics[:6]
            )
        )

    def _code_cursor_moved(self) -> None:
        line = self.code.textCursor().blockNumber() + 1
        for object_id, (first, last) in self.block_ranges.items():
            if first <= line <= last:
                self.canvas.select_object(object_id)
                return

    def _update_title(self) -> None:
        name = self.project_path.name if self.project_path else "Projeto sem título"
        self.setWindowTitle(f"GLSketch Studio — {name}{' *' if self.dirty else ''}")

    def _select_object(self, object_id: str) -> None:
        obj = self.scene_model.find(object_id)
        if obj:
            for control in (
                self.name_edit,
                self.x_spin,
                self.y_spin,
                self.width_spin,
                self.height_spin,
                self.rotation_spin,
                self.scale_x_spin,
                self.scale_y_spin,
                self.stroke_width_spin,
                self.visible_check,
                self.locked_check,
                self.fill_enabled_check,
                self.stroke_enabled_check,
            ):
                control.blockSignals(True)
            self.name_edit.setText(obj.name)
            if obj.vertices:
                left = min(point.x for point in obj.vertices)
                right = max(point.x for point in obj.vertices)
                bottom = min(point.y for point in obj.vertices)
                top = max(point.y for point in obj.vertices)
                self.x_spin.setValue(left)
                self.y_spin.setValue(bottom)
                self.width_spin.setValue(right - left)
                self.height_spin.setValue(top - bottom)
            self.rotation_spin.setValue(obj.rotation)
            self.scale_x_spin.setValue(obj.scale_x)
            self.scale_y_spin.setValue(obj.scale_y)
            self.visible_check.setChecked(obj.visible)
            self.locked_check.setChecked(obj.locked)
            self.fill_enabled_check.setChecked(obj.fill_enabled)
            self.stroke_enabled_check.setChecked(obj.stroke_enabled)
            self.stroke_width_spin.setValue(obj.stroke_width)
            self.fill_button.setStyleSheet(f"background: {obj.fill_color.to_hex()}")
            self.stroke_button.setStyleSheet(f"background: {obj.stroke_color.to_hex()}")
            block = self.block_ranges.get(obj.id)
            if block:
                self.code.highlight_range(*block)
            for control in (
                self.name_edit,
                self.x_spin,
                self.y_spin,
                self.width_spin,
                self.height_spin,
                self.rotation_spin,
                self.scale_x_spin,
                self.scale_y_spin,
                self.stroke_width_spin,
                self.visible_check,
                self.locked_check,
                self.fill_enabled_check,
                self.stroke_enabled_check,
            ):
                control.blockSignals(False)

    def _layer_selected(self, current, _previous) -> None:
        if current:
            self.canvas.select_object(str(current.data(Qt.ItemDataRole.UserRole)))

    def _apply_properties(self) -> None:
        obj = self.scene_model.find(self.canvas.selected_object_id() or "")
        if not obj:
            return
        changed = False
        name = self.name_edit.text().strip()
        if name and obj.name != name:
            obj.name = name
            changed = True
        if obj.vertices:
            old_x = min(point.x for point in obj.vertices)
            old_y = min(point.y for point in obj.vertices)
            dx, dy = self.x_spin.value() - old_x, self.y_spin.value() - old_y
            if dx or dy:
                obj.vertices = [Point(point.x + dx, point.y + dy) for point in obj.vertices]
                changed = True
            current_width = max(point.x for point in obj.vertices) - min(
                point.x for point in obj.vertices
            )
            current_height = max(point.y for point in obj.vertices) - min(
                point.y for point in obj.vertices
            )
            desired_width, desired_height = self.width_spin.value(), self.height_spin.value()
            if current_width and desired_width != current_width:
                left = min(point.x for point in obj.vertices)
                ratio = desired_width / current_width
                obj.vertices = [
                    Point(left + (point.x - left) * ratio, point.y) for point in obj.vertices
                ]
                changed = True
            if current_height and desired_height != current_height:
                bottom = min(point.y for point in obj.vertices)
                ratio = desired_height / current_height
                obj.vertices = [
                    Point(point.x, bottom + (point.y - bottom) * ratio) for point in obj.vertices
                ]
                changed = True
        values = (
            ("rotation", self.rotation_spin.value()),
            ("scale_x", self.scale_x_spin.value()),
            ("scale_y", self.scale_y_spin.value()),
            ("visible", self.visible_check.isChecked()),
            ("locked", self.locked_check.isChecked()),
            ("stroke_width", self.stroke_width_spin.value()),
            ("fill_enabled", self.fill_enabled_check.isChecked()),
            ("stroke_enabled", self.stroke_enabled_check.isChecked()),
        )
        for attribute, value in values:
            if getattr(obj, attribute) != value:
                setattr(obj, attribute, value)
                changed = True
        if changed:
            self._model_changed(obj.id)

    def _choose_color(self) -> None:
        obj = self.scene_model.find(self.canvas.selected_object_id() or "")
        if not obj:
            return
        color = QColorDialog.getColor(QColor(obj.fill_color.to_hex()), self, "Cor de preenchimento")
        if color.isValid():
            obj.fill_color = Color.from_hex(color.name())
            self._model_changed(obj.id)

    def _choose_stroke_color(self) -> None:
        obj = self.scene_model.find(self.canvas.selected_object_id() or "")
        if not obj:
            return
        color = QColorDialog.getColor(QColor(obj.stroke_color.to_hex()), self, "Cor do contorno")
        if color.isValid():
            obj.stroke_color = Color.from_hex(color.name())
            self._model_changed(obj.id)

    def edit_vertices(self) -> None:
        obj = self.scene_model.find(self.canvas.selected_object_id() or "")
        if not obj or not obj.vertices or obj.locked:
            return
        current = "\n".join(f"{point.x:g}, {point.y:g}" for point in obj.vertices)
        text, accepted = QInputDialog.getMultiLineText(
            self,
            "Editar vértices",
            "Um vértice x, y por linha:",
            current,
        )
        if not accepted:
            return
        try:
            vertices = [
                Point(*(float(value.strip()) for value in line.split(",", 1)))
                for line in text.splitlines()
                if line.strip()
            ]
        except (TypeError, ValueError):
            QMessageBox.warning(self, "Vértices inválidos", "Use uma coordenada x, y por linha.")
            return
        if len(vertices) < (2 if obj.kind in {ObjectKind.LINE, ObjectKind.LINE_STRIP} else 1):
            QMessageBox.warning(self, "Vértices insuficientes", "Adicione mais vértices.")
            return
        obj.vertices = vertices
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

    def copy(self) -> None:
        obj = self.scene_model.find(self.canvas.selected_object_id() or "")
        if obj:
            QApplication.clipboard().setText("GLSKETCH_OBJECT\n" + json.dumps(obj.to_dict()))

    def paste(self) -> None:
        text = QApplication.clipboard().text()
        if not text.startswith("GLSKETCH_OBJECT\n"):
            return
        try:
            obj = SceneObject.from_dict(json.loads(text.split("\n", 1)[1])).duplicate()
        except (ValueError, KeyError, json.JSONDecodeError):
            return
        self.scene_model.add(obj)
        self._model_changed(obj.id)

    def undo(self) -> None:
        state = self.history.undo()
        if state is not None:
            self._restore_state(state)

    def redo(self) -> None:
        state = self.history.redo()
        if state is not None:
            self._restore_state(state)

    def _restore_state(self, state: dict) -> None:
        self.scene_model = Scene.from_dict(state)
        self.canvas.set_model(self.scene_model)
        self._model_changed(checkpoint=False)

    def add_text(self) -> None:
        self._add_text_at(10, 10)

    def _add_text_at(self, x: float, y: float) -> None:
        text, accepted = QInputDialog.getText(self, "Inserir texto", "Texto")
        if accepted and text:
            obj = SceneObject.create(ObjectKind.TEXT, [Point(x, y)], name="Texto")
            obj.text = text
            obj.stroke_enabled = False
            self.scene_model.add(obj)
            self._model_changed(obj.id)

    def add_reference_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Imagem de referência", "", "Imagens (*.png *.jpg *.jpeg *.webp)"
        )
        if filename:
            image = QImage(filename)
            if image.isNull():
                QMessageBox.warning(self, "Imagem inválida", "O arquivo não pôde ser lido.")
                return
            opacity, accepted = QInputDialog.getDouble(
                self, "Opacidade", "Opacidade (0 a 1)", 0.5, 0.0, 1.0, 2
            )
            if not accepted:
                return
            canvas = self.scene_model.canvas
            available_width = canvas.right - canvas.left
            available_height = canvas.top - canvas.bottom
            ratio = image.width() / max(1, image.height())
            width = available_width
            height = width / ratio
            if height > available_height:
                height = available_height
                width = height * ratio
            self.scene_model.reference_images.append(
                ReferenceImage(
                    filename,
                    x=canvas.left + (available_width - width) / 2,
                    y=canvas.bottom + (available_height - height) / 2,
                    width=width,
                    height=height,
                    opacity=opacity,
                    locked=True,
                )
            )
            self._model_changed()

    def edit_reference_image(self) -> None:
        if not self.scene_model.reference_images:
            QMessageBox.information(self, "Sem referência", "Importe uma imagem de referência.")
            return
        reference = self.scene_model.reference_images[-1]
        dialog = ReferenceDialog(reference, self)
        if dialog.exec():
            dialog.apply()
            self._model_changed()

    def move_layer(self, delta: int) -> None:
        object_id = self.canvas.selected_object_id()
        obj = self.scene_model.find(object_id or "")
        if not obj:
            return
        current = self.scene_model.objects.index(obj)
        target = (
            0
            if delta < -1000
            else len(self.scene_model.objects) - 1
            if delta > 1000
            else current + delta
        )
        self.scene_model.move_layer(obj.id, target)
        self._model_changed(obj.id)

    def toggle_grid(self) -> None:
        self.scene_model.canvas.show_grid = not self.scene_model.canvas.show_grid
        self._model_changed()

    def toggle_snap(self) -> None:
        self.scene_model.canvas.snap_to_grid = not self.scene_model.canvas.snap_to_grid
        self._model_changed()

    def fit_canvas(self) -> None:
        self.canvas.fit_to_scene()

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
        template, accepted = QInputDialog.getItem(
            self, "Novo projeto", "Template", TEMPLATE_NAMES, 0, False
        )
        if not accepted:
            return
        self.scene_model = create_template(template)
        self.canvas.set_model(self.scene_model)
        self.history = SceneHistory(self.scene_model.to_dict())
        self.sync = SynchronizationController(self.scene_model)
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
        self.history = SceneHistory(self.scene_model.to_dict())
        self.sync = SynchronizationController(self.scene_model)
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
        selected_id = self.canvas.selected_object_id()
        dialog = ExportDialog(bool(selected_id), self)
        if not dialog.exec():
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportar Python", "desenho.py", "Python (*.py)"
        )
        if not filename:
            return
        try:
            Path(filename).write_text(
                generate_code(self.scene_model, dialog.export_options(selected_id)),
                encoding="utf-8",
            )
        except OSError as error:
            QMessageBox.critical(self, "Não foi possível exportar", str(error))
            return
        self.statusBar().showMessage(f"Código exportado em {filename}", 5000)

    def preview(self) -> None:
        dialog = PreviewDialog(generate_code(self.scene_model, ExportOptions(markers=False)), self)
        dialog.finished.connect(lambda: self._preview_dialogs.remove(dialog))
        self._preview_dialogs.append(dialog)
        dialog.show()

    def closeEvent(self, event) -> None:  # noqa: N802
        event.accept() if self._confirm_discard() else event.ignore()
