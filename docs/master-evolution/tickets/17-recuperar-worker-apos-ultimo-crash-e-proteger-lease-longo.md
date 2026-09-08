# T17 — Recuperar worker após último crash e proteger lease longo

**What to build:** O operador vê job terminal/recuperável após falhas e nenhum worker antigo confirma efeito de outro owner.

**Blocked by:** T01.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P4. **Problemas do brief:** 4,10.

## Problema e resultado

Auditoria indica possível running órfão na última tentativa; execução longa precisa de contrato de ownership.

## Como implementar

Reproduzir hipótese pela interface; definir transições na expiração final; renovar ownership ou bloquear reassunção enquanto dono verificavelmente vivo; usar fencing/recibos antes de permitir sobreposição.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Se hipótese não reproduzir, registrar evidência e limitar mudança ao gap confirmado; distinguir retryável de blocked; preservar idempotência existente.
- [ ] Três crashes com leases expiradas não deixam running eterno; job lento não duplica efeito; dono antigo não confirma após perda de lease.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Três crashes com leases expiradas não deixam running eterno; job lento não duplica efeito; dono antigo não confirma após perda de lease.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Sem prometer exactly-once para efeitos externos que não forneçam idempotência.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
