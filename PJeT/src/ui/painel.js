'use strict';

// ── PJeT — ui/painel.js ───────────────────────────────────────────
// Painel flutuante principal do PJeT.
// Gerencia botões de acesso rápido, arrasto, limpeza de cache
// e integração com as preferências do usuário.
// ─────────────────────────────────────────────────────────────────

(function () {
    const log = window.PJeLogger || {
        painel:  (...a) => console.log('[PJeT::PAINEL]', ...a),
        dom:     (...a) => console.log('[PJeT::DOM]', ...a),
        warn:    (c, ...a) => console.warn(`[PJeT::${c}]`, ...a),
        error:   (c, m, e) => console.error(`[PJeT::${c} ERRO] ${m}:`, e),
        success: (c, ...a) => console.log(`[PJeT::${c}] ✅`, ...a),
    };

    window.CSS_PAINEL = `
    .pjetools-destaque        { outline:3px solid #007bff!important; background:#e7f3ff!important; transition:.3s; }
    .pjetools-destaque-edital { outline:3px solid #28a745!important; background:#e8f5e8!important; transition:.3s; }
    #pjetools-painel button:hover { opacity:.88; transform:translateY(-1px); }
    #pjetools-painel button:active { transform:translateY(0); }
    `;

    window.criarPainel = function (botoes) {
        try {
            document.getElementById('pjetools-painel')?.remove();
            addStyles(CSS_PAINEL, 'pjetools-styles');

            const painel = document.createElement('div');
            painel.id = 'pjetools-painel';
            painel.style.cssText = `position:fixed;bottom:170px;right:20px;z-index:99999;` +
                `background:#fff;border:2px solid #333;border-radius:8px;` +
                `box-shadow:0 8px 32px rgba(0,0,0,.25);padding:10px 12px;font-family:sans-serif;` +
                `min-width:190px;user-select:none;transition:box-shadow .2s;`;

            const titulo = document.createElement('div');
            titulo.textContent = 'PJeT Pro v1.0';
            titulo.style.cssText = `font-weight:bold;margin-bottom:8px;color:#333;font-size:12px;` +
                `text-align:center;border-bottom:1px solid #ddd;padding-bottom:6px;cursor:move;`;
            titulo.title = 'Arraste para mover o painel';
            painel.appendChild(titulo);

            const grid = document.createElement('div');
            grid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:6px;';

            botoes.forEach(btn => {
                const b = document.createElement('button');
                b.id = btn.id;
                b.textContent = btn.texto;
                b.title = btn.titulo || '';
                b.style.cssText = `padding:7px 6px;background:${btn.bg};color:#fff;border:none;` +
                    `border-radius:4px;cursor:pointer;font-weight:bold;font-size:11px;` +
                    `transition:all .15s ease;`;

                // Encapsulamento seguro de execução de cada botão
                b.onclick = async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    log.painel(`Ação iniciada: [${btn.id}] ${btn.texto}`);
                    try {
                        await btn.fn(e);
                        log.success('PAINEL', `Ação concluída com sucesso: [${btn.id}]`);
                    } catch (err) {
                        log.error('PAINEL', `Falha ao executar ação do botão [${btn.id}]`, err, {
                            botaoId: btn.id,
                            botaoTexto: btn.texto
                        });
                    }
                };

                if (btn.full) b.style.gridColumn = '1 / -1';
                grid.appendChild(b);
            });

            painel.appendChild(grid);

            // Botão Limpar Cache
            const limparBtn = document.createElement('button');
            limparBtn.textContent = '🔄 Limpar Cache';
            limparBtn.style.cssText = `margin-top:8px;width:100%;padding:5px;background:#6c757d;` +
                `color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:10px;font-weight:bold;`;
            limparBtn.onclick = () => {
                try {
                    log.painel('Limpando cache da timeline...');
                    invalidarCacheTimeline();
                    showToast('Cache da timeline limpo', '#6c757d', 2000);
                    log.success('PAINEL', 'Cache da timeline invalidado.');
                } catch (err) {
                    log.error('PAINEL', 'Erro ao invalidar cache', err);
                }
            };
            painel.appendChild(limparBtn);

            _tornaPainelArrastavel(painel);
            document.body.appendChild(painel);
            PJeState.registry.add(() => painel.remove());
            log.dom(`Painel flutuante renderizado com ${botoes.length} botão(ões).`);
        } catch (err) {
            log.error('PAINEL', 'Erro ao criar elemento do painel no DOM', err);
        }
    };

    window._tornaPainelArrastavel = function (el) {
        let ox = 0, oy = 0, drag = false;
        const onDown = e => {
            if (e.target.tagName === 'BUTTON') return;
            drag = true; ox = e.clientX - el.offsetLeft; oy = e.clientY - el.offsetTop;
            e.preventDefault();
        };
        const onMove = e => {
            if (!drag) return;
            el.style.left = (e.clientX - ox) + 'px';
            el.style.top = (e.clientY - oy) + 'px';
            el.style.right = 'auto'; el.style.bottom = 'auto';
        };
        const onUp = () => { drag = false; };
        el.addEventListener('mousedown', onDown);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        PJeState.registry.add(() => {
            el.removeEventListener('mousedown', onDown);
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        });
    };

    window.inicializarPainel = function (prefs = {}) {
        if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) {
            log.painel('inicializarPainel: URL não é de detalhe, abortando.');
            return;
        }

        function isAtivo(key) {
            return (key in prefs) ? !!prefs[key] : true;
        }

        const todosBotoes = [
            {
                key: 'lista-check',
                id: 'btnCheck',
                texto: '🔎 Check',
                bg: '#007bff',
                fn: async () => {
                    if (typeof window.executarCheck === 'function') {
                        await window.executarCheck();
                    } else {
                        showToast('Módulo Lista Check não disponível', '#dc3545', 3000);
                        log.warn('PAINEL', 'window.executarCheck não encontrado');
                    }
                },
                titulo: 'Relatório de Medidas e Autocheck'
            },
            {
                key: 'lista-edital',
                id: 'btnEdital',
                texto: '📣 Edital',
                bg: '#28a745',
                fn: async () => {
                    if (typeof window.executarEdital === 'function') {
                        await window.executarEdital();
                    } else {
                        showToast('Módulo Edital não disponível', '#dc3545', 3000);
                        log.warn('PAINEL', 'window.executarEdital não encontrado');
                    }
                },
                titulo: 'Relatório de Editais'
            },
            {
                key: 'simba',
                id: 'btnSimba',
                texto: '⚖️ Simba',
                bg: '#ff9800',
                fn: async () => {
                    if (typeof window.executarSimba === 'function') {
                        await window.executarSimba();
                    } else {
                        showToast('Módulo Simba não carregado', '#dc3545', 3000);
                    }
                },
                titulo: 'Salvar dados e pesquisar no SIMBA'
            },
            {
                key: 'sisbajud',
                id: 'btnSisbajud',
                texto: '💸 Sisbajud',
                bg: '#1e88e5',
                fn: async () => {
                    if (typeof window.executarSisbajudPJe === 'function') {
                        await window.executarSisbajudPJe();
                    } else {
                        showToast('Módulo Sisbajud não carregado', '#dc3545', 3000);
                    }
                },
                titulo: 'Extrair Sisbajud'
            },
            {
                key: 'debito',
                id: 'btnDebito',
                texto: '💰 Débito',
                bg: '#17a2b8',
                fn: async () => {
                    if (window.PjeRegistrarDebito && typeof window.PjeRegistrarDebito.executar === 'function') {
                        await window.PjeRegistrarDebito.executar();
                    } else {
                        showToast('Módulo Débito não carregado', '#dc3545', 3000);
                    }
                },
                titulo: 'Registrar débito'
            },
            {
                key: 'argos',
                id: 'btnArgos',
                texto: '⚖️ Argos',
                bg: '#6f42c1',
                fn: async () => {
                    if (typeof window.executarArgos === 'function') {
                        await window.executarArgos();
                    } else {
                        showToast('Módulo Argos não carregado', '#dc3545', 3000);
                    }
                },
                titulo: 'Abrir Nova Pesquisa no ARGOS'
            }
        ];

        // Filtra os botões de acordo com as preferências do usuário no popup
        const botoesAtivos = todosBotoes.filter(b => isAtivo(b.key));
        log.painel(`Montando painel com ${botoesAtivos.length} botão(ões) habilitado(s) de ${todosBotoes.length}.`);

        criarPainel(botoesAtivos);
    };

})();
