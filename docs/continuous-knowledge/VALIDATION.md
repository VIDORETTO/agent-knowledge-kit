# Validação, métricas e aceitação

[Índice](README.md) · [Especificação](SPEC.md) · [TDD](TDD.md)

Status: **plano de verificação proposto**. Nenhum threshold novo está comprovado.

## Matriz de aceitação

| ID | Comportamento observável | Tickets |
|---|---|---|
| A01 | Atualizar fonte não sobrescreve skill enriquecida silenciosamente | T01, T03 |
| A02 | Evento idêntico não cria segunda publicação | T11, T12 |
| A03 | Atualização factual mantém skill e registra nova revisão de corpus | T02, T03 |
| A04 | Reindexar corpus idêntico não solicita enriquecimento | T13 |
| A05 | Embedding alterado impede reuso incompatível | T05, T15 |
| A06 | Erro/parcial do backend impede publicação | T05, T08 |
| A07 | Falha preserva geração válida e retomada é possível | T04, T08, T09, T12 |
| A08 | Alterar candidata aprovada invalida aprovação | T08 |
| A09 | Base obsoleta impede publicação | T08 |
| A10 | Aquisição incompleta não remove documentos | T10 |
| A11 | Conversa não revisada não aparece na busca ativa | T17 |
| A12 | Revogação não é revertida por rollback | T09, T17 |
| A13 | Reinício retoma sem duplicar efeitos | T11, T12 |
| A14 | Sessão identifica geração e não mistura composição | T14 |
| A15 | Relatórios e exportações não vazam dados privados | T06, T17, T18 |
| A16 | Pacotes anteriores continuam legíveis e não são migrados implicitamente | T01–T05, T08 |

Além destes critérios, nenhum teste deve validar uma afirmação apenas porque o
mesmo gerador a produziu. Fontes esperadas e relevância vêm de revisão independente.

## Métricas e denominadores

| Métrica | Fórmula/definição | Observação |
|---|---|---|
| Hit@k legado | Casos cujo arquivo esperado está no top-k / casos | É o desenho atual de recall_at_k com uma fonte esperada |
| Recall@k múltiplo | Relevantes recuperados / relevantes conhecidos, macro por pergunta | Exige julgamentos múltiplos; novo campo/contrato |
| MRR@k | Média de 1/rank do primeiro relevante; zero quando ausente | Relatar k e unidade de relevância |
| Precision@k | Relevantes no top-k / k | Posições faltantes contam como não relevantes; declarar convenção |
| Fidelidade | Afirmações verificáveis sustentadas / afirmações verificáveis emitidas | Avaliação de resposta, não apenas retrieval |
| Correção | Casos com resposta compatível com referência / casos avaliados | Rubrica revisada por tipo de pergunta |
| Cobertura de citação | Afirmações que exigem fonte com citação válida / total que exige fonte | Fonte deve existir e sustentar alegação |
| Abstention | Consultas com abstention / consultas | Não minimizar isoladamente |
| Falsa abstention | Casos respondíveis abstidos / casos respondíveis | Mede perda de utilidade |
| Resposta indevida | Casos não respondíveis respondidos sem suporte / casos não respondíveis | Mede risco de alucinação |
| Latência | p50/p95 por busca, indexação, geração e publicação | Separar espera na fila e processamento |
| Atualidade | Publicação factual menos admissão | Separar prioridade e volume |
| Custo | CPU, RAM, disco, tokens externos e minutos humanos | Não atribuir preço sem configuração de provedor |

Denominador zero produz `not_applicable`, nunca 100% automático. Relatar contagens,
casos excluídos e erros. Em corpus com múltiplos trechos do mesmo arquivo, declarar
se relevância é por documento ou trecho e deduplicar conforme o contrato do caso.
Não mudar silenciosamente o significado de recall_at_k existente (E13).

## Baseline e conjunto de teste

