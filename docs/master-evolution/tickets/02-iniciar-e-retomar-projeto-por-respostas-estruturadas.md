# T02 — Iniciar e retomar projeto por respostas estruturadas

**What to build:** O usuário interrompe a conversa e outro harness a retoma sem repetir decisões confirmadas.

**Blocked by:** T01.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P1. **Problemas do brief:** 1,2.

## Problema e resultado

O agente não tem sessão persistente de configuração de projeto.

## Como implementar

Criar o protocolo de init e sessão dos contratos de estado; persistir revisão após resposta aceita; retornar perguntas pendentes e erros estruturados; incluir instrução operacional no pacote instalado.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Idempotência e retomada verificadas; estado desconhecido não vira sucesso; pergunta sobre sentido do curso é obrigatória quando ambíguo.
- [ ] Iniciar projeto só de conhecimento, responder objetivo, reiniciar processo e ler mesma sessão; resposta com revisão antiga falha sem sobrescrever.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Iniciar projeto só de conhecimento, responder objetivo, reiniciar processo e ler mesma sessão; resposta com revisão antiga falha sem sobrescrever.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Sem geração de curso, captura de fontes ou LLM interna.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
