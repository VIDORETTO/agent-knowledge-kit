# Atualização contínua de conhecimento

Status: **piloto implementado e verificável na branch `feat/continuous-knowledge`**.

Este conjunto documenta a evolução do DOCOPS para atualizar RAG e skill com
cadências distintas, candidatas revisáveis, evidências e rollback. Criar estes
documentos não aprova as decisões pendentes nem habilita automação fora do
worker local. Consulte o [estado de implementação](IMPLEMENTATION-STATUS.md)
para distinguir o que já existe no checkout, o que é contrato de integração e o
que permanece pendente.

## Ordem de leitura

1. [Especificação técnica](SPEC.md): recomendação e análise nos 13 tópicos solicitados.
2. [Evidências da arquitetura atual](EVIDENCE.md): fatos, símbolos e limitações observadas.
3. [Contratos propostos](CONTRACTS.md): interfaces, identidades, estados e transações.
4. [Validação e aceitação](VALIDATION.md): métricas, cenários e gates.
5. [Tickets e dependências](TICKETS.md): 18 entregas verticais, uma por arquivo.
6. [Plano TDD](TDD.md): seams, primeiro RED, GREEN mínimo e ciclos seguintes.
7. [Decisões pendentes](DECISIONS.md): escolhas que precisam ser resolvidas antes da fase correspondente.
8. [Estado de implementação](IMPLEMENTATION-STATUS.md): matriz de tickets, comandos e limites atuais.

## Recomendação

Atualizar fatos rapidamente após admissão das fontes; atualizar conhecimento
conceitual em lotes e candidatas; usar conversas como propostas verificáveis em
quarentena. Preservar o harness externo como executor de modelos.

**Primeiro ticket:** [T01 — proteger enriquecimento](tickets/01-protect-enrichment.md).
Seu primeiro teste deve demonstrar que uma atualização documental não substitui
silenciosamente uma skill enriquecida por scaffold.

## Convenções e autoridade

- **Fato:** observado no checkout analisado, com referência em EVIDENCE.md.
- **Inferência:** consequência deduzida, ainda não necessariamente reproduzida.
- **Proposta:** funcionalidade, política, contrato ou parâmetro futuro.
- **Pendente:** decisão sem aprovação registrada.

Baseline: commit `566ac3b8d16e3e65785859ba46c35fe0212c87c1`, versão declarada
`1.1.0`, análise em 2026-09-04. Mudanças posteriores exigem revalidar as
evidências. Números históricos FastAPI não são novas medições deste plano.

O processo de desenho utilizado foi `to-spec → to-tickets → tdd`, com
vocabulário de seams de `codebase-design`. A implementação incremental desta
branch cobre o ciclo local seguro descrito no estado de implementação; os
tickets continuam sendo a trilha de rastreabilidade, não issues abertas em um
rastreador externo.

Para evitar duplicação normativa: SPEC define a política; CONTRACTS detalha
interfaces; VALIDATION define os critérios; os tickets referenciam esses
documentos. Se uma decisão mudar, atualizar primeiro a especificação e depois
os tickets afetados. Nenhuma proposta aqui altera o contrato atual por si só.
