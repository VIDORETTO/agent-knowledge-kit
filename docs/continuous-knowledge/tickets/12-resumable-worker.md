# T12 — Executar jobs com retomada e indexação autorizada

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **worker local implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Transformar fila em operações limitadas com efeitos idempotentes.

## Contexto

O worker deve reutilizar motor existente e aguardar término MCP; agenda não concede autorização. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T08](./08-approve-publish.md), [T11](./11-durable-events.md)

Decisões aplicáveis: D01, D02. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/coordination.py` (novo), [docops/operations.py](../../../docops/operations.py), [docops/__main__.py](../../../docops/__main__.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

CLI work --once/jobs e inspect.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Interromper após efeito de publicação e antes do reconhecimento; retomar sem segunda publicação.

**GREEN mínimo:** Lease de job e recibo de efeito por revisão; verificar efeito existente antes de repetir.

**REFACTOR:** Centralizar classificação de falhas e retomada.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Sem autorização persistida de RAG não inicia indexação.
- [ ] Retries transitórios limitados; falhas de política ficam blocked.
- [ ] Worker aguarda MCP e encerra só subprocesso próprio.
- [ ] Eventos durante execução permanecem para lote posterior.
- [ ] Até T14, operação automática prepara candidatas; autopublicação permanece desativada.

Rastreabilidade: A02, A07, A13 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Janela SQLite/filesystem não é transação distribuída; recibos devem reconciliá-la.

## Estratégia de rollback

Desligar agendador e operar manualmente; manter jobs/recibos para retomar.
