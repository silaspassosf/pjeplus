import json
import logging

logger = logging.getLogger(__name__)

"""
SISB Minutas - Processamento de reus
"""


def _processar_reus_otimizado(driver, reus, max_validos=10):
    """Helper para processar reus de forma otimizada."""
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

        reus_json = json.dumps(lista_reus_js, ensure_ascii=False)

        script_processar_reus = f"""
        {criar_js_otimizado()}

        async function processarTodosReus() {{
            let reus = {reus_json};
            let log = [];
            let reusAdicionados = 0;
            let reusRemovidos = 0;
            let maxValid = {max_validos};
            let processadosAte = 0;
            let reusValidos = [];
            let reusDescartados = [];

            const _toastLimite = () => {{
                const snacks = Array.from(document.querySelectorAll('simple-snack-bar, snack-bar-container, .mat-snack-bar-container, .toast-message'));
                for (const s of snacks) {{
                    const t = (s.innerText || s.textContent || '').toLowerCase();
                    if (t.includes('excesso') || t.includes('muitas requisi') || t.includes('limite') || t.includes('aguarde')) {{
                        return t;
                    }}
                }}
                return '';
            }};

            try {{
                for (let i = 0; i < reus.length; i++) {{
                    let reu = reus[i];
                    log.push('\\n=== REU ' + (i+1) + '/' + reus.length + ' ===');
                    log.push('Adicionando: ' + reu.nome + ' (' + reu.cpfcnpj + ')');

                    let cpfInput = await esperarElemento('input[placeholder="CPF/CNPJ do réu/executado"]', 3000);
                    if (!cpfInput) {{
                        cpfInput = await esperarElemento('input.mat-input-element[cpfcnpjmask]', 2000);
                    }}
                    if (!cpfInput) {{
                        log.push('Campo CPF nao encontrado');
                        continue;
                    }}

                    cpfInput.focus();
                    cpfInput.value = '';
                    await new Promise(resolve => setTimeout(resolve, 300));

                    cpfInput.value = reu.cpfcnpj;
                    triggerEvent(cpfInput, 'input');
                    triggerEvent(cpfInput, 'change');

                    await new Promise(resolve => setTimeout(resolve, 600));

                    let btnAdicionar = document.querySelector('button.btn-adicionar.mat-mini-fab');
                    if (!btnAdicionar) {{
                        btnAdicionar = document.querySelector('button mat-icon.fa-plus-square');
                        if (btnAdicionar) btnAdicionar = btnAdicionar.closest('button');
                    }}

                    if (!btnAdicionar || btnAdicionar.disabled) {{
                        log.push('Botao adicionar nao disponivel');
                        continue;
                    }}

                    let linhasAntes = document.querySelectorAll('tr.mat-row').length;
                    btnAdicionar.click();
                    log.push('Reu adicionado, aguardando processamento...');

                    // Aguardar a NOVA linha deste reu entrar na tabela (tbl.length > linhasAntes)
                    // com qtdeRelacionamentos preenchida (evita ler linha anterior e disparar rajada).
                    let novaLinhaPronta = false;
                    let tWait = Date.now();
                    while (Date.now() - tWait < 6000) {{
                        let tbl = document.querySelectorAll('tr.mat-row');
                        if (tbl.length > linhasAntes) {{
                            let cel = tbl[tbl.length - 1].querySelector('td.mat-column-qtdeRelacionamentos');
                            if (cel) {{
                                let btn = cel.querySelector('button .mat-button-wrapper');
                                let txt = btn ? btn.textContent.trim() : cel.textContent.trim();
                                if (txt && !txt.includes('...') && /\\d+/.test(txt)) {{
                                    novaLinhaPronta = true;
                                    break;
                                }}
                            }}
                        }} else {{
                            let msgLim = _toastLimite();
                            if (msgLim) {{
                                log.push('Aviso de limite/excesso detectado — aguardando 3s antes de retentar...');
                                await new Promise(resolve => setTimeout(resolve, 3000));
                                if (document.querySelectorAll('tr.mat-row').length === linhasAntes && btnAdicionar && !btnAdicionar.disabled) {{
                                    btnAdicionar.click();
                                    tWait = Date.now();
                                }}
                            }}
                        }}
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }}

                    let tabelaLinhas = document.querySelectorAll('tr.mat-row');
                    if (novaLinhaPronta && tabelaLinhas.length > linhasAntes) {{
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
                                    reusDescartados.push(reu.cpfcnpj);
                                    let botaoMenu = ultimaLinha.querySelector('button.mat-menu-trigger');
                                    if (botaoMenu) {{
                                        botaoMenu.click();
                                        await new Promise(resolve => setTimeout(resolve, 400));

                                        let botaoExcluir = document.querySelector('button.mat-menu-item mat-icon.fa-trash-alt');
                                        if (botaoExcluir) {{
                                            botaoExcluir.closest('button').click();
                                            log.push(emRecuperacao ? 'Reu removido (recuperacao judicial)' : 'Reu removido (0 contas)');
                                            reusRemovidos++;
                                            await new Promise(resolve => setTimeout(resolve, 600));
                                        }}
                                    }}
                                }} else {{
                                    log.push('Reu possui ' + qtde + ' conta(s) - mantido');
                                    reusAdicionados++;
                                    reusValidos.push(reu.cpfcnpj);
                                    if (reusAdicionados >= maxValid) {{
                                        log.push('Limite de ' + maxValid + ' reus validos atingido');
                                        processadosAte = i + 1;
                                        break;
                                    }}
                                }}
                            }}
                        }}
                    }} else {{
                        log.push('Nova linha nao confirmada para ' + reu.cpfcnpj + ' — prosseguindo sem ler linha anterior');
                    }}

                    if (i < reus.length - 1) {{
                        await new Promise(resolve => setTimeout(resolve, 600));
                    }}
                }}

                return {{
                    sucesso: true,
                    log: log,
                    adicionados: reusAdicionados,
                    removidos: reusRemovidos,
                    processados_ate: processadosAte || reus.length,
                    reus_validos: reusValidos,
                    reus_descartados: reusDescartados
                }};

            }} catch(e) {{
                return {{
                    sucesso: false,
                    msg: 'Erro: ' + e.message,
                    log: log,
                    adicionados: reusAdicionados,
                    removidos: reusRemovidos,
                    processados_ate: processadosAte || reus.length,
                    reus_validos: reusValidos,
                    reus_descartados: reusDescartados
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
                    if str(msg).strip():
                        print(f'[SISBAJUD][REUS] {str(msg).strip()}', flush=True)
                        logger.info(f'[SISBAJUD][REUS] {str(msg).strip()}')

            adicionados = resultado_reus.get('adicionados', 0)
            removidos = resultado_reus.get('removidos', 0)

            if resultado_reus.get('sucesso'):
                return {
                    'sucesso': True,
                    'adicionados': adicionados,
                    'removidos': removidos,
                    'processados_ate': resultado_reus.get('processados_ate', len(reus)),
                    'reus_validos': resultado_reus.get('reus_validos') or [],
                    'reus_descartados': resultado_reus.get('reus_descartados') or [],
                }
            return {
                'sucesso': False,
                'msg': resultado_reus.get('msg', ''),
                'adicionados': adicionados,
                'removidos': removidos,
                'processados_ate': resultado_reus.get('processados_ate', 0),
                'reus_validos': resultado_reus.get('reus_validos') or [],
                'reus_descartados': resultado_reus.get('reus_descartados') or [],
            }

        return {'sucesso': False, 'msg': 'Falha no processamento de reus'}

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao processar reus: {e}')
        return {'sucesso': False, 'msg': str(e)}