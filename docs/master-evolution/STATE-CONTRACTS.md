# Contratos de projeto, inicialização e mudança

Status: contrato implementado localmente nesta execução. As fronteiras de publicação, corpus/índice real e credenciais continuam externas e bloqueadas por escopo. Os comandos existentes citados na primeira seção não são substituídos. Convenção: caminhos de evidência são relativos à raiz do repositório; a linha identifica o contrato inspecionado, não uma promessa de estabilidade do número após implementação.

## 1. Fronteira existente que deve ser preservada

| Evidência atual | Implicação para esta proposta |
|---|---|
| `docops/__init__.py:3` e `docops/__init__.py:59`: API raiz expõe planos, aplicação, candidatas, fontes, fila, leitura e snapshots | Expor novas operações na raiz; compor essas capacidades em vez de importar internals no harness |
| `docops/lifecycle.py:1` e `docops/lifecycle.py:29`: a geração de pacote é o único armazenamento ativo de conteúdo e existe vocabulário canônico | Projeto é um agregado de planejamento e referências; não é outra máquina de estados editoriais |
| `docops/__main__.py:221`: `candidate-request` e `candidate-submit`; `docops/__main__.py:234`: aprovação/publicação/rollback | Integrar e observar a execução externa; não alegar ausência total de integração conceitual |
| `docops/__main__.py:265`: cadastro/reconciliação; `docops/__main__.py:299`: `work --once` obrigatório | Reusar reconciliação e worker. Não instruir `work --loop` como comando existente |
| `schemas/source-registration.schema.json:5`: identificação, direitos, privacidade, autoridade, versão e status já obrigatórios | Complementar granularidade e vigência; não criar registry independente |
| `schemas/approval.schema.json:6`: aprovação vinculada à base, revisões, avaliação, política e autoridade autenticada | Referenciar recibo existente; projeto não pode converter booleano “aprovado” em autorização |
| `schemas/publication.schema.json:6` e `schemas/history.schema.json:4`: recibo de promoção e geração retida | Reusar release, composition hash e rollback existentes |
| `schemas/reader-session.schema.json:25`: geração e snapshot pinados; `schemas/reader-session.schema.json:75`: publicação concorrente não habilitada no contrato atual | A nova camada não pode anunciar leitura/publicação concorrente sem trabalho específico e evidência |
| `schemas/conceptual-impact.schema.json:6`: impacto conceitual, batch, backlog e revogações | Acrescentar grafo de curso/página ao resultado de análise; não duplicar o classificador existente |
| `tests/SEAMS.md:3`, `tests/test_public_interface.py:9`, `tests/test_promotion_recovery.py:36`, `tests/test_source_registry.py:117` | Aceitação por raiz/CLI/JSON/MCP; preservar recuperação e reconciliação parcial |
| `docs/SCHEMAS.md:3` e `docs/SCHEMAS.md:64`: contratos versionados, schemas normativos e cópia empacotada | Acrescentar contratos nas duas distribuições pelo sincronizador existente, com testes de drift |

Essas evidências são inspeção de código/contratos e testes existentes, não declaração de que todos esses testes passaram nesta análise.

## 2. Responsabilidades e artefatos novos

Layout do projeto, distinto da estrutura interna do pacote existente:

- `project.json`: identidade, ponteiro para revisão de projeto ativa (ou nulo), locator relocável do pacote e política de escrita. Alteração pequena, atômica e protegida por lease.
- `init/session.json`: conversa minimizada em andamento, respostas estruturadas, revisão de sessão e perguntas pendentes. Não armazenar transcript completo por padrão.
- `revisions/<project_revision_id>/`: composição imutável contendo brief, curso, página, decisões, governança, grafo e manifesto de referências com hashes. Arquivos legíveis em Markdown são projeções auxiliares.
- `changes/<change_id>/`: proposta, relatório de impacto e recibos de preparação/ativação; novos recibos não alteram a proposta original.
- `package/` ou locator relativo equivalente: pacote DOCOPS existente. Sua candidata, release, histórico, reader e índice continuam pertencendo ao DOCOPS atual.
- `AGENTS.md`: instruções estáveis e referência aos artefatos; nunca transcrições, fatos voláteis, preço ou brief integral.

