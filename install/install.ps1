<#
.SYNOPSIS
  Install Yiğit Investment Copilot for Claude Code, Codex / ChatGPT desktop and/or OpenCode (Windows).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install/install.ps1 -Claude -OpenCodeExtras
  powershell -ExecutionPolicy Bypass -File install/install.ps1 -Codex
  powershell -ExecutionPolicy Bypass -File install/install.ps1 -OpenCode

.NOTES
  -OpenCode        skill + agent + commands into ~/.config/opencode
  -OpenCodeExtras  only agent + commands (use when the skill is already in ~/.claude/skills or ~/.agents/skills)
  Existing installs are renamed to <name>.bak-<timestamp> before copying. Nothing is deleted.
#>
param(
  [switch]$Claude,
  [switch]$Codex,
  [switch]$OpenCode,
  [switch]$OpenCodeExtras
)
$ErrorActionPreference = "Stop"
$Name = "yigit-investment-copilot"
$Root = Split-Path -Parent $PSScriptRoot
$Src = Join-Path $Root "skill\$Name"
if (-not (Test-Path (Join-Path $Src "SKILL.md"))) { throw "Skill folder not found: $Src" }
if (-not ($Claude -or $Codex -or $OpenCode -or $OpenCodeExtras)) {
  Write-Host "Choose at least one target: -Claude -Codex -OpenCode -OpenCodeExtras"
  exit 1
}
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

function Install-Skill([string]$TargetRoot) {
  $Dst = Join-Path $TargetRoot $Name
  New-Item -ItemType Directory -Force $TargetRoot | Out-Null
  if (Test-Path $Dst) {
    Rename-Item -Path $Dst -NewName "$Name.bak-$Stamp"
    Write-Host "backup  -> $Dst.bak-$Stamp"
  }
  Copy-Item -Recurse $Src $Dst
  Write-Host "skill   -> $Dst"
}

if ($Claude) { Install-Skill (Join-Path $HOME ".claude\skills") }
if ($Codex) { Install-Skill (Join-Path $HOME ".agents\skills") }
if ($OpenCode) { Install-Skill (Join-Path $HOME ".config\opencode\skills") }
if ($OpenCode -or $OpenCodeExtras) {
  $Oc = Join-Path $HOME ".config\opencode"
  New-Item -ItemType Directory -Force (Join-Path $Oc "agents"), (Join-Path $Oc "commands") | Out-Null
  Copy-Item (Join-Path $Root "platforms\opencode\agents\*.md") (Join-Path $Oc "agents") -Force
  Copy-Item (Join-Path $Root "platforms\opencode\commands\*.md") (Join-Path $Oc "commands") -Force
  Write-Host "opencode agent + commands -> $Oc"
}
if ($OpenCode -and ($Claude -or $Codex)) {
  Write-Warning "OpenCode also reads ~/.claude/skills and ~/.agents/skills; the skill now exists twice. Prefer -OpenCodeExtras with Claude Code or Codex."
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Warning "Python 3.9+ was not found on PATH. The data scripts need it (standard library only)." }
Write-Host "Done. Restart the app(s) and ask, for example: 'Piyasa ne durumda?' or '3 ayda en iyi BIST adaylarını tara'."
