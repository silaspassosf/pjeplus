// =============================================================================
// TEST_BCB_FORM.JS - Teste isolado para preenchimento BCB
// =============================================================================
// COMO USAR:
// 1. Abra a página do BCB (https://www3.bcb.gov.br/saj/requisicao-extratos-cadastro)
// 2. Abra o console (F12 → Console)
// 3. Cole TODO este arquivo no console
// 4. Execute: testBcbForm()
// 5. Veja os logs e ajuste delays/seletores conforme necessário
// =============================================================================

window.testBcbForm = async function() {
    console.clear();
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║ INICIANDO TESTE BCB FORM - Velocidade Controlada           ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // 1. TESTAR VARA
    console.log('\n📋 [1] Testando VARA...');
    
    const inputVara = document.querySelector('input.form-control.saj-input-select-form-input');
    if (!inputVara) {
        console.error('❌ VARA input NÃO ENCONTRADO!');
        console.log('   Inputs com form-control:');
        document.querySelectorAll('input.form-control').forEach((el, i) => {
            console.log(`   [${i}]`, el.className, 'value:', el.value);
        });
    } else {
        console.log('✅ Input de Vara encontrado:', inputVara);
        inputVara.focus();
        await sleep(300);
        
        console.log('📝 Digitando "3ª VA"...');
        inputVara.value = '3ª VA';
        inputVara.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(600);
        
        console.log('🔍 Procurando opções do dropdown...');
        const opcoes = document.querySelectorAll('div.saj-input-select-body-options-value');
        console.log(`   Encontradas ${opcoes.length} opção(ões)`);
        
        opcoes.forEach((op, i) => {
            console.log(`   [${i}] "${op.textContent}"`);
        });
        
        const opcaoVara = Array.from(opcoes).find(op => 
            op.textContent.includes('3ª VARA DO TRABALHO DA ZONA SUL')
        );
        
        if (opcaoVara) {
            console.log('✅ Opção correta encontrada:', opcaoVara.textContent);
            console.log('🖱️  Clicando opção...');
            opcaoVara.click();
            await sleep(600);
        } else {
            console.warn('⚠️  Opção não encontrada. Verifique o texto exato.');
        }
    }

    // 2. TESTAR PRAZO
    console.log('\n📋 [2] Testando PRAZO...');
    
    const inputPrazo = document.querySelector('#prazo');
    if (!inputPrazo) {
        console.error('❌ PRAZO input NÃO ENCONTRADO!');
        console.log('   Inputs com type=number:');
        document.querySelectorAll('input[type="number"]').forEach((el, i) => {
            console.log(`   [${i}] id="${el.id}" value="${el.value}"`);
        });
    } else {
        console.log('✅ Input de Prazo encontrado:', inputPrazo);
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

    // 3. TESTAR CHECKBOXES
    console.log('\n📋 [3] Testando CHECKBOXES (Extractos)...');
    
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    console.log(`   Encontrados ${checkboxes.length} checkbox(s):`);
    
    checkboxes.forEach((cb, i) => {
        console.log(`   [${i}] id="${cb.id}" name="${cb.name}" checked=${cb.checked}`);
    });
    
    // Testar checkbox #2
    console.log('\n   Tentando checkbox #2...');
    const cb2 = document.querySelector('input[type="checkbox"]#2');
    if (cb2) {
        console.log('✅ Checkbox #2 encontrado');
        cb2.click();
        cb2.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(400);
        console.log(`   Resultado: checked=${cb2.checked}`);
    } else {
        console.warn('⚠️  Checkbox #2 não encontrado');
    }
    
    // Testar checkbox #3
    await sleep(300);
    console.log('\n   Tentando checkbox #3...');
    const cb3 = document.querySelector('input[type="checkbox"]#3');
    if (cb3) {
        console.log('✅ Checkbox #3 encontrado');
        cb3.click();
        cb3.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(400);
        console.log(`   Resultado: checked=${cb3.checked}`);
    } else {
        console.warn('⚠️  Checkbox #3 não encontrado');
    }
    
    // Testar checkbox #4
    await sleep(300);
    console.log('\n   Tentando checkbox #4...');
    const cb4 = document.querySelector('input[type="checkbox"]#4');
    if (cb4) {
        console.log('✅ Checkbox #4 encontrado');
        cb4.click();
        cb4.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(400);
        console.log(`   Resultado: checked=${cb4.checked}`);
    } else {
        console.warn('⚠️  Checkbox #4 não encontrado');
    }

    // 4. TESTAR EMAIL
    console.log('\n📋 [4] Testando EMAIL...');
    
    const inputEmail = document.querySelector('#email');
    if (!inputEmail) {
        console.error('❌ EMAIL input NÃO ENCONTRADO!');
        console.log('   Inputs de texto disponíveis:');
        document.querySelectorAll('input[type="text"]').forEach((el, i) => {
            console.log(`   [${i}] id="${el.id}" placeholder="${el.placeholder}"`);
        });
    } else {
        console.log('✅ Input de Email encontrado:', inputEmail);
        inputEmail.focus();
        await sleep(300);
        
        console.log('📝 Digitando email...');
        inputEmail.value = 'vtsps03@trt2.jus.br';
        inputEmail.dispatchEvent(new Event('input', { bubbles: true }));
        inputEmail.dispatchEvent(new Event('change', { bubbles: true }));
        inputEmail.blur();
        await sleep(500);
        
        console.log(`✅ Email preenchido: ${inputEmail.value}`);
    }

    // 5. TESTAR TELEFONE
    console.log('\n📋 [5] Testando TELEFONE...');
    
    const inputTel = document.querySelector('#telefone');
    if (!inputTel) {
        console.error('❌ TELEFONE input NÃO ENCONTRADO!');
        console.log('   Inputs com numero-simba:');
        document.querySelectorAll('input.numero-simba').forEach((el, i) => {
            console.log(`   [${i}] id="${el.id}" placeholder="${el.placeholder}"`);
        });
    } else {
        console.log('✅ Input de Telefone encontrado:', inputTel);
        console.log('   Classes:', inputTel.className);
        console.log('   Placeholder:', inputTel.placeholder);
        
        inputTel.focus();
        await sleep(300);
        
        console.log('📝 Digitando telefone (11)3738-8145...');
        inputTel.value = '(11)3738-8145';
        inputTel.dispatchEvent(new Event('input', { bubbles: true }));
        inputTel.dispatchEvent(new Event('change', { bubbles: true }));
        inputTel.blur();
        await sleep(500);
        
        console.log(`✅ Telefone preenchido: ${inputTel.value}`);
    }

    // RESUMO FINAL
    console.log('\n╔════════════════════════════════════════════════════════════╗');
    console.log('║ TESTE CONCLUÍDO                                            ║');
    console.log('╠════════════════════════════════════════════════════════════╣');
    console.log('║ Verifique os campos que funcionaram e os que falharam      ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
};

console.log('\n✅ Test BCB Form carregado!');
console.log('\n📌 Para executar, digite no console:');
console.log('   testBcbForm()\n');
