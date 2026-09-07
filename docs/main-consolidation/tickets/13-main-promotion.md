---
status: done
---

# T13 — Criar e promover o candidato de integração

## What to build

Montar o candidato final em uma branch revisável, executar todos os gates,
comparar comportamento contra os dois candidatos de origem e produzir a
decisão humana de promoção. A promoção só ocorre se não houver blocker.

## Blocked by

- T12

## Acceptance criteria

- [x] Nenhum lifecycle, CLI ou schema concorrente permanece.
- [x] Funcionalidades escolhidas dos dois candidatos estão rastreadas.
- [x] Compatibilidade e migração possuem evidência.
- [x] Todos os gates do T12 estão verdes no SHA candidato.
- [x] Riscos residuais têm owner, severidade e decisão explícita.
- [x] A documentação normativa corresponde ao SHA candidato.
- [x] A promoção para `main` exige aprovação humana registrada.
- [x] Nenhum corpus privado ou runtime local entra no versionamento.

## Evidence

- RED: `tests/test_integration_candidate.py` falhou antes da criação do seam
  `scripts/prepare_integration_candidate.py`.
- GREEN/verificação: o teste focado do relatório passou; o comando de produção
  é `python scripts/prepare_integration_candidate.py --root . --output
  artifacts/integration-candidate-final-20260907 --bundle-output
  artifacts/integration-bundle-final-20260907-v4 --gates-report
  artifacts/release-gates-final-20260907/release-gates.json --json`.
- O relatório registra a branch `codex/main-consolidation`, o SHA, o digest e
  os arquivos candidatos, compara `origin/main` com
  `origin/feat/continuous-knowledge`, rastreia as capacidades selecionadas e
  aponta `docs/CONTRACT-COMPATIBILITY.md`, `check_contracts.py` e
  `sync_schemas.py` como evidência de compatibilidade/migração.
- Relatório final: `artifacts/integration-candidate-final-20260907/integration-candidate-report.json`,
  `technical_ready=true`, 555 arquivos, digest registrado no próprio JSON, e
  bundle auditado em `artifacts/integration-bundle-final-20260907-v4/`.
- Verificação independente do bundle: `python scripts/verify_candidate.py --root
  artifacts/integration-bundle-final-20260907-v4 --source-root .` retornou
  `ok=true`, sem erros de supply chain e com a mesma identidade do candidato.
- A promoção está explicitamente **blocked**: `performed=false`,
  `authorization_record=null`, e os riscos têm owner, severidade e decisão.
  Isso satisfaz o gate humano sem inferir autorização nem executar merge/push.
- O gate T12 final é `artifacts/release-gates-final-20260907/release-gates.json`,
  com 22 estágios verdes e os artefatos por estágio. A documentação normativa e
  o relatório são gerados no mesmo estado da branch; o SHA só pode ser promovido depois de um commit
  limpo e de CI correspondente.
- O inventário versionado rejeita `.rag_state.json`, caches, venvs, runtime,
  corpus privado e dados de execução; fixtures sintéticas e dados de
  configuração do vendor revisado são allowlist explícita.

## Rollback

Excluir o diretório de relatório/bundle de candidato em `artifacts/` desfaz o
artefato não publicado. A promoção não foi executada, portanto não há merge,
push, release, publicação, alteração de `main` ou mutação de corpus/RAG para
reverter.
