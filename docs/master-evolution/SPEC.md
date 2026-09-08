# Especificação de evolução: projetos de conhecimento operados por agentes

Status: contrato implementado localmente nesta execução, em português. Este documento não autoriza publicação, alteração do corpus/índice real ou uso de credenciais ausentes. O harness externo conduz a conversa e executa modelos; o núcleo permanece determinístico e independente de provedor. Os contratos detalhados estão em [STATE-CONTRACTS.md](STATE-CONTRACTS.md), e as evidências estão em [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md).

## Problem Statement

O agente já dispõe de operações de aquisição, pacote, fontes, candidatas, avaliação, promoção, leitura e coordenação. Entretanto, ainda precisa traduzir manualmente a intenção do usuário em decisões de projeto e conectar essas operações para manter conhecimento, curso e página de maneira consistente. Falta um contrato de projeto que sobreviva à conversa, identifique decisões ausentes e explique os impactos de cada mudança sobre entregáveis diferentes.

Um curso sobre vender no Mercado Livre é diferente de um curso comercializado dentro desse marketplace. Inferir essa intenção, assim como preço, garantia, autorização de uso ou promessa de resultado, pode produzir material comercial inadequado. Misturar esses dados com instruções estáveis do agente dificulta atualização e auditoria. Tratar fontes oficiais, relatos e hipóteses como equivalentes produz respostas aparentemente precisas, mas sem sustentação apropriada.

A continuidade operacional também depende de integração externa: observar arquivos não equivale a executar aquisição, avaliação e publicação; obter um resultado de modelo externo não equivale a aceitá-lo. A evolução deve tornar essas fronteiras observáveis e retomáveis. Os controles existentes de avaliação, autoridade, revogação e publicação são proteção deliberada, não defeitos a eliminar para aumentar autonomia.

## Solution

Adicionar uma camada pequena de projeto sobre o ciclo editorial existente. Um protocolo de inicialização recebe respostas estruturadas do harness, persiste decisões, devolve somente perguntas relevantes ainda não respondidas e produz um rascunho privado verificável. O projeto referencia o pacote operacional e suas gerações; não cria outro índice ou uma segunda máquina de publicação.

O agente apresenta alterações como propostas com base exata, diff, evidências, impactos em RAG, skills, curso e página, verificações exigidas e decisões pendentes. A evolução factual reutiliza reconciliação e indexação; a evolução conceitual reutiliza candidatas e a tarefa externa de enriquecimento. Toda ativação depende de validação e dos gates apropriados. Em caso de interrupção, preservar a última composição válida; se não houver leitura segura durante recuperação, retornar RECOVERY_REQUIRED até reconciliar os recibos, sem servir composição híbrida.

O primeiro preset organiza o domínio de vendedores do Mercado Livre, mas taxonomia, consultas iniciais e restrições do domínio ficam fora do núcleo genérico. Curso e página são artefatos editoriais próprios: fatos dependem de evidência, decisões comerciais dependem do responsável pelo projeto, e instruções operacionais permanecem estáveis.

## User Stories

