# Interface Python estável

O contrato suportado importa da raiz do pacote:

```python
import docops

request = docops.OperationRequest(
    "documents/fixtures/acme-docs",
    docops.OperationOptions(output_dir="artifacts/acme", slug="acme", license="MIT"),
)
operation = docops.plan(request)
result = docops.preview(operation)       # ou docops.apply(operation)
inspection = docops.inspect(request.options.output_dir)
```

`OperationOptions`, `OperationRequest`, `OperationPlan` e
`OperationResult` são os tipos novos e versionados. Options, request e plan
capturam snapshots defensivos; `plan()` não escreve no destino. O resultado
terminal é profundamente imutável, serializável com `result.json()` e os
envelopes carregam `schema_version`; `result.to_dict()` devolve uma cópia
mutável para integrações que precisam transformar a saída.

`docops.cleanup(path, retention_seconds=..., keep_attempts=...)` remove apenas
resíduos expirados e não retomáveis, sob o mesmo lease de writer. A função
retorna `writer_busy` sem tocar no pacote se outro processo estiver escrevendo.

`docops.PipelineOptions` e `docops.pipeline.run_pipeline` são aliases de
compatibilidade 1.0. O adapter legado delega integralmente para `plan`,
`preview` e `apply`; callers novos não devem importar helpers privados nem o
módulo `docops.pipeline`.
