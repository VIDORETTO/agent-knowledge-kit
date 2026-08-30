# consulta-documentacao

`consulta-documentacao` 1.0.0 é um operador portátil para transformar uma referência
de documentação em um pacote de conhecimento para agentes. Ele resolve a
fonte, adquire e normaliza documentos, gera uma skill e um roteador, prepara o
corpus para `knowledge-rag` e registra tudo em um manifesto retomável.

O projeto não contém nem escolhe um LLM, provedor, modelo, chat ou chave de
API. OpenCode, Claude Code, Codex ou outro harness compatível executa a skill e
decide o modelo. O MCP é uma ferramenta local opcional para recuperação; o
operador continua utilizável sem o servidor RAG instalado.

## Começo rápido

Requer Python 3.11 ou mais recente e Git para fontes de repositório.

```text
python scripts/bootstrap.py --dev
python -m docops doctor --json
python -m pytest
```

Para habilitar o RAG local:

```text
python scripts/bootstrap.py --dev --rag
python scripts/mcp_smoke.py "retry policy"
```

No Windows, `scripts/bootstrap.ps1` é equivalente; no Linux/macOS, use
`sh scripts/bootstrap.sh`. Os scripts detectam `bin/python` e
`Scripts/python.exe`, e não dependem de um caminho da máquina do autor.

## Um fluxo completo

O mesmo protocolo aceita pasta, arquivo, URL de página, URL de repositório ou
nome presente no catálogo:

```text
python -m docops resolve ./documents/fixtures/acme-docs --json
python -m docops run ./documents/fixtures/acme-docs --output ./artifacts/acme --slug acme --license MIT
python -m docops validate ./artifacts/acme --json
python -m docops golden-candidates ./artifacts/acme --json
```

O `run` produz `manifest.json`, `config.yaml`, `harness.json`, `skill/`,
`router/` e `rag/`. Repetir o comando reconcilia estado por identidade canônica, versão e
hash; `--index-rag` também executa a sincronização real do MCP. O caminho feliz
não exige copiar e colar instruções entre ferramentas.

Para uma fonte web, use limites explícitos (`--max-pages`, `--max-depth`,
`--include`, `--exclude`). Loopback e redes privadas são bloqueados por padrão;
`--allow-private-network` existe somente para fixtures locais controladas.

## Integração com harnesses

O pacote gerado contém um hand-off relativo em `harness.json`. Copie ou monte
`skill/` e `router/` no diretório de skills do harness e registre o MCP stdio
com `command=python`, `args=["-m", "mcp_server.server"]`, `cwd="."` e
`KNOWLEDGE_RAG_DIR="."`. Guias por host estão em
[docs/HARNESSES.md](docs/HARNESSES.md); o operador não modifica configurações
pessoais automaticamente.

## Política de dados e publicação

Fontes adquiridas podem ter direitos autorais e ficam fora do versionamento.
Fixtures sintéticas e exemplos são os únicos documentos distribuíveis por
padrão. Consulte [docs/PUBLISHING-POLICY.md](docs/PUBLISHING-POLICY.md),
[SECURITY.md](SECURITY.md) e [docs/RELEASE.md](docs/RELEASE.md) antes de
publicar qualquer artefato.

O contrato detalhado e a ordem de implementação estão em
[docs/ROADMAP-GITHUB-PRODUTO.md](docs/ROADMAP-GITHUB-PRODUTO.md). A arquitetura
executável está descrita em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
