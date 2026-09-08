# T23 — Delegar apenas atualizações factuais de baixo risco

**What to build:** Responsável autoriza política limitada e o agente publica somente mudanças elegíveis.

**Blocked by:** T10, T16, T19, T21, T22.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P5. **Problemas do brief:** 6.

## Problema e resultado

Autonomia total removeria gates necessários; delegação precisa de escopo.

## Como implementar

Adicionar autorização delegada com owner/escopo/ações/prazo/limites; produzir receipt via engine existente; revalidar no commit e disponibilizar kill switch.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Padrão continua manual; decisão auditável; nenhuma promoção por flag genérica; revogação da delegação cancela permissão imediatamente.
- [ ] Factual autorizada passa; conflito, conceito, preço, licença incerta, prazo expirado ou revogação bloqueiam; receipt de outro hash não serve.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Factual autorizada passa; conflito, conceito, preço, licença incerta, prazo expirado ou revogação bloqueiam; receipt de outro hash não serve.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Sem publicação pública irrestrita nem autorização inferida de fonte oficial.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
