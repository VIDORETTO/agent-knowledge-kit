# T01 — Proteger a skill enriquecida contra sobrescrita

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **piloto implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Impedir que uma atualização documental substitua silenciosamente uma skill enriquecida por scaffold.

## Contexto

E03–E05 mostram que o staging regenera raízes geradas. A primeira entrega protege o ativo antes de qualquer automação. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: Nenhuma — primeiro ticket da sequência.

Decisões aplicáveis: D07; não depende de aprovação de comandos novos. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/generation.py](../../../docops/generation.py), [docops/operations.py](../../../docops/operations.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

docops.plan/apply, resultado público e arquivos da skill.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Gerar pacote, acrescentar parágrafo conceitual literal à skill, alterar fonte e solicitar atualização. Esperar skill_update_requires_review e conteúdo ativo intacto.

**GREEN mínimo:** Registrar inventário de hashes na geração e verificar propriedade antes da substituição. Conteúdo divergente bloqueia a operação.

**REFACTOR:** Concentrar a verificação de propriedade sem expor helpers.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Scaffold inalterado continua atualizável.
- [ ] Skill modificada, capítulo extra e artefato removido não são sobrescritos silenciosamente.
- [ ] Ausência de baseline em pacote legado produz migração explícita; não adotar automaticamente.
- [ ] Plano obsoleto ou edição durante a operação continua rejeitado.

Rastreabilidade: A01, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Baseline ausente pode bloquear pacote legítimo. Oferecer adoção explícita em migração, sem presumir que o gerador é dono do conteúdo.

## Estratégia de rollback

Desativar atualização desse pacote e conservar a geração ativa. Nenhuma restauração é necessária se a guarda atuar antes da mutação.
