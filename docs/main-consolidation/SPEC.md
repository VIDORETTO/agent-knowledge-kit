# Especificação — consolidação estável do DOCOPS

## Problem Statement

O projeto possui dois candidatos incompatíveis para evolução do conhecimento.
A branch remota oferece um lifecycle integrado e uma experiência operacional
forte para agentes, enquanto o working tree local oferece uma implementação
mais modular e uma superfície de contratos mais completa. Um merge mecânico
criaria duas máquinas de estados, comandos concorrentes, layouts de runtime
incompatíveis e políticas divergentes de leitura, revogação e publicação.

Além da divergência técnica, “aprendizado contínuo” pode ser interpretado de
forma insegura. Conversas, feedback e novas fontes não são automaticamente
verdadeiros, autorizados ou adequados para publicação. O sistema precisa
aprender continuamente sem permitir que conteúdo não confiável, privado,
revogado ou não avaliado altere a skill ativa.

Por fim, o mecanismo pode estar tecnicamente disponível e ainda ser difícil de
usar. Um agente precisa descobrir as skills do próprio sistema, compreender
qual camada usar, operar o lifecycle corretamente e falhar de forma segura
quando faltarem evidência, autoridade ou uma geração consistente.

## Solution

Criar uma única arquitetura de lifecycle baseada no núcleo modular, exposta
por uma fachada pública estável e orientada por contratos. Incorporar a camada
agent-first da branch remota, incluindo descoberta, bootstrap,
interoperabilidade, command cards e distribuição.

Separar explicitamente três fluxos:

1. consulta conceitual, atendida pela skill de domínio;
2. consulta factual, atendida por um reader RAG read-only e pinado;
3. mudança persistente, atendida pelo lifecycle review-first.

O aprendizado contínuo deve começar por sinais. Fontes, conversas e feedback
geram observações, claims ou investigações. Somente uma candidata com
proveniência, avaliação atual, autoridade verificável, consentimento aplicável
e aprovação editorial pode ser publicada. Revogação deve bloquear novas
leituras, invalidar dependências e impedir promoção ou rollback indevidos.

A consolidação ocorrerá em uma branch isolada, por fatias verticais e com
compatibilidade expand-contract. A `main` só será promovida depois de clean
clone, wheel, documentação, Windows/POSIX, RAG real, recuperação de crash e
gates de segurança passarem.

## User Stories

1. Como agente recém-inicializado, quero localizar a skill operacional do
   DOCOPS por uma interface estável, para aprender como consultar e manter o
   sistema sem conhecer o layout do repositório.

2. Como agente em um projeto consumidor, quero instalar uma regra de bootstrap
   idempotente, para carregar a skill operacional sem sobrescrever instruções
   existentes.

3. Como agente respondendo uma pergunta conceitual, quero ser direcionado à
   skill de domínio, para usar modelos mentais curados em vez de tratar o RAG
   como autoridade conceitual irrestrita.

4. Como agente respondendo uma pergunta factual, quero consultar uma geração
   RAG pinada e read-only, para citar uma fonte exata sem observar mudanças no
   meio da resposta.

5. Como agente diante de uma pergunta ambígua ou de alto risco, quero combinar
   racional conceitual e confirmação factual, para declarar divergências e
   abster-me quando a evidência não for suficiente.

6. Como operador, quero registrar uma fonte com direitos, privacidade,
   autoridade, escopo e estado, para impedir ingestão implícita de material não
   autorizado.

7. Como operador, quero reconciliar mudanças de fonte de forma idempotente,
   para transformar alterações em revisões e eventos rastreáveis sem
   duplicação.

8. Como operador, quero que eventos sejam agregados, tenham debounce, lease,
   retry limitado e recuperação, para executar aprendizado contínuo sem
   depender de mutações frágeis.

9. Como editor, quero preparar uma candidata isolada da geração ativa, para
   revisar mudanças sem afetar leitores.

10. Como editor, quero que enriquecimento externo seja recebido como um
    artefato verificável e limitado, para usar modelos externos sem delegar a
    eles autoridade de publicação.

