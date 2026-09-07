# T09 — Reter e restaurar gerações publicadas

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente em 2026-09-05**.

## Objetivo e entrega

Permitir retorno editorial após publicação bem-sucedida.

## Contexto

E18: o backup transacional é descartado após sucesso; não há histórico editorial equivalente. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T08](./08-approve-publish.md)

Decisões aplicáveis: D06, D14. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/candidates.py` (novo), [docops/operations.py](../../../docops/operations.py), [docops/storage.py](../../../docops/storage.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

CLI candidate rollback e inspect.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Publicar duas gerações e solicitar retorno à primeira; recuperar composição inteira e registrar evento novo.

**GREEN mínimo:** Reter composição publicada e restaurá-la transacionalmente após validação.

**REFACTOR:** Separar armazenamento editorial e recuperação operacional.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] Retenção separada de cleanup de resíduos.
- [x] A árvore editorial retida não é descartada por cleanup; a fixação de
  sessão por `release_id` será consumida pelo T14.
- [x] Revogação impede restauração de fonte/derivado.
- [x] Índice incompatível é recusado antes da troca e declara rebuild.
- [x] Quota insuficiente bloqueia publicação antes de perder histórico necessário.

Rastreabilidade: A07, A12 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável por `candidate-rollback` e `inspect`.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Riscos

Disco pode crescer; rollback de dados revogados seria incidente de privacidade.

## Estratégia de rollback

Suspender novas publicações ao atingir quota; conservar ativa e histórico ainda exigido.

### Resultado da execução local

- RED: após duas publicações sintéticas, `candidate-rollback` não era
  reconhecido pela CLI.
- GREEN: a publicação retém a composição anterior em árvore editorial irmã;
  rollback valida manifesto, composição, índice e pacote antes da promoção.
- REFACTOR: histórico editorial e resíduos operacionais usam caminhos e
  inspeção distintos; `cleanup()` não remove releases retidos.
- Verificação: `tests/test_history_rollback.py` — **5 passed**; contratos,
  Ruff lint/formato e `git diff --check` — **PASS**.
- Guardas observadas: `source_revoked`, `index_incompatible` e
  `history_quota_exceeded`, sempre com a geração ativa preservada.
- Limites: execução local com fixtures temporárias; sem corpus real, MCP/harness
  externo, deploy ou publicação. Sessões pinadas e tombstones de leitura serão
  integrados no T14.
