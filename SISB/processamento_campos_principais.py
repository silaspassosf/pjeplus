import logging
logger = logging.getLogger(__name__)

"""
SISB.processamento_campos_principais - Módulo de preenchimento de campos principais SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
"""

import time
from datetime import datetime, timedelta
from .utils import criar_js_otimizado, log_sisbajud
from .processamento_extracao import _extrair_cpf_autor, _extrair_nome_autor

def _preencher_campos_principais(driver, dados_processo):
    """
    Preenche os campos principais da minuta usando JavaScript otimizado.

    Args:
        driver: WebDriver do SISBAJUD
        dados_processo: Dados do processo

    Returns:
        dict: Resultado da operação
    """
    try:
        # Extrair dados necessários
        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        vara = dados_processo.get('sisbajud', {}).get('vara', '30006')
        numero_processo = dados_processo.get('numero', [''])[0]
        cpf_cnpj_autor = _extrair_cpf_autor(dados_processo)
        # Para o campo do autor, usar sempre CPF/CNPJ completo (sem cortar raiz de CNPJ)
        cpf_cnpj_autor_completo = ''.join(filter(str.isdigit, cpf_cnpj_autor))
        log_sisbajud(f"CPF/CNPJ autor extraído: '{cpf_cnpj_autor}' -> processado: '{cpf_cnpj_autor_completo}' (len: {len(cpf_cnpj_autor_completo)})")

        # VERIFICAÇÃO: Garantir que CPF/CNPJ tenha o tamanho correto
        if len(cpf_cnpj_autor_completo) == 11:
            log_sisbajud(f"✅ CPF válido: {cpf_cnpj_autor_completo} (11 dígitos)")
        elif len(cpf_cnpj_autor_completo) == 14:
            log_sisbajud(f"✅ CNPJ válido: {cpf_cnpj_autor_completo} (14 dígitos)")
        else:
            log_sisbajud(f"⚠️ CPF/CNPJ com tamanho inválido: {cpf_cnpj_autor_completo} ({len(cpf_cnpj_autor_completo)} dígitos)")

        nome_autor = _extrair_nome_autor(dados_processo)

        # Calcular data limite
        prazo_dias = 30  # Valor padrão
        data_fim = datetime.now() + timedelta(days=prazo_dias + 2)
        data_formatada = data_fim.strftime('%d/%m/%Y')

        # JavaScript para preenchimento completo
        script_preenchimento = rf"""
        {criar_js_otimizado()}

        async function preencherMinutaCompleta() {{
            let log = [];

            try {{
                // 1. JUIZ
                log.push('Preenchendo juiz...');
                let resultadoJuiz = await window.SISBAJUD.preencherCampo('input[placeholder*="Juiz"]', '{juiz}');
                if (!resultadoJuiz.sucesso) {{
                    return {{sucesso: false, erro: 'Juiz: ' + resultadoJuiz.erro}};
                }}

                // Aguardar e selecionar opção correspondente ao juiz preenchido
                await new Promise(resolve => setTimeout(resolve, 1000));
                let opcoesJuiz = document.querySelectorAll('span.mat-option-text');
                for (let opcao of opcoesJuiz) {{
                    try {{
                        if (opcao.textContent && opcao.textContent.toUpperCase().includes('{juiz}'.toUpperCase())) {{
                            opcao.click();
                            log.push('✅ Juiz selecionado: ' + opcao.textContent.trim());
                            break;
                        }}
                    }} catch(e) {{}}
                }}

                // 2. VARA
                log.push('Preenchendo vara...');
                let resultadoVara = await window.SISBAJUD.clicarBotao('mat-select[name*="varaJuizoSelect"]');
                if (!resultadoVara.sucesso) {{
                    return {{sucesso: false, erro: 'Vara click: ' + resultadoVara.erro}};
                }}

                await new Promise(resolve => setTimeout(resolve, 500));
                let opcoesVara = document.querySelectorAll('mat-option[role="option"]');
                for (let opcao of opcoesVara) {{
                    if (opcao.textContent.includes('{vara}')) {{
                        opcao.click();
                        log.push('✅ Vara selecionada');
                        break;
                    }}
                }}

                // 3. NÚMERO PROCESSO
                log.push('Preenchendo número processo...');
                let resultadoProcesso = await window.SISBAJUD.preencherCampo('input[placeholder="Número do Processo"]', '{numero_processo}');
                if (!resultadoProcesso.sucesso) {{
                    return {{sucesso: false, erro: 'Processo: ' + resultadoProcesso.erro}};
                }}

                // 4. TIPO AÇÃO
                log.push('Selecionando tipo ação...');
                let resultadoAcao = await window.SISBAJUD.clicarBotao('mat-select[name*="acao"]');
                if (!resultadoAcao.sucesso) {{
                    return {{sucesso: false, erro: 'Ação click: ' + resultadoAcao.erro}};
                }}

                await new Promise(resolve => setTimeout(resolve, 500));
                let opcoesAcao = document.querySelectorAll('mat-option[role="option"]');
                for (let opcao of opcoesAcao) {{
                    if (opcao.textContent.includes('Ação Trabalhista')) {{
                        opcao.click();
                        log.push('✅ Ação selecionada');
                        break;
                    }}
                }}

                // 5. CPF/CNPJ AUTOR
                log.push('Preenchendo CPF/CNPJ autor...');
                let cpfLimpo = '{cpf_cnpj_autor_completo}';
                log.push('Valor CPF/CNPJ autor (raw): ' + '{cpf_cnpj_autor}' + ' -> processado: ' + cpfLimpo + ' (len: ' + cpfLimpo.length + ')');

                // Tentar preencher diretamente o input do CPF (várias estratégias)
                function localizarCpfInput() {{
                    const selectors = [
                        'input[placeholder*="CPF"]',
                        'input[formcontrolname*="cpf"]',
                        'input[aria-label*="CPF"]',
                        'input[name*="cpf"]',
                        'input[id*="cpf"]',
                        'input[class*="cpf"]'
                    ];
                    for (let s of selectors) {{
                        let el = document.querySelector(s);
                        if (el) return el;
                    }}
                    // tentar inputs visíveis genéricos
                    const allInputs = Array.from(document.querySelectorAll('input'));
                    for (let inp of allInputs) {{
                        const lbl = (inp.getAttribute('placeholder') || inp.getAttribute('aria-label') || inp.name || inp.id || '').toLowerCase();
                        if (lbl.includes('cpf') || lbl.includes('cnpj')) return inp;
                    }}
                    return null;
                }}

                let cpfInput = localizarCpfInput();
                if (!cpfInput) {{
                    log.push('❌ Campo CPF autor não encontrado por seletores comuns');
                    return {{sucesso: false, erro: 'Campo CPF autor não encontrado'}};
                }}

                // Garantir foco e limpar
                try {{ cpfInput.focus(); }} catch(e) {{}}
                try {{ cpfInput.value = ''; cpfInput.setAttribute('value', ''); }} catch(e) {{}}
                await new Promise(r => setTimeout(r, 120));

                // Remover maxlength em cadeia (pai/ancestrais) se existir
                try {{
                    let el = cpfInput;
                    let depth = 0;
                    while (el && depth < 6) {{
                        try {{ el.removeAttribute && el.removeAttribute('maxlength'); el.maxLength = 100; }} catch(e) {{}}
                        el = el.parentElement; depth++;
                    }}
                }} catch(e) {{}}

                // Estratégia 1: usar o mesmo setter nativo que a.py usa (descriptor) e disparar eventos
                try {{
                    try {{
                        Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(cpfInput, cpfLimpo);
                    }} catch(e2) {{
                        // fallback para atribuição direta
                        cpfInput.value = cpfLimpo;
                    }}
                    try {{ cpfInput.setAttribute('value', cpfLimpo); }} catch(e) {{}}

                    // Disparar eventos semelhantes ao preencherInput de a.py
                    try {{ cpfInput.dispatchEvent(new Event('input', {{bubbles: true}})); }} catch(e) {{}}
                    try {{ cpfInput.dispatchEvent(new Event('change', {{bubbles: true}})); }} catch(e) {{}}
                    try {{ cpfInput.dispatchEvent(new Event('dateChange', {{bubbles: true}})); }} catch(e) {{}}
                    try {{ cpfInput.dispatchEvent(new Event('keyup', {{bubbles: true}})); }} catch(e) {{}}
                    // Simular Enter (keydown) para acionar buscas que a UI espera
                    try {{ cpfInput.dispatchEvent(new KeyboardEvent('keydown', {{keyCode:13, which:13, key:'Enter', bubbles:true}})); }} catch(e) {{}}
                    try {{ cpfInput.blur(); }} catch(e) {{}}
                }} catch(e) {{ log.push('Estratégia 1 falhou: ' + e); }}

                await new Promise(r => setTimeout(r, 220));
                let valorAtual = (cpfInput.value || '').replace(/\D/g, '');
                log.push('Valor no input após tentativa 1: ' + valorAtual + ' (len: ' + valorAtual.length + ')');

                // Estratégia 2: inserção por execCommand (quando disponível) — insere todo o texto de uma vez
                if (valorAtual.length !== cpfLimpo.length) {{
                    try {{
                        cpfInput.focus();
                        if (document.execCommand) {{
                            document.execCommand('selectAll', false, null);
                            document.execCommand('insertText', false, cpfLimpo);
                        }} else if (typeof InputEvent === 'function') {{
                            // fallback por digitação programática char a char
                            cpfInput.value = '';
                            for (let k = 0; k < cpfLimpo.length; k++) {{
                                const ch = cpfLimpo.charAt(k);
                                try {{ cpfInput.dispatchEvent(new KeyboardEvent('keydown', {{key: ch, bubbles: true}})); }} catch(e) {{}}
                                cpfInput.value = (cpfInput.value || '') + ch;
                                cpfInput.dispatchEvent(new Event('input', {{bubbles: true}}));
                                try {{ cpfInput.dispatchEvent(new KeyboardEvent('keyup', {{key: ch, bubbles: true}})); }} catch(e) {{}}
                                await new Promise(r => setTimeout(r, 25 + Math.random() * 40));
                            }}
                        }}
                    }} catch(e) {{ log.push('Estratégia 2 falhou: ' + e); }}
                    await new Promise(r => setTimeout(r, 220));
                    valorAtual = (cpfInput.value || '').replace(/\D/g, '');
                    log.push('Valor no input após tentativa 2: ' + valorAtual + ' (len: ' + valorAtual.length + ')');
                }}

                // Estratégia 3: tentar inserir diretamente no input interno (shadow DOM / wrapper)
                if (valorAtual.length !== cpfLimpo.length) {{
                    try {{
                        let inner = cpfInput.querySelector && cpfInput.querySelector('input');
                        if (!inner && cpfInput.shadowRoot) inner = cpfInput.shadowRoot.querySelector('input');
                        if (inner) {{
                            inner.focus();
                            inner.value = cpfLimpo;
                            inner.dispatchEvent(new Event('input', {{bubbles: true}}));
                            inner.dispatchEvent(new Event('change', {{bubbles: true}}));
                            valorAtual = (inner.value || '').replace(/\D/g, '');
                            log.push('Inseriu no input interno: ' + valorAtual + ' (len: ' + valorAtual.length + ')');
                            cpfInput = inner; // ajustar referência para checagens posteriores
                        }}
                    }} catch(e) {{ log.push('Estratégia 3 falhou: ' + e); }}
                    await new Promise(r => setTimeout(r, 220));
                }}

                // Último recurso: usar helper window.SISBAJUD.preencherCampo
                if ((cpfInput.value || '').replace(/\D/g, '').length !== cpfLimpo.length) {{
                    log.push('Digitação falhou, tentando window.SISBAJUD.preencherCampo...');
                    try {{
                        let resultadoCpf = await window.SISBAJUD.preencherCampo('input[placeholder*="CPF"]', cpfLimpo);
                        if (!resultadoCpf.sucesso) {{
                            // retornar erro com detalhes
                            return {{sucesso: false, erro: 'CPF: ' + resultadoCpf.erro + ' | valorAtual: ' + ((cpfInput.value||'').replace(/\D/g,''))}};
                        }}
                    }} catch(e) {{
                        log.push('Helper preencherCampo falhou: ' + e);
                        return {{sucesso: false, erro: 'Falha ao preencher CPF: ' + e}};
                    }}
                    await new Promise(r => setTimeout(r, 300));
                }}

                valorAtual = (cpfInput.value || '').replace(/\D/g, '');
                log.push('Valor final no input CPF: ' + valorAtual + ' (len: ' + valorAtual.length + ')');
                if (valorAtual.length !== cpfLimpo.length) {{
                    return {{sucesso: false, erro: 'CPF preenchido com tamanho incorreto: ' + valorAtual.length}};
                }}

                log.push('✅ CPF/CNPJ autor preenchido: ' + valorAtual);

                // 6. NOME AUTOR
                log.push('Preenchendo nome autor...');
                let resultadoNome = await window.SISBAJUD.preencherCampo('input[placeholder="Nome do autor/exequente da ação"]', '{nome_autor}');
                if (!resultadoNome.sucesso) {{
                    return {{sucesso: false, erro: 'Nome: ' + resultadoNome.erro}};
                }}

                // 7. TEIMOSINHA
                log.push('Selecionando teimosinha...');
                let radios = document.querySelectorAll('mat-radio-button');
                for (let radio of radios) {{
                    if (radio.textContent.includes('Repetir a ordem')) {{
                        let label = radio.querySelector('label');
                        if (label) {{
                            label.click();
                            log.push('✅ Teimosinha selecionada');
                            break;
                        }}
                    }}
                }}

                // 8. CALENDÁRIO
                log.push('Configurando calendário...');
                let dataFinal = await configurarCalendario('{data_formatada}');
                log.push('✅ Calendário configurado: ' + dataFinal);

                return {{
                    sucesso: true,
                    data_final: dataFinal,
                    log: log
                }};

            }} catch(e) {{
                return {{
                    sucesso: false,
                    erro: e.message,
                    log: log
                }};
            }}
        }}

        async function configurarCalendario(dataAlvo) {{
            // LÓGICA COMPLETA DO CALENDÁRIO - BASEADA NO SISB.PY
            try {{
                // Extrair dia, mês, ano da data alvo
                let partes = dataAlvo.split('/');
                let dia_d = parseInt(partes[0]);
                let mes_d = parseInt(partes[1]) - 1; // JavaScript usa 0-based
                let ano = parseInt(partes[2]);

                // Array de meses em português
                let meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                           'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

                // Abrir calendário
                let btnCalendario = await window.SISBAJUD.esperarElemento('button[aria-label="Open calendar"]', 3000);
                if (!btnCalendario) {{
                    return dataAlvo; // Fallback para data alvo se calendário não encontrado
                }}
                btnCalendario.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Abrir seleção mês/ano
                let btnMesAno = await window.SISBAJUD.esperarElemento('mat-calendar button[aria-label="Choose month and year"]', 3000);
                if (!btnMesAno) {{
                    return dataAlvo; // Fallback
                }}
                btnMesAno.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Selecionar ano
                let anoCell = await window.SISBAJUD.esperarElemento(`mat-calendar td[aria-label="${{ano}}"]`, 3000);
                if (!anoCell) {{
                    return dataAlvo; // Fallback
                }}
                anoCell.click();
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Selecionar mês (lógica exata sisb.py com loop)
                let mesEncontrado = false;
                let mesAtual = mes_d;

                while (mesAtual >= 0) {{
                    let mesStr = meses[mesAtual] + ' de ' + ano;
                    let mesCell = document.querySelector(`mat-calendar td[aria-label="${{mesStr}}"]`);
                    if (mesCell && !mesCell.getAttribute('aria-disabled')) {{
                        mesCell.click();
                        mesEncontrado = true;
                        break;
                    }}
                    mesAtual--;
                }}

                if (!mesEncontrado) {{
                    return dataAlvo; // Fallback
                }}
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Selecionar dia (lógica exata sisb.py com loop)
                let diaEncontrado = false;
                let diaAtual = dia_d;

                while (diaAtual > 0) {{
                    let mesFinalStr = meses[mesAtual] + ' de ' + ano;
                    let diaStr = diaAtual + ' de ' + mesFinalStr;
                    let diaCell = document.querySelector(`mat-calendar td[aria-label="${{diaStr}}"]`);
                    if (diaCell && !diaCell.getAttribute('aria-disabled')) {{
                        diaCell.click();
                        diaEncontrado = true;
                        break;
                    }}
                    diaAtual--;
                }}

                if (!diaEncontrado) {{
                    return dataAlvo; // Fallback
                }}

                // Retornar data efetivamente selecionada
                let dataFinal = diaAtual + '/' + (mesAtual + 1) + '/' + ano;
                return dataFinal;

            }} catch(e) {{
                // Em caso de erro, retornar data alvo original
                return dataAlvo;
            }}
        }}

        return preencherMinutaCompleta().then(arguments[arguments.length - 1]);
        """

        resultado = driver.execute_async_script(script_preenchimento)

        if resultado and resultado.get('sucesso'):
            log_sisbajud("✅ Campos principais preenchidos com sucesso")
            if resultado.get('log'):
                for msg in resultado['log']:
                    log_sisbajud(f"  {msg}")
            return {'sucesso': True}
        else:
            erro = resultado.get('erro', 'Erro desconhecido') if resultado else 'Script falhou'
            log_sisbajud(f"❌ Falha no preenchimento: {erro}", "ERROR")
            return {'sucesso': False, 'erro': erro}

    except Exception as e:
        log_sisbajud(f"❌ Erro no preenchimento de campos: {e}", "ERROR")
        return {'sucesso': False, 'erro': str(e)}