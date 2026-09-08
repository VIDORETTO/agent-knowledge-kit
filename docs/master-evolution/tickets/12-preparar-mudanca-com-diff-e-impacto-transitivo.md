# T12 — Preparar mudança com diff e impacto transitivo

**What to build:** O agente propõe mudança tipada e vê exatamente o que será invalidado antes de executar.

**Blocked by:** T04, T05.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P3. **Problemas do brief:** 3,12.

## Problema e resultado

Plan atual cobre pacote, não mudanças de projeto e derivados.

## Como implementar

Adicionar change proposal com base/policy hash e grafo de dependências; compilar para plan/preview existente; se extração necessária, caracterizar seam e extrair só responsabilidade tocada.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Diff inclui artefatos afetados e justificativa; dry-run sem efeitos; falha mantém release ativa.
- [ ] Adicionar fonte afeta dependentes corretos; mudar texto da página não reindexa fatos; base divergente impede apply; ciclo no grafo falha.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Adicionar fonte afeta dependentes corretos; mudar texto da página não reindexa fatos; base divergente impede apply; ciclo no grafo falha.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Sem reescrever operations inteiro ou criar segundo motor de promoção.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
