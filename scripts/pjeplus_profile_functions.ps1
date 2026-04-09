# PJePlus — Funções rápidas para o PowerShell
# 
# Para ativar de forma permanente, rode UMA VEZ no terminal:
#   Add-Content $PROFILE (Get-Content D:\PjePlus\scripts\pjeplus_profile_functions.ps1 -Raw)
#
# Ou adicione manualmente ao seu $PROFILE (geralmente em
#   C:\Users\<usuario>\Documents\PowerShell\Microsoft.PowerShell_profile.ps1)
#
# ─────────────────────────────────────────────────────────────────────────────

# pje-log: filtra saída de log para linhas de erro antes de copiar para IA
#
# Exemplos:
#   py x.py 2>&1 | pje-log
#   py x.py 2>&1 | pje-log -Nivel WARNING
#   pje-log -Arquivo logs_execucao/run.log
#   pje-log -Arquivo logs_execucao/run.log -Nivel ERROR -Max 20
#
function pje-log {
    param(
        [string]$Arquivo   = "",
        [string]$Nivel     = "ERROR",
        [int]   $Max       = 50,
        [switch]$Clipboard         # copiado direto para área de transferência
    )

    $pjeDir = "D:\PjePlus"

    if ($Arquivo -ne "") {
        $result = & py "$pjeDir\Fix\log_cleaner.py" $Arquivo --nivel $Nivel --max $Max
    } else {
        # Modo pipe: recebe da entrada padrão
        $input | & py "$pjeDir\Fix\log_cleaner.py" --stdin --nivel $Nivel --max $Max
        return
    }

    if ($Clipboard) {
        $result | Set-Clipboard
        Write-Host "[pje-log] $($result.Count) linhas copiadas para área de transferência."
    } else {
        $result
    }
}


# pje-sel: reduz HTML bruto do DevTools para seletor CSS em 1 linha
#
# Exemplos:
#   pje-sel '<button class="btn-salvar" id="s1">Salvar</button>'
#   Get-Clipboard | pje-sel
#
function pje-sel {
    param([string]$Html = "")

    $pjeDir = "D:\PjePlus"

    # Se não foi passado argumento, lê da área de transferência (caso de uso real)
    if ($Html -eq "") {
        $Html = Get-Clipboard
    }

    # Escreve em arquivo temp para evitar escaping de aspas no -c
    $tmpFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tmpFile, $Html, [System.Text.Encoding]::UTF8)
        & py -c @"
from Fix.log_cleaner import extrair_seletor_dom
from pathlib import Path
html = Path(r'$tmpFile').read_text(encoding='utf-8')
print(extrair_seletor_dom(html))
"@
    } finally {
        Remove-Item $tmpFile -ErrorAction SilentlyContinue
    }
}
