# Dependências, atualizações e suporte

O núcleo `docops` usa a biblioteca padrão do Python. Os perfis opcionais são:

- `formats`: `PyYAML==6.0.3`, `pypdf==6.16.2` e `python-docx==1.2.0`;
- `rag`: `knowledge-rag==4.8.5` e suas dependências locais;
- `dev`: `pytest==9.1.1`, `ruff==0.12.7` e `pip-audit==2.10.1`.

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
python scripts/audit_dependencies.py --requirements requirements.lock --local --strict
python -m pip check
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
