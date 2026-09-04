# Divulgação 1.1.0 — rascunho não enviado

> Não enviar nem agendar este texto. Ele só pode sair depois de uma release
> pública verificável, instalação externa aprovada e canário sem regressão.

## Mensagem curta

O `consulta-documentacao` 1.1.0 prepara documentação para agentes como uma
skill estruturada, um roteador e, opcionalmente, um índice RAG local via MCP.
O pacote não inclui LLM, provedor, serviço hospedado, corpus adquirido ou
cache de modelo. O fluxo mínimo é resolver a fonte, executar `run`, validar o
pacote e avaliar as consultas revisadas.

## O que apontar

- Release notes: `docs/RELEASE-NOTES-1.1.0.md`.
- Instalação e limites: `README.md`, `docs/USE.md` e `docs/PUBLISHING-POLICY.md`.
- Segurança: `SECURITY.md`.
- Suporte: `docs/SUPPORT-MATRIX.json`.
- Evidência de assets: checksums, SBOM e provenance anexados à release
  aprovada.

## O que não afirmar

- Não dizer que o pacote executa LLM, escolhe provedor ou oferece RAG remoto.
- Não prometer suporte fora da matriz verificada.
- Não chamar o raw `pip-audit` de limpo enquanto o residual Chroma existir.
- Não divulgar corpus, consultas, prompts, logs, caches, tokens ou caminhos
  privados.
- Não iniciar divulgação ampla antes da observação controlada de 24 horas.

## Destinos e aprovação

O único destino desta versão é o próprio GitHub Release, com README/changelog
coerentes no repositório. Registry e canais externos ficam explicitamente fora
do escopo; não haverá anúncio para contas externas. O responsável deve
confirmar o horário e a janela de observação no handoff antes do envio.
