# T20 — Restaurar backup consistente de projeto e revogações

**What to build:** O operador restaura em local isolado e volta a consultar sem repetir efeitos ou liberar revogados.

**Blocked by:** T16, T17.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P4. **Problemas do brief:** 10.

## Problema e resultado

Backup precisa preservar composição, fila e tombstones como unidade.

## Como implementar

Adicionar procedimento/exportação consistente sob coordenação; manifest/checksums/retention; restore valida compatibilidade e permite índice reconstruído a partir de corpus autorizado.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Ensaio mede RPO/RTO; segredos excluídos ou tratados em política privada; produção original permanece intacta.
- [ ] Backup durante job em curso restaura estado recuperável; tombstone posterior aplicável não é perdido; recibo impede duplicação; checksum inválido bloqueia restore.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Backup durante job em curso restaura estado recuperável; tombstone posterior aplicável não é perdido; recibo impede duplicação; checksum inválido bloqueia restore.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não restaurar índice isolado como se fosse todo o projeto.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
