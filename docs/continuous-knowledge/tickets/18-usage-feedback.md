# T18 — Priorizar investigação por uso e qualidade

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente em 2026-09-05**.

## Objetivo e entrega

Transformar falhas recorrentes em investigação e Golden candidato.

## Contexto

Métricas são sinais de problema, não evidência factual; Golden não pode ser autoajustado para aprovar o sistema. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T07](./07-candidate-evaluation.md), [T12](./12-resumable-worker.md), [T17](./17-conversation-learning.md)

Decisões aplicáveis: D02, D10. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/observability.py](../../../docops/observability.py), `docops/coordination.py` (novo), [docops/evaluator.py](../../../docops/evaluator.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

Implementação entregue em `docops/feedback.py`, com `feedback-submit`,
`feedback-report` e suporte a `feedback_report` em `work --once`. Os envelopes
`feedback`, `feedback-report` e `investigation` são versionados em `schemas/` e
`docops/schemas/`. O armazenamento local fica em `.docops/feedback/` e nunca
faz parte da composição ativa.

## Seam público

Submissão de feedback, jobs e relatórios públicos.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Três ocorrências independentes geram uma investigação e caso reviewed=false; Golden revisado permanece intacto.

**GREEN mínimo:** Agregação minimizada por geração/janela e geração de candidato com origem rastreável.

**REFACTOR:** Separar sinal operacional e evidência de conhecimento.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] Feedback repetido não conta como ocorrências independentes.
- [x] Nenhum sinal publica conhecimento ou altera resposta esperada.
- [x] Relatórios incluem custo/latência e denominadores.
- [x] Perguntas privadas são redigidas na projeção pública.
- [x] Queda de métrica em conjuntos não comparáveis não é apresentada como regressão controlada.

Rastreabilidade: A11, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Riscos

Feedback pode ser manipulado e perguntas podem conter dados privados.

## Estratégia de rollback

Desligar gatilho de investigação mantendo evidências válidas; não editar Golden automaticamente.

O rollback local consiste em deixar de executar `feedback-report`/jobs
`feedback_report` e manter os sinais redigidos para auditoria. Nenhum rollback
de T18 pode alterar a candidata Golden, a resposta esperada ou a geração ativa;
qualquer admissão posterior passa pelos gates de revisão/publicação existentes.

## Verificação observada

- RED: `rtk pytest -q tests\test_usage_feedback.py::test_three_independent_failures_open_unreviewed_investigation_without_mutation` falhou antes do CLI existir.
- GREEN/refactor: `rtk pytest -q tests\test_usage_feedback.py` — **3 passed**.
- Contratos: `rtk python scripts\check_contracts.py --json` — **ok=true**, incluindo as três cópias de schema.
- Ruff: `rtk python -m ruff check docops scripts tests` — **PASS**; formato Ruff — **PASS** após correção.
- Integração real/MCP/harness: não executada neste ticket; os testes usam pacote e fila sintéticos em diretórios temporários.
