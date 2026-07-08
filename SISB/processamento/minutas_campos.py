import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

"""
SISB Minutas - Preenchimento de campos iniciais
"""


def _preencher_campos_iniciais(driver, dados_processo, prazo_dias, agendar_amanha=False):
    """
    Helper para preencher campos iniciais da minuta de bloqueio.

    Args:
        driver: WebDriver do SISBAJUD
        dados_processo: Dados do processo
        prazo_dias: Prazo em dias (0, 1, 30 ou 60). 0 = amanhã para teimosinha.
        agendar_amanha: Se True, seleciona 'Agendar protocolo = Sim' e define
                        a data do protocolo para amanhã (usado na 2ª minuta).
                        Lógica portada do maispje copiarDadosParaNovaOrdem2.
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

        # Calcular amanhã para o agendamento do 2º protocolo (maispje: i=1 → numdias=-1 → hoje+1)
        _amanha = datetime.now() + timedelta(days=1)
        _ag_ano = _amanha.year
        _ag_mes = _amanha.month - 1   # 0-based para JS
        _ag_dia = _amanha.day
        _meses_js = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho",
                     "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        _meses_js_str = str(_meses_js)

        if agendar_amanha:
            # js_agendamento é uma f-string separada: os {{ }} aqui viram { } no valor final.
            # Quando esse valor for injetado no script_unico_campos via {js_agendamento},
            # o f-string externo insere o valor como está — sem reinterpretar as chaves.
            js_agendamento = f"""
                // 9. AGENDAR PROTOCOLO PARA AMANHÃ (2ª minuta — portado do maispje)
                log.push('9. Selecionando agendamento para amanha (dia seguinte)...');
                let agendado = false;
                let todosRowsAg = Array.from(document.querySelectorAll('div.row, sisbajud-cadastro-minuta .row'));
                for (let rwAg of todosRowsAg) {{
                    if (rwAg.textContent.includes('Agendar protocolo do bloqueio')) {{
                        let radsAg = rwAg.parentElement.querySelectorAll('mat-radio-button');
                        for (let rAg of radsAg) {{
                            if (rAg.innerText.includes('Sim')) {{
                                rAg.querySelector('label').click();
                                agendado = true;
                                log.push('Agendamento: Sim clicado');
                                break;
                            }}
                        }}
                        break;
                    }}
                }}
                await new Promise(r => setTimeout(r, 1000));

                // 10. CALENDÁRIO DO AGENDAMENTO (amanhã)
                // Lógica maispje escolherDataNocalendario(i=1): numdias=-1, data=hoje+1
                if (agendado) {{
                    log.push('10. Calendario agendamento (amanha)...');
                    let agAno = {_ag_ano};
                    let agMes = {_ag_mes};
                    let agDia = {_ag_dia};
                    let mesesAg = {_meses_js_str};

                    let inputDataProt = await esperarElemento('input[placeholder="Data do protocolo:"]', 5000);
                    if (inputDataProt) {{
                        let paiDp = inputDataProt.parentElement.parentElement;
                        let btnCalAg = paiDp.querySelector('button[aria-label="Open calendar"]');
                        if (btnCalAg) {{
                            btnCalAg.click();
                            await new Promise(r => setTimeout(r, 1000));
                            let btnMAAg = await esperarElemento('mat-calendar button[aria-label="Choose month and year"]', 3000);
                            if (btnMAAg) {{
                                btnMAAg.click();
                                await new Promise(r => setTimeout(r, 1000));
                                let anoCellAg = await esperarElemento('mat-calendar td[aria-label="' + agAno + '"]', 3000);
                                if (anoCellAg) {{ anoCellAg.click(); await new Promise(r => setTimeout(r, 1000)); }}
                                let mesAtAg = agMes;
                                let diaDag = agDia;
                                while (mesAtAg >= 0) {{
                                    let msAg = mesesAg[mesAtAg] + ' de ' + agAno;
                                    let msCellAg = document.querySelector('mat-calendar td[aria-label="' + msAg + '"]');
                                    if (msCellAg && !msCellAg.getAttribute('aria-disabled')) {{ msCellAg.click(); break; }}
                                    mesAtAg--; diaDag = 31;
                                }}
                                await new Promise(r => setTimeout(r, 1000));
                                let mfAg = mesesAg[mesAtAg] + ' de ' + agAno;
                                while (diaDag > 0) {{
                                    let dStrAg = diaDag + ' de ' + mfAg;
                                    let dCellAg = document.querySelector('mat-calendar td[aria-label="' + dStrAg + '"]');
                                    if (dCellAg && !dCellAg.getAttribute('aria-disabled')) {{
                                        dCellAg.click();
                                        log.push('Data agendamento: ' + diaDag + '/' + (mesAtAg+1) + '/' + agAno);
                                        break;
                                    }}
                                    diaDag--;
                                }}
                            }}
                        }}
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

        meses = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

        script_unico_campos = f"""
        {criar_js_otimizado()}

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
                let varaSelect = await esperarElemento('mat-select[name*="varaJuizoSelect"]', 3000);
                if (varaSelect) {{
                    varaSelect.focus();
                    varaSelect.click();

                    await new Promise(resolve => setTimeout(resolve, 500));
                    let opcoes = await esperarOpcoes('mat-option[role="option"]', 3000);
                    for (let opcao of opcoes) {{
                        if (opcao.textContent.includes('{vara}')) {{
                            opcao.click();
                            log.push('Vara: {vara}');
                            break;
                        }}
                    }}
                    await new Promise(resolve => setTimeout(resolve, 800));
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
                    for (let opcao of opcoes) {{
                        if (opcao.textContent.includes('Execucao Trabalhista') || opcao.textContent.includes('Acao Trabalhista') || opcao.textContent.includes('Execução Trabalhista') || opcao.textContent.includes('Ação Trabalhista')) {{
                            opcao.click();
                            log.push('Acao: ' + opcao.textContent.trim());
                            break;
                        }}
                    }}
                    await new Promise(resolve => setTimeout(resolve, 800));
                }}

                log.push('5. Preenchendo CPF/CNPJ Autor...');
                let cpfInput = await esperarElemento('input[placeholder*="CPF"]', 3000);
                if (cpfInput) {{
                    cpfInput.focus();
                    await new Promise(resolve => setTimeout(resolve, 250));
                    cpfInput.value = '{cpf_cnpj_limpo}';
                    triggerEvent(cpfInput, 'input');
                    cpfInput.blur();
                    log.push('CPF/CNPJ Autor: {cpf_cnpj_limpo}');
                    await new Promise(resolve => setTimeout(resolve, 500));
                }}

                log.push('6. Preenchendo Nome Autor...');
                let nomeInput = await esperarElemento('input[placeholder="Nome do autor/exequente da ação"]', 3000);
                if (nomeInput) {{
                    nomeInput.focus();
                    await new Promise(resolve => setTimeout(resolve, 250));
                    nomeInput.value = '{nome_autor}';
                    triggerEvent(nomeInput, 'input');
                    nomeInput.blur();
                    log.push('Nome Autor: {nome_autor}');
                    await new Promise(resolve => setTimeout(resolve, 500));
                }}

                log.push('7. Selecionando Teimosinha...');
                let radios = document.querySelectorAll('mat-radio-button');
                for (let radio of radios) {{
                    if (radio.textContent.includes('Repetir a ordem')) {{
                        let label = radio.querySelector('label');
                        if (label) {{
                            label.click();
                            log.push('Teimosinha: Repetir ordem');
                            break;
                        }}
                    }}
                }}
                await new Promise(resolve => setTimeout(resolve, 500));

                log.push('8. Configurando Calendario...');
                let btnCalendario = await esperarElemento('button[aria-label="Open calendar"]', 3000);
                if (!btnCalendario) {{
                    return {{sucesso: false, msg: 'Botao calendario nao encontrado', log: log}};
                }}
                btnCalendario.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                let btnMesAno = await esperarElemento('mat-calendar button[aria-label="Choose month and year"]', 3000);
                if (!btnMesAno) {{
                    return {{sucesso: false, msg: 'Selecao mes/ano nao encontrada', log: log}};
                }}
                btnMesAno.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                let anoCell = await esperarElemento('mat-calendar td[aria-label="{ano}"]', 3000);
                if (!anoCell) {{
                    return {{sucesso: false, msg: 'Ano {ano} nao encontrado', log: log}};
                }}
                anoCell.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                let meses = {meses};
                let mesAtual = {mes_d};
                let diaD = {dia_d};
                let mesEncontrado = false;

                while (mesAtual >= 0) {{
                    let mesStr = meses[mesAtual] + ' de {ano}';
                    let mesCell = document.querySelector('mat-calendar td[aria-label="' + mesStr + '"]');
                    if (mesCell && !mesCell.getAttribute('aria-disabled')) {{
                        mesCell.click();
                        mesEncontrado = true;
                        break;
                    }}
                    mesAtual--;
                    diaD = 31;
                }}

                if (!mesEncontrado) {{
                    return {{sucesso: false, msg: 'Nenhum mes disponivel', log: log}};
                }}
                await new Promise(resolve => setTimeout(resolve, 1000));

                let mesFinalStr = meses[mesAtual] + ' de {ano}';
                let diaEncontrado = false;

                while (diaD > 0) {{
                    let diaStr = diaD + ' de ' + mesFinalStr;
                    let diaCell = document.querySelector('mat-calendar td[aria-label="' + diaStr + '"]');
                    if (diaCell && !diaCell.getAttribute('aria-disabled')) {{
                        diaCell.click();
                        diaEncontrado = true;
                        break;
                    }}
                    diaD--;
                }}

                if (!diaEncontrado) {{
                    return {{sucesso: false, msg: 'Nenhum dia disponivel', log: log}};
                }}

                let dataFinal = diaD + '/' + (mesAtual + 1) + '/{ano}';
                log.push('Data final: ' + dataFinal);

{js_agendamento}
                return {{sucesso: true, msg: 'Campos preenchidos com sucesso', log: log, data_final: dataFinal}};

            }} catch(e) {{
                return {{sucesso: false, msg: 'Erro: ' + e.message, log: log}};
            }}
        }}

        return preencherMinutaCompleta().then(arguments[arguments.length - 1]);
        """

        resultado_campos = driver.execute_async_script(script_unico_campos)

        if resultado_campos and resultado_campos.get('sucesso'):
            if resultado_campos.get('log'):
                for msg in resultado_campos['log']:
                    _ = msg
            data_limite_str = resultado_campos.get('data_final', data_fim.strftime('%d/%m/%Y'))
            return data_limite_str

        msg_erro = resultado_campos.get('msg') if resultado_campos else 'Erro desconhecido'
        logger.error(f'[SISBAJUD]  Falha no preenchimento: {msg_erro}')
        if resultado_campos and resultado_campos.get('log'):
            for msg in resultado_campos['log']:
                _ = msg
        return None

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao preencher campos iniciais: {e}')
        return None