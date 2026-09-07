# Status de implementação — atualização contínua de conhecimento

Execução iniciada em 2026-09-04 no checkout `main`, sem publicação externa.
Este arquivo é o registro retomável exigido pelo objetivo. Os estados e
resultados abaixo são atualizados após cada ticket; “concluído” só significa
que o comportamento público, testes e checks pertinentes foram verificados.

## Resumo

- Objetivo: T01–T18.
- Política de segurança: indexação, automação, captura de conversas e
  publicação factual concorrente permanecem desativadas por padrão até os
  gates correspondentes.
- Integração real e avaliação de harness externo serão separadas de fixtures.

## Tickets

| Ticket | Estado | Dependências | Entrega/arquivos | Testes e limitações |
|---|---|---|---|---|
| T01 | concluído | nenhuma | Inventário SHA-256 do owner em `.docops/generated-artifacts.json`; guarda em `docops/generation.py`/`docops/operations.py`; testes públicos em `tests/test_continuous_knowledge.py` | RED funcional observado; gate proporcional `30 passed, 1 skipped` |
| T02 | concluído (evidência; aprovação no T08) | T01 | Revisões/evidências vinculadas a hashes | avaliação persistida e invalidada por mudança; pacote v1/incompleto permanece não publicável |
| T03 | concluído | T01, T02 | Camadas factual/conceitual independentes | factual-only preserva skill/router e mantém indexação opt-in |
| T04 | concluído (aprovação no T08) | T02, T03 | Candidata revisável sem promoção em `docops/candidates.py`; `apply`/`inspect`/`validate` integrados | `14 passed`; lint do slice PASS; fixtures/subprocesso local, sem MCP/harness externo |
| T05 | concluído | T02, T04 | Resultado MCP terminal/perfil verificável em `docops/rag_sync.py` e `docops/operations.py` | `45 passed`; Ruff PASS; MCP real sintético isolado PASS |
| T06 | concluído | T04 | `candidate-request`/`candidate-submit`; recibo, hashes, escopo, orçamento e importação somente em candidata | `5 passed`; contratos, Ruff lint/formato PASS; fixture sintética; harness externo não executado |
| T07 | concluído localmente em 2026-09-05 | T05, T06 | `evaluate` separa retrieval/rota/resposta; recibo externo e hashes exatos | `7 passed` focados; `49 passed` integrados; contratos/Ruff PASS; harness externo não executado |
| T08 | concluído em 2026-09-05 | T04, T07 | `candidate-approve`/`candidate-publish`; aprovação e publicação por hashes, base, política e avaliação; journal e validação pós-promoção | `5 passed` focados; contratos/Ruff/diff PASS; fixtures sintéticas; harness externo não executado |
| T09 | concluído em 2026-09-05 | T08 | Histórico editorial separado de resíduos; `candidate-rollback` transacional e `inspect().history` | `5 passed` focados; contratos/Ruff/formato/diff PASS; fixtures sintéticas |
| T10 | concluído em 2026-09-05 | T02, T03 | `source-register`/`source-reconcile`, registros por `source_id`, snapshots com escopo/completude e retirada explícita | `6 passed` focados; contratos, Ruff e diff-check verificados; fixtures sintéticas |
| T11 | concluído em 2026-09-05 | T10 | `event-submit`/`jobs`, fila SQLite local, deduplicação, debounce e projeção de arquivos | `5 passed` focados; contratos, Ruff/formato e diff-check PASS; fixtures sintéticas; worker/harness externo não executados |
| T12 | concluído em 2026-09-05 | T08, T11 | `work --once`, lease, recibo de efeito, retomada, retries limitados e autorização RAG persistida | `11 passed` focados; contratos/Ruff PASS; fixtures sintéticas; MCP/harness externo não executados |
| T13 | concluído em 2026-09-05 | T06, T10, T12 | `impact-assess`, cursor de impacto líquido, lote conceitual, backlog e revogações | `3 passed` focados; contratos/Ruff/diff PASS; fixtures sintéticas |
| T14 | concluído em 2026-09-05 | T08, T09 | `reader-session`/`reader-query`/`reader-session-revoke`; geração pinada e MCP read-only | `4 passed`; fixtures sintéticas; harness externo não executado |
| T15 | concluído em 2026-09-05 | T05, T09, T14 | `rag-snapshot`/`rag-reuse-plan`, diff por hash, fallback de rebuild e verificação de busca | `5 passed`; fixtures sintéticas; sem MCP/harness externo |
| T16 | concluído localmente em 2026-09-05 | T05, T07, T10 | Localizadores/citações por formato, transcrição externa, quarentena de qualidade e comparação de perfis | `5 passed` focados; contratos, Ruff/formato e diff-check no gate; fixtures sintéticas |
| T17 | concluído localmente em 2026-09-05 | T08, T10, T14 | Quarentena/admissão de conversas em `docops/learning.py`, CLI e pipeline | `3 passed` focados; contratos/Ruff/diff no gate; fixtures sintéticas |
| T18 | concluído localmente em 2026-09-05 | T07, T12, T17 | `feedback-submit`/`feedback-report`, investigação por recorrência, métricas redigidas e job sem autopublicação | `3 passed` focados; contratos/Ruff/formato PASS; fixtures sintéticas, sem MCP/harness externo |

