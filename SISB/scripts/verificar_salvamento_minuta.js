// SISB/scripts/verificar_salvamento_minuta.js
// Script para verificar se a minuta foi salva com sucesso

var url = window.location.href || '';

// 1. Se saiu de /cadastrar e foi para /detalhar, /detalhe ou ID numérico
if (!url.includes('/cadastrar') && (url.includes('/detalhar') || url.includes('/detalhe') || /\/\d{5,}/.test(url))) {
    return 'SALVO_COM_SUCESSO';
}

// 2. Buscar botão "Alterar" como confirmação
var buttons = Array.from(document.querySelectorAll('button'));
var btnAlterar = buttons.find(b => {
    var txt = (b.textContent || '').trim().toLowerCase();
    return txt.includes('alterar') || b.querySelector('mat-icon.fa-edit') || b.querySelector('mat-icon[fonticon*="edit"]');
});
if (btnAlterar) {
    return 'SALVO_COM_SUCESSO';
}

// 3. Buscar botão "Protocolar" como confirmação
var btnProtocolar = buttons.find(b => {
    var txt = (b.textContent || '').trim().toLowerCase();
    return txt.includes('protocolar') || b.querySelector('mat-icon.fa-gavel') || b.querySelector('mat-icon[fonticon*="gavel"]');
});
if (btnProtocolar) {
    return 'SALVO_COM_SUCESSO';
}

// 4. Snackbar de sucesso (ex: "Minuta salva com sucesso")
var snackbars = Array.from(document.querySelectorAll('.mat-snack-bar-container, snack-bar-container, .toast-success, mat-dialog-container'));
for (var i = 0; i < snackbars.length; i++) {
    var st = (snackbars[i].textContent || '').toLowerCase();
    if (st.includes('sucesso') || (st.includes('salv') && !st.includes('erro'))) {
        return 'SALVO_COM_SUCESSO';
    }
}

// 5. Verificar se ainda está na página de edição (botão salvar visível e habilitado)
var btnSalvar = document.querySelector('button.mat-fab.mat-primary mat-icon.fa-save')
             || document.querySelector('button mat-icon.fa-save')
             || buttons.find(b => (b.textContent || '').trim() === 'Salvar');
if (btnSalvar && url.includes('/cadastrar')) {
    return 'AINDA_EDITANDO';
}

// 6. Se não está mais em /cadastrar
if (!url.includes('/cadastrar')) {
    return 'SALVO_COM_SUCESSO';
}

return 'STATUS_DESCONHECIDO';
