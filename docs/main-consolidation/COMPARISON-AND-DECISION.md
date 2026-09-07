# Comparação e decisão para consolidação da main

## Escopo observado

- `HEAD` e `origin/main`:
  `15cfaa6a919eaac7fca315241a4b396b1902f8f8`.
- `origin/feat/continuous-knowledge`:
  `2eaa9c24c9f809db0e0ce8b73206500ba1ed73e6`.
- A branch remota está 10 commits à frente e 0 atrás de `origin/main`.
- O histórico limpo permite fast-forward e não contém conflito Git histórico.
- No snapshot anterior à criação destes documentos, o working tree local tinha
  49 arquivos rastreados modificados e 72 não rastreados, totalizando 121
  caminhos. Depois dos 18 documentos deste pacote, são 90 não rastreados e 139
  caminhos locais; a sobreposição funcional abaixo não mudou.
- A branch remota altera 88 caminhos; 41 deles também são alterados localmente.
- Uma simulação three-way isolada, usando `origin/main` como base, encontrou 33
  conflitos: 29 de conteúdo e 4 `add/add`.

O resultado importante é que não existe divergência histórica entre as
branches, mas existe divergência textual e arquitetural substancial entre a
branch remota e o trabalho local ainda não commitado.

## O que a branch remota faz melhor

A branch remota oferece a experiência operacional mais completa para agentes:

- skill própria `docops-agent`;
- descoberta da skill instalada;
- bootstrap idempotente das instruções do agente;
- command cards, runbooks e regras de interoperabilidade;
- geração e operador declarados no harness;
- router com precedência operacional, abstention, autoridade, citações e
  pinning de geração;
- empacotamento da skill na wheel e verificação em instalação limpa;
- checagem automatizada da documentação;
- enforcement real de MCP read-only no servidor `knowledge-rag`.

Evidências principais:

- `2eaa9c2:skills/docops-agent/SKILL.md`
- `2eaa9c2:docops/agent_skill.py`
- `2eaa9c2:docops/__main__.py`
- `2eaa9c2:docops/harness.py`
- `2eaa9c2:docops/templates/router.md`
- `2eaa9c2:skills/vendor/knowledge-rag/mcp_server/server.py`
- `2eaa9c2:pyproject.toml`
- `2eaa9c2:scripts/verify_wheel.py`
- `2eaa9c2:scripts/check_documentation.py`

Em contrapartida, a implementação concentra grande parte do domínio em
`2eaa9c2:docops/lifecycle.py`, com aproximadamente 1.700 linhas e uma store
SQLite que acumula registro de fontes, eventos, jobs, candidatas, aprendizado,
feedback, publicação e rollback.

## O que o working tree local faz melhor

O working tree local apresenta maior cobertura funcional e separação de
responsabilidades:

- candidatas e avaliação;
- autorização e política de fontes;
- coordenação, jobs e retomada;
- triggers de impacto conceitual;
- sessões de leitura pinadas;
- snapshots e planos de reaproveitamento RAG;
- aprendizado por conversa;
- feedback de uso e investigações;
- histórico, rollback e contratos explícitos.

Evidências principais:

- `working-tree:docops/candidates.py`
- `working-tree:docops/authorization.py`
- `working-tree:docops/source_policy.py`
- `working-tree:docops/coordination.py`
- `working-tree:docops/triggers.py`
- `working-tree:docops/reader_sessions.py`
- `working-tree:docops/learning.py`
- `working-tree:docops/feedback.py`
- `working-tree:docops/revisions.py`
- `working-tree:docops/__main__.py`
- `working-tree:docs/continuous-knowledge/IMPLEMENTATION-STATUS.md`

O working tree também expõe uma superfície contract-first mais rica, com 24
novos schemas mantidos em duas árvores. Essa amplitude é valiosa, mas a
duplicação entre `schemas/` e `docops/schemas/` cria risco de drift.

## Matriz de divergências

| Área | Branch remota | Working tree local | Decisão |
|---|---|---|---|
| Lifecycle | Store SQLite central e monolítica | Módulos de domínio separados | Manter o núcleo modular e criar uma fachada única |
| CLI | Hierarquia `docops lifecycle ...` | Comandos planos | Hierarquia canônica com aliases planos temporários |
| Estado | Runtime SQLite/release central | Estado dividido por registros e diretórios | Definir layout versionado e migração explícita |
| Contratos | Menos schemas dedicados | Superfície extensa de schemas | Preservar contratos ricos com fonte canônica única |
| Agente | `docops-agent`, bootstrap e runbooks | Ausentes | Portar e empacotar |
| Harness | Operador, geração e ambiente read-only | Metadados de capacidade | Compor os dois e exigir enforcement |
| MCP | Barreiras reais contra mutação e filtro de revogação | Read-only sobretudo declarado | Restaurar a barreira no servidor |
| Router | Precedência, autoridade, abstention e pinning | Política mais simples | Adotar a política remota endurecida |
| Aprovação | Fluxo mais leve | Hashes, papéis e evidências mais ricos | Manter o gate local, reforçando autenticidade |
| RAG incremental | T15 declarado parcial | Snapshot/reuse plan implementado | Manter a capacidade local e provar backend real |
| Distribuição | Wheel e clean-install da skill | Sem operador empacotado equivalente | Portar os gates remotos |
| Documentação | Operação agent-first clara | Status funcional mais detalhado | Reescrever estado normativo após consolidação |

## Conflitos textuais relevantes

Os conflitos simulados incluem:

- API/CLI: `docops/__init__.py`, `docops/__main__.py`,
  `docops/operations.py`;