## Registro detalhado por ticket

### T01

- Estado: concluído.
- Dependências confirmadas: nenhuma.
- Seam: `docops.plan/apply`, resultado público e arquivos da skill.
- Primeiro comportamento: uma skill externamente enriquecida não é
  sobrescrita quando a fonte muda; o resultado deve expor
  `skill_update_requires_review` e manter a geração ativa.
- RED: antes da guarda, o teste obrigatório observou `result.ok is True` após
  edição externa. GREEN: a guarda compara hashes da árvore `skill/` e
  `router/`, bloqueia divergência e registra baseline ausente como migração
  explícita. Verificação: `rtk pytest -q tests/test_continuous_knowledge.py
  tests/test_public_interface.py tests/test_public_seams.py tests/test_pipeline.py`
  — `30 passed, 1 skipped`.
- Arquivos alterados: `docops/generation.py`, `docops/operations.py`,
  `tests/test_continuous_knowledge.py`, este ticket e `tasks/todo.md`.
- Limitação/decisão: a guarda protege artefatos conceituais gerados (`skill/`
  e `router/`); adoção de pacotes legados continua desativada e requer fluxo
  explícito futuro. Nenhuma fila, LLM ou indexação nova foi introduzida.
- Rollback: bloquear a atualização antes de qualquer promoção; manter ativa.

### T02

- Estado: concluído para a infraestrutura de revisão/evidência; a decisão de
  aprovação/publicação continua deliberadamente no T08.
- Dependências confirmadas: T01.
- Seam: `docops.evaluate`, `docops.inspect`, `docops.validate` e os envelopes
  JSON de manifest/readiness.
- RED: antes da vinculação, uma avaliação continuava reportada como válida
  depois de uma alteração relevante no pacote.
- GREEN/refactor: `docops/revisions.py` centraliza hashes canônicos de corpus,
  índice, skill, router, policy e Golden; `evaluate`, `inspect` e
  `package_validator` persistem/comparam a revisão e a composição.
- Entrega: avaliações repetidas sem mudança mantêm `composition_hash` e
  revisões estáveis; timestamps/duração não participam da identidade; avaliação
  ausente, incompleta ou divergente não habilita readiness.
- Arquivos alterados: `docops/revisions.py`, `docops/readiness.py`,
  `docops/evaluator.py`, `docops/package_validator.py`,
  `docops/operations.py`, ambos os schemas e
  `tests/test_continuous_knowledge.py`.
- Testes: RED funcional observado; testes de invalidação e identidade estável
  passam; a compatibilidade de configuração operacional foi preservada ao
  excluir `config.yaml` da revisão de conteúdo do índice.
- Limitação/decisão: aprovação/autorização ainda não existe neste ticket e será
  implementada com base exata no T08; nenhuma autopublicação foi habilitada.
- Rollback: ignorar evidências de revisão novas e manter readiness fechado; os
  manifestos v1 continuam legíveis.

### T03

- Estado: concluído.
- Dependências confirmadas: T01 e T02.
- Seam: `OperationOptions.layers`, `docops.plan/apply/inspect` e os artefatos
  do pacote.
- RED: uma atualização factual ainda acionava `skill_update_requires_review`
  e não tinha como preservar a camada conceitual.
- GREEN/refactor: `docops/api_types.py`, CLI e `docops/operations.py` aceitam
  camadas explícitas; modo factual copia byte a byte `skill/`, `router/` e a
  evidência conceitual, reconstrói somente RAG e registra
  `conceptual_lag.status=pending_review`, `coverage=unknown`.
