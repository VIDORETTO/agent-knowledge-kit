# T10 — Registrar fontes e reconciliar escopo completo

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **proposto; não implementado**.

## Objetivo e entrega

Adicionar fontes sem substituir implicitamente o conjunto existente e impedir remoção por falha de aquisição.

## Contexto

E06/E16: diff depende do conjunto desejado e aquisição web é limitada. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T02](./02-revision-evidence.md), [T03](./03-rag-preserve-skill.md)

Decisões aplicáveis: D11, D14. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

`docops/source_policy.py` (novo), [docops/state.py](../../../docops/state.py), [docops/web_acquirer.py](../../../docops/web_acquirer.py), [docops/repository_acquirer.py](../../../docops/repository_acquirer.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

CLI source register/reconcile e docops.plan.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Cadastrar uma segunda fonte e reconciliar; a primeira permanece. Em ciclo seguinte, crawl parcial não deve removê-la.

**GREEN mínimo:** Registro por source_id e snapshot com escopo/completude; remoções exigem evidência dentro desse escopo.

**REFACTOR:** Separar descoberta, admissão e reconciliação.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Nova fonte preserva as cadastradas.
- [ ] Timeout/limite/robots não vira tombstone.
- [ ] Duplicata física preserva proveniências e direitos.
- [ ] Versionamento fixado não avança sozinho.
- [ ] Última fonte removida produz retirada explícita, não ready vazio.

Rastreabilidade: A10, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Escopo incorreto pode causar exclusão indevida; ausência web não comprova remoção.

## Estratégia de rollback

Reverter registro e reconciliar sob revisão; preservar ativa até snapshot válido.
