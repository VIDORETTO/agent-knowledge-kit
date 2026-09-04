# Decisão humana pendente — risco residual ChromaDB

Este arquivo é um gate de publicação, não uma declaração de auditoria limpa.
O perfil RAG usa `chromadb` somente pelo `PersistentClient` local, com MCP
`stdio`, sem `HttpClient`, `trust_remote_code` ou repositório remoto de modelo.

O `pip-audit` cru continua sendo a fonte de verdade para vulnerabilidades. Os
quatro advisories conhecidos precisam permanecer visíveis no relatório:

- `CVE-2026-45829`
- `CVE-2026-45830`
- `CVE-2026-45831`
- `CVE-2026-45833`

## Registro do mantenedor

Antes de qualquer release, um mantenedor deve preencher esta seção com a
decisão `accept`, `mitigate`, `upgrade` ou `remove`, incluindo nome, data,
versão auditada, justificativa e prazo de reavaliação. Enquanto o registro não
estiver preenchido, `scripts/verify_candidate.py --release` deve falhar.

| Campo | Valor obrigatório | Estado atual |
|---|---|---|
| decisão | `accept`, `mitigate`, `upgrade` ou `remove` | `pending-maintainer-decision` |
| responsável | identidade do mantenedor | não registrado |
| data | ISO-8601 | não registrada |
| versão | versão efetivamente auditada | `chromadb==1.5.9` no snapshot documentado |
| justificativa | motivo verificável da decisão | não registrada |
| reavaliação | data ou condição objetiva | não registrada |

Não preencher este registro automaticamente: a aceitação do risco é uma
decisão humana e deve ocorrer fora do gerador de evidências.
