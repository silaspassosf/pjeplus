import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

"""
SISB Minutas - Preenchimento de campos iniciais
"""


def _preencher_campos_iniciais(driver, dados_processo, prazo_dias, agendar_amanha=False, agendar_offset=1):
    """
    Helper para preencher campos iniciais da minuta de bloqueio.

    Args:
        driver: WebDriver do SISBAJUD
        dados_processo: Dados do processo
        prazo_dias: Prazo em dias (0, 1, 30 ou 60). 0 = amanhã para teimosinha.
        agendar_amanha: Se True, seleciona 'Agendar protocolo = Sim' e define
                        a data do protocolo conforme agendar_offset + regras de
                        horário/dia da semana.
        agendar_offset: Offset base em dias para o agendamento (default=1).
                        Ex: offset=1 → amanhã (d+1), offset=2 → d+2.
                        Aplica-se a regra de pós-19h e sexta-feira sobre o offset.
    """
    try:
        from ..utils import criar_js_otimizado

        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        vara = dados_processo.get('sisbajud', {}).get('vara', '30006')
        numero_lista = dados_processo.get('numero', [])
        numero_processo = numero_lista[0] if numero_lista else ''

        cpf_cnpj_autor = ''
        nome_autor = ''
        if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
            cpf_cnpj_autor = dados_processo['autor'][0].get('cpfcnpj', '')
            nome_autor = dados_processo['autor'][0].get('nome', '')
        elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
            cpf_cnpj_autor = dados_processo['reu'][0].get('cpfcnpj', '')
            nome_autor = dados_processo['reu'][0].get('nome', '')

        cpf_cnpj_limpo = cpf_cnpj_autor.replace('.', '').replace('-', '').replace('/', '')

        if prazo_dias not in [0, 1, 30, 60]:
            prazo_dias = 30

        # Calcular data de agendamento da 2ª minuta conforme horário e dia da semana
        _agora = datetime.now()
        _hora = _agora.hour
        _dia_semana = _agora.weekday()  # 0=segunda .. 4=sexta, 5=sáb, 6=dom

        if _dia_semana == 4:            # Sexta-feira
            if _hora < 19:
                _amanha = _agora + timedelta(days=agendar_offset + 2)   # pula fim de semana → segunda (offset 1) ou terça (offset 2)
            else:
                _amanha = _agora + timedelta(days=agendar_offset + 3)   # pula fim de semana → terça (offset 1) ou quarta (offset 2)
        elif _hora >= 19:
            _amanha = _agora + timedelta(days=agendar_offset + 1)       # após 19h → d+offset+1
        else:
            _amanha = _agora + timedelta(days=agendar_offset)           # antes 19h, dia útil → d+offset

        _ag_ano = _amanha.year
        _ag_mes = _amanha.month - 1   # 0-based para JS
        _ag_dia = _amanha.day
        _meses_js = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                     "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        _meses_js_str = str(_meses_js)

        if agendar_amanha:
            # js_agendamento é uma f-string separada: os {{ }} aqui viram { } no valor final.
            # Quando esse valor for injetado no script_unico_campos via {js_agendamento},
            # o f-string externo insere o valor como está — sem reinterpretar as chaves.
            js_agendamento = f"""
                // 9. AGENDAR PROTOCOLO PARA AMANHÃ (2ª minuta)
                log.push('9. Selecionando agendamento de protocolo (Sim)...');
                let agendado = false;
                let todosRowsAg = Array.from(document.querySelectorAll('div.row, sisbajud-cadastro-minuta .row'));
                for (let rwAg of todosRowsAg) {{
                    if (rwAg.textContent.includes('Agendar protocolo do bloqueio')) {{
                        let radsAg = rwAg.parentElement.querySelectorAll('mat-radio-button');
                        for (let rAg of radsAg) {{
                            if (rAg.innerText.includes('Sim')) {{
                                let lblAg = rAg.querySelector('label') || rAg;
                                lblAg.click();
                                agendado = true;
                                log.push('Agendamento: Sim clicado com sucesso');
                                break;
                            }}
                        }}
                        break;
                    }}
                }}
                if (!agendado) {{
                    let allRadios = Array.from(document.querySelectorAll('mat-radio-button'));
                    for (let r of allRadios) {{
                        let parentText = (r.closest('.row') || r.parentElement || {{}}).textContent || '';
                        if (parentText.includes('Agendar') && (r.textContent || '').includes('Sim')) {{
                            let lbl = r.querySelector('label') || r;
                            lbl.click();
                            agendado = true;
                            log.push('Agendamento: Sim clicado via fallback');
                            break;
                        }}
                    }}
                }}
                await new Promise(r => setTimeout(r, 1000));

                // 10. CALENDÁRIO DO AGENDAMENTO (amanhã / próxima data útil)
                if (agendado) {{
                    log.push('10. Configurando calendario do agendamento ({_ag_dia:02d}/{_ag_mes+1:02d}/{_ag_ano})...');
                    let inputDataProt = await esperarElemento('input[placeholder="Data do protocolo:"], input[formcontrolname="dataProtocolo"]', 5000);
                    if (inputDataProt) {{
                        let paiDp = inputDataProt.closest('mat-form-field') || inputDataProt.parentElement.parentElement;
                        let btnCalAg = paiDp ? paiDp.querySelector('button[aria-label="Open calendar"]') : document.querySelector('button[aria-label="Open calendar"]');
                        if (btnCalAg) {{
                            btnCalAg.click();
                            await new Promise(r => setTimeout(r, 800));
                            let calAgOk = await selecionarDataCalendario({_ag_ano}, {_ag_mes}, {_ag_dia}, log, 'Agendamento Protocolo');
                            if (!calAgOk) {{
                                log.push('[CAL] Falha ao clicar calendário agendamento; preenchendo input diretamente...');
                                let dataAgFormatada = '{_ag_dia:02d}/{_ag_mes+1:02d}/{_ag_ano}';
                                inputDataProt.focus();
                                inputDataProt.value = dataAgFormatada;
                                triggerEvent(inputDataProt, 'input');
                                triggerEvent(inputDataProt, 'change');
                                inputDataProt.blur();
                                log.push('[CAL] Input Data do protocolo preenchido: ' + dataAgFormatada);
                            }}
                        }} else {{
                            log.push('[CAL] Botão calendário agendamento não encontrado; preenchendo input...');
                            let dataAgFormatada = '{_ag_dia:02d}/{_ag_mes+1:02d}/{_ag_ano}';
                            inputDataProt.focus();
                            inputDataProt.value = dataAgFormatada;
                            triggerEvent(inputDataProt, 'input');
                            triggerEvent(inputDataProt, 'change');
                            inputDataProt.blur();
                        }}
                    }} else {{
                        log.push('[AVISO] Input Data do protocolo não encontrado');
                    }}
                }}
"""
        else:
            js_agendamento = ''

        numdias = prazo_dias
        hoje = datetime.now()
        data_fim = hoje + timedelta(days=numdias + 1)

        ano = data_fim.year
        mes_d = data_fim.month - 1
        dia_d = data_fim.day

        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

        script_unico_campos = f"""
        {criar_js_otimizado()}

        async function digitarTexto(el, texto, atrasoMs) {{
            // Equivalente a simularDigitacaoDeTexto do +pje: eventos de teclado por caractere
            // (necessario para inputs com mascara CPF/CNPJ e para campos reativos do Angular).
            el.focus();
            el.value = '';
            triggerEvent(el, 'input');
            for (const ch of String(texto).split('')) {{
                el.dispatchEvent(new KeyboardEvent('keydown', {{ key: ch, bubbles: true, cancelable: true }}));
                el.dispatchEvent(new KeyboardEvent('keypress', {{ key: ch, bubbles: true, cancelable: true }}));
                el.value += ch;
                triggerEvent(el, 'input');
                el.dispatchEvent(new KeyboardEvent('keyup', {{ key: ch, bubbles: true, cancelable: true }}));
                if (atrasoMs) await new Promise(r => setTimeout(r, atrasoMs));
            }}
            triggerEvent(el, 'change');
        }}

        async function selecionarDataCalendario(anoAlvo, mesIndexAlvo, diaAlvo, log, descricao) {{
            let desc = descricao || 'Data';
            log.push('[CAL][' + desc + '] Iniciando selecao: dia=' + diaAlvo + ', mes=' + (mesIndexAlvo + 1) + ', ano=' + anoAlvo);

            let mesesExt = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
            let mesesAbrev = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

            let cal = null;
            for (let w = 0; w < 10; w++) {{
                cal = document.querySelector('mat-calendar');
                if (cal) break;
                await new Promise(r => setTimeout(r, 200));
            }}
            if (!cal) {{
                log.push('[CAL][' + desc + '] ERRO: mat-calendar nao encontrado');
                return false;
            }}

            let btnMesAno = cal.querySelector('button[aria-label="Choose month and year"], .mat-calendar-period-button');
            if (btnMesAno) {{
                log.push('[CAL][' + desc + '] Clicando periodo: ' + (btnMesAno.textContent || '').trim());
                btnMesAno.click();
                await new Promise(r => setTimeout(r, 700));
            }}

            let anoSel = 'mat-calendar td[aria-label="' + anoAlvo + '"], mat-calendar button[aria-label="' + anoAlvo + '"], mat-calendar .mat-calendar-body-cell[aria-label="' + anoAlvo + '"]';
            let anoCell = document.querySelector(anoSel);
            if (!anoCell) {{
                let celulas = Array.from(document.querySelectorAll('mat-calendar .mat-calendar-body-cell'));
                anoCell = celulas.find(c => (c.textContent || '').trim() === String(anoAlvo));
            }}
            if (anoCell) {{
                log.push('[CAL][' + desc + '] Ano ' + anoAlvo + ' encontrado. Clicando...');
                anoCell.click();
                await new Promise(r => setTimeout(r, 700));
            }} else {{
                log.push('[CAL][' + desc + '] Celula do ano ' + anoAlvo + ' nao visivel (ja na visao do ano).');
            }}

            let mesAtual = mesIndexAlvo;
            let diaD = diaAlvo;
            let mesClicado = false;

            while (mesAtual >= 0) {{
                let mesNome = mesesExt[mesAtual];
                let mesAbr = mesesAbrev[mesAtual];
                let mesLabel = mesNome + ' de ' + anoAlvo;

                let selMes = 'mat-calendar td[aria-label="' + mesLabel + '"], mat-calendar button[aria-label="' + mesLabel + '"], mat-calendar .mat-calendar-body-cell[aria-label="' + mesLabel + '"]';
                let mesCell = document.querySelector(selMes);

                if (!mesCell) {{
                    let todasMes = Array.from(document.querySelectorAll('mat-calendar .mat-calendar-body-cell'));
                    mesCell = todasMes.find(c => {{
                        let lbl = (c.getAttribute('aria-label') || '').toLowerCase();
                        let txt = (c.textContent || '').trim().toLowerCase();
                        return (lbl.includes(mesNome) || lbl.includes(mesAbr) || txt === mesAbr || txt === mesNome);
                    }});
                }}

                if (mesCell && !mesCell.getAttribute('aria-disabled') && !mesCell.classList.contains('mat-calendar-body-disabled')) {{
                    log.push('[CAL][' + desc + '] Mes encontrado: ' + mesNome + ' (' + (mesAtual + 1) + ')');
                    mesCell.click();
                    mesClicado = true;
                    break;
                }}
                mesAtual--;
                diaD = 31;
            }}

            if (!mesClicado) {{
                log.push('[CAL][' + desc + '] ERRO: Nenhum mes habilitado encontrado');
                return false;
            }}
            await new Promise(r => setTimeout(r, 700));

            let mesFinalNome = mesesExt[mesAtual];
            let diaClicado = false;

            while (diaD > 0) {{
                let diaLabel = diaD + ' de ' + mesFinalNome + ' de ' + anoAlvo;
                let diaLabelCurto = diaD + ' de ' + mesFinalNome;

                let selDia = 'mat-calendar td[aria-label="' + diaLabel + '"], mat-calendar button[aria-label="' + diaLabel + '"], ' +
                             'mat-calendar td[aria-label="' + diaLabelCurto + '"], mat-calendar button[aria-label="' + diaLabelCurto + '"], ' +
                             'mat-calendar .mat-calendar-body-cell[aria-label*="' + diaD + ' de ' + mesFinalNome + '"]';
                let diaCell = document.querySelector(selDia);

                if (!diaCell) {{
                    let todasDia = Array.from(document.querySelectorAll('mat-calendar .mat-calendar-body-cell'));
                    diaCell = todasDia.find(c => {{
                        let content = c.querySelector('.mat-calendar-body-cell-content') || c;
                        return (content.textContent || '').trim() === String(diaD);
                    }});
                }}

                if (diaCell && !diaCell.getAttribute('aria-disabled') && !diaCell.classList.contains('mat-calendar-body-disabled')) {{
                    log.push('[CAL][' + desc + '] Dia encontrado: ' + diaD + ' de ' + mesFinalNome + '. Clicando...');
                    diaCell.click();
                    diaClicado = true;
                    break;
                }}
                diaD--;
            }}

            if (!diaClicado) {{
                log.push('[CAL][' + desc + '] ERRO: Nenhum dia habilitado encontrado em ' + mesFinalNome);
                return false;
            }}

            await new Promise(r => setTimeout(r, 500));
            log.push('[CAL][' + desc + '] Sucesso: data definida para ' + diaD + '/' + (mesAtual + 1) + '/' + anoAlvo);
            return {{ano: anoAlvo, mes: mesAtual + 1, dia: diaD}};
        }}

        async function preencherMinutaCompleta() {{
            let log = [];

            try {{
                log.push('1. Preenchendo Juiz...');
                let juizInput = await esperarElemento('input[placeholder*="Juiz"]', 5000);
                if (juizInput) {{
                    juizInput.focus();
                    juizInput.value = '{juiz}';
                    triggerEvent(juizInput, 'input');

                    await new Promise(resolve => setTimeout(resolve, 500));
                    let opcoes = await esperarOpcoes('mat-option[role="option"]', 3000);
                    for (let opcao of opcoes) {{
                        if (opcao.textContent.toLowerCase().includes('{juiz.lower()}')) {{
                            opcao.click();
                            log.push('Juiz: {juiz}');
                            break;
                        }}
                    }}
                    await new Promise(resolve => setTimeout(resolve, 800));
                }}

                log.push('2. Preenchendo Vara...');
                let varaSelect = await esperarElemento('mat-select[name*="varaJuizoSelect"],mat-select[aria-label*="Selecione a Vara"]', 3000);
                if (varaSelect) {{
                    varaSelect.focus();
                    varaSelect.click();

                    let campoPesquisaVara = await esperarElemento('.mat-select-panel input[placeholder="Pesquisar Vara/Juízo..."]', 3000);
                    if (campoPesquisaVara) {{
                        await new Promise(resolve => setTimeout(resolve, 1000));

                        campoPesquisaVara.focus();
                        campoPesquisaVara.value = '';
                        for (const letraVara of '{vara}'.split('')) {{
                            campoPesquisaVara.dispatchEvent(new KeyboardEvent('keydown', {{ key: letraVara, bubbles: true, cancelable: true }}));
                            campoPesquisaVara.dispatchEvent(new KeyboardEvent('keypress', {{ key: letraVara, bubbles: true, cancelable: true }}));
                            campoPesquisaVara.value += letraVara;
                            triggerEvent(campoPesquisaVara, 'input');
                            triggerEvent(campoPesquisaVara, 'change');
                            campoPesquisaVara.dispatchEvent(new KeyboardEvent('keyup', {{ key: letraVara, bubbles: true, cancelable: true }}));
                            await new Promise(resolve => setTimeout(resolve, 100));
                        }}
                        let opcoesVara = await esperarOpcoes('mat-option[role="option"]', 3000);
                        let varaSelecionada = false;
                        for (let opcaoVara of opcoesVara) {{
                            let textoOpcaoVara = (opcaoVara.textContent || '').trim();
                            if (textoOpcaoVara.split(' - ')[0].trim() === '{vara}') {{
                                opcaoVara.click();
                                log.push('Vara: ' + textoOpcaoVara);
                                varaSelecionada = true;
                                break;
                            }}
                        }}
                        if (!varaSelecionada) {{
                            log.push('[AVISO] Vara {vara} nao encontrada nas opcoes filtradas');
                        }}
                        await new Promise(resolve => setTimeout(resolve, 800));
                    }}
                }}

                log.push('3. Preenchendo Numero Processo...');
                let numeroInput = await esperarElemento('input[placeholder="Número do Processo"]', 3000);
                if (numeroInput) {{
                    numeroInput.focus();
                    numeroInput.value = '{numero_processo}';
                    triggerEvent(numeroInput, 'input');
                    numeroInput.blur();
                    log.push('Processo: {numero_processo}');
                    await new Promise(resolve => setTimeout(resolve, 800));
                }}

                log.push('4. Preenchendo Tipo Acao...');
                let acaoSelect = await esperarElemento('mat-select[name*="acao"]', 3000);
                if (acaoSelect) {{
                    acaoSelect.focus();
                    acaoSelect.click();

                    await new Promise(resolve => setTimeout(resolve, 500));
                    let opcoes = await esperarOpcoes('mat-option[role="option"]', 3000);
                    // +pje: opcao exata 'Ação Trabalhista'. Fallback: qualquer variante trabalhista.
                    let opcaoAcao = null;
                    for (let opcao of opcoes) {{
                        if ((opcao.innerText || opcao.textContent || '').trim() === 'Ação Trabalhista') {{ opcaoAcao = opcao; break; }}
                    }}
                    if (!opcaoAcao) {{
                        for (let opcao of opcoes) {{
                            let t = (opcao.textContent || '');
                            if (t.includes('Ação Trabalhista') || t.includes('Acao Trabalhista') || t.includes('Execução Trabalhista') || t.includes('Execucao Trabalhista')) {{ opcaoAcao = opcao; break; }}
                        }}
                    }}
                    if (opcaoAcao) {{
                        opcaoAcao.click();
                        log.push('Acao: ' + opcaoAcao.textContent.trim());
                    }} else {{
                        log.push('[AVISO] Opcao de Tipo de Acao trabalhista nao encontrada');
                    }}
                    await new Promise(resolve => setTimeout(resolve, 800));
                }}

                log.push('5. Preenchendo CPF/CNPJ Autor...');
                let cpfInput = await esperarElemento('input[placeholder*="CPF"]', 3000);
                if (cpfInput) {{
                    await digitarTexto(cpfInput, '{cpf_cnpj_limpo}', 30);
                    cpfInput.blur();
                    log.push('CPF/CNPJ Autor: {cpf_cnpj_limpo}');
                    await new Promise(resolve => setTimeout(resolve, 500));
                }}

                log.push('6. Preenchendo Nome Autor...');
                let nomeInput = await esperarElemento('input[placeholder="Nome do autor/exequente da ação"]', 3000);
                if (nomeInput) {{
                    await digitarTexto(nomeInput, '{nome_autor}', 10);
                    nomeInput.blur();
                    log.push('Nome Autor: {nome_autor}');
                    await new Promise(resolve => setTimeout(resolve, 500));
                }}

                log.push('7. Selecionando Teimosinha...');
                let radios = document.querySelectorAll('mat-radio-button');
                for (let radio of radios) {{
                    if (radio.textContent.includes('Repetir a ordem')) {{
                        let label = radio.querySelector('label') || radio;
                        if (label) {{
                            label.click();
                            log.push('Teimosinha: Repetir ordem selecionada');
                            break;
                        }}
                    }}
                }}
                await new Promise(resolve => setTimeout(resolve, 600));

                log.push('8. Configurando Calendario de repeticao (prazo {prazo_dias} dias)...');
                let inputDataLimite = document.querySelector('input[placeholder="Data limite:"], input[formcontrolname="dataLimite"]');
                let paiDataLimite = inputDataLimite ? (inputDataLimite.closest('mat-form-field') || inputDataLimite.parentElement.parentElement) : null;
                let btnCalendario = paiDataLimite ? paiDataLimite.querySelector('button[aria-label="Open calendar"]') : document.querySelector('button[aria-label="Open calendar"]');

                if (!btnCalendario) {{
                    return {{sucesso: false, msg: 'Botao calendario nao encontrado', log: log}};
                }}
                btnCalendario.click();
                await new Promise(resolve => setTimeout(resolve, 800));

                let calRes = await selecionarDataCalendario({ano}, {mes_d}, {dia_d}, log, 'Repetição {prazo_dias}d');
                if (!calRes) {{
                    if (inputDataLimite) {{
                        let fallbackData = '{dia_d:02d}/{mes_d + 1:02d}/{ano}';
                        inputDataLimite.focus();
                        inputDataLimite.value = fallbackData;
                        triggerEvent(inputDataLimite, 'input');
                        triggerEvent(inputDataLimite, 'change');
                        inputDataLimite.blur();
                        log.push('[CAL] Fallback no input Data limite preenchido: ' + fallbackData);
                        calRes = {{ano: {ano}, mes: {mes_d + 1}, dia: {dia_d}}};
                    }} else {{
                        return {{sucesso: false, msg: 'Falha ao selecionar data no calendario', log: log}};
                    }}
                }}

                let dataFinal = (calRes.dia < 10 ? '0' + calRes.dia : calRes.dia) + '/' +
                                (calRes.mes < 10 ? '0' + calRes.mes : calRes.mes) + '/' + calRes.ano;
                log.push('Data final configurada: ' + dataFinal);

{js_agendamento}
                return {{sucesso: true, msg: 'Campos preenchidos com sucesso', log: log, data_final: dataFinal}};

            }} catch(e) {{
                return {{sucesso: false, msg: 'Erro: ' + e.message, log: log}};
            }}
        }}

        return preencherMinutaCompleta().then(arguments[arguments.length - 1]).catch(e => arguments[arguments.length - 1]({{sucesso: false, msg: 'Excecao assincrona: ' + (e && e.message ? e.message : e), log: []}}));
        """

        resultado_campos = driver.execute_async_script(script_unico_campos)

        # Logar detalhadamente TODAS as mensagens do script JS no log da execução:
        if resultado_campos and isinstance(resultado_campos, dict) and resultado_campos.get('log'):
            for msg in resultado_campos['log']:
                logger.info(f'[SISBAJUD][CAMPOS] {msg}')

        if resultado_campos and isinstance(resultado_campos, dict) and resultado_campos.get('sucesso'):
            data_limite_str = resultado_campos.get('data_final', data_fim.strftime('%d/%m/%Y'))
            logger.info(f'[SISBAJUD] Campos iniciais preenchidos com sucesso (data limite: {data_limite_str})')
            return data_limite_str

        msg_erro = None
        if isinstance(resultado_campos, dict):
            msg_erro = resultado_campos.get('msg') or resultado_campos.get('erro')
        if not msg_erro:
            msg_erro = str(resultado_campos) if resultado_campos else 'Erro desconhecido (retorno vazio/None)'

        logger.error(f'[SISBAJUD]  Falha no preenchimento: {msg_erro}')
        return None

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao preencher campos iniciais: {e}')
        return None

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao preencher campos iniciais: {e}')
        return None