# T05 — Comprovar indexação e perfil reais

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **piloto implementado; ver [estado](../IMPLEMENTATION-STATUS.md)**.

## Objetivo e entrega

Recusar sucesso aparente do backend e identificar configuração efetiva.

## Contexto

E17/E19: profile é literal no índice e inatividade/smoke não bastam para comprovar sucesso. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T02](./02-revision-evidence.md), [T04](./04-prepare-candidate.md)

Decisões aplicáveis: D08 para capacidades futuras; esta entrega não exige snapshot. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/rag_sync.py](../../../docops/rag_sync.py), [docops/runtime.py](../../../docops/runtime.py), [docops/operations.py](../../../docops/operations.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

Aplicação indexada, relatório JSON e processo MCP externo.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Servidor de fixture termina reindex com erro; operação não pode produzir candidata publicável nem indexed bem-sucedido.

**GREEN mínimo:** Validar erro terminal, resultado, documentos esperados e busca conhecida; registrar fingerprint de configuração real.

**REFACTOR:** Normalizar resultados MCP em envelope único.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [ ] Erro parcial, payload inválido e timeout falham de forma explícita.
- [ ] already_running não confirma o job errado.
- [ ] Smoke vazio não comprova corpus não vazio.
- [ ] Mudança de embedding exige full rebuild e invalida evidência.
- [ ] Executar integração com MCP real para comprovar busca após indexação.

Rastreabilidade: A05, A06, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [ ] Entrega demonstrável pelo seam declarado.
- [ ] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [ ] Critérios acima e checks pertinentes passam.
- [ ] Compatibilidade e exemplos JSON atualizados quando afetados.
- [ ] Evidência de teste distingue fixture, MCP real e harness externo.
- [ ] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [ ] Risco e procedimento de rollback documentados no resultado.

## Riscos

Backend instalado e vendor podem ter respostas distintas. Negociar capacidade/versão e falhar explicitamente.

## Estratégia de rollback

Manter índice ativo e descartar candidata inválida; rebuild explícito continua disponível.