O MVP admite **um pacote operacional por projeto**. Várias fontes pertencem a esse pacote. Vários pacotes por projeto exigem protocolo transacional próprio e ficam fora do MVP. O índice não deve apontar para `revisions/` inteiro: decisões comerciais e documentos de controle não entram automaticamente no corpus factual.

## 3. Protocolo conversacional determinístico

Comandos disponíveis sob `python -m docops`: `init start --project <dir> --input <json> --json`; `init status --project <dir> --json`; `init answer --project <dir> --input <json> --json`; `init finalize --project <dir> --input <json> --json`. API raiz equivalente: `start_project_init`, `inspect_project_init`, `answer_project_init`, `finalize_project_init`. Cada mutação recebe idempotency key e revisão esperada no JSON; nenhum prompt interativo é obrigatório no subprocesso.

1. **Start:** valida pasta, identidade e payload; cria sessão privada. O harness pode fornecer contexto já explícito, sem perguntar novamente. Um preset pode sugerir tópicos; não pode confirmar decisões do usuário.
2. **Interpretar intenção:** classificar objetivo, público, entregáveis e a ambiguidade de canal. “Curso para vender no Mercado Livre” mantém `course_intent=unresolved` até confirmação; registra hipóteses separadas.
3. **Perguntas prioritárias:** primeiro intenção/público/uso permitido; depois entregáveis e restrições; por último formato/estilo. O núcleo devolve chaves estáveis, motivo e entregáveis bloqueados; o harness formula perguntas em linguagem natural, em grupos pequenos.
4. **Answer:** recebe respostas por chave, origem e revisão esperada. Só a operação aplicada incrementa a revisão; repetição idêntica devolve o recibo anterior. Correção substitui o valor da sessão e acrescenta decisão que referencia a anterior.
5. **Status/retomada:** leitura sem efeitos devolve respostas minimizadas, estado, perguntas ainda pendentes, bloqueios, próximos passos permitidos e número de revisão. Não depende de memória da conversa, PID ou provedor do harness.
6. **Validação:** distinguir `missing_required` (sem isso não há projeto coerente), `pending_product_decision` (pode haver draft privado) e `blocked_use` (licença/privacidade/publicação sem autorização). Campos opcionais não geram pergunta repetida.
7. **Finalize:** grava revisão imutável privada e projeções, com pendências explícitas. Não indexa, enriquece, aprova, ativa nem publica. Cria pacote vazio somente se o contrato atual permitir isso; caso contrário, locator fica reservado e o primeiro pacote é criado pela operação de pacote já existente quando houver fonte admissível.
8. **Trabalho posterior:** alterações usam propostas com base da revisão finalizada. Uma sessão finalizada é somente leitura; corrigir gera nova proposta ou nova sessão ligada à revisão, sem reescrever histórico.

Estados novos pertencem somente à sessão de init: `collecting → draft_ready → finalized`, com `cancelled` permitido antes da finalização. `draft_ready` exige nome/objetivo mínimo e seleção ou pendência explícita dos entregáveis; aceita decisões de produto pendentes. Answer posterior a `draft_ready` pode retornar a `collecting` se remover uma informação estrutural. `finalized` e `cancelled` são terminais. Erro transitório é recibo de operação, não novo estado editorial.

### Decisões e bloqueios obrigatórios

| Chave | Pode ser desconhecida no draft? | Regra |
|---|---|---|
| objetivo e nome | Não ao finalizar | Texto não vazio; nome não determina identidade interna |
| público e região | Sim | Bloqueia recomendações segmentadas/normativas até resolução ou declaração de escopo limitado |
| intenção do curso | Sim | `about_marketplace_selling` e `sold_on_marketplace` não se fundem; bloqueia curso final e oferta dependentes |
| mapa do curso, nível, formato, transformação | Sim | Esboço identificado como proposta; sem promessa automática de resultado |
| oferta, preço, garantia, CTA de compra | Sim | Nenhum valor inventado; bloqueia página comercial publicável |
| licença e permissão por uso | Sim no cadastro | Bloqueia uso específico não concedido, inclusive redistribuição de transcrição |
| política de publicação | Padrão técnico seguro | `manual`; qualquer delegação exige autorização autenticada e escopo explícito posterior |

## 4. Convenções normativas para os novos schemas

