# T17 — Verificar propostas de conversa antes da admissão

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente em 2026-09-05**.

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

- [x] Captura é opt-in e minimizada.
- [x] Resposta do agente não é evidência independente.
- [x] approved=true no conteúdo não autoriza admissão.
- [x] Preferência pessoal não vai para skill compartilhada.
- [x] Revogação bloqueia derivados e rollback que ressuscitaria conteúdo.

Rastreabilidade: A11, A12, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Riscos

Privacidade e envenenamento da base; responsáveis precisam verificar escopo e fonte.

## Estratégia de rollback

Revogar proposta/fonte e invalidar derivados; manter apenas auditoria redigida permitida.

## Resultado da execução

- `docops/learning.py` grava somente um trecho minimizado em
  `.docops/learning/proposals/` depois de `capture_opt_in=true`; campos de
  transcrição integral são rejeitados e o estado inicial é `quarantined`.
- `learning-review` exige ator e papel `human_approver`, rejeita auto-revisão,
  ignora `approved=true` como autoridade e filtra evidência proveniente do
  agente. Alegações factuais/experimentais admitidas geram um documento
  rastreável com `reindex_required=true`, sem publicação automática.
- Preferências admitidas ficam em `.docops/learning/private/` e nunca são
  incorporadas à skill ou ao corpus compartilhado.
- Revogação remove derivados, grava tombstones e faz `candidate-rollback`
  falhar se a geração histórica tentaria ressuscitar o caminho revogado.
- `docops/operations.py` carrega o estado de aprendizagem em staging e
  reconstitui documentos admitidos sem readquirir conversa.
- RED: antes do seam, não havia contrato/CLI pública para quarentena e revisão;
  GREEN: `tests/test_learning.py` cobre opt-in, admissão, preferência,
  resposta do agente e revogação; REFACTOR: política de evidência, estado,
  derivados e tombstones ficaram separados.
- Verificação: `rtk pytest -q tests\test_learning.py` — **3 passed**;
  exemplos/contratos, Ruff e diff-check serão repetidos no gate final.
- Integração: testes usam somente pacote e conteúdo sintéticos temporários;
  nenhuma conversa real, corpus real, reindexação ativa ou harness externo foi
  usado.
