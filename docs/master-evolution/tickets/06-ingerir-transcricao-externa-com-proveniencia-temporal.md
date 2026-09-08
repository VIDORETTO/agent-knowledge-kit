# T06 — Ingerir transcrição externa com proveniência temporal

**What to build:** O agente consulta transcrição autorizada e cita segmento correto com versão.

**Blocked by:** T05.

**Status:** verified-local; external boundaries remain explicitly blocked by scope. See [implementation evidence](../IMPLEMENTATION-EVIDENCE.md).

**Fase:** P2. **Problemas do brief:** 7.

## Problema e resultado

Transcrição externa existe, mas falta contrato de rastreabilidade comercial completo.

## Como implementar

Usar Markdown externo já suportado; vincular vídeo/canal/captura/método/permissão; validar segmentos temporais; ligar resumo derivado à transcrição.

Trabalhar pela interface pública estabelecida no plano TDD. Uma fatia de comportamento por ciclo; modificar contrato, implementação, distribuição e documentação necessários àquela fatia. Consultar os documentos irmãos SPEC, STATE-CONTRACTS, KNOWLEDGE-QUALITY e TDD-EXECUTION, conforme o assunto. As referências atuais de código ficam no diagnóstico e na auditoria, não são novos módulos obrigatórios.

## Critérios de aceite

- [ ] Permissão de resumo não libera transcrição pública; instruções maliciosas da fonte permanecem dados; limites de entrada aplicados.
- [ ] Fixture com dois segmentos retorna o localizador esperado; tempo negativo/invertido é rejeitado; sem tempo conhecido não há timestamp inventado.
- [ ] Regressões relevantes do comportamento anterior passam; resultado observável pelo agente e erros estruturados documentados.
- [ ] Evidência registra baseline, teste RED com causa esperada, GREEN, limitações e arquivos alterados. Nenhuma mudança de corpus/índice ativo real para validar fixture.

## Primeiro ciclo TDD

Transformar o primeiro cenário descrito em “Fixture com dois segmentos retorna o localizador esperado; tempo negativo/invertido é rejeitado; sem tempo conhecido não há timestamp inventado.” em um teste mínimo na seam pública. Observar falha pela ausência/defeito do comportamento, não por ambiente quebrado; implementar o mínimo; repetir pelos demais cenários. Fixtures têm expectativas literais revisadas, não calculadas pelo próprio código sob teste. Se o comportamento já passar, registrar caracterização e corrigir somente a lacuna demonstrada.

## Fora do escopo

Sem downloader YouTube ou parser nativo SRT/VTT.

## Recuperação e handoff

Falha deixa estado anterior utilizável ou operação explicitamente recuperável. Novos formatos exigem leitura compatível e migração reversível até adoção confirmada. Não apagar versão antiga para fazer teste passar. Entregar resumo do comportamento, comandos efetivamente executados, resultado, riscos e próximo ticket desbloqueado; não marcar ticket concluído apenas por ter criado os arquivos.