Cada novo documento persistente possui `schema_version` inteiro igual a 1, `kind` constante do schema, identificador opaco não vazio, `created_at` UTC RFC3339 e `content_hash` SHA-256 hexadecimal de 64 posições calculado sobre JSON canônico sem o próprio hash. Ordenar chaves, UTF-8, sem whitespace supérfluo; preservar ordem dos arrays quando semanticamente relevante. O algoritmo é único e versionado pelo schema. Markdown não é autoridade para calcular conteúdo JSON.

Todos os campos listados nas tabelas são obrigatórios, salvo marcação **opcional**. `null` significa desconhecido/não aplicável conforme o campo, nunca autorização, ausência de revogação ou string vazia. Array vazio significa nenhum item registrado. ID desconhecido não pode ser substituído por nome. Referências devem existir e pertencer ao mesmo projeto/pacote; validação relacional ocorre além do JSON Schema.

Novos objetos aceitam extensões somente no campo opcional `extensions`, objeto com chaves namespaced; campos desconhecidos fora dele falham para evitar typo silencioso. A regra vale para os contratos **novos**, sem mudar retroativamente a permissividade dos schemas atuais. Consumidor não pode usar extensão desconhecida para conceder direitos ou publicar. Mudança semântica/remover campo exige nova versão; não ampliar enum existente sem avaliar compatibilidade.

### 4.1 Identidade e sessão

| Schema/campo | Tipo / valores | Invariante |
|---|---|---|
| Project/project_id | string | ID estável, não derivado de caminho absoluto |
| Project/name | string | Não vazio |
| Project/package_locator | string ou null | Caminho relativo contido no projeto; nulo antes de pacote real |
| Project/active_project_revision_id | string ou null | Nulo até ativação completa; deve referenciar composição válida |
| Project/working_project_revision_id | string ou null | Último draft finalizado; não representa ativo |
| Project/write_revision | integer ≥ 0 | CAS do ponteiro e locator; diferente do ID editorial |
| Project/visibility | enum `private` | MVP não oferece publicação web automática |
| InitSession/session_id, project_id | string | Vinculam sessão à identidade correta |
| InitSession/session_revision | integer ≥ 0 | Incrementa em mutação efetivamente aplicada |
| InitSession/status | enum `collecting`, `draft_ready`, `finalized`, `cancelled` | Transições da seção 3 |
| InitSession/preset | objeto `{id:string, version:string}` ou null | Cópia de sugestões rastreável; não confirmar decisões |
| InitSession/answers | array de Answer | Uma resposta vigente por question_key |
| InitSession/decisions | array de Decision | Histórico minimizado; IDs imutáveis |
| InitSession/pending_questions | array de Question | Calculado deterministicamente a partir de respostas/política |
| InitSession/finalized_revision_id | string ou null | Não nulo somente após finalização |
| Answer/question_key | string | Chave pertencente ao contrato/preset conhecido |
| Answer/value | valor tipado pela question_key | Contrato por chave, não aceitar JSON arbitrário como política |
| Answer/origin | enum `user_explicit`, `imported_confirmed`, `agent_proposed`, `preset_default` | Somente duas primeiras podem registrar decisão confirmada com evidência |
| Answer/evidence_ref | string ou null | Referência minimizada à confirmação; sem transcript bruto |
| Question/key, prompt, reason | string | Texto não vazio; key estável entre retomadas |
| Question/blocks | array de enum `draft`, `course`, `page`, `ingestion`, `activation`, `public_distribution` | Explica efeito da pendência |
| Question/required | boolean | Se false, recusa/adiamento não impede draft |
| Decision/decision_id, key | string | Key identifica decisão de produto ou técnica |
| Decision/status | enum `pending`, `proposed`, `confirmed`, `superseded`, `rejected` | Origem agent/preset não confirma produto |
| Decision/value | valor JSON ou null | Null permitido somente pending/rejected |
| Decision/actor, evidence_ref, supersedes | string ou null | Confirmed exige actor/evidence_ref; supersedes exige ID anterior |

### 4.2 Revisão, curso e página

