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
| candidate submit/approve/publish/rollback | Nova CLI | Importar resultado externo e controlar publicação |
| source register/reconcile | Nova CLI | Cadastrar conjunto desejado e reconciliar escopo completo |
| event submit/jobs/work --once | Nova CLI | Fila durável e processamento limitado |
| learning submit/review | Nova CLI | Quarentena e admissão de alegações |
| MCP de consulta/manutenção | Existente com extensão | Separar permissões e fixar geração |

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
| Event | event_id, type, package_id, source_id quando aplicável, observed_revision, occurred_at, origin, causation_id |
| Job | job_id, type, target_revision, state, attempt, due_at, lease, result_ref, error_code |
| Candidate | candidate_id, base_release_id, target revisions, affected claims, status, artifacts, evidence_refs |
| EnrichmentRequest | candidate_id, base hashes, snapshot, diff, allowed_artifacts, policy_revision, language, budget |
| EnrichmentReceipt | request_id, tool/version, input/output hashes, validation, provenance, usage |
| Approval | approval_id, candidate_id, base_release_id, artifact/evidence hashes, policy_revision, actor, role, expiry |
| Release | release_id, composition, parent_release_id, approval/policy ref, publication event |
| KnowledgeProposal | proposal_id, claim, type, scope/version, origin, evidence, privacy, status, review |
| EvaluationEvidence | evaluated revisions, cases hash, adapter/backend/config, metrics, thresholds, cases, outcome |

Não armazenar credenciais nesses objetos. Payload de evento não contém chat ou
documento inteiro. event_id repetido com payload diferente é erro de integridade.

## 4. Transições e guardas

| Objeto | Transição | Guarda | Falha |
|---|---|---|---|
| Documento | discovered → admitted | Direitos/privacidade/qualidade/escopo aceitos | quarantined ou rejected |
| Documento | admitted → superseded | Nova representação válida | Manter anterior |
| Documento | admitted → revoked | Revogação autorizada | Registrar erro operacional sem ignorar bloqueio |
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

## 6. Publicação e readers

Preparar snapshot/candidata → validar → avaliar → aprovar → adquirir lease →
verificar base/hash/revogação → promover com journal → validar publicação →
registrar recibo → reconhecer job.

Reutilizar recuperação existente. A extensão não promete transação distribuída
entre SQLite e filesystem; o recibo idempotente reconcilia a janela entre ambos.
Artefatos de índice precisam ser verificáveis também depois da mudança de caminho.

Sessão registra release_id e usa a mesma composição para skill/router/RAG.
Arquivos de uma geração publicada são logicamente imutáveis; manutenção cria outra.
Perfil de consulta deve recusar add/update/remove/reindex por enforcement no backend,
não apenas pelo texto do router. Perfil de manutenção é reservado ao operador.
Cache deve incluir a geração ou ser invalidado na troca; tombstones de revogação
precisam ser respeitados inclusive por leitores de gerações antigas.

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

Quarentena, conversas, aprovações privadas e índices ficam fora da release pública.
Defaults de retenção da SPEC não superam uma ordem autorizada de expurgo.
O pacote pode registrar metadados redigidos de expurgo sem reter o conteúdo removido.

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
