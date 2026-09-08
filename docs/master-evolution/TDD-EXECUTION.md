# Plano TDD e protocolo de execução por uma IA de implementação

Este guia orientou a implementação e a validação locais dos tickets; os testes e evidências efetivamente executados estão em [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md). As seams abaixo continuam sendo o contrato de revisão e reutilizam a política existente de `tests/SEAMS.md:3`; não autorizam publicação externa, indexação do corpus real ou testes com credenciais ausentes.

## Pacote de contexto mínimo

Ler MASTER-PLAN, MASTER-IMPROVEMENT-PLAN e o ticket escolhido. Depois ler SPEC, os trechos aplicáveis de STATE-CONTRACTS/KNOWLEDGE-QUALITY e este arquivo. Usar CURRENT-STATE-EVIDENCE apenas para localizar código atual; confirmar nomes/linhas no novo checkout. Para T11/T15/T24 acrescentar MERCADO-LIVRE-PRESET. Não carregar todos os 24 tickets no mesmo contexto.

Instrução pronta para repassar:

> Implemente apenas TNN do roadmap master-evolution. Confirme baseline e blockers. Leia o ticket, contratos e política de testes. Preserve lifecycle, isolamento e gates existentes. Planeje em tasks/todo.md; execute uma fatia de comportamento por ciclo RED → GREEN. Não implemente tickets seguintes. Não use corpus real, não publique e não instale scheduler durante testes. Entregue evidência de aceite, regressões, recuperação, limitações e próximo ticket elegível. Se encontrar comportamento já pronto, prove e não o reescreva. Se o contrato for contraditório, registre a divergência antes de fazer escolha que altere o produto.

## Seams e antecedentes

| Seam | Comportamento observado | Antecedentes atuais | Tickets |
|---|---|---|---|
| CLI subprocesso + JSON público | Init/inspect/change, códigos de saída, retomada entre processos | tests/test_cli.py; tests/test_public_interface.py; tests/test_public_seams.py | T01–T06, T11–T12, T18–T19 |
| API raiz import docops + artefatos públicos | Plan/apply/candidate/receipts/rollback e projeções de estado | tests/test_candidate_publication.py; tests/test_history_rollback.py; tests/test_promotion_recovery.py | T04–T05, T12–T17, T20, T23 |
| Reader público → MCP real | Recuperação, isolamento, metadados, snapshot, rebuild e revogação | tests/test_reader_sessions.py; tests/test_rag_snapshots.py; tests/test_formats_portuguese.py | T06–T10, T13, T16, T24 |
| Request/submit público de harness | Payload, timeout, resultado stale, orçamento e artefatos permitidos | tests/test_enrichment.py; tests/test_candidate_evaluation.py | T09–T10, T14–T15 |
| Gates executáveis como ferramentas | Contratos, docs, dependências, wheel e matriz | tests/test_contract_doc_drift.py; tests/test_dependency_evidence.py; tests/test_release_gates.py | T01, T21–T22 |

Não criar seam nova somente para espiar estado interno. Estado persistido pode ser conferido pelo JSON público/inspect/export; consulta direta a tabelas internas não deve ser aceite de produto. Testes de infraestrutura existentes podem permanecer quando protegem adapters, leases ou falhas específicas.

## Ciclo obrigatório

1. Escolher um cenário observável do ticket e fixture pequena com resultado conhecido.
2. Executar o teste e registrar RED: erro esperado do comportamento ausente. Import inexistente pode caracterizar uma nova interface, mas não substitui depois o cenário funcional. Falha de Python/dependência não é RED do produto.
3. Implementar o mínimo para esse cenário; manter saídas públicas, migração e recursos instalados consistentes.
4. Executar teste e registrar GREEN; fazer próximo cenário de falha ou recuperação antes de ampliar escopo.
5. Após fatia verde, revisar simplicidade/localidade; refatoração é etapa de revisão, protegida pelos testes de comportamento.
6. Rodar regressões pertinentes e gates do ticket. Atualizar evidência e handoff; não marcar aceite não demonstrado.

