# GLSketch Studio

Editor visual 2D para criar desenhos com primitivas geométricas e sincronizá-los com código Python/PyOpenGL. O modelo de cena é independente da interface e a exportação usa OpenGL imediato no estilo de disciplinas introdutórias.

## Recursos

- Canvas vetorial com grid, snap, seleção, movimento, zoom e pan.
- Linha, retângulo, triângulo e elipse.
- Código Legacy OpenGL atualizado a partir do desenho.
- Projetos JSON versionados em `.glsketch`.
- Exportação de programa `.py` completo e preview GLUT em subprocesso.
- Layers, renomear, cores, duplicar e excluir.

## Instalação no Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
python -m glsketch
```

No Prompt de Comando, ative com `.venv\Scripts\activate.bat`. Em Linux/macOS, use `python3 -m venv .venv`, `source .venv/bin/activate` e os mesmos comandos `pip`/`python`.

## Uso

Escolha uma ferramenta à esquerda, desenhe no canvas e veja o código à direita. Salve o projeto pelo menu **Arquivo** ou exporte um programa PyOpenGL executável. Consulte [atalhos](docs/shortcuts.md), [arquitetura](docs/architecture.md), [gerador](docs/code-generator.md) e [formato do projeto](docs/project-format.md).

## Desenvolvimento

```powershell
ruff check .
pytest
```

O código usa `src/glsketch`, com módulos separados para domínio, UI, geração, parsing, persistência e histórico. Veja [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- v0.2: polígonos, layers avançadas, referência, undo/redo e edição de vértices.
- v0.3: parser seguro e sincronização código → desenho.
- v1.0: produto refinado, exemplos e documentação completa.

Licenciado sob [MIT](LICENSE).
