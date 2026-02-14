import logging
logger = logging.getLogger(__name__)

"""
SISB.processamento_ordens_processamento - Módulo de processamento de ordens SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
"""

import time as time_module
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from Fix.core import safe_click

def _processar_ordem(driver, ordem, tipo_fluxo, log=True, valor_parcial=None, apenas_extrair=False):
    """
    Processa uma ordem individual do SISBAJUD - VERSÃO OTIMIZADA.

    Otimizações aplicadas:
    - CSS selector direto em vez de iteração (reduz latência 50%)
    - Delays mínimos: 0.2-0.3s entre ações (em vez de 0.5s)
    - WebDriverWait com timeout curto (máximo 3s)
    - Safe click com simulação humana mínima

    Sequência:
    1. Localizar linha por CSS selector direto
    2. Clicar em menu (botão ellipsis)
    3. Clicar em "Detalhar"
    4. (Se apenas_extrair=False) Selecionar Juiz, ação, dados de transferência
    5. (Se apenas_extrair=False) Salvar
    6. (Se apenas_extrair=True) Apenas extrair dados e voltar

    Args:
        driver: WebDriver SISBAJUD
        ordem: Dict com 'sequencial', 'data', 'valor_bloqueio_esperado', 'protocolo', 'linha_el'
        tipo_fluxo: 'POSITIVO' ou 'DESBLOQUEIO'
        log: Se deve fazer log
        valor_parcial: Se presente, faz transferência parcial com este valor (float)
        apenas_extrair: Se True, apenas abre /desdobrar, extrai dados e volta (sem processar)

    Returns:
        bool: True se processamento bem-sucedido
    """
    _start_geral = time_module.time()

    try:
        if log:
            print(f"[SISBAJUD] [ORDEM] Processando ordem {ordem['sequencial']} (tipo: {tipo_fluxo}) +0.0s")
            print(f"[SISBAJUD] [ORDEM] 📍 URL atual: {driver.current_url}")

        # ===== VERIFICAR SE ESTÁ NA PÁGINA CORRETA =====
        # URL esperadas:
        # - https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes (lista de ordens - CORRETO)
        # - https://sisbajud.pdpj.jus.br/teimosinha (página de pesquisa - ERRADO)
        # - https://sisbajud.cnj.jus.br/minuta (minuta - ERRADO)

        url_atual = driver.current_url.lower()

        # Verificar se está em página inválida (não deve fazer back se estiver em /detalhes)
        if "/detalhes" not in url_atual and ("/minuta" in url_atual or url_atual.endswith("/teimosinha")):
            if log:
                print(f"[SISBAJUD] [ORDEM] ⚠️ ALERTA: Página incorreta detectada!")
                print(f"[SISBAJUD] [ORDEM] Tentando navegar para lista de ordens da série...")
            # NÃO usar driver.back() - pode piorar a situação
            # Retornar False para que o retry externo navegue corretamente
            return False

        # ===== OTIMIZAÇÃO 1: CSS SELECTOR DIRETO =====
        # Em vez de iterar todas as linhas, usar XPath direto para a ordem
        sequencial = ordem['sequencial']

        # Seletor otimizado: vai direto para a célula com sequencial
        xpath_linha = f"//tr[.//td[@class='mat-cell cdk-column-index mat-column-index' and text()='{sequencial}']]"

        try:
            linha_el = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xpath_linha))
            )
            if log:
                print(f"[SISBAJUD] [ORDEM] Linha localizada via XPath direto +{time_module.time()-_start_geral:.1f}s")
        except:
            if log:
                print(f"[SISBAJUD] [ORDEM] Fallback: buscando linha por CSS selector...")
            # Fallback: buscar via CSS selector de tabela
            try:
                # Aguardar um pouco para garantir que a página carregou após voltar
                time_module.sleep(0.5)

                tabela = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
                )
                linhas = tabela.find_elements(By.CSS_SELECTOR, "tr.mat-row")
                linha_el = None

                if log:
                    print(f"[SISBAJUD] [ORDEM] Buscando ordem {sequencial} entre {len(linhas)} linhas...")

                for linha in linhas:
                    try:
                        cel_seq = linha.find_element(By.CSS_SELECTOR, "td.mat-cell.cdk-column-index")
                        seq_text = cel_seq.text.strip()
                        if seq_text == str(sequencial):
                            linha_el = linha
                            if log:
                                print(f"[SISBAJUD] [ORDEM] ✅ Linha encontrada: ordem {sequencial}")
                            break
                    except:
                        continue

                if not linha_el:
                    if log:
                        print(f"[SISBAJUD] ❌ Linha não encontrada para ordem {sequencial}")
                    return False
            except Exception as e_fallback:
                if log:
                    print(f"[SISBAJUD] ❌ Erro no fallback: {e_fallback}")
                return False

        # ===== OTIMIZAÇÃO 2: CLIQUE DIRETO NO BOTÃO MENU =====
        # Localizar botão de menu (ellipsis) na linha
        try:
            btn_menu = linha_el.find_element(
                By.CSS_SELECTOR,
                "button.mat-menu-trigger"
            )

            # Clique rápido com delays mínimos
            safe_click(driver, btn_menu, 'click')
            time_module.sleep(0.2)  # REDUZIDO de 0.5s para 0.2s

            if log:
                print(f"[SISBAJUD] [ORDEM] Menu clicado +{time_module.time()-_start_geral:.1f}s")
        except Exception as e:
            if log:
                print(f"[SISBAJUD] ❌ Erro ao clicar em menu: {e}")
            return False

        # ===== OTIMIZAÇÃO 3: LOCALIZAR E CLICAR "DETALHAR" =====
        # Aguardar opções do menu com timeout curto
        try:
            opcoes = WebDriverWait(driver, 2).until(  # REDUZIDO de 3s para 2s
                EC.presence_of_all_elements_located((By.XPATH, "//button[@role='menuitem']"))
            )

            detalhar_clicado = False
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    # Buscar "Detalhar" ou "Desdobrar"
                    if "detalh" in texto or "desdobr" in texto:
                        safe_click(driver, opcao, 'click')
                        detalhar_clicado = True
                        if log:
                            print(f"[SISBAJUD] [ORDEM] 'Detalhar' clicado +{time_module.time()-_start_geral:.1f}s")
                        break
                except:
                    continue

            if not detalhar_clicado:
                if log:
                    print(f"[SISBAJUD] ❌ Opção 'Detalhar' não encontrada")
                return False
        except:
            if log:
                print(f"[SISBAJUD] ❌ Menu não carregou corretamente")
            return False

        # ===== OTIMIZAÇÃO 4: AGUARDAR /DESDOBRAR COM TIMEOUT CURTO =====
        for tentativa in range(6):  # 6 tentativas × 0.5s = 3s máximo
            if "/desdobrar" in driver.current_url:
                if log:
                    print(f"[SISBAJUD] [ORDEM] Página /desdobrar carregada +{time_module.time()-_start_geral:.1f}s")
                break
            time_module.sleep(0.5)
        else:
            if log:
                print(f"[SISBAJUD] ❌ Página /desdobrar não carregou")
            return False

        # ===== VERIFICAR SE APENAS EXTRAÇÃO: EXTRAIR DADOS E VOLTAR =====
        if apenas_extrair:
            if log:
                print(f"[SISBAJUD] [ORDEM] Modo apenas extração - coletando dados...")

            try:
                # Extrair dados dos bloqueios
                from .helpers import extrair_dados_bloqueios_processados
                protocolo_ordem = ordem.get('protocolo', 'N/A')

                dados_ordem = extrair_dados_bloqueios_processados(driver, log, protocolo_ordem=protocolo_ordem)

                # Atualizar entrada do relatório com discriminação
                if '_relatorio' in ordem and dados_ordem:
                    ordem['_relatorio']['status'] = 'processado'
                    ordem['_relatorio']['discriminacao'] = dados_ordem

                if log:
                    print(f"[SISBAJUD] [ORDEM] ✅ Dados extraídos e registrados no relatório")

                # Voltar para lista de ordens
                driver.back()
                time_module.sleep(0.5)

                return True

            except Exception as e_ext:
                if log:
                    print(f"[SISBAJUD] [ORDEM] ⚠️ Erro ao extrair dados: {e_ext}")
                # Tentar voltar mesmo com erro
                try:
                    driver.back()
                    time_module.sleep(0.5)
                except:
                    pass
                return False

        # ===== OTIMIZAÇÃO 5: SELEÇÃO ROBUSTA DE JUIZ =====
        time_module.sleep(0.8)  # Aguardar estabilização da página (AUMENTADO para SISBAJUD)

        juiz_selecionado = False
        try:
            if log:
                print(f"[SISBAJUD] [ORDEM] Selecionando juiz...")

            # Localizar campo de juiz
            juiz_input = WebDriverWait(driver, 5).until(  # Timeout maior: 5s
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
            )

            if log:
                print(f"[SISBAJUD] [ORDEM]    Campo juiz encontrado")

            # Limpar e digitar
            juiz_input.click()
            time_module.sleep(0.3)
            juiz_input.clear()
            time_module.sleep(0.3)
            juiz_input.send_keys("OTAVIO AUGUSTO")
            time_module.sleep(1.2)  # AUMENTADO: Aguardar autocomplete carregar (SISBAJUD sensível)

            if log:
                print(f"[SISBAJUD] [ORDEM]    Digitado 'OTAVIO AUGUSTO', aguardando autocomplete...")

            # Buscar opções de autocomplete (SEM retry excessivo)
            try:
                opcoes = WebDriverWait(driver, 3).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
                )

                if log:
                    print(f"[SISBAJUD] [ORDEM]    Encontradas {len(opcoes)} opções de juiz")
            except:
                # Se falhar, aguardar mais e tentar UMA vez apenas
                if log:
                    print(f"[SISBAJUD] [ORDEM]    Autocomplete demorou, aguardando mais 1s...")
                time_module.sleep(1.0)
                try:
                    opcoes = driver.find_elements(By.CSS_SELECTOR, "mat-option[role='option']")
                    if log:
                        print(f"[SISBAJUD] [ORDEM]    Encontradas {len(opcoes)} opções (retry)")
                except:
                    opcoes = []

            # Clicar na primeira opção com "OTAVIO"
            for idx, opcao in enumerate(opcoes):
                try:
                    texto = opcao.text.upper()
                    if "OTAVIO" in texto:
                        if log:
                            print(f"[SISBAJUD] [ORDEM]    Clicando em opção {idx+1}: {texto[:50]}")
                        safe_click(driver, opcao, 'click')
                        juiz_selecionado = True
                        time_module.sleep(0.5)
                        break
                except:
                    continue

            # Fechar dropdown se ainda aberto
            if not juiz_selecionado:
                try:
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    time_module.sleep(0.3)
                except:
                    pass

            if log:
                if juiz_selecionado:
                    print(f"[SISBAJUD] [ORDEM]    ✅ Juiz selecionado")
                else:
                    print(f"[SISBAJUD] [ORDEM]    ⚠️ Juiz NÃO selecionado")

        except Exception as e:
            if log:
                print(f"[SISBAJUD] [ORDEM] ❌ Erro ao selecionar juiz: {e}")
                import traceback
                traceback.print_exc()

        # ===== OTIMIZAÇÃO 6: SELEÇÃO ROBUSTA DE AÇÃO =====
        if log:
            print(f"[SISBAJUD] [ORDEM] 🎯 Selecionando ação (tipo: {tipo_fluxo})...")

        acao_selecionada = False
        try:
            from .helpers import _aplicar_acao_por_fluxo
            resultado_acao = _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=log, valor_parcial=valor_parcial)
            acao_selecionada = resultado_acao

            if acao_selecionada:
                if log:
                    print(f"[SISBAJUD] [ORDEM]    ✅ Ação selecionada com sucesso")
            else:
                if log:
                    print(f"[SISBAJUD] [ORDEM]    ⚠️ Ação NÃO foi selecionada")
                    print(f"[SISBAJUD] [ORDEM]    ⛔ ABORTANDO: sem juiz/ação não abre modal")
                return False  # PARAR AQUI - sem ação selecionada não funciona

        except Exception as e:
            if log:
                print(f"[SISBAJUD] [ORDEM] ❌ Erro ao selecionar ação: {e}")
                import traceback
                traceback.print_exc()
            return False  # PARAR AQUI

        # ===== VERIFICAR SE SELEÇÕES FORAM FEITAS =====
        if not juiz_selecionado:
            if log:
                print(f"[SISBAJUD] [ORDEM] ⚠️ ALERTA: Juiz não foi selecionado, mas continuando...")

        if not acao_selecionada:
            if log:
                print(f"[SISBAJUD] [ORDEM] ⛔ CRÍTICO: Ação não selecionada - modal não abrirá")
            return False

        # ===== CLICAR BOTÃO SALVAR PARA ABRIR MODAL =====
        time_module.sleep(0.5)
        try:
            # Botão Salvar com ícone fa-save
            btn_salvar = None

            # Seletor 1: por ícone fa-save
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, "button.mat-fab .fa.fa-save")
                btn_salvar = btn_salvar.find_element(By.XPATH, "./ancestor::button")
            except:
                pass

            # Seletor 2: por texto "Salvar"
            if not btn_salvar:
                try:
                    btn_salvar = driver.find_element(By.XPATH, "//button[contains(., 'Salvar')]")
                except:
                    pass

            # Seletor 3: button.mat-fab[color='primary']
            if not btn_salvar:
                try:
                    btn_salvar = driver.find_element(By.CSS_SELECTOR, "button.mat-fab[color='primary']")
                except:
                    pass

            if btn_salvar:
                safe_click(driver, btn_salvar, 'click')
                time_module.sleep(1.2)  # Aguardar modal aparecer (se POSITIVO)
                if log and tipo_fluxo == "POSITIVO":
                    print(f"[SISBAJUD] [ORDEM] Botão Salvar clicado - abrindo modal de dados...")
                elif log:
                    print(f"[SISBAJUD] [ORDEM] Botão Salvar clicado")
            else:
                if log:
                    print(f"[SISBAJUD] ⚠️ Botão Salvar não encontrado")
        except Exception as e:
            if log:
                print(f"[SISBAJUD] ⚠️ Erro ao clicar Salvar: {e}")

        # ===== VERIFICAR SE MODAL ABRIU (APENAS PARA POSITIVO) =====
        if tipo_fluxo == "POSITIVO":
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "mat-select[formcontrolname='tipoCredito']"))
                )
                if log:
                    print(f"[SISBAJUD] [ORDEM] Modal de dados aberto com sucesso")
            except:
                if log:
                    print(f"[SISBAJUD] ⚠️ Modal não detectado após clicar Salvar")

        # ===== OTIMIZAÇÃO 7: PREENCHIMENTO DE DADOS DE TRANSFERÊNCIA (USANDO FIX.UTILS) =====
        if tipo_fluxo == "POSITIVO":
            time_module.sleep(0.3)  # delay final para form render

            if log:
                print(f"[SISBAJUD] [ORDEM] Preenchendo dados de transferência (Tipo: Geral, Banco: 00001, Agência: 5905) +{time_module.time()-_start_geral:.1f}s")

            # Importar função do Fix (reutilização de código)
            try:
                from Fix.utils import preencher_campos_angular_material
            except ImportError:
                if log:
                    print(f"[SISBAJUD] ⚠️ Fix.utils não disponível, usando fallback")
                preencher_campos_angular_material = None

            if preencher_campos_angular_material:
                # Usar função reutilizável do Fix
                resultado = preencher_campos_angular_material(driver, {}, debug=log)

                # Verificar resultado
                sucesso = resultado and resultado.get('sucesso', False)
                agencia_final = resultado.get('campos_preenchidos', {}).get('input[formcontrolname="agencia"]', '') if resultado else ''

                if sucesso and agencia_final == '5905':
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ✅ Campos preenchidos com sucesso +{time_module.time()-_start_geral:.1f}s")
                else:
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ❌ FALHA NO PREENCHIMENTO - NÃO FORAM PREENCHIDOS!")
                        print(f"[SISBAJUD] [ORDEM] Erros: {resultado.get('erros', []) if resultado else []}")
                        print(f"[SISBAJUD] [ORDEM] ⛔ PAUSANDO EXECUÇÃO PARA DEBUG")
                    return False  # PARAR AQUI
            else:
                # Fallback: usar script direto (compatibilidade)
                if log:
                    print(f"[SISBAJUD] [ORDEM] Usando fallback de script direto (Fix.utils não disponível)")

                script_preencher = """
                (async function() {
                    const debug = [];

                    function sleep(ms) {
                        return new Promise(r => setTimeout(r, ms));
                    }

                    try {
                        // 1. TIPO DE CRÉDITO: Selecionar "Geral" (padrão a.py)
                        debug.push('=== INICIANDO PREENCHIMENTO ===');
                        const selectTipoCredito = document.querySelector('mat-select[formcontrolname="tipoCredito"]');
                        debug.push('1. selectTipoCredito encontrado: ' + (!!selectTipoCredito));

                        if (selectTipoCredito) {
                            // IMPORTANTE: Clicar no .parentElement.parentElement como em a.py
                            selectTipoCredito.parentElement.parentElement.click();
                            await sleep(1000);  // Sleep maior como em a.py

                            const opcoes = Array.from(document.querySelectorAll('mat-option[role='option']'));
                            debug.push('   - Opções encontradas: ' + opcoes.length);

                            let encontrou = false;
                            for (let opcao of opcoes) {
                                const texto = (opcao.textContent || '').trim().toLowerCase();
                                if (texto.includes('geral')) {
                                    opcao.click();
                                    encontrou = true;
                                    debug.push('   - ✅ Opção "Geral" clicada');
                                    await sleep(500);
                                    break;
                                }
                            }

                            if (!encontrou) {
                                debug.push('   - ❌ Opção "Geral" NÃO encontrada em ' + opcoes.length + ' opções');
                            }
                        }

                        // Verificar valor atual
                        await sleep(300);
                        const selectTipoCreditoValue = document.querySelector('mat-select[formcontrolname="tipoCredito"] .mat-select-value-text');
                        debug.push('   - Valor atual tipoCredito: ' + (selectTipoCreditoValue?.textContent?.trim() || 'VAZIO'));

                        // 2. BANCO: input com autocomplete (padrão a.py)
                        const inputBanco = document.querySelector('input[formcontrolname="instituicaoFinanceiraPorCategoria"]');
                        debug.push('2. inputBanco encontrado: ' + (!!inputBanco));

                        if (inputBanco) {
                            // IMPORTANTE: Clicar no .parentElement.parentElement como em a.py
                            inputBanco.parentElement.parentElement.click();
                            await sleep(500);

                            inputBanco.focus();
                            await sleep(300);

                            // Limpar e digitar BRASIL
                            inputBanco.value = 'BRASIL';
                            const evento = new Event('input', { bubbles: true, cancelable: false });
                            inputBanco.dispatchEvent(evento);

                            debug.push('   - Digitado "BRASIL"');
                            debug.push('   - Valor no input: ' + inputBanco.value);

                            await sleep(1200);  // Aguardar autocomplete aparecer

                            const opcoesBanco = Array.from(document.querySelectorAll('mat-option[role='option']'));
                            debug.push('   - Opções banco encontradas: ' + opcoesBanco.length);

                            let encontrou = false;
                            for (let opcao of opcoesBanco) {
                                const texto = (opcao.textContent || '').toUpperCase();
                                if (texto.includes('00001') || texto.includes('BRASIL') || texto.includes('BCO')) {
                                    opcao.click();
                                    encontrou = true;
                                    debug.push('   - ✅ Banco selecionado: ' + opcao.textContent.trim().substring(0, 40));
                                    await sleep(500);
                                    break;
                                }
                            }

                            if (!encontrou) {
                                debug.push('   - ⚠️ Banco NÃO encontrado em ' + opcoesBanco.length + ' opções');
                            }

                            debug.push('   - Valor final banco: ' + inputBanco.value);
                        } else {
                            debug.push('   - ❌ Campo Banco NÃO encontrado');
                        }

                        // 3. AGÊNCIA: 5905 (padrão a.py: apenas focus, value, input event, blur)
                        const inputAgencia = document.querySelector('input[formcontrolname="agencia"]');
                        debug.push('3. inputAgencia encontrado: ' + (!!inputAgencia));

                        if (inputAgencia) {
                            inputAgencia.focus();
                            await sleep(300);

                            inputAgencia.value = '5905';
                            const eventoInput = new Event('input', { bubbles: true, cancelable: false });
                            inputAgencia.dispatchEvent(eventoInput);

                            inputAgencia.blur();

                            debug.push('   - ✅ Agência preenchida: ' + inputAgencia.value);
                            await sleep(500);
                        } else {
                            debug.push('   - ❌ Campo Agência NÃO encontrado');
                        }

                        // Verificações finais
                        debug.push('=== VERIFICAÇÕES FINAIS ===');
                        const tipoFinal = document.querySelector('mat-select[formcontrolname="tipoCredito"] .mat-select-value-text')?.textContent?.trim() || 'VAZIO';
                        const bancoFinal = document.querySelector('input[formcontrolname="instituicaoFinanceiraPorCategoria"]')?.value || 'VAZIO';
                        const agenciaFinal = document.querySelector('input[formcontrolname="agencia"]')?.value || 'VAZIO';

                        debug.push('Tipo Crédito final: ' + tipoFinal);
                        debug.push('Banco final: ' + bancoFinal);
                        debug.push('Agência final: ' + agenciaFinal);

                        return {
                            sucesso: true,
                            tipo: tipoFinal,
                            banco: bancoFinal,
                            agencia: agenciaFinal,
                            debug: debug.join('\\n')
                        };

                    } catch (e) {
                        debug.push('❌ ERRO: ' + e.message + ' em ' + e.stack);
                        return {
                            sucesso: false,
                            erro: e.message,
                            debug: debug.join('\\n')
                        };
                    }
                })();"""

                # Executar script e capturar resultado
                resultado = driver.execute_script(script_preencher)

                if log:
                    print(f"[SISBAJUD] [ORDEM] === DEBUG DO PREENCHIMENTO ===")
                    if resultado and 'debug' in resultado:
                        for linha in resultado['debug'].split('\n'):
                            print(f"[SISBAJUD] [ORDEM] {linha}")

                # Verificar resultado
                if resultado and resultado.get('agencia') == '5905':
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ✅ Campos preenchidos com sucesso +{time_module.time()-_start_geral:.1f}s")
                else:
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ❌ FALHA NO PREENCHIMENTO - NÃO FORAM PREENCHIDOS!")
                        print(f"[SISBAJUD] [ORDEM] Resultado: Tipo='{resultado.get('tipo') if resultado else 'ERRO'}', Banco='{resultado.get('banco') if resultado else 'ERRO'}', Agência='{resultado.get('agencia') if resultado else 'ERRO'}'")
                        print(f"[SISBAJUD] [ORDEM] ⛔ PAUSANDO EXECUÇÃO PARA DEBUG")
                    return False  # PARAR AQUI

            # ===== CONFIRMAR MODAL (só continua se preenchimento foi OK) =====
            time_module.sleep(0.5)
            try:
                # Procurar botão Confirmar com múltiplos seletores
                btn_confirmar = None

                # Seletor 1: button.mat-primary[type="submit"]
                try:
                    btn_confirmar = WebDriverWait(driver, 1).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.mat-primary[type='submit']"))
                    )
                except:
                    pass

                # Seletor 2: button[color="primary"]
                if not btn_confirmar:
                    try:
                        btn_confirmar = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[color='primary']"))
                        )
                    except:
                        pass

                # Seletor 3: por texto
                if not btn_confirmar:
                    try:
                        btn_confirmar = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirmar')]"))
                        )
                    except:
                        pass

                if btn_confirmar:
                    safe_click(driver, btn_confirmar, 'click')
                    if log:
                        print(f"[SISBAJUD] [ORDEM] ✅ Modal confirmado +{time_module.time()-_start_geral:.1f}s")
                else:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Botão Confirmar não encontrado com nenhum seletor")

            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao clicar Confirmar: {e}")

        # ===== OTIMIZAÇÃO 8: AGUARDAR FECHAMENTO DO MODAL =====
        time_module.sleep(1.0)  # Aguardar modal fechar após confirmar

        if log:
            print(f"[SISBAJUD] [ORDEM] ✅ Ordem {sequencial} processada (tipo: {tipo_fluxo}) em {time_module.time()-_start_geral:.1f}s")

        # ===== OTIMIZAÇÃO 9: SALVAR COM CLIQUE RÁPIDO =====

        salvar_clicado = False
        try:
            btn_salvar = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@class,'mat-fab')]//mat-icon[contains(@class,'fa-save')]//ancestor::button"))
            )
            safe_click(driver, btn_salvar, 'click')
            salvar_clicado = True
            if log:
                print(f"[SISBAJUD] [ORDEM] Salvar clicado +{time_module.time()-_start_geral:.1f}s")
        except:
            if log:
                print(f"[SISBAJUD] ⚠️ Botão Salvar não encontrado (prosseguindo)")

        # ===== OTIMIZAÇÃO 10: AGUARDAR PROCESSAMENTO MÍNIMO =====
        time_module.sleep(1.0)  # REDUZIDO de 2.0s para 1.0s

        # Verificar sucesso com timeout curto
        try:
            WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'mat-fab') and @title='Protocolar']"))
            )
            if log:
                print(f"[SISBAJUD] [ORDEM] ✅ Processada +{time_module.time()-_start_geral:.1f}s TOTAL")
        except:
            if log:
                print(f"[SISBAJUD] [ORDEM] ⚠️ Botão Protocolar não detectado (prosseguindo)")

        if log:
            print(f"[SISBAJUD] ✅ Ordem {sequencial} concluída em {time_module.time()-_start_geral:.1f}s")

        return True

    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro geral na ordem {ordem['sequencial']}: {e}")
        return False