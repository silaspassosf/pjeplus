// cit.js — Teste isolado e otimizado de verificação de domicílio eletrônico
(function() {
    // 1. Clicar no link de detalhes do processo
    const linkDetalhes = document.querySelector('a[aria-label^="Detalhes do Processo"]');
    if (!linkDetalhes) {
        console.error('Botão "Detalhes do Processo" não encontrado.');
        return;
    }
    
    console.log('A abrir detalhes do processo...');
    linkDetalhes.click();

    // 2. Aguardar a abertura do modal (Verificação a cada 300ms)
    let tentativas = 0;
    const tempoMaximo = 30; // 30 tentativas x 300ms = 9 segundos de limite

    const verificador = setInterval(() => {
        tentativas++;
        const modal = document.querySelector('mat-dialog-container');
        
        // Se o modal ainda não carregou, continuamos a tentar
        if (!modal) {
            if (tentativas >= tempoMaximo) {
                clearInterval(verificador);
                console.error('Tempo esgotado: O modal não abriu.');
            }
            return;
        }

        // Se encontrou o modal, paramos o temporizador
        clearInterval(verificador);
        console.log('Modal aberto. A analisar o Polo Passivo...');

        // 3. Encontrar o Polo Passivo e analisar as partes
        const poloPassivo = document.querySelector('[aria-label="Polo Passivo"]');
        
        if (!poloPassivo) {
            console.warn('Polo Passivo não encontrado no ecrã.');
        } else {
            // No HTML do PJe, cada parte fica isolada dentro de um <li> com a classe "partes-corpo"
            const partes = poloPassivo.querySelectorAll('li.partes-corpo');
            let comDomicilio = 0;
            let semDomicilio = 0;

            // Percorremos cada parte encontrada
            partes.forEach((parte, index) => {
                // Procuramos qualquer imagem que indique o domicílio dentro DESTA parte específica
                const iconeDomicilio = parte.querySelector('img[src*="domicilio"], img[alt*="domicilio"], img[alt*="Eletrônico"]');
                
                // Vamos extrair o nome da parte apenas para deixar o log mais amigável
                const nomeElemento = parte.querySelector('pje-nome-parte span.upperCase');
                const nomeParte = nomeElemento ? nomeElemento.textContent.trim() : `Parte ${index + 1}`;

                if (iconeDomicilio) {
                    comDomicilio++;
                    console.log(`✅ COM domicílio: ${nomeParte}`);
                } else {
                    semDomicilio++;
                    console.log(`❌ SEM domicílio: ${nomeParte}`);
                }
            });

            console.log(`📊 RESULTADO FINAL: ${partes.length} parte(s) analisada(s). ${comDomicilio} COM domicílio, ${semDomicilio} SEM domicílio.`);
        }

        // 4. Fechar o modal de forma elegante
        setTimeout(() => {
            const botaoFechar = modal.querySelector('[mat-dialog-close], button[aria-label="Fechar"], .mat-dialog-close');
            if (botaoFechar) {
                botaoFechar.click();
                console.log('Modal fechado com sucesso.');
            } else {
                // Fallback: simula a tecla ESC
                document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
                console.log('Modal fechado via tecla Escape.');
            }
        }, 500); // Aguarda meio segundo antes de fechar para garantir que a interface responde bem

    }, 300); // Frequência de 300 milissegundos
})();