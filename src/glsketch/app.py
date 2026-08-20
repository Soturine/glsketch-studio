from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('PySide6 não está instalado. Execute: pip install -e ".[dev]"', file=sys.stderr)
        return 2

    from glsketch.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("GLSketch Studio")
    app.setOrganizationName("Soturine")
    window = MainWindow()
    window.show()
    return app.exec()
