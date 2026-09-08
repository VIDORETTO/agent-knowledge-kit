# T11 — Aplicar preset Mercado Livre sem acoplar o núcleo

**What to build:** O init usa taxonomia/consultas ML ou um preset neutro com o mesmo protocolo.

**Blocked by:** T03, T05.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P2. **Problemas do brief:** 1,7,8.

## Problema e resultado

O primeiro domínio precisa de cobertura sem virar regra hardcoded.

## Como implementar

Criar preset declarativo validado; mapear 17 temas e consultas complementares; produzir Golden candidates e entregáveis opcionais.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Nenhuma condicional de negócio ML no core; consultas marcadas candidatas; decisões comerciais desconhecidas ficam pendentes.
- [ ] Mesma conversa estrutural funciona com dois presets; curso sobre ML e curso vendido no ML permanecem alternativas; tema inválido falha.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Mesma conversa estrutural funciona com dois presets; curso sobre ML e curso vendido no ML permanecem alternativas; tema inválido falha.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não executar pesquisa de fontes reais sem política de aquisição adequada.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
