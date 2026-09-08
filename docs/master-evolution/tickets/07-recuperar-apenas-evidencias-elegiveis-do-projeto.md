# T07 — Recuperar apenas evidências elegíveis do projeto

**What to build:** Perguntas retornam fontes elegíveis de toda a composição do projeto, com filtros e citações versionadas.

**Blocked by:** T05.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P2. **Problemas do brief:** 7,8.

## Problema e resultado

A interface de busca não carrega os filtros de governança necessários.

## Como implementar

Estender interface pública existente e adapter; transportar metadados ao índice/resultados; prefilter ou refill limitado; cache por política/composição/filtros.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Zero vazamento entre projetos/revogadas; limitações de refill declaradas; path/seção/página/tempo preservados quando existentes.
- [ ] Top hits de outro projeto são excluídos e fonte elegível abaixo deles é encontrada; filtro inválido falha; revogação após cache bloqueia hit.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Top hits de outro projeto são excluídos e fonte elegível abaixo deles é encontrada; filtro inválido falha; revogação após cache bloqueia hit.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Sem rewrite do vendor antes de demonstrar limitação do adapter.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
