# consulta-documentacao 1.1.0 — release notes (draft)

> **Status:** candidate only; not published. Review this file against the
> final tag, wheel, checksums, SBOM and provenance before making it public.

## What this release is for

`consulta-documentacao` turns a documentation source into an agent-usable
package containing a structured skill, a query router, a local RAG corpus and
machine-readable provenance. The core operator is usable without an LLM,
provider, hosted service or API key.

## Highlights

- Explicit `resolve`, `plan`, `run`, `validate` and `evaluate` flows with
  relative paths, terminal outcomes and resumable checkpoints.
- Optional local `knowledge-rag`/MCP indexing with redacted diagnostics,
  factual-query evaluation and source-aware result handling.
- Candidate identity, release audit, wheel verification, SBOM, checksums and
  vendor/model provenance suitable for an independently reviewed release.
- Cross-platform bootstrap and support evidence for Python 3.11–3.13 on
  Ubuntu, Windows and macOS; Python 3.14 remains tolerated only.
- No acquired corpus, index, model cache, token, user log or private path is
  part of the release candidate.

## Installation after publication

The registry and trusted-publishing identity are not configured yet. Once a
maintainer approves a channel, install the exact downloaded wheel and verify
its checksum before use:

```text
python -m pip install consulta_documentacao-1.1.0-py3-none-any.whl
python -m docops doctor --json
```

The RAG profile is optional and must be installed only when the selected
channel, dependency decision and local threat model have been reviewed.

## Minimal flow

```text
python -m docops resolve ./documents/fixtures/acme-docs --json
python -m docops run ./documents/fixtures/acme-docs --output ./artifacts/acme --slug acme --license MIT
python -m docops validate ./artifacts/acme --json
```

## Limits and security

This package does not execute a model, choose a provider, host an HTTP service
or guarantee compatibility with every agent harness. Acquired documentation
may be copyrighted and requires an explicit license/redistribution decision.
The optional RAG dependency currently has four documented ChromaDB advisories;
the raw audit remains visible and publication requires the maintainer decision
in [`CHROMA-RESIDUAL-DECISION.md`](CHROMA-RESIDUAL-DECISION.md). Report
security issues privately according to [`SECURITY.md`](../SECURITY.md).

## Support

The normative support matrix is
[`SUPPORT-MATRIX.json`](SUPPORT-MATRIX.json). Public claims must be limited to
the platforms, Python versions and profiles verified by the final candidate
and its canary.
