# Formato de projeto

Arquivos `.glsketch` são JSON UTF-8 versionado. A raiz contém `format: "glsketch"`, `version: 1`, configurações do canvas, objetos ordenados por camada e imagens de referência. Imagens permanecem externas; caminhos relativos são resolvidos a partir do projeto.

O loader rejeita formatos e versões desconhecidos para evitar perda silenciosa de dados.