Antes de calibrar gates, fixar: hardware/OS, corpus_revision, index_revision,
perfil e modelo, chunker, reranker, k, Golden, harness, configuração de geração e
política de abstention. Distinguir execução fria/quente e backend real/diagnóstico.

Criar pelo menos 100 casos revisados que cubram fatos, conceitos, mistos,
português, conflitos, ausência de resposta, versões e referências. Preservar
Golden FastAPI como conjunto independente. Separar conjunto de ajuste e conjunto
de avaliação; não ajustar thresholds olhando apenas para o conjunto de avaliação.

Casos gerados de headings ou conversas ficam reviewed=false até revisão. Casos
conceituais precisam de rubrica de resposta, não apenas caminho da skill.
Teste de route_query mede a regra lexical; testar router no harness é outra medição.

## Gates iniciais propostos

- Hit/Recall legado @5 ≥ 0,95; MRR@5 ≥ 0,80 no conjunto correspondente.
- Nenhuma regressão > 0,02 versus ativa no mesmo conjunto e configuração comparável.
- Recall múltiplo e Precision@k: baseline anotado antes de impor piso absoluto;
  bloquear regressão > 0,02 quando baseline existir.
- Fidelidade e cobertura de citações ≥ 0,98 no conjunto anotado.
- Zero afirmação crítica sem suporte; 100% nos casos de credenciais, isolamento e revogação.
- Roteamento real ≥ 0,95 em casos revisados, incluindo português e ambiguidade.
- Busca p95 não piora > 20% no mesmo hardware; medir também cache frio.
- Arquivos finalizados entram no lote em até 5 minutos; não incluir indexação nesse limite.
- Em fixture de 100 documentos com um alterado, T15 comprova reuso dos 99 demais
  e substituição factual correta, através do relatório público e busca real.

Estes gates são candidatos a aprovação (D02). Não transferir números históricos
FastAPI para português/livros sem nova avaliação. Amostras pequenas devem mostrar
contagens e incerteza; casos críticos falham individualmente mesmo com média alta.

## Cenários adversos obrigatórios

| Grupo | Cenários |
|---|---|
| Integridade | Skill editada, capítulo extra, inventário ausente, artefato removido, hash divergente |
| Fontes | Crawl parcial, 404 temporário, robots, mesma origem versões distintas, nova fonte sem remover antiga |
| Arquivos | Conteúdo alterado com mtime/tamanho iguais, caminho escapando, symlink, upload incompleto |
| Indexação | active=false com erro, already_running, resposta inválida, zero resultados, modelo incompatível |
| Publicação | Crash antes/depois de rename, base avançada, aprovação alterada, falha pós-promoção |
| Fila | Entrega duplicada, evento perdido recuperado por reconciliação, lease morto, retry limitado |
| Sessões | Reader durante promoção, cache antigo, geração revogada, permissão de escrita negada |
| Conversas | Alucinação do agente, opinião, consenso artificial, segredo, decisão fora de escopo |
| Injection | Instrução em português/inglês, aprovação forjada, caminho malicioso em saída do harness |
| Formatos | PDF sem texto, slide sem semântica visual, localizador ausente, transcrição com timestamps |
| Retenção | Quota excedida, geração fixada, rollback incompatível, última fonte removida |

## Estratégia de execução

1. Testes rápidos via raiz/CLI e fixtures sintéticas; relógio controlado para tempo.
2. Backend externo de teste pode simular erros de protocolo, sem mocks dos helpers DOCOPS.
3. Integração MCP real comprova busca, mutação restrita, índice e recuperação.
4. Harness externo executa avaliação de respostas; DOCOPS importa evidência.
5. Checks de schemas/cópias, interfaces públicas e wheel acompanham contratos alterados.
6. Executar plataformas declaradas afetadas por filesystem/lease, sobretudo Windows/POSIX.

Não escrever todos os testes antes da implementação. Aplicar um ciclo por cenário,
conforme [TDD](TDD.md). O orçamento da avaliação integra a política do lote, mas
falta de orçamento não autoriza publicar sem gate: candidata fica aguardando.