- Entrega: remoção de fonte invalida apenas o suporte factual dependente sem
  declarar a skill sincronizada; atualização factual sem `--index-rag`
  permanece `corpus-ready` e não inicia MCP.
- Arquivos alterados: `docops/api_types.py`, `docops/__main__.py`,
  `docops/operations.py`, `tests/test_continuous_knowledge.py` e o registro
  de execução.
- Testes: RED funcional observado; preservação, remoção factual e caminho sem
  indexação passam. O gate focado encontrou e corrigiu uma regressão de revisão
  causada por `config.yaml`; o teste de preservação de configuração voltou a
  passar.
- Limitação/decisão: só a seleção factual é segura para preservar artefatos;
  qualquer atualização conceitual continua sujeita à guarda de propriedade do
  T01. A defasagem conceitual é explícita e não vira publicação automática.
- Rollback: reverter a atualização factual para a geração anterior, sem
  regenerar a skill como fallback.

### T04

- Estado: concluído localmente; aprovação e promoção continuam bloqueadas até
  o T08.
- Dependências confirmadas: T02 e T03.
- Seam: `OperationOptions.publication_policy`, `apply`, `inspect` e CLI
  `validate`.
- RED: a política candidata ainda promovia a atualização e não deixava uma
  candidata revisável.
- GREEN/refactor: `docops/candidates.py` cria identificadores opacos,
  diretório irmão controlado e recibo `.docops/candidate.json` com
  `base_release_id`, `base_composition_hash`, `plan_hash` e revisões. O
  caminho candidato é validado antes de ser exposto; `inspect` marca
  estruturas inválidas/arbitrárias como rejeitadas e `validate` permanece
  fail-closed.
- Entrega: preparação candidata não altera `manifest.json`, RAG ou demais
  bytes da geração ativa; staging interrompido é consumido na próxima
  execução compatível. O envelope de outcome expõe `candidate_id` e
  `candidate_locator`.
- Arquivos alterados: `docops/api_types.py`, `docops/__main__.py`,
  `docops/operations.py`, `docops/candidates.py`, ambos os
  `outcome.schema.json`, `tests/test_continuous_knowledge.py` e o ticket.
- RED/GREEN/verificação: `rtk pytest -q tests/test_continuous_knowledge.py`
  — **14 passed**; `ruff check` no slice — **PASS**.
- Limitação/decisão: retenção é local e explícita; não há aprovação humana,
  publicação, deploy, MCP real ou hand-off externo neste ticket. O T08 deve
  verificar novamente base, composição e revisões antes de promover.
- Rollback: remover somente o candidato identificado ou mantê-lo rejeitado;
  a geração ativa permanece intacta.

### T05

- Estado: concluído localmente; nenhuma publicação ou operação no corpus ativo.
- Dependências confirmadas: T02 e T04.
- Seam: `RagSynchronizer.sync`, `docops.apply` com `--index-rag`, relatório
  `rag/index.json` e processo MCP externo.
- RED/GREEN: o primeiro RED demonstrou que `last_error` terminal era aceito
  como sucesso. O GREEN exige envelopes JSON válidos, operação esperada,
  conclusão sem erro, stats inteiros compatíveis com os documentos, smoke com
  resultado conhecido e timeout explícito. `already_running` só é aceito
  quando o backend confirma a operação solicitada.
- Entrega: o índice persiste fingerprint configuracional, perfil,
  configuração efetiva, modelo/dimensões do backend, versão e modo de
  reindex. Alteração de embedding força nuclear/full rebuild; falha em
  candidata não toca a geração ativa nem cria candidata.
- Arquivos alterados: `docops/rag_sync.py`, `docops/operations.py`,
  `tests/test_rag_sync.py`, `tests/test_continuous_knowledge.py`,
  `tests/test_post_lifecycle.py` e este ticket.
- Verificação: `46 passed` nos testes focados; Ruff lint/formato PASS; MCP real
  `knowledge-rag==4.8.5` PASS sobre diretório temporário sintético, com busca
  não vazia e configuração efetiva observada.
- Limitações/decisões: o harness externo ainda não foi executado; a integração
  real permanece opt-in e foi executada somente no temporário. O relatório
  redige a consulta e diagnósticos sem persistir conteúdo sensível.
