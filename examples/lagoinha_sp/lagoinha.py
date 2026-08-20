from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys


def Desenha():
    glClear(GL_COLOR_BUFFER_BIT)
    # Aguardando confirmação de uma referência oficial da bandeira.
    glFlush()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutCreateWindow(b"Lagoinha-SP - referencia pendente")
    gluOrtho2D(0, 150, 0, 100)
    glutDisplayFunc(Desenha)
    glutMainLoop()


if __name__ == "__main__":
    main()
