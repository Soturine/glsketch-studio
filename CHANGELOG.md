# Changelog

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) e versionamento SemVer.

## [1.0.0] - 2026-08-20

### Changed

- Renderer principal migrado de QGraphics para `QOpenGLWidget + PyOpenGL`.
- Grid, primitivas, seleção e overlays agora são desenhados em OpenGL imediato.
- Imagens de referência agora são texturas OpenGL.

### Added

- Testes de conformidade para canvas e exportação exclusivamente OpenGL.
- Lápis livre, quadrado, círculo, estrela e texto posicionado no canvas.
- Preenchimento/borda opcionais, cores separadas e espessura.
- Resize por alça e deformação por vértices.
- Templates, exemplos e preview controlável em subprocesso.
- Launcher Windows com instalação automática e workflow de pacote portátil.
- Opções de escopo, marcadores, comentários e coordenadas na exportação.
- Testes de UI, performance com 500 objetos e projetos de exemplo.
- Paleta premium com ícones vetoriais próprios para todas as ferramentas.

### Fixed

- Round-trip de texto, polígonos côncavos e estilos de forma.
- Seleção do canvas OpenGL agora atualiza propriedades e bloco de código.
- Estrelas orientadas corretamente e trianguladas no canvas e no código gerado.

### Known limitations

- Python arbitrário permanece somente código e nunca é executado pelo parser.
- Autosave/recovery não sobrescreve projetos: a v1 prioriza salvamento explícito confiável.
- O editor numérico configura a imagem de referência mais recentemente importada.

## [0.3.0] - 2026-08-20

### Added

- Editor de código com numeração de linhas e destaque de sintaxe.
- Parser seguro baseado em AST para OpenGL imediato suportado.
- Sincronização código → cena com debounce de 350 ms.
- Diagnósticos por severidade, linha e coluna.
- Seleção sincronizada entre blocos de código e objetos.
- Testes de round-trip para formas, cores, layers e transformações.

### Changed

- Atualizações visuais preservam texto externo aos blocos GLSketch.
- Código temporariamente inválido mantém a última cena válida.

### Known limitations

- Python arbitrário permanece somente código e nunca é executado pelo parser.

## [0.2.0] - 2026-08-20

### Added

- Polígonos, linhas contínuas/fechadas e texto.
- Triangulação determinística de polígonos côncavos na exportação.
- Undo/redo, copiar, colar e duplicar com novos IDs.
- Imagens de referência não exportáveis.
- Controles numéricos de posição, rotação, escala, visibilidade e bloqueio.
- Reordenação de camadas e alternância de grid/snap.

### Changed

- Canvas e histórico agora tratam edições visuais como transações da cena.

### Known limitations

- Edição direta do código chega na v0.3.0.

## [0.1.0] - 2026-08-20

### Added

- Modelo de cena independente da UI.
- Canvas Qt com linha, retângulo, triângulo e elipse, seleção, movimento, zoom, grid e snap.
- Geração em tempo real de código Legacy OpenGL.
- Formato `.glsketch`, abrir, salvar e exportar `.py`.
- Layers, propriedades básicas, duplicação e preview em subprocesso.
- Testes unitários e CI em Windows e Linux.

### Known limitations

- O editor de código é somente leitura nesta milestone.
- Undo/redo e ferramentas avançadas chegam nas milestones seguintes.
