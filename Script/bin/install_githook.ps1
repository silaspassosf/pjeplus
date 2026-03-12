#!/usr/bin/env pwsh
param()

$repoRoot = Split-Path -Parent $PSScriptRoot
$src = Join-Path $repoRoot '.githooks\pre-commit'
$destDir = Join-Path $repoRoot '.git\hooks'
$dest = Join-Path $destDir 'pre-commit'

if (-not (Test-Path $src)) { Write-Error "Source hook not found: $src"; exit 1 }
if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }

Copy-Item -Path $src -Destination $dest -Force
Write-Host "Installed pre-commit hook to $dest"
Write-Host "Make sure the hook is executable on Unix systems (chmod +x .git/hooks/pre-commit)."

exit 0
