# Plano TDD por ciclos verticais

[Índice](README.md) · [Tickets](TICKETS.md) · [Aceitação](VALIDATION.md)

Status: **planejamento**; nenhum teste novo foi escrito ou executado. Os seams
abaixo são propostas para revisão, não autorização implícita para implementar.

## Disciplina

Aplicar `RED → GREEN → REFACTOR`, um comportamento por vez. O pedido do usuário
define REFACTOR após proteção do comportamento. Não criar todos os testes de
todas as fases de uma só vez. Confirmar o RED por falha na expectativa funcional,
não por fixture quebrada ou import ausente acidental.

Testar import público da raiz, CLI, JSON documentado, arquivos de artefato e MCP.
Não importar helpers novos, verificar chamadas privadas ou ordem interna, nem
consultar tabelas SQLite como prova de que um job é observável. Preferir filesystem
temporário real. Relógio e processo externo são seams legítimos de substituição.

## Seams propostos antes dos testes

| Grupo | Seam | Observação externa |
|---|---|---|
| Ciclo de pacote | docops.plan/preview/apply/inspect | Resultado, revisão ativa, arquivos e blockers |
| Candidata | CLI candidate e validate/evaluate | Candidata, aprovação e composição publicada |
| Fontes/jobs | CLI source/event/work/jobs | Snapshot, pendência, resultado e retries |
| Conversas | CLI learning e busca MCP | Quarentena/admissão e presença factual |
| Backend | Processo MCP real ou servidor externo de fixture | Protocolo, erro terminal, busca e permissões |
| Harness | Tarefa/recibo e execução externa | Artefatos, evidências e respostas avaliadas |

Raiz e CLI são preferíveis a ampliar exports para cada módulo interno. Detalhes
dos comandos novos em CONTRACTS permanecem propostos. Exemplos de estilo existentes:
[test_public_interface](../../tests/test_public_interface.py),
[test_public_seams](../../tests/test_public_seams.py),
[test_promotion_recovery](../../tests/test_promotion_recovery.py).

## Primeiro ciclo obrigatório — T01

Nome comportamental sugerido:
`test_document_update_does_not_overwrite_externally_enriched_skill`.

Preparação pelo seam público:

1. Criar fonte Markdown sintética em diretório temporário.
2. Gerar pacote por OperationRequest/plan/apply.
3. Acrescentar à skill um parágrafo conceitual literal conhecido, representando
   o enriquecimento externo permitido pelo produto. Não editar estado privado para
   fingir que a evidência existe.
4. Alterar a fonte e construir um novo plano de atualização.

**RED:** a operação deve recusar a substituição com código proposto
`skill_update_requires_review`; o parágrafo e a geração ativa permanecem intactos.
O caminho atual tende a regenerar scaffold (E04); isso deve ser observado ao
executar o teste, não apenas presumido nesta documentação.

**GREEN mínimo:** registrar inventário com hashes na geração inicial e verificar
integridade/propriedade antes de planejar ou aplicar substituição. Se houver
edição externa, bloquear. Não implementar fila, aprovação, LLM ou RAG novo.

**REFACTOR:** concentrar a guarda de propriedade sem alterar o seam nem a expectativa.

Próximos ciclos do mesmo ticket, somente após o primeiro passar:

- scaffold inalterado continua atualizável;
- capítulo adicional e arquivo gerado removido recebem proteção;
- pacote legado sem baseline confiável recebe resultado de migração explícito;
- nova edição entre plan e apply é rejeitada pelas verificações de estado.

Não comparar apenas SKILL.md: o contrato protege o conjunto de artefatos. Porém
não exigir todos os cenários no primeiro GREEN; avançar verticalmente.

## Mapa dos ciclos seguintes

| Ticket | Primeiro RED | GREEN mínimo | REFACTOR protegido |
|---|---|---|---|
| T02 | Artefato alterado não pode continuar avaliado | Hashes nas evidências e invalidação | Centralizar composição |
| T03 | Atualização factual muda skill | Preservar camada e declarar defasagem | Preparação por camada |
| T04 | Preparar candidata altera ativa | Staging retornado sem promoção | Reusar motor transacional |
| T05 | Backend com erro é reportado indexed | Validar término, perfil e busca | Envelope de resultado |
| T06 | Saída externa fora de escopo é aceita | Validar tarefa/recibo/arquivos | Isolar importação |
| T07 | Resposta sem suporte passa no gate | Julgamentos independentes e métricas | Separar tipos de avaliação |
| T08 | Candidata alterada após aprovação publica | Verificar hashes/base sob lease | Decisão única de publicação |
| T09 | Não é possível restaurar geração após sucesso | Histórico e restauração validada | Separar retenção de cleanup |
| T10 | Fonte adicional remove anterior | Registro e completude por escopo | Descoberta versus reconciliação |
| T11 | Evento repetido/reinício duplica trabalho | Fila durável e chave idempotente | Encapsular armazenamento |
| T12 | Crash após publicação causa republicação | Recibo de efeito e retomada | Classificar retries |
| T13 | Reindex idêntico gera skill candidata | Diff/impacto e cursores separados | Política de lote |
| T14 | Sessão consulta composição mista | Fixar geração e restringir ferramentas | Capacidades de runtime |
| T15 | Um arquivo exige reembedding de todos | Snapshot consistente e diff | Estratégia de reuso |
| T16 | Citação perde localizador disponível | Proveniência por formato | Modelo comum de localizador |
| T17 | Proposta não revisada aparece no RAG | Quarentena e decisão verificável | Alegação/evidência/revisão |
| T18 | Feedback altera Golden revisado | Investigação e candidato não revisado | Sinal versus evidência |

Cada arquivo de ticket detalha cenários adicionais, dependências e rollback.
Para tempo, usar relógio controlável e testar os instantes antes/depois do prazo;
não esperar 24 horas em teste. Para falhas MCP, usar processo externo de fixture;
não monkeypatch de helpers do operador. Para reuso do índice, combinar relatório
público com busca real, sem depender de IDs internos do Chroma.

## Critério de encerramento de cada ciclo

- Falha RED correspondeu ao comportamento desejado.
- GREEN resolveu o caso sem antecipar módulos de tickets futuros.
- Refactor preservou expectativas públicas.
- Checks pertinentes passaram; nenhum schema espelhado ficou divergente.
- Relato separa comportamento determinístico, integração real e avaliação do harness.
- Nenhum resultado de fixture foi anunciado como desempenho do corpus real.
