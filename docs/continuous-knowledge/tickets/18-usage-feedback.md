# T18 — Priorizar investigação por uso e qualidade

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **sinalização implementada; ver [estado](../IMPLEMENTATION-STATUS.md)**.

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

- [ ] Feedback repetido não conta como ocorrências independentes.
- [ ] Nenhum sinal publica conhecimento ou altera resposta esperada.
- [ ] Relatórios incluem custo/latência e denominadores.
- [ ] Perguntas privadas são redigidas na projeção pública.
- [ ] Queda de métrica em conjuntos não comparáveis não é apresentada como regressão controlada.

Rastreabilidade: A11, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Feedback pode ser manipulado e perguntas podem conter dados privados.

## Estratégia de rollback

Desligar gatilho de investigação mantendo evidências válidas; não editar Golden automaticamente.
