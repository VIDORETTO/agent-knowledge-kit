# Plano de estabilização e publicação — agent-knowledge-kit

> Checklist operacional da release técnica pública 1.0.0. Cada item marcado
> abaixo tem uma decisão, um teste ou uma evidência verificável. Corpus,
> índices, caches, tokens, ambientes virtuais e artefatos gerados permanecem
> fora do Git.

## Estado da execução

- **Data da execução:** 2026-08-30.
- **Versão:** `1.0.0` em `pyproject.toml`.
- **Baseline:** `736c321eb46d1e279e49be7d77727f857b5fe62a` (estado recebido).
- **Escopo anunciado:** protocolo DOCOPS, skills, MCP/RAG opcional e fixtures
  sintéticas; o produto não hospeda nem escolhe um LLM.
- **Suporte verificado:** OpenCode 1.18.25 e Codex CLI 0.151.0 no Windows.
  Claude Code não está instalado e não é anunciado nesta versão.
- **Plataformas:** Windows comprovado manualmente; Linux/macOS cobertos pela
  matriz pública do CI quando os workflows finais passarem. Não há alegação de
  bootstrap manual local nesses dois sistemas.

## Fase 0 — contrato, escopo e política

- [x] Confirmar a fronteira: o harness externo executa o modelo; este projeto
  fornece protocolo, skills, artefatos, ferramentas e MCP opcional.
- [x] Definir o seam de teste como o pacote de conhecimento validável:
  `skill/`, `router/`, `rag/`, `manifest.json`, `harness.json` e checkpoints.
- [x] Fixar MIT para o código e manter documentos adquiridos fora do release
  salvo licença/permissão explícita no manifesto.
- [x] Definir política de fontes, redaction, proveniência, ambiguidade e
  citações factuais (`path#secao` ou `path:linha`).
- [x] Definir que `stdio` local é o padrão e que HTTP/SSE é opt-in protegido.

## Fase 1 — clone, instalação e empacotamento

