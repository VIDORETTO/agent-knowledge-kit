# T22 — Provar distribuição e operação do produto local

**What to build:** Clean clone e wheel reproduzem init → candidata → consulta → mudança → recuperação.

**Blocked by:** T16, T19, T20, T21.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P4. **Problemas do brief:** 9,10,11,12.

## Problema e resultado

Novos contratos e skills precisam funcionar também no pacote instalado.

## Como implementar

Executar gates existentes sequencialmente; incluir novos schemas/preset/skill no wheel; verificar help/docs/aliases e plataformas declaradas; registrar SHAs/digests.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Matriz declara executado/skipped/unsupported por perfil; zero corpus/cache/segredos no bundle; evidência vinculada ao mesmo candidato.
- [ ] Cenário sintético completo no core e MCP real; falha de rede/harness mantém ativo; wheel encontra recursos sem checkout.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Cenário sintético completo no core e MCP real; falha de rede/harness mantém ativo; wheel encontra recursos sem checkout.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Sem commit/tag/push/publicação implícita; skip obrigatório não conta como gate verde.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
