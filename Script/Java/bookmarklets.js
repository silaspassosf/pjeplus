javascript:(function(){
  function waitFor(selector, timeout = 5000) {
    return new Promise(function(resolve) {
      var element = document.querySelector(selector);
      if (element) { resolve(element); return; }
      var observer = new MutationObserver(function() {
        element = document.querySelector(selector);
        if (element) { observer.disconnect(); resolve(element); }
      });
      observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'aria-label'] });
      setTimeout(function() { observer.disconnect(); resolve(null); }, timeout);
    });
  }

  function waitForOption(text, timeout = 5000) {
    text = String(text).trim().toUpperCase();
    return new Promise(function(resolve) {
      function check() {
        var options = document.querySelectorAll('mat-option');
        for (var i = 0; i < options.length; i++) {
          if (options[i].textContent.trim().toUpperCase() === text) {
            return options[i];
          }
        }
        return null;
      }
      var option = check();
      if (option) { resolve(option); return; }
      var observer = new MutationObserver(function() {
        option = check();
        if (option) { observer.disconnect(); resolve(option); }
      });
      observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'aria-label'] });
      setTimeout(function() { observer.disconnect(); resolve(null); }, timeout);
    });
  }

  function triggerEvent(element, type) {
    if (!element) return;
    try {
      element.dispatchEvent(new Event(type, { bubbles: true }));
    } catch (e) {
      var evt = document.createEvent('HTMLEvents');
      evt.initEvent(type, true, true);
      element.dispatchEvent(evt);
    }
  }

  async function clearResponsible() {
    var input = await waitFor('input[aria-label^="Responsável:"]', 5000);
    if (!input) {
      console.log('[GIGS_CLEANUP] Responsável não encontrado');
      return;
    }
    input.click();
    input.focus();
    triggerEvent(input, 'focus');
    input.value = 'S';
    triggerEvent(input, 'input');

    var option = await waitForOption('SEM RESPONSÁVEL', 5000);
    if (option) {
      option.click();
      await waitFor('input[aria-label="Sem Responsável"]', 5000);
      console.log('[GIGS_CLEANUP] Responsável limpo');
    } else {
      console.log('[GIGS_CLEANUP] Opção SEM RESPONSÁVEL não encontrada');
    }
  }

  function findConfirmButton() {
    var buttons = document.querySelectorAll('button[color="primary"]');
    for (var i = 0; i < buttons.length; i++) {
      var span = buttons[i].querySelector('span.mat-button-wrapper');
      if (span && span.textContent.trim() === 'Sim') return buttons[i];
    }
    var allButtons = document.querySelectorAll('button');
    for (var j = 0; j < allButtons.length; j++) {
      if (allButtons[j].textContent.trim() === 'Sim') return allButtons[j];
    }
    return null;
  }

  async function processAtividades() {
    var hasMore = true;
    while (hasMore) {
      hasMore = false;
      var rows = document.querySelectorAll('pje-gigs-atividades table tbody tr');
      for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        try {
          if (row.style.display === 'none') continue;
          var descEl = row.querySelector('td .descricao');
          if (!descEl) continue;
          var descricao = descEl.textContent.trim();
          var alertaPrazo = row.querySelector('pje-gigs-alerta-prazo .prazo');
          if (!alertaPrazo) continue;
          var isVencida = alertaPrazo.querySelector('i.danger.fa-clock.far');
          var isSemPrazo = alertaPrazo.querySelector('i.fa.fa-pen.atividade-sem-prazo');
          var isRelogioVerde = alertaPrazo.querySelector('i.fa-clock.far.success');
          if (isRelogioVerde) continue;
          var hasXsOrSilas = descricao.toLowerCase().includes('xs') || descricao.toLowerCase().includes('silas');
          var hasDomE = descricao.includes('Dom.E');
          var qualifica = (isVencida && hasXsOrSilas) || (isSemPrazo && (hasXsOrSilas || hasDomE));
          if (!qualifica) continue;
          var btnExcluir = row.querySelector('button[mattooltip="Excluir Atividade"]');
          if (!btnExcluir) continue;
          processedCount++;
          btnExcluir.click();
          var btnConfirmar = findConfirmButton();
          if (btnConfirmar) {
            btnConfirmar.click();
            removedCount++;
            hasMore = true;
            break;
          }
        } catch (error) {
          console.error('[GIGS_CLEANUP] Erro ao processar atividade:', error);
        }
      }
    }
  }

  var processedCount = 0;
  var removedCount = 0;
  console.log('[GIGS_CLEANUP] Iniciando limpeza de atividades...');
  clearResponsible().then(processAtividades).then(function() {
    console.log('[GIGS_CLEANUP] Processamento concluído! Atividades processadas: ' + processedCount + ' Atividades removidas: ' + removedCount);
  }).catch(function(error) {
    console.error('[GIGS_CLEANUP] Erro durante processamento:', error);
  });
})();
