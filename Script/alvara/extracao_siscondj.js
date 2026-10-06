// Script/alvara/extracao_siscondj.js — extração de dados dentro do SISCONDJ (fase 2).
//
// Responsabilidade: ler a tela/API do SISCONDJ e devolver dados estruturados
// para a minuta (Alv.minuta). Roda SOMENTE quando a aba ativa é do SISCONDJ.
//
// Alvo de tamanho na fase 2: ~300 linhas. Estrutura abaixo já organiza os
// pontos de extensão para chegar lá sem retrabalho:
//   - CONFIG: seletores/endpoints (preencher com os valores reais levantados
//     na fase 2 — usar o padrão de levantamento do gigs-plugin.js/hcalc-prep).
//   - _dom(): leitura de campos por seletor.
//   - _api(): leitura por endpoint, se disponível (XSRF igual dados_processo).
//   - extrairDadosSiscondj(): orquestra e devolve objeto canônico.

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    // ─────────────────────────────────────────────────────────────────
    // CONFIG — preencher na fase 2 com valores reais do SISCONDJ.
    // ─────────────────────────────────────────────────────────────────
    const CONFIG = {
        dominios: [
            'siscondj',
            'alvaraeletronico',
            'portaltrtsp'
        ],
        seletores: {
            numeroProcesso: '#numeroProcesso',
            btnBuscar: '#bt_buscar',
            tabelaContas: '#table_contas',
            btnEmitirMandato: '#bt_emitir_mandato'
        },
        endpoints: {}
    };

    function _ehSiscondj() {
        const host = (window.location.hostname || '').toLowerCase();
        const href = (window.location.href || '').toLowerCase();
        return CONFIG.dominios.some(d => host.includes(d) || href.includes(d));
    }

    function _log(...args) {
        console.log('[PjeAlvara][siscondj]', ...args);
    }

    // ─────────────────────────────────────────────────────────────────
    // LEITURA POR DOM
    // ─────────────────────────────────────────────────────────────────
    function _valorDoCampo(seletor) {
        const el = document.querySelector(seletor);
        return el ? String(el.value || el.innerText || '').trim() : '';
    }

    function _lerTela() {
        const dados = {};

        for (const [chave, seletor] of Object.entries(CONFIG.seletores)) {
            const valor = _valorDoCampo(seletor);
            if (valor) dados[chave] = valor;
        }

        return dados;
    }

    // ─────────────────────────────────────────────────────────────────
    // LEITURA POR API (opcional, fase 2)
    // ─────────────────────────────────────────────────────────────────
    async function _lerApi() {
        // TODO fase 2: GET com credentials include + XSRF, mesmo padrão de
        // Alv.dados (ver dados_processo.js). Retornar null se não houver.
        return null;
    }

    // ─────────────────────────────────────────────────────────────────
    // ORQUESTRADOR
    // ─────────────────────────────────────────────────────────────────

    /**
     * Extrai os dados correntes do SISCONDJ para a minuta.
     * Formato canônico devolvido (fase 2 define os campos finais):
     * {
     *     sucesso: true|false,
     *     tela: { ...campos lidos por seletor... },
     *     api:  { ...dados de endpoint, se houver... },
     *     origem: 'siscondj'
     * }
     */
    async function extrairDadosSiscondj() {
        if (!_ehSiscondj()) {
            return {
                sucesso: false,
                erro: 'aba atual nao e do SISCONDJ',
                origem: 'siscondj'
            };
        }

        const tela = _lerTela();
        const api = await _lerApi();

        const sucesso = Object.keys(tela).length > 0 || !!api;

        _log('extracao concluida — campos de tela:', Object.keys(tela).length);

        return {
            sucesso,
            tela,
            api,
            origem: 'siscondj'
        };
    }

    // API pública usada pelo painel de AUD; a busca efetiva fica centralizada
    // em siscon_consulta.js, que já conhece os endpoints e o parser do SISCON.
    async function consultarDocumento(documento) {
        if (!Alv.siscon || typeof Alv.siscon.consultarDocumento !== 'function') {
            throw new Error('Módulo de consulta SISCON não disponível.');
        }
        return Alv.siscon.consultarDocumento(documento);
    }

    // ─────────────────────────────────────────────────────────────────
    // FASE 2: INJEÇÃO DE CARDS DE VERBAS SALVAS NO SISCONDJ
    // ─────────────────────────────────────────────────────────────────
    function _escape(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function preencherCreditoExequente(d) {
        console.log('[Siscondj] Placeholder: preencherCreditoExequente', d);
        alert(`[Preenchimento: Crédito do Exequente]\nBeneficiário: ${d.destinatarioNome || 'N/A'}\nCPF/CNPJ: ${d.destinatarioDocumento || 'N/A'}\nValor: ${d.valor || 'N/A'}\nBanco: ${d.banco || 'N/A'}\nAg: ${d.agencia || 'N/A'} Conta: ${d.conta || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function preencherFgts(d) {
        console.log('[Siscondj] Placeholder: preencherFgts', d);
        alert(`[Preenchimento: FGTS]\nBanco: ${d.banco || 'N/A'}\nValor: ${d.valor || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function preencherInss(d) {
        console.log('[Siscondj] Placeholder: preencherInss', d);
        alert(`[Preenchimento: INSS]\nValor: ${d.valor || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function preencherCustas(d) {
        console.log('[Siscondj] Placeholder: preencherCustas', d);
        alert(`[Preenchimento: Custas]\nValor: ${d.valor || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function preencherHonorariosAutor(d) {
        console.log('[Siscondj] Placeholder: preencherHonorariosAutor', d);
        alert(`[Preenchimento: Honorários Autor]\nAdvogado: ${d.destinatarioNome || 'N/A'}\nCPF: ${d.destinatarioDocumento || 'N/A'}\nValor: ${d.valor || 'N/A'}\nBanco: ${d.banco || 'N/A'}\nAg: ${d.agencia || 'N/A'} Conta: ${d.conta || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function preencherHonorariosReclamada(d) {
        console.log('[Siscondj] Placeholder: preencherHonorariosReclamada', d);
        alert(`[Preenchimento: Honorários Reclamada]\nAdvogado: ${d.destinatarioNome || 'N/A'}\nCPF: ${d.destinatarioDocumento || 'N/A'}\nValor: ${d.valor || 'N/A'}\nBanco: ${d.banco || 'N/A'}\nAg: ${d.agencia || 'N/A'} Conta: ${d.conta || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function preencherHonorariosPericiais(d) {
        console.log('[Siscondj] Placeholder: preencherHonorariosPericiais', d);
        alert(`[Preenchimento: Honorários Periciais]\nPerito: ${d.destinatarioNome || 'N/A'}\nDocumento: ${d.destinatarioDocumento || 'N/A'}\nValor: ${d.valor || 'N/A'}\nBanco: ${d.banco || 'N/A'}\nAg: ${d.agencia || 'N/A'} Conta: ${d.conta || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function preencherDevolucaoReclamada(d) {
        console.log('[Siscondj] Placeholder: preencherDevolucaoReclamada', d);
        alert(`[Preenchimento: Devolução Reclamada]\nDestinatário: ${d.destinatarioNome || 'N/A'}\nValor: ${d.valor || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function preencherVerbaGenerica(tipo, d) {
        console.log('[Siscondj] Placeholder: preencherVerbaGenerica', tipo, d);
        alert(`[Preenchimento: ${tipo}]\nDestinatário: ${d.destinatarioNome || 'N/A'}\nValor: ${d.valor || 'N/A'}\n\n(Automação do formulário em desenvolvimento)`);
    }

    function executarPreenchimento(tipo, dados) {
        switch (tipo) {
            case 'Crédito do exequente':
                preencherCreditoExequente(dados);
                break;
            case 'FGTS':
                preencherFgts(dados);
                break;
            case 'Contribuições previdenciárias — INSS':
            case 'INSS':
                preencherInss(dados);
                break;
            case 'Custas':
                preencherCustas(dados);
                break;
            case 'Honorários advocatícios (autor)':
            case 'Honorários advocatícios':
                preencherHonorariosAutor(dados);
                break;
            case 'Honorários advocatícios (reclamada)':
                preencherHonorariosReclamada(dados);
                break;
            case 'Honorários periciais':
                preencherHonorariosPericiais(dados);
                break;
            case 'Devolução à reclamada':
                preencherDevolucaoReclamada(dados);
                break;
            default:
                preencherVerbaGenerica(tipo, dados);
        }
    }

    function renderizarCardSiscondj(item, idx) {
        const id = item.id || `verba-${idx}`;
        const tipo = item.tipo || 'Verba';
        const valor = item.valor || 'R$ 0,00';
        const nome = item.destinatarioNome || item.perito || '';
        const doc = item.destinatarioDocumento || '';
        const banco = item.dados?.banco || item.banco || '';
        const agencia = item.dados?.agencia || '';
        const conta = item.dados?.conta || '';
        const tipoConta = item.dados?.tipoConta || '';

        const ehFgts = tipo === 'FGTS';
        const temDadosBancarios = !['INSS', 'Contribuições previdenciárias — INSS', 'Custas'].includes(tipo) && !ehFgts;

        return `
            <div class="pje-siscondj-card" data-card-id="${_escape(id)}" style="background:#ffffff;border:1px solid #cbd5e1;border-radius:6px;padding:10px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-weight:bold;font-size:12px;color:#0369a1;background:#e0f2fe;padding:2px 6px;border-radius:4px;">${_escape(tipo)}</span>
                    <span style="font-size:11px;color:#64748b;">#${idx + 1}</span>
                </div>

                <div style="display:flex;flex-direction:column;gap:5px;font-size:12px;">
                    ${!['INSS', 'Contribuições previdenciárias — INSS', 'Custas'].includes(tipo) ? `
                        <div>
                            <label style="display:block;font-size:10px;color:#475569;font-weight:600;margin-bottom:1px;">Beneficiário</label>
                            <input type="text" data-campo="destinatarioNome" value="${_escape(nome)}" style="width:100%;box-sizing:border-box;padding:4px 6px;border:1px solid #cbd5e1;border-radius:3px;font-size:11px;">
                        </div>
                        <div>
                            <label style="display:block;font-size:10px;color:#475569;font-weight:600;margin-bottom:1px;">CPF / CNPJ</label>
                            <input type="text" data-campo="destinatarioDocumento" value="${_escape(doc)}" style="width:100%;box-sizing:border-box;padding:4px 6px;border:1px solid #cbd5e1;border-radius:3px;font-size:11px;">
                        </div>
                    ` : ''}

                    <div>
                        <label style="display:block;font-size:10px;color:#475569;font-weight:600;margin-bottom:1px;">Valor</label>
                        <input type="text" data-campo="valor" value="${_escape(valor)}" style="width:100%;box-sizing:border-box;padding:4px 6px;border:1px solid #cbd5e1;border-radius:3px;font-size:11px;font-weight:bold;color:#166534;">
                    </div>

                    ${temDadosBancarios ? `
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
                            <div>
                                <label style="display:block;font-size:10px;color:#475569;font-weight:600;margin-bottom:1px;">Banco</label>
                                <input type="text" data-campo="banco" value="${_escape(banco)}" placeholder="Banco" style="width:100%;box-sizing:border-box;padding:4px 6px;border:1px solid #cbd5e1;border-radius:3px;font-size:11px;">
                            </div>
                            <div>
                                <label style="display:block;font-size:10px;color:#475569;font-weight:600;margin-bottom:1px;">Agência</label>
                                <input type="text" data-campo="agencia" value="${_escape(agencia)}" placeholder="Agência" style="width:100%;box-sizing:border-box;padding:4px 6px;border:1px solid #cbd5e1;border-radius:3px;font-size:11px;">
                            </div>
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
                            <div>
                                <label style="display:block;font-size:10px;color:#475569;font-weight:600;margin-bottom:1px;">Conta</label>
                                <input type="text" data-campo="conta" value="${_escape(conta)}" placeholder="Conta" style="width:100%;box-sizing:border-box;padding:4px 6px;border:1px solid #cbd5e1;border-radius:3px;font-size:11px;">
                            </div>
                            <div>
                                <label style="display:block;font-size:10px;color:#475569;font-weight:600;margin-bottom:1px;">Tipo Conta</label>
                                <input type="text" data-campo="tipoConta" value="${_escape(tipoConta)}" placeholder="Corrente/Poupança" style="width:100%;box-sizing:border-box;padding:4px 6px;border:1px solid #cbd5e1;border-radius:3px;font-size:11px;">
                            </div>
                        </div>
                    ` : ''}

                    ${ehFgts ? `
                        <div>
                            <label style="display:block;font-size:10px;color:#475569;font-weight:600;margin-bottom:1px;">Banco do FGTS</label>
                            <input type="text" data-campo="banco" value="${_escape(banco || 'Banco do Brasil')}" style="width:100%;box-sizing:border-box;padding:4px 6px;border:1px solid #cbd5e1;border-radius:3px;font-size:11px;">
                        </div>
                        <button type="button" data-gerar-oficio-btn style="margin-top:2px;padding:5px;background:#0284c7;color:#fff;border:none;border-radius:4px;font-size:11px;font-weight:bold;cursor:pointer;">📄 Gerar Ofício</button>
                    ` : ''}
                </div>

                <button type="button" class="btn-preencher-verba" data-tipo="${_escape(tipo)}" style="width:100%;margin-top:8px;padding:6px;background:#16a34a;color:#ffffff;border:none;border-radius:4px;font-weight:bold;font-size:12px;cursor:pointer;transition:background 0.2s;">
                    Preencher
                </button>
            </div>
        `;
    }

    function iniciarPainelSiscondj() {
        if (!_ehSiscondj()) return;
        if (document.getElementById('pje-alvara-siscondj-dock')) return;

        let estado = null;
        try {
            if (typeof GM_getValue === 'function') {
                const raw = GM_getValue('pje_alvara_estado');
                if (raw) estado = JSON.parse(raw);
            }
        } catch (e) {
            console.warn('[PjeAlvara][siscondj] erro ao ler GM_getValue:', e);
        }

        if (!estado) {
            try {
                const raw = localStorage.getItem('pje_elaboracao_alvara_v1');
                if (raw) estado = JSON.parse(raw);
            } catch (e) {}
        }

        if (!estado || !Array.isArray(estado.itens) || estado.itens.length === 0) {
            console.log('[PjeAlvara][siscondj] Nenhuma verba salva encontrada no estado.');
            return;
        }

        const dock = document.createElement('div');
        dock.id = 'pje-alvara-siscondj-dock';
        dock.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            width: 360px;
            max-height: 90vh;
            z-index: 2147483646;
            background: #f8fafc;
            border: 2px solid #0284c7;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.25);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        `;

        const numProc = (estado.processo && estado.processo.numero) || estado.processoId || '';

        dock.innerHTML = `
            <div style="background:#0284c7;color:#ffffff;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;cursor:move;">
                <div>
                    <strong style="font-size:13px;display:block;">PJe Alvará — Verbas</strong>
                    <span style="font-size:11px;opacity:0.9;">Processo: ${_escape(numProc)}</span>
                </div>
                <button type="button" id="pje-siscondj-btn-toggle" style="background:transparent;border:none;color:#fff;font-size:16px;cursor:pointer;padding:0 4px;" title="Minimizar / Expandir">−</button>
            </div>
            <div id="pje-siscondj-status-bar" style="background:#e0f2fe;border-bottom:1px solid #bae6fd;padding:6px 10px;font-size:11px;font-weight:600;display:flex;align-items:center;gap:6px;">
                <span>⚡</span>
                <span id="pje-siscondj-status-msg" style="color:#0369a1;">PJe Alvará ativo</span>
            </div>
            <div id="pje-siscondj-body" style="padding:10px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;max-height:calc(90vh - 85px);">
                ${estado.itens.map(renderizarCardSiscondj).join('')}
            </div>
        `;

        document.body.appendChild(dock);

        // Toggle minimizar
        const btnToggle = dock.querySelector('#pje-siscondj-btn-toggle');
        const bodyEl = dock.querySelector('#pje-siscondj-body');
        const statusBar = dock.querySelector('#pje-siscondj-status-bar');
        btnToggle?.addEventListener('click', () => {
            if (bodyEl.style.display === 'none') {
                bodyEl.style.display = 'flex';
                if (statusBar) statusBar.style.display = 'flex';
                btnToggle.textContent = '−';
            } else {
                bodyEl.style.display = 'none';
                if (statusBar) statusBar.style.display = 'none';
                btnToggle.textContent = '+';
            }
        });

        // Eventos dos cards (Preencher e Gerar Ofício)
        dock.addEventListener('click', event => {
            if (event.target.closest('[data-gerar-oficio-btn]')) {
                event.preventDefault();
                alert('Gerar Ofício: função em desenvolvimento (placeholder da fase 1/2).');
                return;
            }

            const btnPreencher = event.target.closest('.btn-preencher-verba');
            if (btnPreencher) {
                event.preventDefault();
                const card = btnPreencher.closest('.pje-siscondj-card');
                const tipo = btnPreencher.getAttribute('data-tipo');
                const dados = {};

                card.querySelectorAll('[data-campo]').forEach(input => {
                    dados[input.getAttribute('data-campo')] = input.value.trim();
                });

                executarPreenchimento(tipo, dados);
            }
        });

        console.log('[PjeAlvara][siscondj] Painel de verbas injetado com sucesso:', estado.itens.length, 'verba(s).');

        // Dispara a automação de páginas
        iniciarAutomacaoSiscondj();
    }

    // ─────────────────────────────────────────────────────────────────
    // FASE 2: AUTOMAÇÃO DE BUSCA DE CONTAS E SELEÇÃO DE PARCELAS
    // ─────────────────────────────────────────────────────────────────
    function _parseMoeda(str) {
        if (!str) return 0;
        const limpo = String(str).replace(/[^\d,\.-]/g, '').replace(/\./g, '').replace(',', '.');
        const num = parseFloat(limpo);
        return isNaN(num) ? 0 : num;
    }

    function _atualizarStatusDock(msg, tipo) {
        _log(msg);
        const el = document.getElementById('pje-siscondj-status-msg');
        if (el) {
            el.textContent = msg;
            el.style.color = tipo === 'ok' ? '#166534' : (tipo === 'warn' ? '#854d0e' : '#0369a1');
        }
    }

    let _consultaIniciada = false;
    let _mandatoClicado = false;

    // Etapa 1: Preenche o número do processo, clica em buscar e, ao constar valor disponível, clica em emitir mandado
    function executarFluxoConsultaContas() {
        if (_mandatoClicado) return;

        const inputProc = document.getElementById('numeroProcesso');
        const btnBuscar = document.getElementById('bt_buscar');
        const tabelaContas = document.getElementById('table_contas');
        const btnEmitirMandato = document.getElementById('bt_emitir_mandato');

        // Se a tabela de contas já foi carregada e tem valor disponível:
        if (tabelaContas) {
            const linhasContas = Array.from(tabelaContas.querySelectorAll('tr[id^="linhaConta_"]'));
            const linhasComValor = linhasContas.filter(tr => {
                const tdDisp = tr.querySelector('[id^="td_saldo_corrigido_conta_"]');
                const texto = (tdDisp?.innerText || '').trim();
                return texto.includes('R$') && !tr.querySelector('img.rotate');
            });

            if (linhasComValor.length > 0) {
                const primeiraComSaldo = linhasComValor.find(tr => {
                    const tdDisp = tr.querySelector('[id^="td_saldo_corrigido_conta_"]');
                    return _parseMoeda(tdDisp?.innerText) > 0;
                }) || linhasComValor[0];

                const saldoTexto = primeiraComSaldo.querySelector('[id^="td_saldo_corrigido_conta_"]')?.innerText?.trim() || '';
                _atualizarStatusDock(`Contas localizadas! Valor disponível: ${saldoTexto}. Emitindo mandado...`, 'ok');

                if (btnEmitirMandato && !_mandatoClicado) {
                    _mandatoClicado = true;
                    setTimeout(() => {
                        _log('Clicando em bt_emitir_mandato...');
                        if (typeof window.executarAcao_bt_emitir_mandato === 'function') {
                            try { window.executarAcao_bt_emitir_mandato(); } catch (e) { btnEmitirMandato.click(); }
                        } else {
                            btnEmitirMandato.click();
                        }
                    }, 500);
                }
                return;
            }
        }

        // Se ainda não buscou: preenche o número do processo e clica em buscar
        if (inputProc && !_consultaIniciada) {
            let numProc = '';
            try {
                if (typeof GM_getValue === 'function') {
                    numProc = GM_getValue('pje_alvara_processo') || '';
                }
            } catch (e) {}

            if (!numProc) {
                const param = new URLSearchParams(window.location.search).get('numeroDoProcesso');
                if (param) {
                    numProc = decodeURIComponent(param).replace(/^avjtSiscondjConsultarAlvaras/i, '').trim();
                }
            }

            if (!numProc) {
                numProc = inputProc.value.trim();
            }

            if (numProc) {
                if (inputProc.value.trim() !== numProc) {
                    inputProc.value = numProc;
                    inputProc.dispatchEvent(new Event('input', { bubbles: true }));
                    inputProc.dispatchEvent(new Event('change', { bubbles: true }));
                    if (typeof window.Mascara === 'function' && window.ProcessoNumero) {
                        try { window.Mascara(inputProc, window.ProcessoNumero); } catch (e) {}
                    }
                }

                _atualizarStatusDock(`Processo ${numProc} preenchido. Clicando em buscar...`);

                if (btnBuscar) {
                    _consultaIniciada = true;
                    setTimeout(() => {
                        _log('Clicando em bt_buscar...');
                        if (typeof window.executarAcao_bt_buscar === 'function') {
                            try { window.executarAcao_bt_buscar(); } catch (e) { btnBuscar.click(); }
                        } else {
                            btnBuscar.click();
                        }
                    }, 400);
                }
            }
        }
    }

    let _parcelaExpandida = false;
    let _parcelaSelecionada = false;

    // Etapa 2: Na tela de novo mandado (pages/mandado/pagamento/new/*), espera valor disponível, expande parcelas e clica no checkbox da parcela com saldo
    function executarFluxoNovoMandado() {
        if (_parcelaSelecionada) return;

        const tabelaContas = document.getElementById('table_contas') || document.querySelector('table.relatorio');
        if (!tabelaContas) return;

        // 1. Espera povoar a coluna "Valor Disponível"
        const linhasContas = Array.from(tabelaContas.querySelectorAll('tr[id^="linhaConta_"]'));
        if (linhasContas.length === 0) return;

        const linhasComSaldo = linhasContas.filter(tr => {
            const tdDisp = tr.querySelector('[id^="td_saldo_corrigido_conta_"]');
            const texto = (tdDisp?.innerText || '').trim();
            return texto.includes('R$') && !tr.querySelector('img.rotate');
        });

        if (linhasComSaldo.length === 0) {
            _atualizarStatusDock('Aguardando povoamento do valor disponível nas contas judiciais...');
            return;
        }

        // Encontra a conta judicial com saldo disponível
        const contaComSaldo = linhasComSaldo.find(tr => {
            const tdDisp = tr.querySelector('[id^="td_saldo_corrigido_conta_"]');
            return _parseMoeda(tdDisp?.innerText) > 0;
        }) || linhasComSaldo[0];

        const contaIdMatch = contaComSaldo.id.match(/linhaConta_(\d+)/);
        const contaId = contaIdMatch ? contaIdMatch[1] : '';

        // 2. Clica no ícone de soma para expandir parcelas
        const subTabela = contaId ? document.getElementById('contaId_' + contaId) : document.querySelector('tr.subtabela');
        const estaExpandida = subTabela && subTabela.style.display !== 'none';

        if (!estaExpandida && !_parcelaExpandida) {
            const btnSoma = contaComSaldo.querySelector('img[onclick*="abrirParcelasEvent"], img[src*="soma-ico"], img#ico-img, img[alt="Parcelas"]');
            if (btnSoma) {
                _atualizarStatusDock(`Expandindo parcelas da conta judicial ${contaId}...`);
                _parcelaExpandida = true;
                setTimeout(() => {
                    if (contaId && typeof window.abrirParcelasEvent === 'function') {
                        try { window.abrirParcelasEvent(contaId, new MouseEvent('click')); } catch (e) { btnSoma.click(); }
                    } else {
                        btnSoma.click();
                    }
                }, 300);
            }
            return;
        }

        // 3. Na tabela que expande, espera povoar os valores e seleciona a parcela com saldo disponível
        if (subTabela) {
            const tabelaParcelas = subTabela.querySelector('table.subrelatorio, [id^="tabela_parcelas_conta_"]');
            if (!tabelaParcelas) return;

            const linhasParcelas = Array.from(tabelaParcelas.querySelectorAll('tr[id^="linhaParcela_"]'));
            if (linhasParcelas.length === 0) return;

            // Verifica se ainda há imagens girando (refresh.png / rotate)
            const aindaCarregando = tabelaParcelas.querySelector('img.rotate, img[src*="refresh"]');
            if (aindaCarregando) {
                _atualizarStatusDock('Aguardando atualização dos saldos das parcelas...');
                return;
            }

            // Procura a linha com valor disponível > 0
            let parcelaAlvo = null;
            let saldoAlvoTexto = '';

            for (const linha of linhasParcelas) {
                const tdDisp = linha.querySelector('[id^="td_saldo_parcela_saldo_"]');
                const texto = (tdDisp?.innerText || '').trim();
                const valorNum = _parseMoeda(texto);

                if (valorNum > 0) {
                    parcelaAlvo = linha;
                    saldoAlvoTexto = texto;
                    break;
                }
            }

            // Se encontrou a parcela com saldo disponível:
            if (parcelaAlvo && !_parcelaSelecionada) {
                const chk = parcelaAlvo.querySelector('input[name="parcelasSelecionadas"], input[id^="parcelasSelecionadas_"], input[type="checkbox"]');
                if (chk) {
                    _parcelaSelecionada = true;
                    _atualizarStatusDock(`Parcela com saldo encontrada (${saldoAlvoTexto})! Selecionando checkbox...`, 'ok');
                    setTimeout(() => {
                        if (!chk.checked) {
                            chk.click();
                        }
                        _log('Checkbox da parcela marcado com sucesso!', parcelaAlvo.id);
                        _atualizarStatusDock(`Parcela selecionada (${saldoAlvoTexto})! Pronto para emissão de alvará.`, 'ok');
                    }, 300);
                }
            } else if (!parcelaAlvo && linhasParcelas.length > 0) {
                _atualizarStatusDock('Nenhuma parcela com saldo disponível positivo identificada.', 'warn');
            }
        }
    }

    function iniciarAutomacaoSiscondj() {
        if (!_ehSiscondj()) return;

        const executarPasso = () => {
            const url = window.location.href;
            if (url.includes('/pages/mandado/pagamento/new')) {
                executarFluxoNovoMandado();
            } else if (url.includes('/pages/movimentacao/conta/new') || document.getElementById('numeroProcesso')) {
                executarFluxoConsultaContas();
            }
        };

        setInterval(executarPasso, 800);
        executarPasso();
    }

    Alv.siscondj = {
        extrairDadosSiscondj,
        consultarDocumento,
        iniciarPainelSiscondj,
        iniciarAutomacaoSiscondj,
        executarFluxoConsultaContas,
        executarFluxoNovoMandado,
        executarPreenchimento
    };
})();
