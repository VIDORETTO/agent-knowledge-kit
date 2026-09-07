---
status: done
---

# T09 — Consolidar readers pinados e snapshots RAG

## What to build

Entregar uma consulta factual que usa release e snapshot fixos e um plano de
reaproveitamento que só aceita índice compatível. Comprovar o comportamento
contra um backend RAG real e seus estados de erro.

## Blocked by

- T03
- T04
- T07

## Acceptance criteria

- [x] Sessão fixa release e snapshot do início ao fim.
- [x] Snapshot inclui corpus, perfil, modelo, configuração e artefatos.
- [x] Mudança de perfil exige rebuild completo.
- [x] Reuse parcial ou incompatível é recusado.
- [x] Erro terminal, timeout, índice vazio e resposta malformada não viram sucesso.
- [x] Revogação invalida resultados, sessão e snapshot dependentes.
- [x] O smoke real exige resultado e citação válidos quando aplicável.

## Evidence

- RED: a CLI não aceitava `--snapshot` na criação de reader; uma revogação
  marcada em `rag/sources.json` também passava pelo detector por usar
  `destination` singular; e o smoke MCP aceitava locators sem citação.
- GREEN: readers persistem `release_id`, `composition_hash` e a identidade
  compacta do snapshot em estado separado; cada consulta revalida o snapshot
  contra corpus, configuração, modelo, artefatos e estado de revogação.
  Snapshots são relativos ao pacote e não carregam caminhos absolutos ou
  segredos. Mudança de perfil, configuração, modelo, backend ou artefato
  escolhe `full_rebuild` com `reused_count=0`.
- Verificação: `tests/test_reader_sessions.py`,
  `tests/test_rag_snapshots.py` e `tests/test_rag_sync.py` passaram
  (`24 passed`); os dois processos MCP reais de reader/read-only e documento
  revogado passaram (`2 passed`). O snapshot inclui hashes do corpus,
  release, embedding/modelo, configuração redigida, inventário de artefatos e
  tombstones; resultados com locators exigem citação válida.
- Nenhuma consulta de manutenção, reindexação real ou alteração do corpus/RAG
  persistente foi executada por este ticket.

## Rollback

Reverter `rag_sync.py`, `reader_sessions.py`, os contratos de snapshot/reader
e os argumentos `--snapshot`; remover apenas o diretório externo
`.<package>.readers` das fixtures se necessário. A reversão não toca o
conteúdo ativo nem o backend RAG.
