// Script/alvara/preenchimento_siscondj.js — Motor de Preenchimento e Automação no SISCONDJ (fase 2).
//
// Responsabilidade:
// 1. Automatizar a navegação entre telas: buscar processo, aguardar saldo, emitir mandado, selecionar parcela com saldo.
// 2. Preencher os formulários de cada verba na tela de novo mandado (baseado nas especificações reais de av.md).

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    function _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function _status(msg, tipo) {
        if (Alv.dockSiscondj?.atualizarStatus) {
            Alv.dockSiscondj.atualizarStatus(msg, tipo);
        } else {
            console.log('[PjeAlvara][preenchimento]', msg);
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // PRIMITIVAS DE MANIPULAÇÃO DE CAMPOS E CONTROLES DO SISCONDJ
    // ─────────────────────────────────────────────────────────────────

    function _setValor(seletorOuEl, valor) {
        const el = typeof seletorOuEl === 'string' ? document.querySelector(seletorOuEl) : seletorOuEl;
        if (!el || valor === undefined || valor === null) return false;
        el.value = valor;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    function _setChosen(seletorOuEl, valor) {
        const el = typeof seletorOuEl === 'string' ? document.querySelector(seletorOuEl) : seletorOuEl;
        if (!el || valor === undefined || valor === null) return false;
        el.value = valor;
        el.dispatchEvent(new Event('change', { bubbles: true }));
        if (window.$) {
            try {
                window.$(el).trigger('chosen:updated').trigger('change');
            } catch (e) {}
        }
        return true;
    }

    function _marcarRadio(seletor) {
        const radio = document.querySelector(seletor);
        if (!radio) return false;
        radio.checked = true;
        radio.dispatchEvent(new Event('click', { bubbles: true }));
        radio.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    function _marcarCheck(seletor, checked = true) {
        const chk = document.querySelector(seletor);
        if (!chk) return false;
        if (chk.checked !== checked) {
            chk.click();
        }
        return true;
    }

    function _selecionarOpcaoPorTexto(seletor, regexOuTexto) {
        const select = document.querySelector(seletor);
        if (!select) return null;
        const re = typeof regexOuTexto === 'string' ? new RegExp(regexOuTexto, 'i') : regexOuTexto;
        for (const opt of Array.from(select.options)) {
            if (re.test(opt.text) || re.test(opt.value)) {
                _setChosen(select, opt.value);
                return opt;
            }
        }
        return null;
    }

    function _selecionarTipoFinalidade(tipoFinalidade) {
        _setChosen('#cb_tipoFinalidade', tipoFinalidade);
        if (typeof window.abrirLinhasFinalidades === 'function') {
            try { window.abrirLinhasFinalidades(); } catch (e) {}
        }
    }

    async function _configurarBeneficiario(tipoBeneficiario, nomeOuDoc, isPerito = false) {
        _setChosen('#cb_tipoBeneficiario', tipoBeneficiario);
        if (typeof window.cbTipoBeneficiarioChange === 'function') {
            try { window.cbTipoBeneficiarioChange(); } catch (e) {}
        }
        await _sleep(350);

        if (isPerito) {
            // No alvará para perito, colocamos apenas o CPF e o sistema puxa o nome sozinho
            const docLimpo = String(nomeOuDoc || '').replace(/\D/g, '');
            if (docLimpo) {
                _setValor('#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj', docLimpo);
                if (typeof window.validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj === 'function') {
                    try { window.validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj(); } catch (e) {}
                } else {
                    const btnVal = document.getElementById('solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button');
                    if (btnVal) btnVal.click();
                }
            }
        } else if (nomeOuDoc) {
            const docLimpo = String(nomeOuDoc).replace(/\D/g, '');
            const selBeneficiario = document.getElementById('comboBeneficiario');
            if (selBeneficiario) {
                let optEncontrada = null;
                for (const opt of Array.from(selBeneficiario.options)) {
                    if (opt.value === '0') continue;
                    if (docLimpo && opt.value.replace(/\D/g, '').includes(docLimpo)) {
                        optEncontrada = opt;
                        break;
                    }
                    if (opt.text.toLowerCase().includes(String(nomeOuDoc).toLowerCase())) {
                        optEncontrada = opt;
                        break;
                    }
                }
                if (optEncontrada) {
                    _setChosen(selBeneficiario, optEncontrada.value);
                    if (typeof window.verificarBeneficiarioSelecionado === 'function') {
                        try { window.verificarBeneficiarioSelecionado(); } catch (e) {}
                    }
                    if (typeof window.setarHiddens === 'function') {
                        try { window.setarHiddens(optEncontrada.value); } catch (e) {}
                    }
                }
            }
        }
    }

    function _configurarTitularConta(item) {
        const ehCj = item.dados?.contaJuridica || Boolean(item.dados?.cnpj);
        if (ehCj) {
            // Conta Jurídica: seleciona Não e marca Representante Legal com CNPJ
            _marcarRadio('#rb_beneficiarioTitularContaFalse');
            _marcarCheck('#rb_representanteLegal', true);
            const cnpjLimpo = String(item.dados?.cnpj || item.destinatarioDocumento || '').replace(/\D/g, '');
            if (cnpjLimpo) {
                _setValor('#solicitacaoTransiente_representanteLegal_cpfCnpj', cnpjLimpo);
                if (typeof window.validaCpfCnpj_solicitacaoTransiente_representanteLegal_cpfCnpj === 'function') {
                    try { window.validaCpfCnpj_solicitacaoTransiente_representanteLegal_cpfCnpj(); } catch (e) {}
                }
            }
        } else {
            // Pessoa Física titular
            _marcarRadio('#rb_beneficiarioTitularContaTrue');
        }
    }

    function _configurarContaBancaria(item, finalidade) {
        const bancoStr = item.dados?.banco || item.banco || '';
        const ag = item.dados?.agencia || '';
        const cc = item.dados?.conta || '';
        const tipo = item.dados?.tipoConta || '';
        const ehPoupanca = /poup/i.test(tipo);

        if (finalidade === 'CREDITO_CONTA_BB') {
            _setValor('[name="finalidadeCreditoEmContaBB.contaBancaria.agencia"]', ag);
            _setValor('[name="finalidadeCreditoEmContaBB.contaBancaria.conta"]', cc);
            _setChosen('#cb_tipoCredito', ehPoupanca ? 'POUPANCA' : 'CONTA_CORRENTE');
        } else if (finalidade === 'CREDITO_CONTA_OUTRO_BANCO') {
            const codBanco = (item.dados?.codigoBanco || bancoStr.match(/\b\d{3}\b/)?.[0] || '').trim();
            const nomeBanco = bancoStr.replace(/^\d+[\s—-]+/, '').trim();

            if (codBanco) {
                _selecionarOpcaoPorTexto('#cmb_banco', new RegExp('^' + codBanco + '\\b', 'i'));
            } else if (nomeBanco) {
                _selecionarOpcaoPorTexto('#cmb_banco', new RegExp(nomeBanco, 'i'));
            }

            _setValor('[name="finalidadeCreditoOutrosBancos.contaBancaria.agencia"]', ag);
            _setValor('[name="finalidadeCreditoOutrosBancos.contaBancaria.conta"]', cc);
            _setChosen('#cb_tipoCreditoOutrosBancos', ehPoupanca ? 'POUPANCA' : 'CONTA_CORRENTE');
        }
    }

    function _configurarDarf(item) {
        // Código 1889
        _setValor('[name="finalidadeDARF.codigo.id"]', item.codigoReceita || '1889');

        // Nº de referência = CPF do autor
        const cpfRef = String(item.destinatarioDocumento || '').replace(/\D/g, '');
        if (cpfRef) _setValor('[name="finalidadeDARF.numeroReferencia"]', cpfRef);

        // Data de apuração = data do depósito (ou data atual)
        if (item.dataApuracao) {
            _setValor('[name="finalidadeDARF.periodoApuracao"]', item.dataApuracao);
        }

        // Data de vencimento = último dia do mês corrente
        const agora = new Date();
        const ultimoDia = new Date(agora.getFullYear(), agora.getMonth() + 1, 0);
        const diaFmt = String(ultimoDia.getDate()).padStart(2, '0') + '/' +
                       String(ultimoDia.getMonth() + 1).padStart(2, '0') + '/' +
                       ultimoDia.getFullYear();
        _setValor('[name="finalidadeDARF.dataVencimento"]', diaFmt);

        // Valor principal
        const valLimpo = String(item.valor || '').replace(/[^\d,\.]/g, '').trim();
        if (valLimpo) _setValor('[name="finalidadeDARF.valorPrincipal"]', valLimpo);
    }

    function _configurarValorEResgate(item) {
        _setChosen('#cb_tipoResgate', 'RESGATE_PARCIAL');

        const valLimpo = String(item.valor || '').replace(/[^\d,\.]/g, '').trim();
        if (valLimpo) {
            _setValor('#valor_real', valLimpo);
            _setValor('[name="solicitacaoTransiente.valorReal"]', valLimpo);
        }

        // Sempre selecionar "com correção"
        _marcarRadio('#rb_comCorrecao');
    }

    // ─────────────────────────────────────────────────────────────────
    // ROTINAS DE PREENCHIMENTO POR TIPO DE VERBA (AV.MD)
    // ─────────────────────────────────────────────────────────────────

    async function preencherCreditoExequente(item) {
        _status('Preenchendo Crédito do Exequente...');
        const bancoStr = item.dados?.banco || item.banco || '';
        const ehBB = /Banco do Brasil|^001\b/i.test(bancoStr);
        const finalidade = ehBB ? 'CREDITO_CONTA_BB' : 'CREDITO_CONTA_OUTRO_BANCO';

        _selecionarTipoFinalidade(finalidade);
        await _sleep(300);

        // Autor ('1')
        await _configurarBeneficiario('1', item.destinatarioDocumento || item.destinatarioNome);
        await _sleep(300);

        _configurarTitularConta(item);
        _configurarContaBancaria(item, finalidade);
        _configurarValorEResgate(item);
        _status('Crédito do Exequente preenchido!', 'ok');
    }

    async function preencherHonorariosAutor(item) {
        _status('Preenchendo Honorários Advocatícios...');
        const bancoStr = item.dados?.banco || item.banco || '';
        const ehBB = /Banco do Brasil|^001\b/i.test(bancoStr);
        const finalidade = ehBB ? 'CREDITO_CONTA_BB' : 'CREDITO_CONTA_OUTRO_BANCO';

        _selecionarTipoFinalidade(finalidade);
        await _sleep(300);

        // Advogado do Autor ('9')
        await _configurarBeneficiario('9', item.destinatarioNome || item.dados?.advogadoNome);
        await _sleep(300);

        _configurarTitularConta(item);
        _configurarContaBancaria(item, finalidade);
        _configurarValorEResgate(item);
        _status('Honorários Advocatícios preenchidos!', 'ok');
    }

    async function preencherHonorariosReclamada(item) {
        _status('Preenchendo Honorários Advocatícios (Ré)...');
        const bancoStr = item.dados?.banco || item.banco || '';
        const ehBB = /Banco do Brasil|^001\b/i.test(bancoStr);
        const finalidade = ehBB ? 'CREDITO_CONTA_BB' : 'CREDITO_CONTA_OUTRO_BANCO';

        _selecionarTipoFinalidade(finalidade);
        await _sleep(300);

        // Advogado do Réu ('10')
        await _configurarBeneficiario('10', item.destinatarioNome || item.dados?.advogadoNome);
        await _sleep(300);

        _configurarTitularConta(item);
        _configurarContaBancaria(item, finalidade);
        _configurarValorEResgate(item);
        _status('Honorários da Ré preenchidos!', 'ok');
    }

    async function preencherHonorariosPericiais(item) {
        _status(`Preenchendo Honorários Periciais (${item.perito || ''})...`);
        const bancoStr = item.dados?.banco || item.banco || '';
        const ehBB = /Banco do Brasil|^001\b/i.test(bancoStr);
        const finalidade = ehBB ? 'CREDITO_CONTA_BB' : 'CREDITO_CONTA_OUTRO_BANCO';

        _selecionarTipoFinalidade(finalidade);
        await _sleep(300);

        // Perito é Terceiro ('11')
        await _configurarBeneficiario('11', item.destinatarioDocumento, true);
        await _sleep(300);

        _configurarTitularConta(item);
        _configurarContaBancaria(item, finalidade);
        _configurarValorEResgate(item);
        _status('Honorários Periciais preenchidos!', 'ok');
    }

    async function preencherCustas(item) {
        _status('Preenchendo Custas (GRU)...');
        _selecionarTipoFinalidade('GRU');
        await _sleep(300);

        // Beneficiária é sempre a reclamada ('5')
        await _configurarBeneficiario('5', item.destinatarioNome);
        await _sleep(300);

        _configurarValorEResgate(item);
        _status('Custas (GRU) preenchidas!', 'ok');
    }

    async function preencherInss(item) {
        _status('Preenchendo INSS (DARF / GPS)...');
        _selecionarTipoFinalidade('DARF');
        await _sleep(300);

        // Contribuinte é o autor ('1')
        await _configurarBeneficiario('1', item.destinatarioDocumento || item.destinatarioNome);
        await _sleep(300);

        _configurarDarf(item);
        _configurarValorEResgate(item);
        _status('INSS preenchido!', 'ok');
    }

    async function preencherImpostoRenda(item) {
        _status('Preenchendo Imposto de Renda (DARF 1889)...');
        _selecionarTipoFinalidade('DARF');
        await _sleep(300);

        // Contribuinte é o autor ('1')
        await _configurarBeneficiario('1', item.destinatarioDocumento || item.destinatarioNome);
        await _sleep(300);

        _configurarDarf(item);
        _configurarValorEResgate(item);
        _status('Imposto de Renda (DARF 1889) preenchido!', 'ok');
    }

    async function preencherDevolucaoReclamada(item) {
        _status('Preenchendo Devolução à Reclamada...');
        const bancoStr = item.dados?.banco || item.banco || '';
        const ehBB = /Banco do Brasil|^001\b/i.test(bancoStr);
        const finalidade = ehBB ? 'CREDITO_CONTA_BB' : 'CREDITO_CONTA_OUTRO_BANCO';

        _selecionarTipoFinalidade(finalidade);
        await _sleep(300);

        // Réu ('5')
        await _configurarBeneficiario('5', item.destinatarioDocumento || item.destinatarioNome);
        await _sleep(300);

        _configurarTitularConta(item);
        _configurarContaBancaria(item, finalidade);
        _configurarValorEResgate(item);
        _status('Devolução à Reclamada preenchida!', 'ok');
    }

    async function preencherFgts(item) {
        _status('FGTS: em regra expedido via ofício CEF.');
        alert('FGTS: O pagamento é expedido via ofício bancário à CEF. Utilize o botão "Gerar Ofício".');
    }

    async function preencherVerbaGenerica(tipo, item) {
        _status(`Preenchendo ${tipo}...`);
        const bancoStr = item.dados?.banco || item.banco || '';
        const ehBB = /Banco do Brasil|^001\b/i.test(bancoStr);
        const finalidade = ehBB ? 'CREDITO_CONTA_BB' : 'CREDITO_CONTA_OUTRO_BANCO';

        _selecionarTipoFinalidade(finalidade);
        await _sleep(300);

        await _configurarBeneficiario('1', item.destinatarioDocumento || item.destinatarioNome);
        await _sleep(300);

        _configurarTitularConta(item);
        _configurarContaBancaria(item, finalidade);
        _configurarValorEResgate(item);
        _status(`${tipo} preenchido!`, 'ok');
    }

    async function executarPreenchimento(tipo, dados) {
        switch (tipo) {
            case 'Crédito do exequente':
                await preencherCreditoExequente(dados);
                break;
            case 'FGTS':
                await preencherFgts(dados);
                break;
            case 'Contribuições previdenciárias — INSS':
            case 'INSS':
                await preencherInss(dados);
                break;
            case 'Custas':
                await preencherCustas(dados);
                break;
            case 'Imposto de Renda':
            case 'IRPF':
            case 'DARF':
                await preencherImpostoRenda(dados);
                break;
            case 'Honorários advocatícios (autor)':
            case 'Honorários advocatícios':
                await preencherHonorariosAutor(dados);
                break;
            case 'Honorários advocatícios (reclamada)':
                await preencherHonorariosReclamada(dados);
                break;
            case 'Honorários periciais':
                await preencherHonorariosPericiais(dados);
                break;
            case 'Devolução à reclamada':
                await preencherDevolucaoReclamada(dados);
                break;
            default:
                await preencherVerbaGenerica(tipo, dados);
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // AUTOMAÇÃO DE BUSCA DE CONTAS E SELEÇÃO DE PARCELAS
    // ─────────────────────────────────────────────────────────────────
    let _consultaIniciada = false;
    let _mandatoClicado = false;
    let _parcelaExpandida = false;
    let _parcelaSelecionada = false;

    function executarFluxoConsultaContas() {
        if (_mandatoClicado) return;

        const inputProc = document.getElementById('numeroProcesso');
        const btnBuscar = document.getElementById('bt_buscar');
        const tabelaContas = document.getElementById('table_contas');
        const btnEmitirMandato = document.getElementById('bt_emitir_mandato');

        // Se a tabela de contas já foi carregada e tem valor disponível:
        if (tabelaContas) {
            const contas = Alv.siscondj?.lerContasJudiciais ? Alv.siscondj.lerContasJudiciais() : [];
            const contasComSaldo = contas.filter(c => c.saldoValor > 0 && !c.carregando);

            if (contasComSaldo.length > 0) {
                const alvo = contasComSaldo[0];
                _status(`Contas localizadas! Valor disponível: ${alvo.saldoTexto}. Emitindo mandado...`, 'ok');

                if (btnEmitirMandato && !_mandatoClicado) {
                    _mandatoClicado = true;
                    setTimeout(() => {
                        console.log('[PjeAlvara][preenchimento] Clicando em bt_emitir_mandato...');
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

                _status(`Processo ${numProc} preenchido. Clicando em buscar...`);

                if (btnBuscar) {
                    _consultaIniciada = true;
                    setTimeout(() => {
                        console.log('[PjeAlvara][preenchimento] Clicando em bt_buscar...');
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

    function executarFluxoNovoMandado() {
        if (_parcelaSelecionada) return;

        const tabelaContas = document.getElementById('table_contas') || document.querySelector('table.relatorio');
        if (!tabelaContas) return;

        const contas = Alv.siscondj?.lerContasJudiciais ? Alv.siscondj.lerContasJudiciais() : [];
        if (contas.length === 0) return;

        const contasComSaldo = contas.filter(c => c.saldoValor > 0 && !c.carregando);
        if (contasComSaldo.length === 0) {
            _status('Aguardando povoamento do valor disponível nas contas judiciais...');
            return;
        }

        const contaComSaldo = contasComSaldo[0];
        const contaId = contaComSaldo.id;

        // 2. Clica no ícone de soma para expandir parcelas
        const subTabela = contaId ? document.getElementById('contaId_' + contaId) : document.querySelector('tr.subtabela');
        const estaExpandida = subTabela && subTabela.style.display !== 'none';

        if (!estaExpandida && !_parcelaExpandida) {
            const btnSoma = contaComSaldo.linhaEl.querySelector('img[onclick*="abrirParcelasEvent"], img[src*="soma-ico"], img#ico-img, img[alt="Parcelas"]');
            if (btnSoma) {
                _status(`Expandindo parcelas da conta judicial ${contaId}...`);
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

        // 3. Na tabela expandida, seleciona a parcela com saldo disponível
        if (subTabela) {
            const parcelas = Alv.siscondj?.lerParcelasConta ? Alv.siscondj.lerParcelasConta(contaId) : [];
            const aindaCarregando = subTabela.querySelector('img.rotate, img[src*="refresh"]');
            if (aindaCarregando) {
                _status('Aguardando atualização dos saldos das parcelas...');
                return;
            }

            const parcelaAlvo = parcelas.find(p => p.saldoValor > 0);

            if (parcelaAlvo && !_parcelaSelecionada) {
                const chk = parcelaAlvo.checkboxEl;
                if (chk) {
                    _parcelaSelecionada = true;
                    _status(`Parcela com saldo encontrada (${parcelaAlvo.saldoTexto})! Selecionando...`, 'ok');
                    setTimeout(() => {
                        if (!chk.checked) {
                            chk.click();
                        }
                        console.log('[PjeAlvara][preenchimento] Checkbox da parcela marcado com sucesso!');
                        _status(`Parcela selecionada (${parcelaAlvo.saldoTexto})! Pronto para emissão de alvará.`, 'ok');
                    }, 300);
                }
            } else if (!parcelaAlvo && parcelas.length > 0) {
                _status('Nenhuma parcela com saldo disponível positivo identificada.', 'warn');
            }
        }
    }

    function iniciarAutomacaoSiscondj() {
        const host = (window.location.hostname || '').toLowerCase();
        const href = (window.location.href || '').toLowerCase();
        const ehSiscon = ['siscondj', 'alvaraeletronico', 'portaltrtsp'].some(d => host.includes(d) || href.includes(d));
        if (!ehSiscon) return;

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

    Alv.preenchimentoSiscondj = {
        preencherCreditoExequente,
        preencherHonorariosAutor,
        preencherHonorariosReclamada,
        preencherHonorariosPericiais,
        preencherCustas,
        preencherInss,
        preencherImpostoRenda,
        preencherDevolucaoReclamada,
        preencherFgts,
        preencherVerbaGenerica,
        executarPreenchimento,
        executarFluxoConsultaContas,
        executarFluxoNovoMandado,
        iniciarAutomacaoSiscondj
    };

    // Atalhos para compatibilidade com fachada Alv.siscondj
    Alv.siscondj = Alv.siscondj || {};
    Alv.siscondj.executarPreenchimento = executarPreenchimento;
    Alv.siscondj.executarFluxoConsultaContas = executarFluxoConsultaContas;
    Alv.siscondj.executarFluxoNovoMandado = executarFluxoNovoMandado;
    Alv.siscondj.iniciarAutomacaoSiscondj = iniciarAutomacaoSiscondj;
})();
