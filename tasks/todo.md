# Registro de autoanálise e especificação pós-1.0

## Execução de preparação para commit/push — 2026-09-04

### Plano executável

- [x] Confirmar antes de qualquer alteração: cwd, branch, remote, `HEAD`,
  `origin/main`, working tree e arquivos ignorados; preservar todas as mudanças
  recebidas do usuário.
- [x] Ler integralmente instruções, lições, documentação normativa, tickets
  19–29, workflows, schemas e superfícies públicas relacionadas.
- [x] Revalidar o baseline atual sem confiar em resultados históricos: versão,
  metadata, lista distribuível, suíte, Ruff, formato, contratos, support matrix,
  public seams, release audit e `git diff --check`.
- [x] Auditar os tickets 19–29 por dependência técnica e confirmar gaps reais
  em promoção/recovery, identidade do candidate, supply chain/CVEs, suporte,
  workflows/community e observabilidade/stress.
- [x] Para cada gap local confirmado, executar TDD estrito no seam público:
  teste focado RED, GREEN mínimo de causa-raiz, classe relacionada e regressão.
- [x] Reexecutar os gates locais completos: bootstrap/doctor, pytest, Ruff,
  compileall, contratos, matriz, public seams, clean clone, wheels core/RAG,
  `pip check`, raw `pip-audit`, wrapper strict, supply chain, auditorias,
  vendor security/chaos, MCP/Golden/fixture, stress e metadata/workflows.
- [x] Gerar, depois do commit, um candidate novo em `artifacts/` e verificar lista/digest/identidade,
  auditoria, supply chain, re-medição da fonte e modo release fail-closed.
- [x] Atualizar docs, tickets, changelog, auditoria, este registro e lessons com
  apenas evidência observada nesta execução; revisar elegância e diff final.
- [x] Confirmar working tree pronto, criar os commits corretivos necessários e
  fazer push para `origin/main`, conforme autorização explícita posterior do
  usuário. Tag, GitHub Release e publicação continuam fora do escopo.

### Classificação de pendências e evidência

**Pendências locais implementáveis**

- [x] Corrigir somente gaps reproduzidos por testes/gates atuais, sem reabrir
  conclusões históricas por suposição.
- [x] Eliminar warning inesperado, workaround frágil, drift documental ou gate
  local vermelho encontrado durante a revalidação.

**Gates que exigem ambiente externo**

- [ ] CI remoto no SHA exato do candidate, incluindo Ubuntu/Windows/macOS e
  Python 3.11–3.13; não concluir localmente sem URL/artefato verificável.
- [ ] Estado autenticado de branch protection, required reviewers, secret
  scanning, push protection, Dependabot e permissões de release.

**Decisões do mantenedor humano**

- [ ] Registrar `accept`, `mitigate`, `upgrade` ou `remove` para o residual
  Chroma; manter release fail-closed enquanto a decisão estiver pendente.
- [x] Commit e push foram autorizados explicitamente pelo usuário em 2026-09-04.
- [ ] Autorizar separadamente tag, GitHub Release e publicação; nenhuma dessas
  ações está autorizada nesta execução.

**Evidência já confirmada nesta execução**

- [x] Repositório correto em `main`, remote
  `https://github.com/VIDORETTO/agent-knowledge-kit`, com
  `HEAD == origin/main == 0c766d2d7144a8861efe132fbc4c62498a0cfeb6`.
- [x] Working tree recebido contém mudanças rastreadas e novos arquivos; dados,
  corpus, caches, ambientes e estado RAG aparecem apenas como ignorados.
- [x] Suíte completa final: `227 passed, 2 skipped in 431.95s`; ambos os
  skips são a capacidade de symlink indisponível neste host Windows.
- [x] A race real que interrompia a suíte foi reproduzida: no Windows,
  `os.kill(pid, 0)` usado por um reader enviava um evento de console ao writer.
  A correção usa `OpenProcess`/`GetExitCodeProcess`; o teste focado passou e a
  classe lifecycle/reliability/recovery fechou com `27 passed`.
- [x] Raw `pip-audit` saiu 1 para quatro CVEs de `chromadb==1.5.9`; wrapper
  strict saiu 0 com residual=4/unresolved=0 e evidência crua preservada.
- [x] Wheels core/RAG, supply-chain, auditorias tracked/candidate, Golden/MCP e
  três execuções do stress concorrente passaram no estado implementado.
- [x] O clean clone final criou venv próprio com core+formats+dev, passou doctor,
  auditoria de release e a suíte inteira: `227 passed, 2 skipped in 184.77s`.
- [x] O gate de supply chain agora declara perfil `core` ou `rag`: somente a
  ausência de `knowledge-rag` é opcional no core; qualquer outra ausência ou
  qualquer versão divergente reprova, e o perfil RAG exige a raiz completa.

**Evidência ainda ausente ou externa**

- [x] Candidate RAG local reconstruído a partir do commit de código enviado,
  com snapshot externo de modelo e re-medição da fonte; o release continua
  fail-closed sem evidência remota/decisão humana.
