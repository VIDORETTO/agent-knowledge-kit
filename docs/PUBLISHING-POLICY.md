# Política de publicação

## Código

O código deste repositório é MIT, conforme `LICENSE`.

## Fontes e derivados

Uma fonte só pode sair de uma máquina privada quando a licença e a permissão de
redistribuição estiverem registradas no manifesto e forem compatíveis com a
política do mantenedor. `--license` registra o identificador fornecido pelo
usuário; o operador não presume que uma página web seja redistribuível. Sem
identificador, o pacote pode ser usado em `private-only`, mas não é elegível
para release pública.

O `.gitignore` mantém fontes adquiridas, índices, caches e saídas de execução
fora do versionamento. Apenas fixtures sintéticas e exemplos revisados ficam
permitidos em `documents/`. Antes de adicionar qualquer documento real,
confirme licença, autorização e necessidade de incluir o conteúdo.

## Release

Uma release deve conter código, testes, schemas, templates e fixtures
distribuíveis; nunca `documents/` adquirido, `.rag_state.json`, `data/`,
`models_cache/`, `.venv*`, tokens ou logs de usuário.

Em uma cópia limpa, rode `python scripts/audit_release.py --json` antes de
publicar. Em um checkout de trabalho que contenha ambientes ou caches
ignorados, use `python scripts/audit_release.py --tracked-only --json`; essa
forma audita exatamente o conteúdo que entrará no Git, sem transformar o
ambiente local em artefato de release.
