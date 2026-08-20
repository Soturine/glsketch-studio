from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass, field
from enum import StrEnum

from glsketch.domain.objects import Color, ObjectKind, Point, SceneObject
from glsketch.domain.scene import Scene


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: Severity
    message: str
    line: int = 1
    column: int = 1


@dataclass(slots=True)
class ParseResult:
    scene: Scene | None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    block_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)
    unsupported_lines: list[int] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.scene is not None and not any(
            item.severity == Severity.ERROR for item in self.diagnostics
        )


_START = re.compile(
    r'^\s*#\s*<glsketch-object\s+id="(?P<id>[^"]+)"\s+name="(?P<name>[^"]*)"'
    r'(?:\s+type="(?P<type>[^"]+)")?>\s*$'
)
_END = re.compile(r"^\s*#\s*</glsketch-object>\s*$")
_KINDS = {
    "GL_LINES": ObjectKind.LINE,
    "GL_LINE_STRIP": ObjectKind.LINE_STRIP,
    "GL_LINE_LOOP": ObjectKind.LINE_LOOP,
    "GL_TRIANGLES": ObjectKind.TRIANGLE,
    "GL_QUADS": ObjectKind.RECTANGLE,
    "GL_POLYGON": ObjectKind.POLYGON,
    "GL_TRIANGLE_FAN": ObjectKind.ELLIPSE,
}
_SUPPORTED = {
    "glColor3f",
    "glBegin",
    "glVertex2i",
    "glVertex2f",
    "glEnd",
    "glPushMatrix",
    "glPopMatrix",
    "glTranslatef",
    "glRotatef",
    "glScalef",
    "glLineWidth",
    "glRasterPos2f",
}


