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
Se o mesmo checkout for acessado por Windows e WSL, o bootstrap detecta um
`.venv` de outra plataforma e usa `.venv-windows` ou `.venv-posix`, evitando
que um ambiente nativo seja sobrescrito; esses diretórios são ignorados pelo
Git.

## Protocolo único de fonte

```text
python -m docops resolve <nome|URL|repo|pasta> --json
python -m docops plan <nome|URL|repo|pasta> --output <pacote> --license <id> --json
python -m docops run <nome|URL|repo|pasta> --output <pacote> --license <id>
python -m docops validate <pacote> --json
```

`resolve` não baixa nem executa nada. Nomes usam o catálogo oficial e param
quando a confiança é ambígua; uma URL de repositório pode receber `--version`
e `--scope`. Para catálogo próprio, passe `--catalog catalog.json` a `resolve`
ou `run`.

`plan` executa as fases somente leitura, calcula add/update/remove, valida
licença e mostra blockers/readiness esperados. `run` aplica esse plano em
staging; `--mode create` e `--mode update` impõem as invariantes de ciclo de
vida, e `--mode dry-run` é o alias sem efeitos. Uma falha deixa a geração ativa
intacta e pode deixar staging resumível; `inspect()` mostra tentativas e
resíduos sem conteúdo privado e espera um writer vivo terminar a promoção.
`cleanup()` remove apenas resíduos expirados segundo a política de retenção;
ela nunca remove a geração ativa nem staging resumível recente.

O `run` gera skill, router, corpus normalizado, `config.yaml`, `harness.json` e
manifesto. A configuração padrão é relativa ao pacote e não sobrescreve uma
configuração existente. Para indexar de fato no servidor local, acrescente
`--index-rag`; sem essa opção o `rag/index.json` fica em modo `corpus-ready`,
pronto para o processo MCP.

`rag/index.json` uses named metrics: `corpus_documents` counts documents
accepted by the operator; `operator_chunks` is the local estimate before the
backend; `backend_total_documents` and `backend_total_chunks` are totals
observed from knowledge-rag, or `null` when real indexing was not executed.
The current generator does not emit the ambiguous `documents`/`chunks` aliases.

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
`streamable-http`, e o servidor recusa iniciar se o bearer token estiver
ausente. Não coloque esse arquivo no Git. O perfil RAG usa `PersistentClient`
local e o cache de modelos fica em `models_cache/`, que é ignorado.

## Avaliação

```text
python -m docops golden-candidates <pacote> --json
python -m docops evaluate --package <pacote> --cases <golden-revisado.json> --adapter lexical --json
python -m docops evaluate --package <pacote> --cases <golden-revisado.json> --adapter mcp --runtime-root . --json
python scripts/evaluate_golden.py --cases golden-set/test-cases.json
```

O adapter `lexical` é um diagnóstico rápido; `memory` é adequado ao TDD; o
adapter `mcp` é a avaliação híbrida real e exige `rag/index.json` em modo
`indexed`. Todos exigem Golden revisado e o relatório explicita backend,
versão, perfil, corpus, rota, top-k e casos. Toda resposta factual do harness
deve citar `path#secao` ou `path:linha`.

O suporte publicado é Python 3.11–3.13 em Ubuntu, Windows e macOS; Python 3.14
é somente tolerado localmente. A matriz normativa está em
`docs/SUPPORT-MATRIX.json` e é validada por `scripts/check_support_matrix.py`.

## Auditoria de dependências

Em cada release, execute no ambiente usado pelo RAG:

```text
python scripts/audit_dependencies.py --requirements requirements.lock --local --strict
```

O comando falha para qualquer advisory fora do residual explicitamente
documentado em [SECURITY.md](../SECURITY.md). Trocar o perfil de embedding
exige `reindex_documents(full_rebuild=True)`; não reutilize um índice com
dimensão ou modelo diferentes.
Para integração Python, use a interface raiz documentada em
[`docs/PYTHON-API.md`](PYTHON-API.md); `docops.pipeline` permanece somente como
adapter de compatibilidade.
