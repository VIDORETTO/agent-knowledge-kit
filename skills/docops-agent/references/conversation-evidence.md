# Evidência mínima para aprendizado de conversas

Uma conversa produz uma proposta, não uma verdade. Capture somente a alegação
mínima autorizada; nunca copie o chat inteiro para o corpus compartilhado.

## Envelope recomendado

```json
{
  "claim": "A regra ...",
  "claim_type": "correction",
  "scope": "service-x",
  "version": "2026.09",
  "privacy": "shared",
  "origin": {
    "actor": "user-or-system-id",
    "consent": true,
    "source": "conversation",
    "observed_at": "2026-09-05T12:00:00Z"
  },
  "evidence": [
    {
      "kind": "primary-source",
      "source": "docs/retry.md",
      "locator": "#policy",
      "content_hash": "...",
      "independent": true
    }
  ]
}
```

O campo `independent` é uma declaração para revisão, não uma prova de
identidade. A pessoa responsável deve verificar autoridade, escopo e conteúdo.

## Regras por tipo

| Tipo | Evidência exigida | Destino |
|---|---|---|
| `fact` | fonte primária ou experimento reproduzível | candidata factual/conceitual conforme impacto |
| `correction` | fonte que contradiz a resposta anterior | investigação e candidata |
| `decision` | decisão aprovada por responsável do escopo | registro local e candidata |
| `experiment` | condições, resultado e limites | candidata/rubrica experimental |
| `question` | ausência de resposta, sem alegar verdade | investigação ou Golden candidato |
| `opinion`/`preference` | não são evidência compartilhada | memória privada ou rejeição |

`privacy=shared` exige consentimento e revisão. `private` e `restricted` não
podem ser materializados no RAG compartilhado. Uma resposta do agente, repetição
de usuários ou feedback positivo não é evidência independente.

## Checklist do revisor

1. A alegação está minimizada e sem segredo/PII?
2. O ator autorizou o uso no escopo indicado?
3. A fonte é acessível, licenciada e realmente sustenta o claim?
4. O reviewer é independente do proponente?
5. Existe conflito com fonte de maior autoridade ou versão diferente?
6. A materialização deve atingir apenas RAG, candidata de skill ou ambos?

Se qualquer resposta for incerta, mantenha `quarantined`; não promova por
popularidade ou pela confiança do modelo.