| Schema/campo | Tipo / valores | Invariante |
|---|---|---|
| ProjectRevision/project_revision_id, project_id | string | Revisão imutável |
| ProjectRevision/parent_project_revision_id | string ou null | Null somente primeira revisão |
| ProjectRevision/package_ref | PackageRef ou null | Nulo em draft sem pacote; obrigatório para ativação operacional |
| ProjectRevision/artifacts | array de ArtifactRef | Tipos únicos para brief, course, page, decisions, source-governance, policy, dependencies; curso/página podem estar omitidos se fora do escopo |
| ProjectRevision/pending_decision_ids | array de string | Referências válidas a decisões pending/proposed |
| ProjectRevision/change_id | string ou null | Origem rastreável; nulo na primeira inicialização |
| PackageRef/package_id, release_id, composition_hash | string | Identidade real obtida do pacote/recibo, nunca gerada pela camada de projeto |
| PackageRef/candidate_id | string ou null | Candidata exata em preparação; ativa usa release publicado verificado |
| ArtifactRef/kind | enum `brief`, `course`, `page`, `decisions`, `source-governance`, `policy`, `dependencies` | Sem duplicatas |
| ArtifactRef/artifact_id, revision_id, path, hash | string | Caminho relativo sem traversal; conteúdo corresponde ao hash |
| Course/course_id, revision_id | string | Identidade estável; revisões imutáveis |
| Course/intent | string ou null | Descrição genérica confirmada da intenção; null mantém pendência. Enum Mercado Livre fica na extensão do preset, nunca no enum do núcleo |
| Course/level, transformation, format | string ou null | Pendência explícita se desconhecida |
| Course/modules | array de Module | Ordem editorial explícita; IDs não dependem da posição |
| Module/module_id, title | string | Identidade estável por módulo |
| Module/lessons | array de Lesson | IDs globais dentro do curso; sem repetição |
| Lesson/lesson_id, title | string | Identidade estável |
| Lesson/objectives, exercises, examples, prerequisite_ids, evidence_refs | arrays de strings | Referências/locadores validados; não tratar texto de exemplo como evidência |
| Page/page_id, revision_id | string | Identidade estável/revisão imutável |
| Page/goal, tone, audience | string ou null | Escopo independente do corpus operacional |
| Page/sections | array de Section | Ordem define composição da página |
| Section/section_id, purpose | string | Identidade estável e finalidade |
| Section/claim_ids, evidence_refs, decision_ids | arrays de string | Toda alegação/prova e decisão comercial rastreável |
| Page/offer | objeto | Campos obrigatórios `benefits:array[string]`, `proof_refs:array[string]`, `price:null|{amount_decimal:string,currency:string}`, `guarantee:null|string`, `cta:null|string` |
| Page/restrictions | array de string | Linguagem, conformidade e promessas vedadas |

`Brief` possui `goal:string`, `audience:null|string`, `region:null|string`, `language:null|string`, `deliverables:array[knowledge,course,page]`, `constraints:array[string]`, `open_decision_ids:array[string]`. Sem entregável knowledge não há ativação operacional neste produto; curso/página são opcionais. `Policy` possui `publication_mode:manual|trusted_factual`, `delegation_ref:null|string`, `private_draft_only:boolean`, `rights_policy_revision:string`, `privacy_policy_revision:string`. MVP aceita somente manual e delegation_ref nulo; `trusted_factual` fica reservado e é rejeitado com `FEATURE_NOT_ENABLED` até a fase correspondente.

O preset Mercado Livre pode validar `extensions["mercado-livre"].course_intent` pelo enum `about_marketplace_selling|sold_on_marketplace|both_confirmed|other|unresolved`. O núcleo trata a decisão correspondente como pendente/confirmada por contrato genérico; não importa um enum de marketplace para sua lógica. Sem preset, Course/intent continua suficiente para representar outros domínios.

### 4.3 Metadados de fonte e evidência (overlay)

Preservar `SourceRegistration` v1. Criar `SourceGovernance` v1 vinculado a `source_id` e `observed_revision`; acesso efetivo é a interseção entre registro atual, governança, revogações e política do projeto. Ausência do overlay significa “contexto desconhecido”, nunca “livre”. Migração não infere direitos de `rights` textual legado.

