# Consolidação da main — plano e execução

Data da análise: 6 de setembro de 2026.

Este diretório registra a decisão e a execução da consolidação entre o working
tree analisado e `origin/feat/continuous-knowledge`, em uma branch isolada e
orientada a agentes. A implementação é seletiva e continua sem autorização
para merge automático, alteração de corpus/RAG real, publicação ou promoção de
release.

## Veredito em uma frase

Adotar uma consolidação seletiva, orientada por contratos: preservar o núcleo
modular do working tree, portar a experiência `docops-agent` e as barreiras
reais de segurança da branch remota, e oferecer um único lifecycle público
antes de promover qualquer coisa para `main`.

## Documentos

- [Comparação e decisão](COMPARISON-AND-DECISION.md): evidências, conflitos,
  riscos e decisão arquitetural.
- [Especificação](SPEC.md): resultado no formato da skill `to-spec`.
- [Plano TDD](TDD.md): seams públicos, ciclos RED → GREEN e gates.
- [Índice de tickets](tickets/README.md): ordem de execução e dependências.
- [Status de implementação](IMPLEMENTATION-STATUS.md): ticket, evidência e
  gate atual.
- [Política de contratos](../CONTRACT-COMPATIBILITY.md): fonte canônica,
  versionamento e compatibilidade expand-contract.

## Premissas usadas

- O destino é uma única `main`, e não a manutenção permanente de dois
  lifecycles.
- Compatibilidade pública deve ser expandida antes de qualquer remoção.
- “Aprendizado contínuo” significa sinal → investigação → candidata →
  avaliação → aprovação → publicação; nunca mutação automática da skill ativa.
- Não há integração autenticada com um issue tracker nesta tarefa. Os tickets
  são registros Markdown versionáveis e a evidência operacional fica no
  próprio ticket/status; a publicação local de issues continua fora do
  escopo.
- O questionário opcional da skill `to-tickets` foi substituído pelas
  preferências explícitas do pedido: documentação local, máxima estabilidade e
  agent-first.

## Estado da execução

O pedido confirmou a especificação, os seams públicos e a ordem dos tickets.
T01–T13 estão concluídos na branch `codex/main-consolidation`. T12 foi
verificado por 22 gates Windows sequenciais em
`artifacts/release-gates-final-20260907/release-gates.json`, clean clone,
wheels, MCP real, crash/revogação e concorrência; a evidência POSIX/WSL
registra os checks executáveis e os skips por ausência de pip/venv. T13 gerou o
relatório do candidato de integração em
`artifacts/integration-candidate-final-20260907/`. A decisão humana de
promoção permanece separada da implementação e não é inferida por um teste
verde.
