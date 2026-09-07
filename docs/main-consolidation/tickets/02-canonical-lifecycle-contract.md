---
status: done
---

# T02 — Definir lifecycle, estado e compatibilidade canônicos

## What to build

Entregar uma fatia pública que represente uma fonte desde o registro até um
status de lifecycle consultável, usando uma única máquina de estados, uma
fachada pública e um layout de runtime versionado. Definir a migração dos
estados concorrentes e a política expand-contract.

## Blocked by

- T01

## Acceptance criteria

- [x] Existe uma única máquina de estados normativa.
- [x] A fachada pública expõe status sem revelar detalhes internos.
- [x] O runtime fica fora da geração ativa e possui versão.
- [x] Estados legados são detectados e migrados ou rejeitados de forma segura.
- [x] A matriz de compatibilidade cobre CLI, JSON, exit codes e artefatos.
- [x] Testes observam somente seams públicos.

## Execution evidence — 2026-09-06

- Seam público: `docops.LifecycleFacade`, `LifecycleStateMachine` e o
  envelope `lifecycle-status`; nenhum teste acessa tabela, helper privado ou
  caminho de armazenamento.
- RED: `tests/test_main_consolidation.py` começou com quatro falhas por
  `AttributeError: LifecycleFacade`.
- GREEN mínimo: `docops/lifecycle.py` criou uma fachada única sobre
  `operations.plan/apply/preview`, uma máquina de estados normativa e um
  `runtime.json` externo com `schema_version=1`/`layout_version=1`. A raiz
  exporta aliases `Lifecycle`, `CanonicalLifecycle` e `lifecycle_status`.
- Migração: marcador de schema/layout incompatível e runtimes legados são
  reportados como `runtime_schema_unsupported`, `runtime_layout_unsupported`
  ou `runtime_migration_required`, sem sobrescrever o arquivo inválido.
- Contrato: `schemas/lifecycle-status.schema.json` e sua cópia distribuída
  validam o envelope versionado; a projeção redige caminhos privados e não
  expõe SQLite.
- Verificação: `rtk pytest -q tests/test_main_consolidation.py` — **4 passed**;
  suíte de área (`test_main_consolidation`, interface, seams e pipeline) —
  **29 passed, 1 skipped** (symlink indisponível no Windows); contratos,
  Ruff lint/formato, `compileall` e `git diff --check` — **PASS**.
- Rollback: remover a fachada do ponto de entrada mantém os módulos legados;
  runtime inválido permanece intacto e nenhuma geração ativa é alterada.

Status: concluído; compatibilidade antiga permanece para o ticket T06.
