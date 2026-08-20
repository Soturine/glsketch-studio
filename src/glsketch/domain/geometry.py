from __future__ import annotations

from glsketch.domain.objects import Point


def polygon_area(vertices: list[Point]) -> float:
    return (
        sum(
            point.x * vertices[(index + 1) % len(vertices)].y
            - vertices[(index + 1) % len(vertices)].x * point.y
            for index, point in enumerate(vertices)
        )
        / 2
    )


def is_convex(vertices: list[Point]) -> bool:
    if len(vertices) < 4:
        return True
    signs = []
    for index in range(len(vertices)):
        a, b, c = vertices[index - 2], vertices[index - 1], vertices[index]
        cross = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)
        if cross:
            signs.append(cross > 0)
    return not signs or all(sign == signs[0] for sign in signs)


def _inside_triangle(point: Point, a: Point, b: Point, c: Point) -> bool:
    def cross(p1: Point, p2: Point, p3: Point) -> float:
        return (p2.x - p1.x) * (p3.y - p1.y) - (p2.y - p1.y) * (p3.x - p1.x)

    values = (cross(a, b, point), cross(b, c, point), cross(c, a, point))
    return not (any(value < 0 for value in values) and any(value > 0 for value in values))


def triangulate(vertices: list[Point]) -> list[tuple[Point, Point, Point]]:
    """Triangulate a simple polygon with deterministic ear clipping."""
    if len(vertices) < 3:
        return []
    working = list(vertices if polygon_area(vertices) > 0 else reversed(vertices))
    triangles: list[tuple[Point, Point, Point]] = []
    guard = len(working) ** 2
    while len(working) > 3 and guard:
        guard -= 1
        for index, current in enumerate(working):
            previous = working[index - 1]
            following = working[(index + 1) % len(working)]
            cross = (current.x - previous.x) * (following.y - current.y) - (
                current.y - previous.y
            ) * (following.x - current.x)
            if cross <= 0:
                continue
            others = [point for point in working if point not in {previous, current, following}]
            if any(_inside_triangle(point, previous, current, following) for point in others):
                continue
            triangles.append((previous, current, following))
            working.pop(index)
            break
        else:
            raise ValueError("Polygon must be simple and non-self-intersecting")
    if len(working) == 3:
        triangles.append(tuple(working))
    return triangles