Não escrever todos os testes de uma fase para depois implementar tudo. Não mockar collaborators internos ou afirmar ordem de chamadas. Mock/fake somente para rede externa, harness externo, relógio e falhas controladas; recuperação e contrato semântico que exigem MCP devem ter pelo menos uma execução real isolada. Contratos com resultados numéricos usam referência literal independente.

## Fixtures e cenários essenciais

- Dois projetos A/B com palavras idênticas e fatos distintos: busca A nunca retorna documento B.
- Fonte oficial BR vigente e opinião recente de outra região: pergunta normativa usa somente evidência elegível; sem ela, insufficient_evidence.
- Fonte antiga substituída e conflito aberto: testar as_of antes/depois e conflicting, sem escolher apenas por data de captura.
- Fonte autorizada para indexação privada mas sem redistribuição: busca privada elegível e bundle público bloqueado.
- Transcrição sintética em 00:10–00:20: citação resolve nesse intervalo; resumo herda origem e direitos.
- Fonte revogada após cache/reader: nenhum conteúdo nem derivado retornado; rollback também bloqueia restauração.
- Crash antes/depois do commit de composição: inspeção retorna composição velha inteira ou nova inteira, nunca mistura.
- Crash na última tentativa do worker e job longo: estado terminal/recuperável observável e nenhum efeito duplicado por claim concorrente.
- Relógio após validade de delegação/mitigação: gate falha com motivo específico; não depender da data da máquina para o teste.
- Backup restaurado sem tombstone ou com checksum errado: restore recusa; restore consistente preserva receipts e revogações.

## Comandos e evidência

Executar no ambiente suportado do projeto, prefixando shell com rtk conforme instrução local. No Windows auditado, foi usado `.venv/Scripts/python.exe`. Não confundir Python global 3.14 tolerado com a matriz declarada.

Exemplos existentes: `python -m pytest -q tests/test_cli.py`; `python scripts/check_documentation.py --json`; `python scripts/check_contracts.py`; `python scripts/check_public_seams.py`; `git diff --check`. Conferir help dos demais scripts antes de invocá-los. Os comandos de projeto descritos em STATE-CONTRACTS têm aliases planos executáveis na CLI e permanecem separados das integrações MCP/full que exigem runtime externo.

Para T22, reutilizar runner de release gates e executar builds sequencialmente. Não rodar gate que indexa corpus real: usar diretórios temporários e configuração fixture. Não aceitar test double como benchmark de embeddings. Não remover gate ou diminuir limiar para obter verde.

Registro por ticket: SHA inicial/final se houver commit; dirty state; ambiente/perfil; comando exato; exit code; número passed/skipped/failed; RED e GREEN; localização segura do relatório; comportamento antes/depois; riscos; rollback; blockers satisfeitos. Conteúdo protegido/consultas/segredos não entram nos relatórios públicos.

## Verificação realizada no planejamento

No baseline c438c82, a CLI de worker mostrou --once obrigatório e ausência de loop. O checker documental retornou ok=true, 77 Markdown, mesmo com a recomendação de loop na skill distribuída: evidencia a lacuna de flags.

Run A: tests/test_cli.py, test_contract_doc_drift.py, test_source_registry.py, test_candidate_publication.py, test_worker.py, test_enrichment.py e test_reader_sessions.py: **50 passed em 233,58s**.

Run B: tests/test_source_registry.py, test_formats_portuguese.py, test_reader_sessions.py, test_rag_snapshots.py, test_dependency_evidence.py e test_support_matrix.py: **42 passed em 59,90s**. Há sobreposição entre runs; não somar como 92 testes únicos.

Esses resultados demonstram contratos existentes selecionados. Não são suíte completa, validação nova do CI, benchmark multilíngue real, auditoria online de CVEs, avaliação de conteúdo Mercado Livre nem permissão comercial. Números históricos em tasks/todo.md e AGENTS não foram reutilizados como medição desta entrega.
