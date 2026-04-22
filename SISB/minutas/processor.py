from Fix.scripts import carregar_js
from pathlib import Path
import logging
import os
logger = logging.getLogger(__name__)

"""
SISBAJUD Minutas - Processamento de minutas de bloqueio
"""

import time
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def _selecionar_prazo_bloqueio(driver, padrao=30):
    """
    Helper para selecionar prazo (30 ou 60 dias) via diálogo JavaScript no SISBAJUD.

    Args:
        driver: Driver SISBAJUD
        padrao: Valor padrão (30 ou 60)

    Returns:
        int: Prazo selecionado (30 ou 60) ou padrão se usuário cancelar
    """
    try:
        script_selecao_prazo = """
        return new Promise((resolve) => {
            // Criar overlay
            const overlay = document.createElement('div');
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 100000;
                display: flex;
                justify-content: center;
                align-items: center;
            `;

            // Criar diálogo
            const dialog = document.createElement('div');
            dialog.style.cssText = `
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                text-align: center;
                min-width: 400px;
            `;

            // Título
            const titulo = document.createElement('h2');
            titulo.textContent = 'Selecionar Prazo de Bloqueio';
            titulo.style.cssText = 'color: #333; margin-bottom: 20px; font-size: 18px;';
            dialog.appendChild(titulo);

            // Texto explicativo
            const explicacao = document.createElement('p');
            explicacao.textContent = 'Escolha o prazo para a minuta de bloqueio:';
            explicacao.style.cssText = 'color: #666; margin-bottom: 20px;';
            dialog.appendChild(explicacao);

            // Container de botões
            const btnContainer = document.createElement('div');
            btnContainer.style.cssText = 'display: flex; gap: 10px; justify-content: center;';

            // Botão 30 dias
            const btn30 = document.createElement('button');
            btn30.textContent = '30 dias + 1';
            btn30.style.cssText = `
                padding: 12px 30px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
            `;
            btn30.onmouseover = () => btn30.style.background = '#0056b3';
            btn30.onmouseout = () => btn30.style.background = '#007bff';
            btn30.onclick = () => {
                overlay.remove();
                resolve(30);
            };
            btnContainer.appendChild(btn30);

            // Botão 60 dias
            const btn60 = document.createElement('button');
            btn60.textContent = '60 dias + 1';
            btn60.style.cssText = `
                padding: 12px 30px;
                background: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
            `;
            btn60.onmouseover = () => btn60.style.background = '#1e7e34';
            btn60.onmouseout = () => btn60.style.background = '#28a745';
            btn60.onclick = () => {
                overlay.remove();
                resolve(60);
            };
            btnContainer.appendChild(btn60);

            dialog.appendChild(btnContainer);
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);
        });
        """

        prazo_selecionado = driver.execute_async_script(script_selecao_prazo)

        if prazo_selecionado in [30, 60]:
            return prazo_selecionado
        else:
            return padrao

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao selecionar prazo: {e}, usando padrão: {padrao}')
        return padrao