- Rollback: manter a geração ativa e descartar a candidata/staging que falhou;
  para mudança de embedding, repetir a operação explícita com
  `full_rebuild=true`.

### T06

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T04.
- Seam: CLI `candidate-request` e `candidate-submit`, recibos JSON e
  `inspect`/readiness da candidata.
- RED/GREEN/refactor: o RED inicial observou a ausência do comando; o GREEN
  exporta tarefa com base/snapshot/diff/política/orçamento e importa somente
  `skill/`/`router/` após validar hashes, contrato, caminho, orçamento,
  ferramenta/versão e ausência de campos sensíveis. O refactor isolou a
  validação e faz commit atômico dentro da candidata.
- Critérios: ausência de harness fica em `awaiting_enrichment`; recibo interno
  registra ferramenta, versão, entradas, saídas e proveniência redigida;
  traversal, symlink, Golden e base divergente são recusados; submissão válida
  retorna `published=false` e mantém `manifest.json` ativo byte a byte.
- Arquivos alterados: `docops/candidates.py`, `docops/harness.py`,
  `docops/readiness.py`, `docops/__main__.py`, os dois schemas de enrichment,
  `scripts/check_contracts.py`, `tests/test_enrichment.py` e documentação.
- Testes: `5 passed`; contratos, Ruff lint e formato do slice passaram. A
  integração de harness externo não foi executada; a prova usa apenas diretório
  temporário e conteúdo sintético.
- Limitação/decisão: não há modelo interno, captura de conversa, publicação ou
  aprovação humana implícita. A candidata exige o gate T08 antes de ativar.
- Rollback: rejeitar o recibo ou remover a candidata; não restaurar conteúdo
  para a ativa por esta operação.

### T07

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T05 e T06.
- Seam: CLI `evaluate`, Golden revisado e recibo externo
  `evaluation-receipt`.
- RED: o primeiro teste público rejeitou a ausência do novo seam de recibo
  porque `evaluate_package` ainda não aceitava `response_receipt`.
- GREEN/refactor: `docops/evaluator.py` valida geração, candidata, hashes de
  composição e Golden, calcula `response_fidelity` e `citation_coverage`,
  marca denominador zero como `not_applicable` e reprova afirmações críticas
  sem suporte. A configuração registra adapter, backend, thresholds e modo;
  o recibo é persistido como evidência com hash. O adapter lexical continua
  apenas diagnóstico.
- Arquivos alterados: `docops/evaluator.py`, `docops/__main__.py`,
  `docops/contracts.py`, os dois schemas de `evaluation-receipt` e Golden,
  `scripts/check_contracts.py`, `tests/test_candidate_evaluation.py`,
  `docs/SCHEMAS.md`, `docs/USE.md`, este ticket e `tasks/todo.md`.
- Verificação: `rtk pytest -q tests/test_candidate_evaluation.py` — **7
  passed**; integração de evaluator/CLI/contratos/contínuo — **49 passed**;
  Ruff lint/formato, `scripts/check_contracts.py --json` e
  `git diff --check` — **PASS**.
- Integração e limites: fixtures sintéticas em diretórios temporários; nenhum
  harness externo, conversa real, corpus real ou índice ativo. A evidência MCP
  real permanece a do T05, isolada em temporário.
- Rollback: recibo ausente, inválido, stale ou reprovado não habilita
  publicação; manter a geração ativa e descartar ou quarentenar a candidata.

### T08

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T04 e T07.
- Arquivos: `docops/operations.py`, `docops/__main__.py`, `docops/__init__.py`,
  `schemas/{approval,publication}.schema.json`, cópias em `docops/schemas/`,
  `scripts/check_contracts.py`, testes e documentação.
- Entrega: aprovação explícita vinculada a ator/escopo, base, composição,
  política, Golden e avaliação; publicação transacional com journal, validação
  pós-promoção e preservação da ativa em falhas.
- RED observado: conteúdo com `approved=true` não autorizou publicação e
  retornou `approval_missing`.
- Testes: cinco cenários públicos cobrindo publicação feliz, evidência alterada,
  base avançada e papéis factual/conceitual; contratos e diff-check passaram.
- Limites: autoridade é local e explícita, não autenticação remota; nenhum
  harness externo, corpus real, deploy ou publicação foi executado.

### T09

- Estado: concluído localmente em 2026-09-05.
- Dependência confirmada: T08.
- RED observado: depois de publicar duas gerações, o seam
  `candidate-rollback` não existia; o teste público falhou no comando ausente.
