// =============================================================================
// TESTE TELEFONE ISOLADO - Sem tocar em nenhum outro campo
// =============================================================================

window.testTel = async function() {
    console.clear();
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║ TESTE TELEFONE ISOLADO - Nenhum outro campo é tocado      ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    
    const inputTel = document.querySelector('#telefone');
    if (!inputTel) {
        console.error('❌ #telefone não encontrado!');
        return;
    }
    
    console.log('\n1️⃣ Estado inicial do campo:');
    console.log(`   value: "${inputTel.value}"`);
    console.log(`   disabled: ${inputTel.disabled}`);
    console.log(`   readOnly: ${inputTel.readOnly}`);
    console.log(`   class: ${inputTel.className}`);
    console.log(`   offsetParent: ${inputTel.offsetParent?.tagName || 'null'}`);
    
    // Verificar se está visível
    const rect = inputTel.getBoundingClientRect();
    console.log(`   posição: (${rect.x}, ${rect.y}) ${rect.width}x${rect.height}`);
    console.log(`   visível na viewport: ${rect.top < window.innerHeight && rect.bottom > 0}`);
    
    // Verificar overlays
    const topElement = document.elementFromPoint(rect.x + rect.width/2, rect.y + rect.height/2);
    console.log(`   elemento no centro: ${topElement?.tagName}#${topElement?.id || ''}`);
    console.log(`   é o próprio input? ${topElement === inputTel}`);
    
    if (topElement !== inputTel) {
        console.warn('⚠️ ALGO ESTÁ POR CIMA DO INPUT! Elemento overlay:', topElement);
    }
    
    // Scroll e tentar focar
    console.log('\n2️⃣ Scroll + Focus + Click...');
    inputTel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await sleep(800);
    
    // Tentar focus primeiro
    console.log('   focus()...');
    inputTel.focus();
    await sleep(500);
    console.log(`   activeElement: ${document.activeElement?.id || 'nenhum'}`);
    console.log(`   value após focus: "${inputTel.value}"`);
    
    // Se focus não mostrou máscara, tentar click
    console.log('   click()...');
    inputTel.click();
    await sleep(500);
    console.log(`   activeElement: ${document.activeElement?.id || 'nenhum'}`);
    console.log(`   value após click: "${inputTel.value}"`);
    
    // Tentar dar blur e focus de novo (toggle)
    console.log('   blur + refocus...');
    inputTel.blur();
    await sleep(300);
    inputTel.focus();
    await sleep(500);
    console.log(`   value após refocus: "${inputTel.value}"`);
    
    // ATIVAR A MÁSCARA via FocusEvent (não focus()!)
    console.log('   🔑 FocusEvent nativo...');
    inputTel.dispatchEvent(new FocusEvent('focus', { bubbles: true }));
    await sleep(500);
    console.log(`   ✅ Máscara ativa! value: "${inputTel.value}"`);
    
    // Agora digitar dígito por dígito SEM mexer no value!
    console.log('\n3️⃣ Digitando (deixando a máscara processar)...');
    const telefone = '11373881451';
    
    for (let i = 0; i < telefone.length; i++) {
        const digit = telefone[i];
        const charCode = digit.charCodeAt(0);
        
        // NÃO setar inputTel.value! Deixar a máscara fazer isso.
        inputTel.dispatchEvent(new KeyboardEvent('keydown', {
            key: digit,
            code: `Digit${digit}`,
            keyCode: charCode,
            which: charCode,
            bubbles: true,
            cancelable: true,
            view: window
        }));
        
        await sleep(30);
        
        inputTel.dispatchEvent(new KeyboardEvent('keypress', {
            key: digit,
            code: `Digit${digit}`,
            keyCode: charCode,
            which: charCode,
            bubbles: true,
            cancelable: true,
            view: window
        }));
        
        inputTel.dispatchEvent(new Event('input', { bubbles: true }));
        
        await sleep(30);
        
        inputTel.dispatchEvent(new KeyboardEvent('keyup', {
            key: digit,
            code: `Digit${digit}`,
            keyCode: charCode,
            which: charCode,
            bubbles: true,
            cancelable: true,
            view: window
        }));
        
        console.log(`   [${i+1}/${telefone.length}] "${digit}" → value: "${inputTel.value}"`);
        await sleep(80);
    }
    
    inputTel.dispatchEvent(new Event('change', { bubbles: true }));
    await sleep(500);
    
    console.log('\n4️⃣ Resultado final:');
    console.log(`   value: "${inputTel.value}"`);
    console.log(`   class: ${inputTel.className}`);
    console.log(`   Preenchido? ${inputTel.value.length > 4 ? 'SIM ✅' : 'NÃO ❌'}`);
    
    if (!inputTel.value) {
        console.log('\n💡 DIAGNÓSTICO: Algo impede o input de receber foco/clique.');
        console.log('   Possíveis causas:');
        console.log('   1. Overlay (elemento por cima)');
        console.log('   2. Input em tab não ativa');
        console.log('   3. Angular state travado');
        console.log('   4. Máscara precisa de evento específico');
    }
};

console.log('\n✅ Test Tel Isolado carregado!');
console.log('📌 Execute: testTel()\n');
