# Contratos propostos

[Índice](README.md) · [Especificação](SPEC.md) · [Validação](VALIDATION.md)

Tudo neste documento é **proposta**, salvo as interfaces marcadas como existentes.
Exemplos descrevem decisões; não são schemas executáveis nem comandos disponíveis.

## 1. Interface e compatibilidade

Seam existente preferencial: `import docops`, tipos Operation*, plan/preview/apply,
inspect e JSON documentado. A CLI delega para o mesmo motor (E01 em EVIDENCE).

| Interface | Situação | Comportamento proposto |
|---|---|---|
| plan/preview | Existente | Planejar camadas, fingerprints, impacto e blockers sem alterar destino |
| apply | Existente | Opção explícita para preparar candidata; comportamento legado preservado salvo proteção contra sobrescrita |
| inspect | Existente | Ativa, revisões, candidatas, defasagem, jobs e recuperação |
| validate/evaluate | CLI existente | Trabalhar sobre candidata identificada e persistir evidência vinculada |
| candidate submit/approve/publish/rollback | CLI implementada para submit/approve/publish/rollback | Importar resultado externo, controlar publicação e restaurar histórico |
| source register/reconcile | Nova CLI | Cadastrar conjunto desejado e reconciliar escopo completo |
| event submit/jobs/work --once | Implementada no T12 | `event-submit`/`jobs` persistem e projetam a fila; `work --once` executa um job com lease, recibo e retomada |
| impact-assess | Implementada no T13 | Cursor de impacto líquido, lote conceitual, revisão de incerteza, backlog e revogação |
| learning submit/review | Implementada no T17 | Captura minimizada, quarentena, revisão humana, memória privada e tombstones |
| feedback submit/report | Implementada no T18 | Sinais redigidos, deduplicação, investigação por recorrência, métricas comparáveis e candidata Golden não revisada |
| reader-session/query/revoke | Implementada no T14 | Fixar `release_id`/composição, aceitar apenas leitura e respeitar revogação |
| MCP de consulta/manutenção | Compatibilidade explícita no harness | `mode=read_only` para readers; manutenção fica fora da sessão |
| rag-snapshot/reuse-plan | Implementada no T15 | Inventário relocável, diff por hash, fallback de rebuild e busca de verificação |
| rag-profile-compare | Implementada no T16 | Comparação de perfis sem mutação, Golden nativo obrigatório e full rebuild na troca |

Opções sugeridas: seleção de camadas em OperationOptions e política de publicação
direta/candidata. O nome exato e a tipagem ficam em D04. Não ampliar `mode` atual
silenciosamente; preservar create/update/run/dry-run e seus significados.

Novos tipos públicos só são exportados da raiz quando necessários a callers.
Não exigir import de candidates, coordination ou helpers. Novos outcomes são
versionados; não converter falha em sucesso para manter um comando aparentemente verde.

## 2. Identidades e dependências

| Identidade | Conteúdo que a determina |
|---|---|
| source_id | Identidade estável da origem cadastrada e escopo |
| document_identity | Origem canônica, versão e hash normalizado, compatível com StateStore |
| corpus_revision | Documentos admitidos, hashes, escopos e metadados que afetam validade/consulta |
| index_revision | Corpus, backend, embedding, normalizador, chunker e configuração de recuperação |
| skill_revision | Bytes da skill/capítulos e mapa de dependências |
| router_revision | Bytes e versão da política de roteamento |
| golden_revision | Casos revisados, julgamentos, escopos e versão do contrato |
| policy_revision | Política autorizada de atualização/admissão/publicação |
| release_id | Composição das revisões publicadas |

Ordenação e serialização canônicas devem ser documentadas. Excluir durações,
timestamps e IDs da própria composição do hash. Evidências referenciam hashes,
mas não entram circularmente nos artefatos que medem. Mudar metadado meramente
operacional não dispara geração conceitual.

