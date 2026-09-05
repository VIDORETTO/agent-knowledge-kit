# T04 — Preparar candidata sem ativar

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **piloto implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Produzir pacote revisável e retomável sem substituir a geração ativa.

## Contexto

E02 oferece staging e recuperação, mas apply normalmente promove ao concluir. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T02](./02-revision-evidence.md), [T03](./03-rag-preserve-skill.md)

Decisões aplicáveis: D04. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/operations.py](../../../docops/operations.py), `docops/candidates.py` (novo).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

apply com política proposta de candidata, inspect e CLI validate.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Preparar candidata de uma fonte alterada; a ativa deve continuar na revisão anterior enquanto a candidata é inspecionável.

**GREEN mínimo:** Concluir staging validado e devolver candidate_id, sem executar promoção.

**REFACTOR:** Reutilizar as fases existentes de preparação e validação.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Candidata possui base e hashes identificados.
- [ ] Ativa não muda durante preparação.
- [ ] Candidata interrompida é retomável e caminhos arbitrários são rejeitados.
- [ ] Falha estrutural impede estado publicável.

Rastreabilidade: A07, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Candidatas podem consumir disco e conter dados privados. Retenção operacional deve ser explícita.

## Estratégia de rollback

Descartar somente candidata identificada ou mantê-la bloqueada; a ativa permanece intacta.