- [ ] CI remoto do mesmo SHA/digest, settings autenticadas e decisão humana
  Chroma. O commit/ref remoto será criado nesta execução; os demais dependem do
  GitHub e do mantenedor.

### Registro de verificação

- [x] TDD red → green → verificação registrado para cada mudança nova.
- [x] Revisão final de privacidade, arquivos proibidos, status e pendências antes
  do commit/push.

## Follow-up pós-CI do primeiro push — 2026-09-04

- [x] Confirmar o run `33891442751` no SHA publicado e separar o caminho feliz
  do wheel RAG do bloqueio humano do modo release.
- [x] Confirmar que a falha dos testes de candidate também existia no CI do
  commit-base `7916083`, portanto não foi causada pelo ajuste do cache.
- [x] Reproduzir em checkout Linux/WSL que `Path.resolve()` removia o launcher
  do venv POSIX e selecionava um Python sem `pip`.
- [x] Corrigir `scripts/prepare_candidate.py` para tornar o caminho absoluto
  sem resolver symlinks e atualizar changelog, handoff e lessons.
- [x] Reexecutar o teste de candidate e os gates locais disponíveis.
- [x] Confirmar no novo CI (`33897740714`) que quick, clean-clone e package
  passam no mesmo SHA; manter o release gate bloqueado enquanto a decisão
  Chroma estiver pendente.

## Fechamento do checkpoint apos o CI — 2026-09-04

- [x] Preservar os commits que chegaram ao remoto durante a execução e fazer
  rebase do handoff sobre o `origin/main` mais recente.
- [x] Executar a suíte completa no `.venv` com versões fixadas: `230 passed,
  2 skipped`; os skips são apenas os testes de symlink indisponível neste
  Windows.
- [x] Reexecutar os testes de candidate/identidade: `10 passed`, incluindo o
  fallback de venv criado com `--no-install` e sem `pip`.
- [x] Enviar o commit de código `6b850ad` para `origin/main` e confirmar
  `HEAD == origin/main`.
- [x] Confirmar o CI `33897740714`: os 13 jobs passaram, incluindo wheel RAG,
  clean clone nos três sistemas e toda a matriz quick.
- [x] Regenerar e verificar um candidate RAG local a partir do commit de código
  enviado; a identidade é local e não substitui a evidência remota de release.
- [ ] Revisar settings autenticadas do GitHub e decidir explicitamente os
  quatro CVEs residuais de `chromadb==1.5.9`; sem isso, não criar tag, release
  ou publicar.

### Evidência do diagnóstico adicional

- O job `wheel / Python 3.12` do run `33891442751` passou construção, smoke RAG,
  candidate, supply chain e re-medição; a etapa `--release` retornou
  `human_decision_pending` como esperado.
- Os jobs quick/clean-clone falharam nos testes de candidate porque o venv
  POSIX era canonicalizado para `/usr/bin/python3.12`, sem `pip`.

## Execução Goal Mode — revalidação e implementação — 2026-09-03

**Estado inicial revalidado:** `HEAD == origin/main == 0c766d2d7144a8861efe132fbc4c62498a0cfeb6`, working tree limpo, Python local 3.14.2 (tolerado), `171 passed, 2 skipped`, Ruff/format/contratos/matriz verdes. Os skips são exclusivamente a capacidade de criar symlink neste host Windows.

**Seams públicos aprovados:** raiz `docops`, CLI/JSON, pacote ativo/`inspect()`, repositório candidate/auditor, wheel instalado, fixtures externas/processos MCP e concorrência observável. Nenhum teste novo deve importar helpers privados, verificar call count ou ordem interna.

### Plano executável

- [x] 23 — fechar identidade candidate: digest/lista/SHA, modo release fail-closed, evidência CI transportável e invalidação após mutação.
- [x] 24 — migrar caracterizações relevantes para a raiz/CLI e isolar compatibilidade legada.
- [x] 25 — tornar promoção recuperável após interrupção entre transições, com `inspect()`/`cleanup()` seguros e limites de filesystem documentados.
- [x] 26 — tornar resolução/provenance verificáveis, separar raw `pip-audit` do wrapper e registrar decisão explícita para os quatro CVEs Chroma.
- [x] 27 — ligar claims a jobs/perfis executados e tornar clean clone/bootstrap acionável e reproduzível.
- [x] 28 — completar verificador local de metadata/assets/community e checklist humana de settings, sem mutações GitHub.
- [x] 29 — desambiguar métricas de chunks e fortalecer stress concorrente com carga mínima repetível, resíduos e warnings separados.
- [x] Executar red → green → gate proporcional em cada ticket, nessa ordem, atualizando ticket, spec, docs e changelog quando necessário.
- [x] Reexecutar os gates locais em clone limpo e wheel core/RAG; classificar honestamente skips, limitações ambientais e residual de CVEs.
- [ ] Encerrar a release somente após decisão humana Chroma, identidade remota/CI do mesmo SHA e settings autenticadas; não fazer commit, push, tag, release ou publicação nesta tarefa.

