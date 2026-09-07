# Exemplos práticos

## 1. Pergunta conceitual

Usuário: “Qual padrão devo usar para tarefas em background?”

Ação: ler `skill/<slug>` e capítulos relacionados. Responder o modelo, trade-
offs e limites. Se mencionar um default, assinatura ou versão, confirmar esse
literal no RAG e citar a seção.

## 2. Pergunta factual

Usuário: “Qual é o valor padrão de `timeout`?”

Ação: chamar `search_knowledge`, confirmar o trecho com `get_document` se
necessário e responder, por exemplo: “O default é `X` ([guide.md#Client]
...).” Nunca responder apenas com uma lembrança do modelo.

## 3. Novo documento na fonte

Usuário: “Adicionei `docs/retry.md`; mantenha o conhecimento atualizado.”

Ação: executar `source reconcile` com a fonte correta, deixar o job ser
consumido por `work`, e confirmar se o resultado ficou `corpus-ready` ou
`indexed`.
Não dizer que a skill mudou: uma alteração conceitual gera candidata e exige
enriquecimento, avaliação e aprovação.

## 4. Enriquecimento externo

Usuário: “O book-to-skill gerou uma skill melhor.”

Ação: importar apenas Markdown permitido para a candidata, registrar ferramenta,
versão, hashes e proveniência, executar avaliação externa independente e pedir
aprovação conforme a política. A skill ativa permanece intacta até `publish`.

## 5. Conversa com uma correção

Usuário: “A resposta anterior estava errada; a regra correta é ...”

Ação: registrar uma `learning proposal` com evidência e privacidade. Não copiar
o chat inteiro nem promover a afirmação. Se houver conflito com fonte oficial,
abrir investigação e declarar a divergência.

## 6. Fonte revogada

Usuário: “Não podemos mais usar esse PDF.”

Ação: executar `source revoke` com ator e motivo, verificar o tombstone e a
filtragem do reader. Não apagar arquivos indiscriminadamente nem restaurar uma
release que dependa da fonte revogada.
