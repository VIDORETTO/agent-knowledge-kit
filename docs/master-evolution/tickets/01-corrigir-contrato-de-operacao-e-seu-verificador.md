# T01 — Corrigir contrato de operação e seu verificador

**What to build:** Um agente segue todos os exemplos operacionais distribuídos e recebe opções aceitas pela CLI.

**Blocked by:** None — can start immediately.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P0. **Problemas do brief:** 9.

## Problema e resultado

O guia instalado recomenda uma opção inexistente e o checker não a detecta.

## Como implementar

Caracterizar opções reais; substituir a promessa de loop por execução única supervisionada; ampliar verificação para flags e exemplos inline sem executar mutações dos exemplos.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Nenhum exemplo normativo recomenda loop inexistente; aliases legados continuam equivalentes; checker distingue proposta/histórico de contrato executável.
- [ ] Guia com flag inexistente deve reprovar, exemplo válido deve passar; testar também exemplo com placeholders e comando citado apenas como proposta futura.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Guia com flag inexistente deve reprovar, exemplo válido deve passar; testar também exemplo com placeholders e comando citado apenas como proposta futura.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não implementar daemon neste ticket.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
