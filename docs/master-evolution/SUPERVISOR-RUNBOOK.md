# Runbook operacional do supervisor

Este runbook cobre o T18 com execução limitada e scheduler externo. O DOCOPS
não instala, inicia ou mantém um daemon de agenda. Cada invocação faz um poll
único, persiste o tick/estado e termina; a recorrência é responsabilidade da
operação que explicitamente configurar o agendador.

## Execução única

Prepare um `--project` persistente e um `--queue` dedicado ao projeto. O
processo deve usar o mesmo ambiente Python das demais operações do pacote:

```text
python -m docops supervisor run --project <project-root> --source <source-dir> --source-id <source-id> --queue <queue-dir> --max-missed-cycles 3 --now 2026-09-08T12:00:00Z --json
python -m docops project health --project <project-root> --queue <queue-dir> --max-missed-cycles 3 --json
```

O `--now` é opcional em operação; ele aparece nos exemplos apenas para tornar
fixtures e incidentes reproduzíveis. A execução prepara/reconcilia o trabalho,
mas não publica candidata. Repetições do mesmo estado geram no máximo um job
por identidade e o supervisor conserva a fonte quando ela está indisponível.

## Windows Task Scheduler

Instale a tarefa somente por procedimento operacional explícito. Um exemplo de
ação é `C:\caminho\projeto\.venv\Scripts\python.exe`; os argumentos devem
conter `-m docops supervisor run`, o projeto e a fila persistentes. Configure
uma execução a cada minuto, marque reinício após exit code não-zero e mantenha
o histórico JSON em diretório protegido. Uma segunda tarefa pode chamar
`project health` em intervalo maior para encaminhar incidentes.

Valide a tarefa sem executar instalação pelo teste de fixture:

```text
python scripts/run_master_evolution_fixture.py
```

O teste não cria Task Scheduler, não altera corpus/índice real e não publica.

## Linux (cron ou systemd timer)

Cron, por exemplo:

```cron
* * * * * cd /srv/docops && /srv/docops/.venv/bin/python -m docops supervisor run --project /var/lib/docops/project --source /srv/docs/project --source-id source-main --queue /var/lib/docops/queue --max-missed-cycles 3 --json >> /var/log/docops-supervisor.jsonl 2>&1
*/5 * * * * cd /srv/docops && /srv/docops/.venv/bin/python -m docops project health --project /var/lib/docops/project --queue /var/lib/docops/queue --max-missed-cycles 3 --json >> /var/log/docops-health.jsonl 2>&1
```

Um systemd timer equivalente deve chamar um serviço `Type=oneshot`; o timer
define a periodicidade e o serviço termina após um poll. Não transforme o
comando em loop interno, não instale o timer como efeito de teste e não rode
dois writers para o mesmo projeto.

## Parada, retomada e indisponibilidade

- `supervisor stop` deixa o estado parado e recuperável; `supervisor resume`
  reabre o próximo ciclo sem apagar eventos.
- Ao reiniciar, execute `supervisor run` uma vez. Eventos pendentes são
  reconciliados pela identidade estável; duplicatas não criam efeitos novos.
- Falhas consecutivas incrementam `missed_cycles`. Ao atingir
  `max_missed_cycles`, `project health` retorna saúde degradada e incidente
  acionável; o contador volta a zero quando uma fonte válida é observada e o
  incidente de recuperação é fechado.
- Origem indisponível é estado observável, não autorização para revogar ou
  substituir fonte. Corrija a origem e rode o próximo poll.

Para encerrar um processo em Windows, confirme o PID e o `CommandLine` do
projeto antes de agir; nunca finalize todos os processos Python por nome.
