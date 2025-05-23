; Atalho: Ctrl+Alt+S para login automático SISBAJUD
^!s::
    cpf := "300.692.778-85"
    senha := "Fl@quinho182"

    ; Ativar a janela do Firefox SISBAJUD
    WinActivate, SISBAJUD
    Sleep, 300

    ; Tab 11 vezes até o campo CPF
    Send, {Tab 11}
    Sleep, 150
    Send, %cpf%
    Sleep, 200

    ; Tab para o campo Senha
    Send, {Tab}
    Sleep, 150
    Send, %senha%
    Sleep, 200

    ; Enter para logar
    Send, {Enter}
    return