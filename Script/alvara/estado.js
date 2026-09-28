// Script/alvara/estado.js - estado do alvara: itens, storage, mascaras monetarias.
(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});
    const utils = Alv.utils;
    const STORAGE_KEY = Alv.const.STORAGE_KEY;
    const OVERLAY_ID = Alv.const.OVERLAY_ID;
    const aplicarPreenchimentoAutomatico = Alv.dados.aplicarPreenchimentoAutomatico;
    function criarIdItem(prefixo) {
        return `${prefixo}-${Date.now()}-${Math.random()
            .toString(36)
            .slice(2, 8)}`;
    }
    function valorInicial(valor) {
        return valor ? `R$ ${valor}` : 'R$ 0,00';
    }

    function criarItemDevolucaoReclamada(valores) {
        return {
            id: criarIdItem('devolucao-reclamada'),
            tipo: 'Devolução à reclamada',
            origem: 'extraído da decisão',
            valor: valorInicial(valores.devolucaoReclamadaValor),
            valorPendente: !valores.devolucaoReclamadaValor &&
                Boolean(valores.devolucaoReclamadaDeposito?.id),
            destinoTipo: 'Conta da reclamada',
            destinatarioNome: '',
            destinatarioDocumento: '',
            deposito: valores.devolucaoReclamadaDeposito || {
                detectado: false,
                id: '',
                banco: '',
                valor: '',
                pendenteConsulta: false
            },
            dados: {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            },
            siscon: true
        };
    }

    function criarItemTransferenciaOutroProcesso(valores) {
        return {
            id: criarIdItem('transferencia-outro-processo'),
            tipo: 'Transferência para outro processo',
            origem: 'extraído da decisão',
            valor: valorInicial(
                valores.transferenciaOutroProcessoValor
            ),
            valorPendente: !valores.transferenciaOutroProcessoValor &&
                Boolean(valores.transferenciaOutroProcessoDeposito?.id),
            destinoTipo: 'Novo depósito em outro processo',
            destinatarioNome: '',
            destinatarioDocumento: '',
            deposito: valores.transferenciaOutroProcessoDeposito || {
                detectado: false,
                id: '',
                banco: '',
                valor: '',
                pendenteConsulta: false
            },
            transferencia: {
                processoDestino:
                    valores.transferenciaProcessoDestino || '',
                tribunalDestino: '',
                unidadeDestino: ''
            },
            dados: null,
            siscon: true
        };
    }

    function criarItemManual(tipo) {
        const base = {
            id: criarIdItem('manual'),
            tipo,
            origem: 'adicionado manualmente',
            valor: 'R$ 0,00',
            valorPendente: false,
            destinoTipo: '',
            destinatarioNome: '',
            destinatarioDocumento: '',
            deposito: null,
            dados: null,
            siscon: true
        };

        if (tipo === 'Crédito do exequente') {
            base.destinoTipo =
                'Transferência para conta do advogado';

            base.dados = {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            };
        }

        if (tipo === 'INSS') {
            base.destinoTipo = 'DARF';
            base.siscon = false;
        }

        if (tipo === 'Custas') {
            base.destinoTipo = 'GRU';
            base.siscon = false;
        }

        if (tipo === 'Honorários advocatícios') {
            base.destinoTipo = 'Conta do advogado autor';
            base.dados = {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            };
        }

        if (tipo === 'Honorários periciais') {
            base.destinoTipo = 'Conta do perito';
            base.perito = '';
            base.dados = {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            };
        }

        if (tipo === 'Devolução à reclamada') {
            base.destinoTipo = 'Conta da reclamada';
            base.dados = {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            };
            base.deposito = {
                detectado: false,
                id: '',
                banco: '',
                valor: '',
                pendenteConsulta: false
            };
        }

        if (tipo === 'Transferência para outro processo') {
            base.destinoTipo =
                'Novo depósito em outro processo';

            base.dados = null;

            base.transferencia = {
                processoDestino: '',
                tribunalDestino: '',
                unidadeDestino: ''
            };

            base.deposito = {
                detectado: false,
                id: '',
                banco: '',
                valor: '',
                pendenteConsulta: false
            };
        }

        // Mesmas regras de preenchimento das verbas detectadas — usa o
        // cache dos dados do processo da última chamada de API.
        return aplicarPreenchimentoAutomatico(base, _dadosProcessoCache);
    }

    function criarEstado(valores, dadosProcesso) {
        // Só cria campos para os tipos DETECTADOS na decisão.
        // Tipos adicionais entram manualmente pelo botão "Adicionar Verba".
        // dadosProcesso (API /partes) alimenta Nome/CPF de beneficiários e
        // advogados conforme o tipo de verba.
        const itens = [];

        if (valores.credito || valores.creditoPorDepositoSemValor) {
            itens.push(aplicarPreenchimentoAutomatico({
                id: 'credito',
                tipo: 'Crédito do exequente',
                // "pagamento de parte de seu credito" -> valor depende do
                // deposito integral atualizado: texto fixo, NAO editavel.
                valor: valores.creditoParcialDeposito
                    ? 'Depósito integral atualizado'
                    : valorInicial(valores.credito),
                valorFixo: valores.creditoParcialDeposito === true,
                valorPendente: !valores.credito &&
                    valores.creditoPorDepositoSemValor === true &&
                    valores.creditoParcialDeposito !== true,
                origem: valores.creditoOrigem || '',
                deposito: valores.deposito || {
                    detectado: false,
                    id: '',
                    banco: ''
                },
                destinoTipo: 'Transferência para conta do advogado',
                destinatarioNome: '',
                destinatarioDocumento: '',
                dados: {
                    banco: '',
                    agencia: '',
                    conta: '',
                    tipoConta: ''
                },
                siscon: true
            }, dadosProcesso));
        }

        if (valores.inss) {
            itens.push({
                id: 'inss',
                tipo: 'Contribuições previdenciárias — INSS',
                valor: valorInicial(valores.inss),
                destinoTipo: 'DARF',
                dados: null,
                siscon: false
            });
        }

        if (valores.custas) {
            itens.push({
                id: 'custas',
                tipo: 'Custas',
                valor: valorInicial(valores.custas),
                destinoTipo: 'GRU',
                dados: null,
                siscon: false
            });
        }

        if (valores.honorariosAdvocaticios) {
            itens.push(aplicarPreenchimentoAutomatico({
                id: 'honorarios-advocaticios',
                tipo: 'Honorários advocatícios',
                valor: valorInicial(valores.honorariosAdvocaticios),
                destinoTipo: 'Conta do advogado autor',
                destinatarioNome: '',
                destinatarioDocumento: '',
                dados: {
                    banco: '',
                    agencia: '',
                    conta: '',
                    tipoConta: ''
                },
                siscon: true
            }, dadosProcesso));
        }

        if (valores.honorariosPericiais) {
            itens.push(aplicarPreenchimentoAutomatico({
                id: 'honorarios-periciais',
                tipo: 'Honorários periciais',
                valor: valorInicial(valores.honorariosPericiais),
                destinoTipo: 'Conta do perito',
                perito: valores.peritoNome || '',
                dados: {
                    banco: '',
                    agencia: '',
                    conta: '',
                    tipoConta: ''
                },
                siscon: false
            }, dadosProcesso));
        }

        if (valores.devolucaoReclamada) {
            itens.push(aplicarPreenchimentoAutomatico(
                criarItemDevolucaoReclamada(valores),
                dadosProcesso
            ));
        }

        if (valores.transferenciaOutroProcesso) {
            itens.push(criarItemTransferenciaOutroProcesso(valores));
        }

        return {
            versao: 1,
            processoId: (dadosProcesso && dadosProcesso.processoId) || obterProcessoId(),
            processo: dadosProcesso ? {
                numero: dadosProcesso.numero || '',
                partes: dadosProcesso.partes,
                peritos: dadosProcesso.peritos,
                consultadoEm: dadosProcesso.consultadoEm
            } : null,
            url: window.location.href,
            salvoEm: new Date().toISOString(),
            itens
        };
    }

    function salvarEstado(estado) {
        estado.salvoEm = new Date().toISOString();
        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(estado)
        );
    }

    function carregarEstado() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (error) {
            console.error('[PjeAlvara] Erro ao carregar estado:', error);
            return null;
        }
    }

    function aplicarMascaraMonetaria(input) {
        let somenteDigitos = input.value
            .replace(/\D/g, '');

        if (!somenteDigitos) {
            input.value = 'R$ 0,00';
            return;
        }

        const valor = parseInt(somenteDigitos, 10) / 100;

        input.value = utils.moneyWithSymbol(valor);
    }

    function aplicarMascaraCampos(container) {
        container.querySelectorAll(
            '[data-money-input="true"]'
        ).forEach(input => {
            input.addEventListener('focus', () => {
                input.select();
            });

            input.addEventListener('input', () => {
                aplicarMascaraMonetaria(input);
                atualizarEstadoPeloOverlay();
            });

            input.addEventListener('blur', () => {
                aplicarMascaraMonetaria(input);
                atualizarEstadoPeloOverlay();
            });
        });
    }

    function obterDadosDoCard(card) {
        const dados = {
            id: card.dataset.itemId,
            tipo: card.querySelector('[data-field="tipo"]')?.value || '',
            valor: card.querySelector('[data-field="valor"]')?.value || '',
            destinoTipo: card.querySelector('[data-field="destinoTipo"]')?.value || '',
            destinatarioNome:
                card.querySelector('[data-field="destinatarioNome"]')?.value || '',
            destinatarioDocumento:
                card.querySelector('[data-field="destinatarioDocumento"]')?.value || '',
            perito:
                card.querySelector('[data-field="perito"]')?.value || '',
            origem: card.dataset.origem || 'extraído da decisão'
        };

        const banco = card.querySelector('[data-field="banco"]');
        const agencia = card.querySelector('[data-field="agencia"]');
        const conta = card.querySelector('[data-field="conta"]');
        const tipoConta = card.querySelector('[data-field="tipoConta"]');

        if (banco || agencia || conta || tipoConta) {
            dados.dados = {
                banco: banco?.value || '',
                agencia: agencia?.value || '',
                conta: conta?.value || '',
                tipoConta: tipoConta?.value || ''
            };
        } else {
            dados.dados = null;
        }

        const depositoId = card.querySelector(
            '[data-field="depositoId"]'
        );

        const depositoBanco = card.querySelector(
            '[data-field="depositoBanco"]'
        );

        if (depositoId || depositoBanco) {
            dados.deposito = {
                detectado: Boolean(depositoId?.value),
                id: depositoId?.value || '',
                banco: depositoBanco?.value || '',
                valor: dados.valor,
                pendenteConsulta: !dados.valor ||
                    dados.valor === 'R$ 0,00'
            };
        }

        const processoDestino = card.querySelector(
            '[data-field="processoDestino"]'
        );

        const tribunalDestino = card.querySelector(
            '[data-field="tribunalDestino"]'
        );

        const unidadeDestino = card.querySelector(
            '[data-field="unidadeDestino"]'
        );

        if (processoDestino || tribunalDestino || unidadeDestino) {
            dados.transferencia = {
                processoDestino: processoDestino?.value || '',
                tribunalDestino: tribunalDestino?.value || '',
                unidadeDestino: unidadeDestino?.value || ''
            };
        }

        return dados;
    }

    function atualizarEstadoPeloOverlay() {
        const overlay = document.getElementById(OVERLAY_ID);
        if (!overlay) return;

        const estado = carregarEstado() || {
            versao: 1,
            processoId: obterProcessoId(),
            itens: []
        };

        estado.itens = Array.from(
            overlay.querySelectorAll('[data-alvara-card]')
        ).map(obterDadosDoCard).map(item => {
            if (
                item.tipo === 'Devolução à reclamada' ||
                item.id === 'devolucao-reclamada'
            ) {
                item.valorPendente =
                    !item.valor ||
                    item.valor === 'R$ 0,00';

                item.deposito = item.deposito || {
                    detectado: false,
                    id: '',
                    banco: '',
                    valor: '',
                    pendenteConsulta: false
                };
            }

            if (
                item.tipo === 'Transferência para outro processo' ||
                item.id === 'transferencia-outro-processo'
            ) {
                item.valorPendente =
                    !item.valor ||
                    item.valor === 'R$ 0,00';

                item.transferencia = item.transferencia || {
                    processoDestino: '',
                    tribunalDestino: '',
                    unidadeDestino: ''
                };
            }

            return item;
        });

        salvarEstado(estado);

        const status = overlay.querySelector(
            '[data-status-salvamento]'
        );

        if (status) {
            status.textContent =
                `Salvo para conferência às ${new Date().toLocaleTimeString('pt-BR')}`;
        }
    }

    Alv.estado = {
        criarEstado: criarEstado,
        salvarEstado: salvarEstado,
        carregarEstado: carregarEstado,
        atualizarEstadoPeloOverlay: atualizarEstadoPeloOverlay,
        aplicarMascaraCampos: aplicarMascaraCampos,
        aplicarMascaraMonetaria: aplicarMascaraMonetaria,
        criarItemManual: criarItemManual
    };
})();
