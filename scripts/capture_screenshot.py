from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from glsketch.templates import create_template
from glsketch.ui.main_window import MainWindow


def main() -> int:
    surface = QSurfaceFormat()
    surface.setVersion(2, 1)
    surface.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
    surface.setSamples(4)
    QSurfaceFormat.setDefaultFormat(surface)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.scene_model = create_template("Formas geométricas")
    window.canvas.set_model(window.scene_model)
    window.history.checkpoint(window.scene_model.to_dict())
    window._refresh_all(window.scene_model.objects[0].id)
    window.dirty = False
    window.resize(1440, 900)
    window.show()

    def capture() -> None:
        target = Path(__file__).parents[1] / "docs" / "assets" / "glsketch-studio.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(target), "PNG"):
            raise RuntimeError("Falha ao capturar screenshot")
        print(target)
        window.close()
        app.quit()

    QTimer.singleShot(1200, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
