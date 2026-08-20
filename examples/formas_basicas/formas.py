from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys


def Desenha():
    glClear(GL_COLOR_BUFFER_BIT)
    glColor3f(0.145, 0.388, 0.922)
    glBegin(GL_QUADS)
    for x, y in ((10, 10), (10, 35), (40, 35), (40, 10)):
        glVertex2f(x, y)
    glEnd()
    glColor3f(0.918, 0.702, 0.031)
    glBegin(GL_TRIANGLES)
    for x, y in (
        (65.3, 76.5),
        (51, 76.2),
        (62.5, 67.5),
        (70, 90),
        (65.3, 76.5),
        (62.5, 67.5),
        (70, 90),
        (62.5, 67.5),
        (58.2, 53.8),
        (70, 90),
        (58.2, 53.8),
        (70, 62),
        (70, 90),
        (70, 62),
        (81.8, 53.8),
        (70, 90),
        (81.8, 53.8),
        (77.5, 67.5),
        (77.5, 67.5),
        (89, 76.2),
        (74.7, 76.5),
        (77.5, 67.5),
        (74.7, 76.5),
        (70, 90),
    ):
        glVertex2f(x, y)
    glEnd()
    glColor3f(0.72, 0.35, 0.02)
    glLineWidth(2)
    glBegin(GL_LINE_LOOP)
    for x, y in (
        (70, 90),
        (74.7, 76.5),
        (89, 76.2),
        (77.5, 67.5),
        (81.8, 53.8),
        (70, 62),
        (58.2, 53.8),
        (62.5, 67.5),
        (51, 76.2),
        (65.3, 76.5),
    ):
        glVertex2f(x, y)
    glEnd()
    glFlush()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutCreateWindow(b"Formas GLSketch")
    gluOrtho2D(0, 100, 0, 100)
    glutDisplayFunc(Desenha)
    glutMainLoop()


if __name__ == "__main__":
    main()
