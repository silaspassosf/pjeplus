import logging

logger = logging.getLogger(__name__)

"""
SISB Minutas - Processamento de reus
"""


def _processar_reus_otimizado(driver, reus):
    """
    Helper para processar reus de forma otimizada.
    """
    try:
        from ..utils import criar_js_otimizado

        if not reus:
            return {'sucesso': False, 'msg': 'Nenhum reu encontrado'}

        lista_reus_js = []
        for reu in reus:
            cpf_cnpj = reu.get('cpfcnpj', '')
            if cpf_cnpj:
                cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
                if len(cpf_cnpj_limpo) == 14:
                    cpf_cnpj_limpo = cpf_cnpj_limpo[:8]
                lista_reus_js.append({
                    'cpfcnpj': cpf_cnpj_limpo,
                    'nome': reu.get('nome', '')
                })

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
                    log.push('\n=== REU ' + (i+1) + '/' + reus.length + ' ===');
                    log.push('Adicionando: ' + reu.nome + ' (' + reu.cpfcnpj + ')');

                    let cpfInput = await esperarElemento('input[placeholder="CPF/CNPJ do reu/executado"]', 3000);
                    if (!cpfInput) {{
                        cpfInput = await esperarElemento('input.mat-input-element[cpfcnpjmask]', 2000);
                    }}
                    if (!cpfInput) {{
                        log.push('Campo CPF nao encontrado');
                        continue;
                    }}

                    cpfInput.focus();
                    cpfInput.value = '';
                    await new Promise(resolve => setTimeout(resolve, 400));

                    cpfInput.value = reu.cpfcnpj;
                    triggerEvent(cpfInput, 'input');
                    triggerEvent(cpfInput, 'change');

                    await new Promise(resolve => setTimeout(resolve, 800));

                    let btnAdicionar = document.querySelector('button.btn-adicionar.mat-mini-fab');
                    if (!btnAdicionar) {{
                        btnAdicionar = document.querySelector('button mat-icon.fa-plus-square');
                        if (btnAdicionar) btnAdicionar = btnAdicionar.closest('button');
                    }}

                    if (!btnAdicionar || btnAdicionar.disabled) {{
                        log.push('Botao adicionar nao disponivel');
                        continue;
                    }}

                    btnAdicionar.click();
                    log.push('Reu adicionado, aguardando processamento...');

                    await new Promise(resolve => setTimeout(resolve, 3000));

                    let tabelaLinhas = document.querySelectorAll('tr.mat-row');
                    if (tabelaLinhas.length > 0) {{
                        let ultimaLinha = tabelaLinhas[tabelaLinhas.length - 1];
                        let celulaRelacionamentos = ultimaLinha.querySelector('td.mat-column-qtdeRelacionamentos');
                        let celulaIdentificacao = ultimaLinha.querySelector('td.mat-column-identificacao');
                        
                        let nomeNaTabela = '';
                        if (celulaIdentificacao) {{
                            nomeNaTabela = celulaIdentificacao.textContent.toUpperCase();
                        }}
                        let emRecuperacao = nomeNaTabela.includes('RECUPERAÇÃO JUDICIAL') || nomeNaTabela.includes('RECUPERACAO JUDICIAL') || nomeNaTabela.includes('RECUPERCAO JUDICIAL');

                        if (celulaRelacionamentos) {{
                            let botaoRelacionamentos = celulaRelacionamentos.querySelector('button .mat-button-wrapper');
                            if (botaoRelacionamentos || emRecuperacao) {{
                                let qtde = botaoRelacionamentos ? botaoRelacionamentos.textContent.trim() : '0';

                                if (qtde === '0' || emRecuperacao) {{
                                    if (emRecuperacao) {{
                                        log.push('Reu em recuperacao judicial - removendo...');
                                    }} else {{
                                        log.push('Reu sem contas - removendo...');
                                    }}
                                    let botaoMenu = ultimaLinha.querySelector('button.mat-menu-trigger');
                                    if (botaoMenu) {{
                                        botaoMenu.click();
                                        await new Promise(resolve => setTimeout(resolve, 500));

                                        let botaoExcluir = document.querySelector('button.mat-menu-item mat-icon.fa-trash-alt');
                                        if (botaoExcluir) {{
                                            botaoExcluir.closest('button').click();
                                            log.push(emRecuperacao ? 'Reu removido (recuperacao judicial)' : 'Reu removido (0 contas)');
                                            reusRemovidos++;
                                            await new Promise(resolve => setTimeout(resolve, 800));
                                        }}
                                    }}
                                }} else {{
                                    log.push('Reu possui ' + qtde + ' conta(s) - mantido');
                                    reusAdicionados++;
                                }}
                            }}
                        }}
                    }}

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
            return {
                'sucesso': False,
                'msg': resultado_reus.get('msg', ''),
                'adicionados': adicionados,
                'removidos': removidos
            }

        return {'sucesso': False, 'msg': 'Falha no processamento de reus'}

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao processar reus: {e}')
        return {'sucesso': False, 'msg': str(e)}