from __future__ import annotations

import json
from pathlib import Path

from glsketch.domain.scene import Scene


def save_project(scene: Scene, path: str | Path) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".glsketch":
        target = target.with_suffix(".glsketch")
    target.write_text(
        json.dumps(scene.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return target


def load_project(path: str | Path) -> Scene:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid GLSketch JSON at line {error.lineno}, column {error.colno}"
        ) from error
    return Scene.from_dict(payload, source=source)
