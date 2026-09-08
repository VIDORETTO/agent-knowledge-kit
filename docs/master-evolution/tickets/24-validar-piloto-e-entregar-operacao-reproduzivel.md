# T24 — Validar piloto e entregar operação reproduzível

**What to build:** Operador executa projeto ML e projeto neutro e recebe evidência de prontidão por capacidade.

**Blocked by:** T11, T22, T23.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P5. **Problemas do brief:** 1,2,3,4,5,6,7,8,9,10,11,12.

## Problema e resultado

Entrega técnica precisa demonstrar o ciclo completo e seus limites ao usuário.

## Como implementar

Rodar roteiro sintético e piloto autorizado; verificar todos os requisitos do brief; separar aprovado tecnicamente de autorização pública; registrar decisões pendentes e handoff.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Nenhum requisito sem evidência ou pendência explícita; métricas reais não confundidas com fixture; autorização de publicação é externa ao aceite técnico.
- [ ] Init retomado, pergunta citada, nova fonte, conflito, remoção, crash, backup/restore e delegação revogada no mesmo protocolo.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Init retomado, pergunta citada, nova fonte, conflito, remoção, crash, backup/restore e delegação revogada no mesmo protocolo.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não inventar fontes reais, receita de vendas ou prontidão multi-host.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
