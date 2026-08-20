from __future__ import annotations

from PySide6.QtCore import QRect, QRegularExpression, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        keyword = QTextCharFormat()
        keyword.setForeground(QColor("#7C3AED"))
        keyword.setFontWeight(QFont.Weight.Bold)
        function = QTextCharFormat()
        function.setForeground(QColor("#0369A1"))
        comment = QTextCharFormat()
        comment.setForeground(QColor("#64748B"))
        string = QTextCharFormat()
        string.setForeground(QColor("#15803D"))
        number = QTextCharFormat()
        number.setForeground(QColor("#B45309"))
        self.rules = [
            (QRegularExpression(r"\b(def|for|in|if|else|import|from|as|return|pass)\b"), keyword),
            (QRegularExpression(r"\b(gl[A-Z]\w*|glu\w+|glut\w+)\b"), function),
            (QRegularExpression(r"#[^\n]*"), comment),
            (QRegularExpression(r"(['\"]).*?\1"), string),
            (QRegularExpression(r"\b\d+(?:\.\d+)?\b"), number),
        ]

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for expression, text_format in self.rules:
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), text_format)


class LineNumberArea(QWidget):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.editor.line_number_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self.editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.line_numbers = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_margin)
        self.updateRequest.connect(self._update_line_numbers)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._special_selections: list[QTextEdit.ExtraSelection] = []
        self._update_margin()
        self._highlight_current_line()
        self.highlighter = PythonHighlighter(self.document())

    def line_number_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margin(self) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_line_numbers(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_numbers.scroll(0, dy)
        else:
            self.line_numbers.update(0, rect.y(), self.line_numbers.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margin()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        contents = self.contentsRect()
        self.line_numbers.setGeometry(
            QRect(contents.left(), contents.top(), self.line_number_width(), contents.height())
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self.line_numbers)
        painter.fillRect(event.rect(), QColor("#F1F5F9"))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#64748B"))
                painter.drawText(
                    0,
                    top,
                    self.line_numbers.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    def _highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#EEF2FF"))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection, *self._special_selections])

    def highlight_range(self, first_line: int, last_line: int, *, error: bool = False) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#FEE2E2" if error else "#DBEAFE"))
        cursor = QTextCursor(self.document().findBlockByLineNumber(max(0, first_line - 1)))
        end = self.document().findBlockByLineNumber(max(0, last_line - 1))
        cursor.setPosition(end.position() + end.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        self._special_selections = [selection]
        self._highlight_current_line()

    def clear_special_highlight(self) -> None:
        self._special_selections = []
        self._highlight_current_line()
