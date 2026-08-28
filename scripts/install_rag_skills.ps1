# Instala as skills comportamentais do knowledge-rag (vendor) em ~/.agents/skills/
# Uso: pwsh -File scripts/install_rag_skills.ps1 [-Force]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$vendor = Join-Path $PSScriptRoot "..\skills\vendor\knowledge-rag\skills"
$target = Join-Path $env:USERPROFILE ".agents\skills"

if (-not (Test-Path $vendor)) { throw "vendor não encontrado: $vendor — clone o repo com git clone --depth 1 https://github.com/lyonzin/knowledge-rag.git skills\vendor\knowledge-rag" }
if (-not (Test-Path $target)) { New-Item -ItemType Directory -Path $target -Force | Out-Null }

$installed = @()
Get-ChildItem $vendor -Directory | ForEach-Object {
    $group = $_.Name
    Get-ChildItem $_.FullName -Directory | ForEach-Object {
        $skillName = $_.Name
        $dst = Join-Path $target $skillName
        if ((Test-Path $dst) -and -not $Force) {
            Write-Host "Pulado (já existe, use -Force para sobrescrever): $skillName"
        } else {
            if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
            Copy-Item $_.FullName $dst -Recurse -Force
            $installed += "$dst (de $group)"
        }
    }
}

if ($installed.Count -eq 0) {
    Write-Host "Nada a instalar."
} else {
    Write-Host "Instaladas $($installed.Count) skill(s):"
    $installed | ForEach-Object { Write-Host "  - $_" }
}
