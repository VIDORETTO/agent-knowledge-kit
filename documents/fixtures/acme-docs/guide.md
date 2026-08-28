# Acme API Guide

The Acme client is a synthetic documentation fixture for `consulta-documentacao`.
It demonstrates authentication, retries and source citations without copying a
real project's documentation.

## Authentication

Create a client with a bearer token. The token is sent in the `Authorization`
header and must never be written to a source file or report.

## Retries

Retry a transient `429` or `503` response with bounded exponential backoff.
Do not retry authentication failures or malformed requests.

## Errors

Return a JSON error with a stable `code` and a human-readable `message`.