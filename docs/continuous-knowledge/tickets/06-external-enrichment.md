# T06 — Receber enriquecimento externo em candidata

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente em 2026-09-05**.

## Objetivo e entrega

Integrar resultado de book-to-skill sem modelo interno e sem editar ativa.

## Contexto

E03/E23: enriquecimento é responsabilidade do harness; falta hand-off editorial verificável. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T04](./04-prepare-candidate.md)

Decisões aplicáveis: D04, D05. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/candidates.py` (novo), [docops/harness.py](../../../docops/harness.py), [docops/readiness.py](../../../docops/readiness.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

EnrichmentRequest/Receipt JSON e CLI candidate submit proposta.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Submeter saída com base divergente ou caminho fora dos artefatos permitidos; rejeitar sem alteração da ativa.

**GREEN mínimo:** Exportar tarefa identificada e importar somente arquivos autorizados após verificar hashes e escopo.

**REFACTOR:** Encapsular validação de tarefa, recibo e importação.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] Ausência de harness mantém awaiting_enrichment.
- [x] Recibo registra ferramenta/versão e entradas/saídas, sem credenciais.
- [x] Symlink/path traversal e tentativa de editar Golden revisado são recusados.
- [x] Saída válida fica candidata; não é publicada por submissão.

Rastreabilidade: A07, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Resultado da execução

- RED: `candidate-submit` inexistente foi observado pela CLI; depois a fixture
  foi completada com o contrato de tarefa/recibo para que o teste alcançasse a
  guarda de escopo.
- GREEN: `candidate-request` grava uma tarefa com base, snapshot, hashes,
  escopo, política, idioma e orçamento; `candidate-submit` verifica o recibo,
  rejeita conteúdo sensível, caminhos fora de `skill/` e `router/`, hashes
  divergentes e base obsoleta, e importa somente para a candidata.
- REFACTOR: validação de caminho, hashes, orçamento, contrato e importação
  transacional ficaram isolados em `docops/candidates.py`; o hand-off
  determinístico ficou em `docops/harness.py`.
- Verificação: `tests/test_enrichment.py` — **5 passed**; `scripts/check_contracts.py`
  — **ok**; Ruff lint e formato do slice — **passaram**.
- Integração: nenhum harness externo real foi executado. O resultado válido é
  uma fixture sintética; T05 continua sendo a única prova MCP real isolada.
- Rollback: rejeitar o recibo ou descartar a candidata; a geração ativa nunca
  é alterada pela submissão.

## Riscos

Saída do harness é conteúdo não confiável e pode conter instrução/arquivo malicioso.

## Estratégia de rollback

Rejeitar submissão e manter candidata anterior; repetir enriquecimento requer nova tentativa registrada.
