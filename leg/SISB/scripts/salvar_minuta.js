// SISB/scripts/salvar_minuta.js
// Script para clicar no botão Salvar da minuta

// Buscar botão de salvar com seletor específico
var btnSalvar = document.querySelector('button.mat-fab.mat-primary mat-icon.fa-save');
if (btnSalvar) {
    btnSalvar.closest('button').click();
    return true;
}

// Fallback: buscar por qualquer botão com ícone de save
var btnFallback = document.querySelector('button mat-icon.fa-save');
if (btnFallback) {
    btnFallback.closest('button').click();
    return true;
}

// Fallback 2: buscar por texto "Salvar"
var buttons = document.querySelectorAll('button');
for (var i = 0; i < buttons.length; i++) {
    if (buttons[i].textContent.includes('Salvar')) {
        buttons[i].click();
        return true;
    }
}

return false;
