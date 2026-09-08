# T18 — Agendar reconcile e worker com parada e retomada

**What to build:** Supervisor configurado detecta mudança e prepara candidata sem publicação automática.

**Blocked by:** T05, T17.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P4. **Problemas do brief:** 4,10.

## Problema e resultado

Adicionar arquivo não inicia o ciclo por si só.

## Como implementar

Criar configuração/runbook e integração verificável de scheduler externo; invocar seams existentes; persistir tick/status; polling recupera eventos perdidos.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Instalação de agenda exige configuração explícita; execução limitada não se confunde com daemon; exemplos Windows e Linux validados nas plataformas disponíveis.
- [ ] Reiniciar supervisor após mudança pendente gera um efeito; arquivo duplicado não duplica job; parada deixa estado recuperável; origem indisponível conserva fontes.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Reiniciar supervisor após mudança pendente gera um efeito; arquivo duplicado não duplica job; parada deixa estado recuperável; origem indisponível conserva fontes.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Não instalar agenda na máquina do usuário como efeito de teste.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
