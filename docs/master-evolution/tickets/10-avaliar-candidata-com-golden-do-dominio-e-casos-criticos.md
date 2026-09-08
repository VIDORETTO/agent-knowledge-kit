# T10 — Avaliar candidata com Golden do domínio e casos críticos

**What to build:** O agente recebe relatório comparativo que bloqueia candidatas com regressão crítica.

**Blocked by:** T08, T09.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P2. **Problemas do brief:** 8.

## Problema e resultado

Métricas existentes não demonstram qualidade no domínio alvo.

## Como implementar

Estender evaluator/receipts; curar 60 casos por distribuição definida; separar ajuste/holdout; avaliar respostas via harness e revisão independente.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Todos os limiares/fatias/denominadores relatados; identidade do Golden e snapshot fixada; harness ausente fica pending/failed.
- [ ] Candidata com Recall maior mas vazamento/revogação falha; caso não revisado não libera gate; citação aponta versão/trecho exato.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Candidata com Recall maior mas vazamento/revogação falha; caso não revisado não libera gate; citação aponta versão/trecho exato.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não gerar e autoaprovar respostas de referência.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