| Campo | Tipo / valores | Invariante |
|---|---|---|
| source_id, observed_revision | string | Identidade/revisão do registro observado |
| source_type | enum `official_documentation`, `policy`, `article`, `study`, `experiment`, `video_transcript`, `other`, `unknown` | Independente de kind local/repository/web existente |
| author, organization, published_at, captured_at, language, region | string ou null | captured_at obrigatório não nulo após aquisição; timestamps UTC RFC3339; published_at admite YYYY-MM-DD com published_precision=date |
| published_precision | enum `unknown`, `date`, `timestamp` | unknown exige published_at null; date não autoriza inventar hora; timestamp exige RFC3339 |
| authority_class | enum `official`, `research`, `practitioner`, `community`, `unknown` | Não é nota universal de verdade |
| validity | objeto `{from:null|string, until:null|string, checked_at:null|string, review_after:null|string}` | Until anterior a from é inválido; ausência de until não implica vigência perpétua |
| use_policy | objeto | `license_id:null|string`, `grants:array[UseGrant]`, `restrictions:array[string]`; uma entrada por finalidade obrigatória, sem duplicatas |
| lifecycle | enum `active`, `archived`, `revoked` | Archived não participa do corpus ativo; retirada/revogação chama mecanismos existentes, sem apenas alterar overlay |
| privacy | objeto `{classification:public|internal|restricted|unknown, retention_until:null|string, redaction_required:boolean}` | Unknown bloqueia usos que exigem classificação |
| transcript | objeto ou null | Se não nulo: `video_url:string`, `provider:string`, `permission_ref:null|string`, `segments:array[{segment_id:string,start_ms:integer≥0,end_ms:integer>start_ms,text_ref:string}]`; texto pode ser privado |
| derived_from | array de EvidenceRef | Vincula resumo/transcrição/artefato à representação original |

`EvidenceRef`: `{source_id, observed_revision, document_id, content_hash, locator}`; IDs/hashes strings obrigatórios. `locator` exige `kind:section|page|timestamp|line`, `value:string` e `end:null|string`. Timestamp tem intervalo verificável na transcrição; fallback genérico para URL não pode fingir localizar uma afirmação. Uma evidência expirada, revogada ou regionalmente inaplicável continua rastreável, mas não sustenta automaticamente uma resposta atual.

`UseGrant`: `purpose:acquisition|storage|indexing|internal_query|quotation|derivatives|redistribution`, `decision:unknown|allowed|denied`, `evidence_ref:null|string`, `actor:null|string`, `valid_from:null|string`, `valid_until:null|string`, `review_after:null|string`. Datas UTC RFC3339; allowed exige evidência e responsável, além de validade ou prazo de revisão explícito. Finalidade ausente/unknown bloqueia o uso correspondente. Consulta interna permitida não implica captura, indexação ou redistribuição permitidas. Expiração ou revogação invalida a autorização efetiva. Este overlay é o contrato canônico aditivo; não criar um segundo registry nem alterar silenciosamente SourceRegistration v1.

`Claim`: `claim_id:string`, `text:string`, `classification:official_rule|factual_observation|opinion|experience|hypothesis|recommendation`, `region:null|string`, `validity` como acima, `evidence_refs:array[EvidenceRef]`, `conflict_ids:array[string]`, `review_status:proposed|reviewed`, `reviewer_ref:null|string`. Reviewed exige revisor; autoridade oficial exige evidência de verificação, não apenas autodeclaração. `Conflict`: `conflict_id:string`, `claim_ids:array[string]` (mínimo dois), `relation:contradicts|supersedes|scope_difference`, `status:open|resolved`, `resolution:null|string`, `reviewer_ref:null|string`. Resolved exige resolução e revisor; “mais recente” sozinho não resolve conflito de escopo/região.

### Consulta de evidência (extensão pública)

Estender reader query mantendo sua seam e compatibilidade v1. Requisição nova fixa project_id, sessão e filtros opcionais theme, source_kind, claim_type, authority, region, as_of, published_from e published_until. Datas válidas e enums tipados; intervalo invertido ou filtro desconhecido retorna INVALID_INPUT. A sessão determina a composição, que não pode ser substituída pelo chamador.

Resultado novo possui `outcome:supported|conflicting|insufficient_evidence`, `evidence:array[EvidenceRef]`, `claims:array[Claim]`, `conflicts:array[Conflict]`, `applied_filters:object`, `limitations:array[string]`, `snapshot_identity:object`. O envelope técnico conserva sucesso/erro separados do outcome de evidência: insufficient_evidence não é falha de transporte. supported exige ao menos uma evidência elegível; não significa que o núcleo gerou ou validou uma resposta textual. O harness produz a resposta, avaliada separadamente. Implementar como contrato versionado negociado, sem trocar a forma do reader-query v1 silenciosamente.

