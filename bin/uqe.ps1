# =============================================================================
# uqe.ps1 — Universal Quality Engine CLI PowerShell Wrapper
# =============================================================================
[CmdletBinding()]
param()

$ScriptDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:PYTHONPATH = "$ScriptDir;$($env:PYTHONPATH)"

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m uqe.cli $args
    exit $LASTEXITCODE
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    & python3 -m uqe.cli $args
    exit $LASTEXITCODE
} else {
    Write-Host "[uqe][ERROR] Python 3.9+ is required but python was not found in PATH." -ForegroundColor Red
    exit 1
}
