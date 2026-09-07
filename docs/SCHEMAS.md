# Contratos JSON

Os arquivos em `schemas/` são versões públicas e o `manifest.json` sempre
declara `schema_version`. Campos desconhecidos podem ser adicionados de forma
aditiva; remover ou mudar o significado de um campo exige nova versão.

- `manifest.schema.json`: fonte, proveniência, entradas, artefatos,
  checkpoints, métricas, avisos e erros;
- `harness.schema.json`: skills e registro MCP relativo;
- `golden.schema.json`: conjunto revisado de perguntas e origem esperada;
- `validation.schema.json`: resultado do validador de pacote.
- `plan.schema.json`: plano imutável, diff, blockers e fingerprints;
- `result.schema.json`: projeção terminal de `apply`, incluindo outcome e exit code;
- `outcome.schema.json`: autoridade terminal compartilhada por manifesto e resultado;
- `evaluation.schema.json`: métricas, casos, thresholds e procedência do adapter;
- `evaluation-receipt.schema.json`: julgamentos independentes de suporte e
  citação vinculados à geração, candidata e revisões exatas;
- `golden-candidates.schema.json`: candidatos explicitamente ainda não revisados;
- `approval.schema.json`: autorização explícita, escopo, base e hashes exatos
  de uma candidata;
- `publication.schema.json`: recibo factual da promoção transacional de uma
  candidata aprovada.
- `history.schema.json`: geração editorial retida, sua composição, compatibilidade
  de índice e estado de revogação;
- `rollback.schema.json`: evento factual de restauração de uma geração retida.
- `source-registration.schema.json`: identidade cadastrada, escopo, versão,
  direitos, privacidade e autoridade de uma fonte;
- `acquisition-snapshot.schema.json`: observação versionada de uma fonte,
  incluindo escopo e completude da aquisição.
- `event.schema.json`: entrega idempotente de uma observação de mudança para a
  fila local.
- `job.schema.json`: projeção pública de trabalho coalescido, prazo, estado,
  tentativas e arquivos concluídos/adiados.
- `rag-authorization.schema.json`: autorização persistida, com pacote, revisão,
  política e ator exatos, exigida antes de indexar RAG.
- `job-receipt.schema.json`: recibo durável do efeito aplicado por um job,
  usado para reconciliar retomadas sem repetir efeitos.
- `conceptual-impact.schema.json`: cursor de impacto líquido, documentos
  afetados, lote conceitual, backlog de orçamento e revogações.
- `reader-session.schema.json`: sessão de consulta pinada a um `release_id`,
  permissões somente leitura, expiração, revogação e capacidade do backend.
- `reader-query.schema.json`: resultado de uma chamada de leitura vinculada à
  sessão, à geração exata e ao cache dessa composição.
- `rag-snapshot.schema.json`: inventário relocável por hash do corpus, embedding
  e artefatos lógicos do backend.
- `rag-reuse-plan.schema.json`: decisão explícita entre reuso incremental e
  full rebuild, com contagens, caminhos alterados e preservação da ativa.
- `rag-profile-comparison.schema.json`: comparação preparatória de perfis de
  embedding, exigência de avaliação Golden nativa e bloqueio de publicação até
  full rebuild/evidência.
- `learning-proposal.schema.json`: alegação minimizada, escopo, privacidade,
   evidências e estado de quarentena de uma proposta derivada de conversa.
- `learning-review.schema.json`: decisão explícita, ator, evidência filtrada,
   derivados e bloqueio de publicação/rollback de uma proposta.
- `feedback.schema.json`: sinal de uso redigido, hashes da pergunta/geração,
   métricas mínimas e identidade de ocorrência.
- `feedback-report.schema.json`: agregação pública por janela, custo/latência,
   denominadores, comparabilidade e guardas de não mutação.
- `investigation.schema.json`: investigação derivada de ocorrências recorrentes
   e sua candidata Golden ainda não revisada.

O validador Python é a seam executável usada pelos testes; os schemas tornam o
contrato inspecionável por ferramentas externas sem executar o servidor. A
fonte normativa única é `schemas/`; o mesmo conjunto é reproduzido em
`docops/schemas/` por `scripts/sync_schemas.py`, para que o wheel não dependa
do checkout. `scripts/check_contracts.py` verifica exemplos válidos, mutações
negativas, versão/política e drift de conteúdo entre as duas cópias.
