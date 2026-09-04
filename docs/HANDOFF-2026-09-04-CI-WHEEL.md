# Handoff de continuidade — follow-up do CI do wheel RAG

**Data do checkpoint:** 2026-09-04
**Repositório:** `VIDORETTO/agent-knowledge-kit`
**Branch:** `main`
**Base conferida antes da correção:** `7916083df3e930cdaff1e40968040d90ac8e9428` (`HEAD == origin/main`)

## Onde a execução anterior parou

A execução anterior já havia enviado o commit `7916083`. O follow-up ficou
parado na análise do CI desse commit:

- o job Linux do wheel RAG falhou no run `33887455346`;
- a causa raiz confirmada foi o FastEmbed criar symlinks em
  `rag/models_cache`, contaminando o pacote distribuível;
- o wheel RAG real passou localmente em Linux/Python 3.12 e
  Windows/Python 3.14;
- os testes focados reportados eram `7 passed`;
- Ruff, formato, contratos, public seams, matriz de suporte e
  `git diff --check` haviam passado;
- a suíte completa foi interrompida por volta de 35–40%, sem resultado final
  coletado; os dois skips esperados eram de symlink no Windows;
- a correção ainda não tinha commit, push ou novo CI;
- o candidate anterior, produzido a partir de `7916083`, ficou obsoleto;
- nenhuma tag ou release foi criada;
- permanece pendente a decisão humana sobre os quatro CVEs residuais de
  `chromadb==1.5.9`.

## Correção e estado local atual

A correção em andamento faz duas coisas relacionadas à causa raiz:

1. `docops/rag_sync.py` gera `models_cache_dir: ~/.cache/docops/models`, fora
   da árvore do pacote. O cache é estado de execução, não artefato
   distribuível.
2. `scripts/verify_wheel.py` extrai `errors` e `outcome` do JSON de uma CLI que
   falhou, preservando o diagnóstico estruturado mesmo quando o relatório é
   maior que o limite de saída.

Há regressões para a configuração renderizada pelo pipeline e para o
diagnóstico do verificador em `tests/test_pipeline.py`, `tests/test_rag_sync.py`
e `tests/test_verify_wheel.py`. A documentação operacional foi alinhada em
`docs/USE.md`; o checklist e as lições desta execução ficam em
`tasks/todo.md` e `tasks/lessons.md`.

## Evidência coletada nesta continuação

- Identidade inicial confirmada: `main`, `HEAD == origin/main`, base
  `7916083df3e930cdaff1e40968040d90ac8e9428`.
- Testes focados executados:
  `python -m pytest -q tests/test_pipeline.py tests/test_rag_sync.py tests/test_verify_wheel.py` —
  `21 passed, 1 skipped`; o skip é a criação de symlink indisponível neste
  host Windows.
- Suíte completa executada com o Python local tolerado 3.14.2:
  `228 passed, 2 skipped in 419.82s`; os skips são os testes de symlink
  `tests/test_package_contract.py` e `tests/test_pipeline.py` neste Windows.
- Ruff lint, Ruff format, contratos, matriz de suporte, workflows, public seams,
  `compileall` e `git diff --check` passaram.
- `audit_release.py --tracked-only --json` passou com 401 arquivos e
  `audit_release.py --candidate --json` passou com 403 arquivos.
- `pip check` passou no ambiente `.venv` do projeto. O interpretador global
  tinha pacotes externos inconsistentes e não foi usado como evidência do
  projeto.
- Wheel core passou em sequência com `adapter=memory`, `rag=false`; wheel RAG
  passou em sequência com o `.venv` do projeto, `adapter=mcp`, `rag=true`.
- Depois do commit local, um candidate RAG novo foi gerado e verificado
  independentemente com sucesso. A identidade registra
  `local-commit-candidate` e remote evidence não observada; o digest deve ser
  lido de `candidate-identity.json`, sem ser copiado para este documento.
- Uma primeira tentativa paralela dos dois wheels foi descartada: o core teve
  `WinError 2` por corrida nos diretórios de build compartilhados e o RAG foi
  iniciado no interpretador global sem o backend. Após remover somente os
  diretórios gerados/ignorados e executar sequencialmente, ambos passaram.

## Estado após o commit local

O diff foi revisado, o commit corretivo foi criado e o candidate local foi
regenerado/verificado depois dele. Em um computador novo, confirme o estado
sincronizado com `git log -1`, `git rev-parse HEAD`, `git rev-parse
origin/main` e `git status --short`.

Continuidade pós-push:

- conferir que `origin/main` aponta para o novo `HEAD` e aguardar o CI do mesmo
  SHA, em especial o job `package` Linux/Python 3.12;
- considerar o candidate gerado pelo CI como o novo candidate, pois qualquer
  bundle anterior baseado em `7916083` não representa esta correção;
- manter release/tag/publicação bloqueadas até o CI do novo SHA, a revisão
  autenticada das settings do GitHub e a decisão humana sobre o residual do
  Chroma;
- não commitar `documents/`, `data/`, `models_cache/`, ambientes, caches ou
  `artifacts/`.

O commit que contém este handoff deve ser identificado com `git log -1` após o
push; este documento não repete seu próprio SHA para evitar referência
circular na identidade do candidate.
