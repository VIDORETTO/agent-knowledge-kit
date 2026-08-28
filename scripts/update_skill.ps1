# Atualiza uma skill sem exigir copiar/colar instruções no agente.
# O operador gera um scaffold estrutural determinístico; um harness que tenha
# book-to-skill pode enriquecer o diretório depois, sem o operador integrar IA.
param(
    [Parameter(Mandatory=$true)][string]$Sources,
    [string]$Slug = "documentation",
    [string]$Output = "",
    [string]$License = "",
    [string]$Mode = "text"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($Sources -notmatch '^(https?|file)://' -and -not (Test-Path $Sources)) { throw "Fonte não encontrada: $Sources" }
if (-not $Output) { $Output = Join-Path $Root (Join-Path "artifacts" $Slug) }

$Arguments = @("-m", "docops", "run", $Sources, "--output", $Output, "--slug", $Slug)
if ($License) { $Arguments += @("--license", $License) }
Write-Host "== docops :: gerar e validar skill/router/RAG =="
& python @Arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nPacote gerado em $Output. O caminho feliz não requer copiar/colar."
Write-Host "Para enriquecer mental models, invoque a Agent Skill book-to-skill do seu harness sobre a fonte; o sistema não escolhe um LLM."
Write-Host "Validação estrutural:"
& python -m docops validate $Output --json
exit $LASTEXITCODE
