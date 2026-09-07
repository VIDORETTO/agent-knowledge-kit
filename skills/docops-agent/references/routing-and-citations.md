# Roteamento, evidência e citações

## Decisão rápida

| Pergunta | Camada primária | Ação obrigatória |
|---|---|---|
| “Como”, “por que”, padrão, trade-off, arquitetura | `skill/<slug>` | Explicar o modelo e suas condições |
| Assinatura, default, versão, endpoint, valor exato, changelog | MCP/RAG | Buscar antes de afirmar e citar |
| “Como fazer X e qual é o default?” | Skill + RAG | Raciocinar na skill, confirmar o literal no RAG |
| Escopo ambíguo, conflito, segurança ou alto risco | Skill + RAG | Declarar divergência, limitar escopo e considerar abstention |

Não use a skill conceitual como substituta de uma confirmação literal. Não use
um trecho RAG isolado como explicação geral quando ele não contém contexto.

## Busca factual

1. Verificar no `harness.json` qual MCP e geração estão configurados.
2. Usar `search_knowledge` com termos suficientes e limitar `max_results`.
3. Quando a resposta depender de um trecho específico, usar
   `get_document` para confirmar contexto e localizador.
4. Citar cada afirmação factual relevante como `path#secao` ou `path:linha`.
5. Se a busca não cobrir a pergunta, dizer que a evidência não foi encontrada;
   não preencher a lacuna com memória ou inferência não marcada.

Não use um `min_score` ou limiar copiado de outro corpus como verdade universal.
Calibre relevância com o Golden do pacote e considere intenção, escopo,
versão, autoridade e contexto do trecho. Um score alto em documento errado não
é evidência; um score baixo em uma fonte única pode exigir `get_document` ou
abstention.

## Conflitos

Priorize a fonte dentro do escopo aplicável, versão correta, autoridade
declarada, evidência direta e atualidade. Livro, curso, artigo ou transcrição
podem explicar racional, mas não substituem automaticamente o contrato oficial
ou a decisão interna aprovada. Quando duas fontes válidas divergem, informe as
duas, suas versões/escopos e a necessidade de decisão.

## Forma da resposta

- Separe claramente conhecimento conceitual, fatos citados e inferências.
- Preserve nomes de API, identificadores e valores exatamente como na fonte.
- Não exponha conteúdo protegido além do necessário para a resposta.
- Se a geração mudar durante uma consulta pinada, descarte o resultado e
  reabra o leitor na nova geração.
- Se não houver suporte suficiente, responda com abstention explícita: diga o
  que foi buscado, o que não foi encontrado e qual verificação humana/fonte
  adicional é necessária.
