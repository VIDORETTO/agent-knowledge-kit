# Changelog

## Unreleased

No changes yet.

## 1.0.0 — 2026-08-29

- Primeira versão estável do protocolo DOCOPS para fontes locais, web e
  repositórios.
- Pacotes gerados agora são autossuficientes, com configuração MCP relativa,
  validação de divergência, harness manifest e smoke test do wheel instalado.
- Adicionados bootstrap multiplataforma, auditoria de configuração/release,
  fixtures sintéticas e documentação de integração com harnesses externos.
- Atualizado o conjunto direto de ferramentas para `pytest==9.1.1`,
  `ruff==0.12.7`, `pip-audit==2.10.1` e bootstrap com `pip==26.2.1`.
- Adicionada auditoria de dependências com allowlist estreita e documentada
  para os quatro CVEs sem correção conhecida do ChromaDB; outros achados
  permanecem bloqueadores.
- Corrigido o fallback YAML para comentários inline, tornando o doctor
  funcional em clones limpos sem PyYAML.
- Corrigidos os nomes das métricas do avaliador para refletirem qualquer
  `--top-k` válido.
- Tornado o smoke MCP resistente a timeout, EOF prematuro, stderr cheio e
  encerramento de processo sem mascarar o erro original.
- Alinhado o `serverInfo` vendorizado com `knowledge-rag==4.8.5` e feito o
  transporte HTTP/SSE recusar inicialização sem bearer token.
- Reforçadas as aquisições externas contra DNS rebinding (inclusive com IPs
  fixados no Git), redirects, submódulos, protocolo `file`, prompts interativos
  e clones acima do limite.
- Adicionados testes de regressão para SSRF/TOCTOU, repositório remoto,
  autenticação bearer, auditoria de dependências e fluxo de erro do smoke MCP.
- Mantido o perfil padrão local `stdio`; corpus adquirido, índices, caches,
  tokens e ambientes virtuais continuam fora da publicação.
