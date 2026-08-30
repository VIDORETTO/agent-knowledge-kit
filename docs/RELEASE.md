# Checklist de release 1.0.0

Execute em um clone limpo e preserve a ordem. O comando de dependências deve
ser executado com o ambiente opcional RAG quando esse perfil fizer parte da
release:

```text
python scripts/bootstrap.py --dev
python -m docops doctor --json
python -m pytest -q
python -m ruff check docops tests scripts
python scripts/verify_wheel.py
python scripts/audit_release.py --json
python scripts/audit_dependencies.py --requirements requirements.lock --local --strict
python -m docops run documents/fixtures/acme-docs --output artifacts/acme --slug acme --license MIT
python -m docops validate artifacts/acme --json
python -m docops evaluate --package artifacts/acme --cases golden-set/test-cases-fixture.json --json
```

Para integração RAG, prepare o perfil opcional e rode `scripts/mcp_smoke.py` e
`scripts/test_reindex_concurrency.py`. O CI rápido não baixa modelos nem
material protegido; integração e cenários de harness ficam em workflow manual,
agenda ou release.

## Gatilhos de segurança

Antes da tag:

- confirme que `manifest.json` registra versão, proveniência e licença;
- audite o transporte configurado e não inclua `config/network.yaml`;
- confira que `git status --ignored` mostra corpora, estado, cache e saídas como
  ignorados;
- confira a lista de arquivos rastreados com `git ls-files`;
- execute a auditoria de dependências; somente os quatro CVEs documentados do
  ChromaDB podem permanecer como risco residual explícito;
- valide o contrato gerado com `schemas/harness.schema.json`;
- registre as versões dos harnesses realmente instalados. Um harness sem
  acesso não deve ser anunciado como compatível.

O auditor de release completo deve ser executado em clone limpo. Em um checkout
de trabalho com `.venv`, caches ou artefatos ignorados, use
`python scripts/audit_release.py --tracked-only --json` para auditar exatamente
o conteúdo que será publicado; a auditoria completa deve continuar rejeitando
esses diretórios caso tentem entrar no release.

## Evidência desta release

O resultado final, incluindo commit, tag, release do GitHub, workflows e hashes,
é registrado em `tasks/todo.md` depois da publicação. A matriz de harnesses e as
limitações de plataforma estão em [HARNESSES.md](HARNESSES.md). A publicação não
inclui corpus adquirido, índices, caches, tokens ou ambientes virtuais.
