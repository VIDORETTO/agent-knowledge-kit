# T16 — Promover composição do projeto de forma atômica

**What to build:** Uma candidata avaliada/aprovada vira revisão ativa única e pode ser revertida com segurança.

**Blocked by:** T10, T13, T15.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P3. **Problemas do brief:** 3,6.

## Problema e resultado

Nova composição não pode ativar parcialmente RAG, skill, curso e página.

## Como implementar

Estender transação e receipts existentes à composição; revalidar base/política/revogação no commit; preservar referência da release e readers pinned.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Nenhum leitor mistura versões; inspeção mostra composição/hash; histórico e resíduos distinguíveis; mudança factual preserva bytes dos derivados inalterados.
- [ ] Crash antes/depois de troca recupera composição inteira; aprovação de hash anterior falha; rollback com tombstone vigente é bloqueado.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Crash antes/depois de troca recupera composição inteira; aprovação de hash anterior falha; rollback com tombstone vigente é bloqueado.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não habilitar autopublish nem remover approval gate.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
