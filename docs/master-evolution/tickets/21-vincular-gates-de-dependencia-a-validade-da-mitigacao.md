# T21 — Vincular gates de dependência a validade da mitigação

**What to build:** Release gate distingue auditoria bruta, mitigação vigente e decisão expirada.

**Blocked by:** T01.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P4. **Problemas do brief:** 11.

## Problema e resultado

Decisão residual existe, mas validade temporal não é verificada pelo checker.

## Como implementar

Estender validação com relógio controlável e threat-model identity; auditar dependências do artefato exato; manter matriz support/tolerated.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Owner/prazo/evidência obrigatórios; Python 3.14 tolerado não vira suportado por teste local; upstream status verificado na execução.
- [ ] Decisão expirada, versão diferente, novo advisory ou threat model alterado bloqueia; decisão vigente não mascara raw audit com findings.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Decisão expirada, versão diferente, novo advisory ou threat model alterado bloqueia; decisão vigente não mascara raw audit com findings.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não atualizar dependências indiscriminadamente nem declarar zero CVEs por allowlist.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
