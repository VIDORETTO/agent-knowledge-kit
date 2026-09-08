# T05 — Governar uma fonte do cadastro ao uso autorizado

**What to build:** O agente cadastra fonte e recebe decisão explícita sobre captura, indexação, derivados e redistribuição.

**Blocked by:** T04.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P2. **Problemas do brief:** 7.

## Problema e resultado

Metadados livres não expressam uso comercial, vigência e região.

## Como implementar

Estender registro versionado e política de uso; persistir metadados desde normalização até source mapping; impedir inferência permissiva em migração.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Região/datas/autor/direitos rastreáveis; registro v1 permanece compatível/restrito; alteração de política invalida autorização anterior.
- [ ] Fonte com captura permitida e redistribuição negada pode seguir somente usos autorizados; unknown bloqueia ação dependente; fonte incompleta não é retirada.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Fonte com captura permitida e redistribuição negada pode seguir somente usos autorizados; unknown bloqueia ação dependente; fonte incompleta não é retirada.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não emitir parecer legal nem tratar URL pública como licença.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
