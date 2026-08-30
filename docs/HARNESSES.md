# Harnesses e contrato de integração

O operador entrega Agent Skills e MCP; cada harness mantém sua própria
configuração. O arquivo gerado `harness.json` é deliberadamente relativo e
serve como hand-off, não como uma configuração pessoal pronta para sobrescrever
arquivos do usuário.

## Matriz verificada na release 1.0.0

| Harness | Host e versão | Resultado | Escopo comprovado |
|---|---|---|---|
| OpenCode | Windows, 1.18.25 | aprovado | Sessão real somente leitura: versão, comando MCP, transporte padrão e consistência do contrato |
| Codex CLI | Windows, 0.151.0 | aprovado | Sessão real somente leitura: inspeção do contrato e validação Draft 2020-12 do manifesto em memória |
| Claude Code | não instalado neste host | não anunciado | Não faz parte da matriz de suporte desta release |

Os testes foram executados sem editar, fazer commit, publicar ou executar
comandos destrutivos. Eles comprovam a integração do contrato e do MCP stdio;
não prometem comportamento específico de um modelo nem substituem testes do
projeto que receberá o pacote.

## Passos comuns

1. Prepare o clone com `python scripts/bootstrap.py --dev --rag`.
2. Gere um pacote com `python -m docops run <fonte> --output <pacote> --license <id>`.
3. Instale/mapeie `<pacote>/skill` e `<pacote>/router` no diretório de skills
   que o harness já utiliza.
4. Registre o servidor stdio usando o interpretador do ambiente preparado:

```json
{
  "name": "knowledge-rag",
  "command": "python",
  "args": ["-m", "mcp_server.server"],
  "cwd": ".",
  "env": {
    "KNOWLEDGE_RAG_DIR": ".",
    "KNOWLEDGE_RAG_WATCHER_DISABLED": "1"
  }
}
```

O `cwd` acima é o diretório do pacote. Em uma configuração que aceita
`mcpServers`, coloque o objeto sob `mcpServers.knowledge-rag`; em uma que usa
`servers`, `context_servers` ou TOML, preserve exatamente os mesmos campos
sem converter o caminho relativo em um caminho do autor. O contrato canônico é
validado por `schemas/harness.schema.json`.

## OpenCode

Na versão 1.18.25, adicione a entrada MCP equivalente à seção de servidores
MCP do projeto e aponte as skills para o diretório de skills do
projeto/harness. O comando deve ser resolvido pelo ambiente no clone (`.venv`
ou `DOCOPS_RAG_PYTHON`), nunca por um caminho absoluto copiado do computador de
outra pessoa.

Comprovação desta release: `opencode run --format json --model openai/gpt-5.4`
inspecionou `README.md`, `docops/harness.py`, o schema e o metadado do pacote;
reportou versão 1.0.0, `python -m mcp_server.server`, transporte `stdio` e
contrato consistente.

## Codex CLI

Na versão 0.151.0, carregue `skill/SKILL.md` e `router/SKILL.md` como skills do
projeto e registre o mesmo processo stdio na configuração MCP do Codex. O
harness continua responsável por credenciais do provedor e pela seleção do
modelo.

Comprovação desta release: `codex exec --json --ephemeral --sandbox read-only`
inspecionou os mesmos arquivos e validou o manifesto gerado em memória com
Draft 2020-12, sem erros de schema. O runner global não conseguiu iniciar
pytest por falta de diretório temporário utilizável; a suíte do projeto foi
executada no `.venv` dedicado e essa limitação não afetou a validação do
contrato.

## Qualquer outro harness

O suporte genérico é protocolar, não uma promessa de compatibilidade testada.
Se o harness suporta Agent Skills e MCP stdio, carregue os dois diretórios,
execute o processo no `cwd` do pacote e envie as chamadas MCP pelo stdin/stdout
JSON-RPC. O router exige `search_knowledge` para fatos literais e citações
`path#secao` ou `path:linha`.

Para transporte HTTP/SSE, use uma cópia privada de
`config/network.example.yaml`, substitua o token por um valor forte, rode
`config-audit` e aplique firewall/rede local. O servidor também recusa iniciar
quando o bearer token está ausente; o perfil público padrão permanece stdio.
