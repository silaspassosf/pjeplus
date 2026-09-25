// credito_mock.js — preenche um input monetário do PJe (obrigação de pagar).
//
// Estratégia de teclado porta a porta de
// `Script/modules/debito/registrar_debito.js::preencherMonetario` (FIX 3 — a
// única que habilita o botão Salvar do PJe, porque a currency mask formata o
// valor enquanto os eventos `input` chegam caractere a caractere).
//
// Uso: `driver.page.evaluate(carregar_js('credito_mock.js', SCRIPTS_DIR),
//                            {valor: '0,01', placeholder: 'Crédito do demandante'})`
// Retorna `{ok, valor|motivo}`.
async (args) => {
  const valorBR = (args && args.valor) || '0,01';
  const placeholder = (args && args.placeholder) || 'Crédito do demandante';
  const input = document.querySelector('input[data-placeholder="' + placeholder + '"]');
  if (!input) {
    return { ok: false, motivo: 'campo nao encontrado: ' + placeholder };
  }

  // Máscara do PJe recebe só dígitos: "0,01" -> "001" -> exibe "0,01"
  const digitos = String(valorBR).replace(/R\$\s*/g, '').replace(/\./g, '').replace(/[^\d]/g, '');
  const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

  input.focus();
  await dormir(80);

  set.call(input, '');
  input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward' }));
  await dormir(40);

  for (const ch of digitos) {
    input.dispatchEvent(new KeyboardEvent('keydown', { key: ch, bubbles: true, cancelable: true }));
    input.dispatchEvent(new KeyboardEvent('keypress', {
      key: ch, bubbles: true, cancelable: true, charCode: ch.charCodeAt(0),
    }));
    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: ch }));
    input.dispatchEvent(new KeyboardEvent('keyup', { key: ch, bubbles: true }));
    await dormir(30);
  }

  input.dispatchEvent(new Event('change', { bubbles: true }));
  input.dispatchEvent(new Event('blur', { bubbles: true }));
  await dormir(60);

  return { ok: true, valor: input.value };
}
