'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — Módulo Minuta (Ordem 2, Teimosinha, Endereço)
// Baseado em SISB/processamento/minutas_campos.py + minutas_reus.py
// Requer: core.js (SisbCore), detalhes.js (SisbDetalhes)
// ═══════════════════════════════════════════════════════════════════

(function() {
    if (window.location.href.indexOf('sisbajud.cnj.jus.br') === -1 && window.location.href.indexOf('sisbajud.pdpj.jus.br') === -1) return;

    const C = window.SisbCore;

    // ── Lógica Ordem 2 ───────────────────────────────────────────────
    function calcularProximoDiaUtilProtocolo() {
        var agora = new Date();
        var diaSemana = agora.getDay(); // 0 = Dom, 1 = Seg, 2 = Ter, 3 = Qua, 4 = Qui, 5 = Sex, 6 = Sáb
        var hora = agora.getHours();

        var proximaData = new Date(agora);

        if (diaSemana >= 1 && diaSemana <= 4) { // Seg a Qui
            if (hora < 19) {
                // ANTES das 19h: Próximo dia útil
                proximaData.setDate(agora.getDate() + 1);
            } else {
                // APÓS as 19h: 2 dias úteis
                if (diaSemana === 4) proximaData.setDate(agora.getDate() + 4);
                else proximaData.setDate(agora.getDate() + 2);
            }
        } else if (diaSemana === 5) { // Sexta
            if (hora < 19) {
                proximaData.setDate(agora.getDate() + 3);
            } else {
                proximaData.setDate(agora.getDate() + 4);
            }
        } else if (diaSemana === 6) { // Sábado -> Terça (+3 dias)
            proximaData.setDate(agora.getDate() + 3);
        } else if (diaSemana === 0) { // Domingo -> Terça (+2 dias)
            proximaData.setDate(agora.getDate() + 2);
        }

        var d = String(proximaData.getDate()).padStart(2, '0');
        var m = String(proximaData.getMonth() + 1).padStart(2, '0');
        var a = proximaData.getFullYear();
        return d + '/' + m + '/' + a;
    }

    function injetarBotaoOrdem2() {
        var isDetalhes = window.location.href.includes('/detalhe');
        if (!isDetalhes) return;

        if (document.getElementById('btn-sisb-ordem2')) return;

        var container = document.getElementById('pjetools-sisb-ordem2-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'pjetools-sisb-ordem2-container';
            container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;display:flex;flex-direction:column;gap:8px;';
            document.body.appendChild(container);
        }

        var btnOrdem2 = C.criarBotao('btn-sisb-ordem2', 'Ordem 2 (+1)', '#8e44ad', function() {
            console.log('Iniciando extração SISBAJUD (Ordem 2)...');
            try {
                const D = window.SisbDetalhes || {};
                const numeroProcesso = (D.extrairNumeroProcesso && D.extrairNumeroProcesso()) || (D.getValueByLabel && D.getValueByLabel('Número do Processo:'));
                const numeroProtocolo = (D.extrairNumeroProtocolo && D.extrairNumeroProtocolo()) || (D.getValueByLabel && D.getValueByLabel('Número do Protocolo:'));
                const repeticaoProgramada = D.getValueByLabel ? D.getValueByLabel('Repetição programada?') : '';
                const limiteRepeticao = D.getValueByLabel ? D.getValueByLabel('Data limite da repetição:') : '';
                const valorBloqueio = D.getCleanText ? D.getCleanText('td[data-label="valorBloquear:"]') : '';
                const executados = [];
                const partesPassivasObj = [];

                const rowsExecutados = document.querySelectorAll('tr.element-row');
                rowsExecutados.forEach(row => {
                    const nomeElement = row.querySelector('.col-reu-dados-nome-pessoa');
                    const documentoElement = row.querySelector('.col-reu-dados a');
                    if (nomeElement && documentoElement) {
                        const nome = nomeElement.textContent.trim();
                        const documento = documentoElement.textContent.trim();
                        executados.push(`${nome} - [${documento}]`);
                        partesPassivasObj.push({ nome: nome, cpfcnpj: documento.replace(/[^0-9]/g, '') });
                    }
                });

                const pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';
                let resultado = `<p ${pStyle}><strong>Dados da Teimosinha protocolada (Ordem 2):</strong></p>`;
                resultado += `<p ${pStyle}>Número do processo: <strong>${numeroProcesso || 'Não encontrado'}</strong></p>`;
                resultado += `<p ${pStyle}>Número do protocolo: <strong>${numeroProtocolo || 'Não encontrado'}</strong></p>`;
                resultado += `<p ${pStyle}>Repetição programada? <strong>${repeticaoProgramada || 'Não encontrado'}</strong></p>`;
                resultado += `<p ${pStyle}>Limite da repetição: <strong>${limiteRepeticao || 'Não encontrado'}</strong></p>`;
                resultado += `<p ${pStyle}>Valor do bloqueio: <strong>${valorBloqueio ? valorBloqueio.split('\n')[0] : 'Não encontrado'}</strong></p>`;
                resultado += `<p ${pStyle}><strong>Partes alvo do bloqueio:</strong></p>`;

                if (executados.length > 0) {
                    executados.forEach(executado => { resultado += `<p ${pStyle}><strong>${executado}</strong></p>`; });
                } else {
                    resultado += `<p ${pStyle}><strong>Nenhum executado encontrado</strong></p>`;
                }

                resultado += `<p ${pStyle}>Notas:</p>`;
                resultado += `<p ${pStyle}>-Por padrão é consultado CNPJ raiz.</p>`;
                resultado += `<p ${pStyle}>-Eventuais partes faltantes se referem a CPF ou CNPJ sem relacionamento bancário.</p>`;

                // Salva no state de detalhar para a 2ª ordem poder consolidar os 2 protocolos
                const procNorm = (numeroProcesso || '').replace(/\D/g, '');
                const st = {
                    processo: numeroProcesso,
                    processoNorm: procNorm,
                    protocolo1: numeroProtocolo,
                    primeiroTextoHtml: resultado,
                    repeticaoProgramada: repeticaoProgramada,
                    limiteRepeticao: limiteRepeticao,
                    valorBloqueio: valorBloqueio,
                    executados: executados,
                    timestamp: Date.now()
                };
                if (D.obterMapaDetalhar && D.salvarMapaDetalhar) {
                    const mapa = D.obterMapaDetalhar();
                    mapa[procNorm] = st;
                    D.salvarMapaDetalhar(mapa);
                }
                window._sisbUltimoProtocoloProcessado = numeroProtocolo;

                C.mostrarToast('1ª ordem guardada (' + numeroProtocolo + '). Aguardando 2ª ordem...', 'aviso');

                let diasRepeticao = 30;
                if (repeticaoProgramada && repeticaoProgramada.includes('60')) diasRepeticao = 60;

                let vlrNum = 0;
                if (valorBloqueio) {
                    let vb = valorBloqueio.split('\n')[0].replace('R$', '').trim().replace(/\./g, '').replace(',', '.');
                    vlrNum = parseFloat(vb);
                }

                let dataProtocolo = calcularProximoDiaUtilProtocolo();

                let dadosOrdem2 = {
                    numero: numeroProcesso ? numeroProcesso.replace(/[^0-9.-]/g, '') : '',
                    partesPassivas: partesPassivasObj,
                    valorExecucao: vlrNum,
                    diasTeimosinha: diasRepeticao,
                    dataProtocolo: dataProtocolo,
                    partesAtivas: []
                };

                C.salvarEstado('sisbajud_dados_basicos', dadosOrdem2);
                C.salvarEstado('sisbajud_acao', 'ordem2');

                let baseUrl = window.location.href.includes('cnj.jus.br') ? 'https://sisbajud.cnj.jus.br' : 'https://sisbajud.pdpj.jus.br';
                let url = baseUrl + '/minuta/cadastrar';
                setTimeout(() => {
                    if (typeof GM_openInTab !== 'undefined') {
                        GM_openInTab(url, { active: true });
                    } else {
                        window.open(url, '_blank');
                    }
                }, 500);
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro na extração. Verifique o console.');
            }
        });

        container.appendChild(btnOrdem2);
    }

    function injetarBotoesMinuta(dados) {
        var container = document.getElementById('pje-botoes-minuta-container');
        if (container) {
            container.style.display = 'flex';
            return;
        }
        container = document.createElement('div');
        container.id = 'pje-botoes-minuta-container';
        container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;display:flex;flex-direction:column;gap:8px;';

        let btnEnd = C.criarBotao('btn-minuta-endereco', '📍 Endereço', '#17a2b8', () => {
            if (window.PjeSisbajudAuto && typeof window.PjeSisbajudAuto.mostrarDialogoExecutados === 'function') {
                window.PjeSisbajudAuto.mostrarDialogoExecutados(dados.partesPassivas || [], (partesFiltradas) => {
                    dados.partesPassivas = partesFiltradas;
                    C.salvarEstado('sisbajud_dados_basicos', dados);
                    container.style.display = 'none';
                    preencherFormularioMinuta('endereco', dados);
                });
            } else {
                container.style.display = 'none';
                preencherFormularioMinuta('endereco', dados);
            }
        });

        let btnTeim = C.criarBotao('btn-minuta-teimosinha', '⚡ Teimosinha', '#28a745', () => {
            container.style.display = 'none';
            preencherFormularioMinuta('teimosinha', dados);
        });

        container.appendChild(btnEnd);
        container.appendChild(btnTeim);
        document.body.appendChild(container);
    }

    async function selecionarDataNoCalendario(ancoraInput, offsetDias) {
        try {
            if (!ancoraInput) return false;
            let pai = ancoraInput.closest('mat-form-field') || ancoraInput.parentElement.parentElement;
            let btnCal = pai ? pai.querySelector('button[aria-label="Open calendar"]') : null;
            if (!btnCal) btnCal = document.querySelector('button[aria-label="Open calendar"]');
            if (!btnCal) return false;

            btnCal.click();
            await C.sleep(800);

            let btnMesAno = await C.wait('mat-calendar button[aria-label="Choose month and year"]', 3000);
            if (!btnMesAno) return false;
            btnMesAno.click();
            await C.sleep(800);

            let hoje = new Date();
            let dataAlvo = new Date(hoje);
            dataAlvo.setDate(hoje.getDate() + offsetDias);

            let anoStr = String(dataAlvo.getFullYear());
            let anoCell = await C.wait('mat-calendar td[aria-label="' + anoStr + '"]', 3000);
            if (anoCell) {
                anoCell.click();
                await C.sleep(800);
            }

            let meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
            let mesAlvo = dataAlvo.getMonth();
            let diaAlvo = dataAlvo.getDate();

            while (mesAlvo >= 0) {
                let mesStr = meses[mesAlvo] + ' de ' + anoStr;
                let elMes = document.querySelector('mat-calendar td[aria-label="' + mesStr + '"]');
                if (elMes && !elMes.hasAttribute('aria-disabled')) {
                    elMes.click();
                    break;
                }
                mesAlvo--;
                diaAlvo = 31;
            }
            await C.sleep(800);

            let mesFinalStr = meses[mesAlvo] + ' de ' + anoStr;
            while (diaAlvo > 0) {
                let diaStr = diaAlvo + ' de ' + mesFinalStr;
                let elDia = document.querySelector('mat-calendar td[aria-label="' + diaStr + '"]');
                if (elDia && !elDia.hasAttribute('aria-disabled')) {
                    elDia.click();
                    return true;
                }
                diaAlvo--;
            }
        } catch (e) {
            console.warn('[SisbMinuta] Erro ao selecionar data no calendário:', e);
        }
        return false;
    }

    async function preencherFormularioMinuta(acao, dados) {
        dados = dados || {};
        var nomeAcao = acao === 'endereco' ? 'Endereço' : (acao === 'ordem2' ? 'Ordem 2' : 'Teimosinha');
        console.log('[SisbMinuta] Preenchendo formulário para:', acao, dados);
        C.mostrarToast('Preenchendo ' + nomeAcao + '...', 'aviso');

        var elProc = await C.wait('input[placeholder*="Processo"], input[formcontrolname*="processo"], input[formcontrolname*="Processo"], input#numeroProcesso', 10000);
        if (!elProc) {
            console.warn('[SisbMinuta] Campo Número do Processo não encontrado');
            C.mostrarToast('Erro: campo de processo não encontrado', 'erro');
            return;
        }
        await C.sleep(500);

        // 1. Juiz (padrão 'Otavio Augusto')
        var juizNome = dados.juiz || 'Otavio Augusto';
        console.log('[SisbMinuta] 1. Preenchendo Juiz:', juizNome);
        var elJuiz = await C.wait('input[placeholder*="Juiz"]', 4000);
        if (elJuiz) {
            C.preencherInput(elJuiz, juizNome);
            await C.sleep(600);
            var optJuiz = await C.wait(() => {
                var opcoes = Array.from(document.querySelectorAll('mat-option[role="option"]'));
                return opcoes.find(e => (e.textContent || '').toLowerCase().includes(juizNome.toLowerCase().split(' ')[0]));
            }, 3000);
            if (optJuiz) {
                await C.click(optJuiz, 2000);
            }
            await C.sleep(600);
        }

        // 2. Vara (padrão '30006')
        var varaCod = dados.vara || '30006';
        console.log('[SisbMinuta] 2. Preenchendo Vara:', varaCod);
        var selectVara = await C.wait('mat-select[name*="varaJuizoSelect"], mat-select[aria-label*="Selecione a Vara"]', 3000);
        if (selectVara) {
            await C.click(selectVara, 2000);
            await C.sleep(800);

            var campoPesquisaVara = await C.wait('.mat-select-panel input[placeholder*="Pesquisar Vara"]', 3000);
            if (campoPesquisaVara) {
                await C.sleep(1000);
                campoPesquisaVara.focus();
                campoPesquisaVara.value = '';
                for (const charVara of String(varaCod).split('')) {
                    campoPesquisaVara.dispatchEvent(new KeyboardEvent('keydown', { key: charVara, bubbles: true, cancelable: true }));
                    campoPesquisaVara.dispatchEvent(new KeyboardEvent('keypress', { key: charVara, bubbles: true, cancelable: true }));
                    campoPesquisaVara.value += charVara;
                    campoPesquisaVara.dispatchEvent(new Event('input', { bubbles: true }));
                    campoPesquisaVara.dispatchEvent(new Event('change', { bubbles: true }));
                    campoPesquisaVara.dispatchEvent(new KeyboardEvent('keyup', { key: charVara, bubbles: true, cancelable: true }));
                    await C.sleep(100);
                }
                await C.sleep(800);

                var optVara = await C.wait(() => {
                    var opcoes = Array.from(document.querySelectorAll('mat-option[role="option"]'));
                    return opcoes.find(e => {
                        var txt = (e.textContent || '').trim();
                        return txt.startsWith(varaCod) || txt.split(' - ')[0].trim() === varaCod;
                    });
                }, 3000);
                if (optVara) {
                    await C.click(optVara, 2000);
                }
                await C.sleep(600);
            }
        }

        // 3. Número do Processo
        var numProc = dados.numero || dados.processo || '';
        if (!numProc) {
            var dadosB = C.lerEstado('sisbajud_dados_basicos') || {};
            numProc = dadosB.numero || dadosB.processo || '';
        }

        if (elProc && numProc) {
            console.log('[SisbMinuta] 3. Preenchendo Processo:', numProc);
            var numLimpo = String(numProc).replace(/\D/g, '');
            elProc.focus();
            if (typeof elProc.click === 'function') elProc.click();
            await C.sleep(200);

            // 1ª tentativa: preencher diretamente
            C.preencherInput(elProc, numProc);
            await C.sleep(400);

            // 2ª tentativa se não pegou ou ficou curto (ex: máscara do Angular que requer digitação pura)
            var valAtual = (elProc.value || '').replace(/\D/g, '');
            if (valAtual.length < 15 && numLimpo.length >= 15) {
                console.log('[SisbMinuta] Digitando processo caractere por caractere...', numLimpo);
                elProc.value = '';
                elProc.focus();
                for (const ch of numLimpo.split('')) {
                    elProc.dispatchEvent(new KeyboardEvent('keydown', { key: ch, bubbles: true, cancelable: true }));
                    elProc.dispatchEvent(new KeyboardEvent('keypress', { key: ch, bubbles: true, cancelable: true }));
                    var okCmd = false;
                    try { okCmd = document.execCommand('insertText', false, ch); } catch(e) {}
                    if (!okCmd) elProc.value += ch;
                    elProc.dispatchEvent(new Event('input', { bubbles: true }));
                    elProc.dispatchEvent(new KeyboardEvent('keyup', { key: ch, bubbles: true, cancelable: true }));
                    await C.sleep(25);
                }
                elProc.dispatchEvent(new Event('change', { bubbles: true }));
                elProc.blur();
                await C.sleep(300);
            }
        } else {
            console.warn('[SisbMinuta] Número do processo não disponível nos dados:', dados);
        }

        // 4. Tipo de Ação
        console.log('[SisbMinuta] 4. Selecionando Tipo de Ação...');
        var selectAcao = await C.wait('mat-select[name*="acao"], mat-select[formcontrolname*="acao"]', 3000);
        if (selectAcao) {
            await C.click(selectAcao, 2000);
            await C.sleep(500);
            var optAcao = await C.wait(() => {
                var opcoes = Array.from(document.querySelectorAll('mat-option'));
                return opcoes.find(e => {
                    var txt = (e.textContent || '').trim();
                    return txt.includes('Ação Trabalhista') || txt.includes('Execução Trabalhista') ||
                           txt.includes('Acao Trabalhista') || txt.includes('Execucao Trabalhista');
                });
            }, 3000);
            if (optAcao) {
                await C.click(optAcao, 2000);
            }
            await C.sleep(500);
        }

        // 5. Autor / Reclamante
        if (dados.partesAtivas && dados.partesAtivas.length > 0) {
            var autor = dados.partesAtivas[0];
            var docLimpo = (autor.cpfcnpj || '').replace(/\D/g, '');
            console.log('[SisbMinuta] 5. Preenchendo Reclamante:', autor.nome, docLimpo);

            var elAutorDoc = document.querySelector('input[placeholder*="CPF/CNPJ do autor"]');
            if (!elAutorDoc) {
                var cpfs = document.querySelectorAll('input[placeholder*="CPF"]');
                if (cpfs.length > 0) elAutorDoc = cpfs[0];
            }
            if (elAutorDoc && docLimpo) {
                C.preencherInput(elAutorDoc, docLimpo);
                await C.sleep(300);
            }

            var elAutorNome = document.querySelector('input[placeholder*="Nome do autor"]') ||
                              document.querySelector('input[placeholder="Nome do autor/exequente da ação"]');
            if (elAutorNome && autor.nome) {
                C.preencherInput(elAutorNome, autor.nome);
                await C.sleep(300);
            }
        }

        // 6. Se for Requisição de Informações (Endereço)
        if (acao === 'endereco') {
            console.log('[SisbMinuta] 6. Endereço - Selecionando Requisição de Informações...');
            var btnReq = await C.wait(() => Array.from(document.querySelectorAll('mat-radio-button')).find(e => (e.textContent || '').includes('Requisição de informações')), 5000);
            if (btnReq) {
                await C.click(btnReq, 3000);
            } else {
                await C.click('mat-radio-button[value="REQUISICAO_INFORMACAO"]', 3000);
            }
            await C.sleep(800);
        }

        // 7. Se for Teimosinha / Ordem 2 (Bloqueio)
        if (acao === 'teimosinha' || acao === 'ordem2') {
            console.log('[SisbMinuta] 7. Preenchendo Valor da Execução:', dados.valorExecucao);
            var elValor = document.querySelector('input[placeholder*="Valor a bloquear"]') ||
                          document.querySelector('input[placeholder*="Valor aplicado a todos"]');
            if (elValor && dados.valorExecucao && Number(dados.valorExecucao) > 0) {
                var valorFormatado = Number(dados.valorExecucao).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                C.preencherInput(elValor, valorFormatado);
                await C.sleep(300);

                var btnAplicarValor = document.querySelector('span#maisPJe_valor_execucao') ||
                                      document.querySelector('sisbajud-cadastro-minuta mat-icon[class*="fa-check-square"]');
                if (btnAplicarValor) {
                    var btnTarget = btnAplicarValor.closest('button') || btnAplicarValor;
                    if (btnTarget) await C.click(btnTarget, 2000);
                }
            }

            console.log('[SisbMinuta] Marcando Teimosinha (Repetir a ordem)...');
            var checkRepetir = Array.from(document.querySelectorAll('mat-radio-button')).find(el => (el.textContent || '').includes('Repetir a ordem'));
            if (checkRepetir) {
                await C.click(checkRepetir, 3000);
                await C.sleep(600);
            }

            var diasRepeticao = dados.diasTeimosinha || 30;
            var elDias = document.querySelector('input[formcontrolname="qtdeDiasRepeticao"]');
            if (elDias) {
                C.preencherInput(elDias, diasRepeticao);
                await C.sleep(400);
            } else {
                var inputDataLimite = document.querySelector('input[placeholder="Data limite:"]');
                if (inputDataLimite) {
                    await selecionarDataNoCalendario(inputDataLimite, parseInt(diasRepeticao) + 2);
                    await C.sleep(600);
                }
            }

            var agora = new Date();
            var hora = agora.getHours();
            var diaSemana = agora.getDay();
            var precisaAgendar = (acao === 'ordem2' && !!dados.dataProtocolo);

            if (hora >= 19 || diaSemana === 0 || diaSemana === 6 || (diaSemana === 5 && hora >= 19)) {
                precisaAgendar = true;
            }

            if (precisaAgendar) {
                console.log('[SisbMinuta] Agendamento necessário detectado.');
                var dataAgendamento = dados.dataProtocolo;
                var offsetDias = 1;

                if (!dataAgendamento) {
                    var dataAlvo = new Date(agora);
                    if (diaSemana === 5 && hora >= 19) {
                        offsetDias = 3;
                    } else if (diaSemana === 6) {
                        offsetDias = 2;
                    } else if (diaSemana === 0) {
                        offsetDias = 1;
                    } else if (hora >= 19) {
                        offsetDias = 1;
                    }
                    dataAlvo.setDate(agora.getDate() + offsetDias);
                    var d = String(dataAlvo.getDate()).padStart(2, '0');
                    var m = String(dataAlvo.getMonth() + 1).padStart(2, '0');
                    var a = dataAlvo.getFullYear();
                    dataAgendamento = d + '/' + m + '/' + a;
                }

                console.log('[SisbMinuta] Agendando protocolo para:', dataAgendamento);

                var checkAgendar = document.querySelector('mat-checkbox[formcontrolname="agendarProtocolo"] input');
                if (checkAgendar && !checkAgendar.checked) {
                    checkAgendar.click();
                    await C.sleep(600);
                } else {
                    var todosRows = Array.from(document.querySelectorAll('div.row, sisbajud-cadastro-minuta .row'));
                    for (var rw of todosRows) {
                        if ((rw.textContent || '').includes('Agendar protocolo')) {
                            var rads = rw.parentElement.querySelectorAll('mat-radio-button');
                            for (var r of rads) {
                                if ((r.innerText || '').includes('Sim')) {
                                    var lbl = r.querySelector('label') || r;
                                    lbl.click();
                                    await C.sleep(600);
                                    break;
                                }
                            }
                            break;
                        }
                    }
                }

                var elDataAgend = document.querySelector('input[placeholder="Data do protocolo:"]') ||
                                  document.querySelector('input[placeholder="DD/MM/AAAA"]');
                if (elDataAgend) {
                    C.preencherInput(elDataAgend, dataAgendamento);
                    await C.sleep(500);
                    if (!elDataAgend.value || elDataAgend.value !== dataAgendamento) {
                        await selecionarDataNoCalendario(elDataAgend, offsetDias);
                    }
                }
            }
        }

        // 8. Réus / Executadas (Iterativo + Remoção de 0 contas / Recuperação Judicial)
        if (dados.partesPassivas && dados.partesPassivas.length > 0) {
            console.log('[SisbMinuta] 8. Adicionando ' + dados.partesPassivas.length + ' executadas...');
            for (var p of dados.partesPassivas) {
                var docReu = (p.cpfcnpj || '').replace(/\D/g, '');
                if (docReu.length === 14) {
                    docReu = docReu.slice(0, 8);
                }
                if (!docReu) continue;

                var elReuDoc = document.querySelector('input[placeholder*="CPF/CNPJ do réu"]') ||
                               document.querySelector('input[placeholder*="Adicionar Réu/Executado CPF/CNPJ"]') ||
                               document.querySelector('input.mat-input-element[cpfcnpjmask]');
                if (!elReuDoc) {
                    var todosCpfs = document.querySelectorAll('input[placeholder*="CPF"]');
                    if (todosCpfs.length > 1) elReuDoc = todosCpfs[todosCpfs.length - 1];
                    else if (todosCpfs.length === 1) elReuDoc = todosCpfs[0];
                }

                if (elReuDoc) {
                    console.log('[SisbMinuta] Digitando executada:', p.nome, docReu);
                    C.preencherInput(elReuDoc, docReu);
                    await C.sleep(400);

                    var btnAdd = document.querySelector('button.btn-adicionar.mat-mini-fab') ||
                                 document.querySelector('button mat-icon.fa-plus-square') ||
                                 document.querySelector('button[mattooltip="Adicionar Réu/Executado"]');
                    if (btnAdd) {
                        var targetAdd = btnAdd.closest('button') || btnAdd;
                        targetAdd.click();
                        console.log('[SisbMinuta] Executada adicionada, aguardando validação Receita/Bacen...');
                        await C.sleep(2800);

                        if (acao === 'teimosinha' || acao === 'ordem2') {
                            var linhasTabela = document.querySelectorAll('tbody tr.mat-row, tbody tr');
                            if (linhasTabela.length > 0) {
                                var ultimaLinha = linhasTabela[linhasTabela.length - 1];
                                var celulaRelac = ultimaLinha.querySelector('td.mat-column-qtdeRelacionamentos');
                                var celulaIdent = ultimaLinha.querySelector('td.mat-column-identificacao');

                                var nomeNaTabela = celulaIdent ? celulaIdent.textContent.toUpperCase() : '';
                                var emRecuperacao = nomeNaTabela.includes('RECUPERAÇÃO JUDICIAL') ||
                                                    nomeNaTabela.includes('RECUPERACAO JUDICIAL') ||
                                                    nomeNaTabela.includes('RECUPERCAO JUDICIAL');

                                var qtde = '1';
                                if (celulaRelac) {
                                    var btnRelac = celulaRelac.querySelector('button .mat-button-wrapper') || celulaRelac;
                                    qtde = btnRelac ? btnRelac.textContent.trim() : '0';
                                }

                                if (qtde === '0' || emRecuperacao) {
                                    var motivo = emRecuperacao ? 'Recuperação Judicial' : '0 contas';
                                    console.log('[SisbMinuta] Removendo réu (' + motivo + '):', nomeNaTabela || p.nome);
                                    var btnMenu = ultimaLinha.querySelector('button.mat-menu-trigger');
                                    if (btnMenu) {
                                        btnMenu.click();
                                        await C.sleep(500);
                                        var btnExcluir = document.querySelector('button.mat-menu-item mat-icon.fa-trash-alt') ||
                                                         document.querySelector('button.mat-menu-item');
                                        if (btnExcluir) {
                                            var targetExcluir = btnExcluir.closest('button') || btnExcluir;
                                            targetExcluir.click();
                                            await C.sleep(800);
                                            C.mostrarToast('Réu removido (' + motivo + ')', 'aviso');
                                        }
                                    }
                                } else {
                                    console.log('[SisbMinuta] Réu mantido com ' + qtde + ' relacionamento(s)');
                                }
                            }
                        }
                    }
                }
            }
        }

        console.log('[SisbMinuta] Preenchimento concluído para ' + nomeAcao);
        C.mostrarToast('Preenchimento concluído (' + nomeAcao + ')!', 'ok');
    }

    async function autoRunMinuta() {
        var href = window.location.href;
        if (href.indexOf('sisbajud.cnj.jus.br') === -1 && href.indexOf('sisbajud.pdpj.jus.br') === -1) return;

        let acao = C.lerEstado('sisbajud_acao');
        let dados = C.lerEstado('sisbajud_dados_basicos');

        if (dados && href.indexOf('/minuta/cadastrar') > -1) {
            if (acao === 'ordem2' || acao === 'teimosinha' || acao === 'endereco') {
                C.salvarEstado('sisbajud_acao', null);
                await preencherFormularioMinuta(acao, dados);
            } else {
                injetarBotoesMinuta(dados);
            }
        }
    }

    window.SisbMinuta = {
        calcularProximoDiaUtilProtocolo: calcularProximoDiaUtilProtocolo,
        injetarBotaoOrdem2: injetarBotaoOrdem2,
        injetarBotoesMinuta: injetarBotoesMinuta,
        selecionarDataNoCalendario: selecionarDataNoCalendario,
        preencherFormularioMinuta: preencherFormularioMinuta,
        autoRunMinuta: autoRunMinuta
    };

})();
