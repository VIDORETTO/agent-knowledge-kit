# Autoridade, conflitos e idiomas

O registro de fontes já aceita `scope`, `version_policy`, `language`, `rights`,
`privacy` e `authority`. Preencha esses campos antes de comparar documentos.
Uma origem mais nova não vence automaticamente uma origem mais autorizada.

## Ordem de prioridade

1. escopo aplicável ao projeto, produto ou versão;
2. fonte autorizada para aquele escopo;
3. versão/edição e validade temporal;
4. evidência direta e reproduzível;
5. qualidade de extração e localizador;
6. atualidade dentro do mesmo escopo.

Uma decisão interna aprovada governa a implementação local, mas não vira regra
universal. Documentação oficial governa contrato público quando o projeto não
registrou uma exceção. Livro, curso, artigo e transcrição ajudam a explicar
racional e alternativas; não substituem contrato atual sem revisão.

## Classes de fonte

| Fonte | Registrar | Uso seguro |
|---|---|---|
| Oficial/API | organização, URL, release, licença | contrato e fatos literais |
| Decisão interna | responsável, aprovação, escopo, data | política local |
| Livro/curso | autor, edição, ISBN/módulo, direitos | mental models e contexto |
| Artigo/paper | autor, publicação, versão, revisão | evidência contextual |
| YouTube/transcrição | URL/ID, autor, idioma, timestamps | somente texto transcrito com conversão registrada |
| PDF/OCR | arquivo, parser/OCR, confiança, página | quarentena quando a extração for incerta |
| Código | commit/tag, símbolo, licença | comportamento daquela revisão |

## Conflito

Nunca fundir duas afirmações incompatíveis em uma regra única. Retorne as duas
fontes, seus escopos/versões e o que falta decidir. Se uma fonte for revogada,
ela não volta a ser válida apenas porque uma release antiga a referenciava.

## Português e multilíngue

- preserve UTF-8, acentos, nomes próprios e identificadores exatamente;
- registre idioma e edição da fonte;
- não traduza nomes de API, flags, símbolos ou valores;
- avalie o perfil `multilingual` com corpus e Golden nativos antes de trocar o
  embedding;
- teste consultas em português, inglês e termos mistos quando o corpus for
  multilíngue;
- cite a seção/página/timestamp realmente preservado pelo normalizador;
- se o extrator não conservar página ou timestamp, declare essa limitação.
