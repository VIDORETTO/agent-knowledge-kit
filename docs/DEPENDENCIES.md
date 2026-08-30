# Dependências e suporte

O núcleo `docops` usa a biblioteca padrão do Python. Os perfis opcionais são:

- `formats`: PyYAML, pypdf e python-docx para formatos especiais;
- `rag`: `knowledge-rag==4.8.5` e suas dependências locais;
- `dev`: pytest e ruff.

As versões diretas estão em `requirements.txt`, `requirements-dev.txt` e
`requirements.lock`; o `pyproject.toml` mantém o mesmo contrato para instalação
editável. Dependências transitivas do fornecedor são resolvidas pelo release
fixado do `knowledge-rag` e não devem ser vendorizadas junto com corpora.

O alvo de CI é Python 3.11, 3.12 e 3.13 em Windows, Ubuntu e macOS; o job de
empacotamento usa Python 3.12. O perfil
rápido não precisa de RAG; o doctor informa `rag: missing` como capacidade
opcional. Defina `DOCOPS_REQUIRE_RAG=1` quando a validação depender do servidor.