def _number(node: ast.expr) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _number(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    raise ValueError("expected a numeric literal")


def _call(statement: ast.stmt) -> tuple[str, list[ast.expr]] | None:
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return None
    function = statement.value.func
    if not isinstance(function, ast.Name):
        return None
    return function.id, statement.value.args


def _parse_block(
    statements: list[ast.stmt],
    object_id: str,
    name: str,
    line_offset: int,
    type_hint: str | None = None,
) -> tuple[SceneObject | None, list[Diagnostic], list[int]]:
    diagnostics: list[Diagnostic] = []
    unsupported: list[int] = []
    color = Color(0.18, 0.55, 0.96)
    stroke_width = 1.0
    primitive: str | None = None
    current_vertices: list[Point] = []
    batches: list[tuple[str, list[Point], Color, float]] = []
    translate_x = translate_y = rotation = 0.0
    scale_x = scale_y = 1.0
    raster_position: Point | None = None
    text_value = ""
    for statement in statements:
        parsed = _call(statement)
        line = line_offset + statement.lineno - 1
        if (
            isinstance(statement, ast.For)
            and isinstance(statement.iter, ast.Constant)
            and isinstance(statement.iter.value, str)
        ):
            text_value = statement.iter.value
            continue
        if parsed is None or parsed[0] not in _SUPPORTED:
            unsupported.append(line)
            diagnostics.append(
                Diagnostic(Severity.WARNING, "Trecho válido, mas somente código", line)
            )
            continue
        function, args = parsed
        try:
            if function == "glColor3f" and len(args) == 3:
                color = Color(*(_number(arg) for arg in args))
            elif function == "glLineWidth" and len(args) == 1:
                stroke_width = _number(args[0])
            elif function == "glRasterPos2f" and len(args) == 2:
                raster_position = Point(_number(args[0]), _number(args[1]))
            elif function == "glBegin" and len(args) == 1 and isinstance(args[0], ast.Name):
                if primitive is not None:
                    diagnostics.append(Diagnostic(Severity.ERROR, "glBegin aninhado", line))
                primitive = args[0].id
                current_vertices = []
            elif function in {"glVertex2f", "glVertex2i"} and len(args) == 2:
                if primitive is None:
                    diagnostics.append(
                        Diagnostic(Severity.ERROR, f"{function} fora de glBegin/glEnd", line)
                    )
                current_vertices.append(Point(_number(args[0]), _number(args[1])))
            elif function == "glEnd":
                if primitive is None:
                    diagnostics.append(Diagnostic(Severity.ERROR, "glEnd sem glBegin", line))
                else:
                    batches.append((primitive, current_vertices, color, stroke_width))
                    primitive = None
                    current_vertices = []
            elif function == "glTranslatef" and len(args) >= 2:
                translate_x, translate_y = _number(args[0]), _number(args[1])
            elif function == "glRotatef" and args:
                rotation = _number(args[0])
            elif function == "glScalef" and len(args) >= 2:
                scale_x, scale_y = _number(args[0]), _number(args[1])
            elif function in {"glPushMatrix", "glPopMatrix"}:
                continue
            else:
                diagnostics.append(
                    Diagnostic(Severity.ERROR, f"Chamada {function} incompleta ou inválida", line)
                )
        except ValueError as error:
            diagnostics.append(Diagnostic(Severity.ERROR, f"{function}: {error}", line))
    if raster_position is not None and primitive is None:
        obj = SceneObject(
            id=object_id,
            name=name or "Texto",
            kind=ObjectKind.TEXT,
            vertices=[raster_position],
            fill_color=color,
            stroke_color=color,
            text=text_value,
            fill_enabled=True,
            stroke_enabled=False,
        )
        return obj, diagnostics, unsupported
    if primitive is not None:
        diagnostics.append(Diagnostic(Severity.ERROR, f"{primitive} sem glEnd()", line_offset))
    if not batches:
        diagnostics.append(Diagnostic(Severity.ERROR, "Bloco sem glBegin suportado", line_offset))
        return None, diagnostics, unsupported
    if any(batch[0] not in _KINDS for batch in batches):
        unsupported_primitive = next(batch[0] for batch in batches if batch[0] not in _KINDS)
        diagnostics.append(
            Diagnostic(
                Severity.WARNING,
                f"Primitiva {unsupported_primitive} ainda não suportada",
                line_offset,
            )
        )
        return None, diagnostics, unsupported
    hinted = ObjectKind(type_hint) if type_hint in {item.value for item in ObjectKind} else None
    line_kinds = {ObjectKind.LINE, ObjectKind.LINE_STRIP, ObjectKind.LINE_LOOP}
    if hinted in line_kinds:
        fill_batch = None
        stroke_batch = batches[0]
        kind = hinted
    else:
        fill_batch = next((batch for batch in batches if batch[0] != "GL_LINE_LOOP"), None)
        stroke_batch = next(
            (batch for batch in batches if batch[0] == "GL_LINE_LOOP" and batch is not fill_batch),
            None,
        )
        primary = fill_batch or stroke_batch or batches[0]
        kind = hinted or _KINDS[primary[0]]
    geometry_batch = fill_batch or stroke_batch or batches[0]
    vertices = list(geometry_batch[1])
    if kind == ObjectKind.ELLIPSE and len(vertices) >= 3:
        vertices = vertices[1:]
        if len(vertices) > 1 and vertices[-1] == vertices[0]:
            vertices.pop()
    vertices = [Point(point.x + translate_x, point.y + translate_y) for point in vertices]
    obj = SceneObject(
        id=object_id,
        name=name or kind.value.replace("_", " ").title(),
        kind=kind,
        vertices=vertices,
        fill_color=fill_batch[2] if fill_batch else Color(0.18, 0.55, 0.96),
        stroke_color=stroke_batch[2] if stroke_batch else geometry_batch[2],
        stroke_width=stroke_batch[3] if stroke_batch else geometry_batch[3],
        fill_enabled=fill_batch is not None,
        stroke_enabled=stroke_batch is not None,
        rotation=rotation,
        scale_x=scale_x,
        scale_y=scale_y,
    )
    return obj, diagnostics, unsupported


def _marked_blocks(code: str) -> list[tuple[str, str, str | None, int, int, str]]:
    lines = code.splitlines()
    blocks = []
    current: tuple[str, str, str | None, int] | None = None
    for index, line in enumerate(lines, start=1):
        start = _START.match(line)
        if start:
            current = (start.group("id"), start.group("name"), start.group("type"), index)
        elif _END.match(line) and current:
            object_id, name, type_hint, first = current
            blocks.append(
                (object_id, name, type_hint, first, index, "\n".join(lines[first : index - 1]))
            )
            current = None
    return blocks


def parse_code(code: str) -> ParseResult:
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return ParseResult(
            None,
            [
                Diagnostic(
                    Severity.ERROR,
                    error.msg,
                    error.lineno or 1,
                    error.offset or 1,
                )
            ],
        )
    scene = Scene()
    diagnostics: list[Diagnostic] = []
    ranges: dict[str, tuple[int, int]] = {}
    unsupported: list[int] = []
    blocks = _marked_blocks(code)
    if blocks:
        for object_id, name, type_hint, first, last, source in blocks:
            ranges[object_id] = (first, last)
            try:
                block_tree = ast.parse(textwrap.dedent(source))
            except SyntaxError as error:
                diagnostics.append(
                    Diagnostic(
                        Severity.ERROR,
                        error.msg,
                        first + (error.lineno or 1) - 1,
                        error.offset or 1,
                    )
                )
                continue
            obj, block_diagnostics, block_unsupported = _parse_block(
                block_tree.body, object_id, name, first + 1, type_hint
            )
            diagnostics.extend(block_diagnostics)
            unsupported.extend(block_unsupported)
            if obj is not None:
                scene.add(obj)
    else:
        draw = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "Desenha"
            ),
            None,
        )
        statements = draw.body if draw else tree.body
        groups: list[list[ast.stmt]] = []
        pending: list[ast.stmt] = []
        for statement in statements:
            parsed = _call(statement)
            if (
                parsed
                and parsed[0]
                in {
                    "glColor3f",
                    "glPushMatrix",
                    "glTranslatef",
                    "glRotatef",
                    "glScalef",
                }
                or parsed
                and parsed[0] == "glBegin"
            ):
                pending.append(statement)
            elif pending:
                pending.append(statement)
                if parsed and parsed[0] == "glEnd":
                    groups.append(pending)
                    pending = []
        for index, group in enumerate(groups, start=1):
            obj, extra, unknown = _parse_block(
                group, f"obj-parsed-{index:04d}", f"Objeto {index}", 1
            )
            diagnostics.extend(extra)
            unsupported.extend(unknown)
            if obj:
                scene.add(obj)
        if not groups:
            diagnostics.append(Diagnostic(Severity.INFO, "Nenhum bloco OpenGL editável encontrado"))
    if any(item.severity == Severity.ERROR for item in diagnostics):
        return ParseResult(None, diagnostics, ranges, unsupported)
    return ParseResult(scene, diagnostics, ranges, unsupported)
