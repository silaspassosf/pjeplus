import logging
logger = logging.getLogger(__name__)

"""
SISB.processamento_campos_reus - Módulo de processamento de réus SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
"""

import time
from .utils import criar_js_otimizado, log_sisbajud

def _processar_reus_otimizado(driver, dados_processo):
    """
    Processa todos os réus de forma otimizada.

    Args:
        driver: WebDriver do SISBAJUD
        dados_processo: Dados do processo

    Returns:
        dict: Resultado da operação
    """
    try:
        reus = dados_processo.get('reu', [])
        if not reus:
            return {'sucesso': True, 'adicionados': 0, 'removidos': 0}

        log_sisbajud(f"Processando {len(reus)} réus...")

        # Preparar dados dos réus
        lista_reus_js = []
        for reu in reus:
            cpf_cnpj = reu.get('cpfcnpj', '')
            if cpf_cnpj:
                cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
                if len(cpf_cnpj_limpo) == 14:  # CNPJ
                    cpf_cnpj_limpo = cpf_cnpj_limpo[:8]  # Raiz do CNPJ
                lista_reus_js.append({
                    'cpfcnpj': cpf_cnpj_limpo,
                    'nome': reu.get('nome', '')
                })

        # JavaScript otimizado para processar todos os réus
        script_reus = f"""
        {criar_js_otimizado()}

        async function processarTodosReus() {{
            let reus = {lista_reus_js};
            let adicionados = 0;
            let removidos = 0;
            let log = [];

            try {{
                for (let i = 0; i < reus.length; i++) {{
                    let reu = reus[i];
                    log.push(`Réu ${{i+1}}/${{reus.length}}: ${{reu.nome}}`);

                    // Adicionar réu
                    let cpfInput = await window.SISBAJUD.esperarElemento('input[placeholder="CPF/CNPJ do réu/executado"]');
                    if (!cpfInput) {{
                        log.push('Campo CPF não encontrado');
                        continue;
                    }}

                    cpfInput.focus();
                    cpfInput.value = '';
                    cpfInput.value = reu.cpfcnpj;
                    window.SISBAJUD.triggerEvent(cpfInput, 'input');

                    await new Promise(resolve => setTimeout(resolve, 800));

                    // Clicar adicionar
                    let btnAdicionar = document.querySelector('button.btn-adicionar.mat-mini-fab');
                    if (btnAdicionar) {{
                        window.SISBAJUD.safeClick(btnAdicionar);
                        log.push('✅ Réu adicionado');
                        adicionados++;

                        // Aguardar processamento
                        await new Promise(resolve => setTimeout(resolve, 3000));

                        // Verificar contas
                        let linhas = document.querySelectorAll('tr.mat-row');
                        if (linhas.length > 0) {{
                            let ultimaLinha = linhas[linhas.length - 1];
                            let qtdeElement = ultimaLinha.querySelector('td.mat-column-qtdeRelacionamentos button .mat-button-wrapper');
                            if (qtdeElement) {{
                                let qtde = qtdeElement.textContent.trim();
                                if (qtde === '0') {{
                                    // Remover réu sem contas
                                    let btnMenu = ultimaLinha.querySelector('button.mat-menu-trigger');
                                    if (btnMenu) {{
                                        btnMenu.click();
                                        await new Promise(resolve => setTimeout(resolve, 500));
                                        let btnExcluir = document.querySelector('button.mat-menu-item mat-icon.fa-trash-alt');
                                        if (btnExcluir) {{
                                            btnExcluir.closest('button').click();
                                            log.push('✅ Réu removido (0 contas)');
                                            removidos++;
                                            adicionados--;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}

                    // Delay entre réus
                    if (i < reus.length - 1) {{
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }}
                }}

                return {{
                    sucesso: true,
                    adicionados: adicionados,
                    removidos: removidos,
                    log: log
                }};

            }} catch(e) {{
                return {{
                    sucesso: false,
                    erro: e.message,
                    adicionados: adicionados,
                    removidos: removidos,
                    log: log
                }};
            }}
        }}

        return processarTodosReus().then(arguments[arguments.length - 1]);
        """

        resultado = driver.execute_async_script(script_reus)

        if resultado and resultado.get('sucesso'):
            adicionados = resultado.get('adicionados', 0)
            removidos = resultado.get('removidos', 0)
            log_sisbajud(f"✅ Réus processados: {adicionados} adicionados, {removidos} removidos")

            if resultado.get('log'):
                for msg in resultado['log']:
                    log_sisbajud(f"  {msg}")

            return {
                'sucesso': True,
                'adicionados': adicionados,
                'removidos': removidos
            }
        else:
            erro = resultado.get('erro', 'Erro desconhecido') if resultado else 'Script falhou'
            log_sisbajud(f"❌ Falha no processamento de réus: {erro}", "ERROR")
            return {'sucesso': False, 'erro': erro}

    except Exception as e:
        log_sisbajud(f"❌ Erro no processamento de réus: {e}", "ERROR")
        return {'sucesso': False, 'erro': str(e)}

def _configurar_valor(driver, dados_processo):
    """Configura valor da dívida se disponível."""
    try:
        divida = dados_processo.get('divida', {})
        valor = divida.get('valor')
        data_divida = divida.get('data', '')

        if valor:
            log_sisbajud(f"Configurando valor: {valor}")

            # Criar overlay clicável
            script_valor = f"""
            var ancora = document.querySelector('div[class="label-valor-extenso"]');
            if (ancora && !document.getElementById('maisPJe_valor_execucao')) {{
                var span = document.createElement('span');
                span.id = 'maisPJe_valor_execucao';
                span.innerText = "Última atualização do processo: {valor} em {data_divida}";
                span.style = "color: white; background-color: slategray; padding: 10px; border-radius: 10px; cursor: pointer; font-weight: bold; margin: 5px 0;";
                span.onclick = function() {{
                    var input = document.querySelector('input[placeholder*="Valor aplicado a todos"]');
                    if (input) {{
                        input.value = "{valor}";
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }};
                ancora.appendChild(document.createElement('br'));
                ancora.appendChild(document.createElement('br'));
                ancora.appendChild(span);
            }}
            return true;
            """

            driver.execute_script(script_valor)
            time.sleep(1)

            # Clicar no overlay
            driver.execute_script("""
            var overlay = document.getElementById('maisPJe_valor_execucao');
            if (overlay) {
                overlay.click();
                return true;
            }
            return false;
            """)

            time.sleep(1)

            # Confirmar valor
            driver.execute_script("""
            var botaoConfirmar = document.querySelector('button.btn-adicionar.mat-mini-fab.mat-primary mat-icon.fa-check-square');
            if (botaoConfirmar) {
                botaoConfirmar.closest('button').click();
                return true;
            }
            return false;
            """)

            log_sisbajud("✅ Valor configurado")

    except Exception as e:
        log_sisbajud(f"⚠️ Erro ao configurar valor: {e}")

def _configurar_opcoes_adicionais(driver, dados_processo):
    """Configura opções adicionais como conta-salário."""
    try:
        # Conta-salário
        if dados_processo.get('sisbajud', {}).get('contasalario', '').lower() == 'sim':
            driver.execute_script("""
            var toggles = document.querySelectorAll('mat-slide-toggle label');
            for (var i = 0; i < toggles.length; i++) {
                toggles[i].click();
            }
            """)
            log_sisbajud("✅ Conta-salário ativada")

    except Exception as e:
        log_sisbajud(f"⚠️ Erro ao configurar opções adicionais: {e}")