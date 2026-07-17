// SISB/scripts/verificar_salvamento_minuta.js
// Script para verificar se a minuta foi salva com sucesso

// Buscar botão "Alterar" como confirmação
var btnAlterar = document.querySelector('button mat-icon.fa-edit');
if (btnAlterar) {
    var btnTexto = btnAlterar.closest('button');
    if (btnTexto && btnTexto.textContent.includes('Alterar')) {
        return 'SALVO_COM_SUCESSO';
    }
}

// Verificar se ainda está na página de edição
var btnSalvar = document.querySelector('button mat-icon.fa-save');
if (btnSalvar) {
    return 'AINDA_EDITANDO';
}

return 'STATUS_DESCONHECIDO';
