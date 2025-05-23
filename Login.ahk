; Login.ahk - Digitação humanizada do PIN/senha do certificado digital usando variável de ambiente

EnvGet, senha, PJE_SENHA
if (senha = "") {
    MsgBox, 16, Erro, Variável de ambiente PJE_SENHA não definida!
    ExitApp
}

; Foca na janela do PIN do certificado digital
WinWaitActive, Verifique PIN do usuário,, 5

; Digitação humanizada, caractere a caractere, com delays aleatórios e simulação de erro/correção
Loop, Parse, senha
{
    Random, erro, 1, 100
    if (erro <= 10) ; 10% de chance de errar uma letra
    {
        Random, letraErrada, 97, 122 ; letra minúscula aleatória
        Send, % Chr(letraErrada)
        Sleep, 140
        Send, {Backspace}
        Sleep, 120
    }
    Random, delay, 180, 350 ; DELAYS MAIS LENTOS
    Send, %A_LoopField%
    Sleep, %delay%
}
Random, enterDelay, 400, 800
Sleep, %enterDelay%
Send, {Enter}