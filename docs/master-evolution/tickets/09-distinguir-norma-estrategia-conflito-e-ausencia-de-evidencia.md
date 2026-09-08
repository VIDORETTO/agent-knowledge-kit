# T09 — Distinguir norma, estratégia, conflito e ausência de evidência

**What to build:** O harness recebe evidências classificadas e sabe quando responder com ressalva ou abster-se.

**Blocked by:** T07.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P2. **Problemas do brief:** 7,8.

## Problema e resultado

Drift de versão não equivale a detectar contradições factuais.

## Como implementar

Adicionar claims/conflitos revisáveis e outcomes do contrato de qualidade; priorizar oficial vigente por região para intenção normativa; instruir router.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Fonte e claim mantêm identidades distintas; ausência de evidência vira outcome explícito; citações ficam próximas à afirmação no teste de harness.
- [ ] Opinião popular não vence norma aplicável; norma expirada e região errada não sustentam resposta; duas regras conflitantes geram conflicting.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Opinião popular não vence norma aplicável; norma expirada e região errada não sustentam resposta; duas regras conflitantes geram conflicting.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não converter relevance score em confiança factual.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
