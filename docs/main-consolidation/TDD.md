# Plano TDD para consolidação da main

## Objetivo

Guiar a implementação futura por fatias verticais observáveis, preservando
segurança, compatibilidade e recuperação. Este documento não implementa os
testes; define a sequência RED → GREEN → REFACTOR.

## Seams públicos propostos

Estes seams devem ser confirmados antes do primeiro ciclo de implementação:

1. CLI canônica hierárquica para `skill`, `agents-bootstrap` e `lifecycle`.
2. Aliases de compatibilidade para os comandos planos existentes.
3. Fachada pública única de lifecycle para os usos Python.
4. Contratos JSON versionados para entradas, receipts e estado publicado.
5. `harness.json` como contrato de operador, geração e processo MCP.
6. Skill operacional instalada e descoberta pelo pacote.
7. Processo MCP reader read-only e pinado.
8. Processo de manutenção separado do reader.
9. Pacote candidato e release publicada como artefatos observáveis.
10. Runtime versionado com status, migração e recuperação públicas.

Se algum seam mudar, atualizar a especificação e os tickets antes de escrever
o teste correspondente.

## Regras TDD

- Um comportamento público por ciclo.
- Primeiro executar o teste e observar a falha pelo motivo esperado.
- Implementar o mínimo para o teste passar.
- Executar o teste focal, depois a suíte da área e por fim o gate regressivo.
- Refatorar somente com todos os testes verdes.
- Não testar chamadas privadas, formato interno de tabelas ou sequência de
  helpers quando o mesmo resultado pode ser observado pelo seam público.
- Não compartilhar diretórios de build entre processos concorrentes.

## Fronteiras que podem ser substituídas

Mocks/fakes são permitidos somente para:

- relógio e geração de IDs;
- filesystem temporário e falhas injetadas de I/O;
- subprocessos e sinais;
- modelo/enriquecedor externo;
- servidor MCP externo;
- scheduler ou launcher;
- identidade/autorização fornecida por um adaptador externo.

O domínio, a máquina de estados, o journal, os contratos e a fachada pública
devem ser exercitados de verdade.

## Sequência de ciclos

Cada bullet listado em `RED` abaixo é um microciclo independente. O próximo só
começa depois de o anterior ter: (a) um teste público falhando pelo motivo
esperado; (b) o menor GREEN; (c) o comando e a saída preservados; (d) a suíte
da área verde; e (e) uma demonstração pelo mesmo seam. Os ciclos agrupam um
marco de produto, não autorizam escrever todos os testes do marco de uma vez.

Seams preexistentes a caracterizar antes de criar a fachada: `import docops`,
CLI pública, envelopes/artefatos JSON e processo MCP real. Para cada ticket,
registrar explicitamente o seam, o primeiro teste, o comando focal, a evidência
observável e o caminho de rollback. UI não se aplica a este produto.

### Ciclo 1 — baseline e compatibilidade

RED:

- snapshot verificável dos dois candidatos;
- ausência de contrato canônico ou migração incompatível falha fechada;
- comandos canônico e legado ainda divergem.

GREEN:

- definir identidade, envelopes, estados e matriz de compatibilidade;
- fazer comando canônico e alias emitirem resultado equivalente.

REFACTOR:

- remover duplicação do roteamento sem remover aliases.

Gate: contrato, CLI e caracterização dos comportamentos preservados.

### Ciclo 2 — agent-first de checkout a wheel

RED:

- wheel instalada não localiza a skill;
- bootstrap duplica ou sobrescreve instruções;
- harness não declara operador e geração.

GREEN:

- descoberta no checkout e na instalação;
- bootstrap idempotente;
- harness e router coerentes.

REFACTOR:

- centralizar descoberta e mensagens sem acoplar ao harness específico.

Gate: clean install offline e smoke de agente.

### Ciclo 3 — reader read-only real

RED:

- reader consegue invocar mutação;
- processo faz bootstrap, watcher ou reindex;
- geração muda durante a sessão sem falha explícita;
- documento revogado ainda aparece.

GREEN:

- bloquear mutações no servidor;
- separar reader de manutenção;
- pinning e filtro de revogação.

REFACTOR:

