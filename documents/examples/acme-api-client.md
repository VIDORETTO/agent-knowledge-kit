# acme-api-client — API Reference (dev corpus, exemplo)

> Corpus fictício de desenvolvimento. Substituir pelo framework-alvo real na
> Fase 0. Serve para validar RAG, skill roteadora e golden set de ponta a ponta.

## Visão geral

`acme-api-client` é um cliente HTTP para a API ACME v3. Funciona em Python
3.11+ e Node.js 18+. Todas as chamadas precisam de `ACME_API_KEY` no cabeçalho
`x-acme-key`.

## Client.request()

Assinatura:

```python
client.request(method: str, path: str, *, body: dict | None = None,
               timeout: float = 30.0, retries: int = 2) -> RequestResult
```

### Parâmetros

- `method` — string HTTP: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`.
- `path` — caminho do recurso, ex.: `"/v3/projects"`.
- `body` — payload JSON opcional (um só nível é serializado com camelCase).
- `timeout` — segundos até `RequestTimeoutError` (padrão 30.0, máx. 120.0).
- `retries` — número de tentativas extras em falha 5xx/429 (padrão 2).

### Retorno

`RequestResult` com `.status_code`, `.data` (dict|None) e `.headers`.

### Erros levantados

| Erro | Condição |
|---|---|
| `RequestTimeoutError` | tempo excedeu `timeout` |
| `RateLimitedError` | HTTP 429 (usa `Retry-After` se presente) |
| `ApiVersionError` | path sem `v3/` prefixo |

Exemplo:

```python
from acme_api import Client

client = Client("acme-key-123")

result = client.request("GET", "/v3/projects")
assert result.status_code == 200
print(result.data)
```

## Paginação

Endpoints listáveis aceitam `page` (1-indexado, padrão 1) e `page_size`
(padrão 50, máx. 500). Respostas paginadas incluem `total_items` e
`has_next`. Para exaustividade use `client.iter_paginated(path)` — ele
acompanha `has_next` automaticamente e faz no máximo 20 páginas.

## Rate limits

- Free tier: 100 requisições/minuto.
- Enterprise: 1.000 requisições/minuto.
- 429 sempre vem com `Retry-After`; o client respeita e tenta de novo
  quando `retries` estiver disponível.

## Módulo assíncrono (novo na v3.3.0)

`Client.async_request()` está disponível para fluxos aguardar `aiohttp` com a
mesma assinatura de `request()`, exceto `timeout` que é aceito em segundos
float e `retries` que usa backoff exponencial padrão quando `retries > 1`.

## Changelog v3.2.0

- `request()` agora aceita `body` como `dict` (antes: string JSON).
- Novo erro `ApiVersionError` para paths sem `v3/`.
- `Client.iter_paginated` introduzido nesta versão.
- Deprecado: `client.join(endpoint, key)` — removido na v4. Use `path` direto.