def _preencher_campos_iniciais(driver, dados_processo, prazo_dias):
    """
    Helper para preencher campos iniciais da minuta de bloqueio.

    Args:
        driver: Driver SISBAJUD
        dados_processo: Dados do processo
        prazo_dias: Prazo em dias

    Returns:
        str or None: Data limite formatada ou None se erro
    """
    try:
        from ..utils import criar_js_otimizado

        # Valores hardcoded (equivalentes às preferências do gigs.py)
        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        vara = dados_processo.get('sisbajud', {}).get('vara', '30006')
        numero_lista = dados_processo.get('numero', [])
        numero_processo = numero_lista[0] if numero_lista else ''

        # CPF/CNPJ e nome do autor
        cpf_cnpj_autor = ''
        nome_autor = ''
        if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
            cpf_cnpj_autor = dados_processo['autor'][0].get('cpfcnpj', '')
            nome_autor = dados_processo['autor'][0].get('nome', '')
        elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
            cpf_cnpj_autor = dados_processo['reu'][0].get('cpfcnpj', '')
            nome_autor = dados_processo['reu'][0].get('nome', '')

        cpf_cnpj_limpo = cpf_cnpj_autor.replace('.', '').replace('-', '').replace('/', '')

        # Validar prazo_dias
        if prazo_dias not in [30, 60]:
            prazo_dias = 30

        # Calcular data
        numdias = prazo_dias
        hoje = datetime.now()
        data_fim = hoje + timedelta(days=numdias + 1)

        ano = data_fim.year
        mes_d = data_fim.month - 1  # Month index (0-11 como no JS)
        dia_d = data_fim.day

        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

        # SCRIPT ÚNICO - Preenche TODOS os campos (1-8) em uma única requisição
        script_unico_campos = f"""
        {criar_js_otimizado()}

        async function preencherMinutaCompleta() {{
            let log = [];

            try {{
                // 1. JUIZ SOLICITANTE
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
                            log.push(' Juiz: {juiz}');
                            break;
                        }}
                    }}
                    await new Promise(resolve => setTimeout(resolve, 800));
                }}

                // 2. VARA/JUÍZO
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
                            log.push(' Vara: {vara}');
                            break;
                        }}
                    }}
                    await new Promise(resolve => setTimeout(resolve, 800));
                }}

                // 3. NÚMERO DO PROCESSO
                log.push('3. Preenchendo Número Processo...');
                let numeroInput = await esperarElemento('input[placeholder="Número do Processo"]', 3000);
                if (numeroInput) {{
                    numeroInput.focus();
                    numeroInput.value = '{numero_processo}';
                    triggerEvent(numeroInput, 'input');
                    numeroInput.blur();
                    log.push(' Processo: {numero_processo}');
                    await new Promise(resolve => setTimeout(resolve, 800));
                }}

                // 4. TIPO DE AÇÃO
                log.push('4. Preenchendo Tipo Ação...');
                let acaoSelect = await esperarElemento('mat-select[name*="acao"]', 3000);
                if (acaoSelect) {{
                    acaoSelect.focus();
                    acaoSelect.click();

                    await new Promise(resolve => setTimeout(resolve, 500));
                    let opcoes = await esperarOpcoes('mat-option[role="option"]', 3000);
                    for (let opcao of opcoes) {{
                        if (opcao.textContent.includes('Ação Trabalhista')) {{
                            opcao.click();
                            log.push(' Ação: Trabalhista');
                            break;
                        }}
                    }}
                    await new Promise(resolve => setTimeout(resolve, 800));
                }}

                // 5. CPF/CNPJ DO AUTOR
                log.push('5. Preenchendo CPF/CNPJ Autor...');
                let cpfInput = await esperarElemento('input[placeholder*="CPF"]', 3000);
                if (cpfInput) {{
                    cpfInput.focus();
                    await new Promise(resolve => setTimeout(resolve, 250));
                    cpfInput.value = '{cpf_cnpj_limpo}';
                    triggerEvent(cpfInput, 'input');
                    cpfInput.blur();
                    log.push(' CPF/CNPJ Autor: {cpf_cnpj_limpo}');
                    await new Promise(resolve => setTimeout(resolve, 500));
                }}

                // 6. NOME DO AUTOR
                log.push('6. Preenchendo Nome Autor...');
                let nomeInput = await esperarElemento('input[placeholder="Nome do autor/exequente da ação"]', 3000);
                if (nomeInput) {{
                    nomeInput.focus();
                    await new Promise(resolve => setTimeout(resolve, 250));
                    nomeInput.value = '{nome_autor}';
                    triggerEvent(nomeInput, 'input');
                    nomeInput.blur();
                    log.push(' Nome Autor: {nome_autor}');
                    await new Promise(resolve => setTimeout(resolve, 500));
                }}

                // 7. TEIMOSINHA
                log.push('7. Selecionando Teimosinha...');
                let radios = document.querySelectorAll('mat-radio-button');
                for (let radio of radios) {{
                    if (radio.textContent.includes('Repetir a ordem')) {{
                        let label = radio.querySelector('label');
                        if (label) {{
                            label.click();
                            log.push(' Teimosinha: Repetir ordem');
                            break;
                        }}
                    }}
                }}
                await new Promise(resolve => setTimeout(resolve, 500));

                // 8. CALENDÁRIO - LÓGICA COMPLETA DO SISB.PY
                log.push('8. Configurando Calendário...');

                // Abrir calendário
                let btnCalendario = await esperarElemento('button[aria-label="Open calendar"]', 3000);
                if (!btnCalendario) {{
                    return {{sucesso: false, msg: 'Botão calendário não encontrado', log: log}};
                }}
                btnCalendario.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Abrir seleção mês/ano
                let btnMesAno = await esperarElemento('mat-calendar button[aria-label="Choose month and year"]', 3000);
                if (!btnMesAno) {{
                    return {{sucesso: false, msg: 'Seleção mês/ano não encontrada', log: log}};
                }}
                btnMesAno.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Selecionar ano
                let anoCell = await esperarElemento('mat-calendar td[aria-label="{ano}"]', 3000);
                if (!anoCell) {{
                    return {{sucesso: false, msg: 'Ano {ano} não encontrado', log: log}};
                }}
                anoCell.click();
                log.push(' Ano: {ano}');
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Selecionar mês (lógica exata sisb.py com loop)
                let meses = {meses};
                let mesAtual = {mes_d};
                let diaD = {dia_d};
                let mesEncontrado = false;

                while (mesAtual >= 0) {{
                    let mesStr = meses[mesAtual] + ' de {ano}';
                    let mesCell = document.querySelector('mat-calendar td[aria-label="' + mesStr + '"]');
                    if (mesCell && !mesCell.getAttribute('aria-disabled')) {{
                        mesCell.click();
                        log.push(' Mês: ' + mesStr);
                        mesEncontrado = true;
                        break;
                    }}
                    mesAtual--;
                    diaD = 31;
                }}

                if (!mesEncontrado) {{
                    return {{sucesso: false, msg: 'Nenhum mês disponível', log: log}};
                }}
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Selecionar dia (lógica exata sisb.py com loop)
                let mesFinalStr = meses[mesAtual] + ' de {ano}';
                let diaEncontrado = false;

                while (diaD > 0) {{
                    let diaStr = diaD + ' de ' + mesFinalStr;
                    let diaCell = document.querySelector('mat-calendar td[aria-label="' + diaStr + '"]');
                    if (diaCell && !diaCell.getAttribute('aria-disabled')) {{
                        diaCell.click();
                        log.push(' Dia: ' + diaD);
                        diaEncontrado = true;
                        break;
                    }}
                    diaD--;
                }}

                if (!diaEncontrado) {{
                    return {{sucesso: false, msg: 'Nenhum dia disponível', log: log}};
                }}

                let dataFinal = diaD + '/' + (mesAtual + 1) + '/{ano}';
                log.push(' Data final: ' + dataFinal);

                return {{sucesso: true, msg: 'Campos preenchidos com sucesso', log: log, data_final: dataFinal}};

            }} catch(e) {{
                return {{sucesso: false, msg: 'Erro: ' + e.message, log: log}};
            }}
        }}

        return preencherMinutaCompleta().then(arguments[arguments.length - 1]);
        """

        # Executar SCRIPT ÚNICO
        resultado_campos = driver.execute_async_script(script_unico_campos)

        if resultado_campos and resultado_campos.get('sucesso'):
            if resultado_campos.get('log'):
                for msg in resultado_campos['log']:
                    _ = msg
            data_limite_str = resultado_campos.get('data_final', data_fim.strftime('%d/%m/%Y'))
            return data_limite_str
        else:
            msg_erro = resultado_campos.get('msg') if resultado_campos else 'Erro desconhecido'
            logger.error(f'[SISBAJUD]  Falha no preenchimento: {msg_erro}')
            if resultado_campos and resultado_campos.get('log'):
                for msg in resultado_campos['log']:
                    _ = msg
            return None

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao preencher campos iniciais: {e}')
        return None


