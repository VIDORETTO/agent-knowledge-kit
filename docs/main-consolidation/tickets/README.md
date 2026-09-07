# Tickets de consolidação

Os tickets são tracer bullets: cada um entrega uma fatia observável por um seam
público e termina com gates executáveis. A ordem abaixo é também a ordem de
dependência.

| Ordem | Ticket | Bloqueado por |
|---:|---|---|
| 01 | [Congelar baselines e decisão](01-freeze-baselines.md) | — |
| 02 | [Definir lifecycle, estado e compatibilidade](02-canonical-lifecycle-contract.md) | 01 |
| 03 | [Impor MCP read-only e revogação](03-read-only-mcp-boundary.md) | 02 |
| 04 | [Consolidar geração, harness e router](04-generation-harness-router.md) | 02, 03 |
| 05 | [Distribuir a skill operacional](05-agent-skill-distribution.md) | 04 |
| 06 | [Unificar a CLI com aliases](06-cli-expand-contract.md) | 02, 05 |
| 07 | [Consolidar candidata até rollback](07-publication-lifecycle.md) | 02, 03, 04 |
| 08 | [Consolidar fontes, eventos e worker](08-sources-events-worker.md) | 02, 07 |
| 09 | [Consolidar readers e snapshots RAG](09-readers-rag-snapshots.md) | 03, 04, 07 |
| 10 | [Governar aprendizado e feedback](10-learning-feedback-governance.md) | 07, 08, 09 |
| 11 | [Eliminar drift de contratos e docs](11-contract-doc-drift.md) | 04, 06, 07, 08, 09, 10 |
| 12 | [Provar clean clone, wheel e plataformas](12-release-gates.md) | 05, 06, 11 |
| 13 | [Promover candidato de integração](13-main-promotion.md) | 12 |

Todos os tickets começam como `draft-pending-confirmation`. Eles só podem ser
publicados em um issue tracker depois de confirmação humana da granularidade,
dos seams e dos blockers. Nesta execução o pedido confirmou esses elementos;
os tickets concluídos registram a evidência no próprio arquivo. Em qualquer
estado, nunca devem ser executados diretamente na `main`.
