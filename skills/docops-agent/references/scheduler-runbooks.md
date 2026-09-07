# Runbooks de reconciliação e worker

O DOCOPS não instala um scheduler. O worker processa jobs existentes; a
reconciliação é que descobre arquivos novos e deve ser agendada separadamente.
Use runtime privado fora do pacote e mantenha um writer por pacote.

## Ciclo recomendado

```text
reconcile a cada 6h ou após upload finalizado
worker a cada 1min (foreground ou serviço)
triagem de candidata diariamente
avaliação após lote, mudança de embedding ou regressão
```

Não dispare reconciliação em cada evento de escrita parcial. Use debounce e
confirme tamanho/hash estáveis quando a origem não fornece um recibo de upload.

## POSIX (cron)

```cron
*/1 * * * * cd /srv/docops && .venv/bin/python -m docops lifecycle worker run --package artifacts/api --runtime-root /var/lib/docops/api --json >> /var/log/docops-worker.jsonl 2>&1
17 */6 * * * cd /srv/docops && .venv/bin/python -m docops lifecycle source reconcile --package artifacts/api --runtime-root /var/lib/docops/api --source /srv/docs/api --source-root /srv/docs --index-rag --json >> /var/log/docops-reconcile.jsonl 2>&1
```

Para um serviço contínuo, use `work --loop --interval-seconds 60` com um
gerenciador que reinicie o processo e alerte em exit code não zero.

## Windows

Crie duas tarefas no Task Scheduler: uma chama `docops lifecycle worker run` a cada
minuto e outra chama `source reconcile` após a janela de upload. Use o Python do
ambiente preparado, `--runtime-root` em disco local e saída JSON redigida. Não
encerre processos Python por nome; confirme o PID e o `CommandLine` do projeto.

## CI/containers

Em CI, prefira `plan`/`reconcile` sem publicação automática. Um worker de
produção deve possuir volume persistente para SQLite/receipts e backup testado;
WAL em filesystem de rede não é uma garantia de consistência. O job deve falhar
fechado quando licença, autenticação, perfil de embedding ou completude da
fonte não puderem ser confirmados.

## Recuperação

- `pending`/`retry_wait`: corrigir falha transitória e executar `work` novamente;
- `blocked`: resolver licença, conflito, aprovação ou base obsoleta; não forçar
  retry infinito;
- lease expirado: o próximo worker pode reclamar o job, mas confirme a geração;
- crash de promoção: executar `inspect`, deixar o journal recuperar e validar;
- backup/restore: restaurar runtime e pacote compatíveis, depois consultar
  status e geração antes de abrir readers;
- mudança de embedding: iniciar rebuild completo, nunca retomar um índice misto.
