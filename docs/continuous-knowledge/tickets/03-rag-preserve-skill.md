# T03 — Atualizar corpus preservando a camada conceitual

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **piloto implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Permitir atualização factual sem regeneração da skill e do router.

## Contexto

E04/E07: as camadas são geradas juntas. A proposta exige cadências independentes. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T01](./01-protect-enrichment.md), [T02](./02-revision-evidence.md)

Decisões aplicáveis: D04. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/operations.py](../../../docops/operations.py), [docops/api_types.py](../../../docops/api_types.py), [docops/divergence.py](../../../docops/divergence.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

OperationOptions, docops.plan/apply/inspect e artefatos.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Selecionar atualização factual, alterar documento e observar novo corpus com bytes idênticos da skill e router.

**GREEN mínimo:** Adicionar seleção explícita de camadas; preservar artefatos cuja integridade foi verificada e registrar corpus de derivação anterior.

**REFACTOR:** Separar preparação das camadas dentro do motor existente.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Atualização factual preserva skill e router.
- [ ] Defasagem e cobertura desconhecida aparecem na inspeção.
- [ ] Fonte removida invalida suporte dependente; não declara skill sincronizada indevidamente.
- [ ] Atualização não indexada continua corpus-ready; não inicia MCP implicitamente.

Rastreabilidade: A01, A03, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Preservar bytes pode manter recomendação obsoleta. Tornar invalidação e necessidade de confirmação observáveis.

## Estratégia de rollback

Voltar à geração anterior ou suspender conceito afetado; nunca regenerar automaticamente a skill como fallback.
