# Checklist de release 1.0.0

Execute em um clone limpo e preserve a ordem:

```text
python scripts/bootstrap.py --dev
python -m docops doctor --json
python -m pytest
python -m ruff check docops tests scripts
python scripts/verify_wheel.py
python scripts/audit_release.py --json
python -m docops run documents/fixtures/acme-docs --output artifacts/acme --slug acme --license MIT
python -m docops validate artifacts/acme --json
python -m docops evaluate --package artifacts/acme --cases golden-set/test-cases-fixture.json --json
```

Para integração RAG, prepare o perfil opcional e rode `scripts/mcp_smoke.py` e
`scripts/test_reindex_concurrency.py`. O CI rápido não baixa modelos nem
material protegido; integração e cenários de harness ficam em workflow manual,
agenda ou release.

Antes de publicar a tag:

- confirme que o `manifest.json` registra versão, proveniência e licença;
- audite o transporte configurado e não inclua `config/network.yaml`;
- confira que `git status --ignored` mostra corpora, estado, cache e saídas como
  ignorados;
- repita o tutorial em Windows, Linux e macOS fora da máquina de desenvolvimento;
- valide manualmente uma sessão em OpenCode, Claude Code e Codex, porque o
  repositório não pode controlar esses hosts.

O código já está preparado para publicação local como 1.0.0. Commit, tag, push e
sessões externas continuam sendo ações do mantenedor e não são executadas pelo
pipeline.
