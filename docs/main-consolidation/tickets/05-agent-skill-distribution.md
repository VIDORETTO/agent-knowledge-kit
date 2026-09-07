---
status: done
---

# T05 — Distribuir e descobrir a skill operacional

## What to build

Portar a experiência `docops-agent` como artefato de primeira classe. Um agente
deve localizar a skill no checkout e na wheel, instalar um bootstrap
idempotente e acessar command cards, runbooks e interoperabilidade.

## Blocked by

- T04

## Acceptance criteria

- [x] A mesma interface localiza a skill no checkout e na wheel.
- [x] Symlinks, caminhos fora do root e conteúdo incompleto são rejeitados.
- [x] O bootstrap não duplica nem sobrescreve instruções existentes.
- [x] Existe modo read-only de verificação do bootstrap.
- [x] Wheel offline contém skill, referências e metadados.
- [x] Há instruções verificadas para os harnesses suportados.

## Evidence

- RED: os quatro testes públicos de descoberta, bootstrap, rejeição e CLI
  falharam antes da implementação com `ModuleNotFoundError`.
- GREEN: `docops.agent_skill` passou a fornecer descoberta determinística,
  metadados, bootstrap idempotente e verificação read-only; a skill completa
  `docops-agent` foi distribuída com command cards, runbooks e
  interoperabilidade. Os testes focados passaram: `5 passed, 1 skipped`.
- CLI: `python -m docops skill path --json` e
  `python -m docops agents-bootstrap --check --json` exercitam os seams
  públicos sem depender do checkout.
- Wheel: `python scripts/verify_wheel.py --core` passou com wheel offline,
  verificando os arquivos da skill, `openai.yaml`, referência de
  interoperabilidade, bootstrap e probe do CLI instalado.
- Verificação adicional: Ruff check/format, contratos e regressão permaneceram
  verdes; nenhuma alteração foi feita no corpus ou no índice RAG real.

## Rollback

Remover `docops/agent_skill.py`, `skills/docops-agent/`, as entradas de dados do
`pyproject.toml`, os comandos de skill do CLI e o gate adicional do wheel; os
demais contratos modulares permanecem independentes desta distribuição.
