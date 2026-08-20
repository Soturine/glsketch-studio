from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from glsketch.domain.objects import SceneObject


@dataclass(slots=True)
class CanvasSettings:
    left: float = 0.0
    right: float = 100.0
    bottom: float = 0.0
    top: float = 100.0
    grid_size: float = 5.0
    show_grid: bool = True
    snap_to_grid: bool = True
    prefer_integers: bool = False
    background: str = "#F8FAFC"

    def to_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanvasSettings:
        known = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
        return cls(**known)


@dataclass(slots=True)
class ReferenceImage:
    path: str
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    opacity: float = 0.5
    visible: bool = True
    locked: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in self.__dataclass_fields__}


@dataclass(slots=True)
class Scene:
    objects: list[SceneObject] = field(default_factory=list)
    canvas: CanvasSettings = field(default_factory=CanvasSettings)
    reference_images: list[ReferenceImage] = field(default_factory=list)
    title: str = "Projeto sem título"

    def add(self, obj: SceneObject, index: int | None = None) -> None:
        if self.find(obj.id) is not None:
            raise ValueError(f"Duplicate object id: {obj.id}")
        self.objects.insert(len(self.objects) if index is None else index, obj)

    def find(self, object_id: str) -> SceneObject | None:
        return next((obj for obj in self.objects if obj.id == object_id), None)

    def remove(self, object_id: str) -> SceneObject:
        for index, obj in enumerate(self.objects):
            if obj.id == object_id:
                return self.objects.pop(index)
        raise KeyError(object_id)

    def move_layer(self, object_id: str, index: int) -> None:
        obj = self.remove(object_id)
        self.objects.insert(max(0, min(index, len(self.objects))), obj)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "glsketch",
            "version": 1,
            "title": self.title,
            "canvas": self.canvas.to_dict(),
            "objects": [
                obj.to_dict() | {"z_order": index} for index, obj in enumerate(self.objects)
            ],
            "reference_images": [image.to_dict() for image in self.reference_images],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, source: Path | None = None) -> Scene:
        if data.get("format") != "glsketch":
            raise ValueError("Not a GLSketch project")
        if data.get("version") != 1:
            raise ValueError(f"Unsupported GLSketch version: {data.get('version')}")
        objects = sorted(data.get("objects", []), key=lambda item: item.get("z_order", 0))
        references = []
        for raw in data.get("reference_images", []):
            item = dict(raw)
            if source and item.get("path") and not Path(item["path"]).is_absolute():
                item["path"] = str((source.parent / item["path"]).resolve())
            references.append(ReferenceImage(**item))
        return cls(
            objects=[SceneObject.from_dict(item) for item in objects],
            canvas=CanvasSettings.from_dict(data.get("canvas", {})),
            reference_images=references,
            title=str(data.get("title", "Projeto sem título")),
        )
