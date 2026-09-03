# Arquitetura e fronteiras

## O que este projeto faz

```text
entrada (nome | URL | repo | pasta)
             |
     resolução segura
             |
   plan (sem efeitos) ----> plano imutável + diff + políticas
             |
   apply --> staging + validação --> promoção transacional
             |
       skill + router + rag/documents
             |
       knowledge-rag MCP (opcional, externo ao pacote)
             |
 harness externo decide como carregar contexto e qual modelo usar
```

O comando `docops` é determinístico nas partes sob seu controle. Ele não
interpreta a documentação como instruções executáveis e não chama modelos.
`book-to-skill` continua sendo uma Agent Skill executada pelo harness: pode
enriquecer o scaffold estrutural produzido pelo operador, mas o caminho base
não depende de uma sessão de chat nem de copiar e colar.

Na web, o `WebAcquirer` consulta `robots.txt` (incluindo `Sitemap:`), respeita
regras `Disallow`, tenta sitemaps antes da navegação interna e aplica limites de
host, páginas, profundidade, payload, timeout e redirects.

## Artefato público

Cada execução bem-sucedida cria:

- config.yaml: configuração stdio relativa ao pacote; é criada no primeiro run
  e preservada quando já existe uma configuração customizada;

- `manifest.json`: versão do contrato, outcome terminal, identidade da fonte, candidatos,
  licença/proveniência, entradas aceitas/ignoradas/erro, métricas e checkpoints;
- `skill/`: `SKILL.md`, capítulos, glossário, padrões e cheatsheet;
- `router/`: regra para separar orientação conceitual de fatos literais RAG;
- `rag/documents/`, `rag/sources.json` e `rag/index.json`: corpus normalizado e
  estado pronto para o backend;
- `harness.json`: registro MCP stdio com caminhos relativos para o host externo.
- `.docops/`: state, plano, recibos de fase, tentativas falhas e evidências de
  readiness; esse diretório é operacional e não deve ser publicado com corpus.

O pacote só é considerado consultável quando
`python -m docops validate <pacote>` passa. `corpus-ready` significa que os
documentos e metadados estão prontos; `indexed` significa que `--index-rag`
executou o servidor real e registrou suas estatísticas.

## Estado e recuperação

`StateStore` usa `canonical + version` como chave lógica e inclui o hash no
identity. Escritas de JSON e texto são temporárias, sincronizadas e trocadas
com `os.replace`. `CheckpointStore` grava recibos com identidade do plano,
hash de entrada/saída, schema, duração e caminhos; repetir a execução só
reutiliza fases cujo recibo ainda coincide.

Cada pacote possui um lease local recuperável. Writers concorrentes falham ou
aguardam conforme `lease_policy`; o owner é redigido e nenhum processo global é
encerrado. A interface pública `docops.inspect()` espera a estabilização de um
writer vivo antes de devolver uma geração, preservando a geração ativa para
readers durante staging. A promoção troca diretórios no mesmo volume e restaura
o backup se a validação pós-promoção falhar; não é um lock distribuído. Readers
que acessam o filesystem diretamente podem observar uma janela de troca
específica da plataforma; o produto não promete atomicidade universal.

O `knowledge-rag` é iniciado apenas quando `--index-rag` ou um adapter MCP é
solicitado. O cliente encerra somente o processo filho que abriu e não usa
comandos globais para matar processos Python. O manifesto e a avaliação
registram a versão e a procedência (`reviewed-vendor` ou `installed-package`).

O avaliador mantém o scorer lexical como diagnóstico nomeado. O adapter em
memória serve ao TDD; o gate de release usa `--adapter mcp`, que exige um
pacote realmente indexado e registra perfil, corpus, top-k e resultados.

## Limites deliberados

Browser rendering, OCR, autenticação de fonte e confirmação de licença não são
fingidos como concluídos. O manifesto retorna um código de ação (`browser`,
`ocr_required`, `authentication_required` ou `license_required`) para o
harness decidir como prosseguir.
