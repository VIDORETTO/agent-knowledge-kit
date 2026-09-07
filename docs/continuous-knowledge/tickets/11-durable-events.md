# T11 — Persistir eventos com deduplicação e debounce

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído em 2026-09-05**.

## Objetivo e entrega

Absorver rajadas e reinícios sem perder ou duplicar trabalho.

## Contexto

E09/E24: watcher não substitui fila durável; estado operacional deve ficar fora da árvore ativa. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T10](./10-source-registry.md)

Decisões aplicáveis: D02 e localização operacional em D04. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/coordination.py` (novo), [docops/__main__.py](../../../docops/__main__.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

CLI event submit/jobs e relógio controlável no teste.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Enviar evento duas vezes, reiniciar processo e listar jobs; existe um trabalho para a mesma revisão.

**GREEN mínimo:** Fila SQLite local, chave idempotente, prazos duráveis e projeção pública.

**REFACTOR:** Encapsular persistência e cálculo de prazos.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] event_id com payload divergente é recusado.
- [x] Janela normal e máxima seguem SPEC.
- [x] Arquivo instável não bloqueia arquivos concluídos.
- [x] Estado da fila é excluído de aquisição, Git e release.
- [x] Não exigir inspeção SQL interna para observar jobs.

Rastreabilidade: A02, A13, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Resultado da execução

- O RED público falhou porque `event-submit` e `jobs` ainda não existiam.
- O GREEN implementou uma fila SQLite local com WAL, deduplicação por
  `event_id`/hash e chave de trabalho por pacote, tipo, revisão e política.
- A janela segue `min(last_event + 60s, first_event + 5min)` e é observável
  pelo campo `due_at` sem inspeção SQL.
- O payload pode projetar arquivos concluídos e adiados; arquivos instáveis
  ficam em `deferred_files` sem bloquear `ready=true` quando há trabalho
  concluído.
- O estado operacional fica em um caminho de fila fornecido pelo operador,
  fora da árvore ativa por convenção, e `.docops/*.sqlite*` é ignorado pelo
  Git; a aquisição já ignora `.docops`.
- Verificação: `rtk pytest -q tests\test_coordination.py` — **5 passed**;
  `scripts/check_contracts.py --json`, Ruff e `git diff --check` — **PASS**.
- Limitações: lease, retomada, retries e execução do job permanecem no T12;
  nenhuma fila de produção, corpus real, conversa real ou harness externo foi
  usado.

## Riscos

Filesystem de rede e corrupção local estão fora da garantia de fila local.

## Estratégia de rollback

Suspender worker e reconciliar fontes; não apagar fila como recuperação
automática. A implementação não iniciou worker no T11, portanto a recuperação
manual consiste em preservar o SQLite e reler `jobs` pela CLI.