def _processar_reus_otimizado(driver, reus):
    """
    Helper para processar réus de forma otimizada.

    Args:
        driver: Driver SISBAJUD
        reus: Lista de réus

    Returns:
        dict: Resultado do processamento
    """
    try:
        from ..utils import criar_js_otimizado

        if not reus:
            return {'sucesso': False, 'msg': 'Nenhum réu encontrado'}

        # Preparar lista de réus para processar
        lista_reus_js = []
        for reu in reus:
            cpf_cnpj = reu.get('cpfcnpj', '')
            if cpf_cnpj:
                cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
                # Para bloqueio, sempre usar apenas raiz do CNPJ
                if len(cpf_cnpj_limpo) == 14:
                    cpf_cnpj_limpo = cpf_cnpj_limpo[:8]
                lista_reus_js.append({
                    'cpfcnpj': cpf_cnpj_limpo,
                    'nome': reu.get('nome', '')
                })

        # SCRIPT ÚNICO que processa TODOS os réus
        script_processar_reus = f"""
        {criar_js_otimizado()}

        async function processarTodosReus() {{
            let reus = {lista_reus_js};
            let log = [];
            let reusAdicionados = 0;
            let reusRemovidos = 0;

            try {{
                for (let i = 0; i < reus.length; i++) {{
                    let reu = reus[i];
                    log.push('\\n=== RÉU ' + (i+1) + '/' + reus.length + ' ===');
                    log.push('Adicionando: ' + reu.nome + ' (' + reu.cpfcnpj + ')');

                    // 1. Buscar campo CPF
                    let cpfInput = await esperarElemento('input[placeholder="CPF/CNPJ do réu/executado"]', 3000);
                    if (!cpfInput) {{
                        cpfInput = await esperarElemento('input.mat-input-element[cpfcnpjmask]', 2000);
                    }}
                    if (!cpfInput) {{
                        log.push(' Campo CPF não encontrado');
                        continue;
                    }}

                    // 2. Preencher CPF/CNPJ
                    cpfInput.focus();
                    cpfInput.value = '';
                    await new Promise(resolve => setTimeout(resolve, 400));

                    cpfInput.value = reu.cpfcnpj;
                    triggerEvent(cpfInput, 'input');
                    triggerEvent(cpfInput, 'change');

                    // 3. Aguardar e clicar no botão adicionar
                    await new Promise(resolve => setTimeout(resolve, 800));

                    let btnAdicionar = document.querySelector('button.btn-adicionar.mat-mini-fab');
                    if (!btnAdicionar) {{
                        btnAdicionar = document.querySelector('button mat-icon.fa-plus-square');
                        if (btnAdicionar) btnAdicionar = btnAdicionar.closest('button');
                    }}

                    if (!btnAdicionar || btnAdicionar.disabled) {{
                        log.push(' Botão adicionar não disponível');
                        continue;
                    }}

                    btnAdicionar.click();
                    log.push(' Réu adicionado, aguardando processamento...');

                    // 4. Aguardar processamento (CRÍTICO)
                    await new Promise(resolve => setTimeout(resolve, 3000));

                    // 5. VERIFICAR CONTAS
                    let tabelaLinhas = document.querySelectorAll('tr.mat-row');
                    if (tabelaLinhas.length > 0) {{
                        let ultimaLinha = tabelaLinhas[tabelaLinhas.length - 1];
                        let celulaRelacionamentos = ultimaLinha.querySelector('td.mat-column-qtdeRelacionamentos');

                        if (celulaRelacionamentos) {{
                            let botaoRelacionamentos = celulaRelacionamentos.querySelector('button .mat-button-wrapper');
                            if (botaoRelacionamentos) {{
                                let qtde = botaoRelacionamentos.textContent.trim();

                                if (qtde === '0') {{
                                    log.push(' Réu sem contas - REMOVENDO...');

                                    // 6. REMOVER RÉU SEM CONTAS
                                    let botaoMenu = ultimaLinha.querySelector('button.mat-menu-trigger');
                                    if (botaoMenu) {{
                                        botaoMenu.click();
                                        await new Promise(resolve => setTimeout(resolve, 500));

                                        let botaoExcluir = document.querySelector('button.mat-menu-item mat-icon.fa-trash-alt');
                                        if (botaoExcluir) {{
                                            botaoExcluir.closest('button').click();
                                            log.push(' Réu removido (0 contas)');
                                            reusRemovidos++;
                                            await new Promise(resolve => setTimeout(resolve, 800));
                                        }}
                                    }}
                                }} else {{
                                    log.push(' Réu possui ' + qtde + ' conta(s) - MANTIDO');
                                    reusAdicionados++;
                                }}
                            }}
                        }}
                    }}

                    // 7. Delay entre réus
                    if (i < reus.length - 1) {{
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }}
                }}

                return {{
                    sucesso: true,
                    log: log,
                    adicionados: reusAdicionados,
                    removidos: reusRemovidos
                }};

            }} catch(e) {{
                return {{
                    sucesso: false,
                    msg: 'Erro: ' + e.message,
                    log: log,
                    adicionados: reusAdicionados,
                    removidos: reusRemovidos
                }};
            }}
        }}

        return processarTodosReus().then(arguments[arguments.length - 1]);
        """

        # Executar processamento de TODOS os réus em 1 requisição
        # Aumentar timeout de script assíncrono temporariamente (evita ScriptTimeoutError)
        try:
            driver.set_script_timeout(120)
        except Exception:
            pass
        try:
            resultado_reus = driver.execute_async_script(script_processar_reus)
        finally:
            try:
                driver.set_script_timeout(30)
            except Exception:
                pass

        if resultado_reus:
            if resultado_reus.get('log'):
                for msg in resultado_reus['log']:
                    _ = msg

            adicionados = resultado_reus.get('adicionados', 0)
            removidos = resultado_reus.get('removidos', 0)

            if resultado_reus.get('sucesso'):
                return {
                    'sucesso': True,
                    'adicionados': adicionados,
                    'removidos': removidos
                }
            else:
                return {
                    'sucesso': False,
                    'msg': resultado_reus.get('msg', ''),
                    'adicionados': adicionados,
                    'removidos': removidos
                }
        else:
            return {'sucesso': False, 'msg': 'Falha no processamento de réus'}

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao processar réus: {e}')
        return {'sucesso': False, 'msg': str(e)}


