# Changelog

## 1.0.0 — 2026-08-29

- Primeira versão estável do protocolo DOCOPS para fontes locais, web e
  repositórios.
- Pacotes gerados agora são autossuficientes, com configuração MCP relativa,
  validação de divergência e smoke test do wheel instalado.
- Atualizações protegem configuração existente, evitam colisões, removem
  capítulos obsoletos e falham fechado para saídas dentro da fonte, symlinks,
  documentos inválidos e golden sets não revisados.

## Unreleased

- Adicionado o protocolo portátil `docops` para resolução, aquisição,
  normalização, skill, roteador, manifesto e validação.
- Adicionadas políticas de SSRF, limites de crawl, proveniência, checkpoints,
  idempotência e sincronização opcional com `knowledge-rag`.
- O crawler passou a respeitar `robots.txt`, rejeitar credenciais em query string
  e gerar destinos seguros e distintos para variantes de URL.
- Adicionados bootstrap multiplataforma, auditoria de configuração/release,
  fixtures sintéticas e documentação de integração com harnesses externos.