- GREEN/refactor: `candidate-publish` copia a geração ativa anterior para
  `.<package>.history/<release_id>/` antes de remover o backup transacional.
  `candidate-rollback` valida a cópia, grava `rollback.json` e promove com
  journal, restauração segura e validação final. `inspect()` expõe histórico
  editorial separado de `staging`, `backups` e `attempts`; `cleanup()` não
  toca nessa árvore.
- Guardas: revogação retorna `source_revoked`; incompatibilidade declarada de
  índice retorna `index_incompatible`; quota insuficiente retorna
  `history_quota_exceeded` antes de mover a ativa. Conflito, symlink, hash ou
  manifesto divergente falham fechadamente.
- Arquivos: `docops/operations.py`, `docops/__main__.py`,
  `docops/__init__.py`, schemas `history`/`rollback` nas duas raízes,
  `scripts/check_contracts.py`, `tests/test_history_rollback.py` e docs.
- Verificação: `rtk pytest -q tests/test_history_rollback.py` — **5 passed**;
  contratos, Ruff lint/formato e `git diff --check` — **PASS**.
- Limitações: fixtures são sintéticas em temporários; nenhum corpus real,
  MCP/harness externo, deploy ou publicação foi executado. A fixação de sessão
  por `release_id` será consolidada no T14; o armazenamento editorial já é
  protegido contra limpeza operacional.
- Rollback: se retenção ou restauração falhar, a ativa permanece intacta e
  qualquer journal/staging pode ser recuperado pela rotina existente.

### T10

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T02 e T03.
- RED observado: o primeiro teste público falhou porque os comandos
  `source-register`/registro por `source_id` ainda não existiam.
- GREEN/refactor: `docops/source_policy.py` separa registro desejado,
  observação de aquisição e retirada explícita. O registro vive em
  `.docops/source-registry.json`; entradas com canonical físico igual mantêm
  proveniência, direitos e responsáveis distintos. `source-reconcile` valida
  escopo, completude e versão antes de persistir a observação.
- Guardas: snapshots parciais/falhos/limitados não removem fontes;
  `version_policy=pinned` rejeita avanço automático; snapshot completo vazio
  exige `--withdraw`; `docops.plan` não anuncia `removed` quando a aquisição
  falha ou fica sem documentos aceitos.
- Arquivos: `docops/source_policy.py`, `docops/operations.py`,
  `docops/__main__.py`, `docops/__init__.py`, schemas
  `source-registration`/`acquisition-snapshot` nas duas raízes,
  `scripts/check_contracts.py`, `tests/test_source_registry.py` e docs.
- Verificação: `rtk pytest -q tests/test_source_registry.py` — **6 passed**;
  `rtk python scripts/check_contracts.py --json` — **PASS**.
- Limitações: o registro é local e determinístico; aquisição web/repositório
  real, corpus real, MCP/harness externo, deploy e publicação continuam fora do
  escopo. A reconciliação de eventos duráveis será consolidada no T11.
- Rollback: restaurar `.docops/source-registry.json` e reconciliar um snapshot
  completo sob revisão; a geração ativa não é alterada pelo registro.

### T11

- Estado: concluído em 2026-09-05.
- Dependência confirmada: T10.
- RED observado: o primeiro teste público falhou porque `event-submit` e
  `jobs` ainda não existiam.
- GREEN/refactor: `docops/coordination.py` persiste eventos em SQLite com WAL,
  valida envelopes, deduplica por `event_id`/hash, coalesce por chave de
  pacote/tipo/revisão/política e calcula
  `min(last_event + 60s, first_event + 5min)`. A CLI retorna a projeção pública
  dos jobs com `ready`, `event_count`, `completed_files` e `deferred_files`.
- Guardas: payload divergente para o mesmo `event_id` falha como
  `event_id_conflict`; arquivos instáveis são adiados sem bloquear arquivos
  concluídos; aquisição ignora `.docops` e o Git ignora `.docops/*.sqlite*`.
- Arquivos: `docops/coordination.py`, `docops/__main__.py`,
  `docops/__init__.py`, schemas `event`/`job` nas duas raízes,
  `scripts/check_contracts.py`, `.gitignore`, `tests/test_coordination.py` e
  documentação.
