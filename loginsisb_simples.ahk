; ========================================
; SCRIPT AUTOHOTKEY - LOGIN SISBAJUD (VERSÃO ULTRA SIMPLES CORRIGIDA)
; ========================================
; Versão minimalista para casos problemáticos
; Execução automática em 2 segundos
; ========================================

#NoEnv
#SingleInstance Force
SendMode Input
SetWorkingDir %A_ScriptDir%

; Credenciais
CPF := "300.692.778-85"
SENHA := "Fl@quinho182"

; Aguardar 2 segundos e executar automaticamente
Sleep, 2000
LoginUltraSimples()

LoginUltraSimples() {
    ; Método ultra direto - assumindo que cursor já está no campo CPF
    
    ; Limpar campo atual
    Send, ^a
    Sleep, 100
    
    ; Digitar CPF
    SendRaw, %CPF%
    Sleep, 500
    
    ; Ir para próximo campo (senha)
    Send, {Tab}
    Sleep, 300
    
    ; Limpar e digitar senha
    Send, ^a
    Sleep, 100
    SendRaw, %SENHA%
    Sleep, 500
    
    ; Submeter formulário
    Send, {Enter}
    
    ; Aguardar e sair
    Sleep, 3000
    ExitApp
}

; === HOTKEYS DE EMERGÊNCIA ===

; F1: Login rápido manual
F1::
    SendRaw, %CPF%
    Send, {Tab}
    SendRaw, %SENHA%
    Send, {Enter}
return

; F2: Apenas CPF
F2::
    Send, ^a
    Sleep, 50
    SendRaw, %CPF%
return

; F3: Apenas senha
F3::
    Send, ^a
    Sleep, 50
    SendRaw, %SENHA%
return

; F4: Apenas Enter
F4::
    Send, {Enter}
return

; F5: Executar login completo (modo manual)
F5::
    ; Limpar e preencher CPF
    Send, ^a
    Sleep, 100
    SendRaw, %CPF%
    Sleep, 300
    
    ; Próximo campo
    Send, {Tab}
    Sleep, 300
    
    ; Limpar e preencher senha
    Send, ^a
    Sleep, 100
    SendRaw, %SENHA%
    Sleep, 300
    
    ; Submeter
    Send, {Enter}
    
    ; Mostrar confirmação
    ToolTip, Login enviado!, 100, 100
    Sleep, 2000
    ToolTip
return

; Escape: Sair
Esc::
    ExitApp
return
    SendRaw, %SENHA%
return

; F3: Apenas Enter
F3::
    Send, {Enter}
return

; F4: Tab (próximo campo)
F4::
    Send, {Tab}
return

; ESC: Sair
Esc::
    ExitApp
return

; === INSTRUÇÕES ===
; 1. Execute este script
; 2. Abra o SISBAJUD no navegador
; 3. Clique no primeiro campo (CPF)
; 4. Pressione F5 para login automático
;
; Ou use as teclas individuais:
; F1 = Digitar CPF
; F2 = Digitar senha  
; F3 = Pressionar Enter
; F4 = Próximo campo (Tab)
; ESC = Sair do script
