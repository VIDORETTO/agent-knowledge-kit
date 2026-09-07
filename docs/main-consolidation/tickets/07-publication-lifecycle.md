---
status: done
---

# T07 — Consolidar candidata, avaliação, aprovação, publicação e rollback

## What to build

Entregar uma fatia completa que prepara uma candidata isolada, recebe
enriquecimento verificável, avalia, aprova hashes exatos, publica sob lease e
faz rollback somente para uma release válida.

## Blocked by

- T02
- T03
- T04

## Acceptance criteria

- [x] Candidata nunca altera a geração ativa antes da publicação.
- [x] Avaliação válida e atual é obrigatória.
- [x] Aprovação comprova identidade e autoridade externas.
- [x] A base é revalidada depois da aquisição do lease.
- [x] Dependência revogada bloqueia aprovação, publicação e rollback.
- [x] Crash antes/depois de cada efeito converge para um único estado válido.

## Evidence

- RED: o failpoint `after-active-to-backup` deixava a publicação sem geração
  ativa no retry; a aprovação ainda persistia `authority.authenticated=false`,
  e uma fonte `withdrawn` não bloqueava uma candidata.
- GREEN: publicação e rollback recuperam o journal sob o lease antes de
  reavaliar o contexto; a troca de diretório usa o prefixo recuperável
  `staging-`, e retries são idempotentes inclusive depois da instalação da
  geração. Revogações de registry, tombstone e `rag/sources.json` são
  verificadas em aprovação, publicação e rollback.
- Autoridade: `--authority-json` valida subject, role, source, autenticação e
  proof; somente o hash do proof entra no receipt. O caminho de compatibilidade
  registra explicitamente o adapter de processo, sem armazenar credencial.
- Verificação: suíte de candidata/avaliação/publicação/rollback verde; cinco
  failpoints de promoção e dois failpoints de rollback foram exercitados em
  processos separados, preservando o pacote ativo quando a operação não podia
  concluir.
- Nenhum corpus, índice RAG real ou publicação externa foi alterado.

## Rollback

Reverter os helpers de recuperação e as chamadas no início de
`publish_candidate`/`rollback_candidate`, remover a checagem de dependências
revogadas e restaurar o schema anterior de approval; a candidata isolada e os
leases existentes continuam independentes.
