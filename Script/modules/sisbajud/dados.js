'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — dados.js (Extração automática de Dados da Ordem Judicial)
// Roda SOZINHO no carregamento da página, SEM botão e SEM overlay.
// Gate duplo (obrigatório):
//   1. URL: https://sisbajud.cnj.jus.br/ordem-judicial/*/desdobrar
//   2. Card: <mat-card-title> "Dados da Ordem Judicial de Requisição de Informações"
// Sem o card, NÃO executa nada.
// Saída: copia HTML formatado no clipboard + card minúsculo "DADOS EXTRAÍDOS".
// ═══════════════════════════════════════════════════════════════════

(function () {
    if (window.SisbDados) return;

    // ── Gate 1: apenas na rota de desdobrar do CNJ ────────────────
    const href = window.location.href;
    if (href.indexOf('sisbajud.cnj.jus.br') === -1) return;
    if (!/^\/ordem-judicial\/.+\/desdobrar/.test(window.location.pathname)) return;

    const TITULO_CARD = 'Dados da Ordem Judicial de Requisição de Informações';

    const cleanup = window.CleanupRegistry ? new window.CleanupRegistry() : null;
    let executado = false;

    // ── Notificação: card pequeno, sem overlay ────────────────────
    function mostrarCard(ok, detalhe) {
        let c = document.getElementById('sisbajud-dados-card');
        if (c) c.remove();
        c = document.createElement('div');
        c.id = 'sisbajud-dados-card';
        c.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:12px 20px;' +
            'border-radius:8px;font-size:14px;font-weight:bold;z-index:999999;' +
            'box-shadow:0 4px 15px rgba(0,0,0,0.3);font-family:Arial,sans-serif;' +
            'transition:opacity 0.3s ease;max-width:340px;';
        if (ok) {
            c.textContent = '✅ DADOS EXTRAÍDOS';
            c.style.background = '#4CAF50';
            c.style.color = 'white';
        } else {
            c.textContent = '❌ Erro ao copiar — veja o console (F12).';
            c.style.background = '#f44336';
            c.style.color = 'white';
            if (detalhe) console.log('=== DADOS EXTRAÍDOS SISBAJUD ===\n' + detalhe);
        }
        document.body.appendChild(c);
        setTimeout(function () {
            c.style.opacity = '0';
            setTimeout(function () { c.remove(); }, 300);
        }, 4000);
    }

    // ── Normalização / similaridade ───────────────────────────────
    function normalizar(a) {
        return (a || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toUpperCase()
            .replace(/\s+/g, ' ')
            .trim();
    }

    function similaridade(a, b) {
        a = normalizar(a);
        b = normalizar(b);
        if (a === b) return 1;
        var siglas = { JARDIM: 'JD', PARQUE: 'PQ', VILA: 'VL', AVENIDA: 'AV', RUA: 'R' };
        for (var k in siglas) {
            if ((a === k && b === siglas[k]) || (a === siglas[k] && b === k)) return 0.95;
        }
        var la = a.length, lb = b.length, dp = [];
        for (let i = 0; i <= la; i++) dp[i] = [i];
        for (let j = 0; j <= lb; j++) dp[0][j] = j;
        for (let i = 1; i <= la; i++) {
            for (let j = 1; j <= lb; j++) {
                var custo = a[i - 1] === b[j - 1] ? 0 : 1;
                dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + custo);
            }
        }
        var dist = dp[la][lb], maior = Math.max(la, lb);
        return (maior - dist) / maior;
    }

    function extrairCep(a) {
        var b = normalizar(a);
        var c = b.match(/\b(\d{5})-?(\d{3})\b/);
        if (c) return c[1] + c[2];
        c = b.match(/\b(\d{8})\b/);
        if (c) return c[1];
        c = b.match(/\b(\d{7})\b/);
        return c ? '0' + c[1] : null;
    }

    function extrairNumero(a) {
        var b = normalizar(a)
            .replace(/\b\d{5}-?\d{3}\b|\b\d{8}\b/g, '')
            .match(/\b(\d{1,5})\b/g);
        if (!b) return null;
        for (let n of b) {
            if (n !== '0' && n !== '00000') return n;
        }
        return '0';
    }

    var TIPOS_LOGRADOURO = {
        R: 'RUA', RUA: 'RUA', AV: 'AVENIDA', AVE: 'AVENIDA', AVENIDA: 'AVENIDA',
        AL: 'ALAMEDA', ALAMEDA: 'ALAMEDA', PC: 'PRACA', PCA: 'PRACA', PRACA: 'PRACA',
        LARGO: 'LARGO', EST: 'ESTRADA', ESTRADA: 'ESTRADA', ROD: 'RODOVIA',
        RODOVIA: 'RODOVIA', TV: 'TRAVESSA', TRAVESSA: 'TRAVESSA', PQ: 'PARQUE',
        PARQUE: 'PARQUE', VL: 'VILA', VILA: 'VILA', JD: 'JARDIM', JARDIM: 'JARDIM',
        COND: 'CONDOMINIO', CONDOMINIO: 'CONDOMINIO'
    };

    var TITULOS_AUTORIDADE = {
        DEP: 'DEPUTADO', DEPUT: 'DEPUTADO', DR: 'DOUTOR', DOUT: 'DOUTOR',
        PROF: 'PROFESSOR', ENG: 'ENGENHEIRO', CEL: 'CORONEL', COR: 'CORONEL',
        CAP: 'CAPITAO', GEN: 'GENERAL', PRES: 'PRESIDENTE', VER: 'VEREADOR',
        SEN: 'SENADOR', MIN: 'MINISTRO', MAL: 'MARECHAL'
    };

    function normalizarEndereco(a) {
        var b = normalizar(a);
        b = b.replace(/,/g, ' ').replace(/ - /g, ' ');
        b = b.replace(/\b\d{5}-?\d{3}\b|\b\d{8}\b|\b\d{7}\b/g, '');
        b = b.replace(/\b\d{1,5}\b/g, '');
        b = b.replace(/\b(APTO|APARTAMENTO|CASA|LOJA|SALA|CONJ|CONJUNTO|BLOCO|EDIF|EDIFICIO)\s+\d+\w*\b/g, '');
        b = b.replace(/\b\d+\w*\s+(ANDAR|FUNDOS|FRENTE|LADO)\b/g, '');
        b = b.replace(/\b(BAIRRO|CENTRO|MORUMBI|SAO|PAULO|SP|BRASIL|CEP)\b/g, '');
        b = b.replace(/\b([A-Z]+)\b/g, function (m) { return TITULOS_AUTORIDADE[m] || m; });
        b = b.replace(/\b([A-Z]+)\b/g, function (m) { return TIPOS_LOGRADOURO[m] || m; });
        return b
            .replace(/\b(DA|DE|DO|DAS|DOS|EM|COM|PARA)\b/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function criarChave(a) {
        var b = normalizar(a);
        var cep = extrairCep(b);
        var num = extrairNumero(b);
        var base = normalizarEndereco(b);
        var chave = '';
        if (cep) chave += cep + '|';
        chave += base;
        if (num && num !== '0') chave += '|' + num;
        return chave;
    }

    function enderecoValido(a) {
        var b = normalizar(a);
        return !!b.replace(/\b0+\b/g, '').replace(/\s+/g, '').trim() &&
            b.replace(/[\d\s\-,\.]/g, '').trim().length >= 3;
    }

    // ── Leitura dos rótulos (div.sisbajud-label → .sisbajud-label-valor) ──
    function extrairRotulo(texto) {
        let labels = document.querySelectorAll('div.sisbajud-label');
        for (let l of labels) {
            if (l.textContent.includes(texto)) {
                let v = l.nextElementSibling;
                while (v && v.nodeType === Node.COMMENT_NODE) v = v.nextElementSibling;
                if (v && v.classList.contains('sisbajud-label-valor')) return v.textContent.trim();
                break;
            }
        }
        return '';
    }

    // ── Montagem do HTML ──────────────────────────────────────────
    function montarHTML() {
        const protocolo = extrairRotulo('Número do Protocolo') || '';
        const processo = extrairRotulo('Número do Processo') || '';
        const varaJuizo = extrairRotulo('Vara/Juízo') || '';

        const estiloCorpo = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;font-family:Arial,sans-serif;"';
        const estiloRecuo = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:4.5cm !important;text-align:justify !important;font-family:Arial,sans-serif;"';

        let saida = [];
        saida.push(`<p ${estiloCorpo}>Certifico que, em consulta ao SISBAJUD, foram obtidos os seguintes dados:</p>`);
        if (processo) saida.push(`<p ${estiloCorpo}>Número do processo: <strong>${processo}</strong></p>`);
        if (protocolo) saida.push(`<p ${estiloCorpo}>Protocolo: <strong>${protocolo}</strong></p>`);
        if (varaJuizo) saida.push(`<p ${estiloCorpo}>Juízo: <strong>${varaJuizo}</strong></p>`);
        saida.push(`<p ${estiloCorpo}>&nbsp;</p>`);

        let paineisPessoas = Array.from(document.querySelectorAll('mat-expansion-panel'))
            .filter(p => p.querySelector('div.col-pessoa-pesquisada'));
        let contadorPessoa = 1;

        if (paineisPessoas.length === 0) {
            saida.push(`<p ${estiloCorpo}>Nenhum pesquisado encontrado na tela.</p>`);
        }

        for (let painel of paineisPessoas) {
            let nomeEl = painel.querySelector('span.col-pessoa-pesquisada-dados-nome-pessoa');
            if (!nomeEl) continue;
            let nome = nomeEl.textContent.trim();

            let dadosEl = painel.querySelector('.col-pessoa-pesquisada-dados');
            let dadosTxt = dadosEl ? (dadosEl.innerText || dadosEl.textContent) : '';
            let docMatch = dadosTxt.match(/\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/);
            let documento = docMatch ? docMatch[0] : '';

            let contas = [];
            let enderecos = [];
            let emails = [];
            let ordem = 0;

            let subPaineis = painel.querySelectorAll('mat-expansion-panel');
            for (let sub of subPaineis) {
                let instEl = sub.querySelector('div.div-title-instituicao span.col-pessoa-pesquisada-dados-nome-pessoa');
                if (!instEl) continue;
                let instituicao = instEl.textContent.trim();

                let agencias = sub.querySelectorAll('td.cdk-column-agenciasContas span');
                for (let a of agencias) {
                    let t = a.textContent.trim();
                    if (t && t !== '-') contas.push(`${instituicao} - ${t.replace(/Ag\b/g, 'Agência')}`);
                }

                let linhas = sub.querySelectorAll('tr.mat-row');
                for (let linha of linhas) {
                    let colEnd = linha.querySelector('td.cdk-column-enderecos');
                    if (!colEnd) continue;
                    let ps = colEnd.querySelectorAll('p');
                    for (let p of ps) {
                        let t = p.textContent.trim();
                        if (t && t !== '-' && enderecoValido(t)) {
                            if (t.includes('@') || /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/.test(t)) {
                                emails.push({ texto: t, ordem: ordem++ });
                            } else {
                                enderecos.push({ texto: t, ordem: ordem++ });
                            }
                        }
                    }
                }
            }

            // Dedupe de e-mails (normalizado)
            let listaEmails = [];
            let vistosEmail = new Set();
            emails.sort((x, y) => x.ordem - y.ordem);
            for (let e of emails) {
                let t = e.texto.replace(/\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$/i, '@$1');
                if (!t.includes('@') && /[a-zA-Z0-9._%+-]+\.[a-zA-Z]{2,}/.test(t)) {
                    t = t.replace(/^([^@]+)$/, '$1@desconhecido.com');
                }
                let chave = normalizar(t);
                if (!vistosEmail.has(chave)) {
                    vistosEmail.add(chave);
                    listaEmails.push(t);
                }
            }

            // Dedupe de endereços (chave CEP+número, similaridade sem CEP ≥ 0.82)
            let listaEnderecos = [];
            let chaves = [];
            enderecos.sort((x, y) => x.ordem - y.ordem);
            for (let e of enderecos) {
                let texto = e.texto;
                let chave = criarChave(texto);
                let semCep = chave.replace(/^\d{8}\|/, '');
                if (chaves.some(c => c.chave === chave)) continue;
                let duplicado = false;
                for (let i = 0; i < chaves.length; i++) {
                    let outra = chaves[i].semCep;
                    if (semCep && outra && semCep === outra) { duplicado = true; break; }
                    if (semCep.length > 8 && outra.length > 8 && similaridade(semCep, outra) >= 0.82) {
                        duplicado = true;
                        break;
                    }
                }
                if (!duplicado) {
                    chaves.push({ chave: chave, semCep: semCep });
                    listaEnderecos.push(texto);
                }
            }

            saida.push(`<p ${estiloCorpo}><strong>${contadorPessoa++} - ${nome}${documento ? ' - ' + documento : ''}</strong></p>`);
            for (let c of contas) saida.push(`<p ${estiloCorpo}>${c}</p>`);
            if (listaEnderecos.length > 0) {
                saida.push(`<p ${estiloCorpo}><strong>Endereços encontrados:</strong></p>`);
                for (let end of listaEnderecos) saida.push(`<p ${estiloRecuo}>${end}</p>`);
            }
            if (listaEmails.length > 0) {
                saida.push(`<p ${estiloCorpo}><strong>E-mails encontrados:</strong></p>`);
                for (let em of listaEmails) saida.push(`<p ${estiloRecuo}>${em}</p>`);
            }
            if (contas.length === 0 && listaEnderecos.length === 0 && listaEmails.length === 0) {
                saida.push(`<p ${estiloCorpo}>Nenhum dado retornado para este pesquisado.</p>`);
            }
            saida.push(`<p ${estiloCorpo}>&nbsp;</p>`);
        }

        while (saida.length > 0 && saida[saida.length - 1].includes('&nbsp;')) saida.pop();
        return saida.join('\n');
    }

    // ── Clipboard HTML (ClipboardItem + fallback) ─────────────────
    function copiarHTML(html) {
        function textoPuro(h) {
            return h.replace(/<[^>]*>?/gm, '').replace(/&nbsp;/g, ' ');
        }
        function fallback() {
            let box = document.createElement('div');
            box.innerHTML = html;
            box.style.position = 'absolute';
            box.style.left = '-9999px';
            document.body.appendChild(box);
            let range = document.createRange();
            range.selectNodeContents(box);
            let sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            try {
                let ok = document.execCommand('copy');
                mostrarCard(ok, ok ? '' : textoPuro(html));
            } catch (e) {
                mostrarCard(false, textoPuro(html));
            } finally {
                if (document.body.contains(box)) document.body.removeChild(box);
                sel.removeAllRanges();
            }
        }

        if (navigator.clipboard && window.ClipboardItem) {
            navigator.clipboard.write([
                new window.ClipboardItem({
                    'text/html': new Blob([html], { type: 'text/html' }),
                    'text/plain': new Blob([textoPuro(html)], { type: 'text/plain' })
                })
            ]).then(function () {
                mostrarCard(true);
            }).catch(function () {
                fallback();
            });
        } else {
            fallback();
        }
    }

    // ── Execução única ────────────────────────────────────────────
    function executar() {
        if (executado) return;
        executado = true;
        if (observerCard) { observerCard.disconnect(); observerCard = null; }
        const html = montarHTML();
        copiarHTML(html);
    }

    // ── Gate 2: aguarda o card-título específico (MutationObserver) ──
    // Sem esse card, o script jamais executa.
    let observerCard = null;

    function cardPresente() {
        const alvo = 'mat-card-title';
        for (let el of document.querySelectorAll(alvo)) {
            if ((el.textContent || '').includes(TITULO_CARD)) return true;
        }
        return false;
    }

    function iniciar() {
        if (executado) return;
        if (cardPresente()) { executar(); return; }

        observerCard = new MutationObserver(function () {
            if (cardPresente()) executar();
        });
        observerCard.observe(document.documentElement, {
            childList: true,
            subtree: true,
            characterData: true
        });
        if (cleanup) {
            cleanup.observer(observerCard);
            // Rede de segurança: para de observar após 120s (nunca executou = sem card)
            cleanup.timeout(function () {
                if (observerCard) { observerCard.disconnect(); observerCard = null; }
            }, 120000);
        }
    }

    window.SisbDados = {
        executar: executar,
        montarHTML: montarHTML
    };
    window.PjeSisbDados = window.SisbDados;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar, { once: true });
    } else {
        iniciar();
    }
})();
