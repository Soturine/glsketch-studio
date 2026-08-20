from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys


def Desenha():
    glClear(GL_COLOR_BUFFER_BIT)
    glColor3f(0.965, 0.757, 0.467)
    glBegin(GL_QUADS)
    for x, y in ((25, 15), (25, 55), (75, 55), (75, 15)):
        glVertex2f(x, y)
    glEnd()
    glColor3f(0.761, 0.255, 0.231)
    glBegin(GL_TRIANGLES)
    for x, y in ((20, 55), (50, 85), (80, 55)):
        glVertex2f(x, y)
    glEnd()
    glFlush()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutCreateWindow(b"Casa GLSketch")
    gluOrtho2D(0, 100, 0, 100)
    glutDisplayFunc(Desenha)
    glutMainLoop()


if __name__ == "__main__":
    main()