def _salvar_minuta(driver):
    """
    Helper para salvar a minuta.

    Args:
        driver: Driver SISBAJUD

    Returns:
        bool: True se salvou com sucesso
    """
    try:
        SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
        script_salvar = carregar_js("salvar_minuta.js", SCRIPTS_DIR)
        salvou = driver.execute_script(script_salvar)
        if salvou:
            # Aguardar confirmação do salvamento
            time.sleep(3)

            # Verificar se foi salvo
            script_verificar_salvamento = carregar_js("verificar_salvamento_minuta.js", SCRIPTS_DIR)
            status_salvamento = driver.execute_script(script_verificar_salvamento)

            if status_salvamento == 'SALVO_COM_SUCESSO':
                return True
            elif status_salvamento == 'AINDA_EDITANDO':
                return False
            else:
                return False
        else:
            return False

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao salvar minuta: {e}')
        return False


def _gerar_relatorio_minuta(driver, numero_processo):
    """
    Helper para gerar relatório da minuta.
    Salva no clipboard.txt centralizado.

    Args:
        driver: Driver SISBAJUD
        numero_processo: Número do processo

    Returns:
        dict: Dados do relatório
    """
    try:
        # Coletar dados da minuta
        from ..core import coletar_dados_minuta_sisbajud
        dados_relatorio = coletar_dados_minuta_sisbajud(driver)
        if dados_relatorio:
            try:
                # Salvar no clipboard.txt centralizado
                from PEC.anexos import salvar_conteudo_clipboard
                
                sucesso = salvar_conteudo_clipboard(
                    conteudo=dados_relatorio,
                    numero_processo=numero_processo or "SISBAJUD",
                    tipo_conteudo="sisbajud_minuta",
                    debug=True
                )
                
                if sucesso:
                    _ = sucesso
                else:
                    _ = sucesso

                # Extrair protocolo
                protocolo = None
                try:
                    url = driver.current_url
                    import re
                    match = re.search(r'/(\d{10,})/', url)
                    if match:
                        protocolo = match.group(1)
                except Exception as e:
                    _ = e

                return {
                    'protocolo': protocolo,
                    'tipo': 'bloqueio',
                    'repeticao': 'sim',
                    'conteudo': dados_relatorio  # Guardar conteúdo para possível atualização
                }
            except Exception as e:
                logger.error(f'[SISBAJUD]  Erro ao salvar relatório: {e}')
                return None
        else:
            return None

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao gerar relatório: {e}')
        return None


