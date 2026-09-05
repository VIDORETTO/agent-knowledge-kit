# T13 — Disparar enriquecimento por impacto conceitual

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **piloto implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Evitar ciclos de geração causados por reindex e formar lotes relevantes.

## Contexto

Diff factual e reembedding têm significados distintos; SPEC define cursores e thresholds. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T06](./06-external-enrichment.md), [T10](./10-source-registry.md), [T12](./12-resumable-worker.md)

Decisões aplicáveis: D02, D05. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/coordination.py` (novo), [docops/divergence.py](../../../docops/divergence.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

Eventos, jobs, candidatas e inspeção pública.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Reindex sem diff não cria tarefa de enriquecimento; décimo documento relevante cria uma candidata.

**GREEN mínimo:** Contadores por identidade/revisão, idade do lote e causation_id, com uma geração simultânea.

**REFACTOR:** Isolar política de lotes e cursores de cobertura/publicação.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Mudança revertida à base sai do contador.
- [ ] Atualização factual comprovada não gera lote conceitual.
- [ ] Impacto incerto requer revisão, não publicação.
- [ ] Limite de orçamento mantém backlog visível.
- [ ] Revogação invalida suporte imediatamente mesmo sem orçamento.

Rastreabilidade: A04, A12 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Classificador pode superestimar relevância e gerar excesso de candidatas.

## Estratégia de rollback

Desativar gatilho conceitual preservando backlog e invalidações.