Embedding fingerprint inclui perfil, modelo/revisão, dimensões e prefixos.
Também registrar procedência do runtime e versão do backend. Nome de perfil
igual não comprova modelo igual. Reranker/configuração de busca invalidam avaliações
dependentes, sem obrigar reembedding quando não afetam vetores.

Dependência de conceito proposta: `claim_id`, seção da skill, fontes/versões,
localizadores, hashes e estado do suporte. Origem revogada invalida todos os
derivados alcançáveis. Ausência de mapa em pacote antigo significa cobertura
desconhecida, não cobertura total.

## 3. Envelopes mínimos

Todos incluem schema_version e validação de tamanho, caminhos, enums e tipos.
Guardar referências privadas separadas da projeção pública redigida.

| Objeto | Campos mínimos |
|---|---|
| SourceRegistration | source_id, canonical, kind, scope, version_policy, language, rights, privacy, authority, owner |
| AcquisitionSnapshot | source_id, revision, entries, scope, completeness, observation_time, errors |
| Event | event_id, type, package_id, source_id quando aplicável, observed_revision, occurred_at, origin, causation_id, payload |
| Job | job_id, job_key, type, package_id, target_revision, state, attempt, due_at, first/last_event_at, event_count, lease, result_ref, error_code, completed/deferred files |
| Candidate | candidate_id, base_release_id, target revisions, affected claims, status, artifacts, evidence_refs |
| EnrichmentRequest | candidate_id, base hashes, snapshot, diff, allowed_artifacts, policy_revision, language, budget |
| EnrichmentReceipt | request_id, tool/version, input/output hashes, validation, provenance, usage |
| Approval | `approval.schema.json`: approval_id, candidate_id, base_release_id, base/composition/evaluation/policy hashes, actor, role e timestamp |
| Release | `publication.schema.json`: release_id, candidate_id, approval_id, composition, parent_release_id e publicação factual |
| History | `history.schema.json`: history_id, release_id, composição, índice, retenção, revogação e compatibilidade |
| Rollback | `rollback.schema.json`: rollback_id, target_release_id, previous_release_id e timestamp |
| KnowledgeProposal | proposal_id, claim, type, scope/version, origin, evidence, privacy, status, review |
| EvaluationEvidence | evaluated revisions, cases hash, adapter/backend/config, metrics, thresholds, cases, outcome; optional independent response receipt hash and generation/candidate link |

Não armazenar credenciais nesses objetos. Payload de evento não contém chat ou
documento inteiro. event_id repetido com payload diferente é erro de integridade.

## 4. Transições e guardas

| Objeto | Transição | Guarda | Falha |
|---|---|---|---|
| Documento | discovered → admitted | Direitos/privacidade/qualidade/escopo aceitos | quarantined ou rejected |
| Documento | admitted → superseded | Nova representação válida | Manter anterior |
| Documento | admitted → revoked | Revogação autorizada | Registrar erro operacional sem ignorar bloqueio |
| Fonte | registered → reconciled | Snapshot completo no mesmo escopo | Preservar registro e observar `acquisition_incomplete`/`scope_mismatch` |
| Fonte | active → withdrawn | Snapshot completo vazio e retirada explícita | `withdrawal_confirmation_required`; não produzir ready vazio |
| Fonte | pinned → observed | Versão observada igual à versão fixada | `version_pinned`; não avançar automaticamente |
| Job | pending → running | Lease adquirido e revisão ainda pertinente | retry_wait/blocked |
| Job | running → succeeded | Efeito comprovado e recibo durável | retry_wait/failed |
| Candidata | draft → awaiting_enrichment | Tarefa e base fixadas | blocked |
| Candidata | awaiting_enrichment → validating | Saída íntegra no escopo | rejected |
| Candidata | validating → review_required | Gates estruturais/técnicos passaram | failed |
| Candidata | review_required → approved | Revisor autorizado e hashes atuais | blocked |
| Candidata | approved → published | Base atual, evidência válida, lease e permissões | stale_base/approval_invalidated |
| Proposta | proposed → verifying → review_required | Evidências registradas | unverifiable/rejected |
| Proposta | review_required → admitted | Revisão e consentimento aplicáveis | rejected |
| Pacote | active → retired | Remoção autorizada da última fonte | Não reportar ready vazio |

