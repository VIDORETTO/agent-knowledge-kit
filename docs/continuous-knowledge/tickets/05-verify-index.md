# T05 — Comprovar indexação e perfil reais

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente; sem publicação externa**.

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

- [x] Erro parcial, payload inválido e timeout falham de forma explícita.
- [x] already_running não confirma o job errado.
- [x] Smoke vazio não comprova corpus não vazio.
- [x] Mudança de embedding exige full rebuild e invalida evidência.
- [x] Executar integração com MCP real para comprovar busca após indexação.

Rastreabilidade: A05, A06, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Compatibilidade e exemplos JSON atualizados quando afetados.
- [x] Evidência de teste distingue fixture, MCP real e harness externo.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Riscos

Backend instalado e vendor podem ter respostas distintas. Negociar capacidade/versão e falhar explicitamente.

## Estratégia de rollback

Manter índice ativo e descartar candidata inválida; rebuild explícito continua disponível.

## Resultado da execução

- RED observado primeiro em `tests/test_rag_sync.py`: um fixture com
  `last_error` terminal ainda retornava `ok=true`.
- GREEN/refactor: `docops/rag_sync.py` agora normaliza payloads MCP, exige
  estado terminal verificável, contagens de documentos/chunks e resultado de
  busca não vazio; erros recebem códigos explícitos. O relatório registra
  `requested_operation`, `full_rebuild`, fingerprint da configuração,
  perfil/configuração efetiva, modelo/dimensões observados no backend e
  proveniência/versionamento.
- `docops/operations.py` compara o fingerprint de embedding da geração ativa e
  solicita `full_rebuild=true` quando o embedding muda ou a evidência anterior
  não existe. Falha de indexação durante política `candidate` ocorre antes de
  preparar a candidata, preservando a ativa.
- Fixtures públicas: `46 passed` em
  `tests/test_rag_sync.py`, `tests/test_continuous_knowledge.py` e
  `tests/test_post_lifecycle.py`; Ruff lint/formato do slice: **PASS**.
- MCP real isolado: pacote temporário com um `guide.md`, vendor
  `knowledge-rag==4.8.5`, perfil `compact`, modelo efetivo
  `BAAI/bge-small-en-v1.5`, 384 dimensões, 1 documento/1 chunk e busca com
  1 resultado: **PASS**. Nenhum corpus/índice do checkout foi usado.
- Harness externo: não executado neste ticket.