## 5. Mudança e dependências

Interface sob o domínio CLI `project`: `change propose`, `change inspect`, `change prepare`, `change activate` e `rollback`. Cada comando recebe project locator; mutações recebem JSON com idempotency_key, expected_revision e payload; inspect recebe change_id e é somente leitura. API raiz equivalente: propose_project_change, inspect_project_change, prepare_project_change, activate_project_change e rollback_project. Propose valida e persiste a proposta/diff sem executar aquisição; prepare compila o plano para candidata existente; activate exige recibos do lifecycle e coordena o vínculo da revisão; rollback recebe revisão histórica alvo e nunca ignora revogações. A implementação mantém esses nomes como superfície pública sem expor helpers internos ao harness.

CLI: `project change propose`, `project change inspect`, `project change prepare`, `project change activate`, `project rollback`, todas com `--project`, entrada JSON quando houver mutação e `--json`. API raiz oferece as mesmas operações e resultados, sem exigir import de implementação. `activate` **não** substitui `candidate-approve`/`candidate-publish`: coordena os recibos e só avança depois dos gates existentes.

| Campo de ChangeProposal | Tipo / valores | Regra |
|---|---|---|
| change_id, project_id, base_project_revision_id | string | IDs estáveis; base obrigatória |
| base_package_ref | PackageRef ou null | Base exata se já há pacote |
| operations | array de ChangeOperation | Pelo menos uma; ordem preservada |
| requested_by | string | Identidade do proponente, não autoridade de aprovação |
| reason | string | Obrigatório e não vazio |
| policy_revision | string | Política exata na elaboração |
| ChangeOperation/type | enum `source_add`, `source_update`, `source_withdraw`, `source_revoke`, `course_edit`, `page_edit`, `skill_request`, `policy_change`, `decision_correct`, `conflict_record` | Remoção física de arquivo não vira withdraw automaticamente |
| ChangeOperation/target_id | string | ID estável de entidade existente, exceto criação |
| ChangeOperation/expected_hash | string ou null | Null só em criação; protege contra base divergente |
| ChangeOperation/payload | objeto validado por type | Não permitir patch JSON arbitrário em policy, approvals ou active pointer |

`ImpactReport` exige `change_id`, `base_project_revision_id`, `classification:factual|conceptual|editorial|mixed|unknown`, `affected_nodes:array[string]`, `required_checks:array[string]`, `blockers:array[{code,message,target_id:null|string}]`, `existing_conceptual_report_ref:null|string`, `unknown_dependencies:boolean`. Se unknown_dependencies=true, exigir revisão ampla dos entregáveis dependentes em vez de afirmar ausência de impacto.

`DependencyGraph` usa nós `{id,kind,revision,hash}` (todos strings; kind enum `source_revision`, `claim`, `rag_document`, `skill`, `lesson`, `page_section`, `decision`) e arestas `{from,to,relation}`; relation enum `supports`, `derived_from`, `depends_on`. Convenção: `from` é o dependente, `to` a dependência. Impacto propaga no sentido inverso das arestas. IDs/revisões inexistentes são erro; ciclos de dependência editorial são rejeitados com lista de nós. Relações de evidência que precisem ciclos conceituais devem ser representadas por conflito, não dependência circular.

| Evento | RAG | Skill/router | Curso/página | Gates |
|---|---|---|---|---|
| Adicionar fato admissível sem dependentes conceituais | Reconciliar e indexar candidata/snapshot adequado | Avaliar impacto existente; nenhum rebuild automático se impacto vazio comprovado | Revalidar nós dependentes, se houver | Direitos, privacidade, avaliação e autoridade |
| Mudar definição/regra de decisão | Atualizar evidência | Candidata de enriquecimento externo e avaliação | Revalidar aulas/alegações dependentes | Revisão conceitual manual |
| Revogar fonte | Excluir da recuperação ativa e invalidar snapshots/sessões conforme contrato | Invalidar derivados até revisão | Suspender alegações/aulas dependentes ou substituir evidência | Revogação urgente não espera lote de orçamento; não reativar por rollback |
| Reordenar módulos sem mudar conteúdo factual | Sem mudança | Sem mudança, salvo referência explícita | Nova revisão de curso | Integridade de pré-requisitos e revisão editorial |
| Alterar preço/garantia/CTA | Sem mudança por padrão | Sem mudança | Nova revisão de página e decisões | Confirmação comercial explícita; nenhuma inferência automática |
| Alterar perfil de embedding | Full rebuild | Revalidar router/integração | Não regenerar copy sem dependência | Golden nativo, snapshot compatível e promoção segura |
| Correção de decisão de público/região | Reavaliar filtros/escopo | Reavaliar regras dependentes | Revisar curso/página afetados | Reabrir decisões e invalidar aprovação obsoleta |

