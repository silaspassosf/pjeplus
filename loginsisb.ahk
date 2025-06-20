; ========================================
; SCRIPT AUTOHOTKEY - LOGIN SISBAJUD (COORDENADAS ESPECÍFICAS)
; ========================================
; Baseado na tela real do SISBAJUD com coordenadas precisas
; ========================================

#NoEnv
#SingleInstance Force
SendMode Input
SetWorkingDir %A_ScriptDir%
CoordMode, Mouse, Screen

; Dados de login
CPF := "300.692.778-85"
SENHA := "Fl@quinho182"

; Aguardar 2 segundos antes de iniciar
Sleep, 2000

; Executar login com coordenadas específicas
LoginComCoordenadas()

LoginComCoordenadas() {
    ; === ETAPA 1: CLICAR NO CAMPO CPF ===
    ; Coordenadas aproximadas do campo CPF (baseado na imagem)
    Click, 1050, 181  ; Campo CPF/CNPJ
    Sleep, 300
    
    ; Limpar campo
    Send, ^a
    Sleep, 100
    Send, {Delete}
    Sleep, 200
    
    ; Digitar CPF
    Loop, Parse, CPF
    {
        SendRaw, %A_LoopField%
        Sleep, 60
    }
    
    Sleep, 500
    
    ; === ETAPA 2: CLICAR NO CAMPO SENHA ===
    ; Coordenadas aproximadas do campo senha
    Click, 1050, 254  ; Campo "Digite sua senha"
    Sleep, 300
    
    ; Limpar campo senha
    Send, ^a
    Sleep, 100
    Send, {Delete}
    Sleep, 200
    
    ; Digitar senha
    Loop, Parse, SENHA
    {
        SendRaw, %A_LoopField%
        Sleep, 60
    }
    
    Sleep, 800
    
    ; === ETAPA 3: CLICAR NO BOTÃO ENTRAR ===
    ; Coordenadas do botão "Entrar" (azul)
    Click, 1177, 305  ; Botão "Entrar"
    Sleep, 1000
    
    ; Se não funcionou, tentar Enter como backup
    Send, {Enter}
    
    ; Aguardar processamento
    Sleep, 3000
    
    ; Finalizar
    ExitApp
}

; === HOTKEYS PARA TESTE E AJUSTE ===

; F1: Login completo com coordenadas
F1::
    LoginComCoordenadas()
return

; F2: Apenas clicar e digitar CPF
F2::
    Click, 1050, 181
    Sleep, 300
    Send, ^a
    Sleep, 100
    Send, {Delete}
    Sleep, 100
    Loop, Parse, CPF
    {
        SendRaw, %A_LoopField%
        Sleep, 50
    }
return

; F3: Apenas clicar e digitar senha
F3::
    Click, 1050, 254
    Sleep, 300
    Send, ^a
    Sleep, 100
    Send, {Delete}
    Sleep, 100
    Loop, Parse, SENHA
    {
        SendRaw, %A_LoopField%
        Sleep, 50
    }
return

; F4: Apenas clicar no botão Entrar
F4::
    Click, 1177, 305
return

; F5: Mostrar posição do mouse (para ajustar coordenadas)
F5::
    MouseGetPos, xpos, ypos
    ToolTip, X:%xpos% Y:%ypos%, %xpos%, %ypos%
    Sleep, 3000
    ToolTip
return

; F6: Teste de digitação simples
F6::
    SendRaw, TESTE123
return

; Escape: Sair
Esc::
    ExitApp
return
