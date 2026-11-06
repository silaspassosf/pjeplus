'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — extrair.js (botão "Extrair dados")
// Onde: https://sisbajud.pdpj.jus.br/ordem-judicial/<id>/desdobrar
// Injeção condicionada: só aparece se a tela tiver o título
//   <mat-card-title>Dados da Ordem Judicial de Requisição de Informações</mat-card-title>
// O que faz, ao clicar:
//   1. Lê protocolo, processo e juízo (div.sisbajud-label)
//   2. Percorre os painéis de pesquisados: agências/contas, endereços e e-mails
//   3. Deduplica endereços por CEP + logradouro + número (similaridade 0.82)
//   4. Monta o relatório em HTML (formato do despacho/certidão)
//   5. Copia HTML + texto para a área de transferência
//   6. O botão é SUBSTITUÍDO pelo overlay com os dados extraídos (sem dialog extra)
// Injetado pelo orquestrador (sisbajud.js → injetarUI), sem timer próprio.
// ═══════════════════════════════════════════════════════════════════

(function () {
    if (window.SisbExtrair) return;

    var ID_BOTAO = 'pjetools-sisb-extrair-btn';
    var ID_PAINEL = 'pjetools-sisb-extrair-painel';
    var TEXTO_PADRAO = 'Extrair dados';
    var TITULO_ORDEM = 'Dados da Ordem Judicial de Requisição de Informações';

    // ── Rota e condição de injeção ───────────────────────────────────
    function naRotaDesdobrar() {
        return /^\/ordem-judicial\/[^/]+\/desdobrar\/?$/.test(window.location.pathname || '');
    }

    function temTituloOrdem() {
        var titulos = document.querySelectorAll('mat-card-title');
        for (var i = 0; i < titulos.length; i++) {
            if (normalizar(titulos[i].textContent).indexOf(normalizar(TITULO_ORDEM)) > -1) {
                return true;
            }
        }
        return false;
    }

    // ── Normalização e similaridade (idêntico ao bookmarklet) ────────
    function normalizar(a) {
        return (a || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/\s+/g, ' ').trim();
    }

    function similaridade(a, b) {
        a = normalizar(a);
        b = normalizar(b);
        if (a === b) return 1;
        var sinonimos = { JARDIM: 'JD', PARQUE: 'PQ', VILA: 'VL', AVENIDA: 'AV', RUA: 'R' };
        for (var k in sinonimos) {
            if (a === k && b === sinonimos[k] || a === sinonimos[k] && b === k) return 0.95;
        }
        var la = a.length, lb = b.length, m = [], i, j;
        for (i = 0; i <= la; i++) m[i] = [i];
        for (j = 0; j <= lb; j++) m[0][j] = j;
        for (i = 1; i <= la; i++) {
            for (j = 1; j <= lb; j++) {
                var custo = a[i - 1] === b[j - 1] ? 0 : 1;
                m[i][j] = Math.min(m[i - 1][j] + 1, m[i][j - 1] + 1, m[i - 1][j - 1] + custo);
            }
        }
        var dist = m[la][lb], maior = Math.max(la, lb);
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
        var b = normalizar(a).replace(/\b\d{5}-?\d{3}\b|\b\d{8}\b/g, '').match(/\b(\d{1,5})\b/g);
        if (!b) return null;
        for (var i = 0; i < b.length; i++) if (b[i] !== '0' && b[i] !== '00000') return b[i];
        return '0';
    }

    var TIPOS_LOGRADOURO = {
        R: 'RUA', RUA: 'RUA', AV: 'AVENIDA', AVE: 'AVENIDA', AVENIDA: 'AVENIDA',
        AL: 'ALAMEDA', ALAMEDA: 'ALAMEDA', PC: 'PRACA', PCA: 'PRACA', PRACA: 'PRACA',
        LARGO: 'LARGO', EST: 'ESTRADA', ESTRADA: 'ESTRADA', ROD: 'RODOVIA', RODOVIA: 'RODOVIA',
        TV: 'TRAVESSA', TRAVESSA: 'TRAVESSA', PQ: 'PARQUE', PARQUE: 'PARQUE', VL: 'VILA',
        VILA: 'VILA', JD: 'JARDIM', JARDIM: 'JARDIM', COND: 'CONDOMINIO', CONDOMINIO: 'CONDOMINIO'
    };

    var TITULOS_AUTORIDADE = {
        DEP: 'DEPUTADO', DEPUT: 'DEPUTADO', DR: 'DOUTOR', DOUT: 'DOUTOR', PROF: 'PROFESSOR',
        ENG: 'ENGENHEIRO', CEL: 'CORONEL', COR: 'CORONEL', CAP: 'CAPITAO', GEN: 'GENERAL',
        PRES: 'PRESIDENTE', VER: 'VEREADOR', SEN: 'SENADOR', MIN: 'MINISTRO', MAL: 'MARECHAL'
    };

    function normalizarEndereco(a) {
        var b = normalizar(a);
        b = b.replace(/,/g, ' ').replace(/ - /g, ' ');
        b = b.replace(/\b\d{5}-?\d{3}\b|\b\d{8}\b|\b\d{7}\b/g, '');
        b = b.replace(/\b\d{1,5}\b/g, '');
        b = b.replace(/\b(APTO|APARTAMENTO|CASA|LOJA|SALA|CONJ|CONJUNTO|BLOCO|EDIF|EDIFICIO)\s+\d+\w*\b/g, '');
        b = b.replace(/\b\d+\w*\s+(ANDAR|FUNDOS|FRENTE|LADO)\b/g, '');
        b = b.replace(/\b(BAIRRO|CENTRO|MORUMBI|SAO|PAULO|SP|BRASIL|CEP)\b/g, '');
        b = b.replace(/\b([A-Z]+)\b/g, function (c) { return TITULOS_AUTORIDADE[c] || c; });
        b = b.replace(/\b([A-Z]+)\b/g, function (c) { return TIPOS_LOGRADOURO[c] || c; });
        return b.replace(/\b(DA|DE|DO|DAS|DOS|EM|COM|PARA)\b/g, '').replace(/\s+/g, ' ').trim();
    }

    function criarChave(a) {
        var b = normalizar(a), cep = extrairCep(b), numero = extrairNumero(b), semNum = normalizarEndereco(b), chave = '';
        if (cep) chave += cep + '|';
        chave += semNum;
        if (numero && numero !== '0') chave += '|' + numero;
        return chave;
    }

    function enderecoValido(a) {
        var b = normalizar(a);
        return !!b.replace(/\b0+\b/g, '').replace(/\s+/g, '').trim() &&
            b.replace(/[\d\s\-,\.,]/g, '').trim().length >= 3;
    }

    function extrairRotulo(a) {
        var rotulos = document.querySelectorAll('div.sisbajud-label');
        for (var i = 0; i < rotulos.length; i++) {
            if (rotulos[i].textContent.indexOf(a) > -1) {
                var d = rotulos[i].nextElementSibling;
                while (d && d.nodeType === Node.COMMENT_NODE) d = d.nextElementSibling;
                if (d && d.classList.contains('sisbajud-label-valor')) return d.textContent.trim();
                break;
            }
        }
        return '';
    }

    // ── Montagem do relatório ────────────────────────────────────────
    var ESTILO_CORPO = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;' +
        'text-align:justify !important;text-indent:4.5cm;font-family:Arial,sans-serif;"';
    var ESTILO_RECUO = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:4.5cm !important;' +
        'text-align:justify !important;font-family:Arial,sans-serif;"';

    function montarRelatorio() {
        var protocolo = extrairRotulo('Número do Protocolo') || '';
        var processo = extrairRotulo('Número do Processo') || '';
        var varaJuizo = extrairRotulo('Vara/Juízo') || '';

        var saida = [];
        saida.push('<p ' + ESTILO_CORPO + '>Certifico que, em consulta ao SISBAJUD, foram obtidos os seguintes dados:</p>');
        if (processo) saida.push('<p ' + ESTILO_CORPO + '>Número do processo: <strong>' + processo + '</strong></p>');
        if (protocolo) saida.push('<p ' + ESTILO_CORPO + '>Protocolo: <strong>' + protocolo + '</strong></p>');
        if (varaJuizo) saida.push('<p ' + ESTILO_CORPO + '>Juízo: <strong>' + varaJuizo + '</strong></p>');
        saida.push('<p ' + ESTILO_CORPO + '>&nbsp;</p>');

        var paineisPessoas = Array.prototype.slice
            .call(document.querySelectorAll('mat-expansion-panel'))
            .filter(function (p) { return p.querySelector('div.col-pessoa-pesquisada'); });
        var contadorPessoa = 1;

        if (paineisPessoas.length === 0) {
            saida.push('<p ' + ESTILO_CORPO + '>Nenhum pesquisado encontrado na tela.</p>');
        }

        paineisPessoas.forEach(function (painel) {
            var elNome = painel.querySelector('span.col-pessoa-pesquisada-dados-nome-pessoa');
            if (!elNome) return;

            var nome = elNome.textContent.trim();
            var elDados = painel.querySelector('.col-pessoa-pesquisada-dados');
            var txtDados = elDados ? (elDados.innerText || elDados.textContent) : '';
            var mDoc = txtDados.match(/\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/);
            var documento = mDoc ? mDoc[0] : '';

            var contas = [];      // "Instituição - Agência ..."
            var enderecos = [];   // {texto, ordem}
            var emails = [];      // {texto, ordem}
            var ordem = 0;

            Array.prototype.slice.call(painel.querySelectorAll('mat-expansion-panel')).forEach(function (sub) {
                var elInst = sub.querySelector('div.div-title-instituicao span.col-pessoa-pesquisada-dados-nome-pessoa');
                if (!elInst) return;
                var instituicao = elInst.textContent.trim();

                Array.prototype.slice.call(sub.querySelectorAll('td.cdk-column-agenciasContas span')).forEach(function (sp) {
                    var v = sp.textContent.trim();
                    if (v && v !== '-') contas.push(instituicao + ' - ' + v.replace(/Ag\b/g, 'Agência'));
                });

                Array.prototype.slice.call(sub.querySelectorAll('tr.mat-row')).forEach(function (tr) {
                    var td = tr.querySelector('td.cdk-column-enderecos');
                    if (!td) return;
                    Array.prototype.slice.call(td.querySelectorAll('p')).forEach(function (p) {
                        var texto = p.textContent.trim();
                        if (!texto || texto === '-' || !enderecoValido(texto)) return;
                        var ehEmail = texto.indexOf('@') > -1 || /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/.test(texto);
                        if (ehEmail) emails.push({ texto: texto, ordem: ordem++ });
                        else enderecos.push({ texto: texto, ordem: ordem++ });
                    });
                });
            });

            // E-mails: dedup por texto normalizado
            var listaEmails = [];
            var vistos = new Set();
            emails.sort(function (a, b) { return a.ordem - b.ordem; }).forEach(function (e) {
                var t = e.texto.replace(/\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$/i, '@$1');
                if (t.indexOf('@') === -1 && !/[a-zA-Z0-9._%+-]+\.[a-zA-Z]{2,}/.test(t)) return;
                if (t.indexOf('@') === -1) t = t.replace(/^([^@]+)$/, '$1@desconhecido.com');
                var chave = normalizar(t);
                if (vistos.has(chave)) return;
                vistos.add(chave);
                listaEmails.push(t);
            });

            // Endereços: dedup por CEP + logradouro + número (similaridade >= 0.82)
            var chavesVistas = [];
            var listaEnderecos = [];
            enderecos.sort(function (a, b) { return a.ordem - b.ordem; }).forEach(function (e) {
                var chave = criarChave(e.texto);
                var semCep = chave.replace(/^\d{8}\|/, '');
                if (chavesVistas.some(function (c) { return c.chave === chave; })) return;
                var repetido = false;
                for (var i = 0; i < chavesVistas.length; i++) {
                    var anterior = chavesVistas[i].semCep;
                    if (semCep && anterior && semCep === anterior) { repetido = true; break; }
                    if (semCep.length > 8 && anterior.length > 8 && similaridade(semCep, anterior) >= 0.82) { repetido = true; break; }
                }
                if (repetido) return;
                chavesVistas.push({ chave: chave, semCep: semCep });
                listaEnderecos.push(e.texto);
            });

            // Bloco do pesquisado
            saida.push('<p ' + ESTILO_CORPO + '><strong>' + (contadorPessoa++) + ' - ' + nome +
                (documento ? ' - ' + documento : '') + '</strong></p>');

            contas.forEach(function (c) {
                saida.push('<p ' + ESTILO_CORPO + '>' + c + '</p>');
            });

            if (listaEnderecos.length > 0) {
                saida.push('<p ' + ESTILO_CORPO + '><strong>Endereços encontrados:</strong></p>');
                listaEnderecos.forEach(function (e) {
                    saida.push('<p ' + ESTILO_RECUO + '>' + e + '</p>');
                });
            }

            if (listaEmails.length > 0) {
                saida.push('<p ' + ESTILO_CORPO + '><strong>E‑mails encontrados:</strong></p>');
                listaEmails.forEach(function (e) {
                    saida.push('<p ' + ESTILO_RECUO + '>' + e + '</p>');
                });
            }

            if (contas.length === 0 && listaEnderecos.length === 0 && listaEmails.length === 0) {
                saida.push('<p ' + ESTILO_CORPO + '>Nenhum dado retornado para este pesquisado.</p>');
            }

            saida.push('<p ' + ESTILO_CORPO + '>&nbsp;</p>');
        });

        while (saida.length > 0 && saida[saida.length - 1].indexOf('&nbsp;') > -1) saida.pop();

        return saida.join('\n');
    }

    function htmlParaTexto(html) {
        return html.replace(/<[^>]*>?/gm, '').replace(/&nbsp;/g, ' ');
    }

    // ── Clipboard ────────────────────────────────────────────────────
    function fallbackCopiarHTML(html) {
        var div = document.createElement('div');
        div.innerHTML = html;
        div.style.position = 'absolute';
        div.style.left = '-9999px';
        document.body.appendChild(div);

        var range = document.createRange();
        range.selectNodeContents(div);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        var ok = false;
        try {
            ok = document.execCommand('copy');
        } catch (e) {
            ok = false;
        } finally {
            if (document.body.contains(div)) document.body.removeChild(div);
            sel.removeAllRanges();
        }
        return ok;
    }

    function copiarParaClipboard(html) {
        return new Promise(function (resolve) {
            try {
                if (navigator.clipboard && window.ClipboardItem) {
                    navigator.clipboard.write([new ClipboardItem({
                        'text/html': new Blob([html], { type: 'text/html' }),
                        'text/plain': new Blob([htmlParaTexto(html)], { type: 'text/plain' })
                    })]).then(function () { resolve(true); }, function () { resolve(fallbackCopiarHTML(html)); });
                    return;
                }
            } catch (e) { /* segue para o fallback */ }
            resolve(fallbackCopiarHTML(html));
        });
    }

    // ── Overlay que substitui o botão ────────────────────────────────
    function substituirPorPainel(texto, copiou) {
        var btn = document.getElementById(ID_BOTAO);
        if (btn) btn.remove();

        var antigo = document.getElementById(ID_PAINEL);
        if (antigo) antigo.remove();

        var painel = document.createElement('div');
        painel.id = ID_PAINEL;
        painel.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);' +
            'width:min(760px,92vw);max-height:60vh;display:flex;flex-direction:column;' +
            'background:#fff;border:1px solid #bbb;border-radius:10px;z-index:999999;' +
            'box-shadow:0 6px 24px rgba(0,0,0,0.35);font-family:Arial,sans-serif;overflow:hidden;';

        var barra = document.createElement('div');
        barra.style.cssText = 'display:flex;align-items:center;justify-content:space-between;' +
            'gap:12px;padding:10px 14px;font:bold 13px Arial,sans-serif;color:#fff;' +
            'background:' + (copiou ? '#2e7d32' : '#c62828') + ';';
        barra.textContent = copiou
            ? '✅ Dados extraídos — copiados para a área de transferência'
            : '⚠️ Dados extraídos — falha ao copiar (selecione o texto abaixo)';

        var fechar = document.createElement('button');
        fechar.type = 'button';
        fechar.textContent = '✕';
        fechar.title = 'Fechar';
        fechar.style.cssText = 'background:transparent;border:none;color:#fff;font:bold 15px Arial;' +
            'cursor:pointer;line-height:1;padding:2px 4px;';
        fechar.addEventListener('click', function () { painel.remove(); });
        barra.appendChild(fechar);

        var corpo = document.createElement('div');
        corpo.style.cssText = 'padding:12px 14px;overflow:auto;white-space:pre-wrap;' +
            'font:12px/1.5 Arial,sans-serif;color:#222;';
        corpo.textContent = texto;

        painel.appendChild(barra);
        painel.appendChild(corpo);
        document.body.appendChild(painel);
    }

    // ── Abre a aba do processo no PJe (mesma ação do botão +PJe) ─────
    // Falha aqui NUNCA aborta a extração: os dados já estão no clipboard/painel.
    function abrirProcessoNoPJe(numero) {
        var fn = (window.Atalhos && window.Atalhos.abrir_processo_direto) || window.abrir_processo_direto;
        if (typeof fn !== 'function') {
            console.log('[SisbExtrair] abrir_processo_direto indisponível (atalhos.js não carregado) — aba do PJe não aberta');
            return;
        }
        if (!numero) {
            console.log('[SisbExtrair] número do processo não encontrado na tela — aba do PJe não aberta');
            return;
        }
        Promise.resolve(fn(numero, { focar: true })).then(function (r) {
            console.log('[SisbExtrair] PJe:', r);
        }, function (e) {
            console.log('[SisbExtrair] falha ao abrir o processo:', e);
        });
    }

    // ── Ação do botão ────────────────────────────────────────────────
    function aoClicar(btn) {
        btn.disabled = true;
        btn.textContent = 'Extraindo...';

        var html;
        try {
            html = montarRelatorio();
        } catch (e) {
            console.log('[SisbExtrair] erro na extração:', e);
            btn.disabled = false;
            btn.textContent = TEXTO_PADRAO;
            return;
        }

        console.log('[SisbExtrair] relatório gerado (' + html.length + ' chars)');

        copiarParaClipboard(html).then(function (copiou) {
            if (!copiou) console.log('=== DADOS EXTRAÍDOS SISBAJUD ===\n' + htmlParaTexto(html));
            substituirPorPainel(htmlParaTexto(html), copiou);
            // Extração terminada → abre e FOCA a aba do processo no PJe (ação do botão +PJe)
            var numero = extrairRotulo('Número do Processo') || '';
            setTimeout(function () { abrirProcessoNoPJe(numero); }, 600);
        });
    }

    // ── Injeção do botão (centro inferior) ───────────────────────────
    function injetarBotao() {
        if (!document.body) return;

        var existente = document.getElementById(ID_BOTAO);
        var painel = document.getElementById(ID_PAINEL);

        if (!naRotaDesdobrar() || !temTituloOrdem()) {
            if (existente) existente.remove();
            if (painel) painel.remove();
            return;
        }
        if (existente || painel) return;

        var btn = document.createElement('button');
        btn.id = ID_BOTAO;
        btn.type = 'button';
        btn.textContent = TEXTO_PADRAO;
        btn.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:999999;' +
            'padding:12px 22px;border:none;border-radius:8px;background:#1976d2;color:#fff;' +
            'font:bold 15px Arial,sans-serif;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);';
        btn.addEventListener('click', function () { aoClicar(btn); });
        document.body.appendChild(btn);
    }

    window.SisbExtrair = {
        injetarBotao: injetarBotao,
        montarRelatorio: montarRelatorio,
        naRotaDesdobrar: naRotaDesdobrar,
        temTituloOrdem: temTituloOrdem
    };
})();
