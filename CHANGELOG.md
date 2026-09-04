# Changelog

## Unreleased

- Closed post-1.0 reliability tickets 23–29 locally: candidate identity and
  source remeasurement, public-seam coverage, crash-recoverable promotion,
  executed support/bootstrap checks, community assets, named metrics and
  repeatable concurrent RAG stress evidence.
- Added effective transitive-resolution and vendor provenance evidence while
  preserving raw `pip-audit` findings separately from the narrow local Chroma
  residual policy; release still requires the human decision artifact.
- Bound the dependency exception to `chromadb==1.5.9`, retained raw audit
  stdout/stderr/exit evidence, and limited resolver evidence to the lock-rooted
  transitive closure instead of unrelated interpreter packages.
- Removed model-cache bytes from candidate bundles while retaining a verified
  external snapshot manifest/digest, and redacted queries and local paths from
  public evaluation, smoke, doctor and stress reports.
- Made clean-clone verification use a clone-owned isolated environment and made
  concurrent reindex stress distinguish recoverable residue from retained
  successful attempt history.
- Replaced Windows `os.kill(pid, 0)` lease probing with
  `OpenProcess`/`GetExitCodeProcess`; a separate reader can no longer interrupt
  its live writer while checking lease ownership.
- Made supply-chain resolution profile-aware: a core candidate may omit only
  the optional `knowledge-rag` root, while version drift, other missing roots
  and an incomplete explicit RAG profile fail independent verification.
- The package workflow now retains the complete candidate and identity evidence
  as an artifact named with the workflow commit SHA for later review.
- Kept the FastEmbed model cache outside generated packages and preserved
  structured wheel-gate errors when large CLI reports fail.
- Preserved the interpreter selected for candidate wheel and dependency
  evidence when a POSIX virtual environment exposes it through a symlink, and
  made the fail-closed release identity check an explicit manual CI input.
- Added an explicit authenticated GitHub settings checklist and kept commit,
  push, tag and release operations outside all local automation.
- Added the `plan`/`apply`/`inspect` operation seam with real create/update/dry-run
  lifecycle semantics, staged transactional promotion, resumable phase receipts,
  and a recoverable single-writer lease.
- Added executable contracts for manifests, handoffs, Golden sets, validation,
  plans, outcomes, results, evaluations and review-required Golden candidates.
- Distinguished scaffold, enriched-skill, corpus, indexed, evaluated and release
  readiness using observed evidence rather than editable manifest claims.
- Added resolver providers, explicit runtime provenance, redacted MCP diagnostics,
  named retrieval adapters, and MCP-backed evaluation controls.
- Added a normative support matrix, contract/release gates, immutable GitHub
  Actions revisions, and installed-wheel create/validate/evaluate coverage.

## 1.1.0 — candidate (2026-09-02; not published)

- Hardened candidate auditing for nested runtime artifacts, binary paths,
  structured token canaries and exact Git candidate sets.
- Added deterministic MCP runtime contracts, public root Python operations,
  one-way operation primitives, snapshot revalidation and observable residue
  cleanup.
- Added installed-wheel provenance, reproducible supply-chain evidence, SPDX
  SBOM, lock/digest verification, vendor/model provenance and the explicit
  four-CVE Chroma residual-risk policy.
- Added profile-based support claims, workflow drift checks, community policy
  files and the unpublished candidate bundle/verification tools.

## 1.0.0 — 2026-08-29

- Primeira versão estável do protocolo DOCOPS para fontes locais, web e
  repositórios.
- Pacotes gerados agora são autossuficientes, com configuração MCP relativa,
  validação de divergência, harness manifest e smoke test do wheel instalado.
- Adicionados bootstrap multiplataforma, auditoria de configuração/release,
  fixtures sintéticas e documentação de integração com harnesses externos.
- Atualizado o conjunto direto de ferramentas para `pytest==9.1.1`,
  `ruff==0.12.7`, `pip-audit==2.10.1`, `setuptools==84.0.0` e bootstrap com
  `pip==26.2.1`/`setuptools==84.0.0`.
- Adicionada auditoria de dependências com allowlist estreita e documentada
  para os quatro CVEs sem correção conhecida do ChromaDB; outros achados
  permanecem bloqueadores.
- Corrigido o fallback YAML para comentários inline, tornando o doctor
  funcional em clones limpos sem PyYAML.
- Corrigidos os nomes das métricas do avaliador para refletirem qualquer
  `--top-k` válido.
- Tornado o smoke MCP resistente a timeout, EOF prematuro, stderr cheio e
  encerramento de processo sem mascarar o erro original.
- Alinhado o `serverInfo` vendorizado com `knowledge-rag==4.8.5` e feito o
  transporte HTTP/SSE recusar inicialização sem bearer token.
- Reforçadas as aquisições externas contra DNS rebinding (inclusive com IPs
  fixados no Git), redirects, submódulos, protocolo `file`, prompts interativos
  e clones acima do limite.
- Adicionados testes de regressão para SSRF/TOCTOU, repositório remoto,
  autenticação bearer, auditoria de dependências e fluxo de erro do smoke MCP.
- Mantido o perfil padrão local `stdio`; corpus adquirido, índices, caches,
  tokens e ambientes virtuais continuam fora da publicação.
