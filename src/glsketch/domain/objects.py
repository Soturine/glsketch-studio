from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from math import cos, pi, sin
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def to_list(self) -> list[float]:
        return [self.x, self.y]


@dataclass(frozen=True, slots=True)
class Color:
    r: float
    g: float
    b: float
    a: float = 1.0

    def __post_init__(self) -> None:
        if any(not 0.0 <= channel <= 1.0 for channel in (self.r, self.g, self.b, self.a)):
            raise ValueError("Color channels must be between 0 and 1")

    @classmethod
    def from_hex(cls, value: str) -> Color:
        text = value.strip().lstrip("#")
        if len(text) not in {6, 8}:
            raise ValueError("Expected #RRGGBB or #RRGGBBAA")
        channels = [int(text[index : index + 2], 16) / 255 for index in range(0, len(text), 2)]
        return cls(*channels) if len(channels) == 4 else cls(*channels, 1.0)

    def to_hex(self, include_alpha: bool = False) -> str:
        channels = (self.r, self.g, self.b, self.a) if include_alpha else (self.r, self.g, self.b)
        return "#" + "".join(f"{round(channel * 255):02X}" for channel in channels)

    def to_list(self) -> list[float]:
        return [self.r, self.g, self.b, self.a]


class ObjectKind(StrEnum):
    LINE = "line"
    LINE_STRIP = "line_strip"
    LINE_LOOP = "line_loop"
    RECTANGLE = "rectangle"
    TRIANGLE = "triangle"
    POLYGON = "polygon"
    ELLIPSE = "ellipse"
    TEXT = "text"


@dataclass(slots=True)
class SceneObject:
    id: str
    name: str
    kind: ObjectKind
    vertices: list[Point]
    fill_color: Color = field(default_factory=lambda: Color(0.18, 0.55, 0.96))
    stroke_color: Color = field(default_factory=lambda: Color(0.08, 0.12, 0.18))
    stroke_width: float = 1.0
    visible: bool = True
    locked: bool = False
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        kind: ObjectKind,
        vertices: list[Point],
        *,
        name: str | None = None,
        fill_color: Color | None = None,
    ) -> SceneObject:
        label = kind.value.replace("_", " ").title()
        return cls(
            id=f"obj-{uuid4().hex[:12]}",
            name=name or label,
            kind=kind,
            vertices=list(vertices),
            fill_color=fill_color or Color(0.18, 0.55, 0.96),
        )

    @classmethod
    def rectangle(cls, start: Point, end: Point, **kwargs: Any) -> SceneObject:
        left, right = sorted((start.x, end.x))
        bottom, top = sorted((start.y, end.y))
        vertices = [Point(left, bottom), Point(left, top), Point(right, top), Point(right, bottom)]
        return cls.create(ObjectKind.RECTANGLE, vertices, **kwargs)

    @classmethod
    def triangle(cls, start: Point, end: Point, **kwargs: Any) -> SceneObject:
        vertices = [
            Point((start.x + end.x) / 2, end.y),
            Point(start.x, start.y),
            Point(end.x, start.y),
        ]
        return cls.create(ObjectKind.TRIANGLE, vertices, **kwargs)

    @classmethod
    def ellipse(cls, start: Point, end: Point, segments: int = 32, **kwargs: Any) -> SceneObject:
        segments = max(8, min(256, segments))
        cx, cy = (start.x + end.x) / 2, (start.y + end.y) / 2
        rx, ry = abs(end.x - start.x) / 2, abs(end.y - start.y) / 2
        vertices = [
            Point(
                cx + rx * cos(2 * pi * index / segments), cy + ry * sin(2 * pi * index / segments)
            )
            for index in range(segments)
        ]
        obj = cls.create(ObjectKind.ELLIPSE, vertices, **kwargs)
        obj.metadata["segments"] = segments
        return obj

    def translated(self, dx: float, dy: float) -> SceneObject:
        return replace(
            self, vertices=[Point(point.x + dx, point.y + dy) for point in self.vertices]
        )

    def duplicate(self, offset: float = 2.0) -> SceneObject:
        result = self.translated(offset, offset)
        result.id = f"obj-{uuid4().hex[:12]}"
        result.name = f"{self.name} cópia"
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.kind.value,
            "visible": self.visible,
            "locked": self.locked,
            "z_order": 0,
            "vertices": [point.to_list() for point in self.vertices],
            "fill_color": self.fill_color.to_list(),
            "stroke_color": self.stroke_color.to_list(),
            "stroke_width": self.stroke_width,
            "rotation": self.rotation,
            "scale": [self.scale_x, self.scale_y],
            "text": self.text,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SceneObject:
        scale = data.get("scale", [1.0, 1.0])
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["type"])),
            kind=ObjectKind(data["type"]),
            vertices=[Point(float(x), float(y)) for x, y in data.get("vertices", [])],
            fill_color=Color(*map(float, data.get("fill_color", [0.18, 0.55, 0.96, 1.0]))),
            stroke_color=Color(*map(float, data.get("stroke_color", [0.08, 0.12, 0.18, 1.0]))),
            stroke_width=float(data.get("stroke_width", 1.0)),
            visible=bool(data.get("visible", True)),
            locked=bool(data.get("locked", False)),
            rotation=float(data.get("rotation", 0.0)),
            scale_x=float(scale[0]),
            scale_y=float(scale[1]),
            text=str(data.get("text", "")),
            metadata=dict(data.get("metadata", {})),
        )
