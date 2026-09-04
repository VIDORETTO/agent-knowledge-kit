# Plano de prontidão para produção e divulgação — candidate 1.1.0

> Plano executável para Goal Mode. O objetivo é deixar o produto pronto para
> uma publicação controlada e para divulgação pública progressiva, sem misturar
> evidência local, release pública e material de terceiros.

## 1. Escopo real do produto

`consulta-documentacao` é um pacote Python/CLI com MCP local opcional. Não há
um servidor web, container, processo PM2 ou banco de produção neste
repositório. Portanto, “deploy para produção” significa:

1. produzir um artefato imutável a partir de um commit verificado;
2. disponibilizá-lo no canal de distribuição aprovado;
3. provar que uma instalação externa funciona;
4. tornar a documentação e o suporte coerentes com a versão publicada.

O RAG, índices, caches de modelo, corpora adquiridos e tokens continuam sendo
estado local do usuário. Não entram na release nem em uma divulgação pública.
Se o produto ganhar um serviço hospedado no futuro, isso exigirá um plano de
deploy separado para a infraestrutura correspondente.

“Divulgação em massa” só começa depois do canário pós-publicação. O anúncio
deve promover o pacote e seus limites reais; não deve prometer LLM, provedor,
suporte universal de harnesses ou auditoria de dependências sem vulnerabilidades.

## 2. Estado de entrada observado em 2026-09-04

