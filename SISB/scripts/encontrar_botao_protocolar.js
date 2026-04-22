// SISB/scripts/encontrar_botao_protocolar.js
// Script para encontrar o botão "Protocolar" na minuta

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
    protocoloBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
    return true;
}
return false;
