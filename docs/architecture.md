# Arquitetura

O `Scene` é a fonte de verdade. Objetos de domínio não importam Qt: a interface apenas adapta o modelo para `QGraphicsItem`. Persistência e geração de código também consomem o mesmo modelo.

```text
Canvas / Propriedades → Scene → Gerador Legacy OpenGL → Editor
                           ↕
                    Projeto .glsketch
```

O pacote é separado em `domain`, `ui`, `codegen`, `parsing`, `persistence` e `commands`. Essa fronteira permite testar geometria e sincronização sem iniciar uma interface gráfica. Consulte [sincronização bidirecional](bidirectional-sync.md) e [subconjunto OpenGL](supported-opengl.md).
