# T01 — Proteger a skill enriquecida contra sobrescrita

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente em 2026-09-04**.

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

- [x] Scaffold inalterado continua atualizável.
- [x] Skill modificada, capítulo extra e artefato removido não são sobrescritos silenciosamente.
- [x] Ausência de baseline em pacote legado produz migração explícita; não adotar automaticamente.
- [x] Plano obsoleto ou edição durante a operação continua rejeitado.

Rastreabilidade: A01, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Implementação verificada

`docops/generation.py` grava `.docops/generated-artifacts.json` com o owner e
hash SHA-256 de todos os arquivos em `skill/` e `router/`. Antes de uma
atualização, a operação compara esse inventário com o checkout ativo e bloqueia
qualquer divergência com `skill_update_requires_review`; pacotes gerados antes
do inventário retornam `artifact_baseline_required` para migração explícita.
O inventário é escrito no staging após a geração e participa do recibo da fase
de artefatos.

RED observado: o teste obrigatório passou a falhar porque a atualização
retornava sucesso (`result.ok is True`) após editar a skill. GREEN: o mesmo
teste e os cenários de scaffold, capítulo extra, artefato removido, baseline
legado e plano obsoleto passaram pelo seam público. O comportamento foi
verificado apenas com fixtures sintéticas; nenhuma fonte, índice ou pacote de
produção foi alterado.

## Riscos

Baseline ausente pode bloquear pacote legítimo. Oferecer adoção explícita em migração, sem presumir que o gerador é dono do conteúdo.

## Estratégia de rollback

Desativar atualização desse pacote e conservar a geração ativa. Nenhuma restauração é necessária se a guarda atuar antes da mutação.
