# Aceitação por ticket

Este registro liga cada gate do roadmap a uma seam verificável. Os testes
rápidos não iniciam MCP nem baixam modelos; a integração real é opt-in.

| Ticket/gate | Evidência executável |
|---|---|
| DOCOPS-001 | `bootstrap.py`, `docops doctor`, `verify_clean_clone.py`, CI Windows/Ubuntu/macOS |
| DOCOPS-002 | `run_pipeline` + `validate_package`, `tests/test_pipeline.py` |
| DOCOPS-003/004 | `WebAcquirer`, fixtures HTTP, sitemap/robots, SSRF e limites em `tests/test_web_acquirer.py` |
| DOCOPS-005/006 | `RepositoryAcquirer` e `SourceResolver`, testes de tag/árvore/catálogo |
| DOCOPS-007 | `StateStore`, `CheckpointStore`, escritas atômicas e teste de repetição |
| DOCOPS-008 | `evaluate_package`, Golden revisado obrigatório e métricas Recall@5/MRR@5 |
| DOCOPS-009 | `config-audit`, `release_audit`, prompt-injection/SSRF/OCR/auth tests |
| DOCOPS-010 | workflows CI/integration, schemas, tutorial sintético e checklist de RC |

## Comandos locais

```text
python -m pytest -q
python -m ruff check docops tests scripts
python scripts/audit_release.py --json
python scripts/verify_clean_clone.py
```

O último comando cria um diretório temporário fora do checkout, copia somente o
material distribuível e roda doctor, auditoria e testes. Use `--keep` para
inspecionar o clone temporário.

Na validação desta implementação, a suíte passou com **59 testes**, o Ruff não
encontrou problemas e a auditoria de um clone limpo passou sem findings. O
fluxo real `docops run --index-rag` também passou com fixture sintética, smoke
MCP positivo e reindexação concorrente sem erros.

## Integração opcional

Com `python scripts/bootstrap.py --dev --rag`, o workflow manual/semana executa
o servidor real, `scripts/mcp_smoke.py` e
`scripts/test_reindex_concurrency.py`. Uma execução com rede/configuração de
produção deve também passar `config-audit`; nenhuma etapa publica ou faz commit.

## Harnesses

O contrato comum é validado por `harness.json`. A última etapa de conformidade
em OpenCode, Claude Code e Codex requer cada host instalado pelo mantenedor e
não pode ser simulada por este repositório; [HARNESSES.md](HARNESSES.md)
descreve a sessão manual sem transferir controle do modelo para o operador.
