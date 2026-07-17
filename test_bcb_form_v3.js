// =============================================================================
// TEST_BCB_FORM_V3 - Corrigido com seletores ajustados
// =============================================================================

window.testBcbForm = async function() {
    console.clear();
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║ TESTE BCB v3 - Seletores Corrigidos                        ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // 1. TESTAR VARA - CORRIGIDO
    console.log('\n📋 [1] Testando VARA (CORRIGIDO)...');
    
    const inputVara = document.querySelector('input.form-control.saj-input-select-form-input');
    if (inputVara) {
        console.log('✅ Input de Vara encontrado');
        inputVara.focus();
        await sleep(300);
        
        console.log('📝 Digitando "3ª VA"...');
        inputVara.value = '3ª VA';
        inputVara.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(600);
        
        console.log('🔍 Procurando opções do dropdown (com filtro correto)...');
        const opcoes = document.querySelectorAll('div.saj-input-select-body-options-value');
        
        // NOVO: Buscar EXATAMENTE "3ª VARA DO TRABALHO DA ZONA SUL" (sem 13ª)
        const opcaoVara = Array.from(opcoes).find(op => {
            const texto = op.textContent.trim();
            // Procura por "3ª" no início (não "13ª", "23ª", etc)
            return texto.startsWith('3ª VARA DO TRABALHO DA ZONA SUL DE SÃO PAULO');
        });
        
        if (opcaoVara) {
            console.log('✅ Opção CORRETA encontrada:', opcaoVara.textContent.trim());
            console.log('🖱️  Clicando opção...');
            opcaoVara.click();
            await sleep(600);
        } else {
            console.warn('⚠️  Opção não encontrada.');
        }
    }

    // 2. TESTAR PRAZO
    console.log('\n📋 [2] Testando PRAZO...');
    const inputPrazo = document.querySelector('#prazo');
    if (inputPrazo) {
        console.log('✅ Input de Prazo encontrado');
        inputPrazo.focus();
        await sleep(300);
        
        console.log('📝 Digitando "60"...');
        inputPrazo.value = '60';
        inputPrazo.dispatchEvent(new Event('input', { bubbles: true }));
        inputPrazo.dispatchEvent(new Event('change', { bubbles: true }));
        inputPrazo.blur();
        await sleep(500);
        
        console.log(`✅ Prazo preenchido: ${inputPrazo.value}`);
    }

    // 3. TESTAR CHECKBOXES - CORRIGIDO COM SELETORES DE ID
    console.log('\n📋 [3] Testando CHECKBOXES (CORRIGIDO)...');
    
    // Checkbox #2 (Movimentação)
    console.log('\n   Tentando checkbox #2 (Movimentação)...');
    const cb2 = document.querySelector('input#2');
    if (cb2) {
        console.log('✅ Checkbox #2 encontrado:', cb2);
        cb2.click();
        cb2.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(400);
        console.log(`   ✅ Checkbox #2 MARCADO: checked=${cb2.checked}`);
    } else {
        console.warn('❌ Checkbox #2 não encontrado com seletor input#2');
        console.log('   Tentando alternativas...');
        const alt = document.querySelector('input[id="2"]');
        if (alt) {
            console.log('   ✅ Encontrado com input[id="2"]');
            alt.click();
            await sleep(400);
            console.log(`   Resultado: checked=${alt.checked}`);
        }
    }
    
    // Checkbox #3 (Aplicações Financeiras)
    await sleep(300);
    console.log('\n   Tentando checkbox #3 (Aplicações Financeiras)...');
    const cb3 = document.querySelector('input#3');
    if (cb3) {
        console.log('✅ Checkbox #3 encontrado');
        cb3.click();
        cb3.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(400);
        console.log(`   ✅ Checkbox #3 MARCADO: checked=${cb3.checked}`);
    } else {
        console.warn('❌ Checkbox #3 não encontrado');
    }
    
    // Checkbox #4 (Cartão de Crédito)
    await sleep(300);
    console.log('\n   Tentando checkbox #4 (Cartão de Crédito)...');
    const cb4 = document.querySelector('input#4');
    if (cb4) {
        console.log('✅ Checkbox #4 encontrado');
        cb4.click();
        cb4.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(400);
        console.log(`   ✅ Checkbox #4 MARCADO: checked=${cb4.checked}`);
    } else {
        console.warn('❌ Checkbox #4 não encontrado');
    }

    // 4. TESTAR EMAIL
    console.log('\n📋 [4] Testando EMAIL...');
    const inputEmail = document.querySelector('#email');
    if (inputEmail) {
        console.log('✅ Input de Email encontrado');
        inputEmail.focus();
        await sleep(300);
        
        console.log('📝 Digitando email...');
        inputEmail.value = 'vtsps03@trt2.jus.br';
        inputEmail.dispatchEvent(new Event('input', { bubbles: true }));
        inputEmail.dispatchEvent(new Event('change', { bubbles: true }));
        inputEmail.blur();
        await sleep(500);
        
        console.log(`✅ Email preenchido: ${inputEmail.value}`);
    } else {
        console.error('❌ EMAIL não encontrado!');
    }

    // 5. TESTAR TELEFONE
    console.log('\n📋 [5] Testando TELEFONE...');
    const inputTel = document.querySelector('#telefone');
    if (inputTel) {
        console.log('✅ Input de Telefone encontrado');
        inputTel.focus();
        await sleep(300);
        
        console.log('📝 Digitando telefone...');
        inputTel.value = '(11)3738-8145';
        inputTel.dispatchEvent(new Event('input', { bubbles: true }));
        inputTel.dispatchEvent(new Event('change', { bubbles: true }));
        inputTel.blur();
        await sleep(500);
        
        console.log(`✅ Telefone preenchido: ${inputTel.value}`);
    } else {
        console.error('❌ TELEFONE não encontrado!');
    }

    // RESUMO FINAL
    console.log('\n╔════════════════════════════════════════════════════════════╗');
    console.log('║ TESTE CONCLUÍDO V3                                         ║');
    console.log('╠════════════════════════════════════════════════════════════╣');
    console.log('║ Verifique acima os resultados                             ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
};

console.log('\n✅ Test BCB Form v3 carregado!');
console.log('\n📌 Para executar, digite:');
console.log('   testBcbForm()\n');
