# T07 — Avaliar candidata e respostas com evidência independente

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **implementado como contrato; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Separar qualidade de retrieval, rota e resposta conceitual.

## Contexto

E13/E14: avaliação atual busca arquivo e usa política lexical; não mede fidelidade do modelo. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T05](./05-verify-index.md), [T06](./06-external-enrichment.md)

Decisões aplicáveis: D02 e D05. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/evaluator.py](../../../docops/evaluator.py), [docops/retrieval.py](../../../docops/retrieval.py), [docops/contracts.py](../../../docops/contracts.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

CLI evaluate, Golden revisado e recibo externo de avaliação.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Importar resposta candidata com afirmação sem suporte em caso anotado; gate de fidelidade deve falhar.

**GREEN mínimo:** Computar suporte/citação a partir de julgamentos independentes vinculados à geração, preservando métricas legadas.

**REFACTOR:** Separar recuperação, roteamento e resposta sem duplicar pipeline.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Golden não revisado é recusado.
- [ ] Avaliação informa backend, adapter, configuração e hashes.
- [ ] Zero denominador produz not_applicable.
- [ ] Diagnóstico lexical não substitui MCP nem avaliação de resposta.
- [ ] Casos críticos falham individualmente mesmo com boa média.

Rastreabilidade: A06, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Juiz enviesado pode repetir erro do gerador. Usar rubrica e revisão independentes.

## Estratégia de rollback

Bloquear publicação e manter ativa; não relaxar threshold silenciosamente para aprovar candidata.
