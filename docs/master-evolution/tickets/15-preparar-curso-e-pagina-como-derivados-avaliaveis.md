# T15 — Preparar curso e página como derivados avaliáveis

**What to build:** O harness entrega candidata de aula/página ligada a fontes e decisões, pronta para revisão.

**Blocked by:** T03, T11, T12, T14.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P3. **Problemas do brief:** 1,3,5,7.

## Problema e resultado

Curso e página não têm fluxo próprio de geração/validação no projeto.

## Como implementar

Ampliar contrato de derivados opt-in; course objectives/exercícios e page claims; autorização de artefatos permitidos; validar lineage e restrições comerciais.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Curso e página têm versões independentes e composição conjunta possível; nenhum texto derivado conta como prova independente de si mesmo.
- [ ] Alterar fonte invalida aula correspondente; preço ausente bloqueia oferta pública; claim sem prova não passa avaliação; só conhecimento não exige derivados.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Alterar fonte invalida aula correspondente; preço ausente bloqueia oferta pública; claim sem prova não passa avaliação; só conhecimento não exige derivados.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não construir editor visual, checkout ou plataforma de curso.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
