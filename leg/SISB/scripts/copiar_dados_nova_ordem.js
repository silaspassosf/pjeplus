// Clicar no botão "Copiar Dados para Nova Ordem" ou fallback
const buttons = Array.from(document.querySelectorAll('button[title="Copiar Dados para Nova Ordem"]'));
if (buttons.length > 0) {
    buttons[0].click();
    return true;
}
const allButtons = Array.from(document.querySelectorAll('button'));
const copyBtn = allButtons.find(btn => {
    const icon = btn.querySelector('mat-icon.fa-copy');
    const text = btn.textContent;
    return icon && text.includes('Copiar Dados');
});
if (copyBtn) {
    copyBtn.click();
    return true;
}
return false;
