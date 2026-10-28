'use strict';

// Painel: registra funções mesmo quando o script carrega fora da rota /detalhe
(function () {

    window.CSS_PAINEL = `
    .pjetools-destaque        { outline:3px solid #007bff!important; background:#e7f3ff!important; transition:.3s; }
    .pjetools-destaque-edital { outline:3px solid #28a745!important; background:#e8f5e8!important; transition:.3s; }
    #pjetools-painel button:hover { opacity:.85; }
    #pjetools-painel-titulo:hover { color: #007bff!important; }
    #pjetools-painel-titulo:hover #pjetools-painel-seta { color: #007bff!important; }
    `;

    window.criarPainel = function (botoes) {
        document.getElementById('pjetools-painel')?.remove();
        addStyles(CSS_PAINEL, 'pjetools-styles');

        let recolhido = true;
        let moved = false;

        const painel = document.createElement('div');
        painel.id = 'pjetools-painel';
        painel.style.cssText = `position:fixed;bottom:170px;right:20px;z-index:99999;` +
            `background:#fff;border:2px solid #333;border-radius:8px;` +
            `box-shadow:0 4px 16px rgba(0,0,0,.2);padding:6px 10px;font-family:sans-serif;` +
            `min-width:140px;user-select:none;transition:padding .15s ease, min-width .15s ease;`;

        const titulo = document.createElement('div');
        titulo.id = 'pjetools-painel-titulo';
        titulo.title = 'Clique para expandir ferramentas';
        titulo.style.cssText = `font-weight:bold;color:#333;font-size:12px;` +
            `cursor:pointer;display:flex;align-items:center;justify-content:space-between;` +
            `gap:8px;padding-bottom:0;`;

        const textoTitulo = document.createElement('span');
        textoTitulo.textContent = '🛠️ PJeTools v2.6.28';

        const setaToggle = document.createElement('span');
        setaToggle.id = 'pjetools-painel-seta';
        setaToggle.textContent = '▼';
        setaToggle.style.cssText = 'font-size:10px;color:#666;transition:transform .15s;';

        titulo.appendChild(textoTitulo);
        titulo.appendChild(setaToggle);
        painel.appendChild(titulo);

        const conteudo = document.createElement('div');
        conteudo.id = 'pjetools-painel-conteudo';
        conteudo.style.cssText = 'display:none;margin-top:8px;';

        const grid = document.createElement('div');
        grid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:6px;';

        botoes.forEach(btn => {
            const b = document.createElement('button');
            b.id = btn.id;
            b.textContent = btn.texto;
            b.title = btn.titulo || '';
            b.style.cssText = `padding:7px 6px;background:${btn.bg};color:#fff;border:none;` +
                `border-radius:4px;cursor:pointer;font-weight:bold;font-size:11px;` +
                `transition:opacity .15s;`;
            b.onclick = btn.fn;
            if (btn.full) b.style.gridColumn = '1 / -1';
            grid.appendChild(b);
        });

        conteudo.appendChild(grid);

        const limparBtn = document.createElement('button');
        limparBtn.textContent = '🔄 Limpar Cache';
        limparBtn.style.cssText = `margin-top:8px;width:100%;padding:5px;background:#6c757d;` +
            `color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:10px;`;
        limparBtn.onclick = () => {
            invalidarCacheTimeline();
            showToast('Cache da timeline limpo', '#6c757d', 2000);
        };
        conteudo.appendChild(limparBtn);

        painel.appendChild(conteudo);

        function atualizarEstado() {
            if (recolhido) {
                conteudo.style.display = 'none';
                painel.style.minWidth = '140px';
                painel.style.padding = '6px 10px';
                painel.style.boxShadow = '0 4px 16px rgba(0,0,0,.2)';
                titulo.style.borderBottom = 'none';
                titulo.style.paddingBottom = '0';
                setaToggle.textContent = '▼';
                titulo.title = 'Clique para expandir ferramentas';
            } else {
                conteudo.style.display = 'block';
                painel.style.minWidth = '190px';
                painel.style.padding = '10px 12px';
                painel.style.boxShadow = '0 8px 32px rgba(0,0,0,.25)';
                titulo.style.borderBottom = '1px solid #ddd';
                titulo.style.paddingBottom = '6px';
                setaToggle.textContent = '▲';
                titulo.title = 'Clique para recolher ferramentas';
            }
            console.log('[Painel] Estado atualizado. Recolhido:', recolhido);
        }

        atualizarEstado();

        titulo.onclick = () => {
            if (moved) return;
            recolhido = !recolhido;
            atualizarEstado();
        };

        _tornaPainelArrastavel(painel, m => { moved = m; });
        document.body.appendChild(painel);
        PJeState.registry.add(() => painel.remove());
    };

    window._tornaPainelArrastavel = function (el, onDragChange) {
        let ox = 0, oy = 0, startX = 0, startY = 0, drag = false, moved = false;
        const onDown = e => {
            if (e.target.tagName === 'BUTTON') return;
            drag = true;
            moved = false;
            startX = e.clientX;
            startY = e.clientY;
            ox = e.clientX - el.offsetLeft;
            oy = e.clientY - el.offsetTop;
            if (onDragChange) onDragChange(false);
        };
        const onMove = e => {
            if (!drag) return;
            if (!moved && (Math.abs(e.clientX - startX) > 4 || Math.abs(e.clientY - startY) > 4)) {
                moved = true;
                if (onDragChange) onDragChange(true);
            }
            if (!moved) return;
            el.style.left = (e.clientX - ox) + 'px';
            el.style.top = (e.clientY - oy) + 'px';
            el.style.right = 'auto';
            el.style.bottom = 'auto';
        };
        const onUp = () => {
            drag = false;
            setTimeout(() => {
                moved = false;
                if (onDragChange) onDragChange(false);
            }, 50);
        };
        el.addEventListener('mousedown', onDown);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        PJeState.registry.add(() => {
            el.removeEventListener('mousedown', onDown);
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        });
    };

    window.inicializarPainel = function () {
        if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) {
            console.log('[Painel] inicializarPainel: URL não é de detalhe, abortando. URL:', window.location.href);
            return;
        }
        console.log('[Painel] Criando painel...');
        criarPainel([
            { id: 'btnCheck', texto: '🔎 Check', bg: '#007bff', fn: function() {
                    if (typeof window.executarCheck === 'function') {
                        window.executarCheck();
                    } else {
                        showToast('Módulo Check não carregado', '#dc3545', 3000);
                    }
                }, titulo: 'Relatório de Medidas' },
            { id: 'btnEdital', texto: '📣 Edital', bg: '#28a745', fn: executarEdital, titulo: 'Relatório de Editais' },
            { id: 'btnSimba', texto: '⚖️ Simba', bg: '#ff9800', fn: function() {
                    if (typeof window.executarSimba === 'function') {
                        window.executarSimba();
                    } else {
                        showToast('Módulo Simba não carregado', '#dc3545', 3000);
                    }
                }, titulo: 'Salvar dados e pesquisar Iniciada execução' },
            { id: 'btnInfojud', texto: '🏛️ Infojud', bg: '#c62828', fn: function() {
                    if (typeof window.executarInfojudDetalhe === 'function') {
                        window.executarInfojudDetalhe();
                    } else {
                        showToast('Módulo Infojud não carregado', '#dc3545', 3000);
                    }
                }, titulo: 'Consultar Infojud das partes do processo' },
            { id: 'btnSisbajud', texto: '💸 Sisbajud', bg: '#1e88e5', fn: function (e) {
                    const btn = e.target.closest('button');
                    if (btn.dataset.expanded === "true") return;
                    btn.dataset.expanded = "true";
                    btn.innerHTML = '';
                    btn.style.display = 'flex';
                    btn.style.gap = '3px';
                    btn.style.padding = '2px';
                    
                    const btnStyle = 'flex:1;background:#fff;color:#1e88e5;border:none;border-radius:3px;font-size:10px;font-weight:bold;cursor:pointer;padding:4px 2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
                    
                    const b1 = document.createElement('button');
                    b1.textContent = 'Extrair';
                    b1.title = 'Extrair resultado Sisbajud do PDF ativo';
                    b1.style.cssText = btnStyle;
                    b1.onclick = (ev) => {
                        ev.stopPropagation();
                        if (typeof window.executarSisbajudPJe === 'function') {
                            window.executarSisbajudPJe();
                        } else {
                            showToast('Módulo Sisbajud não carregado', '#dc3545', 3000);
                        }
                    };

                    const b2 = document.createElement('button');
                    b2.textContent = 'Minuta';
                    b2.title = 'Extrair e completar dados do processo para Teimosinha e Endereço';
                    b2.style.cssText = btnStyle;
                    b2.onclick = (ev) => {
                        ev.stopPropagation();
                        if (window.PjeSisbajudAuto && typeof window.PjeSisbajudAuto.iniciarMinuta === 'function') {
                            window.PjeSisbajudAuto.iniciarMinuta();
                        } else {
                            showToast('Módulo Sisbajud não carregado', '#dc3545', 3000);
                        }
                    };
                    
                    btn.appendChild(b1);
                    btn.appendChild(b2);
                }, titulo: 'Sisbajud', full: true },
            { id: 'btnDebito', texto: '💰 Débito', bg: '#17a2b8', fn: function () {
                    if (window.PjeRegistrarDebito && typeof window.PjeRegistrarDebito.executar === 'function') {
                        window.PjeRegistrarDebito.executar();
                    } else {
                        showToast('Módulo Débito não carregado', '#dc3545', 3000);
                    }
                }, titulo: 'Registrar débito' },
            { id: 'btnSaldoAlvara', texto: '🏦 Saldo', bg: '#1a7f37', fn: function (e) {
                    const btn = e.target.closest('button');
                    const api = window.Alv && window.Alv.siscondj;

                    if (!api || typeof api.copiarSaldoProcesso !== 'function') {
                        showToast('Módulo Alvará não carregado', '#dc3545', 3000);
                        return;
                    }
                    if (typeof api.temGMXHR === 'function' && !api.temGMXHR()) {
                        showToast('Falta @grant GM_xmlhttpRequest no pjetools.user.js', '#dc3545', 4000);
                        return;
                    }

                    // Número do processo: delega ao módulo, que usa as mesmas
                    // fontes do Argos (título, .texto-numero-processo, URL).
                    // O /detalhe do PJe não traz o número na URL.
                    const numeroProcesso = typeof api.numeroProcessoDaPagina === 'function'
                        ? api.numeroProcessoDaPagina()
                        : null;

                    if (!numeroProcesso) {
                        showToast('Número do processo não encontrado na página', '#dc3545', 3000);
                        return;
                    }

                    const textoOriginal = btn.textContent;
                    btn.textContent = '⏳ Consultando';
                    btn.disabled = true;

                    api.copiarSaldoProcesso(numeroProcesso)
                        .then(res => {
                            if (res && res.copiado) {
                                btn.textContent = '✅ Saldo copiado';
                                // Saldo positivo: aciona o SISCON pelo menu do
                                // Anexar (hover no ícone, clique no botão).
                                if (window.maisPje && typeof window.maisPje.hover === 'function') {
                                    window.maisPje.hover('anexar').clicar('siscon')
                                        .then(r => {
                                            if (!r || !r.ok) {
                                                showToast('Saldo copiado, mas o SISCON não abriu: '
                                                    + (r && r.erro ? r.erro : 'botão não encontrado'),
                                                    '#ff9800', 5000);
                                            }
                                        })
                                        .catch(err => console.warn('[PjeTools][Saldo] SISCON:', err));
                                } else {
                                    showToast('Motor maisPje não carregado — SISCON não acionado',
                                        '#ff9800', 4000);
                                }
                            } else if (res && res.semSaldo) {
                                btn.textContent = 'Sem saldo';
                            } else {
                                btn.textContent = 'Falha ao copiar';
                            }
                        })
                        .catch(err => {
                            console.error('[PjeTools][Saldo] erro:', err);
                            btn.textContent = 'Erro';
                            showToast('Saldo: ' + (err && err.message ? err.message : err), '#dc3545', 5000);
                        })
                        .finally(() => {
                            setTimeout(() => {
                                btn.textContent = textoOriginal;
                                btn.disabled = false;
                            }, 2500);
                        });
                }, titulo: 'Consultar saldo da conta judicial no Alvará e copiar o resumo' },
            { id: 'btnArgos', texto: '⚖️ Argos', bg: '#6f42c1', fn: function () {
                    if (typeof window.executarArgos === 'function') {
                        window.executarArgos();
                    } else {
                        showToast('Módulo Argos não carregado', '#dc3545', 3000);
                    }
                }, titulo: 'Abrir Nova Pesquisa no ARGOS' },
            { id: 'btnAjustarPDF', texto: '📎 PDF', bg: '#e67e22', fn: function () {
                    if (typeof window.executarAjustarPDF === 'function') {
                        window.executarAjustarPDF();
                    } else {
                        showToast('Módulo PDF não carregado', '#dc3545', 3000);
                    }
                }, titulo: 'Comprimir/Dividir PDF para envio no PJe' },
            { id: 'btnAud', texto: '📅 Aud', bg: '#1565c0', fn: function (e) {
                    const btn = e.target.closest('button');
                    if (btn.dataset.expanded === "true") return;
                    btn.dataset.expanded = "true";
                    btn.innerHTML = '';
                    btn.style.display = 'flex';
                    btn.style.gap = '4px';
                    btn.style.padding = '4px';
                    
                    const b1 = document.createElement('button');
                    b1.textContent = 'Nova';
                    b1.style.cssText = 'flex:1;background:#fff;color:#1565c0;border:none;border-radius:2px;font-size:10px;font-weight:bold;cursor:pointer;';
                    b1.onclick = (ev) => {
                        ev.stopPropagation();
                        if (window.PjeMarcarAud && typeof window.PjeMarcarAud.executarNova === 'function') {
                            window.PjeMarcarAud.executarNova();
                        } else {
                            showToast('Módulo Aud não carregado', '#dc3545', 3000);
                        }
                    };
                    
                    const b2 = document.createElement('button');
                    b2.textContent = 'Ata';
                    b2.style.cssText = 'flex:1;background:#fff;color:#1565c0;border:none;border-radius:2px;font-size:10px;font-weight:bold;cursor:pointer;';
                    b2.onclick = (ev) => {
                        ev.stopPropagation();
                        if (window.PjeMarcarAud && typeof window.PjeMarcarAud.executarAta === 'function') {
                            window.PjeMarcarAud.executarAta();
                        } else {
                            showToast('Módulo Aud não carregado', '#dc3545', 3000);
                        }
                    };
                    
                    btn.appendChild(b1);
                    btn.appendChild(b2);
                }, titulo: 'Agendar Audiência', full: true }
        ]);
    };
})();
