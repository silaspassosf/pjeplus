# tools/build.ps1
# Empacota src/ como pjet-<version>.xpi para instalar no Firefox
param([string]$version = "1.0.0")

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$src  = (Resolve-Path "$PSScriptRoot\..\src").Path
$dist = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\dist")

if (!(Test-Path $dist)) {
    New-Item -ItemType Directory -Path $dist | Out-Null
}

$out = Join-Path $dist "pjet-$version.xpi"
if (Test-Path $out) { Remove-Item $out -Force }

# Cria o arquivo ZIP/XPI com separadores '/' (padrão POSIX exigido pelo Firefox)
$zip = [System.IO.Compression.ZipFile]::Open($out, [System.IO.Compression.ZipArchiveMode]::Create)
Get-ChildItem -Path $src -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($src.Length + 1).Replace('\', '/')
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $rel, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
}
$zip.Dispose()

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  PJeT .xpi gerado com sucesso!" -ForegroundColor Green
Write-Host "  $out" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "INSTALAR NO FIREFOX:" -ForegroundColor Yellow
Write-Host "  Opção A (permanente): Firefox Dev Edition" -ForegroundColor White
Write-Host "    1. about:config → xpinstall.signatures.required = false" -ForegroundColor Gray
Write-Host "    2. Arrastar o .xpi para o Firefox" -ForegroundColor Gray
Write-Host ""
Write-Host "  Opção B (temporária para testes):" -ForegroundColor White
Write-Host "    1. about:debugging → Este Firefox" -ForegroundColor Gray
Write-Host "    2. Carregar extensão temporária → selecionar src\manifest.json" -ForegroundColor Gray
Write-Host ""
Write-Host "  Opção C (distribuição sem loja, qualquer Firefox):" -ForegroundColor White
Write-Host "    web-ext sign --api-key=<KEY> --api-secret=<SECRET> --channel=unlisted" -ForegroundColor Gray
