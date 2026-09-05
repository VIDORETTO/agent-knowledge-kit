# T14 — Fixar geração e restringir MCP de consulta

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **piloto implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Impedir composição mista e mutação fora do coordenador.

## Contexto

E23: hand-off atual não garante fixação de sessão nem enforcement de ferramentas somente leitura. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T08](./08-approve-publish.md), [T09](./09-history-rollback.md)

Decisões aplicáveis: D08; atualizar backend vendor e schemas do harness. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/harness.py](../../../docops/harness.py), [docops/runtime.py](../../../docops/runtime.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

Hand-off de geração, sessão MCP real e publicação concorrente.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Sessão fixada consulta durante publicação; segue na mesma composição. Tentativa de add_document é recusada.

**GREEN mínimo:** Referência à geração imutável e perfil de consulta restrito no backend; manutenção usa capacidade separada.

**REFACTOR:** Separar capacidades de consulta e manutenção no runtime.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Sessão nova recebe geração nova.
- [ ] Writer do harness de consulta é recusado pelo servidor.
- [ ] Cache respeita geração e revogação.
- [ ] Sessão em geração revogada não continua consultando.
- [ ] Backend sem capacidade compatível não habilita autopublicação concorrente.

Rastreabilidade: A12, A14 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Windows e processos com arquivos abertos exigem validação própria; texto do router não é controle de acesso.

## Estratégia de rollback

Desabilitar publicação concorrente e usar atualização coordenada manual, sem alegar isolamento não comprovado.
