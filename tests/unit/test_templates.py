import pytest

from glsketch.codegen import ExportOptions, generate_code
from glsketch.domain import ObjectKind, Point, Scene, SceneObject
from glsketch.parsing import parse_code
from glsketch.templates import TEMPLATE_NAMES, create_template


@pytest.mark.parametrize("name", TEMPLATE_NAMES)
def test_templates_generate_valid_projects(name: str) -> None:
    scene = create_template(name)
    assert scene.title == name
    result = parse_code(generate_code(scene))
    assert result.valid


def test_export_scopes() -> None:
    first = SceneObject.rectangle(Point(0, 0), Point(10, 10))
    second = SceneObject.triangle(Point(20, 20), Point(30, 30))
    scene = Scene(objects=[first, second])
    draw = generate_code(scene, ExportOptions(full_program=False, draw_function_only=True))
    selected = generate_code(
        scene,
        ExportOptions(full_program=False, markers=False, selected_ids=frozenset({second.id})),
    )
    assert draw.startswith("def Desenha():")
    assert "GL_QUADS" not in selected
    assert "GL_TRIANGLES" in selected


def test_star_factory_has_alternating_vertices() -> None:
    star = SceneObject.star(Point(0, 0), Point(100, 100))
    assert star.kind == ObjectKind.STAR
    assert len(star.vertices) == 10
