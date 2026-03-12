<#
  bump-loader.ps1
  Usage: Run from repository root (Windows PowerShell)
    .\Script\bin\bump-loader.ps1

  This script increments the @version patch number in Script/hcalc.user.js
  and increments all numeric `v=` query params and refreshes `t=` timestamps
  to the current datetime (yyyyMMddHHmm), then writes the file back.
  It prints the new version and updated lines.
#>

$file = "Script/hcalc.user.js"
if (-not (Test-Path $file)) {
    Write-Error "File not found: $file"; exit 1
}

$content = Get-Content -Raw -Path $file

# 1) bump @version patch
$content = [regex]::Replace($content, '(@version\s+)(\d+)\.(\d+)\.(\d+)', {
    param($m)
    $prefix = $m.Groups[1].Value
    $major = [int]$m.Groups[2].Value
    $minor = [int]$m.Groups[3].Value
    $patch = [int]$m.Groups[4].Value + 1
    "$prefix$major.$minor.$patch"
})

# 2) increment numeric v= parameters (if present) by 1
$content = [regex]::Replace($content, '(\b\.js\?v=)(\d+)', {
    param($m)
    $prefix = $m.Groups[1].Value
    $v = [int]$m.Groups[2].Value + 1
    "$prefix$v"
})

# 3) update t= to current timestamp
$now = Get-Date -Format yyyyMMddHHmm
# Use a MatchEvaluator to avoid replacement-string ambiguity (e.g. $1 followed by digits)
$content = [regex]::Replace($content, '(\bt=)(\d{10,})', {
  param($m)
  return $m.Groups[1].Value + $now
})

# Write back
Set-Content -Path $file -Value $content -Encoding UTF8

Write-Host "Updated $file. New @version and loader params applied."
Write-Host "New timestamp: $now"

exit 0
