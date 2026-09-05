# T16 — Preservar localizadores e avaliar português

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **proposto; não implementado**.

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

- [ ] Quando localizador não existir, declarar limite e citar seção normalizada.
- [ ] Transcrição entra como Markdown externo; não prometer ASR/VTT nativo.
- [ ] Comparar perfis antes da escolha; rebuild obrigatório na troca.
- [ ] Unidades de planilha e identificadores de código são preservados.
- [ ] Fonte de baixa qualidade permanece em quarentena.

Rastreabilidade: A05, A15 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Extrator pode omitir conteúdo visual; métricas inglesas não generalizam.

## Estratégia de rollback

Retornar extração à quarentena e exigir ferramenta externa, preservando fonte original autorizada.
