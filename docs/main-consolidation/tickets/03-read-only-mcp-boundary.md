---
status: done
---

# T03 — Impor MCP read-only, pinning e revogação no servidor

## What to build

Entregar uma sessão factual que inicia um reader em geração fixa, permite
somente busca e leitura e falha fechada para qualquer mutação. Documentos
revogados não podem aparecer e o processo reader não pode iniciar watcher,
bootstrap ou reindex.

## Blocked by

- T02

## Acceptance criteria

- [x] Mutação é bloqueada na fronteira do servidor.
- [x] Reader e manutenção usam processos e capacidades separados.
- [x] A geração esperada é validada antes e durante a sessão.
- [x] Revogação remove resultados e invalida sessões afetadas.
- [x] Testes usam um processo MCP real, não mock interno.
- [x] Erros de configuração falham fechados com códigos estáveis.

## Execution evidence — 2026-09-06

- Seam público: ambiente `runtime_environment(..., read_only=...)`, harness
  MCP, adapter factual e ferramentas MCP; o enforcement não depende de mocks
  internos do servidor.
- RED: a configuração não possuía `Config.read_only`; depois, o writer MCP
  executou `add_document` e retornou `success` em uma sessão marcada como
  reader; por fim, o adapter não detectou alteração de geração entre duas
  buscas.
- GREEN mínimo: `KNOWLEDGE_RAG_READ_ONLY` tem precedência sobre YAML; o
  servidor não cria diretórios, Chroma, FTS5, watcher, preflight ou reindex em
  modo reader; todos os writers retornam o código estável
  `read_only_session` antes de criar o orquestrador. Writers de manutenção
  usam explicitamente `read_only=0`, enquanto retrieval/smoke usam `1`.
- Pinning e revogação: `McpRetrievalAdapter` fixa `composition_hash`,
  revalida a geração antes de cada busca e falha com `generation_changed`;
  tombstones em `.docops/revocations.json` são filtrados pelo servidor e pelo
  adapter com `source_revoked`/resultado omitido. O harness declara a fronteira
  read-only e não expõe write capabilities.
- Processo real: `tests/test_main_consolidation.py` iniciou o `.venv` MCP
  contra uma coleção Chroma sintética existente, completou handshake,
  `tools/list`, chamada negativa de writer e comparação de arquivos antes/depois;
  também comprovou revogação sem iniciar backend para o documento bloqueado.
- Verificação: testes focalizados T03 e adapter — **15 passed**; suíte vendor
  configurada no próprio ambiente do vendor — **170 passed, 7 skipped, 5
  xfailed**; Ruff lint/formato, contratos e `git diff --check` — **PASS**.
- Rollback: remover os parâmetros/guards read-only mantém o caminho writer
  modular; nenhum corpus, índice real ou geração ativa foi alterado.

Status: concluído; geração/harness/router adicionais permanecem no T04, sem
duplicar a implementação monolítica remota.