### Registro de verificação desta execução

- Baseline completo: `rtk python -m pytest -q` → `171 passed, 2 skipped`.
- Gates rápidos: `rtk python -m ruff check docops tests scripts`, `rtk python -m ruff format --check docops tests scripts`, `rtk python scripts/check_contracts.py --json` e `rtk python scripts/check_support_matrix.py --json` → PASS.
- Próximo red: teste público de identidade do candidate que exige referência verificável para modo release e detecta mutação pós-digest.
- SPEC-23 red → green: `tests/test_candidate_identity.py` começou falhando sem `identity` e sem `--source-root`; após `scripts/candidate_identity.py`, re-medição, CI identity e supply-chain binding, o alvo passou (`4 passed`).
- SPEC-23 revisão: o modo `--release` permanece fechado sem working tree limpo, ref remota verificada e evidência GitHub Actions. A publicação/CI remoto real depende de um commit posterior e continua proibida nesta execução.

## Auditoria real atual — plano documental — 2026-09-02

**Status:** auditoria concluída; documentos revisados; tickets 23–29
intencionalmente não implementados.

> Este é o plano vigente para a auditoria solicitada. As seções abaixo são
> registros históricos de auditorias e execuções anteriores; não substituem a
> revalidação atual do estado público, do `HEAD` e do working tree.

- [x] Ler `AGENTS.md`, `RTK.md`, `README.md`, `tasks/lessons.md`, documentação
  existente, issues locais e o estado do Git antes de concluir qualquer nota.
- [x] Comparar release/tag pública `v1.0.0`, `origin/main`/`HEAD` e working tree
  candidato 1.1.0, incluindo arquivos rastreados e não rastreados.
- [x] Revalidar os riscos solicitados: smoke sem RAG, `pip-audit` limpo,
  CVEs Chroma, acoplamento de módulos, claims de plataforma e publicação de
  corpus/índices/tokens.
- [x] Executar gates proporcionais de testes, lint, formato, contratos,
  dependências, release, clean clone, wheel, suporte e RAG/MCP real.
- [x] Aplicar o vocabulário de módulo/interface/seam do `codebase-design` à
  especificação e separar fatos, inferências e recomendações.
- [x] Aplicar a disciplina `tdd` ao plano: red observável, green mínimo,
  tracer bullets e testes somente nos seams públicos.
- [x] Criar a auditoria atual, revisar a especificação e o plano TDD, e criar
  tickets 23–29 ordenados por blocker, aceite e dependência.
- [x] Revalidar os documentos gerados e registrar o resultado final nesta
  seção.
- [x] Implementar tickets 23–29 — concluído posteriormente no ciclo Goal Mode
  de 2026-09-03; esta linha registra o histórico da auditoria, não uma pendência.

### Revisão da auditoria atual

As conclusões vigentes estão em
`docs/GITHUB-PUBLICATION-AUDIT-2026-09-02.md`. A nota geral é **6,2/10**;
“publicar hoje” é **3,0/10** porque o candidato 1.1.0 existe apenas no working
tree e ainda não tem CI público para o mesmo conteúdo; “produção estável” é
**5,3/10** devido ao residual de quatro CVEs do Chroma, locks sem hashes/transitivas,
recuperação pós-crash não provada e cobertura insuficiente do seam raiz.

Os tickets novos são 23–29 em
`.scratch/post-1-0-reliability/issues/`. Nenhuma implementação, alteração de
código, commit, push, tag, publicação ou release foi feita nesta auditoria.

## Auditoria real de prontidão GitHub — 2026-09-01

> Registro histórico. Os números e resultados abaixo pertencem à execução de
> 2026-09-01 e foram revalidados/contestados quando necessário pela auditoria
> atual; não são o estado vigente por si só.

- [x] Inventariar documentação, código e os estados `v1.0.0`, `HEAD/origin/main` e working tree.
- [x] Executar auditoria crítica pelos 13 setores solicitados, distinguindo fatos, inferências e recomendações.
- [x] Rodar gates proporcionais no ambiente atual e em ambientes limpos: testes, lint, contratos, dependências, release, suporte, clone, wheel e RAG/MCP quando disponível.
- [x] Registrar falhas de ambiente separadamente de defeitos do produto e riscos de reprodutibilidade.
- [x] Produzir relatório de auditoria com notas, blockers, comandos, resultados e evidências localizáveis.
- [x] Aplicar `to-spec` aos achados confirmados e revisar `docs/POST-1.0-IMPROVEMENT-SPEC.md`.
- [x] Aplicar `to-tickets` e revisar os tickets em `.scratch/post-1-0-reliability/issues/` por severidade e dependências.
- [x] Aplicar `tdd` para definir seams públicos, tracer bullets e ciclos red → green, sem implementar tickets.
- [x] Revalidar todos os documentos produzidos e registrar a revisão final nesta seção.

