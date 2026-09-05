# Tickets e plano de entrega

[Índice](README.md) · [Especificação](SPEC.md) · [TDD](TDD.md)

Status: **18 tickets propostos, nenhum implementado ou publicado em rastreador**.
Um arquivo por ticket, em ordem topológica. A documentação está em docs/ por
solicitação do usuário; não é backlog temporário em .scratch/.

## Backlog

| Ticket | Entrega | Blocked by |
|---|---|---|
| [T01](tickets/01-protect-enrichment.md) | Proteger a skill enriquecida contra sobrescrita | Nenhuma |
| [T02](tickets/02-revision-evidence.md) | Vincular revisões e evidências ao conteúdo | T01 |
| [T03](tickets/03-rag-preserve-skill.md) | Atualizar corpus preservando a camada conceitual | T01, T02 |
| [T04](tickets/04-prepare-candidate.md) | Preparar candidata sem ativar | T02, T03 |
| [T05](tickets/05-verify-index.md) | Comprovar indexação e perfil reais | T02, T04 |
| [T06](tickets/06-external-enrichment.md) | Receber enriquecimento externo em candidata | T04 |
| [T07](tickets/07-candidate-evaluation.md) | Avaliar candidata e respostas com evidência independente | T05, T06 |
| [T08](tickets/08-approve-publish.md) | Aprovar e publicar hashes exatos | T04, T07 |
| [T09](tickets/09-history-rollback.md) | Reter e restaurar gerações publicadas | T08 |
| [T10](tickets/10-source-registry.md) | Registrar fontes e reconciliar escopo completo | T02, T03 |
| [T11](tickets/11-durable-events.md) | Persistir eventos com deduplicação e debounce | T10 |
| [T12](tickets/12-resumable-worker.md) | Executar jobs com retomada e indexação autorizada | T08, T11 |
| [T13](tickets/13-conceptual-triggers.md) | Disparar enriquecimento por impacto conceitual | T06, T10, T12 |
| [T14](tickets/14-pinned-readers.md) | Fixar geração e restringir MCP de consulta | T08, T09 |
| [T15](tickets/15-incremental-snapshot.md) | Reaproveitar índice com snapshot consistente | T05, T09, T14 |
| [T16](tickets/16-formats-portuguese.md) | Preservar localizadores e avaliar português | T05, T07, T10 |
| [T17](tickets/17-conversation-learning.md) | Verificar propostas de conversa antes da admissão | T08, T10, T14 |
| [T18](tickets/18-usage-feedback.md) | Priorizar investigação por uso e qualidade | T07, T12, T17 |

## Fases e condições de ativação

1. **Proteção — T01–T03:** impedir perda de enriquecimento e separar camadas.
2. **Ciclo editorial manual — T04–T09:** preparar, avaliar, aprovar, publicar e reverter.
3. **Coordenação — T10–T14:** fontes, fila, jobs, gatilhos e leitores consistentes.
4. **Eficiência/diversidade — T15–T16:** reuso do índice e formatos/português.
5. **Aprendizado assistido — T17–T18:** conversa verificada e feedback operacional.

As fases são marcos de produto. A coluna Blocked by define dependências reais;
não adicionar bloqueios entre tickets independentes apenas por pertencerem a
fases diferentes. T12 pode entregar preparação automática e retomada antes de
T14, mas **publicação factual automática em uso concorrente só é ativada após
T14**, D01 resolvida e gates de recuperação. T15 não é requisito do piloto seguro:
rebuild isolado continua válido, com custo e modo declarados.

## Regras de execução futura

- Trabalhar a fronteira: ticket só inicia quando seus blockers estiverem concluídos.
- Resolver decisões aplicáveis antes do comportamento que depende delas.
- Propostas de seam são revisadas antes de escrever testes novos.
- Cada ticket atravessa interface, contrato, comportamento e teste necessários.
- Não criar uma fase horizontal de todos os schemas ou de todos os testes.
- Não reescrever o motor inteiro para iniciar o primeiro ticket.
- Preservar o import da raiz e contratos de pacotes antigos.
- Uma entrega com backend fixture não comprova integração MCP real.
- Registro documental não autoriza instalar agenda, iniciar reindex, publicar
  artefatos externos ou capturar conversas.

## Primeiro trabalho concreto

[T01](tickets/01-protect-enrichment.md): gerar pacote, enriquecer a skill,
alterar fonte e comprovar que a atualização recusa sobrescrita silenciosa.
O menor GREEN é inventário de hashes e guarda de propriedade antes da substituição.
O roteiro completo está em [TDD](TDD.md).
