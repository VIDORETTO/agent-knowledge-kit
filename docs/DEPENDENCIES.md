# Dependências, atualizações e suporte

O núcleo `docops` usa a biblioteca padrão do Python. Os perfis opcionais são:

- `formats`: `PyYAML==6.0.3`, `pypdf==6.16.2` e `python-docx==1.2.0`;
- `rag`: `knowledge-rag==4.8.5` e suas dependências locais;
- `dev`: `pytest==9.1.1`, `ruff==0.12.7`, `pip-audit==2.10.1` e
  `setuptools==84.0.0`.

As versões diretas são repetidas em `pyproject.toml`,
`requirements-dev.txt` e `requirements.lock`. O bootstrap atualiza o
instalador para `pip==26.2.1` antes de instalar o projeto. O lock é uma lista
de requisitos diretos exatos, não um lock transitivo com hashes: wheels e
dependências transitivas variam por sistema operacional e Python, e o CI
resolve cada ambiente em um clone limpo.

## Política de atualização

Dependências diretas só podem mudar com atualização simultânea do contrato de
instalação, testes, changelog e auditoria. A cada release e no workflow de
integração:

```text
python -m pip check
python -m pip_audit --requirement requirements.lock --format json
python scripts/audit_dependencies.py --requirements requirements.lock --local --strict \
  --evidence-dir artifacts/dependency-audit
```

O gate reprova qualquer vulnerabilidade fora da allowlist explícita. Hoje a
única exceção é o conjunto de quatro avisos sem correção conhecida para o uso
local do ChromaDB; ela é classificada por pacote e CVE, e não por texto amplo.
Um advisory novo do Chroma reprova automaticamente o CI.

## Risco atual

`chromadb==1.5.9` permanece com os quatro CVEs registrados em
[SECURITY.md](../SECURITY.md). A justificativa operacional é restrita ao
`PersistentClient` em processo, sem `HttpClient`, sem `trust_remote_code` e com
MCP `stdio` como padrão. Isso é um risco residual documentado, não uma
declaração de ausência de vulnerabilidades.

Na revalidação final de 2026-09-04, o `pip-audit` cru retornou código 1 para
um pacote vulnerável e exatamente os quatro advisories do Chroma. O wrapper
local retornou `ok=true` somente porque a allowlist é vinculada simultaneamente
a `chromadb==1.5.9` e aos quatro IDs; uma versão diferente ou advisory novo
reprova. O diretório de evidência preserva stdout, stderr e exit code crus das
auditorias do lock e do ambiente local, separados do resumo de política.

O pacote vendorizado é uma cópia revisada de `knowledge-rag`; não se deve
atualizá-lo automaticamente a partir de `main`. O processo é: escolher uma
versão publicada, atualizar o pin e o `serverInfo`, revisar o diff da cópia,
executar os testes de segurança do vendor, a suíte raiz, o smoke RAG, os gates
de release e o `pip-audit`, e registrar a decisão no changelog.

## Plataformas

O alvo declarado é Python 3.11–3.13 em Windows, Ubuntu e macOS. A matriz do CI
executa instalação, testes rápidos, Ruff, doctor e auditoria nas três
plataformas; o pacote não depende de caminhos absolutos. Nesta release, a
execução manual local foi comprovada no Windows. O doctor e o compileall
rodaram em uma cópia Ubuntu WSL, mas o bootstrap completo não pôde ser
executado porque o host não tinha `python3-venv`/`pip` e não permitiu a
instalação administrativa; não há host macOS disponível. Portanto, Linux/macOS
não são apresentados como validação manual local; o CI é evidência adicional,
não substituto dessa limitação declarada.

O perfil RAG é opcional. O doctor informa `rag: missing` quando ele não está
instalado; defina `DOCOPS_REQUIRE_RAG=1` quando a validação depender do
servidor. Os testes de symlink podem ser pulados em hosts sem privilégio para
criar links; limites de tamanho e formatos opcionais continuam cobertos por
fixtures e pelo CI.
## Evidência do candidato

O lock de entrada é `requirements.lock`. Para cada candidato, a ferramenta
offline abaixo materializa o hash do lock e de cada linha, o inventário SPDX,
o digest do wheel, a árvore vendorizada e a provenance dos snapshots de modelo
fornecidos:

```text
python scripts/generate_supply_chain.py --root . --wheel dist/<wheel>.whl \
  --model-cache models_cache --output artifacts/supply-chain \
  --profile rag --require-model
python scripts/verify_supply_chain.py --root . --evidence artifacts/supply-chain
```

Os bytes de `models_cache/` nunca entram no bundle. Quando `--model-cache` é
fornecido, a evidência guarda somente uma lista determinística de arquivos,
digests e identidade do snapshot externo. `supply-chain.json` mantém a política
por perfil: Chroma é somente
`PersistentClient`, os quatro CVEs (`CVE-2026-45829`, `CVE-2026-45830`,
`CVE-2026-45831`, `CVE-2026-45833`) são risco residual explícito, e HTTP do
Chroma, `trust_remote_code` e repositórios remotos de modelo não são
permitidos. A ausência de um snapshot de modelo só é aceita quando
`--require-model` não foi solicitado. O perfil de dependências é independente:
o padrão é `--profile core`; um candidato RAG usa
`--profile rag --require-model`.

## Resolução efetiva e provenance

`requirements.lock` continua sendo a entrada direta agregada, portável entre os
perfis. Cada evidência registra `core` ou `rag` e inclui `locks.resolution` com o fechamento transitivo
observado por `pip inspect --local`, limitado às raízes exatas de
`requirements.lock`. Isso evita misturar pacotes incidentais do interpretador
com o perfil auditado. Dependências declaradas, markers, ausências/divergências
das raízes e o digest canônico são verificados; a evidência declara honestamente
que essa resolução continua ligada ao Python e à plataforma observados. No
perfil core, apenas `knowledge-rag` pode estar ausente; no perfil RAG todas as
raízes são obrigatórias, e uma versão divergente sempre reprova. Para
publicar em mais de um perfil, gere e anexe uma evidência por combinação de
Python/OS.

O vendor `knowledge-rag` é fixado em `v4.8.5` e no commit upstream
`f531148b0d5fe479e7f0a104daf21d8fde7d3189`, com licença, lista de arquivos e
digest verificados. A evidência é transportável no bundle (`evidence/`), não
depende de `artifacts/` ignorado. O arquivo
[`docs/CHROMA-RESIDUAL-DECISION.md`](CHROMA-RESIDUAL-DECISION.md) permanece um
gate: o raw audit e o allowlist são relatados separadamente, e a decisão
humana precisa estar preenchida antes de um release.
