# Cartões de comando e recuperação

Use estes cartões para escolher uma operação sem transformar um comando de
diagnóstico em mutação. Os exemplos assumem que `<package>` é um pacote DOCOPS
válido e que `<runtime>` fica fora da árvore publicada.

## Diagnóstico e geração

| Comando | Efeito | Saída/guarda |
|---|---|---|
| `docops doctor --json` | Somente leitura do checkout | `ok=false` exige corrigir o ambiente antes de gerar |
| `docops resolve <source> --json` | Resolve nome/URL/repo/pasta sem adquirir | Código 2 significa ambiguidade ou decisão necessária |
| `docops plan <source> --output <package> --license <id> --json` | Planeja sem escrever artefatos ativos | Inspecionar blockers, diff e readiness |
| `docops run ...` | Staging, validação e promoção transacional | Falha preserva a geração ativa; `--index-rag` é explícito |
| `docops validate <package> --json` | Valida contrato e estado do pacote | Não prova qualidade da resposta do harness |
| `docops skill path --json` | Localiza a skill operacional instalada | Somente leitura; use o caminho retornado no harness |
| `docops agents-bootstrap --root <project> --json` | Instala regra idempotente no `AGENTS.md` | Preserva regras existentes; `--check` não escreve |

## Atualização factual

```text
docops lifecycle source register \
  --package <package> --source-id docs-main \
  --canonical <source> --owner <operator>

docops lifecycle source reconcile \
  --package <package> --snapshot <acquisition-snapshot.json>

docops lifecycle worker run --once --queue <queue.sqlite>
```

Precondições: origem autorizada, escopo definido e snapshot completo. O
`reconcile` calcula add/update/remove e cria evento; o `work` processa a fila.
Colocar um arquivo no filesystem sem reconciliar não altera o RAG.

Resultados esperados:

- `corpus-ready`: conteúdo e metadados preparados, mas backend ainda não
  comprovado;
- `indexed`: indexação real confirmada pelo MCP;
- `failed`, `blocked` ou `retry_wait`: ler `error_code`, corrigir a causa e
  reprocessar somente quando a falha for recuperável.

Uma aquisição parcial, timeout, `robots.txt` ou erro de rede não autoriza inferir
remoção. Faça nova reconciliação completa antes de aceitar um `remove`.

## Candidata conceitual

```text
docops package run <source> --output <package> \
  --mode update --publication-policy candidate --license <id>

docops lifecycle candidate enrichment-request \
  --package <package> --candidate-id <id>

docops lifecycle candidate enrich \
  --package <package> --candidate-id <id> \
  --skill-root <external-skill> --tool book-to-skill --version <version>

docops quality evaluate \
  --package <candidate-package> --cases <reviewed-golden.json> --adapter memory

docops lifecycle candidate approve \
  --package <package> --candidate-id <id> \
  --actor <id> --role human_approver

docops lifecycle candidate publish \
  --package <package> --candidate-id <id>
```

A avaliação deve declarar a composição que realmente foi avaliada. Qualquer
alteração no corpus, skill, router, política ou backend invalida a aprovação.
Não mantenha lease enquanto espera o harness ou uma pessoa. Se a base avançar,
espere `stale_base`/`approval_invalidated`, reprepare e reavalie.

Para desfazer uma publicação, use rollback auditado:

```text
docops lifecycle candidate rollback \
  --package <package> --release-id <release-id>
```

Rollback não reativa fonte revogada nem promete que um índice incompatível será
consultável sem rebuild.

## Aprendizado de conversa

```text
docops lifecycle learning submit \
  --package <package> --proposal <proposal.json> --capture-opt-in

docops lifecycle learning review \
  --package <package> --proposal-id <id> \
  --decision admit --actor <id>
```

`submit` sempre cria quarentena. `admit` não publica sozinho: uma candidata
precisa materializar a alegação, ser avaliada e publicada. Opiniões,
preferências, segredos e claims sem evidência independente permanecem fora do
corpus compartilhado.

## Feedback e investigação

```text
docops lifecycle feedback submit \
  --package <package> --feedback <feedback.json>

docops lifecycle feedback report --package <package> --window-days 7
docops lifecycle status --package <package>
```

Tipos válidos são `unanswered`, `conflict`, `low_quality`, `citation` e
`abstention`. O mesmo caso repetido por três ocorrências em sete dias abre uma
investigação; feedback não altera skill, Golden ou RAG por si só.

## Reindexação e embedding

Uma mudança em modelo, perfil, dimensão, prefixo ou configuração de chunk que
afete vetores exige rebuild completo do backend. Não publique um `indexed` com
um `index_revision` misturado. Use o MCP local ou o fluxo de manutenção do
operador, registre a nova composição e execute avaliação comparável.

## Checklist de encerramento

1. Ler o JSON terminal inteiro, incluindo `outcome`, `errors`, readiness e
   revisões.
2. Confirmar que a geração ativa não mudou quando a operação era candidata.
3. Confirmar fonte canônica, versão, idioma, licença e hashes.
4. Registrar citação, métricas, falhas e decisão humana pendente.
5. Remover somente resíduos expirados com `docops cleanup`; não apagar runtime,
   corpus privado ou backups sem política autorizada.
