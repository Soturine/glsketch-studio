from glsketch.codegen import generate_code
from glsketch.domain import Color, Point, Scene, SceneObject
from glsketch.sync import SynchronizationController, patch_object_blocks


def _scene() -> Scene:
    return Scene(objects=[SceneObject.rectangle(Point(10, 20), Point(30, 40))])


def test_code_edit_updates_scene_color_and_vertex() -> None:
    scene = _scene()
    code = (
        generate_code(scene)
        .replace("glColor3f(0.18, 0.55, 0.96)", "glColor3f(0.0, 1.0, 0.0)")
        .replace("glVertex2f(10.0, 20.0)", "glVertex2f(15.0, 20.0)", 1)
    )
    outcome = SynchronizationController(scene).from_code(code)
    assert outcome.applied
    assert outcome.scene.objects[0].fill_color == Color(0, 1, 0)
    assert outcome.scene.objects[0].vertices[0] == Point(15, 20)


def test_invalid_code_keeps_last_valid_scene() -> None:
    scene = _scene()
    controller = SynchronizationController(scene)
    outcome = controller.from_code("glColor3f(1.0,")
    assert not outcome.applied
    assert outcome.scene.to_dict() == scene.to_dict()


def test_scene_update_preserves_unknown_text() -> None:
    scene = _scene()
    code = generate_code(scene).replace("import sys", 'import sys\nprint("preservar")')
    scene.objects[0].fill_color = Color(1, 0, 0)
    updated = patch_object_blocks(code, scene)
    assert 'print("preservar")' in updated
    assert "glColor3f(1.0, 0.0, 0.0)" in updated


def test_scene_update_adds_and_removes_blocks() -> None:
    scene = _scene()
    code = generate_code(scene)
    removed_id = scene.objects[0].id
    scene.remove(removed_id)
    added = SceneObject.triangle(Point(0, 0), Point(10, 10))
    scene.add(added)
    updated = patch_object_blocks(code, scene)
    assert removed_id not in updated
    assert added.id in updated
    assert "glBegin(GL_TRIANGLES)" in updated
