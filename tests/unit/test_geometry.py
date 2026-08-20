from glsketch.domain.geometry import is_convex, triangulate
from glsketch.domain.objects import Point


def test_concave_polygon_is_triangulated() -> None:
    vertices = [Point(0, 0), Point(4, 0), Point(4, 4), Point(2, 2), Point(0, 4)]
    assert not is_convex(vertices)
    triangles = triangulate(vertices)
    assert len(triangles) == 3
    assert {point for triangle in triangles for point in triangle} == set(vertices)


def test_convex_polygon_is_detected() -> None:
    assert is_convex([Point(0, 0), Point(4, 0), Point(4, 4), Point(0, 4)])
