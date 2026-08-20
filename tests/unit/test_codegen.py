from glsketch.codegen import ExportOptions, generate_code
from glsketch.domain import Color, ObjectKind, Point, Scene, SceneObject


def test_rectangle_generates_legacy_opengl() -> None:
    scene = Scene(
        objects=[SceneObject.rectangle(Point(20, 30), Point(60, 50), fill_color=Color(1, 0, 0))]
    )
    code = generate_code(scene)
    assert "glBegin(GL_QUADS)" in code
    assert "glColor3f(1.0, 0.0, 0.0)" in code
    assert "glVertex2f(20.0, 30.0)" in code
    assert "gluOrtho2D(0.0, 100.0, 0.0, 100.0)" in code
    compile(code, "generated.py", "exec")


def test_clean_export_removes_markers() -> None:
    scene = Scene(objects=[SceneObject.triangle(Point(0, 0), Point(10, 10))])
    code = generate_code(scene, ExportOptions(markers=False, comments=False))
    assert "glsketch-object" not in code
    assert "Gerado pelo" not in code


def test_integer_preference_uses_vertex2i() -> None:
    scene = Scene(objects=[SceneObject.rectangle(Point(0, 0), Point(10, 10))])
    scene.canvas.prefer_integers = True
    assert "glVertex2i(0, 0)" in generate_code(scene)


def test_concave_polygon_uses_triangles() -> None:
    polygon = SceneObject.create(
        ObjectKind.POLYGON,
        [Point(0, 0), Point(4, 0), Point(4, 4), Point(2, 2), Point(0, 4)],
    )
    code = generate_code(Scene(objects=[polygon]), ExportOptions(markers=False))
    assert "glBegin(GL_TRIANGLES)" in code
    assert "Polígono côncavo triangulado" in code
