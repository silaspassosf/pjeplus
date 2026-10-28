/**
 * VALIDADOR — testa a camada de API do extracao_siscondj.js
 * =========================================================
 * Onde rodar: no console do PJe (/detalhe de qualquer processo), com o
 * pjetools.user.js 2.6.31+ instalado (precisa de GM_xmlhttpRequest).
 *
 * Uso:
 *   await ValidarSaldo('1001636-61.2022.5.02.0703')
 *
 * Ele NÃO altera nada: só consulta e imprime o que o módulo extraiu.
 * Se tudo bater, o botão "🏦 Saldo" do painel vai funcionar igual.
 */
async function ValidarSaldo(numeroProcesso) {
    const api = window.Alv && window.Alv.siscondj;
    if (!api) { console.error('Alv.siscondj não carregado'); return; }
    if (!api.temGMXHR()) { console.error('GM_xmlhttpRequest indisponível — reinstale o pjetools 2.6.31+'); return; }

    if (!numeroProcesso) {
        numeroProcesso = api.numeroProcessoDaPagina();
        if (!numeroProcesso) {
            console.error('Número do processo não encontrado. Passe na mão: await ValidarSaldo("0000000-00.0000.0.00.0000")');
            return;
        }
    }
    console.log('processo:', numeroProcesso);

    console.log('%c=== 1) buscando contas ===', 'color:#8e44ad;font-weight:bold');
    const t0 = performance.now();
    const contas = await api.saldosCompletos(numeroProcesso);
    const ms = Math.round(performance.now() - t0);

    console.log(`encontradas ${contas.length} conta(s) em ${ms}ms`);

    contas.forEach(c => {
        console.log('%c--- conta ' + c.numeroConta + ' (id ' + c.idConta + ') ---', 'color:#1e88e5;font-weight:bold');
        console.log('  status:', c.status);
        console.log('  VALOR DEPOSITADO (td_saldo_conta):', c.depositadoTexto);
        console.log('  VALOR DISPONÍVEL (td_saldo_corrigido_conta):', c.saldoHtmlTexto);
        console.log('  consultou as parcelas?', c.expandida ? 'SIM (tinha saldo)' : 'NÃO (saldo zero)');
        console.log('  total das parcelas:', api.formatarBRL(c.totalDisponivelValor), '(' + c.totalDisponivelValor + ')');
        console.log('  parcelas:', c.parcelas.length);

        if (!c.expandida) return;

        const comSaldo = c.parcelas.filter(p => p.disponivelValor > 0);
        console.log('  parcelas com saldo:', comSaldo.length);
        console.table(comSaldo.map(p => ({
            parcela: p.numero,
            data: p.data,
            depositante: p.depositante,
            disponivel: p.disponivelTexto
        })));
    });

    console.log('%c=== 2) conferência ===', 'color:#8e44ad;font-weight:bold');
    const expandidas = contas.filter(c => c.expandida);
    if (!expandidas.length) {
        console.log('%cNenhuma conta com saldo — nenhuma chamada de parcelas foi feita. O botão mostraria "Sem saldo".',
            'color:#e67e22');
    }
    expandidas.forEach(c => {
        const somaTela = c.saldoHtmlValor;
        const somaParcelas = c.totalDisponivelValor;
        const bate = Math.abs(somaTela - somaParcelas) < 0.01;
        console.log(
            (bate ? '%cOK  ' : '%cDIFF') + (c.numeroConta + ' — conta=' + c.disponivelTexto +
            ' | soma parcelas=' + api.formatarBRL(somaParcelas)),
            bate ? 'color:#27ae60' : 'color:#c0392b'
        );
    });

    console.log('%c=== 3) saída que seria copiada ===', 'color:#8e44ad;font-weight:bold');
    const html = api.montarSaidaHtml(contas);
    if (!html) {
        console.log('%c(sem saldo — o botão mostraria "Sem saldo" e não copiaria nada)', 'color:#e67e22');
    } else {
        console.log(html);
        const previa = document.createElement('div');
        previa.innerHTML = html;
        console.log('%c--- texto puro ---', 'color:#27ae60');
        console.log(previa.innerText);
        previa.style.cssText = 'position:fixed;top:10px;left:10px;width:520px;max-height:80vh;overflow:auto;' +
            'background:#fff;border:2px solid #1a7f37;padding:14px;z-index:9999999;font-size:12px;text-align:justify;';
        document.body.appendChild(previa);
        setTimeout(() => previa.remove(), 30000);
        console.log('(prévia visual exibida por 30s)');
    }
}

console.log('%cValidarSaldo carregado. Rode: await ValidarSaldo("0000000-00.0000.0.00.0000")', 'color:#27ae60;font-weight:bold');
