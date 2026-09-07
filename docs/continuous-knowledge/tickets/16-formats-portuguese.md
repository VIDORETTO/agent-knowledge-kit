# T16 — Preservar localizadores e avaliar português

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente em 2026-09-05**.

## Objetivo e entrega

Tornar formatos diversos e perguntas em português rastreáveis.

## Contexto

E15/E17: formatos têm perdas de extração e compact usa modelo inglês; localizadores não podem ser inventados. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T05](./05-verify-index.md), [T07](./07-candidate-evaluation.md), [T10](./10-source-registry.md)

Decisões aplicáveis: D09, D11. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/normalizer.py](../../../docops/normalizer.py), [docops/retrieval.py](../../../docops/retrieval.py), [docops/evaluator.py](../../../docops/evaluator.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

Ingestão pública, fontes JSON, busca e avaliação de citações.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Ingerir fixture com localizador conhecido e perguntar em português; recuperar evidência com seção/página/slide/aba/timestamp disponível.

**GREEN mínimo:** Adicionar metadado de localizador preservado na transformação e casos nativos revisados.

**REFACTOR:** Padronizar localizadores e cadeia de transformação.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] Quando localizador não existir, declarar limite e citar seção normalizada.
- [x] Transcrição entra como Markdown externo; não prometer ASR/VTT nativo.
- [x] Comparar perfis antes da escolha; rebuild obrigatório na troca.
- [x] Unidades de planilha e identificadores de código são preservados.
- [x] Fonte de baixa qualidade permanece em quarentena.

Rastreabilidade: A05, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Resultado da execução

- RED: o primeiro teste falhou porque a busca não devolvia `locators`; os
  testes seguintes também expuseram a ausência do comando público de comparação
  de perfis.
- GREEN: a normalização preserva páginas, slides, abas/células, timestamps e
  identificadores de código; a busca devolve localizadores e citações estáveis.
  Formatos de transcrição (`.vtt`, `.srt`, `.ass`, `.ssa`) exigem Markdown
  externo com timestamps.
- REFACTOR: localizadores usam um envelope comum com `kind`, disponibilidade e
  limite explícito; extrações suspeitas entram em quarentena e não são
  indexadas; `rag-profile-compare` produz decisão somente leitura e não permite
  escolher perfil sem avaliação Golden nativa.
- Verificação: fixtures sintéticas temporárias cobrem o fluxo público; contratos,
  Ruff, formato e `git diff --check` foram executados no gate do ticket.
- Integração: nenhum corpus real, reindexação real, conversa, publicação externa
  ou harness externo foi usado neste ticket.
- Rollback: manter a fonte autorizada, devolver a extração à quarentena e exigir
  um conversor externo para transcrição; mudança de embedding exige full rebuild
  antes de qualquer promoção.

## Riscos

Extrator pode omitir conteúdo visual; métricas inglesas não generalizam.

## Estratégia de rollback

Retornar extração à quarentena e exigir ferramenta externa, preservando fonte original autorizada.