Readiness e aprovação são eixos separados. Candidata factual sem enriquecimento
pode preservar a skill e passar por revisão/política delegada; não precisa
atravessar awaiting_enrichment. Nenhum estado terminal é inferido apenas de ausência
de thread ativa. `already_running` do MCP exige acompanhar o trabalho correto.

Pacotes antigos continuam com seus estados existentes. Novos campos de ciclo
editorial não reinterpretam o enum de readiness. Retirada da última fonte exige
extensão explícita do contrato, sem fazer o validador antigo aceitar ready vazio.

## 5. Fila, execução e consistência

- Entrega pelo menos uma vez, efeitos idempotentes; não prometer exactly-once distribuído.
- Chave de trabalho usa pacote, tipo, revisão alvo e política; event_id identifica entrega.
- Um writer por pacote; workers de pacotes distintos podem trabalhar independentemente.
- Lease de job é distinto do lease de promoção. Transações da fila devem ser curtas.
- Capturar snapshot antes da fase crítica; revisão/base é verificada antes de publicar.
- Não manter lease de publicação enquanto espera aprovação humana ou harness externo.
- Eventos durante uma execução ficam pendentes para revisão seguinte.
- Mudança da base não é falha transitória: replanejar e invalidar evidência correspondente.
- Reconciliação periódica recupera eventos perdidos; evento é indício, snapshot é autoridade.
- A fila local do T11 usa SQLite durável; a projeção pública é retornada por
  `jobs`, e não depende de inspeção SQL.
- Deduplicação aceita a repetição exata de `event_id` e rejeita o mesmo
  identificador com payload divergente.
- O debounce observável é `min(last_event + 60s, first_event + 5min)`.
- Arquivos instáveis são adiados, mas não bloqueiam arquivos concluídos
  projetados no mesmo evento.
- O worker T12 só prepara candidatas, nunca autopublica. Indexação RAG exige
  autorização persistida que corresponda ao pacote, revisão alvo e política.
- O reconhecimento é separado do efeito: `.docops/job-receipts/` é validado
  por hash da solicitação e permite reconciliar um lease expirado sem repetir
  o efeito. Falhas transitórias têm no máximo cinco tentativas; falhas de
  política ficam bloqueadas.
- O `impact-assess` do T13 mantém cursor por documento/revisão e calcula impacto
  líquido. Reindex sem diff é no-op; reversão para a revisão-base remove o
  documento; eventos factuais não contam para enriquecimento conceitual.
- O lote só é solicitado ao atingir dez documentos distintos, ou três e 10% do
  corpus. Impacto incerto fica `review_required`, com `publication_allowed=false`.
  O limite de quatro lotes em 24 horas deixa novos lotes em `backlog` sem perder
  visibilidade. Um `causation_id` acompanha a origem do lote.
- Revogação grava tombstone de suporte inválido imediatamente, mesmo quando não
  há orçamento. O gatilho não aprova, publica ou reindexa; ele apenas produz uma
  projeção determinística para o próximo job/candidata.

Retry proposto: até cinco execuções por revisão, com espera de 1, 5, 15 e 60 minutos
e jitter de até 10%. Só falhas transitórias entram nesse fluxo. Licença, conflito,
perfil incompatível e ausência de aprovação ficam blocked, sem repetir continuamente.
`harness_unavailable` mantém awaiting_enrichment. Nova evidência pode criar novo job.

Após crash entre publicação e reconhecimento, consultar recibo/publicação por
identidade e confirmar o efeito existente antes de repetir. Cancelamento não apaga
evidência nem elimina geração ativa. A fila fica fora da aquisição e da árvore ativa.