Etapas de progresso da proposta são recibos append-only `proposed`, `prepared`, `activation_pending`, `activated`, `failed`, `cancelled`; esses nomes **não** são estados alternativos da candidata. O status editorial é sempre consultado no lifecycle canônico. Uma tentativa failed pode originar novo recibo de preparação com mesma proposta se a base continuar válida; alterações na proposta exigem novo change_id.

## 6. Ativação, idempotência e concorrência

Toda mutação nova recebe `{idempotency_key:string, expected_revision:integer, payload:object}`. A chave é única por projeto e operação; mesmo payload normalizado retorna o mesmo resultado, mesmo após restart. Chave igual com payload diferente retorna `IDEMPOTENCY_CONFLICT`. O registro de intenção e recibo deve ser durável; timeout não comprova que o efeito não ocorreu.

Usar single-writer e lease existentes; não adquirir locks em ordem inversa. Ordem proposta de coordenação: projeto, depois pacote pelo contrato público suportado; não segurar lease de pacote durante chamada de LLM ou espera humana. Preparação gera candidata/revisão imutável fora da troca de ponteiro. No commit, revalidar base do projeto, pacote, política, revogações, avaliações e aprovações. Base divergente exige nova análise, não sobrescrita.

Como projeto e pacote têm arquivos distintos, não prometer atomicidade multiarquivo apenas com dois renames. Registrar intenção de ativação com base, destino, hashes e idempotency key antes de publicar. Usar a promoção recuperável existente do pacote; só depois escrever ponteiro do projeto e recibo final. Após crash entre as duas etapas, a primeira operação pública executa recuperação: se o recibo editorial prova sucesso e todas as referências continuam válidas, conclui o ponteiro; se a promoção não ocorreu, conserva a base. Se evidências divergem ou foram revogadas, bloquear e recuperar via operação validada; nunca inventar recibo ou servir composição híbrida.

Leitura de projeto exige correspondência entre revisão ativa e release/composition hash. Durante recuperação incompleta, mantém geração anterior somente se o backend e sessão a suportarem validamente; caso contrário, retorna `RECOVERY_REQUIRED`. A restrição atual de publicação concorrente com reader permanece. Não liberar leitura histórica revogada por estar pinada.

Mudança apenas editorial ativa nova revisão referenciando exatamente o mesmo PackageRef, sem republicar pacote. Rollback de projeto usa revisão histórica exata e chama rollback de pacote existente se a geração mudou; valida índice, direitos, revogações e decisões atuais antes de atualizar o ponteiro. Um histórico não constitui autorização permanente.

### Envelope de resultado novo

`{schema_version:1, ok:boolean, operation_id:string, project_id:null|string, session_revision:null|integer, outcome:applied|unchanged|needs_input|blocked|failed, data:object|null, errors:array[{code:string,message:string,retryable:boolean,field:null|string}], next_actions:array[string]}`. Dados sensíveis são minimizados antes de persistir/imprimir. Sem retorno parcial de segredo na mensagem de erro.

CLI proposta: exit 0 para applied/unchanged; 2 para needs_input; 3 para blocked; 1 para failed. Esses códigos pertencem aos comandos novos; não alterar códigos existentes de OperationResult. `status` bem-sucedido retorna 0 mesmo que projete pendências no data.

