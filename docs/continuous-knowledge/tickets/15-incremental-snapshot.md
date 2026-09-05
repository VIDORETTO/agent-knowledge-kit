# T15 — Reaproveitar índice com snapshot consistente

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **proposto; não implementado**.

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

- [ ] Alteração de mesmo mtime/tamanho é detectada.
- [ ] Embedding diferente força full rebuild.
- [ ] Falha de snapshot preserva ativa.
- [ ] Estatísticas lógicas e busca pós-promoção conferem.
- [ ] Backend sem suporte faz rebuild declarado, nunca falsa alegação de incremental.

Rastreabilidade: A05, A06, A07 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

SQLite e arquivos auxiliares Chroma/BM25 podem divergir; cópia viva simples não é aceitável.

## Estratégia de rollback

Desabilitar reuso e reconstruir índice candidato isolado.