- Verificação: `rtk pytest -q tests\test_coordination.py` — **5 passed**;
  `rtk python scripts\check_contracts.py --json`, Ruff lint/formato e
  `rtk git diff --check` — **PASS**.
- Limitações: a fila é local e determinística; lease, retries, retomada e
  execução do worker são T12. Nenhuma fila de produção, corpus real,
  conversa real ou harness externo foi usado.
- Rollback: suspender qualquer consumidor futuro, preservar a fila e
  reconciliar fontes; não apagar SQLite como recuperação automática.

### T12

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T08 e T11.
- Seam: CLI `work --once`, `jobs` e `event-submit`; o worker recebe um job
  durável e devolve uma projeção JSON sem expor tabelas SQLite.
- RED observado: o primeiro teste público falhou porque `work --once` ainda
  não existia.
- GREEN/refactor: `docops/coordination.py` separa claim de lease, execução e
  reconhecimento. O claim é transacional; a execução reutiliza
  `operations.plan/apply`; o recibo `job-receipt` guarda hash da solicitação,
  revisão, efeito e referência; uma retomada após lease expirado reconcilia o
  recibo antes de repetir o efeito.
- Guardas: `index_rag` sem `rag-authorization` persistida fica `blocked` antes
  da aquisição/indexação; `publication_policy=direct` fica bloqueada para o
  worker; `writer_busy` faz retry limitado e depois `blocked`; eventos
  recebidos enquanto um job está `running` formam um job posterior.
- Arquivos: `docops/coordination.py`, `docops/authorization.py`,
  `docops/__main__.py`, `docops/__init__.py`, schemas
  `rag-authorization`/`job-receipt` nas duas raízes,
  `scripts/check_contracts.py`, `tests/test_worker.py` e documentação.
- Verificação: `rtk pytest -q tests\test_coordination.py tests\test_worker.py`
  — **11 passed**; `rtk python scripts\check_contracts.py --json`, Ruff
  lint/formato e `rtk git diff --check` — **PASS**.
- Limitações: fixtures sintéticas em temporários, com subprocesso de lock
  somente do próprio teste. Nenhum corpus real, conversa, harness externo,
  deploy ou reindexação do índice ativo foi usado; a integração MCP real
  continua separada na evidência do T05.
- Rollback: pausar o agendador, preservar fila/recibos e operar manualmente;
  reexecução é segura porque o recibo por job/revisão impede duplicação do
  efeito.

### T13

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T06, T10 e T12.
- Seam: CLI pública `impact-assess` e o envelope `conceptual-impact`; o teste
  observa contador, lote, backlog e revogações sem acessar estado interno.
- RED observado: os três testes iniciaram falhando porque o subcomando
  `impact-assess` ainda não existia.
- GREEN/refactor: `docops/triggers.py` persiste cursor por identidade/revisão,
  ignora reindex sem diff, remove reversões à base, exclui impacto factual,
  marca impacto incerto como `review_required` e limita lotes por orçamento de
  24 horas. Um `causation_id` é mantido no lote; a revogação registra suporte
  inválido independentemente do orçamento.
- Guardas: `publication_allowed` permanece sempre falso; `candidate_requested`
  é somente uma projeção para a coordenação T12. Backlog continua visível
  quando o limite é atingido.
- Arquivos: `docops/triggers.py`, `docops/__main__.py`, `docops/__init__.py`,
  `docops/contracts.py`, schemas `conceptual-impact` nas duas raízes,
  `scripts/check_contracts.py`, `tests/test_conceptual_triggers.py` e
  documentação.
- Verificação: `rtk pytest -q tests\test_conceptual_triggers.py` — **3 passed**;
  contratos, Ruff lint/formato e `rtk git diff --check` — **PASS**.
- Limitações: fixtures sintéticas e diretórios temporários; o classificador não
  consulta um modelo nem um corpus real, e nenhum harness externo ou MCP de
  produção foi executado.
- Rollback: desabilitar o consumidor do gatilho preservando
  `.docops/conceptual-impact.json`, backlog e tombstones de revogação; não
  apagar o estado como forma de desfazer invalidações.

### T14

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T08 e T09.
- Seam: CLI pública `reader-session`, `reader-query` e
  `reader-session-revoke`; os testes observam a geração retornada, resultados,
  recusas e revogações sem acessar tabelas internas.
- RED observado: quatro testes falharam porque os subcomandos ainda não
  existiam.
