# Plano de estabilização — agent-knowledge-kit

## Diagnóstico inicial

- [x] Confirmar repositório, branch, remoto e ponto de parada.
- [x] Ler o backlog de produto e os gates das Fases 0–6.
- [x] Executar baseline: 59 testes, Ruff, doctor, auditoria de release e clone limpo.
- [x] Comparar o contrato documentado com os entry points e os artefatos reais.

## Prioridade 1 — Corrigir agora

- [x] Tornar o bootstrap correto para todas as combinações de perfis, especialmente `--dev --rag` — requisito não duplicado e coberto por teste.
- [x] Tornar o pacote gerado autossuficiente: incluir `config.yaml` relativo e validar o hand-off completo.
- [x] Corrigir o empacotamento para incluir o template do router e manter uma única versão do projeto.
- [x] Garantir que update remova destinos antigos e que colisões de nomes não sobrescrevam documentos.
- [x] Fazer o avaliador exigir revisão por caso, schema válido e parâmetros dentro dos limites.
- [x] Fazer divergência entre skill e fonte invalidar o pacote estável.
- [x] Fechar vazamentos e escapes previsíveis: resolução CLI com URL sensível, symlinks fora da fonte e saída dentro da fonte.
- [x] Não aceitar formatos binários como texto ilegível; normalizar ou retornar dependência/capacidade explícita.

## Prioridade 2 — Prontidão de release

- [x] Expandir testes de contrato para os fluxos e regressões acima — 91 testes automatizados, com dois cenários de symlink pulados apenas por limitação deste host Windows.
- [x] Adicionar gate de build/instalação do wheel e smoke do pacote instalado — scripts/verify_wheel.py e job package no CI.
- [x] Melhorar CI com validação de artefato empacotado e comandos de release reproduzíveis.
- [x] Harmonizar versões, user-agent e client info com a versão declarada em 1.0.0.
- [x] Revisar documentação de uso, release e estado do roadmap contra o comportamento final.

## Prioridade 3 — Backlog técnico explicitado

- [x] Avaliar lock transitivo/hashado por plataforma em uma evolução posterior — dependências diretas estão fixadas; hashes multiplataforma ficam fora da 1.0.0 para não prometer um lock incorreto para wheels diferentes.
- [x] Avaliar lock de execução para impedir duas mutações concorrentes no mesmo pacote — a operação documentada é single-run; a limitação está registrada para evolução posterior e não bloqueia o fluxo retomável por checkpoints.
- [x] Preparar integração real do knowledge-rag — workflow integration.yml, smoke e reindexação concorrente estão prontos; a execução local depende do perfil/modelo opcional.
- [x] Preparar validação manual da matriz de harnesses externos — contrato relativo em harness.json, documentação e gate automatizado prontos; a sessão final depende dos hosts do mantenedor.

## Registro de execução

Este arquivo é o checklist operacional da sessão. Itens só serão marcados como
concluídos depois de teste alvo, suíte completa e auditoria de release.

## Revisão final

- Estado: concluído localmente como release 1.0.0 pronta para publicação.
- Evidências: 91 passed, 2 skipped por symlink indisponível no Windows; Ruff verde; wheel instalado em alvo isolado; clone limpo, auditoria e fluxo run → validate → evaluate verdes.
- Ações externas restantes: commit/tag/push e sessões manuais dos harnesses, que não são executadas automaticamente pelo operador.
