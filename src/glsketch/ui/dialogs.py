from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QTemporaryDir, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from glsketch.codegen import ExportOptions
from glsketch.domain.scene import ReferenceImage


class ReferenceDialog(QDialog):
    def __init__(self, reference: ReferenceImage, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Imagem de referência")
        self.reference = reference
        self.x = self._spin(-10000, 10000, reference.x)
        self.y = self._spin(-10000, 10000, reference.y)
        self.width = self._spin(0.01, 10000, reference.width)
        self.opacity = self._spin(0, 1, reference.opacity)
        self.visible = QCheckBox("Visível")
        self.visible.setChecked(reference.visible)
        self.locked = QCheckBox("Bloqueada")
        self.locked.setChecked(reference.locked)
        form = QFormLayout()
        form.addRow("X", self.x)
        form.addRow("Y", self.y)
        form.addRow("Largura", self.width)
        form.addRow("Opacidade", self.opacity)
        form.addRow(self.visible)
        form.addRow(self.locked)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Não será exportada como geometria."))
        layout.addLayout(form)
        layout.addWidget(buttons)

    @staticmethod
    def _spin(minimum: float, maximum: float, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(3)
        spin.setValue(value)
        return spin

    def apply(self) -> None:
        ratio = self.reference.height / max(self.reference.width, 1e-9)
        self.reference.x = self.x.value()
        self.reference.y = self.y.value()
        self.reference.width = self.width.value()
        self.reference.height = self.reference.width * ratio
        self.reference.opacity = self.opacity.value()
        self.reference.visible = self.visible.isChecked()
        self.reference.locked = self.locked.isChecked()


class ExportDialog(QDialog):
    def __init__(self, has_selection: bool, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportar Python/PyOpenGL")
        self.scope = QComboBox()
        self.scope.addItem("Código completo", "full")
        self.scope.addItem("Somente função Desenha()", "draw")
        if has_selection:
            self.scope.addItem("Somente primitivas selecionadas", "selected")
        self.comments = QCheckBox("Incluir comentários")
        self.comments.setChecked(True)
        self.markers = QCheckBox("Incluir marcadores GLSketch")
        self.integers = QCheckBox("Preferir coordenadas inteiras")
        form = QFormLayout()
        form.addRow("Conteúdo", self.scope)
        form.addRow(self.comments)
        form.addRow(self.markers)
        form.addRow(self.integers)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Modo Aula / Legacy OpenGL"))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def export_options(self, selected_id: str | None) -> ExportOptions:
        scope = self.scope.currentData()
        return ExportOptions(
            full_program=scope == "full",
            draw_function_only=scope == "draw",
            markers=self.markers.isChecked(),
            comments=self.comments.isChecked(),
            selected_ids=frozenset({selected_id}) if scope == "selected" and selected_id else None,
            prefer_integers=self.integers.isChecked(),
        )


class PreviewDialog(QDialog):
    def __init__(self, code: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preview OpenGL")
        self.resize(700, 360)
        self.temporary = QTemporaryDir("glsketch-preview-XXXXXX")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.status = QLabel("Iniciando preview em subprocesso isolado…")
        self.stop_button = QPushButton("Encerrar preview")
        self.stop_button.clicked.connect(self.stop)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.output, 1)
        layout.addWidget(self.stop_button)
        layout.addWidget(buttons)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.finished.connect(self._finished)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.setInterval(30_000)
        self.timeout.timeout.connect(self._timeout)
        target = Path(self.temporary.path()) / "preview.py"
        target.write_text(code, encoding="utf-8")
        self.process.setWorkingDirectory(self.temporary.path())
        arguments = (
            ["--glsketch-preview", str(target)]
            if getattr(sys, "frozen", False)
            else [str(target)]
        )
        self.process.start(sys.executable, arguments)
        self.timeout.start()

    def _read_output(self) -> None:
        self.output.appendPlainText(
            bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        )

    def _finished(self, exit_code: int, _status) -> None:
        self.timeout.stop()
        self._read_output()
        self.status.setText(f"Preview encerrado (código {exit_code}).")
        self.stop_button.setEnabled(False)

    def _timeout(self) -> None:
        self.status.setText("Limite de 30 s atingido; encerrando o preview.")
        self.stop()

    def stop(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.stop()
        event.accept()
