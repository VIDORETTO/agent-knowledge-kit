---
status: done
---

# T12 — Provar clean clone, wheel e plataformas

## What to build

Entregar um pipeline sequencial que, a partir de clone limpo, instala a wheel,
descobre a skill, executa CLI, contratos, docs, segurança, crash matrix e RAG
em Windows e POSIX.

## Blocked by

- T05
- T06
- T11

## Acceptance criteria

- [x] Build e testes não compartilham diretórios entre processos concorrentes.
- [x] Clone limpo e wheel offline executam os mesmos seams públicos.
- [x] O fallback de supply chain sem `pip` passa no ambiente suportado.
- [x] Windows e POSIX têm resultados equivalentes, com skips justificados.
- [x] Ruff, contratos, documentação e diff-check passam.
- [x] Suíte completa passa sequencialmente.
- [x] MCP real, revogação e crash matrix passam.
- [x] O relatório preserva comandos, versões, denominadores e artefatos.

## Evidence

- RED: `tests/test_release_gates.py` inicialmente falhou porque o runner não
  existia; durante o gate real também foram corrigidos, em ciclos RED → GREEN,
  o decode de locale Windows, a seleção do vendor RAG no runtime temporário e
  a interpretação correta de uma geração sem recuperação (`recovery.status=none`).
- GREEN final Windows: `artifacts/release-gates-final-20260907/release-gates.json`,
  22 estágios sequenciais, todos `passed`, com `7793` verificações passadas e
  `57` skips justificáveis; a primeira execução do mesmo gate ficou registrada
  como blocker intermediário e não é usada como evidência final.
- O relatório final preserva comandos redigidos, versões, denominadores,
  timestamps, logs stdout/stderr e artefatos por estágio. O estágio RAG real
  confirmou `wheel-rag` e o composite MCP (run → validate → evaluate MCP →
  smoke → reindex concurrency), cinco comandos com código `0`.
- Clean clone RAG completou com a cópia vendorizada e `chromadb` instalado no
  clone temporário; nenhum diretório de build foi compartilhado.
- POSIX/WSL: Python 3.12.3, `compileall`, bootstrap `--no-install`, doctor,
  contratos e documentação passaram; pip/pytest/Ruff/RAG foram skips explícitos
  porque o host WSL não possuía `pip`/`python3-venv`. O detalhe está em
  `docs/DEPENDENCIES.md`; macOS não estava disponível neste host.
- Wheel core e wheel RAG passaram em instalação isolada; o smoke MCP local e
  os testes de revogação/crash passaram no Windows.

## Rollback

O runner só escreve em `artifacts/` ignorado e em diretórios temporários. Para
reverter esta implementação, remova `scripts/run_release_gates.py`, seus testes
e os ajustes de isolamento/diagnóstico, sem tocar em `documents/`, no índice
RAG real ou em qualquer geração ativa. Os diretórios de evidência podem ser
descartados; não houve merge, push, release ou publicação.
