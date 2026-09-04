# Registro de prontidão — 2026-09-04

**Estado:** `release-ready-pending-human-gate`  
**Escopo:** candidate `1.1.0` do pacote `consulta-documentacao`  
**Política:** nenhuma tag, release, publicação ou anúncio foi criado por esta
execução.

Este registro separa evidência local de autorização externa. O SHA e o digest
do candidate final devem ser lidos dos arquivos gerados em
`artifacts/candidate-1.1.0/`; não são repetidos aqui para evitar referência
circular quando a documentação muda.

## Evidência automática observada

- Ambiente isolado Python 3.12 criado pelo bootstrap com perfis `dev`,
  `formats` e `rag`; `docops doctor --json` e `pip check` passaram.
- `pytest -q`: **234 passed em 310,52 s**.
- Clean clone com bootstrap, auditoria full e suíte completa: **pass**;
  o clone executou **234 passed em 93,70 s**.
- Support matrix, workflows, contratos, public seams, Ruff, format,
  `compileall`, `git diff --check` e auditoria tracked/candidate: **pass**.
- Wheel core: **pass**, `adapter=memory`, `rag=false`.
- Wheel RAG requerido: **pass**, `adapter=mcp`, `rag=true`.
- Fixture RAG: `run --index-rag`, `validate` e avaliação MCP: **pass**;
  MRR@5/Recall@5 **1.0/1.0**, 2 documentos e 4 chunks.
- Clone limpo com perfil RAG: bootstrap, `run --index-rag`, `validate` e
  avaliação MCP: **pass**, MRR@5/Recall@5 **1.0/1.0**, 2 documentos e 4
  chunks.
- MCP smoke: **pass**, handshake `2024-11-05`, backend `4.8.5`, 13 tools;
  consultas e conteúdo permaneceram redigidos.
- Stress de reindex concorrente: **pass**, 10 s, 4 readers, 33.125 buscas,
  zero erros/warnings, reindex terminal e zero resíduo recuperável.
- Vendor security: **173 passed, 3 skipped, 7 xfailed**. A suíte upstream
  completa não é um gate do `config.yaml` do produto: seus testes de preset
  exigem configuração upstream específica; a execução isolada com preset
  registrou 758 pass e 3 incompatibilidades de formatos/configuração, sem
  alterar o vendor nem o perfil do produto.
- Build do wheel agora é byte-reprodutível: o builder fixa
  `SOURCE_DATE_EPOCH=0` e há teste de igualdade byte a byte.

## Evidência negativa preservada

- O `pip-audit` cru retorna código 1 por exatamente quatro advisories em
  `chromadb==1.5.9`: `CVE-2026-45829`, `CVE-2026-45830`, `CVE-2026-45831` e
  `CVE-2026-45833`. O índice consultado não oferece versão posterior nem
  `fix_versions`; o wrapper passa apenas pela allowlist estreita do uso local.
- `verify_candidate.py --release` falha fechado enquanto a decisão Chroma,
  identidade remota e CI correspondente não estiverem presentes.
- O Golden FastAPI não foi convertido em sucesso: os 14 arquivos em
  `documents/fastapi-docs` não estão disponíveis neste checkout. Isso é um
  resultado negativo preservado, mas o piloto FastAPI foi explicitamente
  excluído do escopo público `1.1.0`; a avaliação pública usa a fixture MIT
  revisada, que passou com MRR@5/Recall@5 1.0/1.0.

## Estado externo somente leitura

- No momento da auditoria, `origin/main` e `HEAD` eram o commit
  `912599c8dc6ab7bde30e27a2cc27f0c1f1107c41`; a árvore de trabalho continha
  mudanças locais desta preparação. Os runs públicos observados para esse SHA
  foram CI `33900149915` e Integration `33900161429`, ambos concluídos com
  sucesso; isso não prova mudanças locais posteriores.
- O repositório público tem apenas a release `v1.0.0`; não existe tag/release
  pública `v1.1.0`.
- O canal selecionado para `1.1.0` é o GitHub Release; PyPI e registries
  externos estão fora do escopo, portanto não há trusted publisher a configurar.
- Endpoints públicos de proteção, Dependabot e secret scanning não forneceram
  autenticação suficiente para provar settings. A checklist permanece
  `not verified`; a resposta pública `rules=[]` não é prova de branch
  protection.

## Bloqueios humanos/externos exatos

1. Um administrador autenticado deve preencher
   `community/GITHUB-SETTINGS-CHECKLIST.md` com identidade, data e links para
   proteção de branch, required checks/reviewers, CODEOWNERS, Dependabot,
   secret scanning, push protection e permissões de release.
2. A autorização explícita para push, tag, GitHub Release, upload de assets e
   anúncio controlado foi fornecida pelo proprietário nesta execução; essas
   ações ainda precisam ser executadas depois do CI do SHA final.

## Artefatos preparados

- [`PRODUCTION-PUBLICITY-PLAN.md`](PRODUCTION-PUBLICITY-PLAN.md): fases e
  Definition of Done.
- [`RELEASE-NOTES-1.1.0.md`](RELEASE-NOTES-1.1.0.md): notas revisáveis.
- [`PUBLICITY-DRAFT-1.1.0.md`](PUBLICITY-DRAFT-1.1.0.md): anúncio não enviado.
- [`POST-RELEASE-HANDOFF-TEMPLATE.md`](POST-RELEASE-HANDOFF-TEMPLATE.md):
  canário, observação e rollback.
- `artifacts/candidate-1.1.0/`: bundle local, manifesto, checksums, SBOM,
  provenance e verificação independente; conteúdo é ignorado pelo Git.

Qualquer alteração no código, documentação, lock, vendor, metadata ou conjunto
de arquivos invalida o candidate anterior e exige nova execução dos gates.