1. Como operador de um harness, quero iniciar um projeto por respostas estruturadas, para transformar uma intenção em estado utilizável pelo agente.
2. Como usuário, quero que o agente pergunte somente decisões importantes ausentes, para evitar entrevistas repetitivas.
3. Como usuário, quero interromper e retomar a inicialização, para não perder respostas ou decisões confirmadas.
4. Como usuário, quero corrigir uma resposta mantendo seu histórico, para entender por que o projeto mudou.
5. Como usuário, quero confirmar o significado de “curso para vender no Mercado Livre”, para evitar construir o produto errado.
6. Como responsável pelo produto, quero que preço, garantia e promessa permaneçam pendentes quando desconhecidos, para impedir invenções comerciais.
7. Como agente, quero distinguir suposição reversível de decisão confirmada, para saber o que posso preparar e o que precisa de resolução.
8. Como mantenedor, quero instruções estáveis separadas do brief e dos fatos, para atualizar o projeto sem reescrever as regras do agente.
9. Como autor, quero um mapa versionado de módulos e aulas, para evoluir a sequência pedagógica independentemente do corpus.
10. Como autor, quero associar exercícios, exemplos e pré-requisitos às aulas, para produzir aprendizagem verificável.
11. Como responsável pela página, quero uma especificação de público, objetivo, tom e seções, para orientar uma apresentação coerente.
12. Como responsável pela página, quero vincular provas e benefícios a evidências, para detectar promessas sem suporte.
13. Como operador, quero cadastrar várias fontes com identidade estável, para preservar proveniência mesmo quando seus conteúdos se repetem.
14. Como operador, quero registrar licença, permissão e restrição por finalidade, para distinguir consulta interna de redistribuição comercial.
15. Como operador, quero registrar região, vigência e data de captura, para evitar aplicar regras fora de contexto.
16. Como agente, quero distinguir regra oficial, fato, opinião, experiência, hipótese e recomendação, para comunicar corretamente a natureza da evidência.
17. Como operador, quero ingerir transcrições autorizadas com timestamps, para citar trechos e rastrear resumos derivados.
18. Como operador, quero que aquisições incompletas não revoguem fontes, para que falhas transitórias não apaguem conhecimento válido.
19. Como usuário, quero consultar o índice de todas as fontes ativas relevantes, para obter evidências complementares sem carregar todo o corpus na conversa.
20. Como vendedor, quero prioridade de fontes oficiais em perguntas normativas, para distinguir regras de estratégias pessoais.
21. Como vendedor, quero visualizar conflitos e limitações temporais, para decidir sem falsa certeza.
22. Como vendedor, quero citações próximas às afirmações e localizadores verificáveis, para inspecionar a evidência original.
23. Como vendedor, quero que ausência de evidência seja declarada, para não receber respostas factuais inventadas.
24. Como operador, quero filtrar por tema, tipo, autoridade e data, para obter recuperação adequada ao contexto.
25. Como operador, quero propor inclusão, alteração e revogação de fontes, para manter o corpus sem destruir histórico.
26. Como agente, quero identificar derivados impactados por uma fonte revogada, para impedir respostas e conteúdo editorial que dependam dela.
27. Como autor, quero alterar uma aula ou seção de página sem reconstruir conhecimento não afetado, para reduzir custo e risco.
28. Como revisor, quero inspecionar uma candidata com base, hashes, diff e avaliação exatos, para aprovar somente aquilo que examinei.
29. Como operador, quero continuar consultando a última versão válida durante falhas, para evitar indisponibilidade causada por atualização incompleta.
30. Como operador, quero restaurar uma composição retida compatível e não revogada, para recuperar uma publicação problemática com segurança.
31. Como mantenedor, quero que mudanças no perfil de embedding exijam reconstrução e avaliação, para evitar um índice incompatível.
32. Como avaliador, quero perguntas reais em PT-BR, conflitos, frescor, remoções e casos sem resposta, para medir utilidade no domínio alvo.
33. Como revisor, quero que candidatos Golden gerados automaticamente continuem não revisados, para não validar o sistema com respostas que ele próprio inventou.
34. Como operador, quero observar jobs, retries, leases, falhas e checkpoints, para distinguir trabalho pendente de serviço saudável.
35. Como operador, quero um scheduler externo documentado com execução limitada, para automatizar a continuidade sem pressupor um daemon inexistente.
36. Como operador do harness, quero contratos de tarefa, resultado e recibo para enriquecimento conceitual, para retomar trabalhos externos sem repetir efeitos.
37. Como responsável pelo projeto, quero publicação manual como padrão, para manter controle sobre mudanças conceituais e comerciais.
38. Como responsável pelo projeto, quero poder considerar uma delegação factual limitada posteriormente, para reduzir intervenções sem perder avaliação e autoridade autenticada.
39. Como mantenedor, quero comandos e documentação coerentes, para que outro agente execute somente interfaces suportadas.
40. Como operador, quero backup e restauração testáveis de estado, corpus e evidências, para recuperar o projeto com os mesmos vínculos de confiança.
41. Como mantenedor, quero critérios objetivos de plataforma e dependências antes de liberar o produto, para não confundir tolerância local com suporte declarado.
42. Como criador de outro domínio, quero instalar um preset diferente sem copiar o núcleo, para reutilizar a arquitetura.
43. Como agente implementador, quero contratos, dependências, casos negativos e critérios por tarefa, para entregar pequenas mudanças verificáveis.
44. Como responsável por privacidade, quero conversas minimizadas e evidências sensíveis protegidas, para evitar persistir dados desnecessários ou redistribuí-los.