- unificar a política entre harness, launcher e servidor.

Gate: testes de processo real com permissões negativas.

### Ciclo 4 — fonte, evento e worker

RED:

- fonte não registrada é reconciliada;
- fonte retirada é reativada implicitamente;
- evento duplicado gera dois efeitos;
- lease expirado ou crash duplica publicação.

GREEN:

- política obrigatória;
- reautorização explícita;
- deduplicação, debounce, lease, retry e receipt.

REFACTOR:

- separar emissão, claim, execução e reconhecimento.

Gate: falhas injetadas e retomada.

### Ciclo 5 — candidata, avaliação e publicação

RED:

- candidata muda após avaliação;
- aprovação sem avaliação é aceita;
- aprovador não autenticado é aceito;
- base muda antes da promoção;
- dependência revogada é publicada.

GREEN:

- hashes imutáveis;
- avaliação obrigatória e atual;
- autoridade verificável;
- revalidação sob lease;
- bloqueio de revogação.

REFACTOR:

- concentrar os gates em uma política pública reutilizada por aprovação e
  publicação.

Gate: publicação e rollback com crash matrix.

### Ciclo 6 — leitores, snapshots e rollback

RED:

- sessão vê duas gerações;
- snapshot incompatível é reutilizado;
- rollback restaura release revogada;
- erro terminal do RAG é confundido com sucesso.

GREEN:

- release e snapshot pinados;
- comparação completa de compatibilidade;
- rollback validado;
- estados RAG fechados e explícitos.

REFACTOR:

- compartilhar identidade de geração e snapshot.

Gate: backend RAG real e fixtures sintéticas.

### Ciclo 7 — aprendizado e feedback

RED:

- conversa sem opt-in cria proposta;
- consentimento expirado continua válido;
- evidência auto-declarada é aceita;
- replay de feedback abre investigação;
- conteúdo privado aparece em logs.

GREEN:

- consentimento escopado;
- quarentena e evidência verificável;
- anti-replay, rate limit e origem autenticada;
- redação e minimização.

REFACTOR:

- usar uma linguagem comum de provenance, autoridade e consentimento.

Gate: testes de abuso, privacidade e revogação.

### Ciclo 8 — contratos, documentação e release

RED:

- cópias de schema divergem;
- README, status e CLI descrevem estados diferentes;
- wheel ou clone limpo perde artefatos;
- Windows e POSIX diferem em comportamento público.

GREEN:

- fonte canônica e verificação mecânica;
- documentação gerada/auditada;
- matriz de instalação e plataforma.

REFACTOR:

- reduzir checks redundantes sem reduzir cobertura.

Gate: pipeline completo sequencial.

## Matriz mínima de falhas

| Fluxo | Antes do efeito | Depois do efeito | Resultado esperado |
|---|---|---|---|
| Registro de evento | falha de escrita | receipt ausente | retomada sem duplicação |
| Preparação | candidata parcial | candidata completa sem estado | limpeza ou reconciliação |
| Avaliação | métricas parciais | receipt persistido | estado determinístico |
| Aprovação | autoridade indisponível | aprovação persistida | nunca publicar sem gate válido |
| Publicação | antes do rename | depois do rename | uma única geração ativa válida |
| Revogação | antes de invalidar readers | depois de invalidar | nenhum reader afetado continua |
| RAG | reindex em curso | erro terminal | nunca marcar sucesso parcial |
| Rollback | release ausente | pacote restaurado | journal consistente |

## Gate regressivo por ticket

1. teste focal RED/GREEN;
2. suíte do domínio alterado;
3. validação dos contratos;
4. lint e formatação;
5. `git diff --check`;
6. quando aplicável: subprocesso, wheel, docs e RAG;
7. ao final de um marco: suíte completa sequencial em clone limpo.

## Gate final para promoção

- todos os tickets aceitos;
- zero conflito contratual conhecido;
- zero teste focal ou regressivo falhando;
- wheel e bootstrap funcionais;
- read-only comprovado no processo real;
- revogação ponta a ponta;
- crash matrix verde;
- backend RAG real com erros terminais cobertos;
- Windows e POSIX verdes;
- documentação sem drift;
- relatório humano aprovando a promoção.
