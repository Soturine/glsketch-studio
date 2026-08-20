# Sincronização bidirecional

O `SynchronizationController` coordena quatro origens (`CANVAS`, `CODE`, `PROPERTIES`, `LOAD`) e mantém uma cópia da última cena válida. Alterações do canvas atualizam somente blocos identificados no texto; alterações do editor passam por `ast.parse` após debounce de 350 ms.

```text
Canvas → Scene → patch de blocos → Código
Código → AST seguro → Scene válida → Canvas
                     └ erro → última Scene válida
```

Não há `eval` nem `exec`. Durante código temporariamente inválido, o editor mostra linha, coluna e mensagem, enquanto o canvas continua renderizando o último estado válido. Quando o texto volta a ser válido, a atualização é aplicada como uma única transação.

Marcadores `glsketch-object` associam identidade e intervalo de linhas a cada objeto. Texto fora deles é preservado. Blocos desconhecidos são classificados como “somente código”; erros são destacados sem traceback na interface.

