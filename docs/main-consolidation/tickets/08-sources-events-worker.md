---
status: done
---

# T08 — Consolidar fontes, eventos e worker retomável

## What to build

Entregar uma mudança de fonte autorizada que gera revisão e evento
idempotentes, é processada por um worker com debounce, lease e retry e termina
em candidata ou atualização factual segura.

## Blocked by

- T02
- T07

## Acceptance criteria

- [x] Reconciliação exige fonte registrada e admitida.
- [x] Direitos, privacidade, autoridade e completude são gates executáveis.
- [x] Fonte retirada exige reautorização explícita para retornar.
- [x] Eventos duplicados não duplicam efeitos.
- [x] Leases, retries e receipts permitem retomada após crash.
- [x] Mudança conceitual nunca é publicada como simples atualização factual.
- [x] O worker pode operar em foreground sem prometer scheduler embutido.

## Evidence

- RED: uma fonte com política `unknown` era reconciliada e uma fonte
  `withdrawn` podia ser reativada por um `register` comum.
- GREEN: reconciliação exige direitos, privacidade, autoridade e owner
  explícitos; `--readmit` é obrigatório para reautorização e preserva o
  tombstone/histórico anterior. Eventos são deduplicados por `event_id` e
  coalescidos por chave; o worker continua foreground/`--once`.
- Verificação: `tests/test_source_registry.py`,
  `tests/test_coordination.py` e `tests/test_worker.py` passaram (`19 passed`),
  incluindo retry-limit, lease ocupado, crash após receipt e efeito
  reconciliado. A mudança conceitual permanece em candidata review-first.
- Nenhum scheduler gerenciado, corpus real ou índice ativo foi acionado.

## Rollback

Reverter o gate de admissão/reentrada de `source_policy.py` e as opções
`--readmit`; a fila SQLite local e o worker público permanecem removíveis sem
afetar os artefatos gerados.
