# OpenCode, Claude Code, Codex e harnesses compatíveis

O operador entrega Agent Skills e MCP; cada harness mantém sua própria
configuração. O arquivo gerado `harness.json` é deliberadamente relativo e
serve como fonte de preenchimento, não como uma configuração pessoal pronta
para sobrescrever arquivos do usuário.

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
sem converter o caminho relativo em um caminho do autor. O schema final é
específico do harness e deve ser conferido na documentação da versão instalada.

## OpenCode

Adicione a entrada MCP equivalente à seção de servidores MCP do projeto e
aponte as skills para o diretório de skills do projeto/harness. O comando deve
ser resolvido pelo ambiente no clone (`.venv` ou `DOCOPS_RAG_PYTHON`), nunca por
um caminho absoluto copiado do computador de outra pessoa.

## Claude Code

Instale `skill/` e `router/` em um diretório de skills aceito pelo projeto ou
usuário e registre `knowledge-rag` no arquivo MCP que o Claude Code usa na sua
versão. Faça a fusão preservando outros servidores; o repositório não edita
esse arquivo.

## Codex

Carregue `skill/SKILL.md` e `router/SKILL.md` como skills do projeto e registre
o mesmo processo stdio na configuração MCP do Codex. O harness continua
responsável por credenciais do provedor e pela seleção do modelo.

## Qualquer outro harness

Se ele suporta Agent Skills e MCP stdio, basta carregar os dois diretórios,
executar o processo no `cwd` do pacote e enviar as chamadas MCP pelo stdin/stdout
JSON-RPC. O router exige `search_knowledge` para fatos literais e citações
`path#secao` ou `path:linha`.

Para transporte HTTP/SSE, use uma cópia privada de
`config/network.example.yaml`, substitua o token, rode o auditor e aplique
firewall/rede local. O perfil público padrão permanece stdio.
