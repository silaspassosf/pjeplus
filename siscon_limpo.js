// Versão limpa do siscon.js para verificação
javascript: (function () {
    function brlToFloat(txt) {
        if (!txt) return 0;
        const n = txt.replace(/R\$/g, '').replace(/\./g, '').replace(',', '.').replace(/\s/g, '').trim();
        const v = parseFloat(n);
        return Number.isFinite(v) ? v : 0;
    }

    function toBRL(n) {
        try {
            return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } catch {
            return `R$ ${(Number(n) || 0).toFixed(2).replace('.', ',')}`;
        }
    }

    function showNotification() {
        const notification = document.createElement('div');
        notification.textContent = 'Conteúdo copiado!';
        notification.style.cssText = `position:fixed;bottom:20px;right:20px;background:#4CAF50;color:white;padding:10px 20px;border-radius:5px;font-size:14px;font-weight:bold;z-index:99999;box-shadow:0 2px 10px rgba(0,0,0,0.3);`;
        document.body.appendChild(notification);
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 2000);
    }

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
                            depositos.push({
                                data: dataDeposito,
                                depositante: nomeDepositante,
                                valor: valorDisponivelParcela
                            });
                        }
                    }
                });
            }

            resultados.push({
                numeroConta,
                valorDisponivel,
                depositos
            });
        });

        const hoje = new Date();
        const dia = String(hoje.getDate()).padStart(2, '0');
        const mes = String(hoje.getMonth() + 1).padStart(2, '0');
        const ano = hoje.getFullYear();
        const dataConferencia = `${dia}/${mes}/${ano}`;

        let htmlFinal = '';
        if (resultados.length === 0) {
            htmlFinal += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Nenhuma conta com valor disponível encontrada.</p>';
        } else {
            htmlFinal += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Data da conferência: ${dataConferencia}</p>`;

            resultados.forEach((conta, index) => {
                htmlFinal += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Conta judicial: ${conta.numeroConta}</p>`;
                htmlFinal += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Total disponível: ${toBRL(conta.valorDisponivel)}</p>`;

                if (conta.depositos.length > 0) {
                    htmlFinal += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Discriminação de depósitos disponíveis:</p>`;
                    conta.depositos.forEach(dep => {
                        htmlFinal += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:1cm;text-align:justify !important;text-indent:4.5cm;">• ${dep.data} - ${dep.depositante} - ${toBRL(dep.valor)}</p>`;
                    });
                } else {
                    htmlFinal += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">(Consultar parcelas individuais - expandir detalhes na tela)</p>`;
                }

                if (index < resultados.length - 1) {
                    htmlFinal += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"><br data-cke-filler="true"></p>';
                }
            });
        }

        const textarea = document.createElement('textarea');
        textarea.value = htmlFinal;
        textarea.style.position = 'absolute';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();

        try {
            const success = document.execCommand('copy');
            if (success) {
                document.body.removeChild(textarea);
                showNotification();
            } else {
                throw new Error('Falha no execCommand');
            }
        } catch (err) {
            if (document.body.contains(textarea)) {
                document.body.removeChild(textarea);
            }
            console.error('Erro ao copiar:', err);
        }
    }

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

    const contasExpandidas = expandirContasComValor();
    if (contasExpandidas > 0) {
        setTimeout(() => {
            extrairDados();
        }, 2000);
    } else {
        extrairDados();
    }
})();