- GREEN/refactor: sessões registram `release_id` e `composition_hash`; somente
  `search_knowledge` e `get_document` são aceitos. Cache é vinculado à sessão
  e à geração. Estado runtime fica em `.<package>.readers/`, fora da árvore
  ativa e ignorado pelo Git, para sobreviver à substituição coordenada.
- Harness MCP: `harness.json` declara `mode=read_only`, capacidades explícitas,
  nenhuma capacidade de escrita e `concurrent_publication_allowed=false`;
  manifesto incompatível falha fechado.
- Arquivos: `docops/reader_sessions.py`, `docops/harness.py`,
  `docops/__main__.py`, `docops/__init__.py`, `docops/contracts.py`, os schemas
  `reader-session`/`reader-query`, `tests/test_reader_sessions.py`, `.gitignore`
  e documentação.
- Verificação: `rtk pytest -q tests\test_reader_sessions.py` — **4 passed**;
  contratos, Ruff lint/formato e `rtk git diff --check` serão revalidados no
  gate conjunto antes do fechamento final.
- Limitações: fixture `memory` sintética; o adapter MCP deste ticket valida o
  contrato do harness, sem conectar servidor externo. Nenhum corpus real,
  reindexação, publicação ou deploy foi executado.
- Rollback: desabilitar criação/aceitação de novas sessões e operar publicação
  coordenada manualmente, preservando histórico e tombstones.

### T15

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T05, T09 e T14.
- Seam: CLI pública `rag-snapshot`; o relatório devolve o snapshot relocável,
  o plano de reuso e, opcionalmente, uma busca de verificação pelo adapter
  escolhido.
- RED observado: os cinco testes públicos falharam porque o subcomando ainda
  não existia.
- GREEN/refactor: `docops/rag_sync.py` registra hashes SHA-256, tamanho e mtime
  apenas como diagnóstico para cada documento, além da identidade do embedding,
  do backend e do inventário lógico de `rag/index.json`/`rag/data`. O plano usa
  hashes de conteúdo e só escolhe `incremental` quando o snapshot, embedding e
  backend são compatíveis; caso contrário declara `full_rebuild`. Falhas na
  leitura do snapshot terminam com `active_preserved=true`.
- Arquivos: `docops/rag_sync.py`, `docops/__main__.py`, `docops/contracts.py`,
  `schemas/{rag-snapshot,rag-reuse-plan}.schema.json` e cópias em
  `docops/schemas/`, `scripts/check_contracts.py`, `tests/test_rag_snapshots.py`
  e documentação.
- Verificação: `rtk pytest -q tests\test_rag_snapshots.py` — **5 passed**;
  contratos, Ruff lint/formato e `rtk git diff --check` serão revalidados no
  gate conjunto antes do encerramento.
- Limitações: a verificação de busca é local e sintética; não há promoção,
  reindexação do índice ativo, cópia viva de Chroma/BM25, harness externo ou
  corpus real neste ticket.
- Rollback: desabilitar o reuso e reconstruir uma candidata isolada; snapshot
  incompatível ou inválido nunca altera a composição ativa.

### T16

- Estado: concluído localmente em 2026-09-05.
- Dependências confirmadas: T05, T07 e T10.
- Seam: ingestão pública, `rag/sources.json`, busca por sessão e
  `rag-profile-compare`.
- RED observado: o resultado de busca não expunha `locators`; a CLI de
  comparação de perfis ainda não existia.
- GREEN/refactor: normalização preserva páginas, slides, abas/células,
  timestamps e identificadores de código; a busca retorna `locators`,
  `citations` e metadados de formato. Quando a fonte não oferece estrutura,
  a resposta usa `normalized_section` com `available=false` e uma limitação
  explícita. `.vtt`, `.srt`, `.ass` e `.ssa` ficam como exigência de
  transcrição externa em Markdown. Extrações suspeitas são
  `quarantined` e não entram em `rag/`.
- Perfis: `rag-profile-compare` compara `compact`/`multilingual` por padrão,
  não muta a configuração, exige avaliação Golden nativa em português antes
  da seleção e declara `full_rebuild_required` quando houver troca.
- Arquivos: `docops/normalizer.py`, `docops/operations.py`,
  `docops/retrieval.py`, `docops/manifest.py`, `docops/rag_sync.py`,
  `docops/evaluator.py`, CLI/exports, schemas `rag-profile-comparison`,
  `tests/test_formats_portuguese.py` e documentação.
