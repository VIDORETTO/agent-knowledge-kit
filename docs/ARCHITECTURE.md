# Arquitetura e fronteiras

## O que este projeto faz

```text
entrada (nome | URL | repo | pasta)
             |
     resolução segura
             |
   aquisição + normalização ----> manifest.json + checkpoints
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

- `manifest.json`: versão do contrato, identidade da fonte, candidatos,
  licença/proveniência, entradas aceitas/ignoradas/erro, métricas e checkpoints;
- `skill/`: `SKILL.md`, capítulos, glossário, padrões e cheatsheet;
- `router/`: regra para separar orientação conceitual de fatos literais RAG;
- `rag/documents/`, `rag/sources.json` e `rag/index.json`: corpus normalizado e
  estado pronto para o backend;
- `harness.json`: registro MCP stdio com caminhos relativos para o host externo.

O pacote só é considerado consultável quando
`python -m docops validate <pacote>` passa. `corpus-ready` significa que os
documentos e metadados estão prontos; `indexed` significa que `--index-rag`
executou o servidor real e registrou suas estatísticas.

## Estado e recuperação

`StateStore` usa `canonical + version` como chave lógica e inclui o hash no
identity. Escritas de JSON e texto são temporárias, sincronizadas e trocadas
com `os.replace`. `CheckpointStore` grava as fases resolution, acquisition e
artifacts; repetir a execução reconcilia add/update/remove e retoma após uma
falha sem duplicar fontes.

O fluxo mutante pressupõe uma execução por pacote por vez. As trocas atômicas
protegem arquivos contra interrupções, mas não substituem um lock distribuído
ou uma fila para dois processos concorrentes; em uso automatizado, serialize
execuções que apontem para o mesmo diretório de saída.

O `knowledge-rag` é iniciado apenas quando `--index-rag` ou um script de
integração é solicitado. O cliente encerra somente o processo filho que abriu e
não usa comandos globais para matar processos Python.

## Limites deliberados

Browser rendering, OCR, autenticação de fonte e confirmação de licença não são
fingidos como concluídos. O manifesto retorna um código de ação (`browser`,
`ocr_required`, `authentication_required` ou `license_required`) para o
harness decidir como prosseguir.
