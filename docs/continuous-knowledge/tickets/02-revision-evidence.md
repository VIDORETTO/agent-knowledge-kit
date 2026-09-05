# T02 — Vincular revisões e evidências ao conteúdo

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **piloto implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Impedir que uma avaliação antiga autorize uma composição alterada.

## Contexto

E11–E12: há hash de enriquecimento, mas o conjunto completo avaliado não está vinculado à evidência persistida. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T01](./01-protect-enrichment.md)

Decisões aplicáveis: D04 e D07. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/readiness.py](../../../docops/readiness.py), [docops/manifest.py](../../../docops/manifest.py), [docops/evaluator.py](../../../docops/evaluator.py), [docops/contracts.py](../../../docops/contracts.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

CLI evaluate/validate, docops.inspect e envelopes JSON.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Avaliar pacote por interface pública, alterar artefato relevante e inspecionar. A avaliação não pode continuar válida para a nova composição.

**GREEN mínimo:** Persistir fingerprints de corpus, skill, router, Golden e configuração e comparar durante inspeção/validação.

**REFACTOR:** Centralizar composição e serialização canônica.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Mudança relevante invalida avaliação e aprovação dependentes.
- [ ] Repetição sem mudança preserva identidade estável.
- [ ] Duração/timestamp não entram nos hashes de conteúdo.
- [ ] Pacotes v1 continuam legíveis; evidência incompleta não habilita autopublicação.

Rastreabilidade: A03, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Hashing amplo pode elevar custo; identidade circular pode nunca estabilizar. Separar conteúdo e evidência.

## Estratégia de rollback

Manter leitura v1 e desligar gates novos para publicação automática, sem reclassificar evidência antiga como atual.
