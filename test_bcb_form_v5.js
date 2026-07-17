// =============================================================================
// TEST_BCB_FORM_V5 - Debug dos Labels e Telefone com Máscara
// =============================================================================

window.testBcbForm = async function() {
    console.clear();
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║ TESTE BCB v5 - Debug Labels + Telefone Máscara             ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // 1. TESTAR VARA
    console.log('\n📋 [1] Testando VARA...');
    
    const inputVara = document.querySelector('input.form-control.saj-input-select-form-input');
    if (inputVara) {
        console.log('✅ Input de Vara encontrado');
        inputVara.focus();
        await sleep(300);
        
        console.log('📝 Digitando "3ª VA"...');
        inputVara.value = '3ª VA';
        inputVara.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(600);
        
        const opcoes = document.querySelectorAll('div.saj-input-select-body-options-value');
        const opcaoVara = Array.from(opcoes).find(op => {
            const texto = op.textContent.trim();
            return texto.startsWith('3ª VARA DO TRABALHO DA ZONA SUL DE SÃO PAULO');
        });
        
        if (opcaoVara) {
            console.log('✅ Opção CORRETA encontrada:', opcaoVara.textContent.trim());
            opcaoVara.click();
            await sleep(600);
        }
    }

    // 2. TESTAR PRAZO
    console.log('\n📋 [2] Testando PRAZO...');
    const inputPrazo = document.querySelector('#prazo');
    if (inputPrazo) {
        console.log('✅ Input de Prazo encontrado');
        inputPrazo.focus();
        await sleep(300);
        inputPrazo.value = '60';
        inputPrazo.dispatchEvent(new Event('input', { bubbles: true }));
        inputPrazo.dispatchEvent(new Event('change', { bubbles: true }));
        inputPrazo.blur();
        await sleep(500);
        console.log(`✅ Prazo preenchido: ${inputPrazo.value}`);
    }

    // 3. TESTAR CHECKBOXES - DEBUG COMPLETO
    console.log('\n📋 [3] Testando CHECKBOXES - Debug Completo...');
    
    const allBTags = document.querySelectorAll('b');
    console.log(`\n📊 LISTANDO TODOS OS <b> TAGS (total: ${allBTags.length}):`);
    Array.from(allBTags).forEach((b, i) => {
        console.log(`   [${i}] ${b.textContent.trim()}`);
    });
    
    // Procurar exatos
    const checkboxLabels = [
        { search: 'Extrato de movimentação - Carta-Circular 3454 (Simba)', label: 'Movimentação' },
        { search: 'Extrato de aplicações financeiras', label: 'Aplicações Financeiras' },
        { search: 'Fatura de cartão de crédito', label: 'Cartão de Crédito' }
    ];
    
    for (const item of checkboxLabels) {
        console.log(`\n   🔍 Procurando: "${item.search}"`);
        
        const labelB = Array.from(allBTags).find(b => 
            b.textContent.includes(item.search) || b.textContent.includes(item.label)
        );
        
        if (labelB) {
            console.log(`   ✅ Label "${item.label}" encontrado: ${labelB.textContent.trim()}`);
            console.log('   🖱️  Clicando no label...');
            labelB.click();
            await sleep(400);
            
            const parent = labelB.closest('label') || labelB.parentElement;
            const checkbox = parent?.querySelector('input[type="checkbox"]');
            if (checkbox) {
                console.log(`   ✅ Checkbox MARCADO: checked=${checkbox.checked}`);
            }
        } else {
            console.warn(`   ❌ Label NÃO encontrado com busca: "${item.search}"`);
            console.log(`   💡 Tente variações do texto no console`);
        }
    }

    // 4. TESTAR EMAIL
    console.log('\n📋 [4] Testando EMAIL...');
    const inputEmail = document.querySelector('#email');
    if (inputEmail) {
        console.log('✅ Input de Email encontrado');
        inputEmail.focus();
        await sleep(300);
        inputEmail.value = 'vtsps03@trt2.jus.br';
        inputEmail.dispatchEvent(new Event('input', { bubbles: true }));
        inputEmail.dispatchEvent(new Event('change', { bubbles: true }));
        inputEmail.blur();
        await sleep(500);
        console.log(`✅ Email preenchido: ${inputEmail.value}`);
    }

    // 5. TESTAR TELEFONE - COM MÁSCARA (digitar número por número)
    console.log('\n📋 [5] Testando TELEFONE com MÁSCARA...');
    const inputTel = document.querySelector('#telefone');
    if (inputTel) {
        console.log('✅ Input de Telefone encontrado');
        console.log(`   Máscara atual: ${inputTel.value || '(vazio)'}`);
        
        inputTel.focus();
        await sleep(300);
        
        // Limpar primeiro
        inputTel.value = '';
        inputTel.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(200);
        
        // Digitar número por número
        const telefone = '11373881451'; // Apenas dígitos
        console.log(`📝 Digitando telefone: ${telefone}`);
        
        for (let digit of telefone) {
            inputTel.value += digit;
            inputTel.dispatchEvent(new Event('input', { bubbles: true }));
            inputTel.dispatchEvent(new Event('keydown', { bubbles: true }));
            inputTel.dispatchEvent(new Event('keyup', { bubbles: true }));
            await sleep(100);
        }
        
        inputTel.dispatchEvent(new Event('change', { bubbles: true }));
        inputTel.blur();
        await sleep(500);
        
        console.log(`✅ Telefone preenchido: ${inputTel.value}`);
    } else {
        console.error('❌ TELEFONE não encontrado!');
    }

    // RESUMO FINAL
    console.log('\n╔════════════════════════════════════════════════════════════╗');
    console.log('║ TESTE CONCLUÍDO V5                                         ║');
    console.log('╠════════════════════════════════════════════════════════════╣');
    console.log('║ ✅ Vara, Prazo, Email, Telefone testados                  ║');
    console.log('║ ⚠️  Checkboxes: veja listagem de <b> tags acima             ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
};

console.log('\n✅ Test BCB Form v5 carregado!');
console.log('\n📌 Para executar, digite:');
console.log('   testBcbForm()\n');
