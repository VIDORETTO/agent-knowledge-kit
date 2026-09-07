# Bootstrap do `AGENTS.md`

Use this block once in the target project's `AGENTS.md`. Preserve the file's
existing rules and insert it near the other agent workflow instructions. The
marker makes the operation idempotent.

```markdown
## DOCOPS-PERSISTENT-KNOWLEDGE

Quando uma tarefa envolver documentação persistente, memória do projeto,
Agent Skills, RAG, fontes, citações ou aprendizado de conversas, leia primeiro
`skills/docops-agent/SKILL.md` (ou o caminho equivalente instalado no host).
Use essa skill para decidir entre conhecimento conceitual e busca factual,
preservar proveniência e seguir o ciclo seguro de atualização. Se outras skills
`rag-*` ou de domínio estiverem instaladas, siga a precedência em
`skills/docops-agent/references/skill-interoperability.md`. Depois leia as
regras específicas deste projeto e só então opere.
```

## Procedimento

1. Encontrar o `AGENTS.md` mais próximo da raiz do projeto que será alterado.
2. Ler o arquivo inteiro antes de editar; regras locais continuam tendo
   precedência.
3. Procurar o marcador literal `DOCOPS-PERSISTENT-KNOWLEDGE`.
4. Se ausente, inserir o bloco acima sem remover ou reordenar instruções
   existentes. Se o arquivo não existir, criar um `AGENTS.md` na raiz do
   projeto, mas somente quando a tarefa autorizou instalar o DOCOPS.
5. Confirmar que o caminho da skill é real no ambiente consumidor; se for um
   pacote gerado, usar o caminho indicado pelo harness.

Quando esta pasta foi copiada para o projeto consumidor, o procedimento pode
ser executado sem duplicação por:

```text
python skills/docops-agent/scripts/install_agents_bootstrap.py --root .
```

Use `--check` para auditar sem escrever.

Esse bloco orienta descoberta. Ele não concede permissão para indexar, publicar,
enviar dados a uma rede, alterar uma skill ativa ou compartilhar documentos.