11. Como avaliador, quero comparar uma candidata contra Golden Set, fidelidade
    factual, qualidade conceitual, citações e regressões, para emitir uma
    decisão reproduzível com denominadores claros.

12. Como aprovador autorizado, quero aprovar hashes exatos de uma candidata e
    de sua avaliação, para que qualquer alteração posterior invalide a decisão.

13. Como publicador, quero uma promoção atômica no limite observável, com
    revalidação após o lease e journal de recuperação, para evitar publicar
    sobre uma base que mudou.

14. Como leitor, quero que cada sessão fixe release e snapshot, para receber
    respostas consistentes durante toda a sessão.

15. Como responsável por segurança, quero que o servidor MCP bloqueie
    capacidades de escrita para readers, para que a política não dependa apenas
    de instruções textuais.

16. Como responsável por segurança, quero revogar fontes e propostas de
    aprendizado ponta a ponta, para bloquear leitura, publicação, derivados e
    rollback que dependam de conteúdo retirado.

17. Como usuário, quero consentir explicitamente com o uso de um trecho de
    conversa, com escopo, finalidade e retenção definidos, para que a conversa
    não seja capturada como conhecimento por padrão.

18. Como revisor, quero que uma proposta de conversa permaneça em quarentena
    até possuir evidência independente e autoridade suficiente, para evitar
    auto-contaminação do sistema.

19. Como mantenedor, quero agregar feedback redigido e resistente a replay,
    para abrir investigações com sinais de uso reais sem armazenar queries ou
    conteúdo privado desnecessário.

20. Como operador, quero reaproveitar um índice somente quando corpus, perfil,
    modelo, configuração e artefatos forem compatíveis, para reduzir custo sem
    aceitar um snapshot inconsistente.

21. Como operador, quero rollback apenas para releases válidas e não revogadas,
    para recuperar o serviço sem reintroduzir conhecimento proibido.

22. Como integrador, quero uma CLI hierárquica e previsível, preservando aliases
    temporários, para migrar automações existentes sem ruptura imediata.

23. Como mantenedor, quero uma fonte canônica para cada contrato e geração
    mecânica das cópias distribuídas, para impedir drift entre schemas.

24. Como usuário de wheel, quero que a skill operacional, os schemas e os
    runbooks sejam instalados e descobertos, para obter a mesma experiência do
    checkout.

25. Como maintainer da `main`, quero gates verificáveis em clone limpo,
    Windows, POSIX e backend RAG, para publicar apenas uma versão reproduzível.

26. Como auditor, quero rastrear uma decisão por fonte, revisão, candidata,
    avaliação, aprovador, release e reader, para explicar por que um
    conhecimento foi aceito ou rejeitado.

## Implementation Decisions

1. Haverá uma única máquina de estados pública para fonte, revisão, sinal,
   candidata, avaliação, aprovação, publicação, revogação e leitura.
2. O domínio permanecerá modular; uma fachada de aplicação coordenará os
   módulos sem absorver suas responsabilidades.
3. A interface de comandos será hierárquica e orientada a verbos de domínio.
   Comandos legados permanecerão como aliases durante uma janela de migração.
4. O estado operacional terá layout versionado, fora da geração ativa, com
   migração explícita e recuperação idempotente.
5. Cada contrato terá uma única fonte normativa. Cópias para distribuição serão
   produzidas e verificadas mecanicamente.
6. O harness declarará identidade de geração, operador, transporte,
   capacidades e política de leitura.
7. Read-only será imposto no servidor e no processo, não apenas declarado no
   contrato.
8. Candidatas serão isoladas e imutáveis após avaliação ou aprovação; qualquer
   alteração produzirá nova identidade.
9. Publicação exigirá avaliação válida e atual, autoridade, consentimento,
   ausência de dependências revogadas e revalidação sob lease.
10. Conversas e feedback produzirão somente sinais ou propostas em quarentena.
11. Revogação será uma transição de domínio explícita e propagada para
    dependências, readers, publicação e rollback.
12. O sistema continuará neutro de modelo, provedor, scheduler e harness.
    Integrações externas produzirão requests e receipts verificáveis.
13. Logs e receipts usarão minimização e redação; conteúdo bruto privado não
    será requisito de observabilidade.
