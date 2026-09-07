# Status de implementação — consolidação da main

Execução iniciada em 2026-09-06 na branch local `codex/main-consolidation`,
criada sobre `origin/main`. O working tree histórico foi preservado e não há
autorização para push, merge em `main`, release, publicação ou mutação de
corpus/RAG real.

## Ordem e estado

| Ticket | Estado | Dependências | Evidência principal |
|---|---|---|---|
| T01 | concluído | — | Baselines e decisão em `BASELINE-SNAPSHOT.json`; blocker de supply chain reproduzido em RED |
| T02 | concluído | T01 | `LifecycleFacade`, máquina de estados e runtime externo versionado; 4 testes focados verdes |
| T03 | concluído | T02 | Read-only real no servidor, pinning do adapter, revogação e processo MCP sintético; 15 testes focados + vendor 170 passed |
| T04 | concluído | T02, T03 | Geração canônica, harness validado, router com quatro rotas e drift explícito; regressão 33 passed |
| T05 | concluído | T04 | Skill `docops-agent` distribuída, descoberta checkout/wheel, bootstrap idempotente/read-only e wheel offline verificado; 5 testes focados + `verify_wheel --core` |
| T06 | concluído | T02, T05 | Hierarquia `lifecycle`, mapa explícito expand-contract e equivalência de JSON/exit code; 3 testes focados verdes |
| T07 | concluído | T02, T03, T04 | Candidata review-first, autoridade atestada, revogação fail-closed e recuperação de 5 failpoints; suítes de avaliação/publicação/rollback verdes |
| T08 | concluído | T02, T07 | Registry admitido/retomável, readmission explícita, eventos idempotentes, lease/retry/receipt e worker foreground; 19 testes verdes |
| T09 | concluído | T03, T04, T07 | `reader_sessions.py` + `rag_sync.py`: reader pinado de release/snapshot, identidade completa de corpus/modelo/configuração/artefatos, reuse fail-closed, revogação e smoke MCP; 24 testes focados + 2 processos MCP reais |
| T10 | concluído | T07, T08, T09 | Consentimento/independência verificáveis, feedback autenticado com anti-replay/rate-limit e revogação propagada a snapshots/readers/candidatas; `18 passed` no foco, `13 passed` em publicação e Ruff PASS |
| T11 | concluído | T04, T06, T07, T08, T09, T10 | `35 passed, 1 skipped`; sync de 34 schemas, contratos e documentação sem findings; Ruff PASS |
| T12 | concluído | T05, T06, T11 | `artifacts/release-gates-final-20260907/release-gates.json`: 22/22 estágios verdes; 7793 pass, 57 skips explícitos, zero falhas; wheel, clean clone, MCP real, crash e revogação comprovados |
| T13 | concluído (promoção bloqueada) | T12 | `artifacts/integration-candidate-final-20260907/integration-candidate-report.json`: technical_ready=true, digest registrado no artefato, bundle pronto e decisão humana sem autorização |

## Regras de execução

Cada ticket registra no próprio arquivo o seam público, RED, GREEN mínimo,
verificação, refatoração e rollback. A suíte final foi executada
sequencialmente, com artefatos temporários fora do conjunto versionado.

## Gatilhos de parada

Parar e reportar se a especificação entrar em conflito com o código, se uma
operação ameaçar mudanças locais preexistentes, ou se for necessário decidir
uma política arquitetural não coberta pelos documentos.

## Gates finais executados

O runner sequencial `scripts/run_release_gates.py --profile full` produziu
22 estágios verdes no Windows em
`artifacts/release-gates-final-20260907/release-gates.json`, incluindo suíte
completa, clean clone com RAG, wheel core/RAG, MCP real, revogação, crash matrix
e concorrência de reindexação. O relatório registra 7793 verificações passadas,
57 skips explícitos e zero falhas.
POSIX/WSL executou compileall, bootstrap sem instalação, doctor, contratos e
documentação; os gates que exigem pip/pytest/Ruff/RAG ficaram como skips
explícitos por limitação do host. Os artefatos e denominadores estão preservados
no ticket T12. A decisão de promoção permanece `blocked` por exigir aprovação
humana, commit limpo e CI correspondente; nenhum merge, push, release,
publicação ou corpus/RAG real foi alterado.
