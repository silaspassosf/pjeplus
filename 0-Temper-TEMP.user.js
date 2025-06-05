// ==UserScript==
// @name         0-Temper Robusto
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Automação robusta para PJe - Sistema de vínculos sequenciais baseado em fluxos.py
// @author       You
// @match        https://pje.trt2.jus.br/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    // Sistema de armazenamento global dos vínculos (equivalente ao browser storage do Python)
    if (!window.vinculoStorage) {
        window.vinculoStorage = {
            tempBt: [],                    // Equivalente ao tempBt do JS
            tempAAEspecial: [],           // Equivalente ao tempAAEspecial do JS
            AALote: '',                   // Equivalente ao AALote do JS
            processandoVinculos: false,   // Flag para controle de processamento
            filaExecucao: [],            // Fila para processamento sequencial
            maxTentativas: 3,            // Máximo de tentativas por ação
            delayEntreAcoes: 1500        // Delay padrão entre ações
        };
    }

    // Teste se o script está carregando
    console.log('[0-TEMPER] Script carregado na URL:', window.location.href);

    // Remove qualquer instância anterior da interface
    var old = document.getElementById('maisPjeBox');
    if (old) old.remove();

    // Criar interface básica para teste
    function criarInterface() {
        var box = document.createElement('div');
        box.id = 'maisPjeBox';
        box.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            width: 300px;
            height: 400px;
            background: white;
            border: 2px solid #007acc;
            border-radius: 8px;
            z-index: 10000;
            padding: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        `;
        
        box.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 10px; color: #007acc;">
                0-Temper Robusto - TRT2
            </div>
            <div style="font-size: 12px; color: #666;">
                Script carregado com sucesso!<br>
                URL: ${window.location.href}
            </div>
        `;
        
        document.body.appendChild(box);
        console.log('[0-TEMPER] Interface criada');
    }

    // Aguardar DOM estar pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', criarInterface);
    } else {
        criarInterface();
    }

})();