14. A skill operacional será um artefato de primeira classe, distribuído e
    testado junto com o pacote.
15. A integração será feita por port seletivo e reimplementação de
    comportamento, não por merge linha a linha do lifecycle concorrente.
16. Identidade e autoridade virão de um envelope assinado ou de um adaptador
    autenticado; nomes de ator autodeclarados não satisfazem aprovação.
17. Consentimento terá titular, escopo, finalidade, retenção, expiração e
    revogação verificáveis, e nunca será inferido do conteúdo da conversa.
18. Fonte retirada terá tombstone; retorno exigirá uma operação explícita de
    readmissão, nova decisão de autoridade e trilha de auditoria.
19. Feedback terá identidade de evento, autenticação de origem, anti-replay,
    rate limit e denominadores estáveis antes de abrir investigação.
20. Evidência independente será aceita somente quando procedência, autoridade,
    licença e suporte ao claim forem verificáveis; um booleano declarado pelo
    remetente não basta.
21. Revogação seguirá o mesmo protocolo transacional de publicação e invalidará
    proposta, candidata, release, snapshot e sessão dependentes.
22. O modo `direct` será compatibilidade explícita de bootstrap/desenvolvimento,
    desabilitado por padrão em operação contínua e incapaz de contornar os
    gates de publicação.

## Testing Decisions

1. Os testes observarão seams públicos: CLI, fachada de lifecycle, contratos,
   artefatos instalados, processos MCP e comportamento do pacote publicado.
2. Cada ticket começará por um teste RED de uma fatia vertical observável.
3. Não serão usados mocks de detalhes internos do domínio.
4. Serão usados fakes ou processos controlados apenas nas fronteiras externas:
   relógio, filesystem, subprocessos, modelo externo, scheduler e servidor MCP.
5. Todo gate de segurança terá pelo menos um teste de permissão e um teste de
   negação.
6. Serão injetadas falhas antes e depois de cada efeito entre banco,
   filesystem, índice e publicação.
7. Testes de revogação cobrirão admissão, publicação, sessão ativa, rollback e
   derivados.
8. Testes de supply chain cobrirão ambiente sem pip, wheel offline, hashes,
   lock, symlinks e conteúdo adulterado.
9. Testes RAG cobrirão sucesso, erro terminal, timeout, índice parcial, índice
   vazio, mudança de perfil e resposta malformada.
10. A compatibilidade dos comandos legados será testada contra os mesmos
    envelopes e códigos de saída da interface canônica.
11. A wheel será instalada em ambiente limpo e deverá localizar a skill,
    validar contratos e executar o smoke público.
12. O gate final será sequencial e isolado para evitar concorrência sobre
    diretórios de build.

## Out of Scope

- Implementar ou corrigir código nesta etapa documental.
- Fazer merge, rebase, cherry-pick, commit, push ou abrir pull request.
- Alterar o pacote ativo, corpus, índice RAG ou estado de produção.
- Escolher um provedor de modelo ou scheduler gerenciado.
- Construir uma fila distribuída ou operação multi-host nesta primeira
  consolidação.
- Publicar documentos ou corpus cuja licença não esteja confirmada.
- Manter indefinidamente duas CLIs ou duas máquinas de estados.

## Further Notes

- O teste local de fallback de supply chain está falhando e deve ser tratado
  antes de o working tree ser considerado candidato.
- A branch remota passa seus gates atuais, mas os riscos de revogação,
  avaliação e TOCTOU precisam de testes novos; “verde” não equivale a pronta
  para produção.
- No código local atual, readmissão de fonte, autenticação de aprovação,
  consentimento completo, independência de evidência, anti-replay de feedback
  e propagação transacional de revogação ainda são requisitos, não capacidades
  demonstradas.
- O lifecycle monolítico remoto é uma fonte de requisitos e comportamento, não
  o componente canônico a ser importado.
- A promessa correta ao usuário é aprendizado continuamente assistido e
  governado, não autoedição irrestrita.
- A promoção de `main` deve ocorrer somente depois de uma revisão humana do
  relatório final de gates e da documentação normativa.
