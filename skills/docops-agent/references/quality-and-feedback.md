# Qualidade, feedback e avaliação

Feedback prioriza investigação; não altera conhecimento, Golden Set ou skill
automaticamente. Toda métrica deve ser identificada por corpus, índice,
embedding, router, harness, top-k e conjunto de casos.

## Sinais operacionais

```text
unanswered  → nenhum trecho sustenta a pergunta
conflict    → fontes válidas discordam
low_quality → resultado irrelevante ou resposta infiel
citation    → citação ausente, inválida ou insuficiente
abstention  → agente recusou; verificar se era justificável
```

Registre a geração e um `occurrence-id`; não envie o texto integral da consulta
quando um hash for suficiente.

```text
docops lifecycle feedback submit \
  --package <package> --kind citation --generation <release-id> \
  --occurrence-id <case-id> \
  --payload-json '{"source":"path#section","reason":"locator_missing"}'
```

Três ocorrências independentes do mesmo sinal em sete dias abrem investigação.
Isso é um gatilho, não uma prova de regressão.

## Golden e métricas

Use casos revisados separados em ajuste e avaliação. Relate:

- Recall/Hit@k, MRR@k e Precision@k da recuperação;
- fidelidade, correção e cobertura de citações da resposta final;
- abstention correta, falsa abstention e resposta indevida;
- p50/p95 de busca, fila, indexação e publicação;
- custo de CPU, RAM, disco, tokens externos e minutos de revisão.

Denominador zero é `not_applicable`, não 100%. Não compare números de perfis,
corpora ou top-k diferentes como se fossem uma regressão.

Após reindexação significativa, mudança de parser/chunker/embedding, upgrade do
backend ou reclamação de qualidade:

1. capture `get_index_stats`/`docops evaluate`;
2. execute o mesmo Golden revisado e registre a composição;
3. compare com baseline da mesma configuração;
4. investigue divergências e citações antes de alterar thresholds;
5. só então prepare candidata ou novo caso Golden.

O Golden gerado pelo DOCOPS é não revisado. O agente nunca deve promovê-lo
automaticamente por ter sido gerado a partir dos próprios documentos.
