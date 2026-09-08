# T04 — Adotar pacote existente sem alterar a geração ativa

**What to build:** Um agente registra um pacote legado em um projeto e continua consultando a mesma release.

**Blocked by:** T03.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P1. **Problemas do brief:** 2.

## Problema e resultado

Projeto novo deve coexistir com pacote/state e schemas atuais.

## Como implementar

Implementar importação/migração explícita e dry-run; preservar identidades; versão desconhecida falha; manter leitura v1 durante expand–contract.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Relatório identifica origem, campos pendentes e backup; nenhum índice é reconstruído só por importar; rollback de migração demonstrado.
- [ ] Importar fixture v1 duas vezes preserva source IDs/release; falha no meio mantém pacote original válido; migração não infere direitos novos.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Importar fixture v1 duas vezes preserva source IDs/release; falha no meio mantém pacote original válido; migração não infere direitos novos.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Sem migração em massa do corpus real.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
