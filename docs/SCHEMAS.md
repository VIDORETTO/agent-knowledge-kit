# Contratos JSON

Os arquivos em `schemas/` são versões públicas e o `manifest.json` sempre
declara `schema_version`. Campos desconhecidos podem ser adicionados de forma
aditiva; remover ou mudar o significado de um campo exige nova versão.

- `manifest.schema.json`: fonte, proveniência, entradas, artefatos,
  checkpoints, métricas, avisos e erros;
- `harness.schema.json`: skills e registro MCP relativo;
- `golden.schema.json`: conjunto revisado de perguntas e origem esperada;
- `validation.schema.json`: resultado do validador de pacote.
- `plan.schema.json`: plano imutável, diff, blockers e fingerprints;
- `result.schema.json`: projeção terminal de `apply`, incluindo outcome e exit code;
- `outcome.schema.json`: autoridade terminal compartilhada por manifesto e resultado;
- `evaluation.schema.json`: métricas, casos, thresholds e procedência do adapter;
- `golden-candidates.schema.json`: candidatos explicitamente ainda não revisados.

O validador Python é a seam executável usada pelos testes; os schemas tornam o
contrato inspecionável por ferramentas externas sem executar o servidor. O
mesmo conjunto é empacotado em `docops/schemas/` para que o wheel não dependa
do checkout. `scripts/check_contracts.py` verifica exemplos válidos, mutações
negativas e drift semântico entre as duas cópias.
