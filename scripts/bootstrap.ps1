param(
    [switch]$Rag,
    [switch]$Dev,
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BootstrapArgs = @("$Root\scripts\bootstrap.py", "--root", $Root)
if ($Rag) { $BootstrapArgs += "--rag" }
if ($Dev) { $BootstrapArgs += "--dev" }
if ($NoInstall) { $BootstrapArgs += "--no-install" }
& python @BootstrapArgs
exit $LASTEXITCODE
