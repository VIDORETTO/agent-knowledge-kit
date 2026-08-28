# Tutorial reproduzível com fixture sintética

Este tutorial não baixa nem redistribui documentação de terceiros.
`documents/fixtures/acme-docs/` é conteúdo sintético coberto pela licença do
projeto.

## 1. Preparar

```text
python scripts/bootstrap.py --dev
python -m docops doctor --json
```

## 2. Produzir o pacote

```text
python -m docops run documents/fixtures/acme-docs --output artifacts/acme --slug acme --license MIT --redistribution private-only
```

O comando não precisa de um LLM. Ele normaliza a fixture, escreve a skill,
roteador, RAG e `manifest.json` e valida o contrato no fim.

## 3. Conferir e avaliar

```text
python -m docops validate artifacts/acme --json
python -m docops golden-candidates artifacts/acme --json
```

Perguntas candidatas começam com `reviewed: false`. Um mantenedor deve revisar
cada pergunta e fonte antes de promover o arquivo para avaliação:

```json
{
  "schema_version": 1,
  "reviewed": true,
  "cases": [
    {
      "query": "How does the Acme client authenticate?",
      "expected_filepath": "guide.md",
      "kind": "factual",
      "reviewed": true
    }
  ]
}
```

Depois:

```text
python -m docops evaluate --package artifacts/acme --cases golden.json --json
```

## 4. Usar no harness

Leia `artifacts/acme/harness.json`, carregue seus diretórios `skill/` e
`router/` e registre o MCP. Perguntas conceituais devem carregar a skill;
defaults, assinaturas, versões e números devem chamar `search_knowledge` e
responder com a origem.

## 5. Página local para teste web

Para testar aquisição web sem abrir a rede privada, crie um servidor fixture
em um teste e passe `--allow-private-network` somente nessa execução. Em
produção, não habilite essa opção: a política bloqueia loopback, metadata,
credenciais em URL, redirects perigosos e payloads acima do limite.
