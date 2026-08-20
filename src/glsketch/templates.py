from __future__ import annotations

from glsketch.domain.objects import Color, ObjectKind, Point, SceneObject
from glsketch.domain.scene import Scene

TEMPLATE_NAMES = ("Em branco", "Casa básica", "Formas geométricas", "Bandeira em branco")


def create_template(name: str) -> Scene:
    scene = Scene(title=name)
    if name == "Em branco":
        return scene
    if name == "Casa básica":
        house = SceneObject.rectangle(
            Point(25, 15), Point(75, 55), name="Parede", fill_color=Color.from_hex("#F6C177")
        )
        roof = SceneObject.create(
            ObjectKind.TRIANGLE,
            [Point(20, 55), Point(50, 85), Point(80, 55)],
            name="Telhado",
            fill_color=Color.from_hex("#C2413B"),
        )
        door = SceneObject.rectangle(
            Point(43, 15), Point(57, 42), name="Porta", fill_color=Color.from_hex("#7C4A2D")
        )
        scene.objects.extend([house, roof, door])
    elif name == "Formas geométricas":
        scene.objects.extend(
            [
                SceneObject.rectangle(
                    Point(10, 10),
                    Point(40, 35),
                    name="Retângulo",
                    fill_color=Color.from_hex("#2563EB"),
                ),
                SceneObject.triangle(
                    Point(55, 10),
                    Point(90, 40),
                    name="Triângulo",
                    fill_color=Color.from_hex("#16A34A"),
                ),
                SceneObject.ellipse(
                    Point(10, 52),
                    Point(42, 86),
                    name="Elipse",
                    fill_color=Color.from_hex("#EAB308"),
                ),
                SceneObject.star(
                    Point(58, 50),
                    Point(92, 88),
                    name="Estrela",
                    fill_color=Color.from_hex("#A855F7"),
                ),
            ]
        )
    elif name == "Bandeira em branco":
        scene.canvas.right = 150.0
        scene.objects.append(
            SceneObject.rectangle(
                Point(0, 0),
                Point(150, 100),
                name="Campo da bandeira",
                fill_color=Color(1, 1, 1),
            )
        )
    else:
        raise ValueError(f"Template desconhecido: {name}")
    return scene
