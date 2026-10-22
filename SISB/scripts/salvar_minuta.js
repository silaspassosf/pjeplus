// SISB/scripts/salvar_minuta.js
// Script para clicar no botão Salvar da minuta

function acionarBotao(btn) {
    if (!btn) return false;
    try {
        btn.scrollIntoView({ block: 'center', inline: 'center' });
    } catch (e) {}
    try {
        btn.focus();
        btn.click();
        return true;
    } catch (e) {
        return false;
    }
}

// 1. Buscar botão com ícone fa-save
var btnIcon = document.querySelector('button.mat-fab.mat-primary mat-icon.fa-save')
           || document.querySelector('button mat-icon.fa-save')
           || document.querySelector('button.mat-fab mat-icon[fonticon*="save"]')
           || document.querySelector('button mat-icon[fonticon*="save"]');
if (btnIcon) {
    var b = btnIcon.closest('button');
    if (b && acionarBotao(b)) return true;
}

// 2. Fallback: buscar por texto "Salvar"
var buttons = Array.from(document.querySelectorAll('button'));
for (var i = 0; i < buttons.length; i++) {
    var txt = (buttons[i].textContent || '').trim();
    if (txt === 'Salvar' || (txt.includes('Salvar') && !txt.includes('Salvar como'))) {
        if (acionarBotao(buttons[i])) return true;
    }
}

return false;
