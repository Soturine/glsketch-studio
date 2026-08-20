from __future__ import annotations

from dataclasses import dataclass

from glsketch.domain.objects import ObjectKind, Point, SceneObject
from glsketch.domain.scene import Scene


@dataclass(frozen=True, slots=True)
class ExportOptions:
    full_program: bool = True
    markers: bool = True
    comments: bool = True
    selected_ids: frozenset[str] | None = None
    prefer_integers: bool | None = None


_PRIMITIVES = {
    ObjectKind.LINE: "GL_LINES",
    ObjectKind.LINE_STRIP: "GL_LINE_STRIP",
    ObjectKind.LINE_LOOP: "GL_LINE_LOOP",
    ObjectKind.RECTANGLE: "GL_QUADS",
    ObjectKind.TRIANGLE: "GL_TRIANGLES",
    ObjectKind.POLYGON: "GL_POLYGON",
    ObjectKind.ELLIPSE: "GL_TRIANGLE_FAN",
}


def _number(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if "." in text else f"{text}.0"


def _vertex(point: Point, prefer_integers: bool) -> str:
    if prefer_integers and point.x.is_integer() and point.y.is_integer():
        return f"glVertex2i({int(point.x)}, {int(point.y)})"
    return f"glVertex2f({_number(point.x)}, {_number(point.y)})"


def _object_lines(obj: SceneObject, prefer_integers: bool, markers: bool) -> list[str]:
    lines: list[str] = []
    if markers:
        lines.append(f'# <glsketch-object id="{obj.id}" name="{obj.name}">')
    color = (
        obj.stroke_color
        if obj.kind in {ObjectKind.LINE, ObjectKind.LINE_STRIP, ObjectKind.LINE_LOOP}
        else obj.fill_color
    )
    lines.append(f"glColor3f({_number(color.r)}, {_number(color.g)}, {_number(color.b)})")
    if obj.stroke_width != 1.0:
        lines.append(f"glLineWidth({_number(obj.stroke_width)})")
    if obj.rotation or obj.scale_x != 1.0 or obj.scale_y != 1.0:
        lines.append("glPushMatrix()")
        if obj.rotation:
            lines.append(f"glRotatef({_number(obj.rotation)}, 0.0, 0.0, 1.0)")
        if obj.scale_x != 1.0 or obj.scale_y != 1.0:
            lines.append(f"glScalef({_number(obj.scale_x)}, {_number(obj.scale_y)}, 1.0)")
    if obj.kind == ObjectKind.TEXT:
        anchor = obj.vertices[0]
        lines.append(f"glRasterPos2f({_number(anchor.x)}, {_number(anchor.y)})")
        lines.append(f"for char in {obj.text!r}:")
        lines.append("    glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))")
    else:
        lines.append(f"glBegin({_PRIMITIVES[obj.kind]})")
        if obj.kind == ObjectKind.ELLIPSE and obj.vertices:
            cx = sum(point.x for point in obj.vertices) / len(obj.vertices)
            cy = sum(point.y for point in obj.vertices) / len(obj.vertices)
            lines.append(_vertex(Point(cx, cy), prefer_integers))
        lines.extend(_vertex(point, prefer_integers) for point in obj.vertices)
        if obj.kind == ObjectKind.ELLIPSE and obj.vertices:
            lines.append(_vertex(obj.vertices[0], prefer_integers))
        lines.append("glEnd()")
    if obj.rotation or obj.scale_x != 1.0 or obj.scale_y != 1.0:
        lines.append("glPopMatrix()")
    if markers:
        lines.append("# </glsketch-object>")
    return lines


def generate_draw_body(scene: Scene, options: ExportOptions | None = None) -> str:
    options = options or ExportOptions(full_program=False)
    prefer_integers = (
        scene.canvas.prefer_integers if options.prefer_integers is None else options.prefer_integers
    )
    blocks = []
    for obj in scene.objects:
        if not obj.visible or (
            options.selected_ids is not None and obj.id not in options.selected_ids
        ):
            continue
        blocks.append("\n".join(_object_lines(obj, prefer_integers, options.markers)))
    return "\n\n".join(blocks)


def generate_code(scene: Scene, options: ExportOptions | None = None) -> str:
    options = options or ExportOptions()
    body = generate_draw_body(scene, options)
    if not options.full_program:
        return body + ("\n" if body else "")
    c = scene.canvas
    indented = "\n".join(f"    {line}" if line else "" for line in body.splitlines())
    if not indented:
        indented = "    pass"
    heading = (
        "# Gerado pelo GLSketch Studio — Modo Aula / Legacy OpenGL\n" if options.comments else ""
    )
    return f"""{heading}from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys


def Desenha():
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glClear(GL_COLOR_BUFFER_BIT)

{indented}

    glFlush()


def Inicializa():
    glClearColor(0.0, 0.0, 0.0, 1.0)


def AlteraTamanhoJanela(w, h):
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D({_number(c.left)}, {_number(c.right)}, {_number(c.bottom)}, {_number(c.top)})


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutInitWindowSize(900, 700)
    glutInitWindowPosition(10, 10)
    glutCreateWindow(b"GLSketch Studio Preview")
    glutDisplayFunc(Desenha)
    glutReshapeFunc(AlteraTamanhoJanela)
    Inicializa()
    glutMainLoop()


if __name__ == "__main__":
    main()
"""
