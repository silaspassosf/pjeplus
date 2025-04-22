// ==UserScript==
// @name         Análise Automática PJe TRT2
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Cria botão para analisar o primeiro processo da lista e abrir detalhes, deixando a linha amarela; adiciona botão de prazo na aba de detalhes.
// @author       Você
// @match        https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    const wait = ms => new Promise(r => setTimeout(r, ms));
    const $ = s => document.querySelector(s);
    const $$ = s => [...document.querySelectorAll(s)];

    function criarBotaoAnalise() {
        if ($('#btnAnaliseProcesso')) return;
        const btn = document.createElement('button');
        btn.id = 'btnAnaliseProcesso';
        btn.textContent = 'Analisar 1º Processo';
        Object.assign(btn.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            zIndex: 9999,
            padding: '10px 15px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            fontWeight: 'bold'
        });
        btn.onclick = async () => {
            btn.disabled = true;
            btn.textContent = 'Processando...';
            try {
                const linhas = $$('tr.cdk-drag');
                let selecionado = false;
                for (const row of linhas) {
                    // Critério: primeira linha visível
                    const checkbox = row.querySelector('mat-checkbox input[type=checkbox]');
                    if (checkbox && !checkbox.disabled) {
                        row.style.backgroundColor = '#ffffaa';
                        const btnDetalhes = row.querySelector('button[aria-label="Detalhes do Processo"], button[mattooltip="Detalhes do Processo"]') || row.querySelector('button');
                        if (btnDetalhes) {
                            btnDetalhes.click();
                            selecionado = true;
                            break;
                        }
                    }
                }
                if (!selecionado) {
                    alert('Nenhum processo encontrado para análise.');
                }
            } catch (e) {
                alert('Erro ao iniciar análise: ' + e.message);
            }
            btn.disabled = false;
            btn.textContent = 'Analisar 1º Processo';
        };
        document.body.appendChild(btn);
    }

    function criarBotaoPrazoDetalhe() {
        if ($('#btnPrazoAnalise')) return;
        const btn = document.createElement('button');
        btn.id = 'btnPrazoAnalise';
        btn.textContent = 'Prazo';
        Object.assign(btn.style, {
            position: 'fixed',
            top: '60px',
            right: '20px',
            zIndex: 9999,
            padding: '8px 12px',
            backgroundColor: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontWeight: 'bold',
            boxShadow: '0 2px 5px rgba(0,0,0,0.2)'
        });
        btn.onclick = () => {
            alert('Ação de prazo implementável aqui.');
        };
        document.body.appendChild(btn);
    }

    if (location.href.includes('/painel/global/8/lista-processos')) {
        criarBotaoAnalise();
        // Observa mutações para recriar o botão se necessário
        const observer = new MutationObserver(() => {
            if (!$('#btnAnaliseProcesso')) criarBotaoAnalise();
        });
        observer.observe(document.body, { childList: true, subtree: true });
        setInterval(() => {
            if (!$('#btnAnaliseProcesso')) criarBotaoAnalise();
        }, 2000);
    } else if (/\/processo\/.+\/detalhe/.test(location.href)) {
        criarBotaoPrazoDetalhe();
    }
})();
