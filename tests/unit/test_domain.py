from glsketch.domain import Color, ObjectKind, Point, Scene, SceneObject


def test_color_round_trip() -> None:
    color = Color.from_hex("#3366CC")
    assert color.to_hex() == "#3366CC"
    assert color.r == 0.2


def test_scene_rejects_duplicate_ids() -> None:
    scene = Scene()
    rectangle = SceneObject.rectangle(Point(10, 20), Point(30, 40))
    scene.add(rectangle)
    try:
        scene.add(rectangle)
    except ValueError as error:
        assert rectangle.id in str(error)
    else:
        raise AssertionError("Duplicate id was accepted")


def test_shape_factories_normalize_geometry() -> None:
    rectangle = SceneObject.rectangle(Point(30, 40), Point(10, 20))
    assert rectangle.kind == ObjectKind.RECTANGLE
    assert rectangle.vertices == [Point(10, 20), Point(10, 40), Point(30, 40), Point(30, 20)]
    assert len(SceneObject.ellipse(Point(0, 0), Point(20, 10), segments=24).vertices) == 24