> Restrição desta auditoria: não implementar código e não fazer commit, push,
> tag ou release. Mudanças preexistentes devem ser preservadas.

### Revisão da auditoria real

Concluída sem implementar código. O baseline candidato **não está verde**:
`pytest` teve `1 failed, 153 passed, 2 skipped`; o clean clone preparado
reproduziu a mesma falha sem RAG; o wheel construiu e falhou no contrato de
metadata do adapter. Ruff lint, contratos, matriz e `git diff --check`
passaram; Ruff format reportou 54 arquivos fora do formato. A integração RAG
real passou por run indexado, validate, evaluate MCP e concorrência.

A auditoria de dependências passou após o pin documentado de pip, mantendo
quatro CVEs Chroma allowlisted como risco residual. O auditor de release
tracked retornou sucesso, mas um fixture Git adversarial confirmou falsos
negativos para dados privados aninhados; portanto esse resultado não autoriza
publicação. As notas e comandos estão em
`docs/GITHUB-PUBLICATION-AUDIT-2026-09-01.md`, a spec atual em
`docs/POST-1.0-IMPROVEMENT-SPEC.md`, o plano red → green em
`docs/POST-1.0-TDD-PLAN.md` e os novos tickets são 13–22.

> Objetivo: produzir uma crítica técnica e de produto baseada em evidências,
> uma especificação de melhoria e tickets TDD executáveis por GPT-5.6 Luna Max,
> sem implementar as mudanças nesta etapa.

- [x] Inventariar contratos, fluxos, módulos, documentação, testes, CI e
  dependências do estado atual.
- [x] Executar auditorias independentes de arquitetura, qualidade/segurança e
  experiência do operador/produto com revisores GPT-5.6 Sol High.
- [x] Verificar cada achado relevante no código, nos testes ou por comandos
  reproduzíveis; distinguir fatos, inferências e propostas.
- [x] Escolher os seams públicos de teste e a estratégia red-green por tracer
  bullet, preservando o contrato DOCOPS e a fronteira com o harness externo.
- [x] Publicar uma especificação completa e tickets locais em ordem de
  dependência, dimensionados para contextos frescos do Luna Max.
- [x] Executar os gates atuais para estabelecer o baseline, revisar a
  elegância do plano e registrar resultados, riscos e decisões nesta seção.

## Revisão da autoanálise

Registro histórico de 2026-08-30, anterior ao working tree atual. Naquele
baseline, a suíte permaneceu verde (`107 passed, 2 skipped`,
Ruff e auditoria de release aprovados). A análise confirmou como prioridades:
outcome terminal único, contratos executáveis, plan sem efeitos, apply
transacional, retomada verificável, lease de writer, readiness honesto e gates
de avaliação pelas rotas reais. A especificação está em
`docs/POST-1.0-IMPROVEMENT-SPEC.md`; 12 tickets locais estão em
`.scratch/post-1-0-reliability/issues/`. Esse resultado foi supersedido para o
candidato atual pela auditoria de 2026-09-01 acima.

---

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
  matriz pública do CI final verde `33320817617`. Não há alegação de bootstrap
  manual local nesses dois sistemas.

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

- [x] Criar a tag anotada e imutável `v1.0.0` somente no commit validado
  `e8083ade7f9533cb220b3cf3288ed3b54a6e79c9`; `git show` confirmou a tag e o
  commit, enquanto `git ls-remote --tags origin` confirmou o objeto anotado
  `bfc89d2e69e27fa75d90c2c4c2d33020dbc02d1f` e o peeled SHA esperado.
- [x] Publicar a release GitHub `v1.0.0` com notas e links para changelog,
  release, aceitação, segurança e evidências; a API reportou `isDraft=false`,
  `isPrerelease=false`, e a página pública retornou HTTP 200:
  https://github.com/VIDORETTO/agent-knowledge-kit/releases/tag/v1.0.0.
- [x] Fazer push do commit e da tag para `origin`; a tag/release apontam para o
  commit de produto validado `e8083ade7f9533cb220b3cf3288ed3b54a6e79c9`, e
  `origin/main` recebeu depois o commit documental `73e6aa2216e0f87d0b92eed1364569d69d239eaa`
  com esta evidência. A API pública confirmou `isPrivate=false`,
  `visibility=PUBLIC`, Dependabot alerts/security updates, secret scanning e
  push protection ativos; `git ls-files` não encontrou `.venv-rag/`, `data/`,
  `models_cache/`, `.rag_state.json` ou artefatos gerados.
- [x] Aguardar os workflows públicos do commit final e registrar a prova:
  CI completo `33320817617` (13 jobs verdes: 9 combinações rápidas, 3 clones
  limpos e wheel), integração RAG `33320989219` e docs-reindex
  `33320989436`; todos no SHA `e8083ade7f9533cb220b3cf3288ed3b54a6e79c9`, com
  status `success` e URLs públicas:
  https://github.com/VIDORETTO/agent-knowledge-kit/actions/runs/33320817617,
  https://github.com/VIDORETTO/agent-knowledge-kit/actions/runs/33320989219,
  https://github.com/VIDORETTO/agent-knowledge-kit/actions/runs/33320989436.

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

