import json
from pathlib import Path

import pytest

from glsketch.domain import Point, ReferenceImage, Scene, SceneObject
from glsketch.persistence import load_project, save_project


def test_save_load_round_trip(tmp_path) -> None:
    scene = Scene(
        objects=[SceneObject.rectangle(Point(1, 2), Point(30, 40))],
        reference_images=[ReferenceImage("reference.png", opacity=0.25)],
        title="Teste",
    )
    target = save_project(scene, tmp_path / "drawing")
    loaded = load_project(target)
    assert target.suffix == ".glsketch"
    assert loaded.title == scene.title
    assert loaded.objects[0].to_dict() == scene.objects[0].to_dict()
    assert loaded.reference_images[0].path == str((tmp_path / "reference.png").resolve())


def test_load_rejects_unknown_version(tmp_path) -> None:
    target = tmp_path / "future.glsketch"
    target.write_text(json.dumps({"format": "glsketch", "version": 99}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        load_project(target)


def test_bundled_examples_are_valid() -> None:
    root = Path(__file__).parents[2] / "examples"
    projects = sorted(root.glob("**/*.glsketch"))
    assert len(projects) == 3
    for project in projects:
        assert load_project(project).title
