// Script/alvara/dock_siscondj.js — Painel flutuante (dock) no SISCONDJ (fase 2).
//
// Responsabilidade: renderizar a barra lateral e os cards de verbas no SISCONDJ,
// permitindo ao usuário visualizar, ajustar e disparar o preenchimento automatizado.

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    function _escape(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function atualizarStatus(msg, tipo) {
        console.log('[PjeAlvara][dock]', msg);
        const el = document.getElementById('pje-siscondj-status-msg');
        if (el) {
            el.textContent = msg;
            el.style.color = tipo === 'ok' ? '#166534' : (tipo === 'warn' ? '#854d0e' : '#0369a1');
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
        const itemJsonStr = JSON.stringify(item);

        return `
            <div class="pje-siscondj-card" data-card-id="${_escape(id)}" data-item-json="${_escape(itemJsonStr)}" style="background:#ffffff;border:1px solid #cbd5e1;border-radius:6px;padding:10px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
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
                    ⚡ Preencher
                </button>
            </div>
        `;
    }

    function iniciarPainelSiscondj() {
        const host = (window.location.hostname || '').toLowerCase();
        const href = (window.location.href || '').toLowerCase();
        const ehSiscon = ['siscondj', 'alvaraeletronico', 'portaltrtsp'].some(d => host.includes(d) || href.includes(d));
        if (!ehSiscon) return;

        if (document.getElementById('pje-alvara-siscondj-dock')) return;

        let estado = null;
        try {
            if (typeof GM_getValue === 'function') {
                const raw = GM_getValue('pje_alvara_estado');
                if (raw) estado = JSON.parse(raw);
            }
        } catch (e) {
            console.warn('[PjeAlvara][dock] erro ao ler GM_getValue:', e);
        }

        if (!estado) {
            try {
                const raw = localStorage.getItem('pje_elaboracao_alvara_v1');
                if (raw) estado = JSON.parse(raw);
            } catch (e) {}
        }

        if (!estado || !Array.isArray(estado.itens) || estado.itens.length === 0) {
            console.log('[PjeAlvara][dock] Nenhuma verba salva encontrada no estado.');
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
                const dadosForm = {};

                card.querySelectorAll('[data-campo]').forEach(input => {
                    dadosForm[input.getAttribute('data-campo')] = input.value.trim();
                });

                let itemCompleto = {};
                try {
                    const rawJson = card.getAttribute('data-item-json');
                    if (rawJson) itemCompleto = JSON.parse(rawJson);
                } catch (e) {}

                const itemFinal = Object.assign({}, itemCompleto, dadosForm);
                if (dadosForm.banco || dadosForm.agencia || dadosForm.conta || dadosForm.tipoConta) {
                    itemFinal.dados = Object.assign({}, itemCompleto.dados, {
                        banco: dadosForm.banco !== undefined ? dadosForm.banco : itemCompleto.dados?.banco,
                        agencia: dadosForm.agencia !== undefined ? dadosForm.agencia : itemCompleto.dados?.agencia,
                        conta: dadosForm.conta !== undefined ? dadosForm.conta : itemCompleto.dados?.conta,
                        tipoConta: dadosForm.tipoConta !== undefined ? dadosForm.tipoConta : itemCompleto.dados?.tipoConta
                    });
                }

                if (Alv.preenchimentoSiscondj && typeof Alv.preenchimentoSiscondj.executarPreenchimento === 'function') {
                    Alv.preenchimentoSiscondj.executarPreenchimento(tipo, itemFinal);
                } else if (Alv.siscondj && typeof Alv.siscondj.executarPreenchimento === 'function') {
                    Alv.siscondj.executarPreenchimento(tipo, itemFinal);
                } else {
                    alert('Módulo de preenchimento Siscondj não carregado.');
                }
            }
        });

        console.log('[PjeAlvara][dock] Painel de verbas injetado:', estado.itens.length, 'verba(s).');

        // Dispara a automação de navegação/seleção de contas
        if (Alv.preenchimentoSiscondj?.iniciarAutomacaoSiscondj) {
            Alv.preenchimentoSiscondj.iniciarAutomacaoSiscondj();
        } else if (Alv.siscondj?.iniciarAutomacaoSiscondj) {
            Alv.siscondj.iniciarAutomacaoSiscondj();
        }
    }

    Alv.dockSiscondj = {
        atualizarStatus,
        renderizarCardSiscondj,
        iniciarPainelSiscondj
    };

    // Atalhos para compatibilidade com fachada Alv.siscondj
    Alv.siscondj = Alv.siscondj || {};
    Alv.siscondj.iniciarPainelSiscondj = iniciarPainelSiscondj;
    Alv.siscondj.atualizarStatusDock = atualizarStatus;
})();
