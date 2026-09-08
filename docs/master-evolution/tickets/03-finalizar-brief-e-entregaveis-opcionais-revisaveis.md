# T03 — Finalizar brief e entregáveis opcionais revisáveis

**What to build:** O agente finaliza revisão privada com artefatos separados e lista as pendências que impedem cada entregável.

**Blocked by:** T02.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P1. **Problemas do brief:** 1,2.

## Problema e resultado

Não existe composição explícita de brief, curso, página e decisões.

## Como implementar

Validar contratos de brief/curso/página; gerar projeções Markdown do estado canônico; preservar AGENTS apenas como operação estável; referência cruzada por IDs.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Artefatos têm revisão e origem; rerun não sobrescreve edição divergente; nenhuma promessa/preço/garantia é inventada.
- [ ] Finalizar conhecimento sem curso/página funciona; curso ambíguo ou preço desconhecido mantém apenas o entregável afetado pendente; corrigir público invalida derivados corretos.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Finalizar conhecimento sem curso/página funciona; curso ambíguo ou preço desconhecido mantém apenas o entregável afetado pendente; corrigir público invalida derivados corretos.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não renderizar nem publicar site.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
