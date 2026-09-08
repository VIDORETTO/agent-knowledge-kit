# Especificação complementar — fontes, recuperação e avaliação

Status: contrato implementado localmente nesta execução. Não indexar o corpus real ao executar estes tickets; a evidência fica em [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md), enquanto esta especificação define os limites de qualidade e as fronteiras externas.

## Registro de fontes e afirmações

Preservar source_id e revisões existentes. Adicionar o overlay SourceGovernance definido em STATE-CONTRACTS, sem substituir o registry v1: organização/autor/canal; tipo documental; published_at e captured_at; language BCP-47; region; vigência; próxima revisão; autoridade declarada e evidência de verificação. Timestamps são UTC RFC3339; publicação admite YYYY-MM-DD com published_precision=date. Datas desconhecidas são null, nunca data de captura usada como data de publicação. Permissões seguem UseGrant por finalidade; a migração não infere direitos dos textos legados.

Direitos devem separar permissão de aquisição, armazenamento privado, indexação, geração derivada, citação e redistribuição. Cada permissão tem allowed/denied/unknown, evidência, responsável e validade. unknown não é autorização. Uma licença identificada não substitui a política de uso pretendido. Privacidade identifica classificação, consentimento quando aplicável, retenção e destinos permitidos. Metadados sensíveis ficam fora de relatórios públicos.

Estado editorial da fonte: active, archived ou revoked. Compatibilidade com withdrawn existente deve ser definida na migração: withdrawn permanece não elegível; não converter automaticamente para archived consultável. Arquivada sai da consulta padrão, podendo aparecer apenas em modo histórico explícito e ainda sujeito a direitos. Revogada nunca é recuperada, mesmo em reader antigo.

Classificação no nível de afirmação/trecho: official_rule, factual_observation, opinion, experience, hypothesis, recommendation. Uma fonte pode conter mais de uma classe. Confiança não é uma única nota capaz de transformar opinião em regra. Guardar claim_id, source_revision, localizador, escopo/região/vigência e status de revisão. Atribuição feita pelo harness é proposta até validação/revisão requerida.

Conflito: conflict_id, claim_ids, relação (contradicts/supersedes/scope_difference), descrição, status (open/resolved), decisão e evidências. Uma regra mais recente só substitui outra quando a vigência e o escopo forem compatíveis; documento mais novo pode estar descrevendo uma regra antiga.

## Aquisição e transcrições

Reusar aquisição web/repositório/local e limites existentes. Todo conteúdo é dado não confiável; instruções encontradas em fontes não executam comandos, aprovam candidatas ou mudam políticas. Validar URL/redirect/DNS, tipo real, limites de bytes/tempo/quantidade, symlinks e caminhos. Aquisição incompleta ou timeout não prova remoção: reconcile conserva a última observação válida e informa falha.

MVP de vídeo: receber transcrição Markdown produzida externamente e autorizada. Guardar video_id/origem, canal, data de captura, idioma, método (manual/automático/externo), checksum, licença/permissão e segmentos com start_ms/end_ms. Validar start >= 0, end > start, ordem e duração quando conhecida. Ausência de timestamp permite documento textual explicitamente sem localização temporal; não fabricar timestamp.

Não criar downloader nem scraping autenticado de YouTube no MVP. SRT/VTT nativos são extensão posterior, não pré-requisito para fonte de vídeo. Resumo é derivado com lineage próprio; não presumir que resumir remove restrições de uso. Fixture licenciada/sintética basta para teste de integração. Revisão de direitos de fontes reais é tarefa do responsável; o software registra decisões, não emite parecer jurídico.

## Consulta global governada

O universo é todas as fontes elegíveis da revisão de projeto, não todos os arquivos do computador ou todos os projetos do backend. Buscar lexical + semântico nesse universo. Preservar source_id, source_revision, document_id, chunk_id, project_id e localizador de seção/linha/página/tempo. Uma citação fixa versão e resolve no documento exato; scores não substituem evidência.

Filtros públicos implementados: theme, source_kind, claim_type, authority, region, as_of e faixa de publicação. Validar enum/data e retornar filtro inválido como erro, nunca ignorá-lo. Aplicar elegibilidade antes do ranking quando o backend permitir. Quando não permitir, recuperar em lotes limitados com pós-filtro e informar limite/insuficiência; nunca preencher top-k com fonte proibida. Reaplicar revogação antes de retornar e em cache. Cache inclui projeto, composição, filtros, snapshot e revisão da política/revogação.

Pergunta normativa exige fonte oficial verificada, ativa e compatível com região/vigência. Se só houver influencer, retornar insufficient_evidence com o material identificado como opinião; não promover a opinião a regra. Consulta estratégica pode apresentar experiências diversas e condições de aplicação. Conflitos abertos devem aparecer próximos das afirmações afetadas. Data/região ausente não ganha prioridade de norma vigente.

Contrato de evidência implementado no resultado: outcome = supported | conflicting | insufficient_evidence; evidence[] com fonte/revisão/localizador/classe; conflicts[]; applied_filters; limitations; snapshot identity. DOCOPS fornece evidência e resultado determinístico de elegibilidade; o harness redige a resposta e cita cada afirmação verificável. Não adicionar geração textual interna.

