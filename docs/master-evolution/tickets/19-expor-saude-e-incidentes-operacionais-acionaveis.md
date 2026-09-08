# T19 — Expor saúde e incidentes operacionais acionáveis

**What to build:** O operador identifica fila parada, revisão pendente e índice incompatível por saída estruturada.

**Blocked by:** T18.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P4. **Problemas do brief:** 10.

## Problema e resultado

Status parcial não explica atraso de fonte/fila ao agente.

## Como implementar

Estender inspeção/doctor/status público; métricas e incidentes redigidos; idade de fila/frescor/último sucesso; adapters externos de alerta opt-in.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Estados healthy/degraded/blocked com causa e ação; diagnóstico não executa rebuild/publicação; limiares configuráveis.
- [ ] Dois ciclos perdidos geram incidente; repetição deduplica; recuperação fecha incidente; logs não contêm consulta, token ou documento.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Dois ciclos perdidos geram incidente; repetição deduplica; recuperação fecha incidente; logs não contêm consulta, token ou documento.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não enviar email/Slack nem criar stack de observabilidade obrigatória.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
