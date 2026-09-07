# Atualização contínua e aprendizado seguro

## O que acontece quando um arquivo novo aparece

Colocar um arquivo na pasta é apenas uma mudança no filesystem. O DOCOPS não
deve publicar uma skill ou assumir que o arquivo está admitido sem reconciliação.
O ciclo atual é:

```text
fonte alterada → reconcile → evento idempotente/debounce → job → candidata
RAG (opcional) → avaliação → revisão/aprovação → publicação explícita
```

Registre a fonte uma vez e reconcilie-a por um scheduler externo, watcher
controlado ou comando manual:

```text
python -m docops lifecycle source register \
  --package <pacote> --source-id docs-main --canonical <fonte> --owner operator

python -m docops lifecycle source reconcile \
  --package <pacote> --snapshot <acquisition-snapshot.json>

python -m docops lifecycle worker run \
  --once --queue <fila.sqlite> --worker-id <id>
```

O `work` processa a fila; ele não descobre arquivos novos se nenhum processo
executar `reconcile`. O `--index-rag` é opt-in e atualiza o RAG de modo
incremental quando o backend permite. O harness gerado é leitor read-only e
desativa o watcher para não alterar uma geração enquanto o agente responde.

## RAG versus skill

| Mudança | RAG | Skill ativa |
|---|---|---|
| Novo fato literal | Atualizar após admissão/indexação | Não muda automaticamente |
| Correção/remoção de fato | Reconciliar, substituir ou tombstone | Invalidar suporte afetado |
| Novo padrão conceitual | Candidata e avaliação | Só após aprovação/publicação |
| Reindex sem mudança documental | Nova revisão de índice | Não solicitar fold-in |
| Perfil de embedding diferente | Full rebuild obrigatório | Preservar skill |

Gatilhos conceituais criam `skill.enrichment.requested` por lote (limiares
documentados em [`docs/continuous-knowledge/IMPLEMENTATION-STATUS.md`](../../../docs/continuous-knowledge/IMPLEMENTATION-STATUS.md)),
não editam `SKILL.md` sozinhos.

## Skill candidata

```text
python -m docops package run <fonte> --output <pacote> \
  --mode update --publication-policy candidate --license <id>

python -m docops lifecycle candidate enrichment-request \
  --package <pacote> --candidate-id <id>

# O harness/book-to-skill produz a saída somente dentro da candidata.
python -m docops lifecycle candidate enrich \
  --package <pacote> --candidate-id <id> --skill-root <skill-externa> \
  --tool book-to-skill --version <versao>

python -m docops quality evaluate \
  --package <pacote> --cases <golden-revisado.json> --adapter memory

python -m docops lifecycle candidate approve \
  --package <pacote> --candidate-id <id> --actor <id> \
  --role human_approver

python -m docops lifecycle candidate publish \
  --package <pacote> --candidate-id <id>
```

Avaliação precisa referenciar a composição avaliada. Reenriquecimento, mudança
de corpus, router ou política invalida aprovação anterior. Rollback é uma nova
publicação auditada e não pode reativar proposta revogada.

## Conversas

Capture uma alegação mínima, seu escopo, versão, privacidade e evidências:

```text
python -m docops lifecycle learning submit \
  --package <pacote> --proposal <proposal.json> --capture-opt-in
```

`opinion`, `preference`, resposta sem fonte, segredo e conteúdo privado não
entram no corpus compartilhado. Mesmo uma alegação `fact` só pode ser admitida
após evidência independente e revisão humana. Feedback de perguntas sem resposta
ou conflito prioriza investigação; não altera conhecimento sozinho.