O agendador pode executar worker em background, mas cada operação MCP deve ser
aguardada pelo worker até resultado comprovado. Não abandonar subprocesso após
disparo de reindex. O wrapper legado permanece em primeiro plano conforme AGENTS.
O worker T12 reutiliza o motor existente e mantém a fila/recibos fora da árvore
ativa, ignorados na aquisição em `.docops` e não pertencentes ao release. A
transação entre SQLite e filesystem continua não distribuída; o recibo é a
reconciliação determinística dessa janela.

## 6. Publicação e readers

Preparar snapshot/candidata → validar → avaliar → aprovar → adquirir lease →
verificar base/hash/revogação → promover com journal → validar publicação →
registrar recibo → reconhecer job.

No piloto, os seams CLI `candidate-approve` e `candidate-publish` implementam
essa transição. O recibo de aprovação é separado do recibo de publicação:
mudança de artefato, Golden, política, evidência ou base invalida o gate; a
promoção não acontece sem revalidação. A autorização local é explícita e
redigida, mas não pretende autenticar uma identidade remota.

`candidate-publish` retém a composição ativa anterior em
`.<package>.history/<release_id>/`, fora dos resíduos que `cleanup()` pode
remover. `candidate-rollback` lê essa cópia, valida o recibo `history`, o
manifesto e o índice, grava um novo `rollback` e usa o mesmo journal de
promoção. Revogação ou incompatibilidade declarada do índice bloqueia a troca;
quota insuficiente bloqueia a publicação antes de mover a ativa.

Os seams `source-register` e `source-reconcile` mantêm registros por
`source_id` e não deduplicam proveniências apenas porque dois registros apontam
para o mesmo canonical. Observações com escopo ou completude insuficientes são
preservadas sem remoção; a retirada da última fonte exige autorização explícita.
O planejamento zera o diff destrutivo quando a aquisição não produz uma
observação utilizável, mantendo a geração ativa.

Reutilizar recuperação existente. A extensão não promete transação distribuída
entre SQLite e filesystem; o recibo idempotente reconcilia a janela entre ambos.
Artefatos de índice precisam ser verificáveis também depois da mudança de caminho.

`reader-session` registra `release_id` e `composition_hash` e usa a mesma
composição para skill/router/RAG. `reader-query` só aceita
`search_knowledge`/`get_document`; `add_document`, `update_document`,
`delete_document`, `reindex_documents`, `update_source` e ferramentas
desconhecidas são recusadas por enforcement no backend, não apenas pelo texto
do router. Perfil de manutenção é reservado ao operador e não é herdado pela
sessão.

Arquivos de uma geração publicada são logicamente imutáveis; manutenção cria
outra. Cache inclui sessão, geração, ferramenta, consulta e limite. Revogação
é persistida em tombstone fora do pacote e deve ser respeitada inclusive por
leitores de gerações antigas. Estado de sessão fica em
`.<package>.readers/`, separado da composição ativa, para sobreviver à troca
coordenada do diretório.

O harness gerado declara `mode=read_only`, capacidades explícitas de leitura,
lista de capacidades de escrita vazia e `concurrent_publication_allowed=false`.
Um adapter MCP sem esse perfil falha fechado; portanto a sessão não promete
publicação concorrente segura quando o backend não comprova a capacidade.

`rag-snapshot` é uma operação somente leitura. O snapshot registra caminhos
relativos, hashes de documentos, identidade do embedding e um inventário
lógico de `rag/index.json`/`rag/data`; não copia um processo vivo nem expõe
caminhos absolutos. `rag-reuse-plan` compara hashes, não apenas mtime/tamanho,
e escolhe `incremental` somente quando o embedding, o backend e o snapshot
lógico são compatíveis. Qualquer falha de leitura, mudança de embedding ou
backend sem capacidade declarada resulta em `full_rebuild` ou erro fechado,
com `active_preserved=true` e sem promoção automática.

O relatório pode executar uma busca de verificação pelo adapter escolhido.
Essa verificação é evidência de contagem/fontes no pacote corrente; não concede
autoridade para publicar e não substitui avaliação Golden ou confirmação MCP.

