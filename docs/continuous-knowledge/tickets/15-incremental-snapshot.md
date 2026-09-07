# T15 — Reaproveitar índice com snapshot consistente

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **implementado localmente em 2026-09-05**.

## Objetivo e entrega

Reprocessar apenas documentos alterados preservando isolamento e recuperação.

## Contexto

E07/E08: staging novo e caminhos do backend impedem solução por simples troca de force. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T05](./05-verify-index.md), [T09](./09-history-rollback.md), [T14](./14-pinned-readers.md)

Decisões aplicáveis: D08; envolve backend vendor e seu contrato de snapshot. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/rag_sync.py](../../../docops/rag_sync.py), [docops/runtime.py](../../../docops/runtime.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

Contrato MCP proposto de snapshot, aplicação pública e relatório de reuso.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Em corpus de 100 documentos alterar um; relatório e busca comprovam 99 reutilizados e substituição correta.

**GREEN mínimo:** Snapshot íntegro do backend com caminhos relocáveis, seguido de diff explícito por hash.

**REFACTOR:** Encapsular estratégia de reuso/rebuild.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] Alteração de mesmo mtime/tamanho é detectada.
- [x] Embedding diferente força full rebuild.
- [x] Falha de snapshot preserva ativa.
- [x] Estatísticas lógicas e busca de verificação no pacote corrente conferem.
- [x] Backend sem suporte faz rebuild declarado, nunca falsa alegação de incremental.

Rastreabilidade: A05, A06, A07 em [VALIDATION](../VALIDATION.md).

## Resultado da execução

- RED: os cinco testes públicos falharam porque `rag-snapshot` ainda não
  existia.
- GREEN: a CLI passou a produzir `rag-snapshot` e `rag-reuse-plan`, com
  inventário relocável, diff por SHA-256, identidade de embedding e fallback
  explícito para rebuild.
- REFACTOR: a estratégia ficou isolada em `docops/rag_sync.py`; o relatório
  inclui o inventário lógico de `rag/index.json`/`rag/data`, preserva a ativa,
  pode gravar snapshot atomicamente e aceita busca de verificação pelo adapter
  escolhido sem promover nada.
- Verificação: `rtk pytest -q tests\test_rag_snapshots.py` — **5 passed**;
  contratos, Ruff lint/formato e `rtk git diff --check` foram revalidados no
  gate conjunto.
- Arquivos principais: `docops/rag_sync.py`, `docops/__main__.py`,
  `docops/contracts.py`, os schemas `rag-snapshot`/`rag-reuse-plan`, os
  exemplos de contrato, `tests/test_rag_snapshots.py` e a documentação de uso.
- Evidência: somente fixtures sintéticas em diretórios temporários; nenhuma
  cópia do índice ativo, conversa, corpus real, publicação, reindexação real ou
  harness externo foi executada. A busca opcional usa o adapter `memory` nos
  testes públicos.
- Rollback: desabilitar o reuso, ignorar snapshots incompatíveis e executar
  rebuild em candidata isolada. Snapshot inválido falha fechado e não altera a
  geração ativa.

## Riscos

SQLite e arquivos auxiliares Chroma/BM25 podem divergir; cópia viva simples não é aceitável.

## Estratégia de rollback

Desabilitar reuso e reconstruir índice candidato isolado.
