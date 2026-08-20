APP_STYLESHEET = """
QMainWindow, QDialog { background: #f4f6fa; color: #172033; }
QMenuBar, QMenu, QToolBar { background: #ffffff; color: #172033; }
QToolBar { border: 0; border-bottom: 1px solid #d8dee9; spacing: 6px; padding: 6px; }
QSplitter::handle { background: #d8dee9; width: 2px; height: 2px; }
QListWidget, QPlainTextEdit, QLineEdit, QDoubleSpinBox {
    background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px;
}
QListWidget::item { padding: 7px; border-radius: 7px; }
QListWidget::item:selected { background: #dbeafe; color: #1e3a8a; }
QListWidget::item:hover { background: #eef2ff; }
QListWidget#ToolPalette { background: #f8fafc; padding: 5px; }
QListWidget#ToolPalette::item { border: 1px solid transparent; padding: 4px; }
QListWidget#ToolPalette::item:selected {
    background: #e0e7ff; border: 1px solid #818cf8; color: #312e81;
}
QListWidget#ToolPalette::item:hover { background: #ffffff; border: 1px solid #c7d2fe; }
QPushButton {
    background: #ffffff; border: 1px solid #b8c2d1; border-radius: 6px; padding: 6px 10px;
}
QPushButton:hover { border-color: #2563eb; background: #eff6ff; }
QPushButton:focus, QLineEdit:focus, QDoubleSpinBox:focus, QListWidget:focus {
    border: 2px solid #2563eb;
}
QLabel#WelcomeCard {
    background: #eaf2ff; color: #1e3a8a; border: 1px solid #bfdbfe;
    border-radius: 7px; padding: 8px;
}
QLabel#SectionHeading { color: #475569; font-weight: 700; padding: 6px 2px 2px 2px; }
QStatusBar { background: #172033; color: #ffffff; }
"""
