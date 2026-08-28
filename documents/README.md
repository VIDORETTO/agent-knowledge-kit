# documents/ — corpus local do RAG

Este diretório é uma área de trabalho para fontes que o usuário autorizou. O
pipeline `docops` normalmente grava o corpus de cada pacote em
`<pacote>/rag/documents`; não coloque material adquirido neste diretório para
publicação sem conferir a licença.

## Convenções de pasta (usadas por `category_mappings` no config.yaml)

```text
documents/
├── fixtures/         → fixtures sintéticas versionáveis
├── examples/         → exemplos fictícios versionáveis
└── <fonte-adquirida>/ → ignorada até haver revisão de licença
```

O `config.yaml` do servidor usa `category_mappings: {}` por padrão; pacotes
gerados registram a origem em `rag/sources.json`.

## Estado atual

- `examples/` e `fixtures/` contêm somente documentação sintética para validar
  os pipelines de ponta a ponta.
- Fontes reais devem ser adquiridas para um pacote privado, com
  `--license <identificador>` e revisão de redistribuição.

## Formato ideal de um documento indexado

1. Front-matter do título (`# Título`) na primeira linha.
2. Um parágrafo de resumo com os termos que coletarão buscas (ex.: nomes de
   funções, endpoints, palavras-chave).
3. Seções com `##`/`###` — o chunker corta respeitando esses limites.
4. Exemplos de código com o problema/recurso que representam.