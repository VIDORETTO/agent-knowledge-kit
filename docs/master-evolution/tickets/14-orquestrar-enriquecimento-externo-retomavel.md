# T14 — Orquestrar enriquecimento externo retomável

**What to build:** O agente despacha enriquecimento e retoma após indisponibilidade sem alterar ativo.

**Blocked by:** T12.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P3. **Problemas do brief:** 5.

## Problema e resultado

Request/submit existem, mas acompanhamento durável do harness é incompleto.

## Como implementar

Estender request/receipt existentes com ack, timeout, cancelamento e tentativas; vincular hashes/base/política; exportar status ao harness.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Nenhuma chamada a modelo dentro do core; resultado só altera candidata; orçamento/artefatos permitidos respeitados.
- [ ] Resultado atrasado de base anterior é rejeitado; retry mantém identidade e não duplica efeito; harness ausente informa ação pendente.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Resultado atrasado de base anterior é rejeitado; retry mantém identidade e não duplica efeito; harness ausente informa ação pendente.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não colocar credenciais ou scripts arbitrários no request.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