## Implementation Decisions

- **Status das decisões:** as escolhas abaixo são recomendações técnicas para execução das fases, não consentimento comercial do usuário. Decisões de público, promessa, formato final, oferta e política de publicação pública permanecem pendentes até confirmação registrada.
- **Camada de projeto:** adicionar um serviço de aplicação de projeto exposto pela API raiz e pela CLI. Ele compõe as operações existentes; não executa LLM, não seleciona provedor e não introduz chatbot, servidor web ou agente residente obrigatório.
- **Inicialização:** oferecer operações determinísticas de início, leitura/retomada, aplicação de respostas, validação e finalização de rascunho. O harness formula perguntas naturais a partir do contrato. Cada resposta referencia uma chave estável e sua proveniência. Idempotência e revisão esperada impedem repetição e perda de atualização.
- **Rascunhos e revisões:** sessão é mutável com controle de concorrência; revisão de projeto é imutável, vinculada à revisão anterior e aos artefatos por hash. Finalizar inicialização gera rascunho privado e jamais significa publicação editorial.
- **Pacote como autoridade:** pacote e lifecycle existentes continuam sendo a autoridade sobre fonte, candidata, avaliação, aprovação, publicação, leitor e geração. Projeto referencia esses identificadores e recibos; não copia suas máquinas de estado.
- **Artefatos:** separar brief, decisões, política do projeto, especificação do curso, especificação da página, governança de fontes e mapa de dependências. Documentos legíveis são projeções do estado versionado; edições externas entram como propostas de mudança, sem edição silenciosa do ativo.
- **Schemas:** criar contratos versionados aditivos e validados também no wheel. Campos desconhecidos de extensão não podem alterar gates. Ausência e valor desconhecido possuem semânticas explícitas. Migração de projetos legados é preparatória e preserva os identificadores editoriais.
- **Fontes:** estender o registro existente por metadados vinculados à fonte e à revisão observada, mantendo semântica de reconciliação e retirada explícita. Classificação de alegação é granular: uma fonte oficial pode incluir recomendações, e um relato pode citar uma regra.
- **Direitos e privacidade:** admissão, consulta interna, citação limitada, criação de derivados e redistribuição são permissões distintas. Metadado “oficial” não concede direito autoral. Conteúdo de licença incerta pode ter seu endereço registrado sem aquisição/publicação automática.
- **Mudanças:** usar proposta de alteração com base imutável, operações tipadas, relatório de impacto e gates. Atualização factual não dispensa revogação, avaliação ou validação de derivados. Classificação incerta segue revisão conservadora.
- **Enriquecimento:** compor os contratos existentes de solicitação e submissão de candidata com um registro observável de trabalho externo. O resultado do harness é entrada não confiável até validação; sua conclusão não autoriza ativação.
- **Publicação:** manter aprovação manual por padrão. Delegação factual é opção posterior explicitamente habilitada, com fonte, escopo, validade e autoridade autenticada; não se aplica a alterações conceituais, direitos, privacidade, conflitos não resolvidos ou oferta comercial.
- **Consistência:** ativação de composição de projeto ocorre apenas depois de publicação editorial bem-sucedida quando houver mudança de pacote. Leitores usam referências exatas de revisão e geração. Recuperação completa ou desfaz a transação pendente antes de nova mutação; incompatibilidade bloqueia leitura, sem combinar arbitrariamente gerações.
- **Retirada:** revogar acesso presente sem apagar evidências históricas. A retenção histórica respeita política de privacidade; conservar recibos e hashes não implica conservar indefinidamente todo conteúdo privado.
- **RAG:** reutilizar busca híbrida e snapshots; metadados de contexto e citações acompanham ingestão, filtros e resposta. PT-BR exige comparação do perfil apropriado, rebuild quando necessário e Golden nativo revisado.
- **Operação:** preservar execução local single-writer; documentar scheduler externo sobre worker de passagem única e aproveitar fila, leases e recibos existentes. Escala distribuída só depois de necessidade medida e contrato específico.
- **Manutenção:** aprofundar módulos nas fronteiras comprovadamente complexas durante implementação de comportamento, sem reescrita geral ou criação de wrappers sem responsabilidade própria.

