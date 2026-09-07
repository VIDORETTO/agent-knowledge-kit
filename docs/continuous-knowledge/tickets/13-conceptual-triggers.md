# T13 — Disparar enriquecimento por impacto conceitual

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **implementado localmente em 2026-09-05**.

## Objetivo e entrega

Evitar ciclos de geração causados por reindex e formar lotes relevantes.

## Contexto

Diff factual e reembedding têm significados distintos; SPEC define cursores e thresholds. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T06](./06-external-enrichment.md), [T10](./10-source-registry.md), [T12](./12-resumable-worker.md)

Decisões aplicáveis: D02, D05. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/triggers.py`, `docops/coordination.py`, schemas de
`conceptual-impact` e a CLI `impact-assess`.

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

- [x] Mudança revertida à base sai do contador.
- [x] Atualização factual comprovada não gera lote conceitual.
- [x] Impacto incerto requer revisão, não publicação.
- [x] Limite de orçamento mantém backlog visível.
- [x] Revogação invalida suporte imediatamente mesmo sem orçamento.

Rastreabilidade: A04, A12 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Riscos

Classificador pode superestimar relevância e gerar excesso de candidatas.

## Resultado da execução

- RED: os três testes públicos falharam porque `impact-assess` ainda não existia.
- GREEN: `docops.triggers.assess_conceptual_impact` persiste o cursor em
  `.docops/conceptual-impact.json`, calcula impacto líquido, separa factual de
  conceitual, gera no máximo um lote por chave e registra backlog/revogação.
- REFACTOR: o seam usa a CLI e o envelope `conceptual-impact`; nenhum teste
  depende de SQLite, helpers privados ou ordem de chamadas.
- Verificação: `rtk pytest -q tests\test_conceptual_triggers.py` — **3 passed**;
  contratos, Ruff lint/formato e `git diff --check` passaram.
- Evidência: somente fixtures sintéticas em diretórios temporários; nenhum corpus,
  conversa, reindex ou harness externo foi usado.
- Limitação/decisão: o gatilho não cria nem publica candidata por conta própria;
  `candidate_requested` é apenas uma solicitação para a fila T12. O classificador
  de impacto é determinístico e aceita `uncertain` como revisão obrigatória.

## Estratégia de rollback

Desativar gatilho conceitual preservando backlog e invalidações.