Os gates locais, as decisões de suporte, a tag, a release, o push e os
workflows públicos foram observados e registrados. O residual de Chroma e as
revisões manuais descritas acima continuam sendo limitações conhecidas, não
falhas silenciosas do gate.
# Execução tickets 13–22 — plano ativo

> Objetivo: implementar os gaps pós-1.0 sobre o working tree recebido,
> preservando os tickets 01–12 e sem commit, push, tag, publicação ou release.
> Cada ticket será executado verticalmente: red observável → green mínimo →
> gate proporcional → atualização deste plano e do ticket.

## Ordem de dependência e ciclos

- [x] 13 — Auditoria de candidato fail-closed: Git tracked/candidate, paths
  proibidos, binários, canários de token e relatório redigido.
- [x] 14 — Contrato MCP determinístico: runtime selecionado, drift, ausência,
  timeout/EOF/stderr e smoke real.
- [x] 16 — Interface Python raiz: request/options, plan/apply/inspect, contratos
  imutáveis/versionados e compatibilidade observável.
- [x] 15 — Tracer do wheel instalado: core e RAG sem fallback silencioso,
  metadata de adapter/backend/perfil/proveniência coerente.
- [x] 17 — Expandir primitives internas: ownership unidirecional sem imports
  privados do legado, mantendo todos os seams verdes.
- [x] 18 — Migrar e contrair pipeline legado: callers pela interface nova,
  revalidação por snapshot sem readquisição completa sob lease e remoção segura.
- [x] 19 — Promoção/resíduos: reader concorrente, falhas de promoção, inspect,
  retenção e limpeza segura, com garantia por filesystem.
- [x] 20 — Supply chain: locks por perfil/plataforma, hashes, SBOM, vendor/model
  provenance e allowlist Chroma fail-closed.
- [x] 21 — Suporte perfilado/runbook: matriz por capacidade, wrappers, skips
  obrigatórios, ordem em clean clone e checker de drift docs/workflows.
- [x] 22 — Readiness profissional versionado: identidade nova, bundle de
  candidato verificável, metadata/community e prova de digest único.

## Método de verificação

- [x] Registrar cada red com comando e falha antes da implementação.
- [x] Executar testes somente nos seams públicos já aprovados em
  `docs/POST-1.0-TDD-PLAN.md`; não testar helpers privados/call counts.
- [x] Rodar testes rápidos após cada slice e gates de ticket ao concluir cada
  dependência.
- [x] Rodar suíte sem RAG e com RAG, auditoria de candidato, contratos, lint e
  format como gates separados.
- [x] Reproduzir clean clone, wheel core/RAG, security/dependency/portability,
  e tracer real RAG/MCP sobre o mesmo bundle antes do readiness final.
- [x] Manter falha ambiental separada de defeito do produto e não declarar
  release-ready sem evidência executável.

## Registro de execução

- Baseline inicial: `pytest -q` = 1 failed, 153 passed, 2 skipped; falha em
  `test_public_smoke_cli_rejects_server_version_drift` porque o launcher
  encerra com EOF em vez de reportar drift.
- Cwd/projeto: `<workspace>`, branch `main`, origin
  `https://github.com/VIDORETTO/agent-knowledge-kit`.

# Execução SPEC-002 pós-1.0 — registro histórico

> Esta seção registra a execução anterior do SPEC-002. Para o estado vigente,
> consulte a auditoria de 2026-09-02 e a revisão documental no início deste
> arquivo.

> Atualizado em 2026-09-01 após a implementação dos 12 tickets. `[x]` significa
> implementação e evidência executada; a seção histórica acima foi preservada.

## Ordem e critérios de aceite

- [x] Baseline e seams públicos caracterizados; mudanças preexistentes preservadas.
- [x] 01 — contratos normativos executáveis, outcome terminal único e drift gate.
- [x] 02 — `plan` completo, imutável/sem efeitos, diff fiel e plano verificável.
- [x] 03 — invariantes observáveis de `create`, `update` e `run`.
- [x] 04 — staging no mesmo volume, validação completa e promoção transacional,
  incluindo restauração segura, falhas por fase e leitores concorrentes.
- [x] 05 — recibos atômicos verificáveis, invalidação seletiva e retomada segura.
- [x] 06 — lease local recuperável; um writer por pacote e readers preservados.
- [x] 07 — readiness monotônico com evidências de scaffold, skill, RAG e release.
- [x] 08 — avaliação por rota/adaptador, backend/proveniência e gate MCP real.
- [x] 09 — resolver providers explícitos sem descoberta silenciosa de rede.
- [x] 10 — contexto de runtime explícito e procedência verificável em checkout e
  wheel, incluindo detecção de drift.
