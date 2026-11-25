// ==UserScript==
// @name         PJeTools Argos Poupa Convênios
// @namespace    http://tampermonkey.net/
// @description  Módulo integrado do Argos Poupa Convênios: diálogo de seleção de partes (exclusão mútua entre polos), consulta API completa, regras Art. 131 CNC (Ofício Circular CR 124/2026), geração de PDFs por empresa e cálculo de convênios já cobertos para o fluxo Nova.
// @author       Silas
// ==/UserScript==
'use strict';

(function () {
    const API_BASE = window.location.origin + '/pje-argos-api/api';
    const DEFAULT_PAGE_SIZE = 500;
    const DEFAULT_TIMEOUT_MS = 60000;
    const MAX_ANOS_INFOJUD_POR_TIPO = 3;

    const showToast = window.showToast || function (texto) {
        console.log('[ArgosPoupa]', texto);
    };

    const TIPOS_CONSTRICAO = new Set([
        'SISBAJUD_BLOQUEIO',
        'CNIB_INDISPONIBILIDADE',
        'SERASAJUD_INCLUSAO',
    ]);

    // ── Helpers HTTP / Auth ──────────────────────────────────────────────
    function _xsrf() {
        const c = document.cookie
            .split(';')
            .map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));
        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
    }

    function _headers(extra) {
        const h = Object.assign({ Accept: 'application/json' }, extra || {});
        const x = _xsrf();
        if (x) h['X-XSRF-TOKEN'] = x;
        return h;
    }

    async function _fetchComTimeout(url, opts, timeoutMs) {
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), timeoutMs || DEFAULT_TIMEOUT_MS);
        try {
            const fullUrl = url.startsWith('http') ? url : (API_BASE + url);
            return await fetch(fullUrl, Object.assign({ credentials: 'include', signal: ctrl.signal }, opts || {}));
        } finally {
            clearTimeout(tid);
        }
    }

    async function _getJson(path, timeoutMs) {
        const t0 = performance.now();
        const r = await _fetchComTimeout(path, { method: 'GET', headers: _headers() }, timeoutMs);
        if (!r.ok) {
            const txt = await r.text().catch(() => '');
            throw new Error('HTTP ' + r.status + ' em ' + path + (txt ? ' — ' + txt.slice(0, 120) : ''));
        }
        const data = await r.json();
        return { data, ms: Math.round(performance.now() - t0) };
    }

    async function _getBytes(path, timeoutMs) {
        const r = await _fetchComTimeout(path, { method: 'GET', headers: _headers({ Accept: '*/*' }) }, timeoutMs);
        if (!r.ok) throw new Error('HTTP ' + r.status + ' ao baixar ' + path);
        const bytes = new Uint8Array(await r.arrayBuffer());
        return {
            bytes,
            contentType: (r.headers.get('content-type') || '').toLowerCase(),
            contentDisposition: r.headers.get('content-disposition') || '',
        };
    }

    // ── Identificação de processo e partes (funciona em /detalhe e /argos) ──
    function _idProcessoPje() {
        const m = window.location.pathname.match(/\/processo\/(\d+)/);
        return m ? m[1] : null;
    }

    function extrairNumeroProcesso() {
        const re = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;
        let m = decodeURIComponent(window.location.href).match(re);
        if (m) return m[0];
        m = (document.title || '').match(re);
        if (m) return m[0];
        const el = document.querySelector('.texto-numero-processo');
        if (el) {
            m = (el.textContent || '').match(re);
            if (m) return m[0];
        }
        return null;
    }

    async function _obterPartesProcesso(numeroProcesso) {
        const id = _idProcessoPje();
        if (id) {
            const h = _headers({ 'X-Grau-Instancia': '1' });
            const r = await _fetchComTimeout(
                window.location.origin + '/pje-comum-api/api/processos/id/' + id + '/partes',
                { method: 'GET', headers: h },
                15000
            );
            if (r.ok) {
                const raw = await r.json();
                const shape = (lista, polo) => (lista || []).map(p => ({
                    nome: String(p.nome || '').trim(),
                    documento: String(p.documento || '').replace(/\D/g, ''),
                    polo,
                }));
                return {
                    ativo: shape(raw.ATIVO, 'ATIVO'),
                    passivo: shape(raw.PASSIVO, 'PASSIVO'),
                };
            }
        }
        if (numeroProcesso) {
            const { data } = await _getJson('/processos/' + encodeURIComponent(numeroProcesso), 15000);
            const partes = data.partesProcessuais || [];
            const shape = polo => partes
                .filter(p => String(p.tipoPolo || '').toUpperCase() === polo)
                .map(p => ({
                    nome: String(p.nome || '').trim(),
                    documento: String(p.numeroCpj || '').replace(/\D/g, ''),
                    polo,
                }));
            return { ativo: shape('ATIVO'), passivo: shape('PASSIVO') };
        }
        return { ativo: [], passivo: [] };
    }

    // ── Diálogo de Seleção de Partes (exclusão mútua entre polos) ────────
    function _escapeHtml(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function _fmtDoc(doc) {
        const d = String(doc || '').replace(/\D/g, '');
        if (d.length === 11) return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        if (d.length === 14) return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        return d || 'sem documento';
    }

    /**
     * Abre modal para o usuário escolher as partes alvo da pesquisa.
     * - Reclamadas (PASSIVO) vêm marcadas por padrão.
     * - Reclamante(s) (ATIVO) vêm desmarcados por padrão.
     * - Exclusão mútua: marcar qualquer parte de um polo desmarca automaticamente
     *   todas as partes do outro polo (não é permitido misturar polos).
     * Retorna Promise<{ poloSelecionado, selecionadas, ativo, passivo } | null>.
     */
    function abrirDialogoPartes(partes, titulo) {
        return new Promise(resolve => {
            const prev = document.getElementById('pjetools-argos-partes-overlay');
            if (prev) prev.remove();

            const passivo = (partes && Array.isArray(partes.passivo) ? partes.passivo : []).map(p => ({
                nome: String(p.nome || '').trim(),
                documento: String(p.documento || '').replace(/\D/g, ''),
                polo: 'PASSIVO',
            }));
            const ativo = (partes && Array.isArray(partes.ativo) ? partes.ativo : []).map(p => ({
                nome: String(p.nome || '').trim(),
                documento: String(p.documento || '').replace(/\D/g, ''),
                polo: 'ATIVO',
            }));

            const overlay = document.createElement('div');
            overlay.id = 'pjetools-argos-partes-overlay';
            overlay.style.cssText = [
                'position:fixed', 'inset:0', 'z-index:999999',
                'background:rgba(0,0,0,.55)', 'display:flex',
                'align-items:center', 'justify-content:center',
                'font-family:system-ui,sans-serif', 'font-size:13px',
            ].join(';');

            const card = document.createElement('div');
            card.style.cssText = [
                'width:min(560px,92vw)', 'max-height:85vh', 'background:#111827',
                'color:#f3f4f6', 'border:1px solid #374151', 'border-radius:10px',
                'box-shadow:0 20px 60px rgba(0,0,0,.6)', 'display:flex',
                'flex-direction:column', 'overflow:hidden',
            ].join(';');

            const renderGrupo = (lista, polo, checkedDefault) => {
                if (!lista.length) {
                    return '<div style="color:#9ca3af;font-size:12px;padding:4px 0;">Nenhuma parte encontrada neste polo.</div>';
                }
                return lista.map((p, idx) => `
                    <label style="display:flex;align-items:flex-start;gap:8px;padding:6px 8px;border-radius:6px;cursor:pointer;background:#1f2937;margin-bottom:5px;">
                        <input type="checkbox" class="ap-chk-parte" data-polo="${polo}" data-idx="${idx}" ${checkedDefault ? 'checked' : ''} style="margin-top:2px;" />
                        <div style="flex:1;min-width:0;">
                            <div style="font-weight:600;word-break:break-word;">${_escapeHtml(p.nome || '(Sem nome)')}</div>
                            <div style="color:#9ca3af;font-size:11px;">${_escapeHtml(_fmtDoc(p.documento))}</div>
                        </div>
                    </label>
                `).join('');
            };

            card.innerHTML = `
                <div style="padding:12px 16px;background:#1f2937;border-bottom:1px solid #374151;display:flex;justify-content:space-between;align-items:center;">
                    <strong style="font-size:14px;">${_escapeHtml(titulo || 'Argos — Selecionar Partes')}</strong>
                    <button id="ap-btn-x" style="background:transparent;border:none;color:#9ca3af;font-size:18px;cursor:pointer;line-height:1;">&times;</button>
                </div>
                <div style="padding:10px 16px;background:#182030;border-bottom:1px solid #374151;color:#fbbf24;font-size:12px;">
                    Selecione apenas um polo por vez. Marcar o Reclamante desmarca automaticamente as Reclamadas (e vice-versa).
                </div>
                <div style="padding:12px 16px;overflow:auto;flex:1;">
                    <div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#60a5fa;font-weight:700;margin-bottom:6px;">
                        Polo Passivo — Reclamadas (${passivo.length})
                    </div>
                    ${renderGrupo(passivo, 'PASSIVO', true)}
                    <div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#34d399;font-weight:700;margin:12px 0 6px;">
                        Polo Ativo — Reclamantes (${ativo.length})
                    </div>
                    ${renderGrupo(ativo, 'ATIVO', false)}
                </div>
                <div style="padding:12px 16px;background:#1f2937;border-top:1px solid #374151;display:flex;justify-content:space-between;align-items:center;gap:10px;">
                    <span id="ap-resumo-sel" style="color:#9ca3af;font-size:12px;"></span>
                    <div style="display:flex;gap:8px;">
                        <button id="ap-btn-cancel" style="padding:6px 12px;background:#374151;color:#f3f4f6;border:none;border-radius:6px;cursor:pointer;">Cancelar</button>
                        <button id="ap-btn-ok" style="padding:6px 14px;background:#6f42c1;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;">Confirmar</button>
                    </div>
                </div>
            `;

            overlay.appendChild(card);
            document.body.appendChild(overlay);

            const chks = Array.from(card.querySelectorAll('.ap-chk-parte'));
            const btnOk = card.querySelector('#ap-btn-ok');
            const resumoEl = card.querySelector('#ap-resumo-sel');

            function atualizarEstado() {
                const marcados = chks.filter(c => c.checked);
                const polo = marcados.length ? marcados[0].getAttribute('data-polo') : null;
                btnOk.disabled = marcados.length === 0;
                btnOk.style.opacity = marcados.length ? '1' : '0.45';
                resumoEl.textContent = marcados.length
                    ? (marcados.length + ' parte(s) — Polo ' + polo)
                    : 'Nenhuma parte selecionada';
            }

            chks.forEach(chk => {
                chk.addEventListener('change', () => {
                    if (chk.checked) {
                        const meuPolo = chk.getAttribute('data-polo');
                        chks.forEach(outro => {
                            if (outro.getAttribute('data-polo') !== meuPolo) {
                                outro.checked = false;
                            }
                        });
                    }
                    atualizarEstado();
                });
            });

            function fechar(resultado) {
                overlay.remove();
                resolve(resultado);
            }

            card.querySelector('#ap-btn-x').addEventListener('click', () => fechar(null));
            card.querySelector('#ap-btn-cancel').addEventListener('click', () => fechar(null));
            overlay.addEventListener('click', ev => { if (ev.target === overlay) fechar(null); });

            btnOk.addEventListener('click', () => {
                const marcados = chks.filter(c => c.checked);
                if (!marcados.length) return;
                const poloSelecionado = marcados[0].getAttribute('data-polo');
                const selecionadas = marcados.map(c => {
                    const idx = Number(c.getAttribute('data-idx'));
                    return poloSelecionado === 'PASSIVO' ? passivo[idx] : ativo[idx];
                }).filter(Boolean);
                fechar({ poloSelecionado, selecionadas, ativo, passivo });
            });

            atualizarEstado();
        });
    }

    // ── Camada de API do Argos Poupa ─────────────────────────────────────
    async function buscarConvenios() {
        const { data, ms } = await _getJson('/convenios', 15000);
        const byId = {};
        for (const c of (data || [])) byId[c.id] = c;
        return { lista: data || [], byId, ms };
    }

    async function buscarTodasReaproveitaveis(docs, opts) {
        opts = opts || {};
        const tamanhoPagina = opts.tamanhoPagina || DEFAULT_PAGE_SIZE;
        const apenasLocalizacaoUsuario = !!opts.apenasLocalizacaoUsuario;
        const onProgress = typeof opts.onProgress === 'function' ? opts.onProgress : null;

        if (!docs || !docs.length) {
            return { totalRegistros: 0, qtdPaginas: 0, paginasLidas: 0, resultado: [], msTotal: 0 };
        }

        const t0 = performance.now();
        const todos = [];
        let pagina = 1;
        let qtdPaginas = 1;
        let totalRegistros = 0;

        while (pagina <= qtdPaginas) {
            const qs = new URLSearchParams();
            qs.set('pesquisarProcessos', 'true');
            qs.set('pesquisasRealizadasNaLocalizacaoUsuarioLogado', String(apenasLocalizacaoUsuario));
            for (const d of docs) qs.append('pesquisaRapidaMultiplaTarefas', d);
            qs.set('pagina', String(pagina));
            qs.set('tamanhoPagina', String(tamanhoPagina));

            if (onProgress) onProgress({ pagina, qtdPaginas, carregados: todos.length });

            const { data } = await _getJson('/consulta-tarefas-reaproveitaveis?' + qs.toString(), DEFAULT_TIMEOUT_MS);
            totalRegistros = data.totalRegistros ?? totalRegistros;
            qtdPaginas = data.qtdPaginas ?? 1;
            const lote = Array.isArray(data.resultado) ? data.resultado : [];
            for (const item of lote) todos.push(normalizarTarefa(item));

            if (!lote.length) break;
            pagina += 1;
        }

        return {
            totalRegistros,
            qtdPaginas,
            paginasLidas: pagina - 1,
            resultado: todos,
            msTotal: Math.round(performance.now() - t0),
        };
    }

    async function obterCertidaoReaproveitamentoPdf(numeroProcesso, idsTarefas) {
        const path = '/processos/' + encodeURIComponent(numeroProcesso) + '/tarefas-processo/certidao-avulsa-reaproveitamento';
        const r = await _fetchComTimeout(
            path,
            {
                method: 'POST',
                headers: _headers({ 'Content-Type': 'application/json', Accept: '*/*' }),
                body: JSON.stringify({
                    numeroProcesso,
                    idsTarefasReaproveitadas: idsTarefas,
                }),
            },
            30000
        );
        if (!r.ok) {
            const txt = await r.text().catch(() => '');
            throw new Error('HTTP ' + r.status + ' ao gerar certidão de reaproveitamento' + (txt ? ' — ' + txt.slice(0, 120) : ''));
        }
        return new Uint8Array(await r.arrayBuffer());
    }

    async function listarArquivosTarefa(idTarefa, idResultado) {
        const { data } = await _getJson('/tarefas/' + idTarefa + '/resultados/' + idResultado + '/arquivos', 20000);
        return Array.isArray(data) ? data : [];
    }

    async function baixarArquivoAnexo(idTarefa, idResultado, idArquivo) {
        return _getBytes(
            '/tarefas/' + idTarefa + '/resultados/' + idResultado + '/arquivos/' + idArquivo + '/conteudo/download',
            60000
        );
    }

    // ── Normalização & Regras Art. 131 CNC (Ofício Circular CR 124/2026) ─
    function normalizarTarefa(it) {
        const ano = it.anoDocumentoInfojud || it.anodocumentoinfojud || null;
        const ocultaAno = !!(it.ocultaAnoNaExibicao ?? it.ocultaanonaexibicao);
        const nomeBase = it.nomeTarefa || it.nometarefa || it.tipoTarefa || it.tipotarefa || '';
        const rotuloTarefa = (ano && !ocultaAno) ? (nomeBase + ' (' + ano + ')') : nomeBase;
        return {
            idTarefa: it.idTarefa ?? it.idtarefa,
            idResultado: it.idResultado ?? it.idresultado,
            idConvenio: it.idconvenio ?? it.idConvenio ?? null,
            documentoExecutado: String(it.documentoExecutado || it.documentoexecutado || '').replace(/\D/g, ''),
            nomeExecutado: String(it.nomeExecutado || it.nomeexecutado || '').trim(),
            executadoPessoaFisica: !!(it.executadoPessoaFisica ?? it.executadopessoafisica),
            numeroProcessoOrigem: it.numeroProcesso || it.numeroprocesso || '',
            nomeOrgaoJulgador: it.nomeOrgaoJulgador || it.nomeorgaojulgador || '',
            tipoTarefa: it.tipoTarefa || it.tipotarefa || '',
            nomeTarefa: nomeBase,
            rotuloTarefa,
            anoDocumentoInfojud: ano,
            dataFinalizacao: it.dataFinalizacao || it.datafinalizacao || '',
            resultadoPositivo: !!(it.resultadoPositivo ?? it.resultadopositivo),
            possuiAnexo: !!(it.possuiAnexo ?? it.possuianexo),
            reaproveitamento: !!it.reaproveitamento,
            sempreReaproveitavel: !!(it.semprereaproveitavel ?? it.sempreReaproveitavel),
            diasReaproveitamento: it.quantidadediasreaproveitamentotarefa ?? null,
            ocultaAnoNaExibicao: ocultaAno,
            statusTarefa: it.statustarefa || it.statusTarefa || '',
        };
    }

    function _subtrairMeses(dataRef, meses) {
        const d = new Date(dataRef.getTime());
        const diaOriginal = d.getDate();
        d.setMonth(d.getMonth() - meses);
        if (d.getDate() < diaOriginal) d.setDate(0);
        return d;
    }

    function avaliarElegibilidadeArt131(tarefa, dataRef) {
        const agora = dataRef ? new Date(dataRef) : new Date();
        const tipo = String(tarefa.tipoTarefa || '').toUpperCase();

        if (TIPOS_CONSTRICAO.has(tipo)) {
            return { elegivel: false, regra: 'Constrição (§ 4º)', motivo: 'Ato de constrição não reaproveitável', prazoMeses: 0 };
        }

        const dtFin = tarefa.dataFinalizacao ? new Date(tarefa.dataFinalizacao) : null;
        const diasDecorridos = (dtFin && !Number.isNaN(dtFin.getTime()))
            ? Math.floor((agora.getTime() - dtFin.getTime()) / (24 * 60 * 60 * 1000))
            : null;

        if (tipo.startsWith('INFOJUD_') || tarefa.idConvenio === 3 || tarefa.sempreReaproveitavel) {
            return {
                elegivel: true,
                regra: 'INFOJUD (3 anos)',
                motivo: 'Válida a qualquer tempo (art. 131, c)',
                prazoMeses: null,
                diasDecorridos,
            };
        }

        let prazoMeses = 12;
        let rotuloRegra = 'Demais (12 meses)';
        if (tipo.startsWith('ARISP_') || tarefa.idConvenio === 4) {
            prazoMeses = 12;
            rotuloRegra = 'ARISP (12 meses)';
        } else if (tipo.startsWith('RENAJUD_') || tarefa.idConvenio === 2) {
            prazoMeses = 6;
            rotuloRegra = 'RENAJUD (6 meses)';
        }

        if (!dtFin || Number.isNaN(dtFin.getTime())) {
            return { elegivel: false, regra: rotuloRegra, motivo: 'Sem data de finalização', prazoMeses, diasDecorridos: null };
        }

        const limite = _subtrairMeses(agora, prazoMeses);
        const dentroDoPrazo = dtFin.getTime() >= limite.getTime();
        return {
            elegivel: dentroDoPrazo,
            regra: rotuloRegra,
            motivo: dentroDoPrazo
                ? ('Válida — realizada há ' + diasDecorridos + 'd')
                : ('Expirada — realizada há ' + diasDecorridos + 'd (limite ' + prazoMeses + 'm)'),
            prazoMeses,
            diasDecorridos,
        };
    }

    function resumirPorExecutadoETipo(itens) {
        const mapa = new Map();
        for (const it of itens) {
            const anoChave = (it.anoDocumentoInfojud && !it.ocultaAnoNaExibicao) ? String(it.anoDocumentoInfojud) : '';
            const chave = [it.documentoExecutado, it.tipoTarefa, anoChave].join('|');
            const atual = mapa.get(chave);
            if (!atual || String(it.dataFinalizacao) > String(atual.dataFinalizacao)) {
                mapa.set(chave, it);
            }
        }
        return Array.from(mapa.values()).sort((a, b) =>
            a.documentoExecutado.localeCompare(b.documentoExecutado) ||
            (a.resultadoPositivo === b.resultadoPositivo ? 0 : (a.resultadoPositivo ? -1 : 1)) ||
            a.rotuloTarefa.localeCompare(b.rotuloTarefa)
        );
    }

    function selecionarElegiveisArt131(itens, dataRef, opts) {
        opts = opts || {};
        const maxAnosInfojud = opts.maxAnosInfojud || MAX_ANOS_INFOJUD_POR_TIPO;
        const agora = dataRef ? new Date(dataRef) : new Date();
        const avaliadas = itens.map(it => Object.assign({}, it, { art131: avaliarElegibilidadeArt131(it, agora) }));
        const validas = avaliadas.filter(it => it.art131.elegivel);
        const dedup = resumirPorExecutadoETipo(validas);

        const gruposInfojud = new Map();
        const naoInfojudAnual = [];
        for (const it of dedup) {
            const isInfojudAnual = (String(it.tipoTarefa || '').toUpperCase().startsWith('INFOJUD_') || it.idConvenio === 3)
                && it.anoDocumentoInfojud
                && !it.ocultaAnoNaExibicao;
            if (!isInfojudAnual) {
                naoInfojudAnual.push(it);
                continue;
            }
            const chave = it.documentoExecutado + '|' + it.tipoTarefa;
            if (!gruposInfojud.has(chave)) gruposInfojud.set(chave, []);
            gruposInfojud.get(chave).push(it);
        }

        const descartadasPorLimiteAnos = [];
        const infojudMantidas = [];
        for (const lista of gruposInfojud.values()) {
            lista.sort((a, b) =>
                Number(b.anoDocumentoInfojud) - Number(a.anoDocumentoInfojud) ||
                String(b.dataFinalizacao).localeCompare(String(a.dataFinalizacao))
            );
            lista.forEach((it, idx) => {
                if (idx < maxAnosInfojud) {
                    infojudMantidas.push(it);
                } else {
                    descartadasPorLimiteAnos.push(Object.assign({}, it, {
                        art131: Object.assign({}, it.art131, {
                            elegivel: false,
                            motivo: 'Fora dos ' + maxAnosInfojud + ' anos mais recentes disponíveis de ' + it.nomeTarefa,
                        }),
                    }));
                }
            });
        }

        const elegiveis = naoInfojudAnual.concat(infojudMantidas).sort((a, b) =>
            a.documentoExecutado.localeCompare(b.documentoExecutado) ||
            (a.resultadoPositivo === b.resultadoPositivo ? 0 : (a.resultadoPositivo ? -1 : 1)) ||
            a.rotuloTarefa.localeCompare(b.rotuloTarefa)
        );

        const porEmpresa = {};
        for (const it of elegiveis) {
            const doc = it.documentoExecutado || 'SEM_DOC';
            if (!porEmpresa[doc]) {
                porEmpresa[doc] = { documento: doc, nomeExecutado: it.nomeExecutado, elegiveis: [], positivas: 0, negativas: 0 };
            }
            porEmpresa[doc].elegiveis.push(it);
            if (it.resultadoPositivo) porEmpresa[doc].positivas += 1;
            else porEmpresa[doc].negativas += 1;
        }
        for (const emp of Object.values(porEmpresa)) {
            emp.elegiveis = _ordenarPositivasDepoisNegativas(emp.elegiveis);
        }

        return {
            todasAvaliadas: avaliadas,
            elegiveis,
            expiradasOuExcluidas: avaliadas.filter(it => !it.art131.elegivel).concat(descartadasPorLimiteAnos),
            porEmpresa,
        };
    }

    // ── Cálculo de convênios já cobertos para exclusão em "Argos -> Nova" ─
    const MAPA_TIPO_PARA_CHECKBOX = {
        RENAJUD_CONSULTA: 'RENAJUD',
        ARISP_CONSULTA: 'ARISP',
        INFOJUD_CONSULTA_DIRPF: 'DIRPF',
        INFOJUD_CONSULTA_DECRED: 'DECRED',
        INFOJUD_CONSULTA_DOI: 'DOI',
        INFOJUD_CONSULTA_DIMOB: 'DIMOB',
    };

    /**
     * Calcula quais checkboxes da tela "Nova Ordem" no Argos devem ser EXCLUÍDOS
     * porque TODAS as partes alvo selecionadas já possuem pesquisa reaproveitável
     * válida (Art. 131 CNC) para aquele convênio/sub-opção.
     * - SISBAJUD, CNIB, SERASAJUD nunca são excluídos (atos de constrição).
     * - INFOJUD (pai) só é excluído se TODAS as sub-opções aplicáveis (DIRPF se CPF,
     *   DECRED, DOI, DIMOB) já estiverem cobertas.
     */
    function calcularConveniosExcluidos(docsAlvo, elegiveisArt131, temCpf) {
        const docs = Array.from(new Set((docsAlvo || []).map(d => String(d || '').replace(/\D/g, '')).filter(Boolean)));
        if (!docs.length || !elegiveisArt131 || !elegiveisArt131.length) return [];

        const cobertosPorDoc = new Map();
        for (const d of docs) cobertosPorDoc.set(d, new Set());

        for (const t of elegiveisArt131) {
            const doc = String(t.documentoExecutado || '').replace(/\D/g, '');
            const set = cobertosPorDoc.get(doc);
            if (!set) continue;
            const cb = MAPA_TIPO_PARA_CHECKBOX[String(t.tipoTarefa || '').toUpperCase()];
            if (cb) set.add(cb);
        }

        const candidatos = ['RENAJUD', 'ARISP', 'DIRPF', 'DECRED', 'DOI', 'DIMOB'];
        const excluidos = candidatos.filter(cb =>
            docs.every(d => cobertosPorDoc.get(d).has(cb))
        );

        const subInfojud = temCpf ? ['DIRPF', 'DECRED', 'DOI', 'DIMOB'] : ['DECRED', 'DOI', 'DIMOB'];
        if (subInfojud.every(sub => excluidos.includes(sub))) {
            excluidos.push('INFOJUD');
        }
        return excluidos;
    }

    // ── PDF Único & PDFs por Empresa ─────────────────────────────────────
    function _getPdfLib() {
        const lib = (typeof PDFLib !== 'undefined' && PDFLib)
            || window.PDFLib
            || (typeof unsafeWindow !== 'undefined' && unsafeWindow.PDFLib);
        if (!lib || !lib.PDFDocument) {
            throw new Error('PDFLib não disponível no PJeTools.');
        }
        return lib;
    }

    function _isPdfBytes(u8) {
        return u8 && u8.length >= 5 && u8[0] === 0x25 && u8[1] === 0x50 && u8[2] === 0x44 && u8[3] === 0x46 && u8[4] === 0x2D;
    }

    const IMG_MIN_BYTES_OTIMIZAR = 50 * 1024;
    const PDF_MIN_BYTES_OTIMIZAR = 300 * 1024;
    const IMG_MAX_LADO_PX = 1240; // ~120-150 DPI em A4
    const IMG_JPEG_QUALIDADE = 0.58;

    async function _otimizarImagemBytesGrayscale(bytes, mime, maxLado, qualidade) {
        maxLado = maxLado || IMG_MAX_LADO_PX;
        qualidade = qualidade || IMG_JPEG_QUALIDADE;
        if (!bytes || bytes.byteLength < IMG_MIN_BYTES_OTIMIZAR) return null;
        if (typeof createImageBitmap !== 'function') return null;
        try {
            const blobIn = new Blob([bytes], { type: mime || 'image/jpeg' });
            const bmp = await createImageBitmap(blobIn);
            try {
                const origW = bmp.width;
                const origH = bmp.height;
                if (!origW || !origH) return null;
                const escala = Math.min(1, maxLado / Math.max(origW, origH));
                const w = Math.max(1, Math.round(origW * escala));
                const h = Math.max(1, Math.round(origH * escala));

                let canvas;
                let ctx;
                if (typeof OffscreenCanvas !== 'undefined') {
                    canvas = new OffscreenCanvas(w, h);
                    ctx = canvas.getContext('2d');
                } else {
                    canvas = document.createElement('canvas');
                    canvas.width = w;
                    canvas.height = h;
                    ctx = canvas.getContext('2d');
                }
                if (!ctx) return null;

                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, w, h);
                if ('filter' in ctx) {
                    ctx.filter = 'grayscale(100%)';
                    ctx.drawImage(bmp, 0, 0, w, h);
                } else {
                    ctx.drawImage(bmp, 0, 0, w, h);
                    const imgData = ctx.getImageData(0, 0, w, h);
                    const d = imgData.data;
                    for (let i = 0; i < d.length; i += 4) {
                        const g = (d[i] * 77 + d[i + 1] * 150 + d[i + 2] * 29) >> 8;
                        d[i] = d[i + 1] = d[i + 2] = g;
                    }
                    ctx.putImageData(imgData, 0, 0);
                }

                let blobOut;
                if (typeof canvas.convertToBlob === 'function') {
                    blobOut = await canvas.convertToBlob({ type: 'image/jpeg', quality: qualidade });
                } else {
                    blobOut = await new Promise((res, rej) =>
                        canvas.toBlob(b => (b ? res(b) : rej(new Error('toBlob null'))), 'image/jpeg', qualidade)
                    );
                }
                const outBytes = new Uint8Array(await blobOut.arrayBuffer());
                if (outBytes.byteLength >= bytes.byteLength) return null;
                return { bytes: outBytes, width: w, height: h };
            } finally {
                if (typeof bmp.close === 'function') bmp.close();
            }
        } catch (e) {
            return null;
        }
    }

    async function _otimizarPdfAnexoAntesDeMesclar(srcDoc, rawLen) {
        if (!rawLen || rawLen < PDF_MIN_BYTES_OTIMIZAR) return 0;
        const lib = _getPdfLib();
        const PDFName = lib.PDFName;
        const PDFNumber = lib.PDFNumber;
        const PDFRawStream = lib.PDFRawStream;
        if (!PDFName || !PDFNumber || !PDFRawStream || !srcDoc.context) return 0;

        let otimizadas = 0;
        const kSubtype = PDFName.of('Subtype');
        const kImage = PDFName.of('Image');
        const kFilter = PDFName.of('Filter');
        const kDct = PDFName.of('DCTDecode');
        const kWidth = PDFName.of('Width');
        const kHeight = PDFName.of('Height');
        const kColorSpace = PDFName.of('ColorSpace');
        const kDeviceRGB = PDFName.of('DeviceRGB');
        const kBpc = PDFName.of('BitsPerComponent');
        const kLength = PDFName.of('Length');
        const kDecodeParms = PDFName.of('DecodeParms');
        const kSmask = PDFName.of('SMask');

        for (const [, obj] of srcDoc.context.enumerateIndirectObjects()) {
            if (!(obj instanceof PDFRawStream)) continue;
            const dict = obj.dict;
            if (!dict || dict.get(kSubtype) !== kImage) continue;
            if (dict.get(kSmask)) continue; // preserva máscaras alfa intactas
            const flt = dict.get(kFilter);
            if (flt !== kDct) continue;
            const contents = obj.contents;
            if (!contents || contents.byteLength < IMG_MIN_BYTES_OTIMIZAR) continue;

            const ot = await _otimizarImagemBytesGrayscale(contents, 'image/jpeg');
            if (!ot) continue;

            obj.contents = ot.bytes;
            dict.set(kWidth, PDFNumber.of(ot.width));
            dict.set(kHeight, PDFNumber.of(ot.height));
            dict.set(kColorSpace, kDeviceRGB);
            dict.set(kBpc, PDFNumber.of(8));
            dict.set(kLength, PDFNumber.of(ot.bytes.byteLength));
            dict.delete(kDecodeParms);
            otimizadas += 1;
        }
        return otimizadas;
    }

    async function _anexarBytesAoPdf(pdfDestino, bytes, contentType, nomeArquivo, avisos) {
        const { PDFDocument } = _getPdfLib();
        if (_isPdfBytes(bytes) || contentType.includes('pdf')) {
            const src = await PDFDocument.load(bytes, { ignoreEncryption: true });
            await _otimizarPdfAnexoAntesDeMesclar(src, bytes.byteLength);
            const paginas = await pdfDestino.copyPages(src, src.getPageIndices());
            for (const p of paginas) pdfDestino.addPage(p);
            return paginas.length;
        }
        if (contentType.includes('png') || /\.png$/i.test(nomeArquivo || '')) {
            const ot = await _otimizarImagemBytesGrayscale(bytes, 'image/png');
            const img = ot ? await pdfDestino.embedJpg(ot.bytes) : await pdfDestino.embedPng(bytes);
            const page = pdfDestino.addPage([img.width, img.height]);
            page.drawImage(img, { x: 0, y: 0, width: img.width, height: img.height });
            return 1;
        }
        if (contentType.includes('jpeg') || contentType.includes('jpg') || /\.jpe?g$/i.test(nomeArquivo || '')) {
            const ot = await _otimizarImagemBytesGrayscale(bytes, 'image/jpeg');
            const img = await pdfDestino.embedJpg(ot ? ot.bytes : bytes);
            const page = pdfDestino.addPage([img.width, img.height]);
            page.drawImage(img, { x: 0, y: 0, width: img.width, height: img.height });
            return 1;
        }
        avisos.push('Ignorado (não-PDF/imagem): ' + (nomeArquivo || 'sem nome') + ' [' + contentType + ']');
        return 0;
    }

    function _dispararDownloadBlob(bytes, nomeArquivo) {
        const blob = new Blob([bytes], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nomeArquivo;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 15000);
    }

    function _siglaPesquisa(t, incluirAno) {
        const tipo = String(t.tipoTarefa || '').toUpperCase();
        const mapa = {
            ARISP_CONSULTA: 'ARISP',
            RENAJUD_CONSULTA: 'Renajud',
            INFOJUD_CONSULTA_DOI: 'DOI',
            INFOJUD_CONSULTA_DIMOB: 'DIMOB',
            INFOJUD_CONSULTA_ECF: 'ECF',
            INFOJUD_CONSULTA_E_FINANCEIRA: 'e-Financeira',
            INFOJUD_CONSULTA_DECRED: 'DECRED',
            INFOJUD_CONSULTA_DIRPF: 'DIRPF',
            INFOJUD_CONSULTA_DIRPJ: 'DIRPJ',
            INFOJUD_CONSULTA_DITR: 'DITR',
            SISBAJUD_BLOQUEIO: 'Sisbajud',
            CNIB_INDISPONIBILIDADE: 'CNIB',
            SERASAJUD_INCLUSAO: 'Serasajud',
        };
        let base = mapa[tipo];
        if (!base) {
            base = String(t.nomeTarefa || t.rotuloTarefa || tipo)
                .replace(/^Consulta\s+/i, '')
                .replace(/\s+(no|na)\s+(INFOJUD|ARISP|RENAJUD|SISBAJUD)$/i, '')
                .replace(/\s*\(Consulta\)$/i, '')
                .trim();
        }
        if (incluirAno && t.anoDocumentoInfojud) return base + ' ' + t.anoDocumentoInfojud;
        return base;
    }

    function _sanitizarNomeArquivo(nome) {
        let limpo = String(nome || 'documento')
            .replace(/[\\/:*?"<>|]+/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
            .replace(/\.+$/, '');
        if (limpo.length > 180) limpo = limpo.slice(0, 177).trim() + '...';
        return limpo;
    }

    function _ordenarPositivasDepoisNegativas(tarefas) {
        return tarefas.slice().sort((a, b) => {
            if (a.resultadoPositivo !== b.resultadoPositivo) return a.resultadoPositivo ? -1 : 1;
            return _siglaPesquisa(a, true).localeCompare(_siglaPesquisa(b, true));
        });
    }

    function _normCmp(s) {
        return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().trim();
    }

    function _abreviarNomesEmpresas(grupos) {
        const entries = grupos.map(g => {
            const tokens = String(g.nomeEmpresa || g.documento || 'Executado')
                .replace(/[,.;:]+/g, ' ')
                .replace(/\s+/g, ' ')
                .trim()
                .split(' ')
                .filter(Boolean);
            return { doc: g.documento, tokens, len: 1 };
        });

        let houveColisao = true;
        while (houveColisao) {
            houveColisao = false;
            const contagem = new Map();
            for (const e of entries) {
                const chave = _normCmp(e.tokens.slice(0, e.len).join(' '));
                contagem.set(chave, (contagem.get(chave) || 0) + 1);
            }
            for (const e of entries) {
                const chave = _normCmp(e.tokens.slice(0, e.len).join(' '));
                if (contagem.get(chave) > 1 && e.len < e.tokens.length) {
                    e.len += 1;
                    houveColisao = true;
                }
            }
        }

        const mapa = new Map();
        const usados = new Map();
        for (const e of entries) {
            const curto = e.tokens.slice(0, e.len).join(' ') || e.doc;
            const chave = _normCmp(curto);
            usados.set(chave, (usados.get(chave) || 0) + 1);
            mapa.set(e.doc, curto);
        }
        for (const e of entries) {
            const curto = mapa.get(e.doc);
            if (usados.get(_normCmp(curto)) > 1 && e.doc && e.doc !== 'SEM_DOC') {
                mapa.set(e.doc, curto + ' ' + e.doc.slice(-4));
            }
        }
        return mapa;
    }

    function _extrairMatriculaECartorioTexto(texto) {
        const s = String(texto || '').replace(/[_]+/g, ' ').replace(/\s+/g, ' ').trim();
        if (!s) return { matricula: '', cartorio: '' };

        let matricula = '';
        const mMat = s.match(/(?:matr[ií]cula|mat\.?)\s*(?:n[º°o\.]*)?\s*[:\-]?\s*(\d[\d\.\-]{1,12})/i);
        if (mMat) {
            matricula = mMat[1].replace(/\./g, '').replace(/-$/, '');
        }

        let cartorio = '';
        const mCri = s.match(/(\d+\s*[º°oª]?\s*(?:oficial\s+de\s+)?(?:registro\s+de\s+im[oó]veis|c\.?\s*r\.?\s*i\.?|r\.?\s*i\.?)(?:\s+(?:de|da|do)\s+[A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,2})?)/i);
        if (mCri) {
            cartorio = mCri[1]
                .replace(/oficial\s+de\s+registro\s+de\s+im[oó]veis/i, 'CRI')
                .replace(/registro\s+de\s+im[oó]veis/i, 'CRI')
                .replace(/c\.?\s*r\.?\s*i\.?/i, 'CRI')
                .replace(/\s+/g, ' ')
                .trim();
        } else {
            const mCart = s.match(/(cart[oó]rio\s+[A-Za-zÀ-ÿ0-9º°ª\-]+(?:\s+[A-Za-zÀ-ÿ0-9º°ª\-]+){0,3})/i);
            if (mCart) cartorio = mCart[1].replace(/\s+/g, ' ').trim();
        }
        return { matricula, cartorio };
    }

    function _extrairInfoArispDeFontes(fontesTexto) {
        let matricula = '';
        let cartorio = '';
        for (const f of (fontesTexto || [])) {
            const info = _extrairMatriculaECartorioTexto(f);
            if (!matricula && info.matricula) matricula = info.matricula;
            if (!cartorio && info.cartorio) cartorio = info.cartorio;
            if (matricula && cartorio) break;
        }
        const partes = [];
        if (matricula) partes.push('Mat ' + matricula);
        if (cartorio) partes.push(cartorio);
        return partes.join(' - ');
    }

    function _extrairTextoRapidoPdfBytes(u8) {
        if (!u8 || !u8.length) return '';
        try {
            const fatia = u8.subarray(0, Math.min(u8.length, 65536));
            const dec = new TextDecoder('latin1').decode(fatia);
            return dec.replace(/[^\x20-\x7E\xC0-\xFF]/g, ' ').replace(/\s+/g, ' ');
        } catch (e) {
            return '';
        }
    }

    function _montarNomeArquivoEmpresa(nomeEmpresa, tarefasOrdenadas) {
        const contagemTipo = {};
        for (const t of tarefasOrdenadas) {
            const k = t.tipoTarefa || t.nomeTarefa || '';
            contagemTipo[k] = (contagemTipo[k] || 0) + 1;
        }
        const itensRotulo = [];
        const vistos = new Set();
        for (const t of tarefasOrdenadas) {
            const k = t.tipoTarefa || t.nomeTarefa || '';
            const sigla = _siglaPesquisa(t, contagemTipo[k] > 1);
            const tag = sigla + ' ' + (t.resultadoPositivo ? 'OK' : 'NEG');
            if (!vistos.has(tag)) {
                vistos.add(tag);
                itensRotulo.push(tag);
            }
        }
        const empresaLimpa = String(nomeEmpresa || 'Executado').replace(/\s+/g, ' ').trim();
        return _sanitizarNomeArquivo(empresaLimpa + ' (' + itensRotulo.join(', ') + ')') + '.pdf';
    }

    async function gerarPdfUnico(numeroProcesso, tarefasSelecionadas, opts) {
        opts = opts || {};
        const num = numeroProcesso || extrairNumeroProcesso();
        if (!num) throw new Error('Número do processo não informado.');
        if (!tarefasSelecionadas || !tarefasSelecionadas.length) {
            throw new Error('Selecione ao menos uma pesquisa para gerar o PDF.');
        }

        const tarefasOrdenadas = _ordenarPositivasDepoisNegativas(tarefasSelecionadas);
        const incluirCertidao = opts.incluirCertidao !== false;
        const baixarArquivo = opts.download !== false;
        const onStatus = typeof opts.onStatus === 'function' ? opts.onStatus : function () {};

        const { PDFDocument } = _getPdfLib();
        const pdfFinal = await PDFDocument.create();
        const avisos = [];
        const resumoArquivos = [];
        let totalPaginas = 0;

        const fontesArisp = [];
        if (opts.enriquecerNomeArisp) {
            for (const t of tarefasOrdenadas) {
                fontesArisp.push(t.rotuloTarefa || '', t.nomeTarefa || '', t.descricaoResultado || '', t.observacao || '');
            }
        }

        if (incluirCertidao) {
            onStatus('Gerando certidão/sumário no Argos...');
            const ids = Array.from(new Set(tarefasOrdenadas.map(t => t.idTarefa).filter(Boolean)));
            const certBytes = await obterCertidaoReaproveitamentoPdf(num, ids);
            if (opts.enriquecerNomeArisp) fontesArisp.push(_extrairTextoRapidoPdfBytes(certBytes));
            const pagsCert = await _anexarBytesAoPdf(pdfFinal, certBytes, 'application/pdf', 'Certidao_Reaproveitamento.pdf', avisos);
            totalPaginas += pagsCert;
            resumoArquivos.push({ origem: 'certidao', nome: 'Certidão de Reaproveitamento', paginas: pagsCert, bytes: certBytes.byteLength });
        }

        const tarefasComAnexo = tarefasOrdenadas.filter(t => t.possuiAnexo && t.idTarefa && t.idResultado);
        const filaDownloads = [];
        for (let i = 0; i < tarefasComAnexo.length; i++) {
            const t = tarefasComAnexo[i];
            onStatus('Listando anexos (' + (i + 1) + '/' + tarefasComAnexo.length + ') — ' + t.rotuloTarefa + '...');
            try {
                const arqs = await listarArquivosTarefa(t.idTarefa, t.idResultado);
                for (const arq of arqs) {
                    if (opts.enriquecerNomeArisp && arq && arq.nomeArquivo) fontesArisp.push(arq.nomeArquivo);
                    filaDownloads.push({ tarefa: t, arquivo: arq });
                }
            } catch (err) {
                avisos.push('Falha ao listar anexos tarefa ' + t.idTarefa + ': ' + (err.message || err));
            }
        }

        for (let i = 0; i < filaDownloads.length; i++) {
            const { tarefa, arquivo } = filaDownloads[i];
            const nomeArq = arquivo.nomeArquivo || ('anexo_' + arquivo.id + '.pdf');
            onStatus('Baixando e mesclando anexo ' + (i + 1) + '/' + filaDownloads.length + ': ' + nomeArq);
            try {
                const { bytes, contentType } = await baixarArquivoAnexo(tarefa.idTarefa, tarefa.idResultado, arquivo.id);
                if (opts.enriquecerNomeArisp && (_isPdfBytes(bytes) || contentType.includes('pdf'))) {
                    fontesArisp.push(_extrairTextoRapidoPdfBytes(bytes));
                }
                const pags = await _anexarBytesAoPdf(pdfFinal, bytes, contentType, nomeArq, avisos);
                totalPaginas += pags;
                resumoArquivos.push({
                    origem: 'anexo',
                    idTarefa: tarefa.idTarefa,
                    rotuloTarefa: tarefa.rotuloTarefa,
                    resultadoPositivo: tarefa.resultadoPositivo,
                    idArquivo: arquivo.id,
                    nome: nomeArq,
                    paginas: pags,
                    bytes: bytes.byteLength,
                });
            } catch (err) {
                avisos.push('Falha ao mesclar "' + nomeArq + '" (tarefa ' + tarefa.idTarefa + '): ' + (err.message || err));
            }
        }

        const MAX_PDF_BYTES = Math.floor(9.5 * 1024 * 1024); // margem segura < 10 MB
        const SAVE_OPTS_COMPRIMIDO = { useObjectStreams: true, addDefaultPage: false };

        function _nomePartePdf(nomeBase, parteIdx, totalPartes) {
            if (totalPartes <= 1) return nomeBase;
            const semExt = String(nomeBase || 'documento.pdf').replace(/\.pdf$/i, '');
            return _sanitizarNomeArquivo(semExt + ' - Parte ' + parteIdx + ' de ' + totalPartes) + '.pdf';
        }

        async function _salvarFatia(pdfOrigem, inicio, fim) {
            const sub = await PDFDocument.create();
            const indices = [];
            for (let p = inicio; p < fim; p++) indices.push(p);
            const copiadas = await sub.copyPages(pdfOrigem, indices);
            for (const pg of copiadas) sub.addPage(pg);
            return await sub.save(SAVE_OPTS_COMPRIMIDO);
        }

        async function _dividirPdfAteLimite(pdfOrigem, bytesIniciais, maxBytes) {
            const totalPgs = pdfOrigem.getPageCount();
            if (bytesIniciais.byteLength <= maxBytes || totalPgs <= 1) {
                return [{ bytes: bytesIniciais, paginas: totalPgs }];
            }

            const partes = [];
            const mediaPorPag = Math.max(1, bytesIniciais.byteLength / totalPgs);
            let cursor = 0;

            while (cursor < totalPgs) {
                const restantes = totalPgs - cursor;
                let qtd = Math.max(1, Math.min(restantes, Math.floor((maxBytes * 0.92) / mediaPorPag)));
                onStatus('Compactando e dividindo parte ' + (partes.length + 1) + ' (págs ' + (cursor + 1) + '-' + (cursor + qtd) + '/' + totalPgs + ')...');
                let sliceBytes = await _salvarFatia(pdfOrigem, cursor, cursor + qtd);

                // Se estourou o limite, reduz com busca binária rápida
                if (sliceBytes.byteLength > maxBytes && qtd > 1) {
                    let lo = 1;
                    let hi = qtd - 1;
                    let melhorQtd = 1;
                    let melhorBytes = null;
                    while (lo <= hi) {
                        const mid = Math.floor((lo + hi) / 2);
                        const cand = await _salvarFatia(pdfOrigem, cursor, cursor + mid);
                        if (cand.byteLength <= maxBytes) {
                            melhorQtd = mid;
                            melhorBytes = cand;
                            lo = mid + 1;
                        } else {
                            hi = mid - 1;
                        }
                    }
                    qtd = melhorQtd;
                    sliceBytes = melhorBytes || await _salvarFatia(pdfOrigem, cursor, cursor + 1);
                } else if (sliceBytes.byteLength < maxBytes * 0.72 && cursor + qtd < totalPgs) {
                    // Aproveita folga sem excesso de tentativas (no máx. 2 passos de expansão)
                    for (let step = 0; step < 2 && cursor + qtd < totalPgs; step++) {
                        const fator = Math.min(1.6, (maxBytes * 0.92) / Math.max(1, sliceBytes.byteLength));
                        const novaQtd = Math.min(totalPgs - cursor, Math.max(qtd + 1, Math.floor(qtd * fator)));
                        if (novaQtd <= qtd) break;
                        const cand = await _salvarFatia(pdfOrigem, cursor, cursor + novaQtd);
                        if (cand.byteLength <= maxBytes) {
                            qtd = novaQtd;
                            sliceBytes = cand;
                        } else {
                            break;
                        }
                    }
                }

                partes.push({ bytes: sliceBytes, paginas: qtd });
                cursor += qtd;
            }
            return partes;
        }

        onStatus('Comprimindo e salvando PDF (' + totalPaginas + ' páginas)...');
        const pdfBytes = await pdfFinal.save(SAVE_OPTS_COMPRIMIDO);
        let nomeSaida = opts.nomeArquivo || ('Poupa Convenios - ' + num + '.pdf');
        if (opts.enriquecerNomeArisp) {
            const detalheArisp = _extrairInfoArispDeFontes(fontesArisp);
            if (detalheArisp) {
                const baseEmp = opts.nomeCurtoEmpresa || 'Executado';
                nomeSaida = _sanitizarNomeArquivo(baseEmp + ' (ARISP OK - ' + detalheArisp + ')') + '.pdf';
            }
        }
        const limiteBytes = opts.maxBytes || MAX_PDF_BYTES;
        const partes = await _dividirPdfAteLimite(pdfFinal, pdfBytes, limiteBytes);

        const arquivosGerados = [];
        for (let i = 0; i < partes.length; i++) {
            const p = partes[i];
            const nomeParte = _nomePartePdf(nomeSaida, i + 1, partes.length);
            if (baixarArquivo) {
                _dispararDownloadBlob(p.bytes, nomeParte);
                if (i < partes.length - 1) await new Promise(r => setTimeout(r, 400));
            }
            arquivosGerados.push({
                nomeArquivo: nomeParte,
                totalPaginas: p.paginas,
                bytesFinal: p.bytes.byteLength,
                parte: i + 1,
                totalPartes: partes.length,
            });
        }

        return {
            nomeArquivo: arquivosGerados[0] ? arquivosGerados[0].nomeArquivo : nomeSaida,
            totalPaginas,
            bytesFinal: arquivosGerados.reduce((acc, a) => acc + a.bytesFinal, 0),
            partes: arquivosGerados,
            tarefasProcessadas: tarefasOrdenadas.length,
            anexosMesclados: resumoArquivos.filter(x => x.origem === 'anexo').length,
            resumoArquivos,
            avisos,
        };
    }

    async function gerarPdfsPorEmpresa(numeroProcesso, tarefasSelecionadas, opts) {
        opts = opts || {};
        const num = numeroProcesso || extrairNumeroProcesso();
        if (!num) throw new Error('Número do processo não informado.');
        if (!tarefasSelecionadas || !tarefasSelecionadas.length) {
            throw new Error('Selecione ao menos uma pesquisa.');
        }

        const onStatus = typeof opts.onStatus === 'function' ? opts.onStatus : function () {};

        const gruposMap = new Map();
        for (const t of tarefasSelecionadas) {
            const doc = t.documentoExecutado || 'SEM_DOC';
            if (!gruposMap.has(doc)) {
                gruposMap.set(doc, { documento: doc, nomeEmpresa: t.nomeExecutado || doc, tarefas: [] });
            }
            gruposMap.get(doc).tarefas.push(t);
        }

        const grupos = Array.from(gruposMap.values());
        const nomesCurtos = _abreviarNomesEmpresas(grupos);

        function _ehArisp(t) {
            return String(t.tipoTarefa || t.nomeTarefa || '').toUpperCase().includes('ARISP');
        }
        function _ehRenajud(t) {
            return String(t.tipoTarefa || t.nomeTarefa || '').toUpperCase().includes('RENAJUD');
        }

        // Regra por parte executada (Art. 131 CNC):
        // Positivas divididas em: (a) ARISP 1 por 1, (b) Renajud agrupado, (c) Demais agrupado.
        // Negativas: 1 PDF agrupado por parte executada.
        const lotes = [];
        for (const g of grupos) {
            const nomeCurto = nomesCurtos.get(g.documento) || g.nomeEmpresa;
            const ordenadas = _ordenarPositivasDepoisNegativas(g.tarefas);
            const pos = ordenadas.filter(t => t.resultadoPositivo);
            const neg = ordenadas.filter(t => !t.resultadoPositivo);

            const posArisp = pos.filter(_ehArisp);
            const posRenajud = pos.filter(t => !_ehArisp(t) && _ehRenajud(t));
            const posDemais = pos.filter(t => !_ehArisp(t) && !_ehRenajud(t));

            for (let idx = 0; idx < posArisp.length; idx++) {
                const tArisp = posArisp[idx];
                const sufixo = posArisp.length > 1 ? (' ' + (idx + 1)) : '';
                const nomeArisp = _sanitizarNomeArquivo(nomeCurto + ' (ARISP OK' + sufixo + ')') + '.pdf';
                lotes.push({
                    documento: g.documento,
                    nomeEmpresa: g.nomeEmpresa,
                    nomeCurto,
                    tipoLote: 'ARISP_OK',
                    tarefas: [tArisp],
                    nomeArquivo: nomeArisp,
                });
            }
            if (posRenajud.length) {
                lotes.push({
                    documento: g.documento,
                    nomeEmpresa: g.nomeEmpresa,
                    nomeCurto,
                    tipoLote: 'RENAJUD_OK',
                    tarefas: posRenajud,
                    nomeArquivo: _montarNomeArquivoEmpresa(nomeCurto, posRenajud),
                });
            }
            if (posDemais.length) {
                lotes.push({
                    documento: g.documento,
                    nomeEmpresa: g.nomeEmpresa,
                    nomeCurto,
                    tipoLote: 'DEMAIS_OK',
                    tarefas: posDemais,
                    nomeArquivo: _montarNomeArquivoEmpresa(nomeCurto, posDemais),
                });
            }
            if (neg.length) {
                lotes.push({
                    documento: g.documento,
                    nomeEmpresa: g.nomeEmpresa,
                    nomeCurto,
                    tipoLote: 'NEGATIVAS',
                    tarefas: neg,
                    nomeArquivo: _montarNomeArquivoEmpresa(nomeCurto, neg),
                });
            }
        }

        const gerados = [];
        for (let i = 0; i < lotes.length; i++) {
            const lote = lotes[i];
            const prefixo = '[' + (i + 1) + '/' + lotes.length + ' ' + lote.tipoLote + '] ';
            const res = await gerarPdfUnico(num, lote.tarefas, {
                nomeArquivo: lote.nomeArquivo,
                nomeCurtoEmpresa: lote.nomeCurto,
                enriquecerNomeArisp: lote.tipoLote === 'ARISP_OK',
                incluirCertidao: opts.incluirCertidao,
                download: opts.download,
                maxBytes: opts.maxBytes,
                onStatus: msg => onStatus(prefixo + msg),
            });
            const partesLote = (res.partes && res.partes.length) ? res.partes : [{
                nomeArquivo: res.nomeArquivo,
                totalPaginas: res.totalPaginas,
                bytesFinal: res.bytesFinal,
                parte: 1,
                totalPartes: 1,
            }];
            for (const pt of partesLote) {
                gerados.push({
                    documento: lote.documento,
                    nomeEmpresa: lote.nomeEmpresa,
                    tipoLote: lote.tipoLote,
                    nomeArquivo: pt.nomeArquivo,
                    totalPaginas: pt.totalPaginas,
                    bytesFinal: pt.bytesFinal,
                    parte: pt.parte,
                    totalPartes: pt.totalPartes,
                    avisos: res.avisos,
                });
            }
            if (opts.download !== false && i < lotes.length - 1) {
                await new Promise(r => setTimeout(r, 400));
            }
        }

        return {
            numeroProcesso: num,
            modo: '2_por_empresa_pos_neg',
            totalArquivos: gerados.length,
            arquivos: gerados,
        };
    }

    // ── Consulta por lista explícita de documentos ───────────────────────
    async function consultarPorDocumentos(numeroProcesso, docs, opts) {
        const docsLimpos = Array.from(new Set((docs || []).map(d => String(d || '').replace(/\D/g, '')).filter(Boolean)));
        const reap = await buscarTodasReaproveitaveis(docsLimpos, opts);
        const analise = selecionarElegiveisArt131(reap.resultado);
        const maisRecentes = resumirPorExecutadoETipo(analise.todasAvaliadas);

        return {
            numeroProcesso,
            docsConsultados: docsLimpos,
            reaproveitaveis: {
                totalRegistros: reap.totalRegistros,
                carregados: reap.resultado.length,
                qtdPaginas: reap.qtdPaginas,
                paginasLidas: reap.paginasLidas,
                msTotal: reap.msTotal,
                todos: analise.todasAvaliadas,
                maisRecentesPorExecutadoETipo: maisRecentes,
                elegiveisArt131: analise.elegiveis,
                expiradasArt131: analise.expiradasOuExcluidas,
                porEmpresaArt131: analise.porEmpresa,
            },
            temposMs: { reaproveitaveis: reap.msTotal },
        };
    }

    // ── Modal de Resultados do Poupa ─────────────────────────────────────
    function _fmtData(iso) {
        if (!iso) return '-';
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
        return d.toLocaleDateString('pt-BR');
    }

    function renderizarModalPoupa(relatorio) {
        let modal = document.getElementById('pjetools-argos-poupa-modal');
        if (modal) modal.remove();

        modal = document.createElement('div');
        modal.id = 'pjetools-argos-poupa-modal';
        modal.style.cssText = [
            'position:fixed', 'inset:24px', 'z-index:999999',
            'background:#111827', 'color:#f3f4f6', 'border:1px solid #374151',
            'border-radius:10px', 'box-shadow:0 20px 60px rgba(0,0,0,.6)',
            'display:flex', 'flex-direction:column', 'font-family:system-ui,sans-serif',
            'font-size:13px', 'overflow:hidden',
        ].join(';');

        const docsUnicos = Array.from(new Set(relatorio.reaproveitaveis.todos.map(x => x.documentoExecutado)));
        const convUnicos = Array.from(new Set(relatorio.reaproveitaveis.todos.map(x => x.rotuloTarefa))).sort();
        const selecionadasIds = new Set((relatorio.reaproveitaveis.elegiveisArt131 || []).map(x => x.idTarefa));

        modal.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:#1f2937;border-bottom:1px solid #374151;gap:12px;">
                <div>
                    <strong style="font-size:14px;">Argos Poupa Convênios (Art. 131 CNC)</strong>
                    <span style="margin-left:10px;color:#9ca3af;">Processo ${_escapeHtml(relatorio.numeroProcesso)}</span>
                    <span style="margin-left:10px;color:#34d399;">Elegíveis: ${(relatorio.reaproveitaveis.elegiveisArt131 || []).length}</span>
                    <span style="margin-left:10px;color:#60a5fa;">Total API: ${relatorio.reaproveitaveis.carregados}/${relatorio.reaproveitaveis.totalRegistros}</span>
                    <span style="margin-left:10px;color:#fbbf24;">${(relatorio.temposMs.reaproveitaveis / 1000).toFixed(1)}s</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                    <button id="ap-btn-pdf-sep" style="padding:6px 12px;background:#059669;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:600;">PDFs por Empresa (Pos/Neg) (0)</button>
                    <button id="ap-btn-pdf-uni" style="padding:6px 10px;background:#0d9488;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:600;">1 PDF/Empresa (0)</button>
                    <button id="ap-btn-close" style="padding:6px 10px;background:#dc2626;color:#fff;border:none;border-radius:5px;cursor:pointer;">Fechar</button>
                </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:10px;padding:10px 16px;background:#182030;border-bottom:1px solid #374151;align-items:center;">
                <label>Modo:
                    <select id="ap-f-modo" style="background:#111827;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;padding:3px 6px;">
                        <option value="art131">Elegíveis Art. 131 CNC (${(relatorio.reaproveitaveis.elegiveisArt131 || []).length})</option>
                        <option value="recentes">Mais recente por Executado × Tipo (${relatorio.reaproveitaveis.maisRecentesPorExecutadoETipo.length})</option>
                        <option value="todos">Todas (${relatorio.reaproveitaveis.carregados})</option>
                    </select>
                </label>
                <label>Parte:
                    <select id="ap-f-doc" style="background:#111827;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;padding:3px 6px;">
                        <option value="">Todas (${docsUnicos.length})</option>
                        ${docsUnicos.map(d => `<option value="${_escapeHtml(d)}">${_escapeHtml(d)}</option>`).join('')}
                    </select>
                </label>
                <label>Tarefa:
                    <select id="ap-f-tarefa" style="background:#111827;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;padding:3px 6px;">
                        <option value="">Todas</option>
                        ${convUnicos.map(c => `<option value="${_escapeHtml(c)}">${_escapeHtml(c)}</option>`).join('')}
                    </select>
                </label>
                <label>Resultado:
                    <select id="ap-f-res" style="background:#111827;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;padding:3px 6px;">
                        <option value="">Todos</option>
                        <option value="pos">Positivo</option>
                        <option value="neg">Negativo</option>
                    </select>
                </label>
                <button id="ap-btn-sel-vis" style="padding:4px 8px;background:#374151;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;cursor:pointer;">Marcar visíveis</button>
                <button id="ap-btn-limpar-sel" style="padding:4px 8px;background:#374151;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;cursor:pointer;">Limpar</button>
                <span id="ap-f-count" style="margin-left:auto;color:#9ca3af;"></span>
            </div>
            <div id="ap-status-bar" style="display:none;padding:8px 16px;background:#0f172a;color:#93c5fd;border-bottom:1px solid #374151;font-size:12px;"></div>
            <div style="flex:1;overflow:auto;">
                <table style="width:100%;border-collapse:collapse;font-size:12px;">
                    <thead style="position:sticky;top:0;background:#1f2937;">
                        <tr>
                            <th style="text-align:center;padding:7px 8px;border-bottom:1px solid #374151;width:32px;">✓</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">ID</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Parte / Doc</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Tarefa</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Data</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Art. 131</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Resultado</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Anexo</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Origem / Vara</th>
                        </tr>
                    </thead>
                    <tbody id="ap-tbody"></tbody>
                </table>
            </div>
        `;

        document.body.appendChild(modal);

        const selModo = modal.querySelector('#ap-f-modo');
        const selDoc = modal.querySelector('#ap-f-doc');
        const selTarefa = modal.querySelector('#ap-f-tarefa');
        const selRes = modal.querySelector('#ap-f-res');
        const tbody = modal.querySelector('#ap-tbody');
        const countEl = modal.querySelector('#ap-f-count');
        const btnPdfSep = modal.querySelector('#ap-btn-pdf-sep');
        const btnPdfUni = modal.querySelector('#ap-btn-pdf-uni');
        const statusBar = modal.querySelector('#ap-status-bar');

        let filtradosAtuais = [];

        function atualizarContadores() {
            btnPdfSep.textContent = 'PDFs por Empresa (Pos/Neg) (' + selecionadasIds.size + ')';
            btnPdfUni.textContent = '1 PDF/Empresa (' + selecionadasIds.size + ')';
        }

        function atualizarTabela() {
            const base = selModo.value === 'art131'
                ? (relatorio.reaproveitaveis.elegiveisArt131 || [])
                : selModo.value === 'recentes'
                    ? relatorio.reaproveitaveis.maisRecentesPorExecutadoETipo
                    : relatorio.reaproveitaveis.todos;

            filtradosAtuais = base.filter(it => {
                if (selDoc.value && it.documentoExecutado !== selDoc.value) return false;
                if (selTarefa.value && it.rotuloTarefa !== selTarefa.value) return false;
                if (selRes.value === 'pos' && !it.resultadoPositivo) return false;
                if (selRes.value === 'neg' && it.resultadoPositivo) return false;
                return true;
            });

            countEl.textContent = 'Exibindo ' + filtradosAtuais.length + ' de ' + base.length;
            tbody.innerHTML = filtradosAtuais.map(it => {
                const av = it.art131 || avaliarElegibilidadeArt131(it);
                return `
                    <tr style="border-bottom:1px solid #1f2937;">
                        <td style="text-align:center;padding:6px 8px;">
                            <input type="checkbox" class="ap-row-chk" data-id="${_escapeHtml(it.idTarefa)}" ${selecionadasIds.has(it.idTarefa) ? 'checked' : ''} />
                        </td>
                        <td style="padding:6px 8px;color:#9ca3af;">${_escapeHtml(it.idTarefa)}</td>
                        <td style="padding:6px 8px;">
                            <div>${_escapeHtml(it.nomeExecutado)}</div>
                            <div style="color:#9ca3af;font-size:11px;">${_escapeHtml(it.documentoExecutado)}</div>
                        </td>
                        <td style="padding:6px 8px;color:#93c5fd;">${_escapeHtml(it.rotuloTarefa)}</td>
                        <td style="padding:6px 8px;white-space:nowrap;">${_escapeHtml(_fmtData(it.dataFinalizacao))}</td>
                        <td style="padding:6px 8px;color:${av.elegivel ? '#34d399' : '#f59e0b'};font-size:11px;" title="${_escapeHtml(av.motivo)}">
                            ${av.elegivel ? '✓ ' : '✗ '}${_escapeHtml(av.regra)}
                        </td>
                        <td style="padding:6px 8px;color:${it.resultadoPositivo ? '#34d399' : '#f87171'};font-weight:600;">
                            ${it.resultadoPositivo ? 'Positivo' : 'Negativo'}
                        </td>
                        <td style="padding:6px 8px;">${it.possuiAnexo ? 'Sim' : 'Não'}</td>
                        <td style="padding:6px 8px;">
                            <div>${_escapeHtml(it.numeroProcessoOrigem)}</div>
                            <div style="color:#9ca3af;font-size:11px;">${_escapeHtml(it.nomeOrgaoJulgador)}</div>
                        </td>
                    </tr>
                `;
            }).join('');

            tbody.querySelectorAll('.ap-row-chk').forEach(chk => {
                chk.addEventListener('change', () => {
                    const id = Number(chk.getAttribute('data-id'));
                    if (chk.checked) selecionadasIds.add(id);
                    else selecionadasIds.delete(id);
                    atualizarContadores();
                });
            });
            atualizarContadores();
        }

        [selModo, selDoc, selTarefa, selRes].forEach(el => el.addEventListener('change', atualizarTabela));

        modal.querySelector('#ap-btn-sel-vis').addEventListener('click', () => {
            for (const it of filtradosAtuais) selecionadasIds.add(it.idTarefa);
            atualizarTabela();
        });
        modal.querySelector('#ap-btn-limpar-sel').addEventListener('click', () => {
            selecionadasIds.clear();
            atualizarTabela();
        });

        async function executarGeracao(separarPosNeg) {
            const selecionadas = relatorio.reaproveitaveis.todos.filter(t => selecionadasIds.has(t.idTarefa));
            if (!selecionadas.length) {
                showToast('Poupa: marque ao menos uma pesquisa antes de gerar os PDFs', '#ff9800', 4000);
                return;
            }
            btnPdfSep.disabled = true;
            btnPdfUni.disabled = true;
            statusBar.style.display = 'block';
            statusBar.style.color = '#93c5fd';
            try {
                const res = await gerarPdfsPorEmpresa(relatorio.numeroProcesso, selecionadas, {
                    separarPositivasNegativas: separarPosNeg,
                    onStatus: msg => { statusBar.textContent = msg; },
                });
                const nomes = res.arquivos.map(a => a.nomeArquivo + ' (' + a.totalPaginas + 'p)').join(' | ');
                statusBar.style.color = '#34d399';
                statusBar.textContent = 'Pronto! ' + res.totalArquivos + ' PDF(s): ' + nomes;
                showToast('Poupa: ' + res.totalArquivos + ' PDF(s) gerado(s)', '#28a745', 4000);
            } catch (err) {
                console.error('[ArgosPoupa] erro ao gerar PDFs:', err);
                statusBar.style.color = '#f87171';
                statusBar.textContent = 'Erro: ' + (err && err.message ? err.message : err);
            } finally {
                btnPdfSep.disabled = false;
                btnPdfUni.disabled = false;
            }
        }

        btnPdfSep.addEventListener('click', () => executarGeracao(true));
        btnPdfUni.addEventListener('click', () => executarGeracao(false));
        modal.querySelector('#ap-btn-close').addEventListener('click', () => modal.remove());

        atualizarTabela();
    }

    // ── Pequeno overlay de progresso (sem dialog de seleção de pesquisas) ─
    function _criarOverlayProgressoPoupa(titulo) {
        const prev = document.getElementById('pjetools-argos-poupa-status');
        if (prev) prev.remove();

        const box = document.createElement('div');
        box.id = 'pjetools-argos-poupa-status';
        box.style.cssText = [
            'position:fixed', 'bottom:24px', 'right:24px', 'z-index:2147483647',
            'width:360px', 'max-width:92vw', 'background:#0f172a', 'color:#e2e8f0',
            'border:1px solid #334155', 'border-left:4px solid #7c3aed',
            'border-radius:10px', 'box-shadow:0 12px 32px rgba(0,0,0,.45)',
            'padding:12px 14px', 'font-family:system-ui,-apple-system,sans-serif',
            'font-size:12px', 'line-height:1.4',
        ].join(';');

        box.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;">
                <strong style="color:#c4b5fd;font-size:13px;">⚖️ ${_escapeHtml(titulo || 'Argos Poupa (Art. 131 CNC)')}</strong>
                <button id="ap-prog-close" type="button" style="display:none;padding:2px 8px;background:#334155;color:#e2e8f0;border:none;border-radius:4px;cursor:pointer;font-size:11px;">Fechar</button>
            </div>
            <div id="ap-prog-msg" style="color:#f8fafc;">⏳ Iniciando buscas...</div>
            <div id="ap-prog-detalhe" style="margin-top:6px;color:#94a3b8;font-size:11px;"></div>
        `;
        document.body.appendChild(box);

        const msgEl = box.querySelector('#ap-prog-msg');
        const detEl = box.querySelector('#ap-prog-detalhe');
        const closeBtn = box.querySelector('#ap-prog-close');
        closeBtn.addEventListener('click', () => box.remove());

        return {
            atualizar(texto, detalhe) {
                if (msgEl) msgEl.textContent = texto;
                if (detEl && detalhe !== undefined) detEl.textContent = detalhe;
            },
            concluir(texto, corBorda, linhasDetalhe) {
                box.style.borderLeftColor = corBorda || '#10b981';
                if (msgEl) msgEl.textContent = texto;
                if (detEl) {
                    if (Array.isArray(linhasDetalhe) && linhasDetalhe.length) {
                        detEl.innerHTML = linhasDetalhe.map(l => '<div>• ' + _escapeHtml(l) + '</div>').join('');
                    } else if (typeof linhasDetalhe === 'string') {
                        detEl.textContent = linhasDetalhe;
                    }
                }
                if (closeBtn) closeBtn.style.display = 'inline-block';
            },
            fechar() { box.remove(); },
        };
    }

    // ── Entrypoint do botão "Poupa" no painel ────────────────────────────
    async function executarPoupa() {
        let prog = null;
        try {
            const numero = extrairNumeroProcesso();
            if (!numero) {
                showToast('Poupa: número do processo não encontrado nesta página', '#dc3545', 4000);
                return;
            }
            const partes = await _obterPartesProcesso(numero);
            const escolha = await abrirDialogoPartes(partes, 'Argos Poupa — Selecionar Partes');
            if (!escolha) return;

            const docs = escolha.selecionadas.map(p => p.documento).filter(Boolean);
            if (!docs.length) {
                showToast('Poupa: nenhuma parte selecionada possui CPF/CNPJ', '#dc3545', 4000);
                return;
            }

            prog = _criarOverlayProgressoPoupa('Argos Poupa (Art. 131 CNC)');
            prog.atualizar(
                '⏳ Buscando pesquisas reaproveitáveis na API Argos...',
                docs.length + ' parte(s) executada(s) selecionada(s)'
            );

            const relatorio = await consultarPorDocumentos(numero, docs);
            const totalApi = relatorio.reaproveitaveis.carregados || 0;
            const elegiveis = relatorio.reaproveitaveis.elegiveisArt131 || [];

            if (!elegiveis.length) {
                const detalhe = totalApi
                    ? (totalApi + ' pesquisa(s) localizada(s), mas nenhuma dentro dos prazos do Art. 131 CNC.')
                    : 'Nenhuma pesquisa reaproveitável encontrada para as partes selecionadas.';
                prog.concluir('ℹ️ Nenhuma pesquisa elegível (Art. 131 CNC).', '#f59e0b', detalhe);
                showToast('Poupa: nenhuma pesquisa elegível (Art. 131 CNC)', '#ff9800', 5000);
                return;
            }

            prog.atualizar(
                '⏳ ' + elegiveis.length + ' pesquisa(s) elegível(is) — gerando PDFs (Pos/Neg por parte)...',
                'Aguarde: baixando certidões e anexos...'
            );

            const res = await gerarPdfsPorEmpresa(numero, elegiveis, {
                onStatus: (msg) => prog.atualizar('⏳ ' + msg, elegiveis.length + ' elegível(is) Art. 131 CNC'),
            });

            const nomes = (res.arquivos || []).map(a => {
                const mb = a.bytesFinal ? (' • ' + (a.bytesFinal / (1024 * 1024)).toFixed(2) + ' MB') : '';
                return a.nomeArquivo + ' (' + a.totalPaginas + ' pág.' + mb + ')';
            });
            prog.concluir(
                '✅ ' + res.totalArquivos + ' PDF(s) baixado(s) (Positivo/Negativo por parte)',
                '#10b981',
                nomes
            );
            showToast('Poupa: ' + res.totalArquivos + ' PDF(s) gerado(s) com sucesso', '#28a745', 5000);
        } catch (err) {
            console.error('[ArgosPoupa] erro:', err);
            const msg = err && err.message ? err.message : String(err);
            if (prog) {
                prog.concluir('❌ Erro no Argos Poupa', '#ef4444', msg);
            }
            showToast('Poupa: erro — ' + msg, '#dc3545', 5000);
        }
    }

    window.executarArgosPoupa = executarPoupa;
    window.PjeArgosPoupa = {
        executar: executarPoupa,
        abrirDialogoPartes,
        consultarPorDocumentos,
        avaliarElegibilidadeArt131,
        selecionarElegiveisArt131,
        calcularConveniosExcluidos,
        gerarPdfUnico,
        gerarPdfsPorEmpresa,
    };
})();
