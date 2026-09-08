# Tutorial: do zero à consulta persistente

Este tutorial usa caminhos de exemplo. Substitua `<fonte>` e `<pacote>` por
valores autorizados no projeto.

## 1. Preparar o agente

Na raiz do projeto consumidor:

```text
python skills/docops-agent/scripts/install_agents_bootstrap.py --root .
```

Leia o `AGENTS.md` inteiro e depois `skills/docops-agent/SKILL.md`. O primeiro
comando é idempotente e não apaga regras locais.

Em uma instalação via wheel, descubra a cópia empacotada sem depender do
checkout:

```text
python -m docops skill path --json
python -m docops agents-bootstrap --root . --json
```

## 2. Gerar e validar um pacote

```text
python -m docops doctor --json
python -m docops resolve <fonte> --json
python -m docops run <fonte> --output artifacts/<slug> --license <id> --json
python -m docops validate artifacts/<slug> --json
```

Confira `manifest.json`, `harness.json`, `skill/SKILL.md`,
`router/SKILL.md`, `rag/sources.json` e `rag/index.json`. Sem `--index-rag`, o
resultado está em `corpus-ready`; use-o quando o MCP local deve ser realmente
vetorizado.

## 3. Responder uma pergunta

Carregue a skill e o router no harness. Para uma pergunta conceitual, use a
skill. Para um default/assinatura/versão, consulte `search_knowledge` e cite o
resultado. Para uma pergunta híbrida, faça os dois e declare divergências.

## 4. Atualizar uma fonte

```text
python -m docops lifecycle source register \
  --package artifacts/<slug> --source-id docs-main \
  --canonical <fonte> --owner operator
python -m docops lifecycle source reconcile \
  --package artifacts/<slug> --source <fonte> \
  --source-root <diretorio> --index-rag
python -m docops lifecycle worker run \
  --package artifacts/<slug> --loop --interval-seconds 60
```

O RAG pode receber fatos novos após o job. A skill ativa permanece igual até
que o gatilho conceitual peça enriquecimento, a saída externa seja avaliada e
um revisor publique a candidata.

## 5. Enriquecer e publicar a skill

Prepare uma candidata, importe somente a saída Markdown permitida do
`book-to-skill`, registre a avaliação para a mesma composição, aprove e publique.
Se qualquer arquivo, fonte, router ou política mudar depois da avaliação,
reavalie; não force o publish.

## 6. Fechar a operação

Registre estado, readiness, métricas, citações e pendências. Não versiona o
corpus adquirido, credenciais, índices locais ou runtime privado. Se uma fonte
perder autorização, revogue-a e confirme que readers não retornam seus trechos.

Para execução recorrente, configure o `reconcile` e o `work` conforme
[scheduler-runbooks.md](scheduler-runbooks.md); `work --once` sozinho não
descobre arquivos novos.
