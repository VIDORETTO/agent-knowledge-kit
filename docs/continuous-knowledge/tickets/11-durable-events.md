# T11 — Persistir eventos com deduplicação e debounce

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **piloto implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

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

- [ ] event_id com payload divergente é recusado.
- [ ] Janela normal e máxima seguem SPEC.
- [ ] Arquivo instável não bloqueia arquivos concluídos.
- [ ] Estado da fila é excluído de aquisição, Git e release.
- [ ] Não exigir inspeção SQL interna para observar jobs.

Rastreabilidade: A02, A13, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Filesystem de rede e corrupção local estão fora da garantia de fila local.

## Estratégia de rollback

Suspender worker e reconciliar fontes; não apagar fila como recuperação automática.