def _protocolar_minuta(driver, protocolo_minuta=None, log=True):
    """
    Helper para protocolar/assinar minuta no SISBAJUD.
    
    Processo:
    1. Clica no botão "Protocolar" (já está na página da minuta após salvar)
    2. Aguarda modal de senha
    3. Digita a senha no campo de senha de forma humanizada
    4. Confirma o protocolo
    5. Verifica sucesso pelo botão "Copiar Dados para Nova Ordem"
    
    Args:
        driver: Driver SISBAJUD (já deve estar na página da minuta)
        protocolo_minuta: Número do protocolo da minuta (opcional, apenas para log)
        log: Se True, exibe logs detalhados
        
    Returns:
        bool: True se protocolou com sucesso, False caso contrário
    """
    try:
        if log:
            info_protocolo = f' {protocolo_minuta}' if protocolo_minuta else ''

        # Aguardar página estar pronta
        time.sleep(1)
        
        # 1. Localizar e clicar no botão "Protocolar"
        try:
            SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
            script_encontrar_botao = carregar_js("encontrar_botao_protocolar.js", SCRIPTS_DIR)
            encontrado = driver.execute_script(script_encontrar_botao)
            if not encontrado:
                return False
            from Fix.utils import sleep_fixed
            sleep_fixed(0.5)
            script_clicar = carregar_js("clicar_botao_protocolar.js", SCRIPTS_DIR)
            clicado = driver.execute_script(script_clicar)
            if not clicado:
                return False
        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][PROTOCOLO]  Erro ao clicar no botão "Protocolar": {e}')
            return False
        # 3. Aguardar modal de senha aparecer
        sleep_fixed(1)
        # 4. Localizar e preencher campo de senha
        try:
            # Encontrar o campo de senha
            campo_senha = driver.find_element(By.CSS_SELECTOR, 'input[type="password"][formcontrolname="senha"]')
            # Scroll e foco no campo usando JS externo
            script_scroll = carregar_js("scroll_into_view_center.js", SCRIPTS_DIR)
            driver.execute_script(script_scroll, campo_senha)
            from Fix.utils import sleep_fixed
            sleep_fixed(0.3)
            campo_senha.click()
            sleep_fixed(0.3)
            # Digitar a senha de forma humanizada (igual ao login)
            senha = os.environ.get('BP_PASS', '')
            import random
            for i, char in enumerate(senha):
                # Simular erro de digitação (5% chance)
                if random.random() < 0.05:
                    erro_char = chr(random.randint(33, 126))
                    campo_senha.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    campo_senha.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                # Digitar caractere correto
                campo_senha.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))
            
            
        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][PROTOCOLO]  Erro ao digitar senha: {e}')
            return False
        
        # 5. Aguardar e clicar no botão de confirmação
        time.sleep(0.6)  # Aguardar antes de confirmar
        
        try:
            # Procurar botão "Confirmar" com type="submit" e color="primary"
            script_confirmar = """
            const buttons = Array.from(document.querySelectorAll('button[type="submit"][color="primary"]'));
            const confirmBtn = buttons.find(btn => {
                const wrapper = btn.querySelector('span.mat-button-wrapper');
                return wrapper && wrapper.textContent.trim() === 'Confirmar';
            });
            if (confirmBtn) {
                confirmBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                return true;
            }
            return false;
            """
            
            encontrado = driver.execute_script(script_confirmar)
            
            # 5. Aguardar e clicar no botão de confirmação
            sleep_fixed(0.6)
            try:
                script_confirmar = carregar_js("confirmar_minuta.js", SCRIPTS_DIR)
                clicado = driver.execute_script(script_confirmar)
                if clicado:
                    # Aguardar processamento
                    sleep_fixed(2)
                    # Verificar sucesso pela presença do botão "Copiar Dados para Nova Ordem"
                    script_verificar_sucesso = carregar_js("verificar_sucesso_minuta.js", SCRIPTS_DIR)
                    sucesso_verificado = False
                    for tentativa in range(10):  # 10 x 0.5s = 5 segundos
                        try:
                            sucesso_verificado = driver.execute_script(script_verificar_sucesso)
                            if sucesso_verificado:
                                break
                        except Exception as e:
                            _ = e
                        sleep_fixed(0.5)
                    if sucesso_verificado:
                        return True
                    else:
                        return False
                else:
                    return False
            except Exception as e:
                if log:
                    logger.error(f'[SISBAJUD][PROTOCOLO]  Erro ao confirmar: {e}')
                return False
        # ...existing code...
        except Exception as e:
            _ = e
            is_checked = True  # Assumir que funcionou se não deu erro no JavaScript

        if not is_checked:
            return None

        # 4.1 CONFIRMAR com retry que o campo "Data do protocolo:" apareceu
        time.sleep(0.5)

        campo_visivel = False
        for tentativa in range(5):
            script_confirmar_campo_data = """
            const inputs = Array.from(document.querySelectorAll('input[placeholder="Data do protocolo:"]'));
            if (inputs.length > 0) {
                console.log('[DEBUG] Campo Data do protocolo encontrado:', inputs[0].id);
                return true;
            }
            console.log('[DEBUG] Campo Data do protocolo NÃO encontrado');
            return false;
            """

            campo_visivel = driver.execute_script(script_confirmar_campo_data)
            if campo_visivel:
                break

            if log and tentativa < 4:
                _ = tentativa
            time.sleep(0.5)


        if not campo_visivel:
            if log:
                # Debug adicional
                debug = driver.execute_script("""
                const inputs = Array.from(document.querySelectorAll('input.mat-radio-input[type=\"radio\"]'));
                const estados = inputs.map(i => ({id: i.id, value: i.value, checked: i.checked}));
                return JSON.stringify(estados);
                """)
                _ = debug
            return None

        # 5. Calcular e definir data de agendamento (próximo dia útil)
        from datetime import datetime, timedelta
        data_atual = datetime.now()
        weekday = data_atual.weekday()

        if weekday == 4:  # Sexta
            dias_adicionar = 3  # Segunda
        elif weekday == 5:  # Sábado
            dias_adicionar = 2  # Segunda
        else:  # Segunda a quinta
            dias_adicionar = 1

        data_agendamento = data_atual + timedelta(days=dias_adicionar)
        dia_agendar = data_agendamento.day

        # 6. Clicar no ícone do calendário
        script_abrir_calendario = """
        const svgs = Array.from(document.querySelectorAll('svg.mat-datepicker-toggle-default-icon'));
        if (svgs.length > 0) {
            const button = svgs[0].closest('button');
            if (button) {
                button.click();
                return true;
            }
        }
        """

        calendario_aberto = driver.execute_script(script_abrir_calendario)
        if not calendario_aberto:
            return None

        time.sleep(0.5)

        # 7. Selecionar dia no calendário
        # ...existing code...
        # Preencher juiz (usando código da primeira minuta)
        try:
            juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
            script_preencher_juiz = f"""
const input = document.querySelector('input[placeholder*=\"Juiz\"]');
if (input) {{
    input.focus();
    input.value = '{juiz}';
    input.dispatchEvent(new Event('input', {{bubbles: true}}));

    // Aguardar opções
    return new Promise((resolve) => {{
        setTimeout(() => {{
            const opcoes = document.querySelectorAll('span.mat-option-text');
            for (let opcao of opcoes) {{
                if (opcao.textContent && opcao.textContent.toUpperCase().includes('{juiz}'.toUpperCase())) {{
                    opcao.click();
                    resolve(true);
                    return;
                }}
            }}
            resolve(false);
        }}, 800);
    }});
}}
return false;
"""

            juiz_preenchido = driver.execute_async_script(script_preencher_juiz)
            if juiz_preenchido and log:
                _ = juiz_preenchido
            elif log:
                _ = juiz_preenchido
        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][COPIA]  Erro ao preencher juiz: {e}')

        time.sleep(0.5)

        # Preencher calendário de repetição (30 dias + 1) igual primeira minuta
        try:
            prazo_dias = 30
            data_limite = data_atual + timedelta(days=prazo_dias + 1)
            dia_limite = data_limite.day

            if log:
                _ = prazo_dias

            # Clicar no segundo calendário (repetição)
            script_abrir_calendario_rep = """
            const svgs = Array.from(document.querySelectorAll('svg.mat-datepicker-toggle-default-icon'));
            // O segundo calendário (índice 1) é o de repetição
            if (svgs.length > 1) {
                const button = svgs[1].closest('button');
                if (button) {
                    button.click();
                    return true;
                }
            }
            return false;
            """

            cal_rep_aberto = driver.execute_script(script_abrir_calendario_rep)
            if cal_rep_aberto:
                time.sleep(0.5)

                # Selecionar dia no calendário de repetição
                script_sel_dia_rep = f"""
                const cells = Array.from(document.querySelectorAll('.mat-calendar-body-cell'));
                for (const cell of cells) {{
                    const content = cell.querySelector('.mat-calendar-body-cell-content');
                    if (content && content.textContent.trim() === '{dia_limite}') {{
                        if (!cell.classList.contains('mat-calendar-body-disabled')) {{
                            content.click();
                            return true;
                        }}
                    }}
                }}
                return false;
                """

                dia_rep_selecionado = driver.execute_script(script_sel_dia_rep)
                if dia_rep_selecionado and log:
                    _ = dia_rep_selecionado
                elif log:
                    _ = dia_rep_selecionado
            elif log:
                _ = cal_rep_aberto
        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][COPIA]  Erro ao preencher calendário repetição: {e}')

        time.sleep(0.3)

        # Preencher valor
        try:
            from ..processamento_campos import _configurar_valor
            _configurar_valor(driver, dados_processo)
            if log:
                _ = True
        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][COPIA]  Erro ao configurar valor: {e}')

        time.sleep(0.5)

        # 9. Salvar minuta
        minuta_salva = _salvar_minuta(driver)
        if not minuta_salva:
            return None

        # 10. Protocolar minuta agendada
        minuta_protocolada = _protocolar_minuta(driver, protocolo_minuta=None, log=log)
        if not minuta_protocolada:
            # Continuar mesmo sem protocolar - extrair protocolo da URL
            pass

        # 11. Extrair protocolo da segunda minuta

        # Tentar extrair do elemento específico primeiro
        script_extrair_protocolo = """
        const divs = Array.from(document.querySelectorAll('div.col-md-3'));
        for (const div of divs) {
            const label = div.querySelector('div.sisbajud-label');
            if (label && label.textContent.includes('Número do Protocolo')) {
                const valor = div.querySelector('span.sisbajud-label-valor');
                if (valor) {
                    return valor.textContent.trim();
                }
            }
        }
        return null;
        """

        protocolo_agendada = driver.execute_script(script_extrair_protocolo)

        # Fallback: extrair da URL
        if not protocolo_agendada:
            try:
                import re
                url = driver.current_url
                match = re.search(r'/(\d{10,})/', url)
                if match:
                    protocolo_agendada = match.group(1)
            except Exception as e:
                _ = e

        if protocolo_agendada:
            return protocolo_agendada
        else:
            return None

    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD][COPIA]  Erro ao criar minuta agendada por cópia: {e}')
            import traceback
            logger.exception("Erro detectado")
        return None


