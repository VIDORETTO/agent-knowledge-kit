# Estado da implementação contínua

Status da branch: **piloto implementado e verificável em `feat/continuous-knowledge`**.

Este documento separa o que foi observado no checkout e executado em testes do
que continua sendo uma limitação ou uma integração externa. A especificação
normativa permanece em [SPEC.md](SPEC.md); este arquivo não transforma uma
proposta em garantia de produção.

## Resumo executivo

O piloto agora possui um ciclo seguro e compatível com o DOCOPS existente:

1. uma fonte é registrada, reconciliada e transformada em eventos idempotentes;
2. o RAG pode ser atualizado de modo incremental, com reconstrução completa
   automática quando o perfil de embedding muda;
3. mudanças conceituais, enriquecimentos externos e aprendizado de conversas
   entram em candidata, nunca substituem a geração ativa silenciosamente;
4. avaliação, aprovação explícita, publicação, pin de geração, rollback e
   revogação deixam evidência auditável;
5. leitores MCP recebem sessão somente leitura e rejeitam mudança de geração;
6. a política de gatilhos agrupa mudanças antes de solicitar novo fold-in da
   skill, preservando o harness externo e o modelo externo.

O que não está fingido como pronto: fila distribuída, scheduler gerenciado,
snapshot transacional entre processos externos, OCR/ASR/vídeo nativos e
avaliação de fidelidade feita pelo próprio DOCOPS. Esses itens continuam sendo
integrações ou decisões operacionais do ambiente consumidor.

## Matriz de tickets

| Ticket | Estado no piloto | Evidência pública |
|---|---|---|
| T01 | implementado | `record_skill_enrichment`, guarda contra sobrescrita |
| T02 | implementado | `docops/revisions.py`, manifest e receipts |
| T03 | implementado | sincronização RAG incremental preservando skill |
| T04 | implementado | `prepare_candidate` |
| T05 | implementado | profile/rebuild e diagnóstico de sync |
| T06 | implementado | `submit_enrichment` com allowlist, hash e receipt |
| T07 | implementado como contrato | `evaluate_candidate` aceita receipt externo validado |
| T08 | implementado | aprovação por papel e publicação de hashes |
| T09 | implementado | histórico, rollback e bloqueio por revogação |
| T10 | implementado | registro/reconciliação/revogação de fontes |
| T11 | implementado | SQLite WAL, idempotência e debounce |
| T12 | implementado como worker local | claim, lease, retry, `work --loop` |
| T13 | implementado | política de lote e backlog explicável |
| T14 | implementado | harness/readers pinados e MCP read-only |
| T15 | parcial | o rebuild seguro existe; snapshot distribuído ainda é pendente |
| T16 | implementado no normalizador | idioma, páginas, slides, tabelas e seções |
| T17 | implementado como quarentena | proposta revisada; nenhum auto-admit de conversa |
| T18 | implementado como sinalização | feedback agregado e jobs de investigação |

“Implementado como contrato” significa que o DOCOPS valida e registra a
evidência recebida; a produção dessa evidência continua sendo responsabilidade
do harness/evaluador autorizado. “Parcial” significa que o caminho conservador
está disponível, mas uma otimização ainda não está habilitada.

## Comandos públicos do ciclo

Todos os comandos usam um pacote já gerado e um runtime privado ao lado dele.
Os caminhos de runtime não fazem parte do pacote publicado.

```text
python -m docops lifecycle status --package <package>
python -m docops lifecycle source register --package <package> --source-id <id> --canonical <url-or-path>
python -m docops lifecycle source reconcile --package <package> --source <source> --source-root <dir>
python -m docops lifecycle event submit --package <package> --event-id <id> --type document.changed ...
python -m docops lifecycle work --package <package> [--force] [--loop --interval-seconds 5]
python -m docops lifecycle candidate prepare --package <package> --source <source> --source-root <dir>
python -m docops lifecycle candidate enrichment-request --package <package> --candidate-id <id>
python -m docops lifecycle candidate enrich --package <package> --candidate-id <id> --skill-root <dir> ...
python -m docops lifecycle candidate evaluate --package <package> --candidate-id <id> --evidence-json <json>
python -m docops lifecycle candidate approve --package <package> --candidate-id <id> ...
python -m docops lifecycle candidate publish --package <package> --candidate-id <id>
python -m docops lifecycle candidate rollback --package <package> --release-id <id>
python -m docops lifecycle learning submit/review/revoke --package <package> ...
python -m docops lifecycle feedback submit/status --package <package> ...
```

O `work` é deliberadamente foreground e local. Um scheduler pode invocá-lo,
mas o pacote não instala cron, serviço ou fila externa por conta própria.

## Política efetiva de atualização

- **RAG:** após evento admitido, em job explícito, incremental quando possível.
  `--index-rag` continua opt-in. Alteração do perfil de embedding força
  `full_rebuild=True`.
- **Skill:** não é atualizada por cada upload. Um lote conceptual dispara
  `skill.enrichment.requested` quando atinge 10 documentos, 3 documentos e
  pelo menos 10% do corpus, 20.000 caracteres, 24 horas ou quatro sinais
  relevantes no dia. Conflito e revogação geram investigação imediata.
- **Router/metadados:** são regenerados junto da candidata/publicação; o
  router ativo não muda durante a preparação.
- **Golden Set:** não é alterado automaticamente. Feedback apenas prioriza
  investigação; casos novos exigem curadoria.
- **Conversas:** apenas propostas estruturadas, com evidência e privacidade
  `shared`, podem ser materializadas numa candidata. Opinião, resposta do
  agente sem fonte, segredo ou dado privado fica fora do corpus compartilhado.

## Segurança e limites conhecidos

- Artefatos de skill aceitos no enriquecimento são Markdown regular dentro de
  `skill/`, sem symlink, com limite de 4 MiB; a origem não pode estar dentro da
  candidata.
- Receipts e hashes ligam a candidata à composição avaliada. Publicação exige
  aprovação; rollback recusa uma geração que dependa de proposta revogada.
- Fontes revogadas recebem tombstone em `.docops/revocations.json` e são
  filtradas pelo leitor; remoção física/expurgo permanece uma política de
  retenção do operador.
- O MCP de consulta opera em modo read-only e não aceita mutações nessa sessão.
- O corpus não é uma autorização de execução: prompt injection, copyright,
  credenciais, dados pessoais e licença ainda exigem triagem humana.
- A correspondência de revogação para fontes locais redigidas (`file://local`)
  usa um fallback conservador limitado ao pacote; múltiplos registros locais
  exigem reconciliação explícita.

## Verificação reproduzível

Na raiz do checkout:

```text
PYTHONPATH=. ./.venv/bin/ruff check docops tests skills/vendor/knowledge-rag/mcp_server
PYTHONPATH=. ./.venv/bin/pytest -q
PYTHONPATH=. ./.venv/bin/python -m docops doctor --json
git diff --check
```

Os números de Recall/MRR, faithfulness, custo e latência devem ser publicados
com corpus, perfil, versão e Golden Set identificados. O DOCOPS registra
receipts externos; ele não inventa uma medição quando o harness não a forneceu.

## Próximos gates antes de produção ampla

1. executar o fluxo com o MCP/embedding realmente usado pelo consumidor;
2. definir retenção, backup e isolamento do SQLite runtime;
3. escolher scheduler/fila e política de concorrência fora do pacote;
4. validar licenças e privacidade de cada corpus real;
5. aprovar um Golden Set revisado e gates mínimos por domínio;
6. testar rollback e revogação em staging antes de habilitar publicação.
