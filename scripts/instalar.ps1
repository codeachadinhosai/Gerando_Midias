[CmdletBinding()]
param(
    [switch]$SemDev,
    [switch]$SemChromium
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$VenvRoot = Join-Path $ProjectRoot '.venv'
$VenvPython = Join-Path $VenvRoot 'Scripts\python.exe'

function Confirm-NativeCommand {
    param([string]$Description)
    if ($LASTEXITCODE -ne 0) {
        throw "$Description falhou com codigo $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($Launcher) {
        & py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
        Confirm-NativeCommand 'Verificacao do Python 3.11 ou superior'
        & py -3 -m venv $VenvRoot
    }
    else {
        & python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
        Confirm-NativeCommand 'Verificacao do Python 3.11 ou superior'
        & python -m venv $VenvRoot
    }
    Confirm-NativeCommand 'Criacao do ambiente virtual'
}

$InstallTarget = if ($SemDev) { $ProjectRoot } else { "${ProjectRoot}[dev]" }
& $VenvPython -m pip install -e $InstallTarget
Confirm-NativeCommand 'Instalacao do projeto'

if (-not $SemChromium) {
    & $VenvPython -m playwright install chromium
    Confirm-NativeCommand 'Instalacao do Chromium do Playwright'
}

$EnvPath = Join-Path $ProjectRoot '.env'
if (-not (Test-Path -LiteralPath $EnvPath)) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot '.env.example') -Destination $EnvPath
}

$SpreadsheetPath = Join-Path $ProjectRoot 'entradas\controle_pipeline_flow.xlsx'
if (-not (Test-Path -LiteralPath $SpreadsheetPath)) {
    Copy-Item -LiteralPath (
        Join-Path $ProjectRoot 'exemplos\controle_pipeline_flow.modelo.xlsx'
    ) -Destination $SpreadsheetPath
}

$IdentityDirectory = Join-Path $ProjectRoot 'identidade'
$IdentityPath = Join-Path $IdentityDirectory 'identidade.txt'
if (-not (Test-Path -LiteralPath $IdentityPath)) {
    New-Item -ItemType Directory -Force -Path $IdentityDirectory | Out-Null
    Copy-Item -LiteralPath (
        Join-Path $ProjectRoot 'exemplos\identidade.example.txt'
    ) -Destination $IdentityPath
}

& $VenvPython (Join-Path $ProjectRoot 'scripts\diagnosticar_configuracao.py')
Confirm-NativeCommand 'Diagnostico da instalacao'

Write-Output ''
Write-Output 'Instalacao concluida.'
Write-Output 'Edite .env, informe GFLOW_PROJECT_ID e execute novamente:'
Write-Output '  .\.venv\Scripts\python.exe scripts\diagnosticar_configuracao.py'
