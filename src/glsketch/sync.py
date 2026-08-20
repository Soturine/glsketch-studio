from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum

from glsketch.codegen.generator import ExportOptions, generate_code, generate_draw_body
from glsketch.domain.scene import Scene
from glsketch.parsing import Diagnostic, ParseResult, parse_code


class ChangeOrigin(StrEnum):
    CANVAS = "canvas"
    CODE = "code"
    PROPERTIES = "properties"
    LOAD = "load"


@dataclass(slots=True)
class SyncOutcome:
    scene: Scene
    code: str
    diagnostics: list[Diagnostic]
    applied: bool
    block_ranges: dict[str, tuple[int, int]]


_BLOCK = re.compile(
    r'(?ms)^[ \t]*#\s*<glsketch-object\s+id="(?P<id>[^"]+)"[^\n]*>.*?'
    r"^[ \t]*#\s*</glsketch-object>\s*$"
)


def patch_object_blocks(code: str, scene: Scene) -> str:
    """Update known generated blocks while preserving all other user text."""
    if not code.strip() or not _BLOCK.search(code):
        return generate_code(scene)
    objects = {obj.id: obj for obj in scene.objects}
    seen: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        object_id = match.group("id")
        obj = objects.get(object_id)
        if obj is None:
            return ""
        seen.add(object_id)
        block = generate_draw_body(
            Scene(objects=[obj], canvas=scene.canvas), ExportOptions(full_program=False)
        ).rstrip()
        indentation = re.match(r"^[ \t]*", match.group(0)).group(0)
        return "\n".join(indentation + line if line else "" for line in block.splitlines())

    updated = _BLOCK.sub(replace, code)
    missing = [obj for obj in scene.objects if obj.visible and obj.id not in seen]
    if missing:
        blocks = generate_draw_body(
            Scene(objects=missing, canvas=scene.canvas), ExportOptions(full_program=False)
        )
        insertion = "\n".join("    " + line if line else "" for line in blocks.splitlines())
        marker = updated.find("    glFlush()")
        updated = (
            updated[:marker] + insertion + "\n\n" + updated[marker:]
            if marker >= 0
            else updated.rstrip() + "\n\n" + blocks + "\n"
        )
    return updated


class SynchronizationController:
    def __init__(self, scene: Scene | None = None) -> None:
        self.last_valid_scene = Scene.from_dict((scene or Scene()).to_dict())
        self.origin: ChangeOrigin | None = None

    @contextmanager
    def changing(self, origin: ChangeOrigin) -> Iterator[None]:
        previous = self.origin
        self.origin = origin
        try:
            yield
        finally:
            self.origin = previous

    def from_code(self, code: str) -> SyncOutcome:
        result: ParseResult = parse_code(code)
        if result.valid and result.scene is not None:
            self.last_valid_scene = Scene.from_dict(result.scene.to_dict())
            return SyncOutcome(result.scene, code, result.diagnostics, True, result.block_ranges)
        stable = Scene.from_dict(self.last_valid_scene.to_dict())
        return SyncOutcome(stable, code, result.diagnostics, False, result.block_ranges)

    def from_scene(self, scene: Scene, current_code: str = "") -> SyncOutcome:
        self.last_valid_scene = Scene.from_dict(scene.to_dict())
        code = patch_object_blocks(current_code, scene)
        parsed = parse_code(code)
        return SyncOutcome(scene, code, parsed.diagnostics, True, parsed.block_ranges)
