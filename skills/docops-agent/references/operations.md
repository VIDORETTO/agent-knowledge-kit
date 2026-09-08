# Operação do DOCOPS

## Diagnóstico e criação

```text
python -m docops doctor --json
python -m docops skill path --json
python -m docops agents-bootstrap --root <project> --json
python -m docops resolve <fonte> --json
python -m docops plan <fonte> --output <pacote> --license <id> --json
python -m docops run <fonte> --output <pacote> --license <id> --json
python -m docops validate <pacote> --json
```

`run` gera `skill/`, `router/`, corpus `rag/`, `manifest.json` e
`harness.json`. O pacote não hospeda LLM nem escolhe provedor. Use a skill
externa `book-to-skill` no harness para enriquecer o scaffold; não simule uma
IA dentro do DOCOPS.

## Estado do RAG

- `corpus-ready`: documentos normalizados e `rag/index.json` existem; a
  indexação vetorial real ainda não foi comprovada.
- `indexed`: o MCP local executou a indexação e registrou estatísticas,
  proveniência e smoke.
- `evaluated`: há Golden Set revisado e avaliação registrada.

Para indexar explicitamente, use `--index-rag` no `run` ou no job de manutenção.
Avaliação MCP exige `rag/index.json` em `indexed`. Alteração de
`models.embedding.profile` exige `reindex_documents(full_rebuild=True)`; o
sincronizador detecta o perfil anterior e força esse caminho.

## Contratos a preservar

O pacote ativo continua com `skill/`, `router/`, `rag/`, manifesto e harness.
Atualizações trabalham em staging e só promovem após validação. O manifesto
deve manter origem canônica, versão, idioma, licença, hashes, checkpoints,
revisões e readiness. Nunca use uma falha de aquisição parcial para inferir
remoção de documentos.

Antes de compartilhar um pacote, confira licença, proveniência, referências,
configuração de transporte e ausência de segredos. HTTP/SSE exige configuração
privada com bearer token, rate limit, métricas e auditoria.

Para o mapa completo de efeitos, códigos de erro, recuperação e encerramento,
use [command-cards.md](command-cards.md). Para execução recorrente, use
[scheduler-runbooks.md](scheduler-runbooks.md); agendar `work --once` não substitui
`source reconcile`.