Resultados de recuperação carregam proveniência opcional por formato. O
localizador comum informa `kind`, disponibilidade, linha inicial/final e um
limite quando a fonte não oferece estrutura estável. Citações usam
`path#fragment`; quando só há texto normalizado, o fragmento é
`normalized_section` e a resposta declara a limitação. Transcrição VTT/SRT/ASS/SSA
é deliberadamente externa: somente Markdown com timestamps entra no pipeline.

Extração suspeita é marcada como `quarantined`, contabilizada no manifesto e
excluída do conteúdo indexável. `rag-profile-compare` compara configurações de
embedding sem escolher silenciosamente uma delas; a decisão fica
`publication_allowed=false` até avaliação Golden nativa (português) e a mudança
de perfil requer full rebuild.

Pacote exportado mantém skill/, router/, rag/, manifest.json e harness.json.
Histórico/fila não precisam ser exportados. Migração do harness é explícita;
integração antiga sem fixação não recebe promessa de publicação concorrente segura.

## 7. Aprovação, privacidade e rollback

A aprovação local depende de autoridade do processo/usuário, não de declaração
no documento. Hash detecta mudança; não autentica pessoa. Assinatura criptográfica
e identidade remota ficam fora da primeira entrega, salvo necessidade aprovada.

Rollback cria evento novo e reativa composição compatível após validação.
Não restaurar índice de embedding incompatível nem fonte revogada. Se uma geração
retida precisar de rebuild para ser consultável, mostrar esse requisito antes de
alterar ativa; não prometer rollback instantâneo.

O histórico editorial é separado de staging, backups e tentativas operacionais.
Sessões pinadas são vinculadas a `release_id` pelo T14; nenhum caminho de
cleanup conhece ou remove o diretório de histórico. Se a geração pinada não
estiver na ativa nem no histórico retido, a consulta falha com geração
indisponível.

Quarentena, conversas, aprovações privadas e índices ficam fora da release pública.
Defaults de retenção da SPEC não superam uma ordem autorizada de expurgo.

O seam `learning-submit` exige `--capture-opt-in` e aceita somente um trecho
minimizado; `learning-review` exige ator/papel explícitos e nunca trata
`approved=true` no conteúdo como autorização. Respostas do agente não são
evidência independente. Fatos admitidos geram um documento com hash e
`reindex_required=true`, mas `publication_allowed=false`; preferências ficam
em memória privada. Revogação remove derivados e registra tombstones que
bloqueiam rollback ressuscitador.
O pacote pode registrar metadados redigidos de expurgo sem reter o conteúdo removido.

O seam `feedback-submit` persiste apenas uma projeção redigida, hashes da
pergunta/geração e métricas de uso. `feedback-report` agrupa uma janela
determinística, conta no máximo uma ocorrência por combinação de sessão,
pergunta, tipo e geração, e solicita investigação após três ocorrências
independentes. O relatório inclui latência, custo e denominadores; fingerprints
incompatíveis retornam `not_comparable` e nunca são apresentados como
regressão controlada. A investigação e sua candidata Golden carregam origem,
mas permanecem `reviewed=false`/`publication_allowed=false`; o job de worker
somente grava o relatório/recibo e não altera Golden, resposta esperada ou RAG.

## 8. Estratégia de migração

1. Ler v1 sem reescrita implícita; apresentar capacidades desconhecidas como desconhecidas.
2. Registrar inventário dos artefatos cuja origem é verificável.
3. Se skill legada não tiver baseline verificável, pedir adoção explícita no fluxo de migração;
   não adivinhar que o conteúdo pertence ao gerador.
4. Acrescentar revisões e evidências; evidência antiga não habilita autopublicação.
5. Habilitar candidatas manuais antes de jobs automáticos.
6. Ativar publicação factual somente após T14 e gates de recuperação.
7. Introduzir snapshot incremental como capacidade negociada, com rebuild de fallback.

Schemas em schemas/ e docops/schemas/ evoluem juntos; atualizar check_contracts,
exemplos, documentação e testes públicos no mesmo ticket do comportamento.
