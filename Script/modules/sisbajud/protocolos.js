'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — protocolos.js (botões "Copiar protocolo" e "Unir PDFs")
// Onde: https://sisbajud.pdpj.jus.br/minuta (e também o host cnj)
// O que faz:
//   - "Copiar protocolo": lê a dialog "Relação de protocolos", copia os
//     números separados por ';', fecha a dialog e reaplica o filtro.
//   - "Unir PDFs": clica em cada ícone PDF (.mat-icon-exportar) da dialog,
//     intercepta os blobs gerados no cliente sem baixar avulsos e gera um
//     único PDF consolidado via PDFLib.
//   - Clique manual em um ícone PDF: renomeia o arquivo com o protocolo.
// Injetado pelo orquestrador (sisbajud.js → injetarUI), sem timer próprio.
// ═══════════════════════════════════════════════════════════════════

(function () {
    if (window.SisbProtocolos) return;

    var ID_BOTAO = 'pjetools-sisb-protocolos';
    var ID_BOTAO_PDF = 'pjetools-sisb-protocolos-pdf';
    var ID_BOTAO_ORDEM = 'pjetools-sisb-ordem-protocolos';
    var TEXTO_PADRAO = 'Copiar protocolo';
    var TEXTO_PDF_PADRAO = 'Unir PDFs';
    var TEXTO_ORDEM_PADRAO = 'Baixar protocolos';
    var PAGE_WIN = (typeof unsafeWindow !== 'undefined' && unsafeWindow) || window;

    function hostSisbajud() {
        var h = window.location.hostname || '';
        return h.indexOf('sisbajud.') === 0;
    }

    function naRotaMinuta() {
        var p = window.location.pathname || '';
        return p === '/minuta' || p === '/minuta/';
    }

    function naRotaOrdemJudicial() {
        var p = window.location.pathname || '';
        return p === '/ordem-judicial' || p === '/ordem-judicial/';
    }

    // ── Clipboard: GM_setClipboard → navigator.clipboard → textarea ──
    function copiarFallback(texto) {
        try {
            var ta = document.createElement('textarea');
            ta.value = texto;
            ta.style.cssText = 'position:fixed;top:-1000px;left:-1000px;opacity:0;';
            document.body.appendChild(ta);
            ta.select();
            var ok = document.execCommand('copy');
            ta.remove();
            return ok;
        } catch (e) {
            return false;
        }
    }

    function copiar(texto) {
        return new Promise(function (resolve) {
            try {
                if (typeof GM_setClipboard === 'function') {
                    GM_setClipboard(texto, 'text');
                    return resolve(true);
                }
            } catch (e) { /* segue */ }

            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(texto).then(
                        function () { resolve(true); },
                        function () { resolve(copiarFallback(texto)); }
                    );
                    return;
                }
            } catch (e) { /* segue */ }

            resolve(copiarFallback(texto));
        });
    }

    // ── Leitura da dialog ────────────────────────────────────────────
    function acharDialogProtocolos() {
        var titulos = document.querySelectorAll('h1.h1-title');
        for (var i = 0; i < titulos.length; i++) {
            if ((titulos[i].textContent || '').indexOf('Relação de protocolos') > -1) {
                return titulos[i].closest('form') || titulos[i].parentElement;
            }
        }
        var span = document.querySelector('.span-protocolo');
        if (span) return span.closest('form') || span.parentElement;
        return null;
    }

    function lerProtocolos(escopo) {
        var spans = escopo.querySelectorAll('.span-protocolo');
        var nums = [];
        for (var i = 0; i < spans.length; i++) {
            var n = (spans[i].textContent || '').replace(/\D+/g, '');
            if (n) nums.push(n);
        }
        return nums;
    }

    function clicarVoltar(escopo) {
        var area = escopo.querySelector('.mat-dialog-actions') || escopo;
        var botoes = area.querySelectorAll('button');
        for (var i = 0; i < botoes.length; i++) {
            if (((botoes[i].textContent || '').trim().toLowerCase()) === 'voltar') {
                botoes[i].click();
                return true;
            }
        }
        return false;
    }

    // ── Após "Voltar": reaplicar o filtro da listagem de minutas ─────
    // Sequência capturada no probe de /minuta:
    //   1. mat-radio-button.mat-radio-juiz  ("Minutas a protocolizar destinadas ao juiz")
    //   2. mat-select da delegação          ("Juiz para o qual tenho delegação de protocolo")
    //   3. button.mat-fab "Consultar"       (GET /v2/ordem/minuta)
    var JUIZ_PREFERIDO = 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA';  // vazio = usa a primeira opção

    function esperar(ms) {
        return new Promise(function (r) { setTimeout(r, ms); });
    }

    function txt(el) {
        return (el && (el.innerText || el.textContent) || '').trim();
    }

    function visivel(el) {
        if (!el) return false;
        var r = el.getBoundingClientRect();
        if (!r.width && !r.height) return false;
        return window.getComputedStyle(el).visibility !== 'hidden';
    }

    function clicarRadioJuiz() {
        var radio = document.querySelector('mat-radio-button.mat-radio-juiz');
        if (!radio) return false;
        if (radio.classList.contains('mat-radio-checked')) return true;
        var alvo = radio.querySelector('label, .mat-radio-label, input') || radio;
        alvo.click();
        return true;
    }

    function acharSelectJuiz() {
        var campos = document.querySelectorAll('mat-form-field');
        for (var i = 0; i < campos.length; i++) {
            var t = txt(campos[i]).toLowerCase();
            if (t.indexOf('delega') > -1 || t.indexOf('juiz') > -1) {
                var sel = campos[i].querySelector('mat-select');
                if (sel) return sel;
            }
        }
        var selects = document.querySelectorAll('mat-select');
        return selects.length ? selects[0] : null;
    }

    async function selecionarJuizDelegacao() {
        var sel = acharSelectJuiz();
        if (!sel) return false;
        sel.click();
        await esperar(400);
        var opcoes = Array.prototype.slice
            .call(document.querySelectorAll('mat-option'))
            .filter(visivel);
        if (!opcoes.length) return false;
        var alvo = null;
        if (JUIZ_PREFERIDO) {
            alvo = opcoes.find(function (o) {
                return txt(o).toLowerCase().indexOf(JUIZ_PREFERIDO.toLowerCase()) > -1;
            }) || null;
        }
        alvo = alvo || opcoes[0];
        alvo.click();
        await esperar(300);
        return true;
    }

    function clicarConsultar() {
        var botoes = Array.prototype.slice.call(document.querySelectorAll('button.mat-fab'));
        for (var i = 0; i < botoes.length; i++) {
            if (visivel(botoes[i]) && txt(botoes[i]).toLowerCase().indexOf('consultar') > -1) {
                botoes[i].click();
                return true;
            }
        }
        return false;
    }

    async function reaplicarFiltro(btn) {
        try {
            var radio = clicarRadioJuiz();
            console.log('[SisbProtocolos] filtro: radio juiz =', radio);
            await esperar(400);

            var juiz = await selecionarJuizDelegacao();
            console.log('[SisbProtocolos] filtro: delegação selecionada =', juiz);
            await esperar(300);

            var consultou = clicarConsultar();
            console.log('[SisbProtocolos] filtro: Consultar =', consultou);
            if (btn) avisar(btn, consultou ? 'Lista atualizada' : 'Filtro incompleto', 2000);
        } catch (e) {
            console.log('[SisbProtocolos] filtro falhou:', e);
            if (btn) avisar(btn, 'Filtro falhou', 2000);
        }
    }

    // ── Ação do botão "Copiar protocolo" ─────────────────────────────
    function avisar(btn, texto, ms, padrao) {
        btn.textContent = texto;
        setTimeout(function () { btn.textContent = padrao || TEXTO_PADRAO; }, ms || 2000);
    }

    function aoClicar(btn) {
        var dlg = acharDialogProtocolos();
        if (!dlg) return avisar(btn, 'Dialog não encontrada');

        var nums = lerProtocolos(dlg);
        if (!nums.length) return avisar(btn, 'Nenhum protocolo');

        copiar(nums.join(';')).then(function (ok) {
            if (!ok) return avisar(btn, 'Falha ao copiar');
            avisar(btn, 'Copiado!', 2000);
            setTimeout(function () {
                clicarVoltar(dlg);
                // depois de fechar a dialog, reaplica o filtro da listagem
                setTimeout(function () { reaplicarFiltro(btn); }, 900);
            }, 250);
        });
    }

    // ── Interceptação de PDFs client-side (lote + renomeação manual) ──
    var hooksInstalados = false;
    var modoCaptura = false;
    var resolverCaptura = null;
    var ultimoProtocoloManual = '';
    var tsProtocoloManual = 0;
    var mapaBlobs = new Map();
    var origCreateObjectURL = null;
    var origAnchorClick = null;
    var origWindowOpen = null;

    function obterPdfLib() {
        if (typeof PDFLib !== 'undefined' && PDFLib && PDFLib.PDFDocument) return PDFLib;
        if (window.PDFLib && window.PDFLib.PDFDocument) return window.PDFLib;
        if (PAGE_WIN && PAGE_WIN.PDFLib && PAGE_WIN.PDFLib.PDFDocument) return PAGE_WIN.PDFLib;
        return null;
    }

    function entregarCaptura(origem) {
        if (!modoCaptura || !resolverCaptura) return false;
        var fn = resolverCaptura;
        resolverCaptura = null;
        fn(origem);
        return true;
    }

    function instalarHooksDownload() {
        if (hooksInstalados) return;
        hooksInstalados = true;

        try {
            if (PAGE_WIN.URL && typeof PAGE_WIN.URL.createObjectURL === 'function') {
                origCreateObjectURL = PAGE_WIN.URL.createObjectURL.bind(PAGE_WIN.URL);
                PAGE_WIN.URL.createObjectURL = function (obj) {
                    var url = origCreateObjectURL(obj);
                    try {
                        if (obj && typeof obj.arrayBuffer === 'function') {
                            mapaBlobs.set(url, obj);
                            if (mapaBlobs.size > 60) {
                                var primeira = mapaBlobs.keys().next().value;
                                mapaBlobs.delete(primeira);
                            }
                        }
                    } catch (e) { }
                    return url;
                };
            }
        } catch (e) { console.warn('[SisbProtocolos] hook createObjectURL falhou:', e); }

        try {
            var anchorProto = PAGE_WIN.HTMLAnchorElement && PAGE_WIN.HTMLAnchorElement.prototype;
            if (anchorProto && typeof anchorProto.click === 'function') {
                origAnchorClick = anchorProto.click;
                anchorProto.click = function () {
                    try {
                        var href = this.getAttribute('href') || this.href || '';
                        var ehBlobOuPdf = href.indexOf('blob:') === 0
                            || href.indexOf('data:application/pdf') === 0
                            || (this.hasAttribute('download') && /\.pdf$/i.test(this.getAttribute('download') || ''));

                        if (ehBlobOuPdf && !this.dataset.pjetoolsMerged) {
                            if (modoCaptura && resolverCaptura) {
                                var blob = mapaBlobs.get(href) || null;
                                entregarCaptura({ blob: blob, href: href });
                                return;
                            }
                            // Clique manual em um recibo na dialog: aplica nome real do protocolo
                            if (ultimoProtocoloManual && (Date.now() - tsProtocoloManual) < 10000) {
                                this.setAttribute('download', 'recibo_' + ultimoProtocoloManual + '.pdf');
                            }
                        }
                    } catch (e) { }
                    return origAnchorClick.apply(this, arguments);
                };
            }
        } catch (e) { console.warn('[SisbProtocolos] hook anchor.click falhou:', e); }

        try {
            if (typeof PAGE_WIN.open === 'function') {
                origWindowOpen = PAGE_WIN.open.bind(PAGE_WIN);
                PAGE_WIN.open = function (url) {
                    try {
                        var u = String(url || '');
                        if (modoCaptura && resolverCaptura && (u.indexOf('blob:') === 0 || u.indexOf('data:application/pdf') === 0)) {
                            var blob = mapaBlobs.get(u) || null;
                            entregarCaptura({ blob: blob, href: u });
                            return null;
                        }
                    } catch (e) { }
                    return origWindowOpen.apply(PAGE_WIN, arguments);
                };
            }
        } catch (e) { console.warn('[SisbProtocolos] hook window.open falhou:', e); }

        // Registra o protocolo quando o usuário clica manualmente no ícone PDF
        document.addEventListener('click', function (ev) {
            if (modoCaptura) return;
            try {
                var alvo = ev.target && ev.target.closest && ev.target.closest('.div-relacao-protocolos');
                if (!alvo) return;
                var sp = alvo.querySelector('.span-protocolo');
                var num = sp ? (sp.textContent || '').replace(/\D+/g, '') : '';
                if (num) {
                    ultimoProtocoloManual = num;
                    tsProtocoloManual = Date.now();
                }
            } catch (e) { }
        }, true);
    }

    async function resolverBytes(captura) {
        if (!captura) return null;
        if (captura.blob && typeof captura.blob.arrayBuffer === 'function') {
            return await captura.blob.arrayBuffer();
        }
        if (captura.href) {
            var r = await PAGE_WIN.fetch(captura.href);
            return await r.arrayBuffer();
        }
        return null;
    }

    function aguardarProximoPdf(timeoutMs) {
        return new Promise(function (resolve) {
            var resolvido = false;
            var timer = setTimeout(function () {
                if (resolvido) return;
                resolvido = true;
                resolverCaptura = null;
                resolve(null);
            }, timeoutMs || 8000);

            resolverCaptura = function (dados) {
                if (resolvido) return;
                resolvido = true;
                clearTimeout(timer);
                resolve(dados);
            };
        });
    }

    function baixarPdfUnificado(bytes, nomeArquivo) {
        var blob = new Blob([bytes], { type: 'application/pdf' });
        var url = (origCreateObjectURL || URL.createObjectURL)(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = nomeArquivo;
        a.dataset.pjetoolsMerged = '1';
        a.style.display = 'none';
        document.body.appendChild(a);
        if (origAnchorClick) origAnchorClick.call(a);
        else a.click();
        setTimeout(function () {
            a.remove();
            try { URL.revokeObjectURL(url); } catch (e) { }
        }, 2000);
    }

    function listarItensPdf(dlg) {
        var linhas = dlg.querySelectorAll('.div-relacao-protocolos');
        var itens = [];
        for (var i = 0; i < linhas.length; i++) {
            var sp = linhas[i].querySelector('.span-protocolo');
            var icone = linhas[i].querySelector('mat-icon.mat-icon-exportar, mat-icon.fa-file-pdf, .fa-file-pdf');
            var num = sp ? (sp.textContent || '').replace(/\D+/g, '') : '';
            if (icone) itens.push({ protocolo: num || String(i + 1), icone: icone });
        }
        return itens;
    }

    var unindoEmAndamento = false;

    async function aoClicarUnirPdfs(btn) {
        if (unindoEmAndamento) return;

        var dlg = acharDialogProtocolos();
        if (!dlg) return avisar(btn, 'Dialog não encontrada', 2000, TEXTO_PDF_PADRAO);

        var lib = obterPdfLib();
        if (!lib) return avisar(btn, 'PDFLib indisponível', 2500, TEXTO_PDF_PADRAO);

        var itens = listarItensPdf(dlg);
        if (!itens.length) return avisar(btn, 'Nenhum PDF na dialog', 2000, TEXTO_PDF_PADRAO);

        instalarHooksDownload();
        unindoEmAndamento = true;
        modoCaptura = true;
        btn.disabled = true;

        var capturados = [];
        var falhas = 0;

        try {
            for (var i = 0; i < itens.length; i++) {
                var item = itens[i];
                btn.textContent = 'PDFs ' + (i + 1) + '/' + itens.length + '...';
                var promessa = aguardarProximoPdf(8000);
                item.icone.click();
                var cap = await promessa;
                var bytes = await resolverBytes(cap);
                if (bytes && bytes.byteLength > 100) {
                    capturados.push({ protocolo: item.protocolo, bytes: bytes });
                } else {
                    falhas++;
                    console.warn('[SisbProtocolos] PDF não capturado para protocolo:', item.protocolo);
                }
                await esperar(120);
            }

            if (!capturados.length) {
                avisar(btn, 'Nenhum PDF capturado', 2500, TEXTO_PDF_PADRAO);
                return;
            }

            btn.textContent = 'Unindo ' + capturados.length + ' PDFs...';
            var pdfFinal = await lib.PDFDocument.create();
            for (var j = 0; j < capturados.length; j++) {
                try {
                    var src = await lib.PDFDocument.load(capturados[j].bytes, { ignoreEncryption: true });
                    var paginas = await pdfFinal.copyPages(src, src.getPageIndices());
                    for (var p = 0; p < paginas.length; p++) {
                        pdfFinal.addPage(paginas[p]);
                    }
                } catch (eLoad) {
                    falhas++;
                    console.warn('[SisbProtocolos] Falha ao anexar PDF', capturados[j].protocolo, eLoad);
                }
            }

            var bytesFinais = await pdfFinal.save();
            var primeiro = capturados[0].protocolo;
            var ultimo = capturados[capturados.length - 1].protocolo;
            var nome = capturados.length === 1
                ? ('recibo_' + primeiro + '.pdf')
                : ('recibos_' + primeiro + '_a_' + ultimo + '_' + capturados.length + 'x.pdf');

            baixarPdfUnificado(bytesFinais, nome);
            avisar(
                btn,
                falhas ? ('Unido (' + capturados.length + ', ' + falhas + ' erro)') : ('PDF único (' + capturados.length + ')!'),
                3000,
                TEXTO_PDF_PADRAO
            );
        } catch (e) {
            console.error('[SisbProtocolos] Erro ao unir PDFs:', e);
            avisar(btn, 'Erro ao unir PDFs', 2500, TEXTO_PDF_PADRAO);
        } finally {
            modoCaptura = false;
            resolverCaptura = null;
            unindoEmAndamento = false;
            btn.disabled = false;
        }
    }

    // ── Baixar protocolos "Não enviada" em /ordem-judicial ───────────
    function normalizarTexto(s) {
        return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    }

    function esperarCondicao(fn, timeoutMs, intervaloMs) {
        return new Promise(function (resolve) {
            var inicio = Date.now();
            var teto = timeoutMs || 10000;
            var passo = intervaloMs || 150;
            (function tick() {
                try {
                    var r = fn();
                    if (r) return resolve(r);
                } catch (e) { }
                if (Date.now() - inicio >= teto) return resolve(null);
                setTimeout(tick, passo);
            })();
        });
    }

    function extrairChaveLinhaOrdem(tr) {
        var celProto = tr.querySelector('[data-label*="protocolo"], [data-label*="Protocolo"], td.cdk-column-protocolo');
        var tProto = celProto ? (celProto.textContent || '').replace(/\D+/g, '') : '';
        if (tProto) return tProto;
        var m = (tr.textContent || '').match(/\b20\d{12,16}\b/);
        if (m) return m[0];
        return normalizarTexto(tr.textContent || '').slice(0, 80);
    }

    function listarLinhasNaoEnviadas() {
        var linhas = document.querySelectorAll('table.mat-table tbody tr.mat-row, table.mat-table tbody tr[mat-row]');
        var res = [];
        for (var i = 0; i < linhas.length; i++) {
            var tr = linhas[i];
            var celSit = tr.querySelector('[data-label="descricaoSituacao:"], [data-label*="Situacao"], td.cdk-column-descricaoSituacao');
            var sitTxt = normalizarTexto(celSit ? celSit.textContent : tr.textContent);
            if (sitTxt.indexOf('nao enviada') === -1) continue;
            res.push({ tr: tr, chave: extrairChaveLinhaOrdem(tr) });
        }
        return res;
    }

    async function abrirDetalharLinha(tr) {
        try { tr.scrollIntoView({ block: 'center', inline: 'nearest' }); } catch (e) { }
        await esperar(150);

        var btnMenu = tr.querySelector('button.mat-menu-trigger.mat-icon-button, button.mat-menu-trigger');
        if (!btnMenu) return false;
        btnMenu.click();

        var itemDetalhar = await esperarCondicao(function () {
            var itens = document.querySelectorAll('button[role="menuitem"].mat-menu-item, button[role="menuitem"]');
            for (var i = 0; i < itens.length; i++) {
                if (visivel(itens[i]) && normalizarTexto(txt(itens[i])).indexOf('detalhar') > -1) {
                    return itens[i];
                }
            }
            return null;
        }, 4000, 100);

        if (!itemDetalhar) return false;
        itemDetalhar.click();

        var entrou = await esperarCondicao(function () {
            return (window.location.pathname || '').indexOf('/detalhar') > -1;
        }, 10000, 150);

        return !!entrou;
    }

    async function voltarParaOrdemJudicial() {
        var btnVoltar = document.querySelector(
            'button.mat-icon-button .fa-chevron-left, button[aria-label="Voltar"], button[title="Voltar"]'
        );
        if (btnVoltar) {
            var alvo = btnVoltar.closest('button') || btnVoltar;
            alvo.click();
        } else {
            PAGE_WIN.history.back();
        }

        await esperarCondicao(function () {
            return naRotaOrdemJudicial()
                && document.querySelectorAll('table.mat-table tbody tr.mat-row, table.mat-table tbody tr[mat-row]').length > 0;
        }, 12000, 200);
        await esperar(300);
    }

    async function unirEBaixarPdfs(lib, capturados, falhas, btn, textoPadrao, prefixoNome) {
        if (!capturados.length) {
            avisar(btn, 'Nenhum PDF capturado', 2500, textoPadrao);
            return;
        }
        btn.textContent = 'Unindo ' + capturados.length + ' PDFs...';
        var pdfFinal = await lib.PDFDocument.create();
        for (var j = 0; j < capturados.length; j++) {
            try {
                var src = await lib.PDFDocument.load(capturados[j].bytes, { ignoreEncryption: true });
                var paginas = await pdfFinal.copyPages(src, src.getPageIndices());
                for (var p = 0; p < paginas.length; p++) {
                    pdfFinal.addPage(paginas[p]);
                }
            } catch (eLoad) {
                falhas++;
                console.warn('[SisbProtocolos] Falha ao anexar PDF', capturados[j].protocolo, eLoad);
            }
        }
        var bytesFinais = await pdfFinal.save();
        var primeiro = capturados[0].protocolo;
        var ultimo = capturados[capturados.length - 1].protocolo;
        var nome = capturados.length === 1
            ? ('recibo_' + primeiro + '.pdf')
            : ((prefixoNome || 'recibos') + '_' + primeiro + '_a_' + ultimo + '_' + capturados.length + 'x.pdf');
        baixarPdfUnificado(bytesFinais, nome);
        avisar(
            btn,
            falhas ? ('Unido (' + capturados.length + ', ' + falhas + ' erro)') : ('PDF único (' + capturados.length + ')!'),
            3500,
            textoPadrao
        );
    }

    var loteOrdemEmAndamento = false;

    async function aoClicarBaixarProtocolosOrdem(btn) {
        if (loteOrdemEmAndamento) return;

        var lib = obterPdfLib();
        if (!lib) return avisar(btn, 'PDFLib indisponível', 2500, TEXTO_ORDEM_PADRAO);

        var iniciais = listarLinhasNaoEnviadas();
        if (!iniciais.length) return avisar(btn, 'Nenhuma "Não enviada"', 2500, TEXTO_ORDEM_PADRAO);

        instalarHooksDownload();
        loteOrdemEmAndamento = true;
        modoCaptura = true;
        btn.disabled = true;

        var totalAlvo = iniciais.length;
        var processados = new Set();
        var capturados = [];
        var falhas = 0;
        var contador = 0;

        try {
            while (contador < totalAlvo + 5) {
                var disponiveis = listarLinhasNaoEnviadas();
                var proximo = null;
                for (var i = 0; i < disponiveis.length; i++) {
                    if (!processados.has(disponiveis[i].chave)) {
                        proximo = disponiveis[i];
                        break;
                    }
                }
                if (!proximo) break;

                processados.add(proximo.chave);
                contador++;
                btn.textContent = 'Baixando ' + contador + '/' + totalAlvo + '...';

                var abriu = await abrirDetalharLinha(proximo.tr);
                if (!abriu) {
                    falhas++;
                    console.warn('[SisbProtocolos] Não abriu Detalhar para:', proximo.chave);
                    continue;
                }

                var btnRecibo = await esperarCondicao(function () {
                    var btns = document.querySelectorAll('button.mat-fab, button');
                    for (var k = 0; k < btns.length; k++) {
                        if (visivel(btns[k]) && normalizarTexto(txt(btns[k])).indexOf('gerar recibo') > -1) {
                            return btns[k];
                        }
                    }
                    return null;
                }, 10000, 200);

                if (btnRecibo) {
                    await esperar(350);
                    var promessa = aguardarProximoPdf(10000);
                    btnRecibo.click();
                    var cap = await promessa;
                    var bytes = await resolverBytes(cap);
                    if (bytes && bytes.byteLength > 100) {
                        capturados.push({ protocolo: proximo.chave, bytes: bytes });
                    } else {
                        falhas++;
                        console.warn('[SisbProtocolos] Recibo não capturado em /detalhar:', proximo.chave);
                    }
                } else {
                    falhas++;
                    console.warn('[SisbProtocolos] Botão Gerar Recibo não encontrado:', proximo.chave);
                }

                await voltarParaOrdemJudicial();
            }

            await unirEBaixarPdfs(lib, capturados, falhas, btn, TEXTO_ORDEM_PADRAO, 'recibos_nao_enviadas');
        } catch (e) {
            console.error('[SisbProtocolos] Erro ao baixar protocolos /ordem-judicial:', e);
            avisar(btn, 'Erro ao baixar PDFs', 2500, TEXTO_ORDEM_PADRAO);
        } finally {
            modoCaptura = false;
            resolverCaptura = null;
            loteOrdemEmAndamento = false;
            btn.disabled = false;
        }
    }

    // ── Injeção dos botões (inferior direito) ────────────────────────
    function injetarBotao() {
        if (!hostSisbajud() || !document.body) return;

        var existente = document.getElementById(ID_BOTAO);
        var existentePdf = document.getElementById(ID_BOTAO_PDF);
        var existenteOrdem = document.getElementById(ID_BOTAO_ORDEM);

        if (naRotaMinuta()) {
            instalarHooksDownload();
            if (existenteOrdem && !loteOrdemEmAndamento) existenteOrdem.remove();

            if (!existente) {
                var btn = document.createElement('button');
                btn.id = ID_BOTAO;
                btn.type = 'button';
                btn.textContent = TEXTO_PADRAO;
                btn.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;' +
                    'padding:10px 18px;border:none;border-radius:8px;background:#1976d2;color:#fff;' +
                    'font:bold 14px Arial,sans-serif;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);';
                btn.addEventListener('click', function () { aoClicar(btn); });
                document.body.appendChild(btn);
            }

            if (!existentePdf) {
                var btnPdf = document.createElement('button');
                btnPdf.id = ID_BOTAO_PDF;
                btnPdf.type = 'button';
                btnPdf.textContent = TEXTO_PDF_PADRAO;
                btnPdf.style.cssText = 'position:fixed;bottom:20px;right:185px;z-index:999999;' +
                    'padding:10px 18px;border:none;border-radius:8px;background:#2e7d32;color:#fff;' +
                    'font:bold 14px Arial,sans-serif;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);';
                btnPdf.addEventListener('click', function () { aoClicarUnirPdfs(btnPdf); });
                document.body.appendChild(btnPdf);
            }
            return;
        }

        if (existente) existente.remove();
        if (existentePdf) existentePdf.remove();

        if (naRotaOrdemJudicial() || loteOrdemEmAndamento) {
            instalarHooksDownload();
            if (!existenteOrdem) {
                var btnOrdem = document.createElement('button');
                btnOrdem.id = ID_BOTAO_ORDEM;
                btnOrdem.type = 'button';
                btnOrdem.textContent = TEXTO_ORDEM_PADRAO;
                btnOrdem.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;' +
                    'padding:10px 18px;border:none;border-radius:8px;background:#2e7d32;color:#fff;' +
                    'font:bold 14px Arial,sans-serif;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);';
                btnOrdem.addEventListener('click', function () { aoClicarBaixarProtocolosOrdem(btnOrdem); });
                document.body.appendChild(btnOrdem);
            }
            return;
        }

        if (existenteOrdem) existenteOrdem.remove();
    }

    window.SisbProtocolos = {
        injetarBotao: injetarBotao,
        lerProtocolos: function () {
            var dlg = acharDialogProtocolos();
            return dlg ? lerProtocolos(dlg) : [];
        },
        unirPdfs: function () {
            var btnPdf = document.getElementById(ID_BOTAO_PDF);
            return aoClicarUnirPdfs(btnPdf || { textContent: '', disabled: false });
        },
        baixarProtocolosOrdem: function () {
            var btnOrdem = document.getElementById(ID_BOTAO_ORDEM);
            return aoClicarBaixarProtocolosOrdem(btnOrdem || { textContent: '', disabled: false });
        }
    };
})();