| Gate | Estado | Evidência |
|---|---|---|
| Código e working tree | **verde** | `main` limpo em `912599c8dc6ab7bde30e27a2cc27f0c1f1107c41` |
| CI multiplataforma | **verde** | [run 33900149915](https://github.com/VIDORETTO/agent-knowledge-kit/actions/runs/33900149915) |
| Integração RAG/MCP | **verde** | [run 33900161429](https://github.com/VIDORETTO/agent-knowledge-kit/actions/runs/33900161429) |
| Candidate | **verificado, não publicado** | bundle, checksums, SBOM, provenance e identidade passaram |
| Vulnerabilidades | **gate humano pendente** | quatro advisories de `chromadb==1.5.9`; `--release` falha fechado |
| Settings do GitHub | **revisão pendente** | proteção, reviewers e permissões de release precisam de evidência autenticada |
| Release pública 1.1.0 | **não realizada** | não há tag, GitHub Release ou publicação de registry desta versão |
| Divulgação em massa | **não iniciada** | não há anúncio externo autorizado ou executado |

Este estado é o ponto de partida; qualquer alteração depois dele invalida a
identidade do candidate e exige nova execução dos gates e do CI.

> **Execução atual:** o baseline acima é histórico. Os resultados desta
> execução, inclusive o candidate local, a ausência do corpus FastAPI e os
> bloqueios de autorização, estão em
> [`RELEASE-READINESS-2026-09-04.md`](RELEASE-READINESS-2026-09-04.md).

## 3. Regras de autonomia do Goal Mode

O agente pode continuar sem perguntas intermediárias em tarefas reversíveis e
verificáveis: inspeções, testes, builds temporários, auditorias, geração de
evidências, revisão documental e preparação de textos/artefatos.

O agente não pode inventar nem registrar em nome do mantenedor:

- decisão `accept`, `mitigate`, `upgrade` ou `remove` para um risco de segurança;
- autorização de redistribuição de documentação de terceiros;
- identidade de administrador, reviewer, proprietário de registry ou canal de
  divulgação;
- credencial, segredo, domínio, conta social ou destino de publicação;
- sucesso de uma configuração GitHub que só pode ser vista autenticadamente.

As mutações externas de alto risco — alterar settings, criar tag, criar release,
publicar em registry ou enviar anúncios — só ocorrem quando a autorização e as
credenciais necessárias estiverem previamente disponíveis no ambiente e o
escopo estiver definido. Sem isso, o Goal Mode deve deixar o último artefato
verificado pronto, registrar o bloqueio e não contornar o gate.

## 4. Plano executável por fases

### Fase 0 — congelar o contrato de lançamento

**Gate:** escopo, versão, canais e política de dados estão escritos antes de
qualquer publicação.

- [x] Manter `1.1.0` como candidate e não reutilizar a identidade `v1.0.0`.
- [x] Definir GitHub como fonte canônica do código, documentação e evidência.
- [x] Manter GitHub Release como canal público principal de notas e assets.
- [ ] Verificar se `consulta-documentacao` tem um registry autorizado e
  configurado; usar PyPI somente com publicação confiável/least privilege.
- [x] Confirmar que não serão publicados corpus adquirido, índices, caches,
  snapshots de modelo, tokens, logs de usuário ou caminhos privados.
- [x] Registrar o critério de divulgação: release pública verificável,
  instalação externa aprovada e canário sem regressão.

### Fase 1 — fechar a evidência do candidate

**Gate:** um único commit, digest e conjunto de arquivos explicam todos os
resultados.

- [ ] Confirmar checkout limpo, branch, remote, tag inexistente/conflictante e
  ausência de mudanças depois da última medição.
- [ ] Reexecutar, em clone limpo, o runbook de `docs/RELEASE.md` com os perfis
  `core` e `rag` conforme o escopo do lançamento.
- [ ] Rodar auditoria de release, contratos, suporte, workflows, wheel,
  supply-chain, MCP, Golden Set e stress sem suprimir saídas vermelhas.
- [ ] Gerar um novo candidate fora do Git e verificar manifesto, lista,
  checksums, SBOM, provenance, licença, `publication=false` e `source_commit`.
- [ ] Fazer push do commit candidato apenas com autorização explícita e aguardar
  CI e Integration no SHA exato.
- [ ] Baixar o artifact do CI, comparar digest/lista/SHA e executar o gate
  `verify_candidate.py --release`; código diferente de zero mantém o bloqueio.

### Fase 2 — segurança, supply chain e governança

**Gate:** riscos conhecidos estão tratados por correção técnica ou por uma
decisão humana registrada; nenhuma exceção fica implícita.

- [x] Tentar primeiro uma versão compatível e corrigida do Chroma, se existir;
  repetir lock, vendor, wheel, RAG/MCP, segurança e candidate completos.
- [x] Se a atualização não for viável, aplicar mitigação verificável ou reduzir
  o escopo do perfil RAG; não chamar isso de auditoria limpa.
- [ ] Um mantenedor preencher `docs/CHROMA-RESIDUAL-DECISION.md` com decisão,
  responsável, data, versão, justificativa e reavaliação.
- [x] Auditar dependências cruas e wrapper, mantendo os quatro advisories
  visíveis no relatório e no material de release quando ainda existirem.
- [x] Confirmar provenance do vendor/modelo, licença das fixtures e ausência de
  dados derivados no conjunto distribuível.
- [ ] Com acesso autenticado, verificar branch protection, required checks,
  reviewers, CODEOWNERS, Dependabot, secret scanning, push protection e
  permissões de release conforme `community/GITHUB-SETTINGS-CHECKLIST.md`.
- [ ] Registrar links, identidade do administrador e data da revisão; uma
  inspeção anônima deve permanecer `not verified`.

### Fase 3 — materializar a release imutável

**Gate:** tag, assets e registry apontam para o mesmo commit e candidate.

- [ ] Confirmar que o gate `--release` passou para o SHA final.
- [ ] Criar tag anotada e imutável `v1.1.0` exatamente nesse SHA; nunca mover
  uma tag existente para corrigir divergência.
- [ ] Em ambiente limpo derivado da tag, construir o wheel e recalcular
  `SHA256SUMS`, SBOM e provenance; comparar com o candidate aprovado.
- [ ] Criar a GitHub Release com changelog, limitações, suporte, segurança,
  checksums e links para a documentação. Não anexar corpus, cache ou snapshot.
- [ ] Publicar no registry escolhido somente se a identidade do projeto,
  trusted publishing e permissões least privilege estiverem verificadas.
- [ ] Confirmar por API e download que tag, release, assets, metadados e versão
  do pacote são coerentes; registrar URLs e horários.

### Fase 4 — canário pós-publicação

**Gate:** uma pessoa sem o checkout do autor instala e usa o artefato público.

- [ ] Criar ambientes temporários fora do checkout para Python 3.11, 3.12 e
  3.13, conforme disponibilidade dos runners/capacidades.
- [ ] Instalar pelo canal público, sem `-e` e sem depender de cache local.
- [ ] Executar `docops doctor --json`, smoke do fluxo de fixture, validação e
  auditoria de metadados; confirmar `installed-package` quando aplicável.
- [ ] Exercitar o perfil RAG somente com runtime/model cache externo permitido;
  confirmar MCP, citação, avaliação e comportamento fail-closed.
- [ ] Testar os links públicos, instruções de bootstrap, exemplos e suporte
  anunciado; remover qualquer texto que ainda diga apenas “candidate” depois
  da publicação efetiva.
- [ ] Registrar versão instalada, plataforma, comando, resultado e logs
  redigidos. Nunca coletar ou publicar credenciais, corpus ou prompts.

### Fase 5 — divulgação progressiva

**Gate:** o canário passou e existe uma janela de observação sem regressão
crítica.

- [x] Preparar release notes e anúncio curto com problema resolvido,
  instalação, exemplo mínimo, limites, suporte e canal de segurança.
- [ ] Fazer primeiro uma divulgação controlada nos canais do próprio projeto
  (release, README/changelog e comunidade), sem alegar cobertura além da
  matriz comprovada.
- [ ] Observar por pelo menos 24 horas: instalação, issues, falhas de CI,
  downloads quando disponíveis, alertas de segurança e feedback de suporte.
- [ ] Se não houver regressão crítica, ampliar para os canais externos que
  estejam explicitamente configurados; preparar rascunhos quando o destino não
  existir, mas não enviar mensagens para contas não autorizadas.
- [ ] Atualizar o registro com links de cada anúncio, horário, audiência/canal
  e resultado; não divulgar dados de usuários.

### Fase 6 — operação pós-lançamento e rollback

**Gate:** a versão pode ser contida e corrigida sem reescrever evidência.

- [ ] Monitorar a janela de 24h e a de 72h, triando bugs públicos e incidentes
  de segurança por `SECURITY.md`.
- [x] Para defeito de pacote, preservar a tag/asset original, publicar uma
  versão de correção e, se necessário, fazer yank da versão afetada no registry.
- [x] Para incidente de segurança, interromper a divulgação, usar o canal
  privado, limitar detalhes públicos e preparar correção antes de novo anúncio.
- [x] Para divergência de candidate, não editar asset publicado: invalidar a
  evidência, gerar novo candidate, repetir CI e publicar uma nova versão.
- [ ] Registrar incidente, impacto, decisão, rollback/correção e verificação
  pós-correção em um handoff versionado.

## 5. Gates que não são automatizáveis

O objetivo de “nenhuma intervenção durante o Goal Mode” é compatível com a
execução contínua do trabalho técnico, mas não transforma decisões legais,
segurança ou autorização de publicação em fatos automáticos. Antes de chamar o
processo de concluído, estes itens precisam ter evidência válida:

| Gate humano/externo | Por que existe | Evidência aceita |
|---|---|---|
| Residual Chroma | aceitar ou alterar risco é decisão do mantenedor | registro completo em `docs/CHROMA-RESIDUAL-DECISION.md` |
| Licença/proveniência | conteúdo de terceiros pode ser protegido | manifesto e revisão do conjunto distribuível |
| GitHub governance | configurações protegidas não são provadas anonimamente | checklist autenticado com identidade/data/links |
| Canal/conta de publicação | registry e redes podem pertencer a terceiros | configuração de trusted publishing e escopo autorizado |
| Comunicação externa | “massa” depende de audiência, contas e mensagem | destinos/cópia aprovados ou canais do próprio projeto |

Se algum desses gates não estiver disponível, o estado correto é
`release-ready-pending-human-gate`, nunca `production-ready` ou `publicly
launched`.

## 6. Definition of Done

- [ ] O candidate final tem um único SHA, digest e conjunto de arquivos
  verificados em CI e no ambiente limpo.
- [ ] `verify_candidate.py --release` termina com sucesso.
- [ ] A decisão Chroma e a revisão de settings GitHub estão registradas.
- [ ] A tag é imutável; os assets têm checksums/SBOM/provenance coerentes.
- [ ] A instalação pública foi testada fora do checkout do autor.
- [ ] README, changelog, metadata, suporte e release notes descrevem a versão
  real e os limites do produto.
- [ ] O canário e a observação pós-publicação passaram sem incidente crítico.
- [ ] Existe rollback por nova versão/yank/correção sem mover tag nem expor
  dados privados.
- [ ] A divulgação controlada foi observada antes de qualquer divulgação em
  massa.

## 7. Referências e comandos normativos

- Runbook técnico: [`docs/RELEASE.md`](RELEASE.md).
- Política de publicação: [`docs/PUBLISHING-POLICY.md`](PUBLISHING-POLICY.md).
- Decisão de risco: [`docs/CHROMA-RESIDUAL-DECISION.md`](CHROMA-RESIDUAL-DECISION.md).
- Settings: [`community/GITHUB-SETTINGS-CHECKLIST.md`](../community/GITHUB-SETTINGS-CHECKLIST.md).
- Handoff atual: [`docs/HANDOFF-2026-09-04-CI-WHEEL.md`](HANDOFF-2026-09-04-CI-WHEEL.md).

Os comandos devem ser executados na ordem do runbook, sempre em primeiro plano
quando houver mutação de estado RAG, com checkpoints preservados e sem publicar
saídas intermediárias.