- [x] Manter `README.md`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`,
  `docs/USE.md`, `docs/RELEASE.md` e os schemas no repositório.
- [x] Remover caminhos absolutos do produto e preservar configurações já
  existentes; o pacote gerado usa caminhos relativos.
- [x] Fixar dependências diretas: `knowledge-rag==4.8.5`, `PyYAML==6.0.3`,
  `pypdf==6.16.2`, `python-docx==1.2.0`, `pytest==9.1.1`, `ruff==0.12.7`,
  `pip-audit==2.10.1` e `setuptools==84.0.0`; bootstrap usa
  `pip==26.2.1`/`setuptools==84.0.0`.
- [x] Manter o vendor revisado de `knowledge-rag` sem Git aninhado e alinhar
  `serverInfo.version` com `4.8.5`.
- [x] Configurar `.gitignore` e o auditor para impedir corpus adquirido,
  `.rag_state.json`, `data/`, `models_cache/`, `.venv*`, tokens, logs e saídas.
- [x] Adicionar `dependabot.yml` para atualizações semanais de pip e actions;
  Dependabot security updates e secret scanning/push protection estão ativos
  no repositório público.

## Fase 2 — tracer bullet DOCOPS local

- [x] Resolver nome, URL, repositório HTTPS e pasta local com ambiguidade e
  erros estruturados.
- [x] Adquirir e normalizar Markdown, texto, HTML, PDF, DOCX, OpenAPI, YAML,
  JSON, notebooks, XLSX e PPTX conforme capacidades e limites declarados.
- [x] Aplicar SSRF, robots/sitemap, limites de páginas/payload/tempo/retries,
  redaction, conteúdo não confiável e licenciamento.
- [x] Gerar skill, router, corpus normalizado, `config.yaml`, `harness.json`,
  manifesto, schemas e checkpoints de forma idempotente.
- [x] Executar a fixture `documents/fixtures/acme-docs` com `docops run`,
  `validate` e `evaluate`; resultado observado: 2 documentos, 4 chunks e
  Recall@5/MRR@5 de 1.0 na avaliação lexical.
- [x] Validar a skill FastAPI e o router sem warnings no validator; a skill
  roteadora exige citações para fatos literais e sinaliza divergência.

## Fase 3 — RAG híbrido e MCP

- [x] Manter `knowledge-rag` opcional, `PersistentClient` local, cache de
  modelos ignorado e transporte padrão `stdio`.
- [x] Integrar o vendor revisado ao runtime do reindex/smoke quando o pacote
  é executado a partir deste checkout; não depender silenciosamente de uma
  cópia instalada com versão diferente.
- [x] Executar smoke MCP real: handshake, `tools/list`, busca híbrida e
  verificação de `serverInfo.version == 4.8.5` passaram.
- [x] Executar a fixture com `--index-rag`: 2 documentos e 4 chunks indexados,
  sem erro; o perfil observado foi `BAAI/bge-small-en-v1.5`.
- [x] Executar `scripts/evaluate_golden.py --cases golden-set/test-cases.json`:
  10 casos, Recall@5 `1.0` e MRR@5 `0.95`.
- [x] Executar reindexação concorrente por 5 segundos: 2 buscas, zero erros,
  reindexação final inativa e 2 documentos/4 chunks.

## Fase 4 — qualidade, segurança e dependências (P0/P1/P2)

### P0 — publicação e compatibilidade

- [x] Confirmar visibilidade pública anônima: API e página GitHub retornaram
  HTTP 200, `isPrivate=false`, `visibility=PUBLIC`; `git ls-remote` anônimo
  encontrou `origin/main` no baseline antes desta execução.
- [x] Executar sessão real somente leitura no OpenCode 1.18.25; versão 1.0.0,
  comando MCP relativo, `stdio` e contrato foram confirmados.
- [x] Executar sessão real somente leitura no Codex CLI 0.151.0; manifesto
  gerado foi validado contra Draft 2020-12 sem erros. O runner global não tinha
  diretório temporário utilizável para pytest, mas a suíte do projeto passou no
  `.venv` dedicado.
- [x] Remover Claude Code da promessa de suporte por não estar instalado neste
  host; outros harnesses são suportados apenas pelo protocolo Agent Skills +
  MCP e não por uma sessão específica não verificada.
- [x] Ajustar a documentação de plataforma: bootstrap/doctor/testes foram
  comprovados no Windows; em Ubuntu WSL passaram `doctor` e `compileall`, mas o
  bootstrap completo foi bloqueado pela ausência de `python3-venv`/`pip` e pela
  falta de permissão administrativa; não há host macOS disponível. A matriz CI
  continua sendo a evidência automatizada para Linux/macOS.
- [x] Corrigir o fallback YAML para comentários inline sem corromper `#` dentro
  de strings; o clone limpo agora aceita o `config.yaml` sem PyYAML.
- [x] Corrigir métricas do avaliador para usar `recall_at_<k>`/`mrr_at_<k>`
  coerentes com `--top-k`, com regressão para `top_k=1`.

### P0 — dependências vulneráveis

- [x] Atualizar pip e pytest vulneráveis para `pip==26.2.1` e `pytest==9.1.1`;
  incluir `pip-audit==2.10.1` no perfil de desenvolvimento.
- [x] Criar `scripts/audit_dependencies.py` e gate CI. Auditoria de lock e
  ambiente local passou com `--strict`: não há findings fora da política.
- [x] Registrar explicitamente o residual de `chromadb==1.5.9`: somente
  `CVE-2026-45829`, `CVE-2026-45830`, `CVE-2026-45831` e `CVE-2026-45833`, sem
  versão de correção no snapshot. Qualquer outro advisory reprova o gate.
- [x] Registrar a justificativa limitada: uso `PersistentClient` local,
  `stdio` por padrão, sem `HttpClient` nem `trust_remote_code`; o risco não é
  descrito como ausência de vulnerabilidades.
- [x] Definir política de atualização: pins diretos sincronizados, auditoria a
  cada release/CI, vendor revisado manualmente e sem lock transitivo falso por
  plataforma; procedência/hash dos modelos externos é limitação declarada.

### P1 — correções implementadas

- [x] Tornar `scripts/mcp_smoke.py` não bloqueante em timeout, EOF e stderr;
  preservar diagnósticos e cobrir timeout/EOF/stderr com testes.
- [x] Alinhar o `serverInfo` vendorizado com `knowledge-rag==4.8.5` e fazer o
  smoke detectar drift entre servidor e pacote instalado.
