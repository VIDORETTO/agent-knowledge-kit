# T12 — Executar jobs com retomada e indexação autorizada

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **implementado localmente em 2026-09-05**.

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

- [x] Sem autorização persistida de RAG não inicia indexação.
- [x] Retries transitórios limitados; falhas de política ficam blocked.
- [x] Worker reutiliza o motor em primeiro plano e só reconhece o efeito após
  o retorno terminal da operação.
- [x] Eventos durante execução permanecem para lote posterior.
- [x] Até T14, operação automática prepara candidatas; autopublicação permanece desativada.

Rastreabilidade: A02, A07, A13 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Riscos

Janela SQLite/filesystem não é transação distribuída; recibos devem reconciliá-la.

## Estratégia de rollback

Desligar agendador e operar manualmente; manter jobs/recibos para retomar.

## Resultado da execução

- RED: `tests/test_worker.py` começou falhando porque `work --once` ainda não
  existia.
- GREEN/refactor: `coordination.py` agora faz claim transacional com lease,
  executa uma única `OperationRequest`, grava `job-receipt` atômico e
  reconhece o job somente após o efeito. Lease expirado consulta o recibo
  antes de repetir; jobs em execução recebem uma chave posterior para eventos
  novos.
- Guardas: `index_rag` exige `.docops/rag-authorization.json` com escopo e
  revisão exatos; políticas diferentes de `candidate` ficam bloqueadas;
  `writer_busy` tem cinco tentativas no máximo, com atrasos de 1, 5, 15 e
  60 minutos.
- Arquivos principais: `docops/coordination.py`, `docops/authorization.py`,
  `docops/__main__.py`, `docops/__init__.py`, schemas `rag-authorization` e
  `job-receipt` nas duas raízes, `tests/test_worker.py`, contratos e docs.
- Verificação proporcional:
  `rtk pytest -q tests\test_coordination.py tests\test_worker.py` —
  **11 passed**; `scripts/check_contracts.py --json` — **PASS**; Ruff
  lint/formato — **PASS**.
- Escopo/limites: os testes usam fontes, SQLite, locks e subprocessos
  sintéticos em diretórios temporários. Não foram usados corpus real,
  conversas, harness externo ou reindexação ativa; a integração MCP real
  permanece separada na evidência do T05.
- Rollback operacional: pausar o agendador, deixar a fila e os recibos
  intactos e usar `jobs`/`work --once` manualmente. Nenhum caminho do worker
  publica ou remove a geração ativa automaticamente.