Atualidade depende da fonte: frequência é configurável pelo responsável, não um TTL universal que declara informação falsa. Fonte atrasada recebe stale; em perguntas normativas sensíveis stale bloqueia confiança automática conforme política. Falha de captura gera alerta de frescor, não exclusão silenciosa.

## PT-BR e integridade de índice

Usar perfil multilingual para o piloto PT-BR e comparar com compact em fixtures equivalentes. Não mudar o default global sem evidência para outros domínios. Alteração de perfil/modelo/dimensão/tokenizer/chunking relevante cria fingerprint novo e exige rebuild completo em staging. Preservar snapshot ativo até avaliação e promoção. Falha de download, espaço ou rebuild mantém release e readers anteriores utilizáveis.

Não prometer vantagem do perfil sem benchmark local. Medir qualidade e tempo com versão exata do modelo, corpus, configuração, hardware e cache frio/quente. Reranker só entra se ganho medido justificar custo; não habilitar por estética arquitetural.

## Golden Set revisado

MVP: 60 casos revisados, 40 PT-BR, 10 em espanhol e 10 em inglês. Distribuição primária: 18 lookup/normativos, 12 estratégias/diagnóstico, 8 conflitos, 8 frescor/região, 8 revogações e 6 sem resposta. Usar rótulos secundários para cobrir cada tema do preset sem duplicar artificialmente contagens. Realizar corpus sintético autorizado primeiro; depois casos reais do vendedor sobre fontes aprovadas. Separar conjunto de ajuste e holdout; toda métrica informa qual conjunto foi usado.

Cada caso contém id, pergunta, intenção, região/data de referência, fontes/revisões e trechos esperados, outcome esperado, citações válidas, fontes proibidas, justificativa de referência, reviewer, reviewed_at e versão. Sem evidência/revisão, caso fica candidate e não habilita publicação. O mesmo harness não aprova sozinho sua própria resposta como referência independente.

Aceites iniciais propostos (revisáveis antes do piloto, nunca reduzidos só para fazer teste passar): Recall@5 >= 0,90 e MRR@5 >= 0,75 global; Recall@5 >= 0,85 em cada idioma; zero vazamento de fonte revogada/outro projeto; 100% dos casos críticos normativos/conflito/região/abstenção com outcome correto; zero citações quebradas; cobertura de citações >= 0,95 das afirmações factuais revisadas; nenhuma regra comercial inventada. Informar numerador/denominador por fatia. Amostras pequenas são smoke, não prova estatística de qualidade geral.

Reusar evaluation receipts com identidade exata; estender dimensões, não substituir Recall/MRR por avaliação subjetiva. Avaliação de resposta usa harness externo com receita e revisão independente; falha/indisponibilidade de harness produz pending/failed, nunca sucesso simulado. Comparar candidata e baseline com o mesmo Golden; nenhuma regressão em caso crítico é admissível.

## Publicação e autonomia

Política padrão: revisão manual. Automação factual futura exige consentimento explícito com escopo/projeto/fontes/ações, prazo, responsável, limites e revogação. Além de avaliação verde: fonte confiável verificada, direitos vigentes, nenhum conflito aberto, nenhuma mudança conceitual, nenhuma alteração de curso/página/claims comerciais, nenhuma escalada de privacidade ou região, diff abaixo dos limites aprovados. Violações criam candidata bloqueada para revisão. Não basta passar --yes nem reutilizar recibo de outra candidata.

Permissões automáticas só produzem recibo válido vinculado a hash da candidata/política/avaliação usando o motor existente. Revalidar tudo no instante de promoção para evitar corrida entre avaliação e revogação. Manter kill switch e registrar motivo de cada decisão sem copiar conteúdo privado aos logs.

## Operação verificável

Primeiro usar supervisor externo chamando reconcile e worker run --once, com configuração e instalação explícitas. Adicionar inspeção de status antes de instalar serviço: last_reconcile, last_success, oldest_pending_age, running_age, retries, blocked_jobs, disk_available, index_fingerprint, snapshot, stale_sources e pending_review. Alertar apenas transições acionáveis e deduplicar por incidente; não enviar mensagens externas sem configuração autorizada.

Defaults propostos do piloto: reconcile a cada 15 minutos; alerta após 2 ciclos perdidos; polling worker a cada 60 segundos. São parâmetros operacionais, não garantia de freshness das normas. Medir latência de busca p50/p95 e tempo de indexação; estabelecer SLO com corpus/hardware reais antes de declarar escala.

Backup consistente: parar novas claims, concluir ou registrar operação recuperável, copiar registros/versionamento/recibos/queue e snapshot referenciado como unidade, com checksum e política de retenção. Segredos e dados privados em armazenamento autorizado. Restore em diretório isolado deve preservar revogações e impedir reexecução de efeitos já confirmados; nunca restaurar somente o índice e perder tombstones. Proposta RPO 24h e RTO 2h deve ser demonstrada em ensaio antes da adoção.

Multi-host é futuro: somente após métricas mostrarem limite local. Exige store transacional compartilhado, fencing, autorização entre hosts e estratégia de índice; SQLite local não vira fila distribuída por compartilhar arquivo na rede.
