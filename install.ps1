# install.ps1 -- UQE v3.2 Windows PowerShell installer (parity with install.sh)
# =============================================================================
# Installs the UQE router core + support files into an agent environment on
# Windows without Git Bash/WSL. Same contracts as install.sh:
#   - idempotent marker-block upsert for CLAUDE.md / AGENTS.md / GEMINI.md
#   - post-write verification (file exists AND contains the Prime Directive)
#   - uninstall removes only UQE-managed content; user content is byte-preserved
#   - SHA-256 checksums written to .uqe\SHA256SUMS (always on in this port)
#
# Usage:
#   .\install.ps1                          # auto-detect target in current dir
#   .\install.ps1 -Target claude           # force a target
#   .\install.ps1 -Dest C:\proj -DryRun
#   .\install.ps1 -Uninstall -Target claude
# Targets: auto | cursor | claude | codex | gemini | windsurf | generic | manual
# Activation policy: cursor rule defaults to alwaysApply:false. Opt in with
#   -AlwaysApply or $env:UQE_ALWAYS_APPLY='true'.
# If blocked by execution policy:  powershell -ExecutionPolicy Bypass -File .\install.ps1
# =============================================================================
[CmdletBinding()]
param(
    [string]$Target = 'auto',
    [string]$Dest = '',
    [switch]$DryRun,
    [switch]$Uninstall,
    [switch]$Verbose2,
    [switch]$AlwaysApply
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$PrimeDirective = 'Assume nothing. Verify everything. Use the cheapest sufficient evidence. Do not ship blind. Do not fabricate. Do not over-process trivial work.'
$MarkerBegin = '<!-- BEGIN UQE -->'
$MarkerEnd   = '<!-- END UQE -->'

function Log($m)  { Write-Host "[uqe] $m" }
function Dbg($m)  { if ($Verbose2) { Write-Host "[uqe:debug] $m" } }
function Die($m)  { Write-Host "[uqe][ERROR] $m" -ForegroundColor Red; exit 1 }

$ScriptDir = $null
if ($MyInvocation -and $MyInvocation.MyCommand -and $MyInvocation.MyCommand.Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not $ScriptDir) {
    $ScriptDir = (Get-Location).Path
}

$SrcSkill     = Join-Path $ScriptDir 'SKILL.md'
$SrcModules   = Join-Path $ScriptDir 'modules'
$SrcTemplates = Join-Path $ScriptDir 'templates'
$SrcRefs      = Join-Path $ScriptDir 'references'
$SrcScripts   = Join-Path $ScriptDir 'scripts'
$SrcSchema    = Join-Path $ScriptDir 'evidence.schema.json'

$TempSrcDir = $null
if (-not (Test-Path $SrcSkill)) {
    Dbg "SKILL.md not found in $ScriptDir; attempting remote bootstrap from GitHub..."
    $TempSrcDir = Join-Path ([System.IO.Path]::GetTempPath()) ("uqe-install-" + [System.Guid]::NewGuid().ToString("N"))
    try {
        New-Item -ItemType Directory -Force -Path $TempSrcDir | Out-Null
        $zipFile = Join-Path $TempSrcDir "uqe-main.zip"
        Log "Downloading UQE source archive from GitHub..."
        Invoke-RestMethod -Uri "https://github.com/dollan9/uqe/archive/refs/heads/main.zip" -OutFile $zipFile
        Expand-Archive -Path $zipFile -DestinationPath $TempSrcDir -Force
        $extracted = Get-ChildItem -Directory -Path $TempSrcDir | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') } | Select-Object -First 1
        if ($extracted) {
            $ScriptDir    = $extracted.FullName
            $SrcSkill     = Join-Path $ScriptDir 'SKILL.md'
            $SrcModules   = Join-Path $ScriptDir 'modules'
            $SrcTemplates = Join-Path $ScriptDir 'templates'
            $SrcRefs      = Join-Path $ScriptDir 'references'
            $SrcScripts   = Join-Path $ScriptDir 'scripts'
            $SrcSchema    = Join-Path $ScriptDir 'evidence.schema.json'
            Dbg "Resolved remote source: $ScriptDir"
        }
    } catch {
        Dbg "Remote archive download failed: $_"
    }
}

# --- Validate sources (fail before writing anything) --------------------------
foreach ($p in @($SrcSkill, $SrcModules, $SrcTemplates)) {
    if (-not (Test-Path $p)) { Die "Source missing: $p (run from a full repo checkout or check network connection)" }
}
if ((Get-Content -Raw $SrcSkill) -notlike "*$PrimeDirective*") {
    Die 'SKILL.md lacks the Prime Directive verbatim -- refusing to install a corrupt source.'
}

# --- Resolve destination & target ---------------------------------------------
if ($Dest) { $D = $Dest } elseif ($env:UQE_DEST) { $D = $env:UQE_DEST } else { $D = (Get-Location).Path }
Dbg "destination: $D"

function Detect-Target {
    if (Test-Path (Join-Path $D '.cursor'))   { return 'cursor' }
    if (Test-Path (Join-Path $D '.windsurf')) { return 'windsurf' }
    if (Test-Path (Join-Path $D 'CLAUDE.md')) { return 'claude' }
    if (Test-Path (Join-Path $D 'GEMINI.md')) { return 'gemini' }
    if (Test-Path (Join-Path $D 'AGENTS.md')) { return 'codex' }
    return 'generic'
}
if ($Target -in @('auto','')) { $Target = Detect-Target; Log "Auto-detected target: $Target" }
if ($Target -notin @('cursor','claude','codex','gemini','windsurf','generic','manual')) {
    Die "Invalid -Target '$Target'"
}

$apply = if ($AlwaysApply -or $env:UQE_ALWAYS_APPLY -eq 'true') { 'true' } else { 'false' }
$ShaLines = New-Object System.Collections.Generic.List[string]

function Record-Sha([string]$file) {
    if ($DryRun -or -not (Test-Path $file)) { return }
    $h = (Get-FileHash -Algorithm SHA256 $file).Hash.ToLower()
    $trimmedD = $D.TrimEnd('\','/')
    if ($file.StartsWith($trimmedD, [System.StringComparison]::OrdinalIgnoreCase) -and $file.Length -gt $trimmedD.Length) {
        $rel = $file.Substring($trimmedD.Length).TrimStart('\','/') -replace '\\','/'
    } else {
        $rel = (Split-Path -Leaf $file)
    }
    $ShaLines.Add("$h  $rel")
    Log "sha256: $h  $rel"
}

function Verify-Contains([string]$file) {
    if ($DryRun) { Dbg "dry-run: skipping verification of $file"; return }
    if (-not (Test-Path $file)) { Die "Verification failed: '$file' does not exist after install." }
    if ((Get-Content -Raw $file) -notlike "*$PrimeDirective*") {
        Die "Verification failed: '$file' exists but lacks the Prime Directive."
    }
    Log "verified: $file (exists, Prime Directive present)"
}

function Copy-SupportFiles {
    if ($DryRun) { Dbg 'dry-run: skipping support files'; return }
    $uqe = Join-Path $D '.uqe'
    foreach ($sub in 'modules','templates','references','scripts') {
        New-Item -ItemType Directory -Force -Path (Join-Path $uqe $sub) | Out-Null
    }
    $pairs = @(
        @{src=$SrcModules;   dst=(Join-Path $uqe 'modules');   filter='*.md'},
        @{src=$SrcTemplates; dst=(Join-Path $uqe 'templates'); filter='*.md'}
    )
    if (Test-Path $SrcRefs)    { $pairs += @{src=$SrcRefs;    dst=(Join-Path $uqe 'references'); filter='*.md'} }
    if (Test-Path $SrcScripts) { $pairs += @{src=$SrcScripts; dst=(Join-Path $uqe 'scripts');    filter='*'} }
    foreach ($p in $pairs) {
        Get-ChildItem -File $p.src -Filter $p.filter | ForEach-Object {
            $out = Join-Path $p.dst $_.Name
            if (-not $DryRun) { Copy-Item $_.FullName $out -Force } else { Dbg "dry-run copy $out" }
            Record-Sha $out
        }
    }
    if (Test-Path $SrcSchema) {
        $out = Join-Path $uqe 'evidence.schema.json'
        if (-not $DryRun) { Copy-Item $SrcSchema $out -Force }
        Record-Sha $out
    }
    $brain = Join-Path $uqe 'SKILL.md'
    if (-not $DryRun) { Copy-Item $SrcSkill $brain -Force }
    Record-Sha $brain
    foreach ($seed in 'preferences','lessons') {
        $t = Join-Path $uqe "$seed.md"
        if (-not (Test-Path $t) -and -not $DryRun) {
            Copy-Item (Join-Path $SrcTemplates "$seed-template.md") $t
        }
    }
}

function Upsert-MarkerBlock([string]$file) {
    if ($DryRun) { Log "dry-run: upsert marker block in $file"; Copy-SupportFiles; return }
    $core = Get-Content -Raw $SrcSkill
    if (Test-Path $file) {
        $raw = Get-Content -Raw $file
        $bIdx = $raw.IndexOf($MarkerBegin); $eIdx = $raw.IndexOf($MarkerEnd)
        if ($bIdx -ge 0 -and $eIdx -gt $bIdx) {
            $raw = $raw.Remove($bIdx, $eIdx + $MarkerEnd.Length - $bIdx)
        }
        $block = "`r`n`r`n$MarkerBegin`r`n<!-- Managed by UQE install.ps1. Do not edit inside these markers; edits are overwritten on update. Content outside the markers is never modified. -->`r`n`r`n$core`r`n$MarkerEnd`r`n"
        Set-Content -Path $file -Value ($raw.TrimEnd() + "`r`n" + $block) -NoNewline -Encoding utf8
    } else {
        $head = "# Project Instructions`r`n`r`n"
        $block = "$MarkerBegin`r`n<!-- Managed by UQE install.ps1. Do not edit inside these markers; edits are overwritten on update. Content outside the markers is never modified. -->`r`n`r`n$core`r`n$MarkerEnd`r`n"
        Set-Content -Path $file -Value ($head + $block) -NoNewline -Encoding utf8
    }
    Verify-Contains $file
    Record-Sha $file
    Copy-SupportFiles
}

function Strip-MarkerBlock([string]$file) {
    if (-not (Test-Path $file)) { Log "no $file; nothing to remove"; return }
    $raw = Get-Content -Raw $file
    $bIdx = $raw.IndexOf($MarkerBegin); $eIdx = $raw.IndexOf($MarkerEnd)
    if ($bIdx -lt 0 -or $eIdx -le $bIdx) { Log "$file has no UQE marker block; untouched"; return }
    if ($DryRun) { Log "dry-run: strip marker block from $file"; return }
    $cleaned = $raw.Remove($bIdx, $eIdx + $MarkerEnd.Length - $bIdx).TrimEnd() + "`r`n"
    Set-Content -Path $file -Value $cleaned -NoNewline -Encoding utf8
    Log "stripped UQE marker block from $file -- user content preserved."
}

function Uninstall-Support {
    $brain = Join-Path $D '.uqe\SKILL.md'
    if ((Test-Path $brain) -and ((Get-Content -Raw $brain) -like "*$PrimeDirective*")) {
        if (-not $DryRun) {
            foreach ($x in 'modules','templates','references','scripts','evidence.schema.json','SHA256SUMS','SKILL.md') {
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $D ".uqe\$x")
            }
        }
        Log 'removed UQE-managed runtime files under .uqe (preferences.md and lessons.md kept -- user data).'
    } else { Log 'no UQE-managed runtime copy found; user files untouched.' }
}

Log "mode: $(if ($Uninstall) {'UNINSTALL'} else {'INSTALL'}) | target: $Target | destination: $D | dry-run: $($DryRun.IsPresent)"

if ($Uninstall) {
    switch ($Target) {
        'cursor'   { $f = Join-Path $D '.cursor\rules\uqe.mdc'; if ((Test-Path $f) -and ((Get-Content -Raw $f) -like "*$PrimeDirective*")) { if (-not $DryRun) { Remove-Item $f }; Log "removed $f" } else { Log 'nothing to remove' }; Uninstall-Support }
        'claude'   { Strip-MarkerBlock (Join-Path $D 'CLAUDE.md'); Uninstall-Support }
        'codex'    { Strip-MarkerBlock (Join-Path $D 'AGENTS.md'); Uninstall-Support }
        'gemini'   { Strip-MarkerBlock (Join-Path $D 'GEMINI.md'); Uninstall-Support }
        'windsurf' { $f = Join-Path $D '.windsurf\rules\uqe.md'; if ((Test-Path $f) -and ((Get-Content -Raw $f) -like "*$PrimeDirective*")) { if (-not $DryRun) { Remove-Item $f }; Log "removed $f" } else { Log 'nothing to remove' }; Uninstall-Support }
        default    { Log 'generic/manual: remove wherever you manually placed UQE files; nothing was installed automatically.' }
    }
} else {
    switch ($Target) {
        'cursor' {
            $dir = Join-Path $D '.cursor\rules'; if (-not $DryRun) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
            $out = Join-Path $dir 'uqe.mdc'
            if ($DryRun) { Log "dry-run: write $out (alwaysApply: $apply)" }
            else {
                $fm = "---`r`ndescription: UQE v3.2 -- Universal Quality Engine router core (load when doing non-trivial work)`r`nglobs:`r`nalwaysApply: $apply`r`n---`r`n`r`n"
                Set-Content -Path $out -Value ($fm + (Get-Content -Raw $SrcSkill)) -NoNewline -Encoding utf8
            }
            Verify-Contains $out; Record-Sha $out; Copy-SupportFiles
        }
        'claude'   { Upsert-MarkerBlock (Join-Path $D 'CLAUDE.md') }
        'codex'    { Upsert-MarkerBlock (Join-Path $D 'AGENTS.md') }
        'gemini'   { Upsert-MarkerBlock (Join-Path $D 'GEMINI.md') }
        'windsurf' {
            $dir = Join-Path $D '.windsurf\rules'; if (-not $DryRun) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
            $out = Join-Path $dir 'uqe.md'
            if (-not $DryRun) { Copy-Item $SrcSkill $out -Force }
            Verify-Contains $out; Record-Sha $out; Copy-SupportFiles
        }
        default {
            Log 'generic/manual target: wiring steps --'
            Log '  1. copy SKILL.md to your agent rules file; copy modules/, templates/, references/, scripts/, evidence.schema.json to <workspace>\.uqe\'
            Log "  2. verify activation: Select-String -SimpleMatch '$PrimeDirective' <rules-file>"
            Log '  3. run verification scripts in .uqe\scripts\ and validate evidence JSON against the schema.'
        }
    }
    if ($ShaLines.Count -gt 0 -and -not $DryRun) {
        $sums = Join-Path $D '.uqe\SHA256SUMS'
        New-Item -ItemType Directory -Force -Path (Split-Path $sums) | Out-Null
        Set-Content -Path $sums -Value $ShaLines -Encoding utf8
        Log "wrote $sums ($($ShaLines.Count) entries)"
    }
}

if ($TempSrcDir -and (Test-Path $TempSrcDir)) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $TempSrcDir
}

if ($DryRun) { Log 'DRY RUN complete. No changes made; no verification performed.' }
elseif ($Uninstall) { Log 'UNINSTALL complete.' }
else { Log 'INSTALL complete and VERIFIED by post-write checks listed above.' }
exit 0