- domínio: `docops/coordination.py`, `docops/revisions.py`;
- avaliação e readiness: `docops/evaluator.py`, `docops/readiness.py`;
- harness e leitura: `docops/harness.py`, `docops/retrieval.py`;
- RAG: `docops/rag_sync.py`;
- geração e validação: `docops/normalizer.py`,
  `docops/package_validator.py`;
- documentação: contratos, status e tickets T01–T18;
- testes: `tests/test_coordination.py`.

Isso torna inadequado resolver a consolidação como merge linha a linha. Mesmo
arquivos sem conflito textual carregam conflitos de responsabilidade e estado.

## Riscos que bloqueiam promoção

### Segurança e governança

1. A identidade do aprovador e a autoridade da fonte ainda podem ser
   auto-declaradas; hashes garantem integridade, não autenticidade.
2. Evidência marcada como independente ainda precisa de verificação real de
   origem, licença, autoridade e suporte ao claim.
3. Consentimento para aprender com conversa precisa de escopo, titular,
   finalidade, expiração, revogação, retenção e eliminação.
4. Feedback precisa de anti-replay, autenticação da origem, rate limit e
   denominadores confiáveis.
5. Fonte retirada não pode ser reativada por uma atualização comum.
6. Revogação deve invalidar leitores e derivados, bloquear publicação e
   impedir rollback para conteúdo revogado.

Evidências locais:

- `working-tree:docops/schemas/approval.schema.json`
- `working-tree:docops/learning.py`
- `working-tree:docops/feedback.py`
- `working-tree:docops/source_policy.py`

### Consistência da branch remota

A análise da branch encontrou riscos adicionais que devem ser transformados
em testes antes de qualquer port:

- dependências de aprendizado revogadas podem não ser detectadas corretamente;
- revogação altera artefatos ativos fora do mesmo protocolo de publicação;
- aprovação não exige avaliação válida e atual;
- o estado terminal do RAG é interpretado de forma permissiva;
- reconciliação de fonte não aplica toda a política declarada;
- existe janela TOCTOU entre validação da base e aquisição do lease.

Evidências:

- `2eaa9c2:docops/lifecycle.py`
- `2eaa9c2:docops/rag_sync.py`
- `2eaa9c2:docs/continuous-knowledge/VALIDATION.md`
- `2eaa9c2:docs/continuous-knowledge/DECISIONS.md`

### Atomicidade operacional

SQLite, filesystem, índices e sessões não formam uma transação distribuída.
Receipts e journal tornam a recuperação possível, mas não a provam. A solução
precisa testar crashes antes e depois de cada efeito observável.

## Verificações executadas

### Branch remota em clone isolado

- Uma execução anterior no ambiente alinhado registrou `260 passed, 2 skipped`.
- A reauditoria atual passou 13 testes de lifecycle e 31 testes focados; a
  suíte completa parou em `tests/test_candidate_bundle.py` com
  `direct_resolution_mismatch`, classificado como incompatibilidade do
  interpretador atual com o lock. A branch precisa ser revalidada do zero no
  ambiente travado antes de promoção.
- Ruff: passou.
- contratos: passou, com 9 artefatos e nenhum finding.
- documentação: passou, com 84 arquivos Markdown verificados.
- `git diff --check`: passou.

### Working tree local

- Ruff: passou.
- contratos: passou, com 33 artefatos e nenhum finding.
- `git diff --check`: passou.
- A suíte completa não possui resultado válido nesta análise porque duas
  execuções inicialmente concorreram pelo mesmo diretório de build.
- Em repetição sequencial, o teste
  `test_candidate_falls_back_when_bootstrap_no_install_leaves_a_venv_without_pip`
  continuou falhando com
  `candidate supply-chain evidence failed independent verification`.

Esse teste é um blocker real do candidato local. Ele não foi corrigido porque
o escopo desta tarefa é exclusivamente documental.

## Decisão arquitetural

Não fazer fast-forward da branch remota como solução final. Não promover o
working tree local como está. Não fazer cherry-pick amplo nem merge mecânico.

A arquitetura-alvo deve ser:

1. núcleo modular local como modelo de domínio;
2. uma única fachada de lifecycle e uma única máquina de estados;
3. contratos canônicos e versionados;
4. CLI hierárquica como interface principal, com compatibilidade temporária
   para os comandos planos;
5. skill `docops-agent` como porta de entrada obrigatória para agentes;
6. harness com identidade de geração, operador e política MCP efetivamente
   aplicada;
7. leitores imutáveis, pinados e revogáveis;
8. aprendizado contínuo review-first, nunca auto-publicado;
9. publicação bloqueada por evidência, avaliação, autenticação, autorização,
   consentimento e revogação;
10. integração validada em clone limpo, wheel instalada e backend RAG real.

## Estratégia de consolidação

1. Preservar os dois candidatos e criar uma branch de integração isolada a
   partir de `origin/main`; usar os commits remotos como fontes seletivas, sem
   aplicar o patch local ou o lifecycle remoto integralmente.
2. Congelar contratos, máquina de estados, layout de runtime e compatibilidade.
3. Portar primeiro a camada agent-first e seus testes de distribuição.
4. Restaurar a barreira MCP read-only e revogação no servidor.
5. Integrar o núcleo modular por fatias verticais, evitando importar o
   lifecycle monolítico.
6. Reconciliar CLI, harness, router e schemas.
7. Provar aprendizado, feedback, revogação, readers e RAG com falhas reais.
8. Atualizar a documentação normativa apenas depois de os contratos
   estabilizarem.
9. Criar um candidato de integração, validar em ambientes limpos e só então
   abrir a promoção de `main`.

Os detalhes executáveis estão na [especificação](SPEC.md), no
[plano TDD](TDD.md) e nos [tickets](tickets/README.md).
