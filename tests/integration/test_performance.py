from glsketch.codegen import generate_code
from glsketch.domain import Point, Scene, SceneObject
from glsketch.parsing import parse_code


def test_round_trip_500_simple_objects() -> None:
    scene = Scene(
        objects=[
            SceneObject.rectangle(
                Point(index % 100, index // 100),
                Point(index % 100 + 1, index // 100 + 1),
            )
            for index in range(500)
        ]
    )
    result = parse_code(generate_code(scene))
    assert result.valid and result.scene
    assert len(result.scene.objects) == 500