def _criar_minuta_agendada(driver, dados_processo, reus_ja_processados, prazo_dias=30, log=True):
    """
    Cria segunda minuta idêntica à primeira, mas com agendamento.
    (Implementação completa das linhas 1357-1619)
    """
    try:
        if log:
            _ = True

        # 1. VOLTAR PARA A TELA DE LISTAGEM (onde tem o botão "Nova Minuta")

        script_voltar = """
        // Procurar botão "Voltar" ou ícone de seta
        var btnVoltar = document.querySelector('button mat-icon.fa-arrow-left');
        if (btnVoltar) {
            btnVoltar.closest('button').click();
            return true;
        }
        // Fallback: buscar por texto "Voltar"
        var buttons = document.querySelectorAll('button');
        for (var btn of buttons) {
            if (btn.textContent.toLowerCase().includes('voltar')) {
                btn.click();
                return true;
            }
        }
        return false;
        """

        voltou = driver.execute_script(script_voltar)
        if not voltou:
            # Fallback: navegar para URL base
            try:
                url_atual = driver.current_url
                # Extrair base URL até /minuta/
                import re
                match = re.search(r'(https://[^/]+/sisbajud/[^/]+/teimosinha)', url_atual)
                if match:
                    url_listagem = match.group(1)
                    driver.get(url_listagem)
                    if log:
                        _ = url_listagem
                    time.sleep(2)
                else:
                    return False
            except Exception as e:
                if log:
                    logger.error(f'[SISBAJUD]  Erro ao navegar para listagem: {e}')
                return False
        else:
            time.sleep(1.5)

        # 2. Clicar em "Nova Minuta" novamente

        script_nova_minuta = """
        var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
        if (!botaoNova) {
            botaoNova = document.querySelector('button.mat-fab.mat-primary mat-icon');
        }
        if (botaoNova) {
            if (botaoNova.tagName === 'MAT-ICON') {
                botaoNova = botaoNova.closest('button');
            }
            botaoNova.click();
            return true;
        }
        return false;
        """

        sucesso = driver.execute_script(script_nova_minuta)
        if not sucesso:
            return False

        time.sleep(2)

        # 3. Preencher campos iniciais (reutilizar função existente - com prazo_dias)
        campos_preenchidos = _preencher_campos_iniciais(driver, dados_processo, prazo_dias)
        if not campos_preenchidos:
            return False

        # 3.5. PREENCHER JUIZ EXPLICITAMENTE (da mesma forma que primeira minuta)

        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        script_preencher_juiz = f"""
        async function preencherJuiz() {{
            try {{
                let juizInput = document.querySelector('input[placeholder*="Juiz"]');
                if (juizInput) {{
                    juizInput.focus();
                    juizInput.value = '{juiz}';
                    juizInput.dispatchEvent(new Event('input', {{ bubbles: true }}));

                    await new Promise(resolve => setTimeout(resolve, 500));
                    let opcoes = document.querySelectorAll('mat-option[role="option"]');
                    for (let opcao of opcoes) {{
                        if (opcao.textContent.toLowerCase().includes('{juiz.lower()}')) {{
                            opcao.click();
                            return true;
                        }}
                    }}
                }}
                return false;
            }} catch(e) {{
                return false;
            }}
        }}
        return preencherJuiz();
        """

        juiz_preenchido = driver.execute_async_script(script_preencher_juiz)
        if juiz_preenchido:
            if log:
                _ = juiz_preenchido
        else:
            if log:
                _ = juiz_preenchido

        time.sleep(0.5)

        # 4. Processar REUs (reutilizar função existente)
        reus_processados = _processar_reus_otimizado(driver, dados_processo.get('reu', []))
        if log:
            _ = reus_processados

        # 5. Configurar valor
        from ..processamento_campos import _configurar_valor
        _configurar_valor(driver, dados_processo)

        # 6. MARCAR RADIO "SIM" PARA AGENDAMENTO

        script_marcar_sim = """
        // Procurar radio button "Sim" usando o INPUT com value="2"
        // (Baseado no HTML fornecido: <input type="radio" value="2"> no card "Dados básicos da ordem")
        var radioInputs = document.querySelectorAll('input[type="radio"][name^="mat-radio-group"]');
        for (var input of radioInputs) {
            if (input.value === '2') {  // value="2" = Sim no card "Dados básicos da ordem"
                // Clicar no label associado para acionar corretamente
                var radio = input.closest('mat-radio-button');
                if (radio) {
                    var radioGroup = radio.closest('mat-radio-group');
                    if (radioGroup && radioGroup.classList.contains('sisbajud-radio-group')) {
                        var label = radio.querySelector('label');
                        if (label) {
                            label.click();
                            return true;
                        }
                    }
                }
            }
        }
        return false;
        """

        sim_marcado = driver.execute_script(script_marcar_sim)
        if not sim_marcado:
            return False

        time.sleep(1.5)  # Aguardar campo de data aparecer (aumentado para garantir)

        # 7. CALCULAR DATA DE AGENDAMENTO (próximo dia útil ou segunda se sexta)
        from datetime import datetime, timedelta
        data_atual = datetime.now()
        data_agendamento = data_atual + timedelta(days=1)

        # Se for sexta (4) ou sábado (5), agendar para segunda
        if data_atual.weekday() == 4:  # Sexta
            data_agendamento = data_atual + timedelta(days=3)  # Segunda
            if log:
                _ = data_agendamento
        elif data_atual.weekday() == 5:  # Sábado (improvável, mas por segurança)
            data_agendamento = data_atual + timedelta(days=2)  # Segunda
            if log:
                _ = data_agendamento
        else:
            if log:
                _ = data_agendamento

        data_formatada = data_agendamento.strftime('%d/%m/%Y')
        if log:
            _ = data_formatada

        # 8. CLICAR NO ÍCONE DO CALENDÁRIO DE AGENDAMENTO (não confundir com calendário dos 30 dias)

        script_abrir_calendario = """
        // Procurar ícone do calendário SVG de AGENDAMENTO
        // Importante: há 2 calendários na página - precisamos do de agendamento
        // Ele aparece DEPOIS do radio "Sim" ser marcado
        var todosIcones = document.querySelectorAll('svg.mat-datepicker-toggle-default-icon');
        var iconeAgendamento = null;

        // Procurar o SEGUNDO calendário (o de agendamento) ou o que está visível após marcar "Sim"
        for (var i = 0; i < todosIcones.length; i++) {
            var icone = todosIcones[i];
            // Pegar o último visível (calendário de agendamento vem depois)
            if (icone.offsetParent !== null) {
                // Verificar se está na seção de agendamento (após o radio group)
                var parent = icone.closest('.col-md-3');
                if (parent) {
                    // Se encontrar radio group antes, pular (é o calendário dos 30 dias)
                    var hasRadioGroupBefore = parent.previousElementSibling;
                    if (hasRadioGroupBefore && hasRadioGroupBefore.querySelector('mat-radio-group')) {
                        iconeAgendamento = icone;
                    }
                }
            }
        }

        // Fallback: se não encontrar, usar o último visível
        if (!iconeAgendamento && todosIcones.length > 0) {
            for (var j = todosIcones.length - 1; j >= 0; j--) {
                if (todosIcones[j].offsetParent !== null) {
                    iconeAgendamento = todosIcones[j];
                    break;
                }
            }
        }

        if (iconeAgendamento) {
            var botao = iconeAgendamento.closest('button');
            if (botao) {
                botao.click();
                return true;
            }
        }
        return false;
        """

        calendario_aberto = driver.execute_script(script_abrir_calendario)
        if not calendario_aberto:
            return False

        time.sleep(0.5)

        # 9. SELECIONAR DATA NO CALENDÁRIO
        script_selecionar_data = f"""
        // Aguardar calendário estar visível
        var calendario = document.querySelector('mat-calendar');
        if (!calendario) return false;

        // Procurar célula com a data desejada
        var dia = {data_agendamento.day};
        var celulas = calendario.querySelectorAll('.mat-calendar-body-cell');

        for (var celula of celulas) {{
            var conteudo = celula.querySelector('.mat-calendar-body-cell-content');
            if (conteudo && parseInt(conteudo.textContent.trim()) === dia) {{
                // Verificar se não está disabled
                if (!celula.classList.contains('mat-calendar-body-disabled')) {{
                    conteudo.click();
                    return true;
                }}
            }}
        }}
        return false;
        """

        data_selecionada = driver.execute_script(script_selecionar_data)
        if not data_selecionada:
            return False

        time.sleep(0.5)

        # 10. SALVAR SEGUNDA MINUTA

        minuta_salva = _salvar_minuta(driver)
        if not minuta_salva:
            return False

        if log:
            _ = minuta_salva

        # 11. VOLTAR PARA LISTAGEM NOVAMENTE (para não interferir no fluxo seguinte)
        time.sleep(1)
        driver.execute_script(script_voltar)
        time.sleep(1)

        return True

    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD]  Erro ao criar minuta agendada: {e}')
        return False
