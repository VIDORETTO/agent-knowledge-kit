# Evidência de implementação do master plan

## Escopo e autoridade

Esta execução implementa localmente os contratos de `docs/MASTER-PLAN.md`,
`docs/MASTER-IMPROVEMENT-PLAN.md` e `docs/master-evolution/`, em ordem de
dependências P0→P5. O estado de trabalho permanece na branch
`main`; o gate final registrou o commit-base `4350d67` e o working tree da
execução. O corpus e o índice RAG real não foram alterados. Os arquivos de
planejamento que já estavam no working tree foram preservados.

O teste integrado usa somente diretórios temporários e dados sintéticos. Não
houve publicação, criação de tag, instalação de scheduler, chamada a provedor
comercial, uso de credencial, consulta ao MCP real ou rebuild do índice real.
Ausência de autoridade externa permanece `unknown`/bloqueada; nenhuma
permissão comercial ou licença foi inferida.

## Baseline e protocolo TDD

- Foram lidos os contratos, `TDD-EXECUTION.md`, a skill TDD, SPEC,
  STATE-CONTRACTS, KNOWLEDGE-QUALITY, roadmap e os 24 tickets antes da
  implementação.
- O baseline selecionado anterior registrava 50 testes em um primeiro lote e
  42 em um segundo lote, com sobreposição; esses números são histórico de
  caracterização, não são somados como testes únicos.
- A primeira tentativa da suíte completa no Python global ficou em execução por
  mais de 15 minutos e foi interrompida com segurança; por isso nunca foi
  tratada como verde. O gate final usa o `.venv` do checkout.
- Uma repetição inicial do gate encontrou um caminho absoluto no documento de
  evidências e parou no primeiro estágio dependente; o auditor reproduziu o RED,
  o locator foi tornado portátil e o clean clone passou antes da repetição final.
- Cada fatia nova foi protegida por teste de seam raiz/CLI ou fixture pública;
  falhas de contrato foram corrigidas antes do avanço. O protocolo integrado é
  `scripts/run_master_evolution_fixture.py` e o runner de release o executa
  como estágio obrigatório.

## Atualização T02 → T04 — migração legada e artefatos opcionais — 2026-09-09/10

Esta continuação preservou o pacote DOCOPS existente como locator independente:
ele não foi duplicado nem convertido em estado editorial do projeto. A adoção
usa caminhos relativos no receipt (`source_path`/`source_locator`), hashes de
origem e destino, e mantém direitos/licença e privacidade como `unknown` quando
não há autoridade externa. O dry-run não grava `project.json`, metadados,
package, revisão ou receipt.

### Ledger RED → GREEN da continuação

- **Comercial não confirmado:** o RED mostrou que um preço proposto podia vazar
  para `page.offer`; o GREEN mantém preço, garantia e CTA nulos e a página
  pendente até haver resposta explícita confirmada e preço portátil válido.
- **Adoção legada:** o RED mostrou locator absoluto no receipt e projeto
  incrementado artificialmente no dry-run; o GREEN usa locator relativo, hashes,
  plano de substituição/backup e mantém o estado byte a byte no dry-run.
- **Mudança de audiência:** o RED mostrou derivado dependente inalterado; o
  GREEN atualiza brief/página e marca apenas curso/página como `draft`, criando
  revisão imutável localizada sem inserir campo fora do contrato do curso.
- **Retomada CLI:** o RED mostrou `ok=true` com `needs_input` retornando código
  0; o GREEN retorna código 2, e dois processos CLI retomam a mesma sessão sem
  repetir respostas confirmadas.
- **Preço estruturado:** o RED revelou erro de tipo ao validar um mapa de preço;
  o GREEN valida a forma `{amount_decimal, currency}` sem exceção e mantém a
  pendência quando a forma não é contratual.

## Ledger RED → GREEN por ticket

Na auditoria TDD final, respostas `agent_proposed`/`preset_default` passaram a
permanecer pendentes até uma confirmação explícita; a ingestão estruturada
também passou a recusar segmentos temporais fora de ordem.