- [x] Completar `SECURITY.md` com canal privado, escopo, versões, metas de
  resposta, modelo de ameaça, gates e procedimento para não expor corpus/
  tokens. O endpoint privado do GitHub permaneceu indisponível; o fallback
  privado está documentado.
- [x] Testar bearer HTTP dinamicamente: token ausente recusa antes do bind,
  token correto atravessa e token incorreto falha; perfil de exemplo mantém
  placeholder fora do Git.
- [x] Cobrir limites de clone, formatos opcionais, symlink quando permitido,
  autenticação, config, auditoria, pacote e regressões de rede; symlink é skip
  explícito em hosts Windows sem privilégio.

### P2 — investigações preventivas

- [x] Fechar DNS rebinding/TOCTOU em URLs: validar e conectar aos IPs aprovados
  com Host/SNI original; redirects são revalidados a cada hop.
- [x] Endurecer clone Git: somente HTTPS remoto, redirects HTTP desativados,
  `protocol.file.allow=never`, sem tags/submódulos/prompts, blob filter, DNS
  fixado por `http.curloptResolve` e limite pós-clone de 500 MiB.
- [x] Documentar procedência, cache, integridade não fixada e confiança dos
  modelos RAG externos em `SECURITY.md` e `docs/DEPENDENCIES.md`.
- [x] Registrar o processo de atualização da cópia vendorizada: revisar versão,
  diff, `serverInfo`, testes de segurança, suíte raiz, smoke, reindex e audit.

## Fase 5 — gates finais locais

- [x] `scripts/bootstrap.py --dev --rag`: passou no Windows com JSON `ok=true`.
- [x] `python -m pytest -q`: **107 passed, 2 skipped**; os skips são apenas
  symlink indisponível no Windows.
- [x] Suíte de segurança do vendor: **142 passed, 7 skipped, 5 xfailed**;
  apenas o warning de depreciação do telemetry do upstream foi observado.
- [x] Ruff em `docops tests scripts` e vendor de segurança: **All checks passed**.
- [x] `compileall`, `pip check` e `git diff --check`: passaram; pip reportou
  nenhum requisito quebrado.
- [x] `python -m docops doctor --json`: passou com RAG disponível e `stdio`.
- [x] `python -m docops config-audit config.yaml --json`: passou; o perfil
  `config/network.example.yaml` foi rejeitado como esperado por token
  placeholder.
- [x] Auditoria de release `--tracked-only`: passou; clone limpo copiado fora
  do checkout também passou sem findings.
- [x] Wheel `consulta_documentacao-1.0.0-py3-none-any.whl`: construído,
  instalado em alvo isolado e smoke de import passou.
- [x] Repetir `run → validate → evaluate`, smoke MCP, golden real e concorrência
  RAG após as correções: todos passaram com os resultados acima.

## Fase 6 — publicação pública e prova remota

- [ ] Criar a tag imutável `v1.0.0` somente no commit final validado; aceitar
  apenas quando `git show`, `git ls-remote --tags` e a release apontarem para o
  mesmo SHA.
- [ ] Publicar a release GitHub `v1.0.0` com notas de changelog e link para os
  gates; confirmar página/API acessíveis anonimamente.
- [ ] Fazer push do commit final e da tag para `origin`; confirmar branch,
  tag, release, settings de segurança e ausência de artefatos proibidos.
- [ ] Aguardar os workflows públicos do commit final: CI completo (9 jobs
  rápidos, 3 clones limpos e wheel), integração RAG e reindexação manual;
  registrar IDs, SHA, status e URLs aqui.

## Revisão de segurança

- [x] Nenhum segredo, token, corpus adquirido, índice, cache, ambiente virtual
  ou artefato gerado está listado por `git ls-files`.
- [x] Secret scanning, push protection, Dependabot alerts/security updates e
  workflow de auditoria estão ativos/documentados.
- [x] O residual Chroma está classificado e não bloqueia silenciosamente novas
  vulnerabilidades; revisar upstream antes de ampliar transporte ou escopo.
- [x] Revisão manual ainda requerida para licença de qualquer corpus futuro,
  firewall/TLS ao usar HTTP/SSE, rotação de token e integridade dos modelos.

## Veredito e registro final

Os gates locais e as decisões de suporte estão concluídos. O checklist só pode
ser marcado como totalmente concluído depois de a tag, a release, o push e os
workflows públicos serem observados e registrados nos quatro itens da Fase 6.
