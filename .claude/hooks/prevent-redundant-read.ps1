$ErrorActionPreference = "Stop"

$stateDir = Join-Path $env:CLAUDE_PROJECT_DIR ".claude\hooks\state"
$stateFile = Join-Path $stateDir "read-history.jsonl"
New-Item -ItemType Directory -Force $stateDir | Out-Null
New-Item -ItemType File -Force $stateFile | Out-Null

$inputJson = [Console]::In.ReadToEnd() | ConvertFrom-Json
$toolName = $inputJson.tool_name

switch ($toolName) {
  "Read" {
    $target = $inputJson.tool_input.file_path
  }
  "Grep" {
    $pattern = $inputJson.tool_input.pattern
    $pathArg = $inputJson.tool_input.path
    $target = "grep::$pattern::$pathArg"
  }
  "Glob" {
    $pattern = $inputJson.tool_input.pattern
    $pathArg = $inputJson.tool_input.path
    $target = "glob::$pattern::$pathArg"
  }
  default {
    exit 0
  }
}

$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$windowSeconds = 45

$history = Get-Content $stateFile -ErrorAction SilentlyContinue
$lastHit = $null

foreach ($line in $history) {
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  $obj = $line | ConvertFrom-Json
  if ($obj.tool_name -eq $toolName -and $obj.target -eq $target) {
    $lastHit = [int64]$obj.ts
  }
}

if ($null -ne $lastHit) {
  $delta = $now - $lastHit
  if ($delta -lt $windowSeconds) {
    $out = @{
      hookSpecificOutput = @{
        hookEventName = "PreToolUse"
        permissionDecision = "deny"
        permissionDecisionReason = "Leitura redundante bloqueada: mesma consulta repetida em janela curta. Consolide o que ja leu ou use leituras independentes em paralelo."
      }
    } | ConvertTo-Json -Depth 10
    Write-Output $out
    exit 0
  }
}

@{
  tool_name = $toolName
  target = $target
  ts = $now
} | ConvertTo-Json -Compress | Add-Content $stateFile

exit 0