| Ticket | RED observado | GREEN/evidência local | Estado |
|---|---|---|---|
| T01 | Checker e documentação não distinguiam exemplo futuro de flag executável. | `check_documentation.py`, aliases explícitos e ajuda canônica; `test_documentation_checker...`. | verificado local |
| T02 | Init não tinha sessão master persistida/retomável. | `start/inspect/answer/finalize_project_init`, CAS, idempotência, stale revision e origem confirmada para decisões; `test_project_init...`, `test_proposed_course_intent...`. | verificado local |
| T03 | Finalização não tinha composição de brief/derivados sob contrato. | Artefatos v1 separados, hashes, entregáveis opcionais, estados pendentes, confirmação explícita de respostas comerciais e invalidação localizada por mudança de audiência; `test_unconfirmed_commercial_values_never_enter_page_offer`, `test_audience_correction_invalidates_only_dependent_derivatives`. | verificado local |
| T04 | Adoção/migração pública inexistia; Windows também revelou `WinError 5` na troca de diretório. | Adoção v1, locator relativo, hashes de origem/destino, dry-run não mutante, backup, rollback, idempotência e restauração transacional; `test_adoption_dry_run_is_non_mutating_and_receipt_uses_portable_locators`. | verificado local |
| T05 | Direitos e validade não eram aplicados por finalidade. | Registro governado, grants fail-closed, região/validade e decisão de uso; `test_governance_is_per_purpose...`. | verificado local |
| T06 | Transcrição sem locator temporal deveria recusar. | Segmentos temporais em ordem monotônica, proveniência, limites e redistribuição privada; mesma suíte e fixture integrada. | verificado local |
| T07 | Hits revogados/estrangeiros poderiam ocupar o resultado. | Filtro por projeto/fonte/revisão, refill bounded e `insufficient_evidence`; `test_evidence_query_filters...`. | verificado local |
| T08 | Troca de perfil sem full rebuild e sem preservação do reader não tinha guard. | Candidata isolada, snapshot/receipt pinados, idempotência e active pointer preservado; `test_profile_candidate...`. | verificado local; MCP real externo |
| T09 | Ausência de evidência e conflito não tinham resultado tipado. | Claims classificados, conflito explícito, vigência/região e outcome `conflicting`/`insufficient_evidence`; fixture integrada. | verificado local |
| T10 | Golden não revisado ou candidato não preparado não podia ser aceito silenciosamente. | Receipt/snapshot obrigatórios, métricas e bloqueio de casos críticos; `test_profile_candidate...`. | verificado local; Golden/MCP reais externos |
| T11 | Preset de domínio estava acoplado ao core ou ausente. | JSON declarativo `docops/presets`, preset neutro e ML com 17 temas/candidatos; `test_presets_are_declarative...`. | verificado local |
| T12 | Mudança sem diff/impacto e dependência transitive não tinha seam. | Proposal/inspect/prepare com base, hash semântico, grafo, ciclo/unknown dependency e artefatos inalterados byte a byte. | verificado local |
| T13 | Revogação não propagava para claims/derivados/cache/rollback. | Tombstones e elegibilidade por revisão; query pós-revogação retorna `insufficient_evidence`; fixture e regressões de readers. | verificado local |
| T14 | Enrichment externo não era request/receipt-bound. | Dispatch/submit/timeout/retry, base stale, orçamento, paths e payload sensível bloqueados; `test_enrichment_is_scoped...`. | verificado local |
| T15 | Curso/página não eram derivados avaliáveis. | Validação separada de claims/provas, preço/CTA pendentes e bloqueio de referência inelegível; `test_derivative_validation...`. | verificado local |
| T16 | Ativação poderia parar entre ponteiro e receipt. | Journal de ativação, recovery antes da próxima operação, composição velha/nova inteira e rollback; `activation-recovery`/`activation-recover`. | verificado local |
| T17 | Última tentativa/lease longa precisava de terminalidade e fencing. | Worker/coordination preservam ownership, renewal, dedupe e crash-after-effect; `tests/test_coordination.py` e `tests/test_worker.py`. | verificado local |
| T18 | Não havia supervisor one-shot com parada/retomada e scheduler explícito. | `supervisor run/stop/resume`, fila deduplicada, polling e [runbook](SUPERVISOR-RUNBOOK.md); nenhum scheduler é instalado por teste. | verificado local |
| T19 | Saúde não expunha limiar, incidente deduplicado ou redação. | `project health` com missed cycles, queue metrics, incident open/close e redaction; `test_supervisor_coalesces...`. | verificado local |
| T20 | Backup não preservava unidade de projeto, receipts e tombstones. | Manifest/checksum, exclusão de segredos, snapshot SQLite da fila operacional, restore isolado e tombstone posterior; `test_backup_restore...`, RPO/RTO no fixture. | verificado local |
| T21 | Mitigação expirada/alterada não era validada contra auditoria bruta. | `validate_dependency_mitigation` exige owner, prazo, evidence, lock, versão, advisory e threat model; `test_dependency_mitigation...`. | verificado local; decisão upstream externa |
| T22 | Runner não incluía o protocolo master nem provava pacote core. | Release gates seriais, core fixture obrigatório, schemas empacotados e wheel core; o gate final core aprovou 21/21 estágios, 6.530 testes passados, 70 skips, zero falhas; MCP/full profile depende do runtime externo. | verificado local; MCP/CI externo |
| T23 | Delegação ampla poderia alcançar conflito, conceito ou licença. | Receipt escopado por fonte/ação/prazo/orçamento/policy, hash exato, revalidação e kill switch; `test_factual_delegation...`. | verificado local |
| T24 | Roteiro integrado não tinha fixture provider-free reproduzível. | Init→fonte→transcrição→claims/conflito→revogação→change crash/recovery→backup/restore→delegação revogada→presets; script integrado. | verificado local; fronteiras externas bloqueadas |

