# Subconjunto OpenGL suportado

O canvas principal e o exportador compartilham o mesmo `Scene Model` e usam exclusivamente PyOpenGL. PySide6 fornece o contexto por `QOpenGLWidget`, mas não renderiza as formas. Não são usados Pygame, Turtle, QGraphics, Matplotlib, Cairo, ModernGL ou outro motor gráfico.

| Função/primitiva | Visual → código | Código → visual | Exportável | Observações |
|---|---:|---:|---:|---|
| `glColor3f` | Sim | Sim | Sim | Literais entre 0 e 1 |
| `glVertex2i`, `glVertex2f` | Sim | Sim | Sim | Literais numéricos |
| `GL_LINES` | Sim | Sim | Sim | Pares de vértices |
| `GL_LINE_STRIP` | Sim | Sim | Sim | Linha contínua |
| `GL_LINE_LOOP` | Sim | Sim | Sim | Contorno fechado |
| `GL_TRIANGLES` | Sim | Sim | Sim | Triângulos |
| `GL_TRIANGLE_FAN` | Sim | Sim | Sim | Elipses geradas pelo app |
| `GL_QUADS` | Sim | Sim | Sim | Retângulos didáticos |
| `GL_POLYGON` | Sim | Sim | Sim | Côncavos são triangulados |
| `glTranslatef` | N/A | Sim | Sim | Aplicada aos vértices importados |
| `glRotatef` | Sim | Sim | Sim | Eixo Z nos blocos gerados |
| `glScalef` | Sim | Sim | Sim | Escala X/Y |
| `glPushMatrix`, `glPopMatrix` | Sim | Sim | Sim | Padrão de bloco gerado |

Python ou OpenGL fora desse subconjunto nunca é executado pelo editor. Texto válido permanece exportável e recebe aviso “somente código”.

Imagens de referência usam `GL_TEXTURE_2D`/`glTexImage2D` somente no canvas. Elas nunca são incluídas na exportação de geometria.

Formas amigáveis que não existem como primitivas nativas são decompostas: círculos/elipses usam `GL_TRIANGLE_FAN`, estrelas usam um polígono triangulado e bordas usam `GL_LINE_LOOP`.
