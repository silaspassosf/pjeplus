// =============================================================================
// TEST_BCB_FORM_COMPLETO - Todos os campos da página BCB
// =============================================================================

window.testBcbForm = async function() {
    console.clear();
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║ TESTE BCB COMPLETO - Todos os campos                        ║');
    console.log('╚══════════════════════════════════════════════════════════════╝');
    
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    const r = {};

    // ===================================================================
    // [1] VARA
    // ===================================================================
    console.log('\n📋 [1] VARA...');
    const inputVara = document.querySelector('input.form-control.saj-input-select-form-input');
    if (!inputVara) { console.error('❌ Vara não encontrada!'); r.vara = '❌'; }
    else {
        inputVara.value = '3ª VA';
        inputVara.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(600);
        const opcoes = document.querySelectorAll('div.saj-input-select-body-options-value');
        const opcao = Array.from(opcoes).find(op =>
            op.textContent.trim().startsWith('3ª VARA DO TRABALHO DA ZONA SUL DE SÃO PAULO'));
        if (opcao) { opcao.click(); await sleep(600); console.log('✅ Vara: 3ª VARA ZONA SUL'); r.vara = '✅'; }
        else { console.warn('⚠️ Opção 3ª Vara não encontrada'); r.vara = '⚠️'; }
    }

    // ===================================================================
    // [2] JUIZ
    // ===================================================================
    console.log('\n📋 [2] JUIZ...');
    const selectJuiz = document.querySelector('select.form-control');
    if (!selectJuiz) { console.error('❌ Juiz não encontrado!'); r.juiz = '❌'; }
    else {
        const op = Array.from(selectJuiz.options).find(o => o.text.includes('OTAVIO AUGUSTO MACHADO DE OLIVEIRA'));
        if (op) { selectJuiz.value = op.value; selectJuiz.dispatchEvent(new Event('change', { bubbles: true })); await sleep(300); console.log('✅ Juiz: OTAVIO AUGUSTO'); r.juiz = '✅'; }
        else { console.warn('⚠️ Juiz OTAVIO não encontrado'); r.juiz = '⚠️'; }
    }

    // ===================================================================
    // [3] PROCESSO
    // ===================================================================
    console.log('\n📋 [3] PROCESSO...');
    const inputProc = document.querySelector('#codigoProcesso');
    if (!inputProc) { console.error('❌ Processo não encontrado!'); r.processo = '❌'; }
    else {
        const num = localStorage.getItem('simba_last_processo') || '1000100-23.2025.5.02.0003';
        inputProc.value = num; inputProc.dispatchEvent(new Event('input', { bubbles: true })); inputProc.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(300); console.log(`✅ Processo: ${num}`); r.processo = '✅';
    }

    // ===================================================================
    // [4] PRAZO
    // ===================================================================
    console.log('\n📋 [4] PRAZO...');
    const inputPrazo = document.querySelector('#prazo');
    if (!inputPrazo) { console.error('❌ Prazo não encontrado!'); r.prazo = '❌'; }
    else {
        inputPrazo.value = '60'; inputPrazo.dispatchEvent(new Event('input', { bubbles: true })); inputPrazo.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(300); console.log('✅ Prazo: 60'); r.prazo = '✅';
    }

    // ===================================================================
    // [5] CHECKBOXES
    // ===================================================================
    console.log('\n📋 [5] CHECKBOXES...');
    const allB = document.querySelectorAll('b');
    
    const lbMov = Array.from(allB).find(b => b.textContent.includes('Extrato de movimentação - Carta-Circular 3454 (Simba)'));
    if (lbMov) { lbMov.click(); await sleep(400); r.cbMov = lbMov.closest('label')?.querySelector('input[type="checkbox"]')?.checked ? '✅' : '❌'; console.log(`${r.cbMov} CB Movimentação`); }
    else { r.cbMov = '❌'; console.error('❌ CB Movimentação'); }

    await sleep(300);
    const cb3 = document.querySelector('input[id="3"]');
    if (cb3) { cb3.click(); cb3.dispatchEvent(new Event('change', { bubbles: true })); await sleep(400); r.cbApl = cb3.checked ? '✅' : '❌'; console.log(`${r.cbApl} CB Aplicações`); }
    else { r.cbApl = '❌'; console.error('❌ CB Aplicações'); }

    await sleep(300);
    const cb4 = document.querySelector('input[id="4"]');
    if (cb4) { cb4.click(); cb4.dispatchEvent(new Event('change', { bubbles: true })); await sleep(400); r.cbCart = cb4.checked ? '✅' : '❌'; console.log(`${r.cbCart} CB Cartão`); }
    else { r.cbCart = '❌'; console.error('❌ CB Cartão'); }

    // ===================================================================
    // [6] EMAIL
    // ===================================================================
    console.log('\n📋 [6] EMAIL...');
    const inputEmail = document.querySelector('#email');
    if (!inputEmail) { console.error('❌ Email não encontrado!'); r.email = '❌'; }
    else {
        inputEmail.value = 'vtsps03@trt2.jus.br'; inputEmail.dispatchEvent(new Event('input', { bubbles: true })); inputEmail.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(300); console.log('✅ Email: vtsps03@trt2.jus.br'); r.email = '✅';
    }

    // ===================================================================
    // [7] TELEFONE - FocusEvent + keystrokes (CORRIGIDO!)
    // ===================================================================
    console.log('\n📋 [7] TELEFONE...');
    const inputTel = document.querySelector('#telefone');
    if (!inputTel) { console.error('❌ Telefone não encontrado!'); r.tel = '❌'; }
    else {
        inputTel.scrollIntoView({ behavior: 'smooth', block: 'center' }); await sleep(500);
        inputTel.dispatchEvent(new FocusEvent('focus', { bubbles: true })); await sleep(500);
        
        const telefone = '1137388145';
        for (const digit of telefone) {
            const cc = digit.charCodeAt(0);
            inputTel.dispatchEvent(new KeyboardEvent('keydown', { key: digit, code: `Digit${digit}`, keyCode: cc, which: cc, bubbles: true, cancelable: true, view: window }));
            await sleep(30);
            inputTel.dispatchEvent(new KeyboardEvent('keypress', { key: digit, code: `Digit${digit}`, keyCode: cc, which: cc, bubbles: true, cancelable: true, view: window }));
            inputTel.dispatchEvent(new Event('input', { bubbles: true }));
            await sleep(30);
            inputTel.dispatchEvent(new KeyboardEvent('keyup', { key: digit, code: `Digit${digit}`, keyCode: cc, which: cc, bubbles: true, cancelable: true, view: window }));
            await sleep(60);
        }
        inputTel.dispatchEvent(new Event('change', { bubbles: true })); await sleep(300);
        r.tel = inputTel.value.length > 4 ? '✅' : '❌';
        console.log(`${r.tel} Telefone: "${inputTel.value}"`);
    }

    // ===================================================================
    // RESUMO
    // ===================================================================
    console.log('\n╔══════════════════════════════════════════════════════════════╗');
    console.log('║ RESUMO                                                      ║');
    console.log('╠══════════════════════════════════════════════════════════════╣');
    console.log(`║ [1] Vara:          ${r.vara||'─'}   [2] Juiz:      ${r.juiz||'─'}   [3] Processo: ${r.processo||'─'} ║`);
    console.log(`║ [4] Prazo:         ${r.prazo||'─'}   [5] CB Mov:    ${r.cbMov||'─'}   [6] CB Apl:   ${r.cbApl||'─'} ║`);
    console.log(`║ [7] CB Cartão:     ${r.cbCart||'─'}   [8] Email:     ${r.email||'─'}   [9] Telefone: ${r.tel||'─'} ║`);
    console.log('╚══════════════════════════════════════════════════════════════╝');
    
    const allOk = Object.values(r).every(v => v === '✅');
    console.log(allOk ? '\n🎉 TODOS OK! Pronto pro simba.js!' : '\n⚠️  Alguns falharam, veja acima.');
};

console.log('\n✅ Test BCB Completo carregado!');
console.log('📌 Execute: testBcbForm()\n');
