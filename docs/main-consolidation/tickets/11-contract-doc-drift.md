---
status: done
---

# T11 — Eliminar drift de contratos, schemas e documentação

## What to build

Entregar um contrato canônico que gera ou valida as cópias distribuídas e um
check de documentação que detecta comandos, estados, links e claims
contraditórios.

## Blocked by

- T04
- T06
- T07
- T08
- T09
- T10

## Acceptance criteria

- [x] Cada schema possui uma única fonte normativa.
- [x] Cópias empacotadas são reproduzíveis e comparadas por conteúdo.
- [x] Contratos têm versão e política de compatibilidade.
- [x] README, status, arquitetura, uso e tickets descrevem o mesmo lifecycle.
- [x] Links e comandos documentados são verificados automaticamente.
- [x] Claims de “implementado” exigem evidência de gate atual.
- [x] Documentação histórica é separada da documentação normativa.

## Evidence

- RED: `tests/test_contract_doc_drift.py` falhou na coleta porque
  `scripts.check_documentation` ainda não existia.
- GREEN/verificação: `tests/test_contract_doc_drift.py
  tests/test_post_contracts.py tests/test_main_consolidation.py` — **35 passed,
  1 skipped**; o skip é a indisponibilidade de symlink neste Windows.
- `scripts/sync_schemas.py --check --json` — **PASS**, 34 schemas sem drift.
- `scripts/check_contracts.py --json` — **PASS**, versão/política e exemplos
  consistentes.
- `scripts/check_documentation.py --json` — **PASS**, 76 documentos verificados,
  sem findings.
- Ruff lint/formato dos módulos alterados — **PASS**.

## Rollback

O rollback é local e reversível: remover os três checkers, a política de
compatibilidade e as alterações de documentação/schema, restaurando também o
campo `schema_version` do envelope de outcome. Nenhum corpus, índice RAG,
publicação ou estado externo foi alterado.
