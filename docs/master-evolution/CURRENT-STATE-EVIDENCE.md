# Evidências de lifecycle e operação

Auditoria estática do checkout em 2026-09-07. As referências de testes indicam
comportamentos codificados; este documento não afirma que esses testes foram
executados nesta auditoria. Numeração de problemas: `MASTER-PLANNING-BRIEF.md`.

## 3 — Interface de mudanças: parcialmente pronta

- **Existe:** `docops/operations.py:817` constrói planos; `:971` fornece preview;
  `:3438` aplica. O payload já inclui ações, blockers, fingerprints e diff de
  estado (`:785`). Não criar outro motor transacional.
- **Existe:** candidatas (`docops/candidates.py:72`), aprovação
  (`docops/operations.py:2871`), publicação (`:2941`), histórico (`:2737`) e
  rollback (`:3157`). `tests/test_history_rollback.py:122` cobre retorno à
  primeira geração; `:143` impede restaurar histórico revogado; `:220` cobre
  quota antes de perder a versão ativa; `:268` separa histórico de resíduos.
- **Existe:** reconcile mantém fontes durante aquisição incompleta
  (`docops/source_policy.py:373`), respeita versões pinned (`:388`) e exige
  retirada explícita para snapshot vazio (`:405`).
- **Lacuna:** plano é uma operação de aquisição/pacote, não uma proposta de
  produto cobrindo decisões, tópicos, curso, página e seus derivados. Não há
  grafo tipado dessas dependências nos contratos examinados. Impacto conceitual
  atual usa cursor de documento/revisão e orçamento (`docops/triggers.py:191`).
- **Causa:** evolução orientada a pacote de documentação; faltam entidades do
  projeto, não os mecanismos fundamentais de publicação.
- **Menor evolução:** proposta versionada vinculada à revisão base e à política,
  com operações tipadas e relatório de impacto. Compilar a proposta para os
  planos existentes; estender a transação somente aos novos artefatos.
- **Aceite:** alteração de fonte invalida apenas dependentes identificados;
  alteração de página não reindexa fatos inalterados; base divergente bloqueia
  aplicação; rollback mantém bloqueio de fontes revogadas. Reutilizar testes
  públicos de candidatura, publication e history, sem testar helpers internos.

## 4 — Execução contínua: primitivas existem, supervisor falta

- `docops/__main__.py:300` exige `--once`; `docops/coordination.py:721` executa
  no máximo um job. Não existe ciclo contínuo nessa interface.
- Fila é SQLite (`docops/coordination.py:70`); claim usa transação
  `BEGIN IMMEDIATE` (`:453`); recibo de efeito evita repetir efeito reconhecido
  (`:677`); retries limitados usam backoff (`:772`); falha terminal vira blocked
  (`:791`). Não descrever fila, retries ou retomada como ausentes.
- `tests/test_worker.py:22` cobre candidata sem ativação, `:221` crash após
  efeito, `:307` eventos durante job e `:414` limite de retry.
- **Menor evolução:** runner local opcional e adaptadores de scheduler que
  chamem as mesmas seams de reconcile/event/work_once. Persistir agenda, último
  sucesso, próxima tentativa e parada solicitada. Polling é suficiente no MVP;
  watcher pode antecipar execução, mas não substituir reconciliação periódica.
- **Aceite:** restart não perde eventos; arquivo duplicado não duplica mudança;
  parada termina ou abandona trabalho com estado recuperável; fonte indisponível
  não é interpretada como revogada. Testar com relógio e aquisição controláveis.

## 5 — Enriquecimento: protocolo pronto, orquestração parcial

- `docops/harness.py:158` exporta request portátil sem credenciais/caminhos
  absolutos. `:219` vincula candidate, base, hashes, revisão de política,
  idioma e orçamento; `:236` limita artefatos a skill/router; `:253` registra
  awaiting_enrichment. `docops/candidates.py:352` importa o resultado.
- `tests/test_enrichment.py:183` cobre ausência de harness; `:196` importação
  apenas na candidata; `:231` deriva de base; `:270` Golden revisado e credenciais
  indevidos. O sistema já é integrado por contrato, embora execução seja externa.
- **Decisão preservada:** não embutir modelo/provedor. Isso é fronteira de
  arquitetura, não defeito. `docs/main-consolidation/SPEC.md:169` explicita
  neutralidade de modelo, provedor, scheduler e harness.
- **Menor evolução:** estados de dispatch/ack/timeout/cancelamento/retry e
  correlação durável sobre request/receipt existentes; adaptador externo
  configurável. Não confiar num texto dizendo que a skill foi enriquecida.
- **Aceite:** resultado atrasado para revisão antiga é recusado; ausência do
  harness continua explicável; resposta duplicada é idempotente; falha não
  altera ativa nem dispensa avaliação.

## 6 — Publicação manual: gate intencional

- Worker rejeita política diferente de candidate
  (`docops/coordination.py:627`); `tests/test_worker.py:155` protege essa regra.
- Aprovação fixa base, revisão candidata, hash da avaliação e política
  (`docops/operations.py:2904`). Publish exige receipt (`:2964`) e revalida
  contexto (`:2975`). A solução não deve remover essas verificações.
