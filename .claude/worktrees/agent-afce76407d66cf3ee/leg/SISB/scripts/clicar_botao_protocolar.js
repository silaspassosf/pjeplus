// SISB/scripts/clicar_botao_protocolar.js
// Script para clicar no botão "Protocolar" na minuta

const buttons = Array.from(document.querySelectorAll('button'));
const protocoloBtn = buttons.find(btn => {
    const spans = btn.querySelectorAll('span.mat-button-wrapper');
    return Array.from(spans).some(span => {
        const hasIcon = span.querySelector('mat-icon.fa-gavel');
        const hasText = span.textContent.includes('Protocolar');
        return hasIcon || hasText;
    });
});
if (protocoloBtn) {
    protocoloBtn.click();
    return true;
}
return false;
