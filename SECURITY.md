# Segurança

## Como reportar

Use o fluxo privado de vulnerabilidade do GitHub na aba **Security** ou em
[Report a vulnerability](https://github.com/VIDORETTO/agent-knowledge-kit/security/advisories/new).
Não abra uma issue pública para uma falha ainda explorável. Inclua a versão ou
commit afetado, sistema operacional, comando reproduzível, impacto e um fixture
mínimo sanitizado. Nunca anexe corpus privado, índices, tokens, credenciais ou
logs que os contenham.

No repositório público, secret scanning, push protection e Dependabot security
updates estão habilitados. Se o formulário privado não estiver disponível para
o relator, use um canal privado do mantenedor e não divulgue o detalhe em uma
issue pública.

O mantenedor pretende acusar recebimento em até 3 dias úteis, concluir a
triagem inicial em até 7 dias úteis e combinar a correção com o relator. Esses
tempos são metas operacionais, não uma garantia de disponibilidade.

## Escopo e versões

O escopo inclui o código Python em `docops/`, scripts, workflows, configuração
de release, templates, schemas e a cópia vendorizada de `knowledge-rag` usada
pelo pacote. A linha suportada nesta publicação é `1.0.x`, com `1.0.0` como
versão atual. O corpus FastAPI, índices, caches, ambientes virtuais e qualquer
arquivo em `config/network.yaml` são dados locais e não fazem parte do release.

Ficam fora do escopo falhas que exigem controle prévio do checkout, acesso ao
sistema de arquivos do operador ou um modelo/LLM escolhido pelo usuário, salvo
quando o impacto atravessar uma fronteira controlada pelo produto.

## Modelo de ameaça e controles

| Fronteira | Controle aplicado | Limitação conhecida |
|---|---|---|
| URL e crawler | bloqueio de credenciais, loopback, metadata cloud e redes privadas; revalidação de redirects; conexão ao IP validado; limites de páginas, payload, timeout e retries | não é um sandbox para sites hostis nem um navegador JavaScript |
| Repositório Git | somente HTTPS remoto; DNS/política antes do clone e `http.curloptResolve` para fixar os IPs aprovados; redirects HTTP desativados; sem submódulos, protocolo `file`, prompt interativo ou tags desnecessárias; limite de tamanho pós-clone | não há quota de bytes garantida antes de o servidor iniciar a transferência |
| Documentos adquiridos | normalização limitada por formato/tamanho; conteúdo é dado não confiável e não é executado; prompt injection é marcado | OCR, autenticação e browser são reportados como capacidades ausentes |
| MCP local | `stdio` é o padrão; HTTP/SSE é opt-in e exige bearer token, rate limit, métricas e logging JSON | quem muda o bind para uma rede deve aplicar firewall e TLS/proxy adequados |
| Autenticação HTTP | ausência de token recusa o processo antes de abrir a porta; token correto passa e token incorreto falha; o health check é apenas uma sonda local | o projeto não gerencia rotação, cofre de segredos ou identidade multiusuário |
| ChromaDB | uso local via `PersistentClient`; o caminho do produto não usa `HttpClient` nem `trust_remote_code`; transporte padrão não expõe a base | há quatro CVEs sem correção conhecida no snapshot auditado; ver a seção abaixo |
| Modelos RAG | modelos declarados pelo perfil, cache em diretório ignorado e carregamento local via FastEmbed; não há execução de código remoto | os artefatos externos não têm hash de conteúdo versionado pelo produto |
| Publicação | `audit_release`, `config-audit`, `pip-audit`, fixtures sintéticas e clone limpo bloqueiam dados proibidos e segredos conhecidos | revisão humana de licença e dos artefatos derivados continua necessária |

## Risco residual do ChromaDB

Na auditoria de 2026-08-29, `chromadb==1.5.9` apresentou os seguintes avisos
sem versão de correção publicada no resultado: [CVE-2026-45829](https://nvd.nist.gov/vuln/detail/CVE-2026-45829),
[CVE-2026-45830](https://nvd.nist.gov/vuln/detail/CVE-2026-45830),
[CVE-2026-45831](https://nvd.nist.gov/vuln/detail/CVE-2026-45831) e
[CVE-2026-45833](https://nvd.nist.gov/vuln/detail/CVE-2026-45833).

O risco foi mantido explicitamente, não ocultado: o produto usa somente o
cliente persistente local, inicia por `stdio` e não expõe a API HTTP do Chroma.
O gate permite exatamente esses quatro IDs para `chromadb`; qualquer outro
achado, inclusive um futuro advisory do Chroma, reprova a auditoria. Não
publique o servidor, a porta do Chroma ou o diretório `data/` para a rede até
que o upstream forneça correções e a política seja reavaliada.

## Gates antes de publicar

```text
python -m docops config-audit config/network.yaml --json
python scripts/audit_release.py --tracked-only --json
python scripts/audit_dependencies.py --requirements requirements.lock --local --strict
python scripts/verify_clean_clone.py
```

O perfil de rede de exemplo contém apenas um placeholder. Copie-o para um
arquivo privado, gere um token aleatório forte, valide-o e mantenha o arquivo
fora do Git. Trocar o perfil de embedding exige um rebuild completo do índice;
revisar a configuração e o cache do modelo é parte do procedimento de mudança.

## Limitações e resposta a incidentes

Esta release não fixa hashes de todas as dependências transitivas por sistema
operacional, não fixa hashes dos modelos baixados e não consegue impor um limite
de transferência antes do servidor Git remoto aceitar o clone. O CI e o
`scripts/audit_dependencies.py` devem ser executados em cada release; o risco
residual deve permanecer descrito até existir uma mitigação efetiva.

Ao confirmar uma falha, preserve evidências sem redistribuir dados protegidos,
revogue tokens afetados, bloqueie o vetor no código/configuração, publique uma
correção ou orientação de mitigação e só então divulgue detalhes suficientes
para usuários atualizarem com segurança.
