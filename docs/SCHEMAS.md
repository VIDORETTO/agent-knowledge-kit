# Contratos JSON

Os arquivos em `schemas/` são versões públicas e o `manifest.json` sempre
declara `schema_version`. Campos desconhecidos podem ser adicionados de forma
aditiva; remover ou mudar o significado de um campo exige nova versão.

- `manifest.schema.json`: fonte, proveniência, entradas, artefatos,
  checkpoints, métricas, avisos e erros;
- `harness.schema.json`: skills e registro MCP relativo;
- `golden.schema.json`: conjunto revisado de perguntas e origem esperada;
- `validation.schema.json`: resultado do validador de pacote.

O validador Python é a seam executável usada pelos testes; os schemas tornam o
contrato inspecionável por ferramentas externas sem executar o servidor.
