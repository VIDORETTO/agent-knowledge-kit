# T07 — Avaliar candidata e respostas com evidência independente

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente em 2026-09-05**.

## Objetivo e entrega

Separar qualidade de retrieval, rota e resposta conceitual.

## Contexto

E13/E14: avaliação atual busca arquivo e usa política lexical; não mede fidelidade do modelo. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Dependências confirmadas: [T05](./05-verify-index.md) e [T06](./06-external-enrichment.md)

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

## Implementação e evidência

- **RED:** o teste público tentou importar uma resposta com afirmação sem
  suporte e o seam ainda não aceitava `response_receipt`.
- **GREEN:** `evaluation-receipt` valida julgamentos independentes ligados a
  `generation_id`, `candidate_id`, `package_composition_hash` e
  `golden_revision`; `evaluate` calcula fidelidade e cobertura de citação sem
  alterar as métricas legadas.
- **REFACTOR:** recuperação, rota e resposta permanecem métricas separadas.
  O adapter lexical continua explicitamente diagnóstico; resposta só é
  medida quando um recibo externo válido é fornecido.
- **Verificação:** `tests/test_candidate_evaluation.py` — **7 passed**;
  integração com evaluator, CLI, contratos e conhecimento contínuo — **49
  passed**; Ruff lint/formato, `scripts/check_contracts.py --json` e
  `git diff --check` — **PASS**.
- **Integração:** a prova usa pacote e Golden sintéticos em diretórios
  temporários. Nenhum harness externo, conversa real, corpus real ou índice
  ativo foi usado neste ticket. O MCP real isolado continua coberto apenas
  pela evidência do T05.

## Critérios de aceite

- [x] Golden não revisado é recusado.
- [x] Avaliação informa backend, adapter, configuração e hashes.
- [x] Zero denominador produz `not_applicable`.
- [x] Diagnóstico lexical não substitui MCP nem avaliação de resposta.
- [x] Casos críticos falham individualmente mesmo com boa média.

Rastreabilidade: A06, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Riscos

Juiz enviesado pode repetir erro do gerador. Usar rubrica e revisão independentes.

## Estratégia de rollback

Bloquear publicação e manter ativa; não relaxar threshold silenciosamente para aprovar candidata.
Um recibo ausente, inválido, stale ou com falha crítica mantém o resultado
reprovado e não altera a geração ativa. Para desfazer a alteração local, remova
o arquivo de evidência da candidata ou descarte a candidata identificada, sem
copiar conteúdo de volta para a ativa.
