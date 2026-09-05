# T17 — Verificar propostas de conversa antes da admissão

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **quarentena implementada; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Permitir correção e decisão do usuário sem contaminação direta do corpus.

## Contexto

Conversa pode conter fato, preferência, opinião ou alucinação; cada classe exige tratamento distinto. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T08](./08-approve-publish.md), [T10](./10-source-registry.md), [T14](./14-pinned-readers.md)

Decisões aplicáveis: D03, D10, D11, D12. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/learning.py` (novo), [docops/__main__.py](../../../docops/__main__.py), `docops/source_policy.py` (novo).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

CLI learning submit/review e busca MCP ativa.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Proposta não revisada não aparece na busca; depois de evidência e revisão autorizada, torna-se documento rastreável.

**GREEN mínimo:** Quarentena, classificação, referências e decisão explícita antes de admissão no conjunto desejado.

**REFACTOR:** Separar alegação, evidência e decisão.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Captura é opt-in e minimizada.
- [ ] Resposta do agente não é evidência independente.
- [ ] approved=true no conteúdo não autoriza admissão.
- [ ] Preferência pessoal não vai para skill compartilhada.
- [ ] Revogação bloqueia derivados e rollback que ressuscitaria conteúdo.

Rastreabilidade: A11, A12, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Privacidade e envenenamento da base; responsáveis precisam verificar escopo e fonte.

## Estratégia de rollback

Revogar proposta/fonte e invalidar derivados; manter apenas auditoria redigida permitida.