## Verificações executadas

Comandos executados no checkout, sempre pelo `.venv` local:

```text
rtk proxy powershell -NoProfile -Command "& '.venv\Scripts\python.exe' scripts\sync_schemas.py --write"
rtk proxy powershell -NoProfile -Command "& '.venv\Scripts\python.exe' scripts\check_contracts.py --json"
rtk proxy powershell -NoProfile -Command "& '.venv\Scripts\python.exe' scripts\check_documentation.py --root . --json"
rtk proxy powershell -NoProfile -Command "& '.venv\Scripts\python.exe' scripts\check_public_seams.py --tests tests --json"
rtk proxy powershell -NoProfile -Command "& '.venv\Scripts\python.exe' scripts\run_master_evolution_fixture.py"
rtk proxy powershell -NoProfile -Command "& '.venv\Scripts\python.exe' -m ruff check docops tests scripts"
rtk proxy powershell -NoProfile -Command "& '.venv\Scripts\python.exe' scripts\run_release_gates.py --profile core --output '<artifacts>'"
```

Resultados já observados: 54 schemas sincronizados, contratos sem findings,
112 Markdown sem findings, seams públicos sem findings, Ruff verde e fixture
provider-free verde. A execução mais recente do fixture mediu RPO observado de
0 s, backup em aproximadamente 0,064807 s e RTO em aproximadamente 0,039949 s; os
valores são métricas do diretório temporário, não uma SLO de produção.

O relatório final foi gravado no diretório temporário do runner, no locator
portátil `<artifacts>/release-gates.json`:
`ok=true`, 21 estágios, `failed=0`, `not_run=0`, 6.530 testes passados e 70
skips explicitamente registrados. O pytest do checkout passou em 399 testes e
teve 3 skips; no clean-clone core passaram 394 testes e houve 8 skips, sendo
5 devido à ausência deliberada de `chromadb` e 3 por limitações de symlink do
Windows. O perfil `full`/MCP não foi executado porque exigiria o runtime RAG e
o índice real fora do escopo autorizado; nenhum estágio foi pulado
silenciosamente no perfil core.

## Segurança, recuperação e limitações

- Schemas canônicos e cópia empacotada são sincronizados por conteúdo; campos
  desconhecidos ficam sob `extensions` quando o contrato permite.
- Filtros de busca e derivados falham fechados para projeto/fonte/revisão
  incompatível, revogação, falta de grant e Golden não revisado.
- Segredos, tokens, queries e conteúdo sensível não entram nos eventos de
  supervisor nem em backups; a auditoria bruta de dependências é separada da
  decisão de mitigação.
- Ativação, adoção e restore usam staging/journal e deixam a base anterior
  utilizável em falha. A produção original nunca foi escrita.
- O Python 3.14 usado localmente continua apenas tolerado pela matriz; isso não
  altera a lista suportada 3.11–3.13.
- O runtime MCP real, rebuild multilíngue real, upstream online, permissões
  comerciais, credenciais de publicação, CI em outras plataformas e decisão
  humana sobre os advisories residuais do Chroma não foram executados por
  escopo/autorização. Esses limites são bloqueios externos explícitos, não
  resultados inventados.