- **Limite de confiança:** compatibilidade CLI usa identidade do processo local
  (`docops/operations.py:2316`); atestados externos são validados estruturalmente
  (`:2329`). Isso não representa autenticação remota independente ou assinatura
  criptográfica validada pelo núcleo. Não reutilizar essa fronteira como RBAC
  multiusuário sem projeto adicional.
- **Decisão de produto:** autonomia factual privada pode ser opt-in, limitada
  por fonte admitida, escopo, prazo e orçamento. Publicação pública, direitos,
  privacidade, conflitos e mudanças conceituais/comerciais permanecem gates.
- **Menor evolução:** policy decision/receipt explícito de autorização delegada,
  ligado à candidata e à avaliação, usando o mesmo publish. Não interpretar
  `authority=official` como autorização para republicar material.
- **Aceite:** política expirada, revogada, de outra revisão ou escopo não aprova;
  candidato alterado após autorização bloqueia; nenhuma execução incompleta
  substitui ativa. Testar via API/CLI pública de approval/publication.

## 9 — Deriva de comando: correção delimitada

A CLI só expõe `work --once` (`docops/__main__.py:300`). Referências de skills
distribuídas ainda mostram `work --loop`: `skills/docops-agent/references/scheduler-runbooks.md:26`,
`skills/docops-agent/references/operations.md:47` e
`skills/docops-agent/references/tutorial.md:76` (localizadas na auditoria
coordenada). Corrigir exemplos para o contrato atual antes de implementar uma
interface contínua e incluir essas referências no gate de documentação. Um
comando apresentado como futuro deve estar explicitamente rotulado proposto.

## 10 — Operação: falta produto operacional, não todas as proteções

- Lease exclusivo local: `docops/lease.py:50`; reconhecimento de processo
  incerto é conservador (`:80`). Não é lock distribuído
  (`docs/ARCHITECTURE.md:76`).
- Promoção possui journal (`docops/operations.py:1760`), recuperação (`:1944`),
  backup/restore (`:2008`, `:2085`) e histórico editorial (`:2737`). Histórico
  local e backup transacional não equivalem a backup de desastre fora do disco.
- Diagnósticos e redação existem (`docops/observability.py:25`, `:119`);
  inspeção existe (`docops/operations.py:3943`). Faltam história operacional
  uniforme, saúde de scheduler, alertas úteis e ensaio de restauração integral.
- **Risco adicional a reproduzir:** claim só reassume running expirado enquanto
  attempt < MAX_ATTEMPTS (`docops/coordination.py:470`); incrementa tentativa
  (`:490`); RuntimeError sai sem conclusão (`:740`). Crash na última tentativa
  pode deixar running expirado que nenhum claim retoma. Tratar como hipótese de
  defeito apoiada no fluxo, não como reprodução executada nesta auditoria.
- **Risco de concorrência:** lease temporal de job é estabelecida no claim
  (`:486`); work_once chama execução síncrona (`:734`). Não foi encontrada
  renovação durante trabalho longo. A lease do pacote protege o writer, mas
  isso não basta para garantir ownership de todo efeito do job.
- **Menor evolução:** resolver job órfão terminal; renovar/fence lease se houver
  concorrência; runner com saúde e métricas de lag/blocked; backup consistente
  de pacote, histórico, runtime e SQLite, com política explícita para índice
  reconstruível. Manter implantação em host único primeiro.
- **Aceite:** última tentativa que cai termina em blocked recuperável após
  expiração; worker antigo não reconhece efeito após perder ownership;
  restauração em pasta nova reabre release e reconcilia fila; alertas só mudam
  quando estado requer ação. Testar falhas/restarts pela seam work_once e CLI.
- **Alternativa adiada:** fila distribuída e banco de serviço exigiriam fencing,
  transações e operação novos; adotar somente após métricas mostrarem gargalo.

## 12 — Estrutura: concentração confirmada

`docops/operations.py` reúne aquisição (`:484`), planejamento (`:817`), staging
(`:1510`), promoção/recuperação (`:1731`, `:1944`), autorização (`:2313`),
publicação (`:2941`), rollback (`:3157`), aplicação (`:3438`), inspeção (`:3943`)
e cleanup (`:4002`). A evidência é diversidade de responsabilidades, não apenas
tamanho. `LifecycleFacade` (`docops/lifecycle.py:260`) mantém compatibilidade
delegando plan/apply/preview (`:333`, `:343`, `:351`); criar outra fachada rasa
sem mover responsabilidades não resolve a concentração.

Extrair incrementalmente mecanismos com invariantes coesas: aquisição e
planejamento; transação de geração e recuperação; política de publicação;
histórico e restauração. Preservar imports públicos e códigos de erro durante
expand-contract. Usar testes de comportamento existentes como proteção;
primeiro estabelecer invariantes de crash/rollback, depois mover código.
Não combinar refactor amplo e novas regras no mesmo ticket. Aceite: mesmas
respostas públicas, recusas e recuperação sob falhas antes/depois; dependências
sem ciclos e cada nova interface esconde uma decisão concreta.
