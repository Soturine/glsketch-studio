import pytest

from glsketch.codegen import generate_code
from glsketch.domain import Color, ObjectKind, Point, Scene, SceneObject
from glsketch.parsing import Severity, parse_code


@pytest.mark.parametrize(
    ("kind", "vertices"),
    [
        (ObjectKind.RECTANGLE, [Point(1, 2), Point(1, 8), Point(9, 8), Point(9, 2)]),
        (ObjectKind.TRIANGLE, [Point(5, 9), Point(1, 2), Point(9, 2)]),
        (ObjectKind.POLYGON, [Point(1, 1), Point(8, 1), Point(9, 6), Point(4, 9)]),
        (ObjectKind.LINE, [Point(1, 2), Point(9, 8)]),
        (ObjectKind.LINE_STRIP, [Point(1, 2), Point(5, 8), Point(9, 2)]),
        (ObjectKind.LINE_LOOP, [Point(1, 2), Point(5, 8), Point(9, 2)]),
    ],
)
def test_shape_round_trip(kind: ObjectKind, vertices: list[Point]) -> None:
    original = SceneObject.create(kind, vertices, fill_color=Color(0.1, 0.2, 0.3))
    result = parse_code(generate_code(Scene(objects=[original])))
    assert result.valid
    assert result.scene is not None
    parsed = result.scene.objects[0]
    assert parsed.id == original.id
    assert parsed.kind == kind
    assert parsed.vertices == vertices
    expected_color = (
        original.stroke_color
        if kind in {ObjectKind.LINE, ObjectKind.LINE_STRIP, ObjectKind.LINE_LOOP}
        else original.fill_color
    )
    assert parsed.fill_color == expected_color


def test_ellipse_round_trip() -> None:
    ellipse = SceneObject.ellipse(Point(10, 20), Point(50, 60), segments=24)
    result = parse_code(generate_code(Scene(objects=[ellipse])))
    assert result.valid and result.scene
    assert result.scene.objects[0].kind == ObjectKind.ELLIPSE
    parsed = result.scene.objects[0].vertices
    assert len(parsed) == len(ellipse.vertices)
    for actual, expected in zip(parsed, ellipse.vertices, strict=True):
        assert actual.x == pytest.approx(expected.x, abs=1e-6)
        assert actual.y == pytest.approx(expected.y, abs=1e-6)


def test_transform_round_trip() -> None:
    obj = SceneObject.rectangle(Point(0, 0), Point(10, 10))
    obj.rotation, obj.scale_x, obj.scale_y = 30, 1.5, 0.75
    result = parse_code(generate_code(Scene(objects=[obj])))
    assert result.valid and result.scene
    parsed = result.scene.objects[0]
    assert (parsed.rotation, parsed.scale_x, parsed.scale_y) == (30, 1.5, 0.75)


def test_translate_is_applied_to_vertices() -> None:
    code = """# <glsketch-object id="obj-1" name="Linha">
glPushMatrix()
glTranslatef(10.0, 20.0, 0.0)
glBegin(GL_LINES)
glVertex2f(1.0, 2.0)
glVertex2f(3.0, 4.0)
glEnd()
glPopMatrix()
# </glsketch-object>
"""
    result = parse_code(code)
    assert result.valid and result.scene
    assert result.scene.objects[0].vertices == [Point(11, 22), Point(13, 24)]


def test_layer_order_round_trip() -> None:
    first = SceneObject.rectangle(Point(0, 0), Point(10, 10), name="Fundo")
    second = SceneObject.triangle(Point(20, 20), Point(30, 30), name="Topo")
    result = parse_code(generate_code(Scene(objects=[first, second])))
    assert result.valid and result.scene
    assert [obj.id for obj in result.scene.objects] == [first.id, second.id]


def test_clean_code_without_markers_is_parsed() -> None:
    code = """
def Desenha():
    glColor3f(1.0, 0.0, 0.0)
    glBegin(GL_TRIANGLES)
    glVertex2i(0, 0)
    glVertex2f(5.0, 10.0)
    glVertex2i(10, 0)
    glEnd()
"""
    result = parse_code(code)
    assert result.valid and result.scene
    assert result.scene.objects[0].kind == ObjectKind.TRIANGLE


def test_invalid_temporary_code_has_diagnostic() -> None:
    result = parse_code("glColor3f(1.0,")
    assert not result.valid
    assert result.scene is None
    assert result.diagnostics[0].severity == Severity.ERROR
    assert result.diagnostics[0].line == 1


def test_vertex_outside_begin_is_an_error() -> None:
    code = """# <glsketch-object id="obj-1" name="Inválido">
glVertex2f(1.0, 2.0)
# </glsketch-object>
"""
    result = parse_code(code)
    assert not result.valid
    assert any("fora de glBegin" in item.message for item in result.diagnostics)


def test_unsupported_statement_is_preserved_as_warning() -> None:
    code = """# <glsketch-object id="obj-1" name="Triângulo">
print("preservar")
glBegin(GL_TRIANGLES)
glVertex2f(0.0, 0.0)
glVertex2f(5.0, 10.0)
glVertex2f(10.0, 0.0)
glEnd()
# </glsketch-object>
"""
    result = parse_code(code)
    assert result.valid
    assert any(item.severity == Severity.WARNING for item in result.diagnostics)
    assert 2 in result.unsupported_lines
