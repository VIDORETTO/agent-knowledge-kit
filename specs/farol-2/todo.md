# Todo Farol 2.0

View derivada dos tickets. Atualize estado e tarefas no ticket canônico, depois
regenere esta projeção.

## Próxima fronteira

- [ ] [TK-001](tickets/TK-001.md) — contract test pronto; provar API/parsing/locators RAGFlow v0.27.2 (`not_run` externo).
- [x] [TK-002](tickets/TK-002.md) — expandir contratos fundamentais v2.

Esses tickets são independentes. TK-001 não altera produção; TK-002 não remove
contratos 1.x.

## Bloqueados por dependência

### P1 — Seams e IR

- [x] TK-003 — KnowledgeBackend + adapter legado.
- [ ] TK-004 — IR canônica implementada e coberta localmente; evidência RAGFlow ainda pendente.
- [x] TK-005 — registry governado implementado e verificado; tickets RAGFlow dependentes permanecem condicionados ao spike.

### P2 — Fidelidade

- [x] TK-006 — Markdown/HTML estruturado implementado; regressão local verde.
- [ ] TK-007 — PDF textual/quarentena/OCR autorizado implementados; OCR real ainda pendente.
- [x] TK-008 — DOCX/EPUB estruturados implementados; regressão local verde.
- [x] TK-009 — repositório por escopo implementado; regressão Git/symlink/budgets verde.

### P3 — Conhecimento

- [x] TK-010 — taxonomia versionada/aprovável implementada; regressão local verde.
- [ ] TK-011 — multi-skill/lineage implementado; adapter real book-to-skill ainda pendente.
- [x] TK-012 — router global e citações canônicas implementados; regressão local verde.

### P4 — RAGFlow e lifecycle

- [ ] TK-013 — lifecycle RAGFlow implementado com fake contract; prova real pendente de TK-001.
- [ ] TK-014 — mapping/retrieval/citations implementados; integração RAGFlow real pendente.
- [x] TK-015 — composição/updates/recovery implementados e testados localmente.

### P5 — Migração e foco

- [x] TK-016 — migração 1.x resumível implementada; promoção final permanece condicionada ao cutover.
- [ ] TK-017 — auditor RED/guard implementados; remoção contratual aguarda TK-018 aprovado.

### P6 — Cutover e entrega

- [ ] TK-018 — decisão de cutover e fixture provider-free implementadas; dual-run RAGFlow real pendente.
- [ ] TK-019 — guard de contração implementado; remoção de legado não autorizada antes do cutover.
- [ ] TK-020 — jornada provider-free e gates core verdes; perfil RAGFlow/handoff final pendentes.

## Checklist por ticket

- [ ] Ler spec/plan e paths na ordem do ticket.
- [ ] Confirmar baseline e preservar trabalho do usuário.
- [ ] Executar um caso RED por comportamento ausente.
- [ ] Implementar o mínimo GREEN e refatorar com testes verdes.
- [ ] Executar validação focal e regressão proporcional.
- [ ] Registrar ambiente, SHA, comandos, resultados e skips.
- [ ] Não marcar `done` sem aceites passados e revisão exigida.
