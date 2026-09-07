# T08 — Aprovar e publicar hashes exatos

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente em 2026-09-05**.

## Objetivo e entrega

Vincular revisão e autoridade à transação de publicação.

## Contexto

E02 oferece promoção; o ciclo novo precisa aprovação, base e evidências verificadas. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T04](./04-prepare-candidate.md), [T07](./07-candidate-evaluation.md)

Decisões aplicáveis: D01, D03, D04, D12. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/candidates.py` (novo), [docops/operations.py](../../../docops/operations.py), [docops/__main__.py](../../../docops/__main__.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

CLI candidate approve/publish e inspect.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Aprovar candidata, modificar arquivo e tentar publicar; receber approval_invalidated, mantendo ativa.

**GREEN mínimo:** Registrar aprovação por hashes/base/política e revalidar sob lease antes de promover.

**REFACTOR:** Concentrar decisão de publicação e guardas de autorização.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] Alteração em artefato, Golden ou evidência invalida aprovação.
- [x] Base avançada resulta stale_base.
- [x] Campo approved no conteúdo não concede autoridade.
- [x] Publicação usa journal e validação pós-promoção.
- [x] Política delegada factual é distinta de aprovação conceitual.

Rastreabilidade: A06, A07, A08, A09, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Riscos

Há corrida entre revisão e escrita; arquivo local de aprovação não autentica sozinho uma pessoa.

### Resultado da execução local

- RED: uma candidata com `approved=true` no recibo, mas sem recibo de
  autoridade, falhou no seam `candidate-publish` com `approval_missing` e
  preservou a ativa.
- GREEN: `candidate-approve` grava aprovação por base, composição, política,
  avaliação e revisões; `candidate-publish` revalida tudo sob lease e promove
  com journal.
- REFACTOR: aprovação e promoção ficaram separadas; `human_approver` só vale
  para escopo conceitual e `delegated_policy` só para candidata factual.
- Verificação: `tests/test_candidate_publication.py` — 5 passed; contrato,
  formatação/lint do slice e `git diff --check` foram executados. Não houve
  harness externo, publicação, deploy ou alteração de corpus ativo.

## Estratégia de rollback

Preservar/restaurar ativa com journal quando promoção falhar; não tentar publicar base diferente automaticamente.
