# Gerador de código

O modo principal gera um programa Python/PyOpenGL completo em OpenGL imediato, compatível com o estilo da disciplina. Formas usam `glBegin`, `glVertex2f` ou `glVertex2i` e `glEnd`. Elipses são aproximadas por `GL_TRIANGLE_FAN`.

No código de edição, marcadores `glsketch-object` preservam identidade. Na exportação limpa eles podem ser removidos.

O diálogo exporta um programa completo, somente `Desenha()` ou as primitivas selecionadas. Preenchimento e borda geram passagens OpenGL separadas. Polígonos côncavos e estrelas são triangulados para evitar resultados incorretos.
