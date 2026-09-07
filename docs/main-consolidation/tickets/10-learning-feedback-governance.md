---
status: done
---

# T10 — Governar aprendizado de conversa e feedback

## What to build

Entregar um fluxo em que conversa consentida e feedback autenticado geram
somente sinais ou propostas em quarentena. Uma proposta só entra em candidata
após evidência verificável; feedback repetido só abre investigação quando for
legítimo e deduplicado.

## Blocked by

- T07
- T08
- T09

## Acceptance criteria

- [x] Captura de conversa é opt-in e minimizada.
- [x] Consentimento possui titular, escopo, finalidade, expiração e revogação.
- [x] Evidência independente é verificada, não apenas declarada.
- [x] Conteúdo de agente/RAG não se torna autoridade por recursão.
- [x] Feedback possui origem autenticada, anti-replay e rate limit.
- [x] Logs e receipts não contêm conversa ou query bruta desnecessária.
- [x] Revogação propaga para proposta, candidata, release e readers.

## Evidence

- RED: `tests/test_learning.py::test_learning_does_not_treat_an_independent_flag_as_verified_evidence` and `tests/test_usage_feedback.py::test_feedback_requires_an_authenticated_origin` failed before the respective guards existed.
- GREEN/refactor: `tests/test_learning.py tests/test_usage_feedback.py tests/test_reader_sessions.py` — `18 passed`; `tests/test_candidate_publication.py` — `13 passed`; Ruff passed for the changed modules.
- Consent is normalized with holder, scope, purpose, RFC3339 grant/expiry/revocation and a content hash; admission rejects inactive consent.
- Evidence requires verifier, provenance, authority, license, claim support and matching evidence/receipt hashes; agent, conversation and RAG references remain non-independent.
- Feedback stores only query/identity hashes, requires authenticated origin fields, rejects reused event IDs and limits one origin to 20 submissions per minute.
- Learning tombstones participate in RAG snapshot revocation and candidate publication/rollback checks; `test_reader_snapshot_rejects_a_revoked_learning_derivative` proves reader invalidation.

## Rollback

Revert the T10-only changes in `docops/feedback.py`, `docops/learning.py`, `docops/rag_sync.py`, `docops/operations.py`, the two feedback schemas, and the focused tests. Existing active packages and real RAG state were not modified by the verification fixtures.
