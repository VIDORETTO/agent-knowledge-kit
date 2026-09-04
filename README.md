# consulta-documentacao

`consulta-documentacao` 1.1.0 transforma uma referência de documentação em um
pacote de conhecimento para agentes. Ele resolve a
fonte, adquire e normaliza documentos, gera uma skill e um roteador, prepara o
corpus para `knowledge-rag` e registra tudo em um manifesto com outcome terminal,
proveniência e recibos verificáveis.

O projeto não contém nem escolhe um LLM, provedor, modelo, chat ou chave de
API. OpenCode e Codex foram validados na matriz de suporte; qualquer outro
harness precisa implementar Agent Skills e MCP stdio. O MCP é uma ferramenta
local opcional para recuperação; o operador continua utilizável sem o servidor
RAG instalado. Claude Code não é um alvo de suporte anunciado nesta versão.

## Começo rápido

A versão 1.1.0 cobre Python 3.11–3.13 em Ubuntu, Windows e macOS. Python
3.14 é apenas tolerado localmente até entrar na matriz; Git é necessário para
fontes de repositório.

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
`Scripts/python.exe`, e não dependem de um caminho da máquina do autor. A
execução manual deste candidato foi comprovada no Windows; Linux/macOS ficam
exercitados pela matriz do CI e não são apresentados como validação manual
local.

## Matriz de suporte

A matriz normativa está em [docs/SUPPORT-MATRIX.json](docs/SUPPORT-MATRIX.json).

## Um fluxo completo

O mesmo protocolo aceita pasta, arquivo, URL de página, URL de repositório ou
nome presente no catálogo:

```text
python -m docops resolve ./documents/fixtures/acme-docs --json
python -m docops plan ./documents/fixtures/acme-docs --output ./artifacts/acme --slug acme --license MIT --json
python -m docops run ./documents/fixtures/acme-docs --output ./artifacts/acme --slug acme --license MIT
python -m docops validate ./artifacts/acme --json
python -m docops golden-candidates ./artifacts/acme --json
```

`plan` resolve, adquire, normaliza, aplica políticas e calcula o diff sem
escrever no destino. O plano pode ser aplicado pelo seam Python
`docops.plan()`/`docops.apply()`; `run` é a conveniência compatível que encadeia
os dois. `create` recusa substituir pacote gerenciado, `update` exige pacote
compatível e `dry-run` é alias sem efeitos de `plan`.

O `run` produz `manifest.json`, `config.yaml`, `harness.json`, `skill/`,
`router/` e `rag/`. A nova geração é construída em staging, validada e
promovida como conjunto; checkpoints com hashes permitem retomar fases válidas.
Repetir o comando reconcilia estado por identidade canônica, versão e hash;
`--index-rag` também executa a sincronização real do MCP. O caminho feliz não
exige copiar e colar instruções entre ferramentas.

O manifesto distingue `scaffold-ready`, `skill-enriched`, `corpus-ready`,
`indexed`, `evaluated` e `release-ready`. O scaffold só vira `skill-enriched`
quando o fold-in externo registra ferramenta, versão, hash e validação.

Para uma fonte web, use limites explícitos (`--max-pages`, `--max-depth`,
`--include`, `--exclude`). Loopback e redes privadas são bloqueados por padrão;
`--allow-private-network` existe somente para fixtures locais controladas.

Nomes são resolvidos pelo catálogo curado local por padrão. Um harness pode
fornecer um resolver provider explícito; o núcleo não faz descoberta web
silenciosa. `--runtime-root` e `--source-root` tornam a execução independente do
diretório atual.

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

## Comunidade e metadata

O [Code of Conduct](CODE_OF_CONDUCT.md), a [contribuição](CONTRIBUTING.md),
as políticas em [community/](community/) e o [checklist manual de settings do
GitHub](community/GITHUB-SETTINGS-CHECKLIST.md) são distribuídos e nunca
alterados automaticamente. A metadata do repositório está em
[docs/REPOSITORY-METADATA.json](docs/REPOSITORY-METADATA.json).

## Versão 1.1.0 e verificação

Esta versão é distribuída exclusivamente pelo GitHub Release. O checkpoint
para retomar o follow-up do CI do wheel RAG está em
[docs/HANDOFF-2026-09-04-CI-WHEEL.md](docs/HANDOFF-2026-09-04-CI-WHEEL.md).
Para materializar e verificar o conjunto exato de arquivos:

```text
python scripts/prepare_candidate.py --root . --output artifacts/candidate-1.1.0
python scripts/verify_candidate.py --root artifacts/candidate-1.1.0
python scripts/verify_candidate.py --root artifacts/candidate-1.1.0 --source-root .
```

O bundle registra o commit base, o digest do candidato, wheel, checksums, SBOM,
proveniência do vendor, manifest/digest do snapshot externo de modelo e as
pendências de autorização humana. Bytes de cache de modelo não entram no
candidate. Nenhum script de verificação executa commit, tag, push, publicação
ou release.

O plano completo para fechar os gates, publicar de forma controlada, executar o
canário e fazer divulgação progressiva está em
[docs/PRODUCTION-PUBLICITY-PLAN.md](docs/PRODUCTION-PUBLICITY-PLAN.md).
O registro da execução atual e dos bloqueios humanos está em
[docs/RELEASE-READINESS-2026-09-04.md](docs/RELEASE-READINESS-2026-09-04.md),
e as notas para revisão estão em
[docs/RELEASE-NOTES-1.1.0.md](docs/RELEASE-NOTES-1.1.0.md).

Políticas comunitárias estão em [community/](community/), e a metadata do
repositório está em [docs/REPOSITORY-METADATA.json](docs/REPOSITORY-METADATA.json).