| Código | Condição | Recuperação |
|---|---|---|
| `INVALID_INPUT` | Tipo, enum, referência ou chave desconhecida | Corrigir payload; não retry automático |
| `UNSUPPORTED_SCHEMA_VERSION` | Versão futura ou migração não suportada | Atualizar leitor/migrador; preservar estado |
| `STALE_REVISION` | CAS/base divergiu | Recarregar, mostrar diff e repropor |
| `IDEMPOTENCY_CONFLICT` | Mesma chave, payload diferente | Usar nova chave após inspecionar efeito anterior |
| `LEASE_BUSY` | Outro escritor válido | Retry limitado com backoff/jitter; sem roubar lease |
| `DECISION_REQUIRED` | Decisão de produto necessária ao efeito | Manter draft privado; obter resposta |
| `RIGHTS_BLOCKED` / `PRIVACY_BLOCKED` | Uso não concedido/classificado | Revisar evidência e finalidade; não presumir autorização |
| `DEPENDENCY_UNKNOWN` | Mapa insuficiente para limitar impacto | Revisão ampliada e completar dependências |
| `EVIDENCE_STALE` / `SOURCE_REVOKED` | Base/evidência mudou ou revogou | Reavaliar; bloquear publicação/rollback inválido |
| `RECOVERY_REQUIRED` | Commit interrompido/inconsistente | Inspecionar recibos e recuperar antes de mutação |
| `FEATURE_NOT_ENABLED` | trusted_factual sem implementação/autoridade | Permanecer manual |

Erros do lifecycle existente são preservados como causas estruturadas, sem renomear seu significado nem convertê-los em sucesso. Retry aplica-se a falhas transitórias, com orçamento; decisão de produto e licença desconhecida não se resolvem esperando.

## 7. Migração e compatibilidade

1. Inventariar schemas, pacote e revisões existentes somente leitura. Gerar plano com hashes e campos que não podem ser inferidos. Não converter conteúdo do AGENTS em verdade comercial sem revisão.
2. Criar Project v1 privado que referencia a release atual verificada. Migrar dados explícitos do brief; ausências viram decisões pending. Registry v1 permanece intacto, overlays começam conservadores.
3. Gerar revisão de projeto em staging, validar contratos/links/hashes e persistir recibo de migração. Sem alteração do índice ou criação de aprovação editorial.
4. Commit atômico do novo ponteiro somente após validação. Interrupção permite retomar pela idempotency key. Segunda execução idêntica é unchanged.
5. Manter leitores legados do pacote funcionais e wheel compatível. Novo consumidor rejeita versão desconhecida sem editar arquivos. Rollback da migração remove apenas o ponteiro novo de forma controlada; não apaga pacote nem prova histórica.
6. Documentar migrações v1→v2 separadamente se forem necessárias. Não reutilizar `schema_version:1` para mudar significado de campo publicado.

## 8. Cenários de contrato para TDD e handoff

Estes são critérios para futuros testes, não testes já escritos:

1. Start, duas respostas, encerrar processo e status por CLI: conserva valores, revisão e pendências; finalize privado não cria publicação.
2. Duas respostas concorrentes na mesma revisão: uma aplica, outra retorna STALE_REVISION sem perder valor; repetição idêntica retorna mesmo recibo.
3. Frase ambígua de curso + preço desconhecido: mapa provisório é possível; ativação comercial retorna DECISION_REQUIRED e nenhum CTA/preço fabricado.
4. Fonte com direitos internos permitidos e redistribuição negada: consulta admissível conforme gates, página não pode incluir transcrição; timestamps continuam rastreáveis internamente.
5. Mudança factual com lição dependente: impacto inclui lição, mesmo sem mudança conceitual global; desconhecimento do grafo não vira “zero impacto”.
6. Nova seção editorial sem fatos novos: revision_id muda, release_id/composition hash do pacote não mudam.
7. Revogação após aprovação: publicação e rollback que reintroduziriam a fonte falham; histórico permanece auditável.
8. Crash após promoção de pacote, antes do ponteiro: restart recupera vínculo exato ou bloqueia; não entrega página de uma revisão com RAG incompatível.
9. Migração repetida e versão futura: primeira é idempotente, segunda recusa escrita e preserva bytes originais.
10. Fixture de schema inválido e wheel instalado: ambos rejeitam a mesma entrada; comandos da documentação aparecem no help e o perfil MCP fica explicitamente separado quando o runtime não está instalado.

Usar a seam raiz/CLI como primeira escolha. Fixtures locais controlam fonte, tempo e autoridade; MCP real é necessário para testar consistência efetiva de índice, sessões e rebuild. O implementador deve adicionar uma fatia de comportamento por vez seguindo o TDD acordado, demonstrar a falha antes da implementação e registrar o resultado nos tickets.
