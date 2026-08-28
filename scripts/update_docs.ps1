# Atualização coordenada do pacote de documentação.
#
# Com -Sources, o protocolo público docops faz aquisição, skill, router,
# manifesto, validação e (opcionalmente) indexação em um único fluxo. Sem
# -Sources, preservamos os comandos legados de manutenção do corpus local.
param(
    [string]$Sources = "",
    [string]$Slug = "fastapi",
    [string]$Output = "",
    [string]$License = "",
    [switch]$IndexRag,
    [switch]$AllowPrivateNetwork
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ($Sources) {
    if (-not $Output) { $Output = Join-Path $Root (Join-Path "artifacts" $Slug) }
    $Arguments = @("-m", "docops", "run", $Sources, "--output", $Output, "--slug", $Slug)
    if ($License) { $Arguments += @("--license", $License) }
    if ($IndexRag) { $Arguments += "--index-rag" }
    if ($AllowPrivateNetwork) { $Arguments += "--allow-private-network" }
    Write-Host "== docops :: aquisição + skill + router + RAG =="
    & python @Arguments
    exit $LASTEXITCODE
}

Write-Host "== legacy corpus :: RAG plan =="
& python (Join-Path $Root "scripts\update_rag.py") plan
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n== legacy corpus :: RAG apply (foreground, checkpointed) =="
& python (Join-Path $Root "scripts\update_rag.py") apply
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n== legacy corpus :: RAG status =="
& python (Join-Path $Root "scripts\update_rag.py") status
exit $LASTEXITCODE
