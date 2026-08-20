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
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(70, 70)
    for x, y in (
        (70, 50),
        (74.7, 63.5),
        (89, 63.8),
        (77.5, 72.5),
        (81.8, 86.2),
        (70, 78),
        (58.2, 86.2),
        (62.5, 72.5),
        (51, 63.8),
        (65.3, 63.5),
    ):
        glVertex2f(x, y)
    glVertex2f(70, 50)
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
