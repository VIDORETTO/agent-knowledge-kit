# Release candidate 1.1.0 (not published)

The current publication verdict is recorded in
`docs/GITHUB-PUBLICATION-AUDIT-2026-09-02.md`. It supersedes the historical
2026-09-01 audit for release decisions; the candidate remains local until its
identity, dependency decision and remote CI evidence are closed.

This is the executable runbook for the post-1.0 candidate. Every gate must
refer to the same Git `HEAD` and candidate digest recorded by
`candidate-manifest.json`. The runbook produces local evidence only; it never
commits, tags, pushes, publishes or creates a release.

Run the gates in this order from a clean clone or the explicitly selected
working-tree candidate:

```text
python scripts/bootstrap.py --dev
python -m docops doctor --json
python scripts/audit_dependencies.py --requirements requirements.lock --local --strict
python scripts/check_support_matrix.py --json
python scripts/check_contracts.py --json
python -m pytest -q
python -m ruff check docops tests scripts
python -m ruff format --check docops tests scripts
python scripts/verify_clean_clone.py
python scripts/verify_wheel.py
python scripts/generate_supply_chain.py --root . --wheel dist/<wheel>.whl --output artifacts/supply-chain
python scripts/verify_supply_chain.py --root . --evidence artifacts/supply-chain
python scripts/mcp_smoke.py "background tasks"
python scripts/test_reindex_concurrency.py --seconds 20
python scripts/audit_release.py --candidate --json
python scripts/prepare_candidate.py --root . --output artifacts/candidate-1.1.0
python scripts/verify_candidate.py --root artifacts/candidate-1.1.0
```

The optional RAG profile runs in its own environment. It must execute
`run --index-rag` → `validate` → `evaluate --adapter mcp`; a missing optional
runtime is recorded as `SKIPPED [rag_optional_unavailable]`, while a requested
RAG gate fails. The wheel gate sets `DOCOPS_REQUIRE_WHEEL_RAG=1` when RAG is
part of the candidate and must report the installed-package provenance.

## Candidate identity and artifacts

`prepare_candidate.py` builds the wheel with one selected interpreter, audits
the exact tracked plus non-ignored candidate file set, records `HEAD` and a
SHA-256 candidate digest, and emits:

- `candidate-manifest.json` with version `1.1.0`, gate identity and publication
  status;
- `wheel/*.whl`, top-level `SHA256SUMS` and the repository metadata;
- `evidence/sbom.json`, lock evidence, vendor/model provenance and independent
  supply-chain checksums;
- Code of Conduct, governance/maintainers, support policy and issue/PR
  templates under `community/`.

`verify_candidate.py` is an independent local verifier. It checks the wheel
metadata, bundle checksums, required community/metadata files, candidate audit,
source identity, publication=false and the supply-chain evidence. Model
snapshots are not copied unless `--model-cache` is supplied; use
`--require-model` for a RAG candidate.

## Security and operational review

The four documented Chroma advisories remain an explicit residual risk limited
to the local `PersistentClient` threat model. HTTP Chroma, remote model
repositories and `trust_remote_code` invalidate the candidate policy. Review
licenses, vendor provenance, model provenance and the residual advisories
before publication.

Branch protections, required reviewers, CODEOWNERS and least-privilege release
permissions are represented as `human-review-required` evidence. A maintainer
must verify those GitHub settings before authorizing publication; local scripts
do not attempt to change them.

The public `docops.inspect()` seam waits for an active writer lease to settle
before returning a generation. This is the supported reader guarantee. Raw
filesystem consumers may observe a platform-specific directory replacement
window, so the product does not claim distributed or universally atomic
promotion.

The published `1.0.0` release and its historical workflow evidence remain
documented in `docs/GITHUB-PUBLICATION-AUDIT-2026-09-01.md` and the older
records in `tasks/todo.md`. The current critical re-audit is
`docs/GITHUB-PUBLICATION-AUDIT-2026-09-02.md`; this candidate does not reuse
the 1.0.0 release identity.