- [x] 11 — eventos e diagnósticos limitados, redigidos e derivados de recibos reais.
- [x] 12 — matriz, CI, release gates e documentação alinhados.
- [x] Suíte completa e todos os gates locais/integrados abaixo executados com
  sucesso; os únicos skips são symlinks indisponíveis neste host Windows.

## Evidência por ticket

| Ticket | Teste/artefato proporcional | Resultado atual | Pendência explícita |
|---|---|---|---|
| 01 | `tests/test_post_contracts.py`; `scripts/check_contracts.py --json` | PASS; 9 contratos, sem findings | Nenhuma conhecida |
| 02 | `tests/test_post_lifecycle.py` — plan, imutabilidade, diff e stale plan | PASS | Nenhuma conhecida |
| 03 | `tests/test_post_lifecycle.py` — create/update/run e blockers | PASS | Nenhuma conhecida |
| 04 | lifecycle, promoção/restauração, staging seguro e concorrência | PASS | Nenhuma conhecida no escopo local |
| 05 | lifecycle/reliability — receipts, resume, truncamento/adulteração | PASS | Nenhuma conhecida |
| 06 | `tests/test_post_reliability.py`; teste de reindex concorrente | PASS | Nenhuma conhecida |
| 07 | contratos, package validator e readiness | PASS | Nenhuma conhecida |
| 08 | `tests/test_evaluator.py`; tracer MCP real e Golden fixture | PASS; Recall@5/MRR@5 1,0 | Nenhuma conhecida |
| 09 | `tests/test_source_resolver.py` — catálogo, providers e entradas legadas | PASS | Nenhuma conhecida |
| 10 | `tests/test_runtime.py`; `scripts/verify_wheel.py` com MCP; clean clone | PASS | Nenhuma conhecida |
| 11 | `tests/test_post_observability.py`, MCP, smoke e redaction | PASS | Nenhuma conhecida |
| 12 | `scripts/check_support_matrix.py`; workflows, docs e auditorias | PASS | Nenhuma conhecida |

## Gates executados

- `python -m pytest -q`: **154 passed, 2 skipped** em 17,63 s; os skips são
  criação de symlink indisponível neste host Windows.
- `python -m ruff check docops scripts tests`: **PASS**; `compileall` e
  `git diff --check`: **PASS**.
- `scripts/check_contracts.py --json`: **PASS**, 9 contratos e nenhum finding.
- `scripts/check_support_matrix.py --json`: **PASS**; Python 3.11–3.13
  suportado, 3.14 tolerado, Ubuntu/Windows/macOS declarados e gates coerentes.
- `scripts/audit_release.py --tracked-only --json`: **PASS**, 324 arquivos
  rastreados, nenhum finding.
- `scripts/audit_dependencies.py --requirements requirements.lock --local
  --strict`: **ok=true**; os quatro advisories residuais do Chroma 1.5.9 estão
  explicitamente classificados como permitidos apenas para `PersistentClient`
  local, sem HTTP/trust_remote_code.
- `python -m docops doctor --json`: **ok=true**; config, lock, skill e RAG
  disponíveis. O Python local é 3.14, tolerado pela matriz.
- `python -m docops config-audit config.yaml --json`: **ok=true**; transporte
  `stdio`, sem erros ou warnings.
- `scripts/verify_wheel.py`: **PASS**; wheel 1.0.0 construído e instalado em
  alvo isolado, com `run --index-rag` → `validate` → `evaluate --adapter mcp`;
  saída confirmou `adapter=mcp`, `rag=true` e proveniência `installed-package`.
- Clean clone: **PASS**, doctor, auditoria de release e suíte (**154 passed,
  2 skipped**) em árvore temporária sem estado local.
- Tracer público RAG: **PASS** — `run --index-rag` → `validate` →
  `evaluate --adapter mcp`, com `knowledge-rag` 4.8.5, perfil compact, 2 casos,
  Recall@5=1,0 e MRR@5=1,0; o pacote registrou aquisição, artifacts, index,
  state e validate.
- `scripts/mcp_smoke.py "background tasks"`: **PASS**; handshake, tools/list e
  busca real, com conteúdo, caminhos e stderr redigidos/omitidos.
- `scripts/test_reindex_concurrency.py --seconds 20`: **PASS**; nenhum erro,
  reindex encerrado e índice consistente.
- TDD do gate do wheel: o red inicial expôs drift do backend instalado
  (`serverInfo=4.6.0` versus metadata `4.8.5`); o green usa runtime pinned
  isolado e falha explicitamente se `DOCOPS_REQUIRE_WHEEL_RAG=1` não puder
  executar MCP real.
- Revisão crítica: compatibilidade de `run` e manifests legados preservada;
  symlink/path traversal, SSRF, tokens, corpus e diagnósticos cobertos;
  staging/backup evita sobrescrever dados do usuário; mudanças preexistentes e
  o updater legado foram preservados.

## Pendências e limites honestos

- [x] Nenhum commit, push, tag, publicação ou release foi executado nesta tarefa.

