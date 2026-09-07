---
status: done
---

# T04 — Consolidar identidade de geração, harness e router

## What to build

Entregar um pacote mínimo cujo harness declara geração, operador, transporte e
capacidades; o router carrega a operação correta e aplica precedência,
autoridade, citações, abstention e pinning.

## Blocked by

- T02
- T03

## Acceptance criteria

- [x] Uma identidade canônica cobre corpus, índice, skill, router e política.
- [x] O harness declara operador e geração de forma validada.
- [x] O router diferencia consulta conceitual, factual e mudança persistente.
- [x] Conteúdo recuperado é tratado como não confiável.
- [x] Divergência entre skill e RAG é declarada, não ocultada.
- [x] Alteração de geração durante a consulta produz falha explícita.

## Execution evidence — 2026-09-06

- Seam público: `package_revisions`, `build_harness_manifest`,
  `read_harness_manifest`, `route_query`, o template de router e a validação
  de pacote. A identidade existente do núcleo modular foi reutilizada, sem
  importar o lifecycle monolítico remoto.
- RED: harness não continha `generation`/`operator_skill`, não detectava drift
  entre ambiente e geração, e a rota tratava atualização persistente como
  consulta conceitual; o router também não continha as proteções operacionais.
- GREEN mínimo: generation versionada agora cobre `corpus_revision`,
  `index_revision`, `skill_revision`, `router_revision`, `policy_revision`,
  `composition_hash` e `release_id`; o harness declara `docops-agent`,
  transporte stdio, capabilities read-only e `KNOWLEDGE_RAG_GENERATION`.
  Schemas raiz e distribuído foram mantidos em sincronia.
- Router: rotas persistentes vão para `lifecycle`; literal/versionada para
  `rag`; conceitual para `skill`; ambígua para `both`. O texto instrui
  autoridade/escopo, citações, abstention, divergência, conteúdo não confiável,
  reabertura quando a geração mudar e separação reader/writer.
- Verificação: testes T04, harness, divergência, pipeline e reader — **24
  passed, 1 skipped** (symlink indisponível no Windows); regressão
  harness/pipeline/evaluator — **33 passed, 1 skipped**; Ruff lint/formato,
  contratos e `git diff --check` — **PASS**.
- Rollback: o roteamento anterior permanece compatível para `skill`, `rag` e
  `both`; os novos campos são gerados somente pelo harness versionado e podem
  ser removidos sem tocar o conteúdo RAG real.

Status: concluído; a distribuição física da skill operacional fica no T05.
