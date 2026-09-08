# T08 — Construir candidata multilíngue sem interromper leitores

**What to build:** O agente compara perfis no mesmo corpus e prepara snapshot multilíngue isolado.

**Blocked by:** T07.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P2. **Problemas do brief:** 8.

## Problema e resultado

O piloto PT-BR não pode depender de default focado em inglês.

## Como implementar

Usar fingerprint e rebuild existentes; integrar perfil ao projeto/preset; comparação com mesmos casos e identidade de modelo; não trocar default global.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Recibo fixa corpus/modelo/perfil; promoção só após gate; memória fake não é evidência de qualidade semântica.
- [ ] Mudança de perfil exige full rebuild; falha de download/rebuild deixa reader antigo utilizável; português acentuado é consultado no MCP real.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Mudança de perfil exige full rebuild; falha de download/rebuild deixa reader antigo utilizável; português acentuado é consultado no MCP real.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não selecionar reranker por suposição nem usar métricas históricas FastAPI como resultado ML.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
