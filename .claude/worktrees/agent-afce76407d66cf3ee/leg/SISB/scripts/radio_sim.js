// Clicar no radio SIM dentro do card "Dados básicos da ordem"
try {
    var cards = Array.from(document.querySelectorAll('mat-card'));
    var cardDados = cards.find(card => {
        var title = card.querySelector('mat-card-title');
        return title && title.textContent.includes('Dados básicos da ordem');
    });
    if (!cardDados) {
        return 'card_not_found';
    }
    var radioSim = cardDados.querySelector('mat-radio-button[id="mat-radio-46"]');
    if (!radioSim) {
        return 'radio_not_found';
    }
    var label = radioSim.querySelector('label');
    if (label) {
        label.click();
        return 'clicked';
    } else {
        return 'label_not_found';
    }
} catch (e) {
    return 'error: ' + e.message;
}
