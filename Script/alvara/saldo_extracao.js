// saldo_extracao.js — Botão "Extrair saldo" no Alvará Eletrônico (TRT2)
// =====================================================================
// Injeta, na página de busca de contas do Alvará Eletrônico, um botão
// fixo na parte de baixo da janela que extrai o saldo disponível das
// contas judiciais e copia o bloco HTML pronto para colar no editor
// (mesma ação do bookmarklet "Extrair saldo", portada 1:1).
//
// Página-alvo:
//   https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar
(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    const URL_ALVO = '/portaltrtsp/pages/movimentacao/conta/buscar';
    const BTN_ID = 'btnAlvaraExtrairSaldo';

    // ── Helpers monetários (idênticos ao bookmarklet) ──
    function brlToFloat(txt) {
        if (!txt) return 0;
        const n = txt.replace(/R\$/g, '').replace(/\./g, '').replace(',', '.').replace(/\s/g, '').trim();
        const v = parseFloat(n);
        return Number.isFinite(v) ? v : 0;
    }

    function toBRL(n) {
        try {
            return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } catch (e) {
            return `R$ ${(Number(n) || 0).toFixed(2).replace('.', ',')}`;
        }
    }

    // ── Feedback visual ──
    function showNotification() {
        const notification = document.createElement('div');
        notification.textContent = 'Conteúdo copiado!';
        notification.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#4CAF50;color:white;padding:10px 20px;border-radius:5px;font-size:14px;font-weight:bold;z-index:99999;box-shadow:0 2px 10px rgba(0,0,0,0.3);';
        document.body.appendChild(notification);
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 2000);
    }

    // ── Cópia do HTML para o clipboard (execCommand, como no bookmarklet) ──
    function copyToClipboard(content) {
        const container = document.createElement('div');
        container.innerHTML = content;
        container.style.position = 'absolute';
        container.style.left = '-9999px';
        document.body.appendChild(container);
        const range = document.createRange();
        range.selectNodeContents(container);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        try {
            const success = document.execCommand('copy');
            if (success) {
                document.body.removeChild(container);
                selection.removeAllRanges();
                showNotification();
                return true;
            } else {
                throw new Error('Falha no execCommand');
            }
        } catch (err) {
            if (document.body.contains(container)) {
                document.body.removeChild(container);
            }
            console.error('Erro ao copiar:', err);
            alert('Erro ao copiar. Dados exibidos no console.');
            return false;
        }
    }

    // ── Extração dos dados (idêntica ao bookmarklet) ──
    function extrairDados() {
        const tabelaContas = document.getElementById('table_contas');
        if (!tabelaContas) {
            alert('Tabela de contas não encontrada!');
            return;
        }
        const linhasContas = tabelaContas.querySelectorAll('tr[id^="linhaConta_"]');
        const resultados = [];
        linhasContas.forEach(linha => {
            const idConta = linha.id.replace('linhaConta_', '');
            const numeroConta = linha.querySelector('td:nth-child(2)')?.textContent?.trim() || '';
            const celulaValorDisponivel = linha.querySelector('td[id^="td_saldo_corrigido_conta_"]');
            const valorDisponivelTxt = celulaValorDisponivel?.textContent?.trim() || '';
            const valorDisponivel = brlToFloat(valorDisponivelTxt);
            if (valorDisponivel <= 0) return;

            const tabelaParcelas = document.getElementById(`tabela_parcelas_conta_${idConta}`);
            let depositos = [];
            if (tabelaParcelas) {
                const linhasParcelas = tabelaParcelas.querySelectorAll('tbody > tr:not(:first-child)');
                linhasParcelas.forEach(tr => {
                    const tds = tr.querySelectorAll('td');
                    if (tds.length >= 10) {
                        const dataDeposito = tds[2]?.textContent?.trim() || '';
                        const nomeDepositante = tds[3]?.textContent?.trim() || '';
                        let valorDisponivelTxt = '';
                        const celulaSaldo = tr.querySelector('td[id^="td_saldo_parcela_saldo_"]');
                        if (celulaSaldo) {
                            valorDisponivelTxt = celulaSaldo.textContent?.trim() || '';
                        } else {
                            valorDisponivelTxt = tds[8]?.textContent?.trim() || '';
                        }
                        const valorDisponivelParcela = brlToFloat(valorDisponivelTxt);
                        if (valorDisponivelParcela > 0 && dataDeposito && nomeDepositante) {
                            depositos.push({ data: dataDeposito, depositante: nomeDepositante, valor: valorDisponivelParcela });
                        }
                    }
                });
            }
            resultados.push({ numeroConta, valorDisponivel, depositos });
        });

        const hoje = new Date();
        const dia = String(hoje.getDate()).padStart(2, '0');
        const mes = String(hoje.getMonth() + 1).padStart(2, '0');
        const ano = hoje.getFullYear();
        const dataConferencia = `${dia}/${mes}/${ano}`;

        const pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';
        let htmlFinal = '';
        if (resultados.length === 0) {
            htmlFinal += `<p ${pStyle}>Nenhuma conta com valor disponível encontrada.</p>`;
        } else {
            htmlFinal += `<p ${pStyle}>Data da conferência: ${dataConferencia}</p>`;
            resultados.forEach((conta, index) => {
                htmlFinal += `<p ${pStyle}>Conta judicial: ${conta.numeroConta}</p>`;
                htmlFinal += `<p ${pStyle}>Total disponível: ${toBRL(conta.valorDisponivel)}</p>`;
                if (conta.depositos.length > 0) {
                    htmlFinal += `<p ${pStyle}>Discriminação de depósitos disponíveis:</p>`;
                    conta.depositos.forEach(dep => {
                        htmlFinal += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:1cm;text-align:justify !important;text-indent:4.5cm;">• ${dep.data} - ${dep.depositante} - ${toBRL(dep.valor)}</p>`;
                    });
                } else {
                    htmlFinal += `<p ${pStyle}>(Consultar parcelas individuais - expandir detalhes na tela)</p>`;
                }
                if (index < resultados.length - 1) {
                    htmlFinal += `<p ${pStyle}><br data-cke-filler="true"></p>`;
                }
            });
        }

        const success = copyToClipboard(htmlFinal);
        if (success) {
            console.log('✅ Dados extraídos e copiados!');
            console.log(`• Contas com valor: ${resultados.length}`);
        } else {
            const textoSimples = htmlFinal.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ');
            console.log('DADOS EXTRAÍDOS:');
            console.log(textoSimples);
        }
    }

    // ── Expansão das contas com valor (idêntica ao bookmarklet) ──
    function expandirContasComValor() {
        const linhasContas = document.querySelectorAll('tr[id^="linhaConta_"]');
        let contasExpandidas = 0;
        linhasContas.forEach(linha => {
            const celulaValorDisponivel = linha.querySelector('td[id^="td_saldo_corrigido_conta_"]');
            const valorDisponivelTxt = celulaValorDisponivel?.textContent?.trim() || '';
            const valorDisponivel = brlToFloat(valorDisponivelTxt);
            if (valorDisponivel > 0) {
                const iconeSoma = linha.querySelector('img#ico-img[src*="soma-ico.png"]');
                if (iconeSoma) {
                    iconeSoma.click();
                    contasExpandidas++;
                }
            }
        });
        return contasExpandidas;
    }

    // ── Ação do botão (mesma sequência do bookmarklet) ──
    function extrairSaldo() {
        const contasExpandidas = expandirContasComValor();
        if (contasExpandidas > 0) {
            setTimeout(() => {
                extrairDados();
            }, 2000);
        } else {
            extrairDados();
        }
    }

    // ── Injeção do botão fixo na parte de baixo da janela ──
    // Loga SEMPRE o motivo de não injetar — sem isso, falha de gate é invisível
    // no console (era o caso: nenhum log aparecia quando o botão não entrava).
    function injetarBotao(motivo) {
        const href = window.location.href;
        const de = motivo ? ' [' + motivo + ']' : '';
        if (window.self !== window.top) {
            console.log('[AlvSaldo]' + de + ' Pulo: página dentro de iframe —', href);
            return;
        }
        if (!href.includes(URL_ALVO)) {
            console.log('[AlvSaldo]' + de + ' Pulo: URL não contém a página de busca de contas — esperado:', URL_ALVO, '| atual:', href);
            return;
        }
        if (document.getElementById(BTN_ID)) return;
        if (!document.body) {
            console.log('[AlvSaldo]' + de + ' document.body ainda não existe — retry em 500ms');
            setTimeout(function () { injetarBotao('retry-body'); }, 500);
            return;
        }

        const btn = document.createElement('button');
        btn.id = BTN_ID;
        btn.textContent = 'Extrair saldo';
        btn.title = 'Extrai o saldo disponível das contas judiciais e copia o bloco formatado para o clipboard';
        btn.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:999999999;
            padding:10px 15px;background-color:#1a7f37;color:white;border:none;
            border-radius:4px;font-weight:bold;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.3);
            font-size:14px;text-shadow:0 1px 2px rgba(0,0,0,0.3);`;
        btn.onclick = function (e) {
            e.preventDefault();
            e.stopPropagation();
            btn.disabled = true;
            btn.textContent = 'Extraindo...';
            try {
                extrairSaldo();
            } catch (err) {
                console.error('[AlvSaldo] Erro ao extrair saldo:', err);
                alert('Erro ao extrair saldo: ' + (err && err.message ? err.message : err));
            }
            btn.textContent = 'Extrair saldo';
            btn.disabled = false;
        };

        document.body.appendChild(btn);
        console.log('[AlvSaldo] Botão "Extrair saldo" injetado em', href);
    }

    // API pública (convenção do projeto: window.NomeModulo = {...})
    window.PjeAlvaraSaldo = {
        extrairSaldo,
        injetarBotao,
    };
    // Alias no namespace do módulo alvará
    Alv.saldo = window.PjeAlvaraSaldo;

    // Injeção no load (o módulo roda via @require em document-idle) + retentativas
    // para páginas JSF que montam o body tarde; página não é SPA, então não há
    // observer de mutação. Cada tentativa loga o motivo quando pula.
    console.log('[AlvSaldo] módulo carregado (saldo_extracao.js) — URL:', window.location.href, '| PjeAlvaraSaldo exposto:', typeof window.PjeAlvaraSaldo);
    injetarBotao('load');
    setTimeout(function () { injetarBotao('retry-1.5s'); }, 1500);
    setTimeout(function () { injetarBotao('retry-4s'); }, 4000);
})();
