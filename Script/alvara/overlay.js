// Script/alvara/overlay.js - cards de verba, eventos e abertura do painel lateral.
(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});
    const utils = Alv.utils;
    const OVERLAY_ID = Alv.const.OVERLAY_ID;
    const logAviso = Alv.log.aviso;
    const estado = Alv.estado;
    const estilos = Alv.estilos.estilos;
    const criarItemManual = estado.criarItemManual;
    const carregarEstado = estado.carregarEstado;
    const salvarEstado = estado.salvarEstado;
    const atualizarEstadoPeloOverlay = estado.atualizarEstadoPeloOverlay;
    const aplicarMascaraCampos = estado.aplicarMascaraCampos;
    function campoDadosHtml(item) {
        if (
            item.id === 'inss' ||
            item.id === 'custas'
        ) {
            return `
                <div class="pje-alvara-info">
                    Dados bancários não aplicáveis nesta fase.
                </div>
            `;
        }

        if (item.id === 'transferencia-outro-processo' ||
            item.tipo === 'Transferência para outro processo') {
            return `
                <label>
                    Número do processo de destino
                    <input
                        data-field="processoDestino"
                        placeholder="0000000-00.0000.0.00.0000"
                        value="${utils.escapeHtml(
                            item.transferencia?.processoDestino || ''
                        )}"
                    >
                </label>

                <label>
                    Tribunal de destino
                    <input
                        data-field="tribunalDestino"
                        placeholder="Tribunal de destino"
                        value="${utils.escapeHtml(
                            item.transferencia?.tribunalDestino || ''
                        )}"
                    >
                </label>

                <label>
                    Unidade judicial de destino
                    <input
                        data-field="unidadeDestino"
                        placeholder="Vara ou unidade de destino"
                        value="${utils.escapeHtml(
                            item.transferencia?.unidadeDestino || ''
                        )}"
                    >
                </label>

                <div class="pje-alvara-info">
                    A transferência será implementada na fase 2,
                    dentro do SISCONDJ.
                </div>
            `;
        }

        if (item.id === 'honorarios-periciais' ||
            item.tipo === 'Honorários periciais') {
            return `
                <label>
                    Perito
                    <select data-field="perito">
                        <option value="">Selecione o perito</option>
                        <option value="__PLACEHOLDER_PLANILHA__">
                            Lista de peritos — integração futura
                        </option>
                    </select>
                </label>

                <div class="pje-alvara-info">
                    Os dados do perito serão carregados futuramente
                    a partir de uma planilha.
                </div>

                <div class="pje-alvara-dados-grid">
                    <label>
                        Banco
                        <input
                            data-field="banco"
                            placeholder="Banco"
                            value="${utils.escapeHtml(
                                item.dados?.banco || ''
                            )}"
                        >
                    </label>

                    <label>
                        Agência
                        <input
                            data-field="agencia"
                            placeholder="Agência"
                            value="${utils.escapeHtml(
                                item.dados?.agencia || ''
                            )}"
                        >
                    </label>

                    <label>
                        Conta
                        <input
                            data-field="conta"
                            placeholder="Conta"
                            value="${utils.escapeHtml(
                                item.dados?.conta || ''
                            )}"
                        >
                    </label>

                    <label>
                        Tipo de conta
                        <input
                            data-field="tipoConta"
                            placeholder="Corrente ou poupança"
                            value="${utils.escapeHtml(
                                item.dados?.tipoConta || ''
                            )}"
                        >
                    </label>
                </div>
            `;
        }

        // Sequência visual do preenchimento: Nome e documento → Agência →
        // Conta → Banco. ID de depósito não é exibido (irrelevante no overlay).
        return `
            <div class="pje-alvara-dados-grid">
                <label>
                    Nome do destinatário
                    <input
                        data-field="destinatarioNome"
                        placeholder="Nome"
                        value="${utils.escapeHtml(
                            item.destinatarioNome || ''
                        )}"
                    >
                </label>

                <label>
                    CPF ou CNPJ
                    <input
                        data-field="destinatarioDocumento"
                        placeholder="CPF ou CNPJ"
                        value="${utils.escapeHtml(
                            item.destinatarioDocumento || ''
                        )}"
                    >
                </label>

                <label>
                    Agência
                    <input
                        data-field="agencia"
                        placeholder="Agência"
                        value="${utils.escapeHtml(
                            item.dados?.agencia || ''
                        )}"
                    >
                </label>

                <label>
                    Conta
                    <input
                        data-field="conta"
                        placeholder="Conta"
                        value="${utils.escapeHtml(
                            item.dados?.conta || ''
                        )}"
                    >
                </label>

                <label>
                    Banco
                    <input
                        data-field="banco"
                        placeholder="Banco"
                        value="${utils.escapeHtml(
                            item.dados?.banco || ''
                        )}"
                    >
                </label>

                <label>
                    Tipo de conta
                    <input
                        data-field="tipoConta"
                        placeholder="Corrente ou poupança"
                        value="${utils.escapeHtml(
                            item.dados?.tipoConta || ''
                        )}"
                    >
                </label>
            </div>

            <button
                type="button"
                class="pje-alvara-secondary"
                data-siscon-button
            >
                Puxar do SISCON
            </button>
        `;
    }

    function opcoesDestino(item) {
        if (
            item.id === 'credito' ||
            item.tipo === 'Crédito do exequente'
        ) {
            return `
                <option value="Transferência para conta do advogado">
                    Transferência para conta do advogado
                </option>
                <option value="Conta escritório">
                    Conta escritório
                </option>
                <option value="Conta reclamante">
                    Conta reclamante
                </option>
            `;
        }

        if (
            item.id === 'honorarios-advocaticios' ||
            item.tipo === 'Honorários advocatícios'
        ) {
            return `
                <option value="Conta do advogado autor">
                    Conta do advogado autor
                </option>
                <option value="Conta escritório">
                    Conta escritório
                </option>
            `;
        }

        if (
            item.id === 'inss' ||
            item.tipo === 'INSS' ||
            item.tipo === 'Contribuições previdenciárias — INSS'
        ) {
            return `<option value="DARF">DARF</option>`;
        }

        if (
            item.id === 'custas' ||
            item.tipo === 'Custas'
        ) {
            return `<option value="GRU">GRU</option>`;
        }

        if (
            item.id === 'honorarios-periciais' ||
            item.tipo === 'Honorários periciais'
        ) {
            return `
                <option value="Conta do perito">
                    Conta do perito
                </option>
            `;
        }

        if (
            item.id === 'devolucao-reclamada' ||
            item.tipo === 'Devolução à reclamada'
        ) {
            return `
                <option value="Conta da reclamada">
                    Conta da reclamada
                </option>
                <option value="Conta do procurador da reclamada">
                    Conta do procurador da reclamada
                </option>
                <option value="Conta escritório da reclamada">
                    Conta escritório da reclamada
                </option>
            `;
        }

        if (
            item.id === 'transferencia-outro-processo' ||
            item.tipo === 'Transferência para outro processo'
        ) {
            return `
                <option value="Novo depósito em outro processo">
                    Novo depósito em outro processo
                </option>
            `;
        }

        return `
            <option value="">
                Selecione o tipo
            </option>
        `;
    }

    function renderCard(item, index) {
        const temDados = ![
            'inss',
            'custas',
            'transferencia-outro-processo'
        ].includes(item.id) &&
            item.tipo !== 'Transferência para outro processo';

        const avisoValorPendente =
            item.valorPendente === true
                ? `
                <div class="pje-alvara-pendente">
                    Valor não localizado na decisão.
                    <br>
                    Depósito identificado:
                    ${
                        item.deposito?.id
                            ? `#id:${utils.escapeHtml(item.deposito.id)}`
                            : 'ID não identificado'
                    }
                    ${
                        item.deposito?.banco
                            ? ` — ${utils.escapeHtml(item.deposito.banco)}`
                            : ''
                    }
                    <br>
                    Implementar aqui a leitura do depósito via API.
                </div>
              `
                : '';

        return `
            <section
                class="pje-alvara-card"
                data-alvara-card
                data-item-id="${utils.escapeHtml(item.id)}"
                data-origem="${utils.escapeHtml(
                    item.origem || 'extraído da decisão'
                )}"
            >
                <div class="pje-alvara-card-header">
                    <span class="pje-alvara-index">${index + 1}</span>

                    <input
                        class="pje-alvara-tipo"
                        data-field="tipo"
                        value="${utils.escapeHtml(item.tipo)}"
                    >

                    <button
                        type="button"
                        class="pje-alvara-remove"
                        data-remove-card
                        title="Remover este tipo"
                    >
                        Remover
                    </button>
                </div>

                <div class="pje-alvara-origem">
                    ${utils.escapeHtml(
                        item.origem || 'extraído da decisão'
                    )}
                </div>

                ${avisoValorPendente}

                <label>
                    Valor
                    <input
                        data-field="valor"
                        ${
                            item.valorFixo === true
                                ? 'data-fixo="true" readonly'
                                : 'data-money-input="true"'
                        }
                        value="${utils.escapeHtml(item.valor)}"
                    >
                </label>

                <label>
                    Destinatário / tipo
                    <select data-field="destinoTipo">
                        ${opcoesDestino(item)}
                    </select>
                </label>

                ${
                    temDados
                        ? `<div class="pje-alvara-dados">
                            <div class="pje-alvara-subtitle">
                                Dados do destinatário
                            </div>
                            ${campoDadosHtml(item)}
                           </div>`
                        : `<div class="pje-alvara-dados">
                            ${campoDadosHtml(item)}
                           </div>`
                }
            </section>
        `;
    }
    function abrirOverlay(estado) {
        const existente = document.getElementById(OVERLAY_ID);
        if (existente) existente.remove();

        const overlay = document.createElement('div');
        overlay.id = OVERLAY_ID;

        overlay.innerHTML = `
            ${estilos()}

            <div class="pje-alvara-window">
                <header class="pje-alvara-header">
                    <div>
                        <h2>Elaboração de alvarás</h2>
                        <small>
                            ${
                                (estado.processo && estado.processo.numero)
                                    ? `Processo ${utils.escapeHtml(estado.processo.numero)}`
                                    : `Processo ${utils.escapeHtml(estado.processoId || 'não identificado')}`
                            }
                        </small>
                    </div>

                    <button
                        type="button"
                        class="pje-alvara-close"
                        data-close
                        title="Fechar"
                    >
                        ×
                    </button>
                </header>

                <main class="pje-alvara-content">
                    <div class="pje-alvara-alert">
                        Confira valores e destinatários antes de criar os alvarás.
                    </div>

                    <div data-cards>
                        ${
                            estado.itens.length
                                ? estado.itens.map(renderCard).join('')
                                : `<div class="pje-alvara-empty">
                                    Nenhum tipo de verba detectado na decisão.
                                   </div>`
                        }
                    </div>
                </main>

                <footer class="pje-alvara-footer">
                    <span class="pje-alvara-status" data-status-salvamento>
                        Dados carregados para conferência
                    </span>

                    <div class="pje-alvara-add-row">
                        <select class="pje-alvara-add-select" data-novo-tipo>
                            <option value="">Selecione a verba…</option>
                            <option>Crédito do exequente</option>
                            <option>INSS</option>
                            <option>Custas</option>
                            <option>Honorários advocatícios</option>
                            <option>Honorários periciais</option>
                            <option>Devolução à reclamada</option>
                            <option>Transferência para outro processo</option>
                        </select>

                        <button
                            type="button"
                            class="pje-alvara-add"
                            data-adicionar-tipo
                        >
                            Adicionar Verba
                        </button>
                    </div>

                    <button
                        type="button"
                        class="pje-alvara-primary"
                        data-criar-alvaras
                    >
                        Criar alvarás
                    </button>
                </footer>
            </div>
        `;

        document.body.appendChild(overlay);

        aplicarValoresDosSelects(overlay, estado);
        aplicarMascaraCampos(overlay);
        instalarEventosOverlay(overlay);

        // Consulta automática de dados bancários (verbas detectadas) —
        // verbas adicionadas depois são consultadas no momento em que surgem.
        if (Alv.siscon && Alv.siscon.inicializar) {
            Alv.siscon.inicializar(estado);
        }

        salvarEstado(estado);
    }

    function aplicarValoresDosSelects(overlay, estado) {
        estado.itens.forEach(item => {
            const card = overlay.querySelector(
                `[data-item-id="${CSS.escape(item.id)}"]`
            );

            if (!card) return;

            const destino = card.querySelector(
                '[data-field="destinoTipo"]'
            );

            if (destino && item.destinoTipo) {
                destino.value = item.destinoTipo;
            }

            const perito = card.querySelector(
                '[data-field="perito"]'
            );

            if (perito && item.perito) {
                perito.value = item.perito;
            }

            if (item.dados) {
                for (const campo of [
                    'banco',
                    'agencia',
                    'conta',
                    'tipoConta'
                ]) {
                    const input = card.querySelector(
                        `[data-field="${campo}"]`
                    );

                    if (input) {
                        input.value = item.dados[campo] || '';
                    }
                }
            }

            const processoDestino = card.querySelector(
                '[data-field="processoDestino"]'
            );

            if (processoDestino && item.transferencia) {
                processoDestino.value =
                    item.transferencia.processoDestino || '';
            }

            const tribunalDestino = card.querySelector(
                '[data-field="tribunalDestino"]'
            );

            if (tribunalDestino && item.transferencia) {
                tribunalDestino.value =
                    item.transferencia.tribunalDestino || '';
            }

            const unidadeDestino = card.querySelector(
                '[data-field="unidadeDestino"]'
            );

            if (unidadeDestino && item.transferencia) {
                unidadeDestino.value =
                    item.transferencia.unidadeDestino || '';
            }
        });
    }

    function instalarEventosRemocao(overlay) {
        overlay.querySelectorAll('[data-remove-card]')
            .forEach(button => {
                if (button.dataset.bound === 'true') {
                    return;
                }

                button.dataset.bound = 'true';

                button.addEventListener('click', () => {
                    const card = button.closest(
                        '[data-alvara-card]'
                    );

                    if (!card) {
                        return;
                    }

                    const tipo = card.querySelector(
                        '[data-field="tipo"]'
                    )?.value || 'este item';

                    const confirmar = window.confirm(
                        `Remover "${tipo}"?`
                    );

                    if (!confirmar) {
                        return;
                    }

                    card.remove();
                    atualizarEstadoPeloOverlay();
                });
            });
    }

    function instalarEventosOverlay(overlay) {
        overlay.querySelector('[data-close]')
            ?.addEventListener('click', () => {
                atualizarEstadoPeloOverlay();
                overlay.remove();
            });

        overlay.addEventListener('change', event => {
            if (
                event.target.matches(
                    'input, select, textarea'
                )
            ) {
                atualizarEstadoPeloOverlay();

                // Troca de destinatário/advogado → consulta só para este card.
                if (
                    window.Alv.siscon &&
                    event.target.matches('select[data-field="destinoTipo"]')
                ) {
                    const card = event.target.closest('[data-alvara-card]');

                    if (card) {
                        Alv.siscon.consultarNoCard(card, true);
                    }
                }
            }
        });

        overlay.addEventListener('input', event => {
            if (
                event.target.matches(
                    'input, select, textarea'
                )
            ) {
                atualizarEstadoPeloOverlay();
            }
        });

        // Fallback manual: reexecuta a consulta do card (ou a inicia, se a
        // automática falhou). Sem chamada por trás (ex.: escritório sem CNPJ),
        // informa e mantém os campos editáveis.
        overlay.querySelectorAll('[data-siscon-button]')
            .forEach(button => {
                button.addEventListener('click', () => {
                    const card = button.closest('[data-alvara-card]');

                    if (!card) {
                        return;
                    }

                    if (window.Alv.siscon) {
                        Alv.siscon.consultarNoCard(card, true);
                    }
                });
            });

        overlay.querySelector('[data-adicionar-tipo]')
            ?.addEventListener('click', () => {
                const select = overlay.querySelector('[data-novo-tipo]');
                const tipo = select?.value;

                if (!tipo) {
                    logAviso('selecione a verba antes de adicionar.');
                    return;
                }

                const novoItem = criarItemManual(tipo);

                const estado = carregarEstado() || {
                    versao: 1,
                    processoId: obterProcessoId(),
                    url: window.location.href,
                    itens: []
                };

                estado.itens = Array.isArray(estado.itens)
                    ? estado.itens
                    : [];

                estado.itens.push(novoItem);
                salvarEstado(estado);

                const cards = overlay.querySelector('[data-cards]');

                if (cards) {
                    const vazio = cards.querySelector('.pje-alvara-empty');

                    if (vazio) {
                        vazio.remove();
                    }

                    cards.insertAdjacentHTML(
                        'beforeend',
                        renderCard(
                            novoItem,
                            estado.itens.length - 1
                        )
                    );
                }

                if (select) {
                    select.value = '';
                }

                aplicarMascaraCampos(overlay);

                // Verba adicionada manualmente → consulta neste momento.
                if (window.Alv.siscon) {
                    const novoCard = cards
                        ? cards.querySelector(
                            '[data-item-id="' + CSS.escape(novoItem.id) + '"]'
                          )
                        : null;

                    if (novoCard) {
                        Alv.siscon.consultarNoCard(novoCard, true);
                    }
                }

                instalarEventosRemocao(overlay);
                atualizarEstadoPeloOverlay();
            });

        instalarEventosRemocao(overlay);

        overlay.querySelector('[data-criar-alvaras]')
            ?.addEventListener('click', () => {
                atualizarEstadoPeloOverlay();

                // Fase 2: gancho do processo seguinte (SISCONDJ) — ver minuta.js.
                const estado = carregarEstado();
                const resultado = window.Alv.minuta.iniciarFluxoMinuta(estado);

                if (!resultado || resultado.iniciado !== true) {
                    alert(
                        'Estrutura preparada. A criação efetiva dos alvarás será implementada na próxima etapa.' +
                        (resultado && resultado.motivo ? '\n\n' + resultado.motivo : '')
                    );
                }
            });
    }

    Alv.overlay = { abrirOverlay: abrirOverlay };
})();
