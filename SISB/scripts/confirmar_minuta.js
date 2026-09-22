// SISB/scripts/confirmar_minuta.js
// Script para encontrar e clicar no botão "Confirmar" na modal de senha

const buttons = Array.from(document.querySelectorAll('button[type="submit"][color="primary"]'));
let confirmBtn = buttons.find(btn => {
    const wrapper = btn.querySelector('span.mat-button-wrapper');
    return wrapper && wrapper.textContent.trim() === 'Confirmar';
});
// Fallback se não encontrar o botão específico
if (!confirmBtn) {
    const allButtons = Array.from(document.querySelectorAll('button'));
    confirmBtn = allButtons.find(btn => btn.textContent.includes('Confirmar'));
}
if (confirmBtn) {
    confirmBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
    confirmBtn.click();
    return true;
}
return false;
