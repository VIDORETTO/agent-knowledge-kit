# T04 — Preparar candidata sem ativar

[Índice dos tickets](../TICKETS.md) · [Especificação](../SPEC.md) · [TDD](../TDD.md)

Status: **concluído localmente; aprovação/publicação permanece no T08**.

## Objetivo e entrega

Produzir pacote revisável e retomável sem substituir a geração ativa.

## Contexto

E02 oferece staging e recuperação, mas apply normalmente promove ao concluir. Evidências referenciadas em [EVIDENCE](../EVIDENCE.md).

## Dependências

Blocked by: [T02](./02-revision-evidence.md), [T03](./03-rag-preserve-skill.md)

Decisões aplicáveis: D04. Ver [registro de decisões](../DECISIONS.md).

## Arquivos, módulos e contratos

[docops/operations.py](../../../docops/operations.py), `docops/candidates.py` (novo).

Atualizar CLI/exports apenas quando o seam exigir. Quando houver envelope novo ou
alterado, atualizar schemas/ e docops/schemas/ juntos, exemplos e documentação.
Adicionar teste comportamental em tests/ pela interface pública; nomes de arquivos
novos são propostas, não módulos existentes.

## Seam público

apply com política proposta de candidata, inspect e CLI validate.

Não testar helpers privados, ordem de chamadas ou tabelas internas. Observar o
resultado pelo mesmo caminho disponível ao operador/consumidor.

## Cenário e ciclo TDD

**RED:** Preparar candidata de uma fonte alterada; a ativa deve continuar na revisão anterior enquanto a candidata é inspecionável.

**GREEN mínimo:** Concluir staging validado e devolver candidate_id, sem executar promoção.

**REFACTOR:** Reutilizar as fases existentes de preparação e validação.

Depois do primeiro ciclo, adicionar os demais casos de aceite um por vez. Não
implementar todos os testes primeiro. O RED precisa falhar pela expectativa
comportamental, não por erro acidental da fixture.

## Critérios de aceite

- [x] Candidata possui base e hashes identificados no recibo
  `.docops/candidate.json`.
- [x] Ativa não muda durante preparação; `publication_policy="candidate"`
  nunca executa promoção.
- [x] Candidata interrompida é retomável por staging persistido e caminhos
  arbitrários aparecem como entradas rejeitadas pelo `inspect` seguro.
- [x] Falha estrutural impede estado publicável; `validate` falha e a
  candidata fica `rejected`, sem alterar a ativa.

Rastreabilidade: A07, A16 em [VALIDATION](../VALIDATION.md).

## Definição de pronto

- [x] Entrega demonstrável pelo seam declarado.
- [x] Primeiro RED observado, GREEN mínimo implementado e refactor protegido.
- [x] Critérios acima e checks pertinentes passam.
- [x] Envelope de outcome e os dois schemas foram atualizados com
  `candidate_id`/`candidate_locator`.
- [x] Evidência usa fixtures sintéticas e subprocesso local; MCP real e
  harness externo não foram executados neste ticket.
- [x] Nenhuma alteração fora do escopo ou publicação externa implícita.
- [x] Risco e procedimento de rollback documentados no resultado.

## Evidência da execução

- RED: o primeiro teste de política candidata observou a promoção normal e
  não encontrou uma candidata inspecionável.
- GREEN/refactor: `docops/candidates.py` materializa staging em um diretório
  irmão controlado, grava base/revisões/hash do plano e mantém o pacote ativo
  intocado; `inspect` valida e classifica candidatos, enquanto `validate`
  continua sendo o gate estrutural.
- Verificação focada:
  `rtk pytest -q tests/test_continuous_knowledge.py` — **14 passed**.
- Lint do slice:
  `rtk proxy python -m ruff check docops/candidates.py
  docops/operations.py docops/api_types.py docops/__main__.py
  tests/test_continuous_knowledge.py` — **PASS**.

## Operação e rollback

Use `--publication-policy candidate` em `run`/`update`; o resultado retorna
`candidate_id` e `candidate_locator`. Inspecione a saída ativa e a lista
`candidates` antes de qualquer aprovação futura. A retenção fica no diretório
irmão `.<nome-do-pacote>.candidates`, fora da geração ativa.

Para rollback, descarte somente a candidata identificada ou mantenha-a
`review_required`/`rejected`; não substitua a ativa. Aprovação e promoção por
hash/base exatos pertencem ao T08.

## Riscos

Candidatas podem consumir disco e conter dados privados. Retenção operacional deve ser explícita.

## Estratégia de rollback

Descartar somente candidata identificada ou mantê-la bloqueada; a ativa permanece intacta.
