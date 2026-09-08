# T13 — Revogar fonte e derivados sem ressuscitar conteúdo

**What to build:** A retirada de uma fonte impede uso de todos os derivados afetados, inclusive em snapshots antigos.

**Blocked by:** T12, T07.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P3. **Problemas do brief:** 3,7.

## Problema e resultado

Revogação atual precisa alcançar curso/página e lineage geral.

## Como implementar

Estender tombstones/lineage e validação de readers/publicação/rollback; preservar auditoria segura; permitir eliminação de bytes privados conforme retenção.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Invalidação transitiva imediata e auditável; histórico de hashes não exige guardar dados pessoais; readmission é explícita.
- [ ] Revogar fonte de aula e claim de página bloqueia ambos; outra aula segue válida; rollback e cache não restauram conteúdo revogado.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Revogar fonte de aula e claim de página bloqueia ambos; outra aula segue válida; rollback e cache não restauram conteúdo revogado.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não apagar o projeto inteiro nem tratar timeout como remoção.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