## Testing Decisions

- Testar comportamento observável pela API raiz suportada, CLI em subprocesso, artefatos JSON e MCP real para integração de índice. Evitar testar detalhes de armazenamento ou importar módulos internos em novos testes de aceitação.
- Executar TDD em fatias verticais: escrever um caso de comportamento ausente, observar falha relevante, implementar o mínimo, validar e só então refatorar. Não criar previamente uma grande suíte baseada em arquitetura ainda não validada.
- Usar como precedentes os testes atuais de interface pública, registry de fontes, recuperação de promoção, candidatas, sessões de leitura e snapshots. A política existente de seams públicas se aplica às novas operações de projeto.
- Inicialização deve comprovar retomada após encerramento de processo, ausência de repetição de perguntas respondidas, correção com histórico, rejeição de resposta concorrente e permanência privada diante de decisão comercial ausente.
- Mudanças devem comprovar diff sem efeito, impacto transitivo, distinção de mudança factual e conceitual, ausência de promoção em execução incompleta e rejeição de aprovação obsoleta.
- A composição de projeto deve ser testada com falhas antes e depois da promoção existente, incluindo recuperação e impedimento de combinação inconsistente de curso, página e geração de pacote.
- Governança deve comprovar direitos desconhecidos, fonte revogada, aquisição parcial, conflito regional/temporal, transcrição sem permissão e histórico sem reativação indevida.
- RAG deve ter testes determinísticos de filtragem/locadores e avaliação real separada de qualidade semântica. Teste com adapter de memória não comprova qualidade de recuperação, compatibilidade do modelo ou segurança do MCP real.
- Golden revisado precisa incluir perguntas normativas, estratégicas, ambíguas, conflitantes, atuais e sem suporte. Medir recuperação, suporte das afirmações, qualidade das citações, abstenção e impacto de revogações; não substituir julgamento revisado por sucesso de schema.
- Validação contratual deve executar no checkout e no wheel, incluindo schemas inválidos, versões futuras não suportadas, migração idempotente e drift da documentação com a ajuda da CLI.
- Os testes e comandos concretos foram registrados nos tickets e em [IMPLEMENTATION-EVIDENCE.md](IMPLEMENTATION-EVIDENCE.md). A estratégia de seams acima continua orientando a revisão; o perfil MCP real, publicação e corpus real permanecem limites externos não comprovados nesta execução.

## Out of Scope do produto local

- Publicar issues em serviços externos, indexar corpus real ou executar integrações que exigem credenciais ausentes.
- Gerar um curso comercial completo, fixar preço/garantia, criar página publicada ou afirmar conformidade com regras atuais de uma plataforma.
- Desenvolver chatbot genérico, escolher um provedor de LLM ou incorporar execução de modelo ao núcleo.
- Automatizar coleta de transcrições com direitos incertos ou redistribuir corpus protegido.
- Construir fila distribuída, cluster multi-writer, painel SaaS ou hospedagem pública na primeira entrega.
- Remover aprovação, avaliação, autorização de indexação, isolamento de leitura ou verificação de revogação para simplificar autonomia.
- Tratar o piloto FastAPI como evidência de qualidade no domínio Mercado Livre.

## Further Notes

O conjunto de tickets e fases foi o plano de execução desta especificação. O contrato detalhado complementar resolve nomes, campos, invariantes e integração com interfaces existentes. Se uma integração externa contradisser uma regra de segurança deste conjunto ou o lifecycle vigente, ela deve permanecer bloqueada e a versão ativa intacta.

A publicação em issue tracker indicada pela skill `to-spec` não integra esta entrega: o pedido é produzir documentos locais para outro agente, sem autorização para mensagens externas. A checagem de seams foi registrada como decisão a revisar no handoff. Nenhum dado comercial ausente deve ser preenchido pelo implementador como se fosse aprovado.
