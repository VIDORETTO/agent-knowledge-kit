---
status: done
---

# T06 — Unificar a CLI com migração expand-contract

## What to build

Entregar uma operação completa pela CLI hierárquica e pelo comando plano
legado, comprovando equivalência de envelope, efeito, erro e exit code. Marcar
aliases como compatibilidade temporária sem removê-los.

## Blocked by

- T02
- T05

## Acceptance criteria

- [x] A hierarquia canônica usa linguagem consistente de domínio.
- [x] Cada comando plano existente possui mapeamento explícito.
- [x] Alias e comando canônico produzem o mesmo contrato observável.
- [x] Deprecation não polui JSON estruturado.
- [x] Ajuda e command cards apontam para a interface canônica.
- [x] Existe condição objetiva para remoção futura dos aliases.

## Evidence

- RED: os testes públicos de mapa, ajuda, equivalência e status falharam
  porque `lifecycle` não era uma escolha válida e não havia mapa explícito.
- GREEN: `CLI_COMPATIBILITY_MAP` documenta todos os comandos planos; o
  expand-contract traduz a hierarquia canônica para os seams modulares já
  existentes e mantém os aliases legados sem duplicar dispatch ou estado.
- Verificação: `3 passed` no teste focal; o JSON canônico de
  `lifecycle source register` é byte-a-byte equivalente ao alias
  `source-register`, e `lifecycle status` não emite metadados de depreciação.
- Remoção dos aliases: somente depois de todos os chamadores migrarem e o
  contador de uso de aliases permanecer zero durante uma janela de release
  completa. A condição está registrada na ajuda e não depende de data fixa.

## Rollback

Remover `_expand_canonical_argv`, `CLI_COMPATIBILITY_MAP`, os aliases de
`lifecycle-status` e a entrada de ajuda hierárquica; os comandos planos e os
dispatchers modulares continuam sendo a superfície de compatibilidade.