## Revisão Goal Mode — evidência final local — 2026-09-04

- [x] Implementação local dos tickets 23–29 concluída e revalidada contra os
  seams públicos; o checkout preserva o working tree sem commit/push/tag.
- [x] Suíte completa no estado final: `184 passed, 2 skipped`; os dois skips são
  exclusivamente a capacidade de criar symlink neste host Windows.
- [x] Clean clone atual: doctor, release audit e `184 passed, 2 skipped`, sem
  `.rag_state.json`, corpus adquirido ou outro estado local no clone.
- [x] Ruff lint/format, compileall, contratos, public-seams, support matrix,
  diff-check e release audit tracked/candidate: PASS.
- [x] Wheel core e RAG: PASS; o wheel RAG executou adapter MCP e registrou
  `knowledge-rag==4.8.5` como runtime instalado.
- [x] RAG/MCP real: estado local `164` arquivos e servidor `170` documentos /
  `3296` chunks; Golden FastAPI `Recall@5=1.0`, `MRR@5=0.9048`; fixture MCP
  `Recall@5=1.0`, `MRR@5=1.0`; stress com quatro readers/10s/40 buscas obteve
  `202` buscas, zero erros/warnings e estado final consistente.
- [x] Security/privacidade: vendor security/chaos PASS (`142 passed, 7 skipped,
  5 xfailed`); auditorias não imprimem corpus, tokens ou caminhos privados.
- [x] Dependências: `pip check` PASS; o wrapper strict PASS com allowlist
  estreita e provenance verificável. O raw `pip-audit` permanece explicitamente
  vermelho: a auditoria JSON preserva quatro advisories sem fix para
  `chromadb==1.5.9`, e a invocação direta por requirements no Python 3.14
  também terminou com falha de resolução de `python-docx`; nenhum resultado
  vermelho foi mascarado como auditoria limpa.
- [x] Candidate local final: `artifacts/candidate-goal-final7` passou a
  verificação normal e supply-chain independente; o manifest/identity do
  bundle registra o digest calculado, `source_commit` local e estado
  `working-tree-candidate`. `--release` falha fechadamente sem CI remoto e
  sem decisão humana. O digest não é repetido nesta fonte para evitar uma
  referência circular entre a documentação e a identidade do candidato.
- [ ] Release/publicação: ainda requer decisão humana sobre o residual Chroma,
  commit/ref remoto e CI do mesmo digest, além da revisão autenticada de
  settings GitHub. Esses gates não podem ser inventados nem executados sob a
  proibição explícita de commit/push/release desta tarefa.
- [x] O CI declara a matriz Python 3.11–3.13 e runners Ubuntu/Windows/macOS;
  a execução local desta rodada ocorreu no Windows com Python 3.14 tolerado.
- [x] A decisão sobre o residual de Chroma, licença de novos corpora e eventual
  transporte HTTP/SSE continua exigindo revisão operacional antes de qualquer
  publicação futura.

## Revisão histórica — tickets 13–22 (2026-09-03)

Esta seção é a evidência da execução anterior dos tickets 13–22; os números
históricos acima foram preservados. Ela não substitui a auditoria atual nem
significa que os tickets 23–29 foram implementados.

### TDD red → green

- [x] 13: os testes de candidate audit iniciaram sem seleção de conjunto
  candidato; o CLI agora audita exatamente tracked + novos arquivos aprovados,
  incluindo binários e canários estruturados, sem ecoar segredos.
- [x] 14: o baseline reproduziu EOF em vez de `server_version_drift`; o smoke
  agora seleciona o interpretador real e separa ausência, drift, timeout e EOF.
- [x] 15: o red do wheel mostrou `serverInfo=4.6.0` contra metadata 4.8.5; o
  tracer agora usa o runtime pinado e falha se RAG obrigatório cair em fallback.
- [x] 14/15 follow-up: o módulo MCP redirecionava a versão para stderr e o
  wheel via `selected_version=None`; o contrato agora lê `sys.__stdout__` sem
  contaminar o canal JSON-RPC.
- [x] 16: o seam raiz e o teste de imutabilidade falharam antes dos exports e
  snapshots; `docops` agora expõe tipos versionados e resultados profundamente
  imutáveis e serializáveis.
- [x] 17: callers ainda dependiam da engine/adapter legado; primitives e
  geração foram extraídos e o pipeline legado ficou somente como adapter fino.
- [x] 18: o teste de lease observou 9 requests, acima do limite 6; a
  revalidação agora usa snapshot/fingerprint sem readquirir o corpus sob lease.
- [x] 19: o reader separado observou a janela de rename e a suíte reproduziu
  `WinError 5`; o red revelou que `inspect()` lia a geração durante o lease.
  O green final faz o reader esperar o writer antes de abrir arquivos; retry e
  inspect estável fecham a garantia pública no Windows.
- [x] 20: o teste de bundle iniciou sem gerador; generator/verifier agora
  produzem e validam locks, hashes, SBOM, vendor/model provenance e allowlist.
