// SISB/scripts/verificar_sucesso_minuta.js
// Script para verificar sucesso do protocolo da minuta

const buttons = Array.from(document.querySelectorAll('button[title="Copiar Dados para Nova Ordem"]'));
if (buttons.length > 0) {
    return true;
}
// Fallback: procurar por botão com mat-icon fa-copy e texto "Copiar Dados"
const allButtons = Array.from(document.querySelectorAll('button'));
const copyBtn = allButtons.find(btn => {
    const icon = btn.querySelector('mat-icon.fa-copy');
    const text = btn.textContent;
    return icon && text.includes('Copiar Dados');
});
return copyBtn !== undefined;
