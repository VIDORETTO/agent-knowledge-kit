# Decisões pendentes e registro de revisão

[Índice](README.md) · [Especificação](SPEC.md)

Status de todos os itens: **pendente**. Responsáveis ainda não designados.
Autorizar documentação não equivale a aprovar implementação ou publicação.

| ID | Decisão | Recomendação | Alternativa/tradeoff | Resolver antes de |
|---|---|---|---|---|
| D01 | Publicação factual automática | Somente fontes cadastradas e política persistida, após gates | Aprovação manual de toda mudança aumenta fila editorial | Ativar T12–T14 |
| D02 | Thresholds, agenda e orçamento | Defaults da SPEC; calibrar em piloto | Perfis por corpus após baseline | T07/T11/T13 |
| D03 | Aprovação conceitual | Humana no piloto, proponente não se autoaprova | Autopublicação futura apenas de classes determinísticas comprovadas | T08 |
| D04 | Nomes e tipos dos seams novos | Estender motor raiz; novos fluxos pela CLI | Mais funções públicas aumentam superfície estável | Primeiro ticket que introduzir novo seam |
| D05 | Execução do enriquecimento | Tarefa/recibo para harness externo já escolhido pelo usuário | Integração específica precisa suporte comprovado | T06 |
| D06 | Retenção e quotas | 5 últimas + 30 dias + gerações fixadas; revogação prevalece | Menor retenção reduz disco e capacidade de rollback | T09 |
| D07 | Adoção de pacotes legados | Baseline explícito quando propriedade não é comprovável | Adotar automaticamente pode aceitar conteúdo adulterado | T01/T02 |
| D08 | Backend de consulta e snapshots | Capacidade negociada; modo restrito e snapshot testado | Sem extensão, rebuild e promoção coordenada manual | T14/T15 |
| D09 | Perfil para português | Comparar compact/multilingual com Golden nativo | Perfil maior aumenta RAM e tempo; nunca trocar sem rebuild | T16 |
| D10 | Captura de conversas | Opt-in, trechos mínimos, escopo privado e revisão | Captura abrangente eleva risco e custo | T17 |
| D11 | Autoridade e direitos de fontes | Cadastro por fonte/escopo com responsável | Herança global simplifica mas pode misturar permissões | T10 |
| D12 | Modelo de autenticação do aprovador | Confiança local explicitada; processo autorizado | Assinaturas/identidade remota exigem projeto adicional | T08 ou mudança de threat model |
| D13 | Publicação externa de derivados | Sempre revisão de direitos e privacidade | Private-only não autoriza redistribuição | Qualquer exportação pública |
| D14 | Retirada da última fonte | retired/not-queryable explícito | Manter pacote antigo consultável pode contrariar revogação | Remoções automáticas em produção |

## Como registrar uma decisão

Adicionar, no item correspondente: status, data, responsável, opção escolhida,
justificativa, escopo autorizado, evidências, prazo/condição de reavaliação e
tickets afetados. Atualizar SPEC/CONTRACTS/VALIDATION juntos quando necessário.
Não preencher aprovação em nome do usuário por inferência.

## Riscos com resposta operacional

| Risco | Sinal | Resposta proposta |
|---|---|---|
| Perda de enriquecimento | Inventário divergente | Bloquear substituição, T01 |
| Exclusão indevida | Snapshot incompleto | Preservar conjunto anterior, T10 |
| Contaminação | Alegação sem suporte | Quarentena/rejeição, T17 |
| Snapshot inconsistente | Busca/contagens divergentes | Recusar candidata, fallback rebuild, T15 |
| Custo excessivo | Quota/orçamento ultrapassado | Backlog visível, sem bypass de gate |
| Defasagem perigosa | Fonte revogada ou conflito crítico | Invalidar conceitos/sessões afetados |
| Evidência envelhecida | Hash/config diferente | Invalidar gate e aprovação, T02/T08 |
| Dados privados em derivados | Fonte revogada ou auditoria | Bloquear acesso, expurgar e impedir rollback |
| Host/harness sem suporte | Capacidade não comprovada | awaiting_enrichment ou operação manual |

## Limites de confiança

Hash é integridade, não assinatura de autoria. Licença do código não é licença
do corpus. Fonte oficial também pode estar errada para outra versão. Vários
modelos concordando não constituem múltiplas fontes primárias. Golden com boa
média não elimina falha crítica. Revogar arquivo não apaga contexto já lido por
uma sessão: é necessário interromper/recarregar o uso desse contexto.
