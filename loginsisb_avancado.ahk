; ========================================
; SCRIPT AUTOHOTKEY - LOGIN SISBAJUD (VERSÃO AVANÇADA CORRIGIDA)
; ========================================
; Versão otimizada para resolver problemas de digitação
; ========================================

#NoEnv
#SingleInstance Force
SendMode Input
SetWorkingDir %A_ScriptDir%
CoordMode, Mouse, Screen

; Credenciais
CPF := "300.692.778-85"
SENHA := "Fl@quinho182"

; Aguardar antes de iniciar (reduzido para ser mais rápido)
Sleep, 1000

; Executar login com estratégias otimizadas
LoginAvancadoCorrigido()

LoginAvancadoCorrigido() {
    ; === ESTRATÉGIA PRINCIPAL: PREENCHIMENTO DIRETO ===
    ; Se o cursor já está no campo, vamos preencher diretamente
    
    ; Primeiro, limpar qualquer conteúdo que possa estar no campo
    Send, ^a
    Sleep, 100
    Send, {Delete}
    Sleep, 100
    
    ; Digitar CPF diretamente
    SendRaw, %CPF%
    Sleep, 500
    
    ; Verificar se CPF foi digitado (tentar pegar o clipboard)
    Clipboard := ""
    Send, ^a
    Sleep, 100
    Send, ^c
    Sleep, 200
    
    ; Se não conseguiu digitar ou clipboard não tem o CPF, tentar estratégias alternativas
    if (InStr(Clipboard, "300.692.778") = 0) {
        ; === ESTRATÉGIA ALTERNATIVA 1: MÉTODO CHAR BY CHAR ===
        Send, ^a
        Sleep, 100
        Send, {Delete}
        Sleep, 100
        
        ; Digitar caractere por caractere (mais confiável)
        Loop, Parse, CPF
        {
            SendRaw, %A_LoopField%
            Sleep, 50
        }
        Sleep, 300
    }
    
    ; === PREENCHER SENHA ===
    Send, {Tab}
    Sleep, 300
    
    ; Limpar campo senha
    Send, ^a
    Sleep, 100
    Send, {Delete}
    Sleep, 100
    
    ; Digitar senha
    SendRaw, %SENHA%
    Sleep, 500
    
    ; === SUBMETER FORMULÁRIO ===
    ; Tentar várias formas de submeter
    Send, {Enter}
    Sleep, 1000
    
    ; Se Enter não funcionou, tentar Tab até botão e Enter
    Send, {Tab}
    Sleep, 200
    Send, {Enter}
    Sleep, 1000
    
    ; === ESTRATÉGIA DE FALLBACK: CLIQUES DIRETOS ===
    ; Se as tentativas acima falharam, usar coordenadas
    
    ; Clicar no campo CPF para garantir foco
    Click, 400, 300  ; Coordenadas aproximadas do campo CPF
    Sleep, 300
    
    ; Limpar e preencher CPF
    Send, ^a
    Sleep, 100
    SendRaw, %CPF%
    Sleep, 300
    
    ; Clicar no campo senha
    Click, 400, 350  ; Coordenadas aproximadas do campo senha
    Sleep, 300
    
    ; Limpar e preencher senha
    Send, ^a
    Sleep, 100
    SendRaw, %SENHA%
    Sleep, 300
    
    ; Tentar encontrar e clicar botão Entrar
    ; Clicar em coordenadas típicas de botão de login
    Click, 400, 400
    Sleep, 500
    
    ; === ESTRATÉGIA FINAL: HOTKEYS ESPECÍFICOS ===
    ; Alguns sites respondem melhor a hotkeys específicos
    Send, ^{Enter}  ; Ctrl+Enter
    Sleep, 500
    
    ; Aguardar processamento final
    Sleep, 2000
    
    ; Sair automaticamente
    ExitApp
}

; === HOTKEYS DE EMERGÊNCIA MELHORADOS ===

; F1: Login rápido otimizado
F1::
    Send, ^a
    Sleep, 50
    SendRaw, %CPF%
    Send, {Tab}
    Sleep, 100
    Send, ^a
    Sleep, 50
    SendRaw, %SENHA%
    Send, {Enter}
return

; F2: Apenas CPF (método seguro)
F2::
    Send, ^a
    Sleep, 50
    Send, {Delete}
    Sleep, 50
    SendRaw, %CPF%
return

; F3: Apenas senha (método seguro)
F3::
    Send, ^a
    Sleep, 50
    Send, {Delete}
    Sleep, 50
    SendRaw, %SENHA%
return

; F4: Apenas Enter com múltiplas tentativas
F4::
    Send, {Enter}
    Sleep, 300
    Send, {Tab}
    Send, {Enter}
    Sleep, 300
    Send, ^{Enter}
return

; F5: Teste de digitação (debug)
F5::
    SendRaw, TESTE123
return

; F6: Limpar campo atual
F6::
    Send, ^a
    Sleep, 50
    Send, {Delete}
return

; Escape: Sair
Esc::
    ExitApp
return
