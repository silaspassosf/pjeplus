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

    // ──────────────────────────────────────────────────────────────────────
    // 1. TESTAR VARA (Input com dropdown Angular)
    // ──────────────────────────────────────────────────────────────────────
    console.log('\n📋 [1] Testando VARA...');
    
    const inputVara = document.querySelector('input.form-control.saj-input-select-form-input');
    if (!inputVara) {
        console.error('❌ VARA input NÃO ENCONTRADO!');
        console.log('   Seletores disponíveis com "input" e "form-control":');
        document.querySelectorAll('input.form-control').forEach((el, i) => {
            console.log(`   [${i}]`, el.className, el.value);
        });
    } else {
        console.log('✅ Input de Vara encontrado:', inputVara);
        console.log('   Classes:', inputVara.className);
        
        inputVara.focus();
        await sleep(300);
        
        console.log('📝 Digitando "3ª VA"...');
        inputVara.value = '3ª VA';
        inputVara.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(600);
        
        // Procurar opção do dropdown
        console.log('🔍 Procurando opções do dropdown...');
        const opcoes = document.querySelectorAll('div.saj-input-select-body-options-value');
        console.log(`   Encontradas ${opcoes.length} opção(ões)`);
        
        opcoes.forEach((op, i) => {
            console.log(`   [${i}] "${op.textContent}"`);
        });
        
        const opcaoVara = Array.from(opcoes).find(op => 
            op.textContent.includes('3ª VARA DO TRABALHO DA ZONA SUL')
        );
        
        if (opcaoVara) {\n            console.log('✅ Opção correta encontrada:', opcaoVara.textContent);
            console.log('🖱️  Clicando opção...');
            opcaoVara.click();
            await sleep(600);
        } else {
            console.warn('⚠️  Opção não encontrada. Verifique o texto exato.');
        }\n    }\n\n    // ──────────────────────────────────────────────────────────────────────\n    // 2. TESTAR PRAZO (Input número)\n    // ──────────────────────────────────────────────────────────────────────\n    console.log('\\n📋 [2] Testando PRAZO...');\n    \n    const inputPrazo = document.querySelector('#prazo');\n    if (!inputPrazo) {\n        console.error('❌ PRAZO input NÃO ENCONTRADO!');\n        console.log('   Inputs com ID disponíveis:');\n        document.querySelectorAll('input[type=\"number\"]').forEach((el, i) => {\n            console.log(`   [${i}] id=\"${el.id}\" value=\"${el.value}\"`);\n        });\n    } else {\n        console.log('✅ Input de Prazo encontrado:', inputPrazo);\n        inputPrazo.focus();\n        await sleep(300);\n        \n        console.log('📝 Digitando \"60\"...');\n        inputPrazo.value = '60';\n        inputPrazo.dispatchEvent(new Event('input', { bubbles: true }));\n        inputPrazo.dispatchEvent(new Event('change', { bubbles: true }));\n        inputPrazo.blur();\n        await sleep(500);\n        \n        console.log(`✅ Prazo preenchido: ${inputPrazo.value}`);\n    }\n\n    // ──────────────────────────────────────────────────────────────────────\n    // 3. TESTAR CHECKBOXES (Extractos)\n    // ──────────────────────────────────────────────────────────────────────\n    console.log('\\n📋 [3] Testando CHECKBOXES (Extractos)...');\n    \n    const checkboxes = document.querySelectorAll('input[type=\"checkbox\"]');\n    console.log(`   Encontrados ${checkboxes.length} checkbox(s):`);\n    \n    checkboxes.forEach((cb, i) => {\n        console.log(`   [${i}] id=\"${cb.id}\" name=\"${cb.name}\" checked=${cb.checked}`);\n    });\n    \n    // Tentar checkbox #2\n    const cb2 = document.querySelector('input[type=\"checkbox\"]#2');\n    if (cb2) {\n        console.log('\\n✅ Checkbox #2 encontrado');\n        console.log('   Clicando...');\n        cb2.click();\n        cb2.dispatchEvent(new Event('change', { bubbles: true }));\n        await sleep(400);\n        console.log(`   Resultado: checked=${cb2.checked}`);\n    } else {\n        console.warn('⚠️  Checkbox #2 NÃO encontrado. Buscando por name...');\n        const cb2ByName = document.querySelector('input[name=\"defaultExampleRadios\"]#2');\n        if (cb2ByName) {\n            console.log('✅ Encontrado por nome! Clicando...');\n            cb2ByName.click();\n            await sleep(400);\n            console.log(`   Resultado: checked=${cb2ByName.checked}`);\n        } else {\n            console.error('❌ Checkbox #2 não encontrado por seletor nenhum!');\n        }\n    }\n    \n    // Tentar checkbox #3\n    await sleep(300);\n    const cb3 = document.querySelector('input[type=\"checkbox\"]#3');\n    if (cb3) {\n        console.log('\\n✅ Checkbox #3 encontrado');\n        cb3.click();\n        cb3.dispatchEvent(new Event('change', { bubbles: true }));\n        await sleep(400);\n        console.log(`   Resultado: checked=${cb3.checked}`);\n    } else {\n        console.warn('⚠️  Checkbox #3 não encontrado');\n    }\n    \n    // Tentar checkbox #4\n    await sleep(300);\n    const cb4 = document.querySelector('input[type=\"checkbox\"]#4');\n    if (cb4) {\n        console.log('\\n✅ Checkbox #4 encontrado');\n        cb4.click();\n        cb4.dispatchEvent(new Event('change', { bubbles: true }));\n        await sleep(400);\n        console.log(`   Resultado: checked=${cb4.checked}`);\n    } else {\n        console.warn('⚠️  Checkbox #4 não encontrado');\n    }\n\n    // ──────────────────────────────────────────────────────────────────────\n    // 4. TESTAR EMAIL\n    // ──────────────────────────────────────────────────────────────────────\n    console.log('\\n📋 [4] Testando EMAIL...');\n    \n    const inputEmail = document.querySelector('#email');\n    if (!inputEmail) {\n        console.error('❌ EMAIL input NÃO ENCONTRADO!');\n        console.log('   Inputs de texto disponíveis:');\n        document.querySelectorAll('input[type=\"text\"]').forEach((el, i) => {\n            console.log(`   [${i}] id=\"${el.id}\" placeholder=\"${el.placeholder}\"`);\n        });\n    } else {\n        console.log('✅ Input de Email encontrado:', inputEmail);\n        inputEmail.focus();\n        await sleep(300);\n        \n        console.log('📝 Digitando email...');\n        inputEmail.value = 'vtsps03@trt2.jus.br';\n        inputEmail.dispatchEvent(new Event('input', { bubbles: true }));\n        inputEmail.dispatchEvent(new Event('change', { bubbles: true }));\n        inputEmail.blur();\n        await sleep(500);\n        \n        console.log(`✅ Email preenchido: ${inputEmail.value}`);\n    }\n\n    // ──────────────────────────────────────────────────────────────────────\n    // 5. TESTAR TELEFONE\n    // ──────────────────────────────────────────────────────────────────────\n    console.log('\\n📋 [5] Testando TELEFONE...');\n    \n    const inputTel = document.querySelector('#telefone');\n    if (!inputTel) {\n        console.error('❌ TELEFONE input NÃO ENCONTRADO!');\n        console.log('   Inputs com \"numero-simba\" disponíveis:');\n        document.querySelectorAll('input.numero-simba').forEach((el, i) => {\n            console.log(`   [${i}] id=\"${el.id}\" placeholder=\"${el.placeholder}\"`);\n        });\n    } else {\n        console.log('✅ Input de Telefone encontrado:', inputTel);\n        console.log('   Classes:', inputTel.className);\n        console.log('   Placeholder:', inputTel.placeholder);\n        \n        inputTel.focus();\n        await sleep(300);\n        \n        console.log('📝 Digitando telefone (11)3738-8145...');\n        inputTel.value = '(11)3738-8145';\n        inputTel.dispatchEvent(new Event('input', { bubbles: true }));\n        inputTel.dispatchEvent(new Event('change', { bubbles: true }));\n        inputTel.blur();\n        await sleep(500);\n        \n        console.log(`✅ Telefone preenchido: ${inputTel.value}`);\n    }\n\n    // ──────────────────────────────────────────────────────────────────────\n    // RESUMO FINAL\n    // ──────────────────────────────────────────────────────────────────────\n    console.log('\\n╔════════════════════════════════════════════════════════════╗');\n    console.log('║ TESTE CONCLUÍDO                                            ║');\n    console.log('╠════════════════════════════════════════════════════════════╣');\n    console.log('║ Verifique acima quais campos funcionaram e quais falharam  ║');\n    console.log('║ Copie os seletores corretos para o script                 ║');\n    console.log('╚════════════════════════════════════════════════════════════╝');\n};\n\nconsole.log('\\n✅ Test BCB Form carregado!');\nconsole.log('\\n📌 Para executar, digite no console:');\nconsole.log('   testBcbForm()\\n');\n