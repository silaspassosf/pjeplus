<#
.SYNOPSIS
Gate automatizado para waves de limpeza de shims do projeto PJePlus.

.PARAMETER Wave
Numero da wave sendo validada (informativo).

.EXAMPLE
.\tools\wave_runner.ps1 -Wave 1
.\tools\wave_runner.ps1 -Wave 0

.NOTES
Exit code 0 = gate verde (pode commitar).
Exit code 1 = gate vermelho (reverter com: git checkout -- .)
#>
param(
    [Parameter(Mandatory=$true)]
    [int]$Wave
)

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host ""
Write-Host "=== GATE Wave $Wave ===" -ForegroundColor Cyan
Write-Host "Diretorio: $Root"
Write-Host ""

# --------------------------------------------------------------------------
# 1. Compilar arquivos criticos
# --------------------------------------------------------------------------
$CriticalFiles = @(
    'x.py',
    'Fix\core.py',
    'Fix\utils.py',
    'Fix\extracao.py',
    'Mandado\entrada_api.py',
    'Prazo\p2b_gateway.py',
    'PEC\orquestrador.py',
    'Triagem\runtime_triagem.py',
    'Peticao\runtime_pet.py',
    'SISB\core.py',
    'SISB\facades_contratos.py'
)

Write-Host "[1/3] py_compile arquivos criticos..." -ForegroundColor Yellow
$allOk = $true
foreach ($f in $CriticalFiles) {
    if (Test-Path $f) {
        $result = py -m py_compile $f 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  FAIL: $f" -ForegroundColor Red
            if ($result) { Write-Host "       $result" -ForegroundColor Red }
            $allOk = $false
        } else {
            Write-Host "  OK  : $f" -ForegroundColor Green
        }
    } else {
        Write-Host "  SKIP: $f (nao encontrado)" -ForegroundColor DarkGray
    }
}

if (-not $allOk) {
    Write-Host ""
    Write-Host "[GATE FALHOU] Um ou mais arquivos criticos nao compilam." -ForegroundColor Red
    Write-Host "Reverta com: git checkout -- ." -ForegroundColor Yellow
    exit 1
}

# --------------------------------------------------------------------------
# 2. Gate de importacao
# --------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/3] test_imports.py..." -ForegroundColor Yellow
py test_imports.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[GATE FALHOU] test_imports.py retornou falhas." -ForegroundColor Red
    Write-Host "Reverta com: git checkout -- ." -ForegroundColor Yellow
    exit 1
}

# --------------------------------------------------------------------------
# 3. Verificar shims residuais sem callers (informativo)
# --------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/3] shim_audit (zero callers restantes)..." -ForegroundColor Yellow
if (Test-Path "tools\shim_audit.py") {
    $zeroOutput = py tools/shim_audit.py --zero 2>&1
    $shimCount = ($zeroOutput | Select-String "^  (?!Total|Safe)").Count
    Write-Host "  Shims ainda sem callers: $shimCount" -ForegroundColor $(if ($shimCount -gt 0) { 'Yellow' } else { 'Green' })
} else {
    Write-Host "  SKIP: tools/shim_audit.py nao encontrado (wave 00 nao concluida?)" -ForegroundColor DarkGray
}

# --------------------------------------------------------------------------
# Resultado final
# --------------------------------------------------------------------------
Write-Host ""
Write-Host ("=== Wave " + $Wave + ": GATE VERDE ===") -ForegroundColor Green
Write-Host ""
Write-Host "Proximo passo:"
Write-Host "  git add -A"
Write-Host "  git commit -m 'shim: wave $Wave — <descricao>'"
Write-Host ""
exit 0
