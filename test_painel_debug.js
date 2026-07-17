// Script de teste para debugar o carregamento do painel
// Para rodar: copie este código no console do navegador no PJe

(function testPainelDebug() {
    console.log('=== TESTE PAINEL DEBUG ===');
    
    // 1. Verificar se PJeState existe
    console.log('1. window.PJeState:', typeof window.PJeState);
    if (window.PJeState) {
        console.log('   - PJeState._iniciado:', window.PJeState._iniciado);
        console.log('   - PJeState.registry:', typeof window.PJeState.registry);
    }
    
    // 2. Verificar se funções de UI existem
    console.log('2. Funções de UI:');
    console.log('   - window.addStyles:', typeof window.addStyles);
    console.log('   - window.showToast:', typeof window.showToast);
    console.log('   - window.criarPainel:', typeof window.criarPainel);
    console.log('   - window.inicializarPainel:', typeof window.inicializarPainel);
    
    // 3. Verificar se funções de módulos existem
    console.log('3. Funções de módulos:');
    console.log('   - window.executarCheck:', typeof window.executarCheck);
    console.log('   - window.executarEdital:', typeof window.executarEdital);
    console.log('   - window.executarSimba:', typeof window.executarSimba);
    console.log('   - window.PjeRegistrarDebito:', typeof window.PjeRegistrarDebito);
    
    // 4. Verificar se estamos na rota correta
    console.log('4. Localização:');
    console.log('   - URL:', window.location.href);
    console.log('   - isDetalhe:', /\/processo\/\d+\/detalhe/.test(window.location.href));
    console.log('   - __pjeToolsLoaded:', window.__pjeToolsLoaded);
    
    // 5. Tentar executar inicializarPainel manualmente
    console.log('5. Tentando executar inicializarPainel...');
    if (typeof window.inicializarPainel === 'function') {
        try {
            window.inicializarPainel();
            console.log('   ✓ inicializarPainel executado com sucesso');
        } catch (e) {
            console.error('   ✗ Erro:', e.message, e.stack);
        }
    } else {
        console.log('   ✗ inicializarPainel não é uma função');
    }
    
    // 6. Verificar se há erros no console da página
    console.log('6. Procure por erros vermelho no console acima');
    
    console.log('=== FIM DO TESTE ===');
})();