- [x] 21: o checker de suporte iniciou sem CLI; matriz, workflows, wrappers,
  skips e ordem de gates agora são validados como contrato.
- [x] 21 follow-up: o wrapper POSIX inicialmente não importava o checkout e
  sobrescrevia o venv Windows; o bootstrap agora carrega a raiz antes da
  instalação e separa `.venv-posix`/`.venv-windows` por configuração nativa.
- [x] 21 follow-up: o clean clone inicialmente tentou copiar o symlink `lib64`
  do venv POSIX; os dois diretórios específicos agora são ignorados também
  pelo copiador, auditor e builder de candidato.
- [x] 22: o teste de candidato iniciou sem builder; o bundle 1.1.0 agora é
  digest-bound, verificável independentemente e explicitamente unpublished.

### Gates finais executados

- [x] `rtk python -m pytest -q` e o mesmo comando no `.venv` RAG: **171 passed,
  2 skipped**. Os skips são exclusivamente a capacidade de criar symlink neste
  host Windows.
- [x] `ruff check`, `ruff format --check`, `compileall`, `git diff --check`,
  `check_contracts.py --json`, `check_support_matrix.py --json` e auditoria
  tracked/candidate: **PASS**, sem findings.
- [x] Wheel core e RAG: **PASS**, versão 1.1.0, adapter memory/mcp conforme o
  perfil; o RAG instalado confirmou `knowledge-rag==4.8.5`.
- [x] Dependências: `pip check` limpo; auditoria estrita **ok=true**, com
  exatamente os quatro CVEs Chroma permitidos pelo threat model local
  `PersistentClient` e sem unresolved.
- [x] Smoke MCP real e ciclo RAG: handshake/tools/search **PASS**; run
  indexado, validate, evaluate MCP e reindex concorrente **PASS**, com
  Recall@5=1.0 e MRR@5=1.0.
- [x] Security vendor: **160 passed, 7 skipped, 5 xfailed**; warning apenas de
  depreciação externa do Chroma.
- [x] Clean clone: **171 passed, 2 skipped**; doctor, release audit e suíte
  passaram sem estado local.
- [x] Candidate final: `artifacts/candidate-1.1.0-final11`, manifest e
  verificação independente **PASS**, source commit
  `855038019abbbe37d027728ac1bf034f4af210fb`; o digest final é o valor
  emitido e verificado no `manifest.json` do bundle.
- [x] Portabilidade: bootstrap Python, PowerShell e execução POSIX **PASS**;
  `--no-install` não exige `ensurepip`. O bootstrap completo com instalação de
  dependências ainda requer `pip`/`python3-venv` no host Linux, enquanto os
  wrappers e a matriz CI permanecem cobertos.
- [x] Nenhum commit, push, tag, publish ou release foi executado. A assinatura,
  branch/release protections, licença de corpus e decisão sobre o residual
  Chroma continuam como revisão humana antes de qualquer publicação.

## Follow-up do CI Linux após o commit `7916083` — 2026-09-04

- [x] Reproduzir no Linux/Python 3.12 a falha do job wheel do run
  `33887455346` e capturar os erros completos de validação.
- [x] Manter o cache FastEmbed fora da árvore distribuível do pacote em todos
  os sistemas, com regressão automatizada.
- [x] Melhorar o diagnóstico do gate do wheel para preservar erros estruturados
  sem depender dos últimos 2.000 caracteres do stdout.
- [x] Executar testes focados, suíte/gates proporcionais e os smokes reais dos
  wheels no Windows; o wheel RAG foi executado com o runtime exigido.
- [x] Atualizar documentação/revisão com a evidência local final e preparar o
  commit/push corretivo desta execução. Não criar tag nem release.
- [ ] Confirmar no GitHub o novo CI do mesmo SHA depois do push; a execução
  remota e suas plataformas continuam evidência externa.

### Evidência final local deste follow-up

- `python -m pytest -q`: **228 passed, 2 skipped em 419,82s**; ambos os skips
  são a capacidade de criar symlink neste host Windows.
- Testes focados (`test_pipeline.py`, `test_rag_sync.py` e
  `test_verify_wheel.py`): **21 passed, 1 skipped**.
- Ruff lint/formato, contratos, matriz de suporte, workflows, public seams,
  `compileall` e `git diff --check`: **PASS**.
- Auditoria de release: **PASS**, 401 arquivos tracked e 403 arquivos no
  candidate set.
- `pip check` no `.venv` do projeto: **PASS**.
- `verify_wheel.py --core`: **PASS**, `adapter=memory`, `rag=false`.
- `verify_wheel.py --require-rag` no `.venv` do projeto: **PASS**,
  `adapter=mcp`, `rag=true`.
- A tentativa paralela dos wheels foi descartada por corrida nos diretórios
  `build/` compartilhados; a repetição sequencial passou. Os diretórios
  `build/` e `consulta_documentacao.egg-info/` foram removidos antes da
  repetição por serem artefatos gerados e ignorados.
