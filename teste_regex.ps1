// Teste simples das regex no PowerShell
$texto = "145.951,09 Bruto Devido ao Reclamante Data Liquidação: 31/05/2025 Cálculo: 3948 HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE 7.297,55 IRPF DEVIDO PELO RECLAMANTE 0,00 Documento assinado eletronicamente por GABRIELA CARR"

Write-Host "=== TESTE DAS CORREÇÕES ===" -ForegroundColor Green

# Teste 1: Total Bruto
if ($texto -match '([\d.,]+)\s+bruto\s+devido\s+ao\s+reclamante') {
    Write-Host "✅ Total Bruto: $($Matches[1])" -ForegroundColor Green
} else {
    Write-Host "❌ Total Bruto: NÃO ENCONTRADO" -ForegroundColor Red
}

# Teste 2: Data Liquidação  
if ($texto -match 'data\s+liquidação\s*[:\s]*(\d{1,2}/\d{1,2}/\d{4})') {
    Write-Host "✅ Data Liquidação: $($Matches[1])" -ForegroundColor Green
} else {
    Write-Host "❌ Data Liquidação: NÃO ENCONTRADO" -ForegroundColor Red
}

# Teste 3: ID Planilha
if ($texto -match 'cálculo\s*[:\s]*(\d+)') {
    Write-Host "✅ ID Planilha: $($Matches[1])" -ForegroundColor Green
} else {
    Write-Host "❌ ID Planilha: NÃO ENCONTRADO" -ForegroundColor Red
}

# Teste 4: Honorários
if ($texto -match 'honorários\s+líquidos\s+para\s+advogado\s+da\s+reclamante\s+([\d.,]+)') {
    Write-Host "✅ Honorários: $($Matches[1])" -ForegroundColor Green
} else {
    Write-Host "❌ Honorários: NÃO ENCONTRADO" -ForegroundColor Red
}

# Teste 5: IRPF
if ($texto -match 'irpf\s+devido\s+pelo\s+reclamante\s+([\d.,]+)') {
    Write-Host "✅ IRPF: $($Matches[1])" -ForegroundColor Green
} else {
    Write-Host "❌ IRPF: NÃO ENCONTRADO" -ForegroundColor Red
}

# Teste 6: Assinatura
if ($texto -match 'documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+)') {
    Write-Host "✅ Assinatura: $($Matches[1])" -ForegroundColor Green
} else {
    Write-Host "❌ Assinatura: NÃO ENCONTRADO" -ForegroundColor Red
}
