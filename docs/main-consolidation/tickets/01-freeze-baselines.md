---
status: done
---

# T01 — Congelar baselines e registrar a decisão

## What to build

Criar, em uma branch de integração isolada, snapshots reproduzíveis do baseline
`main`, da branch remota e do trabalho local. Registrar hashes, inventário,
gates observados, conflito three-way e a decisão de consolidação seletiva.
Nenhum comportamento de produção muda neste ticket.

## Blocked by

Nenhum.

## Acceptance criteria

- [x] Os três estados têm identidade imutável e inventário de arquivos.
- [x] O trabalho local é preservado antes de qualquer integração.
- [x] A simulação de conflitos é reproduzível fora do working tree principal.
- [x] O teste local de supply chain falhando está registrado como blocker.
- [x] A decisão “núcleo modular + agent-first + hard security” está aprovada.
- [x] Não houve merge, reindexação ou publicação incidental.

## Execution evidence — 2026-09-06

- Seam: estado do repositório, refs Git e inventário do candidate set; nenhum
  comportamento de produção foi alterado.
- Confirmação humana: o pedido desta execução confirma explicitamente a
  granularidade, os seams e a ordem dos tickets; a decisão seletiva foi
  adotada.
- Branch isolada: `codex/main-consolidation` em
  `15cfaa6a919eaac7fca315241a4b396b1902f8f8`; `main` permanece no mesmo
  baseline e o working tree local foi preservado sem reset.
- Identidades registradas no início: `origin/main` e `HEAD` em
  `15cfaa6a919eaac7fca315241a4b396b1902f8f8`; `origin/feat/continuous-knowledge`
  em `2eaa9c24c9f809db0e0ce8b73206500ba1ed73e6`; merge-base igual ao baseline.
- Inventário do working tree: 525 arquivos no candidate set, digest
  `b99c603e2ba10f2f5a69348ebce99eb09e46c7eee93f6ee365ee35ce789b0022`;
  patch SHA-256 `2360529c2aab1645226426f9e806c5437b6328b795410347d45c51f869ab011a`;
  139 linhas de status, digest de status
  `37a2e5ae7f1be4b95369bbb0a856341338d3ea8aef2b427d5ccc9d29f9dababa`.
- Baseline de gates: `scripts/check_contracts.py --json`, Ruff e
  `git diff --check` passaram. O teste
  `test_candidate_falls_back_when_bootstrap_no_install_leaves_a_venv_without_pip`
  falhou em RED com `candidate_failed`/`supply-chain evidence failed
  independent verification`; esse blocker foi preservado para resolução
  posterior, sem mascará-lo.
- A simulação documental three-way e os 33 conflitos registrados em
  `COMPARISON-AND-DECISION.md` foram tratados como evidência de integração
  seletiva; nenhum merge mecânico foi executado.
- Rollback: como T01 não altera runtime, descartar apenas este registro não
  toca o checkout nem o corpus; a branch isolada preserva o snapshot.

Status: concluído; nenhum merge, reindexação, publicação ou release foi
executado.
