# Uso operacional

Este é o guia curto do piloto/produto. O contrato completo está em
[ARCHITECTURE.md](ARCHITECTURE.md), e o passo a passo por harness em
[HARNESSES.md](HARNESSES.md).

## Instalação

```text
python scripts/bootstrap.py --dev
python -m docops doctor --json
python -m pytest
```

Para o MCP local:

```text
python scripts/bootstrap.py --dev --rag
python scripts/mcp_smoke.py "background tasks"
```

No Windows use `scripts/bootstrap.ps1`; em Linux/macOS use
`sh scripts/bootstrap.sh`. `doctor` trata o RAG como capacidade opcional;
`DOCOPS_REQUIRE_RAG=1 python -m docops doctor --json` torna-o obrigatório.

## Protocolo único de fonte

```text
python -m docops resolve <nome|URL|repo|pasta> --json
python -m docops run <nome|URL|repo|pasta> --output <pacote> --license <id>
python -m docops validate <pacote> --json
```

`resolve` não baixa nem executa nada. Nomes usam o catálogo oficial e param
quando a confiança é ambígua; uma URL de repositório pode receber `--version`
e `--scope`. Para catálogo próprio, passe `--catalog catalog.json` a `resolve`
ou `run`.

O `run` gera skill, router, corpus normalizado, `config.yaml`,
`harness.json` e manifesto. A configuração padrão é relativa ao pacote e não
sobrescreve uma configuração existente. Para indexar de fato no servidor local,
acrescente `--index-rag`; sem essa opção o `rag/index.json` fica em modo
`corpus-ready`, pronto para o processo MCP.

## Atualização legada

`scripts/update_rag.py` continua disponível para o corpus de trabalho legado:

```text
python scripts/update_rag.py plan
python scripts/update_rag.py apply
python scripts/update_rag.py status
```

O modo padrão aplica mudanças por arquivo, salva checkpoint após cada operação
e desabilita o watcher durante mutações explícitas. O estado `.rag_state.json`
é local e ignorado.

`scripts/update_docs.ps1 -Sources <fonte> -Slug <slug>` agora delega ao
`docops run`; não há instrução de copiar/colar no caminho feliz. O
`book-to-skill` instalado no harness pode enriquecer o scaffold estrutural e
validá-lo, mas o operador não cria uma sessão de IA nem envia chaves a um
provedor.

## Configuração e segurança

O `config.yaml` usa caminhos relativos e transporte `stdio`. Não exponha o
servidor na rede sem copiar `config/network.example.yaml` para um arquivo
privado, definir um bearer token forte e executar:

```text
python -m docops config-audit config/network.yaml --json
```

O auditor exige autenticação, rate limit, métricas e logging JSON para `sse` e
`streamable-http`. Não coloque esse arquivo no Git.

## Avaliação

```text
python -m docops golden-candidates <pacote> --json
python -m docops evaluate --package <pacote> --cases <golden-revisado.json> --json
python scripts/evaluate_golden.py --cases golden-set/test-cases.json
```

O avaliador lexical local exige `reviewed: true`; a avaliação real do backend
MCP continua sendo feita por `evaluate_retrieval`. Toda resposta factual do
harness deve citar `path#secao` ou `path:linha`.
