# Arquitetura

O `Scene` é a fonte de verdade. Objetos de domínio não importam Qt: a interface adapta o modelo para um `OpenGLCanvas` baseado em `QOpenGLWidget`, e toda geometria visível é emitida por PyOpenGL. Persistência e geração de código consomem o mesmo modelo.

```text
QOpenGLWidget/PyOpenGL ← Scene → Gerador Legacy PyOpenGL → Editor
                           ↕
                    Projeto .glsketch
```

PySide6 organiza janela, menus, editor, propriedades e layers. O canvas usa `initializeGL`, `resizeGL` e `paintGL`; grid, eixos, formas, seleção e imagens de referência são renderizados com OpenGL imediato. Hit testing, drag, resize, edição de vértices, zoom, pan e snap são cálculos Python sobre o modelo, sem `QGraphicsScene`, `QGraphicsItem` ou `QPainter` como renderer geométrico.

Imagens de referência são carregadas por `QImage` apenas como dados de pixels e enviadas a texturas com `glTexImage2D`; não entram na geometria nem no código exportado.

O pacote é separado em `domain`, `ui`, `codegen`, `parsing`, `persistence` e `commands`. Essa fronteira permite testar geometria e sincronização sem iniciar uma interface gráfica. Consulte [sincronização bidirecional](bidirectional-sync.md) e [subconjunto OpenGL](supported-opengl.md).
