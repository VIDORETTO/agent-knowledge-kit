# T14 — Fixar geração e restringir MCP de consulta

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **implementado em 2026-09-05**.

## Objetivo e entrega

Impedir composição mista e mutação fora do coordenador.

## Contexto

E23: hand-off atual não garante fixação de sessão nem enforcement de ferramentas somente leitura. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Dependências concluídas: [T08](./08-approve-publish.md), [T09](./09-history-rollback.md)

Decisões aplicáveis: D08; atualizar backend vendor e schemas do harness. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/harness.py](../../../docops/harness.py), [docops/runtime.py](../../../docops/runtime.py).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

Hand-off de geração, sessão MCP real e publicação concorrente.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Sessão fixada consulta durante publicação; segue na mesma composição. Tentativa de add_document é recusada.

**GREEN mínimo:** Referência à geração imutável e perfil de consulta restrito no backend; manutenção usa capacidade separada.

**REFACTOR:** Separar capacidades de consulta e manutenção no runtime.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] Sessão nova recebe a geração corrente e fixa `release_id` +
  `composition_hash`.
- [x] Writer do harness de consulta é recusado pelo servidor; a sessão aceita
  somente `search_knowledge` e `get_document`.
- [x] Cache é vinculado a sessão, ferramenta, consulta e geração.
- [x] Revogação de sessão e de geração histórica bloqueia consultas futuras.
- [x] Backend MCP sem `mode=read_only` e capacidades compatíveis falha fechado;
  publicação concorrente permanece desabilitada.

Rastreabilidade: A12, A14 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pela CLI pública `reader-session`,
  `reader-query` e `reader-session-revoke`.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Schemas, exemplos e documentação foram atualizados.
- [x] Evidência de teste usa fixtures sintéticas; a capacidade MCP é validada
  no manifesto, sem executar harness externo.
- [x] Nenhuma publicação externa ou alteração do corpus ativo foi feita.
- [x] Risco e procedimento de rollback estão documentados no resultado.

## Riscos

Windows e processos com arquivos abertos exigem validação própria; texto do router não é controle de acesso.

## Estratégia de rollback

Desabilitar publicação concorrente e usar atualização coordenada manual, sem alegar isolamento não comprovado.

## Resultado da execução

- RED: `tests/test_reader_sessions.py` começou com quatro falhas porque os
  subcomandos ainda não existiam.
- GREEN: `4 passed`; criação, pinagem, recusa de writer, troca de geração,
  cache, revogação e perfil MCP read-only foram observados pela CLI.
- REFACTOR: o estado runtime foi separado para
  `.<package>.readers/`, evitando que uma substituição coordenada do pacote
  apague sessões e tombstones; o diretório é ignorado pelo Git.
- Arquivos principais: `docops/reader_sessions.py`, `docops/harness.py`,
  `docops/__main__.py`, `docops/contracts.py`, os dois pares de schemas,
  `tests/test_reader_sessions.py` e documentação.
- Limitações: a fixture `memory` é sintética; o adapter MCP somente verifica o
  contrato read-only do harness e não conecta um servidor externo neste ticket.
- Rollback: parar de criar/aceitar novas sessões, manter a geração coordenada
  manual e preservar o histórico/tombstones; remover a integração do reader
  não deve apagar o histórico editorial nem revalidar sessões antigas.
