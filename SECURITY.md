# Segurança

Não envie documentos privados, tokens, índices, caches ou relatórios com
conteúdo sensível em uma issue. Use o canal privado do mantenedor e inclua
versão, sistema operacional, comando reproduzível e um fixture mínimo
sanitizado.

As fronteiras externas têm estas regras:

- URLs com credenciais, loopback, metadata cloud, redes privadas e redirects
  para esses destinos são bloqueados por padrão.
- Payload, timeout, content-type, páginas, profundidade e retries são limitados.
- HTML com pouco texto e scripts é reportado como dependente de browser; não há
  falsa indicação de sucesso.
- Conteúdo ingerido é tratado como não confiável e nunca é executado.
- Transporte `sse`/`streamable-http` só é aceitável com bearer token não
  placeholder, rate limit, métricas e logging JSON; valide o arquivo antes de
  iniciar o servidor.

```text
python -m docops config-audit config/network.yaml
python scripts/audit_release.py --json
```

Relate problemas de segurança sem publicar o corpus ou o token afetado.