- Verificação: `rtk pytest -q tests\test_formats_portuguese.py` — **5 passed**;
  contratos, Ruff, formato e `rtk git diff --check` são revalidados no gate
  conjunto.
- Limitações: avaliação de perfil é um relatório preparatório; não troca
  embedding nem executa reindexação. A cobertura nativa depende do extrator
  disponível; transcrições exigem conversor externo. Evidência usa fixtures
  sintéticas temporárias, sem corpus real, conversa, publicação ou harness
  externo.
- Rollback: manter a composição ativa, colocar a extração sob suspeita em
  quarentena, exigir Markdown externo para transcrição e reconstruir uma
  candidata isolada antes de qualquer mudança de embedding.

### T17–T18

- T17 — estado: concluído localmente em 2026-09-05.
- RED/GREEN/refactor: o seam público de quarentena/revisão ainda não existia;
  o GREEN adicionou captura minimizada opt-in, decisão explícita, evidência
  independente, memória privada para preferências e documentos factuais
  rastreáveis. O refactor separou proposta, revisão, derivados e tombstones.
- Arquivos: `docops/learning.py`, `docops/operations.py`,
  `docops/__main__.py`, `docops/__init__.py`, contratos/schema de
  `learning-proposal`/`learning-review`, exemplos, testes e documentação.
- Verificação focada: `rtk pytest -q tests\test_learning.py` — **3 passed**.
  A suíte final no `.venv` alinhado ao lock passou com **317 passed, 2 skipped**;
  os dois skips são apenas a indisponibilidade de criação de symlink neste host
  Windows.
- Limitações: a admissão marca `reindex_required=true`, mas não executa
  reindexação; MCP real, conversas reais e harness externo permanecem
  desativados. `human_approver` é autoridade local explícita, não autenticação
  remota.
- Rollback: rejeitar/quarentenar a proposta; para admissão já revogada, os
  tombstones impedem a restauração histórica do derivado.
- T18 — estado: concluído localmente em 2026-09-05.
  - RED: o primeiro teste público falhou porque `feedback-submit` ainda não
    existia; a falha era do seam ausente, não da fixture.
  - GREEN/refactor: `docops/feedback.py` normaliza e persiste somente a
    projeção redigida, agrupa ocorrências independentes em uma janela de sete
    dias, abre investigação após três ocorrências e cria candidata Golden com
    `reviewed=false`. Repetições da mesma sessão/pergunta/geração contam como
    duplicatas. Comparações com fingerprints incompatíveis ficam
    `not_comparable`; relatórios incluem custo, latência e denominadores.
  - Worker: `feedback_report` usa lease/recibo durável, gera apenas o relatório
    e mantém `golden.json`, resposta esperada e RAG ativo intactos.
  - Arquivos: `docops/feedback.py`, `docops/coordination.py`,
    `docops/__main__.py`, `docops/__init__.py`, contratos/schema de
    `feedback`/`feedback-report`/`investigation`, exemplos, testes e
    documentação.
  - Verificação focada: `rtk pytest -q tests\test_usage_feedback.py` —
    **3 passed**; `rtk python scripts\check_contracts.py --json` —
    **ok=true**; Ruff lint/formato — **PASS**.
  - Limitações/rollback: não houve captura de conversa real, MCP/harness
    externo, publicação ou reindexação. Desligar o job/gatilho preserva os
    sinais redigidos e não pode editar Golden automaticamente.

## Gates finais executados

Os gates foram executados com o interpretador do `.venv` do projeto, que usa as
versões fixadas em `requirements.lock`. A suíte completa passou com **317
passed, 2 skipped**; os skips são esperados porque este host Windows não
permite criar symlinks. Também passaram `check_contracts`, `check_support_matrix`,
`check_public_seams`, Ruff lint, Ruff formato, `compileall` e `git diff --check`.

- [x] Suíte completa e checks de lint/formato/contratos.
- [x] Integração MCP real sobre pacote sintético isolado, conforme evidência
  registrada em T05; T17–T18 não acionam MCP nem harness externo.
- [x] Nenhuma operação no corpus/índice ativo, conversa real, captura ou
  publicação foi executada.
- [x] Revisão de diff, privacidade e arquivos ignorados/proibidos concluída;
  `git diff --check` passou e os artefatos operacionais temporários permanecem
  fora do escopo versionado.
