// Clicar no botão "Confirmar" após copiar ordem
const buttons = Array.from(document.querySelectorAll('button'));
const confirmBtn = buttons.find(btn => {
    const wrapper = btn.querySelector('span.mat-button-wrapper');
    return wrapper && wrapper.textContent.trim() === 'Confirmar';
});
if (confirmBtn) {
    confirmBtn.click();
    return true;
}
return false;
