import logging
logger = logging.getLogger(__name__)

"""
SISB Processamento - Funções de processamento consolidadas
Refatoração do s.py seguindo padrões do projeto PjePlus
"""

import time
import os
import random
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import (
    criar_js_otimizado, safe_click, simulate_human_movement,
    aguardar_elemento, aguardar_e_clicar, escolher_opcao_sisbajud,
    extrair_protocolo, validar_numero_processo, formatar_valor_monetario,
    calcular_data_limite, log_sisbajud, registrar_erro_minuta,
    carregar_dados_processo, SISBAJUD_URLS, TIMEOUTS, SELECTORS
)

def minuta_bloqueio_refatorada(driver_sisbajud, dados_processo, driver_pje=None, driver_created=False, manter_driver_aberto=False):
    """
    Cria minuta de bloqueio no SISBAJUD - versão refatorada e otimizada.
    Agora inclui execução automática de juntada no PJE após criação da minuta.

    Args:
        driver_sisbajud: WebDriver do SISBAJUD
        dados_processo: Dados do processo extraídos (se None, carrega do arquivo dadosatuais.json)
        driver_pje: WebDriver do PJE (opcional) - se fornecido, executa juntada automática
        driver_created: Se o driver foi criado nesta função
        manter_driver_aberto: Se True, mantém o driver aberto em caso de erro para debug

    Returns:
        dict: Resultado da operação
    """
    try:
        log_sisbajud("=== INICIANDO MINUTA DE BLOQUEIO (REFATORADA) ===")

        # 1. VALIDAÇÃO DE DADOS (usando helper consolidado)
        from .helpers import _validar_dados
        dados_validos, numero_processo = _validar_dados(dados_processo)
        if not dados_validos:
            raise ValueError("Dados do processo inválidos ou não encontrados")
        
        # Garantir que dados_processo seja o objeto carregado
        if not dados_processo:
            dados_processo = carregar_dados_processo()
            if not dados_processo:
                raise ValueError("Não foi possível carregar dados do processo do arquivo")

        # 2. INJEÇÃO DO JAVASCRIPT OTIMIZADO
        driver_sisbajud.execute_script(criar_js_otimizado())
        log_sisbajud("JavaScript otimizado injetado")

        # 3. PREENCHIMENTO DOS CAMPOS PRINCIPAIS
        resultado_campos = _preencher_campos_principais(driver_sisbajud, dados_processo)
        if not resultado_campos['sucesso']:
            raise Exception(f"Falha no preenchimento de campos: {resultado_campos.get('erro', 'Erro desconhecido')}")

        # 4. PROCESSAMENTO DOS RÉUS
        resultado_reus = _processar_reus_otimizado(driver_sisbajud, dados_processo)
        if not resultado_reus['sucesso']:
            raise Exception(f"Falha no processamento de réus: {resultado_reus.get('erro', 'Erro desconhecido')}")

        # 5. CONFIGURAÇÃO DE VALOR (se disponível)
        _configurar_valor(driver_sisbajud, dados_processo)

        # 6. CONFIGURAÇÕES ADICIONAIS
        _configurar_opcoes_adicionais(driver_sisbajud, dados_processo)

        # 7. SALVAR MINUTA
        if not _salvar_minuta(driver_sisbajud):
            raise Exception("Falha ao salvar minuta")

        # 8. GERAR RELATÓRIO
        dados_relatorio = _gerar_relatorio_minuta(driver_sisbajud, dados_processo)

        # 9. EXTRAIR PROTOCOLO
        protocolo = extrair_protocolo(driver_sisbajud)

        # 10. EXECUTAR JUNTADA NO PJE (se driver_pje fornecido)
        juntada_executada = False
        if driver_pje:
            log_sisbajud("Executando juntada automática no PJE...")
            try:
                from SISB.helpers import _executar_juntada_pje
                # Determinar tipo de fluxo baseado nos dados (NEGATIVO/DESBLOQUEIO)
                tipo_fluxo = 'NEGATIVO'  # Default para minuta_bloqueio
                juntada_executada = _executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log=True)
                if juntada_executada:
                    log_sisbajud(" Juntada executada com sucesso no PJE")
                else:
                    log_sisbajud(" Juntada pode não ter sido executada corretamente")
            except Exception as e:
                log_sisbajud(f" Erro na execução da juntada: {e}")

        # 11. FINALIZAR
        _finalizar_minuta(driver_sisbajud, driver_pje, driver_created)

        log_sisbajud(" MINUTA DE BLOQUEIO CRIADA COM SUCESSO")

        return {
            'status': 'sucesso',
            'dados_minuta': {
                'protocolo': protocolo,
                'tipo': 'bloqueio',
                'repeticao': 'sim',
                'quantidade_reus': len(dados_processo.get('reu', [])),
                'salvo_em': 'clipboard.txt'
            },
            'juntada_executada': juntada_executada
        }

    except Exception as e:
        log_sisbajud(f" Falha na minuta de bloqueio: {e}", "ERROR")

        # Cleanup em caso de erro (apenas se não estiver em modo debug)
        if not manter_driver_aberto:
            try:
                if driver_created and driver_sisbajud:
                    driver_sisbajud.quit()
            except Exception as e:
                _ = e
        else:
            log_sisbajud(" DEBUG: Mantendo driver SISBAJUD aberto para inspeção do erro")

        return None

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
        from .minutas.processor import _preencher_campos_iniciais as _impl

        prazo_dias = 30  # Valor padrão
        data_limite = _impl(driver, dados_processo, prazo_dias)
        if data_limite:
            log_sisbajud(" Campos principais preenchidos com sucesso")
            return {'sucesso': True}

        log_sisbajud(" Falha no preenchimento: retorno vazio", "ERROR")
        return {'sucesso': False, 'erro': 'retorno vazio'}
    except Exception as e:
        log_sisbajud(f" Erro no preenchimento de campos: {e}", "ERROR")
        return {'sucesso': False, 'erro': str(e)}

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
        from .minutas.processor import _processar_reus_otimizado as _impl

        reus = dados_processo.get('reu', [])
        return _impl(driver, reus)
    except Exception as e:
        log_sisbajud(f" Erro no processamento de réus: {e}", "ERROR")
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
            log_sisbajud(" Conta-salário ativada")

    except Exception as e:
        log_sisbajud(f" Erro ao configurar opções adicionais: {e}")

def _salvar_minuta(driver):
    """Wrapper para SISB.minutas.processor._salvar_minuta."""
    from .minutas.processor import _salvar_minuta as _impl
    return _impl(driver)

def _gerar_relatorio_minuta(driver, dados_processo):
    """Wrapper para SISB.minutas.processor._gerar_relatorio_minuta."""
    numero_processo = None
    if dados_processo:
        numero = dados_processo.get('numero', [])
        if isinstance(numero, list) and len(numero) > 0:
            numero_processo = numero[0]
        elif isinstance(numero, str):
            numero_processo = numero

    from .minutas.processor import _gerar_relatorio_minuta as _impl
    return _impl(driver, numero_processo)


def _salvar_relatorios(dados_relatorio, numero_processo=None):
    """Salva os relatórios no clipboard.txt centralizado."""
    try:
        # Usar clipboard centralizado do PEC/anexos.py
        try:
            from PEC.anexos import salvar_conteudo_clipboard
            
            sucesso = salvar_conteudo_clipboard(
                conteudo=dados_relatorio,
                numero_processo=numero_processo or "SISBAJUD",
                tipo_conteudo="sisbajud",
                debug=True
            )
            
            if sucesso:
                log_sisbajud("✅ Relatório salvo no clipboard.txt centralizado")
            else:
                log_sisbajud("⚠️ Falha ao salvar no clipboard centralizado")
                
        except ImportError as e:
            log_sisbajud(f"⚠️ Não foi possível importar salvar_conteudo_clipboard: {e}")

        return dados_relatorio

    except Exception as e:
        log_sisbajud(f"❌ Erro ao salvar relatórios: {e}")
        return None

def _finalizar_minuta(driver_sisbajud, driver_pje, driver_created):
    """Finaliza a criação da minuta."""
    try:
        # Fechar driver se foi criado aqui
        if driver_created and driver_sisbajud:
            driver_sisbajud.quit()
            log_sisbajud(" Driver SISBAJUD fechado")

        # Retornar foco para PJE
        if driver_pje:
            try:
                driver_pje.switch_to.window(driver_pje.window_handles[-1])
                log_sisbajud(" Foco retornado para PJE")
            except Exception as e:
                log_sisbajud(f" Erro ao retornar foco para PJE: {e}")

    except Exception as e:
        log_sisbajud(f" Erro na finalização: {e}")



def _extrair_cpf_autor(dados_processo):
    """Extrai CPF/CNPJ do autor."""
    if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
        return dados_processo['autor'][0].get('cpfcnpj', '')
    elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
        return dados_processo['reu'][0].get('cpfcnpj', '')
    return ''

def _extrair_nome_autor(dados_processo):
    """Extrai nome do autor."""
    if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
        return dados_processo['autor'][0].get('nome', '')
    elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
        return dados_processo['reu'][0].get('nome', '')
    return ''


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
        ordem: Dict com 'sequencial', 'data', 'valor_bloquear', 'protocolo', 'linha_el'
        tipo_fluxo: 'POSITIVO' ou 'DESBLOQUEIO'
        log: Se deve fazer log
        valor_parcial: Se presente, faz transferência parcial com este valor (float)
        apenas_extrair: Se True, apenas abre /desdobrar, extrai dados e volta (sem processar)
    
    Returns:
        bool: True se processamento bem-sucedido
    """
    import time as time_module
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import StaleElementReferenceException

    _start_geral = time_module.time()
    
    try:

        # ===== VERIFICAR SE ESTÁ NA PÁGINA CORRETA =====
        # URL esperadas:
        # - https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes (lista de ordens - CORRETO)
        # - https://sisbajud.pdpj.jus.br/teimosinha (página de pesquisa - ERRADO)
        # - https://sisbajud.cnj.jus.br/minuta (minuta - ERRADO)
        
        url_atual = driver.current_url.lower()
        
        # Verificar se está em página inválida (não deve fazer back se estiver em /detalhes)
        if "/detalhes" not in url_atual and ("/minuta" in url_atual or url_atual.endswith("/teimosinha")):
            if log:
                logger.warning(f"[SISBAJUD] [ORDEM]  ALERTA: Página incorreta detectada!")
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
        except:
            # Fallback: buscar via CSS selector de tabela
            try:
                # Aguardar um pouco para garantir que a página carregou após voltar
                time_module.sleep(0.5)
                
                tabela = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
                )
                linhas = tabela.find_elements(By.CSS_SELECTOR, "tr.mat-row")
                linha_el = None
                
                for linha in linhas:
                    try:
                        cel_seq = linha.find_element(By.CSS_SELECTOR, "td.mat-cell.cdk-column-index")
                        seq_text = cel_seq.text.strip()
                        if seq_text == str(sequencial):
                            linha_el = linha
                            break
                    except:
                        continue
                
                if not linha_el:
                    return False
            except Exception as e_fallback:
                if log:
                    logger.error(f"[SISBAJUD]  Erro no fallback: {e_fallback}")
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
        except Exception as e:
            if log:
                logger.error(f"[SISBAJUD]  Erro ao clicar em menu: {e}")
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
                        break
                except:
                    continue
            
            if not detalhar_clicado:
                return False
        except:
            return False

        # ===== OTIMIZAÇÃO 4: AGUARDAR /DESDOBRAR COM TIMEOUT CURTO =====
        for tentativa in range(6):  # 6 tentativas × 0.5s = 3s máximo
            if "/desdobrar" in driver.current_url:
                break
            time_module.sleep(0.5)
        else:
            return False

        # ===== VERIFICAÇÃO CRÍTICA: VALIDAR VALOR BLOQUEADO =====
        time_module.sleep(0.5)  # Aguardar renderização dos cabeçalhos
        
        valor_esperado = ordem.get('valor_bloqueio_esperado', 0.0)
        if valor_esperado > 0:  # Só validar se soubermos o valor esperado
            try:
                # Usar função existente de extração de dados para validar
                from .helpers import extrair_dados_bloqueios_processados
                
                dados_validacao = extrair_dados_bloqueios_processados(
                    driver, 
                    log=False,  # Não fazer log detalhado na validação
                    protocolo_ordem=ordem.get('protocolo', 'N/A')
                )
                
                valor_total_encontrado = dados_validacao.get('total_geral', 0.0)
                
                # Se valor for zero ou muito diferente do esperado = ERRO DE BLOQUEIO
                if valor_total_encontrado < 0.01:
                    erro_msg = f"ERRO DE BLOQUEIO: Ordem {ordem.get('sequencial')} deveria ter R$ {valor_esperado:.2f} bloqueado mas está zerada (R$ 0,00)"
                    if log:
                        logger.error(f"[SISBAJUD] [ORDEM] {erro_msg}")
                    
                    # Atualizar entrada do relatório com erro
                    if '_relatorio' in ordem:
                        ordem['_relatorio']['status'] = 'erro'
                        ordem['_relatorio']['erro_msg'] = f"Deveria ter R$ {valor_esperado:.2f} mas está R$ 0,00 no sistema"
                    
                    # Sempre voltar quando detectar erro
                    if log:
                        logger.error(f"[SISBAJUD] [ORDEM]  Erro de bloqueio detectado, voltando...")
                    try:
                        driver.back()
                        time_module.sleep(0.5)
                    except Exception:
                        return False
                    
                    # RETORNAR FALSE para indicar erro (não sucesso)
                    return False
                    
            except Exception as e:
                # Se falhar a validação, continuar normalmente (evitar bloqueio por erro de leitura)
                _ = e

        # ===== SE APENAS EXTRAÇÃO: EXTRAIR DADOS E VOLTAR =====
        if apenas_extrair:
            try:
                # Extrair dados dos bloqueios
                from .helpers import extrair_dados_bloqueios_processados
                protocolo_ordem = ordem.get('protocolo', 'N/A')
                
                dados_ordem = extrair_dados_bloqueios_processados(driver, log, protocolo_ordem=protocolo_ordem)
                
                # Atualizar entrada do relatório com discriminação
                if '_relatorio' in ordem and dados_ordem:
                    ordem['_relatorio']['status'] = 'processado'
                    ordem['_relatorio']['discriminacao'] = dados_ordem
                
                # Voltar para lista de ordens
                driver.back()
                time_module.sleep(0.5)
                
                return True
                
            except Exception as e_ext:
                if log:
                    logger.error(f"[SISBAJUD] [ORDEM]  Erro ao extrair dados: {e_ext}")
                # Tentar voltar mesmo com erro
                try:
                    driver.back()
                    time_module.sleep(0.5)
                except Exception:
                    return False
                return False

        # ===== OTIMIZAÇÃO 5: SELEÇÃO ROBUSTA DE JUIZ =====
        time_module.sleep(0.8)  # Aguardar estabilização da página (AUMENTADO para SISBAJUD)
        
        juiz_selecionado = False
        try:
            # Localizar campo de juiz
            juiz_input = WebDriverWait(driver, 5).until(  # Timeout maior: 5s
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
            )
            
            # Limpar e digitar
            juiz_input.click()
            time_module.sleep(0.3)
            juiz_input.clear()
            time_module.sleep(0.3)
            juiz_input.send_keys("OTAVIO AUGUSTO")
            time_module.sleep(1.2)  # AUMENTADO: Aguardar autocomplete carregar (SISBAJUD sensível)

            # Buscar opções de autocomplete (SEM retry excessivo)
            try:
                opcoes = WebDriverWait(driver, 3).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
                )
            except:
                # Se falhar, aguardar mais e tentar UMA vez apenas
                time_module.sleep(1.0)
                try:
                    opcoes = driver.find_elements(By.CSS_SELECTOR, "mat-option[role='option']")
                except:
                    opcoes = []
            
            # Clicar na primeira opção com "OTAVIO"
            for opcao in opcoes:
                try:
                    texto = opcao.text.upper()
                    if "OTAVIO" in texto:
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
                except Exception:
                    juiz_selecionado = False

        except Exception as e:
            if log:
                logger.error(f"[SISBAJUD] [ORDEM]  Erro ao selecionar juiz: {e}")
                import traceback
                traceback.print_exc()

        # ===== OTIMIZAÇÃO 6: SELEÇÃO ROBUSTA DE AÇÃO =====
        acao_selecionada = False
        try:
            from .ordens.processor import _aplicar_acao_por_fluxo
            resultado_acao = _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=log, valor_parcial=valor_parcial)
            acao_selecionada = resultado_acao
            if not acao_selecionada:
                return False  # PARAR AQUI - sem ação selecionada não funciona
                
        except Exception as e:
            if log:
                logger.error(f"[SISBAJUD] [ORDEM]  Erro ao selecionar ação: {e}")
                import traceback
                traceback.print_exc()
            return False  # PARAR AQUI

        # ===== VERIFICAR SE SELEÇÕES FORAM FEITAS =====
        if not juiz_selecionado:
            if log:
                logger.warning(f"[SISBAJUD] [ORDEM]  ALERTA: Juiz não foi selecionado, mas continuando...")
        
        if not acao_selecionada:
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
            except Exception:
                btn_salvar = None
            
            # Seletor 2: por texto "Salvar"
            if not btn_salvar:
                try:
                    btn_salvar = driver.find_element(By.XPATH, "//button[contains(., 'Salvar')]")
                except Exception:
                    btn_salvar = None
            
            # Seletor 3: button.mat-fab[color='primary']
            if not btn_salvar:
                try:
                    btn_salvar = driver.find_element(By.CSS_SELECTOR, "button.mat-fab[color='primary']")
                except Exception:
                    btn_salvar = None
            
            if btn_salvar:
                safe_click(driver, btn_salvar, 'click')
                time_module.sleep(1.2)  # Aguardar modal aparecer (se POSITIVO)
        except Exception as e:
            if log:
                logger.error(f"[SISBAJUD]  Erro ao clicar Salvar: {e}")

        # ===== VERIFICAR SE MODAL ABRIU (APENAS PARA POSITIVO) =====
        if tipo_fluxo == "POSITIVO":
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "mat-select[formcontrolname='tipoCredito']"))
                )
            except Exception as e:
                _ = e

        # ===== OTIMIZAÇÃO 7: PREENCHIMENTO DE DADOS DE TRANSFERÊNCIA (USANDO FIX.UTILS) =====
        if tipo_fluxo == "POSITIVO":
            time_module.sleep(0.3)  # delay final para form render

            # Importar função do Fix (reutilização de código)
            try:
                from Fix.utils import preencher_campos_angular_material
            except ImportError:
                preencher_campos_angular_material = None
            
            if preencher_campos_angular_material:
                # Usar função reutilizável do Fix
                resultado = preencher_campos_angular_material(driver, {}, debug=log)
                
                # Verificar resultado
                sucesso = resultado and resultado.get('sucesso', False)
                agencia_final = resultado.get('campos_preenchidos', {}).get('input[formcontrolname="agencia"]', '') if resultado else ''

                if not (sucesso and agencia_final == '5905'):
                    if log:
                        logger.error(f"[SISBAJUD] [ORDEM] Erros: {resultado.get('erros', []) if resultado else []}")
                    return False  # PARAR AQUI
            else:
                # Fallback: usar script direto (compatibilidade)
                
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
                            
                            const opcoes = Array.from(document.querySelectorAll('mat-option[role="option"]'));
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
                            
                            const opcoesBanco = Array.from(document.querySelectorAll('mat-option[role="option"]'));
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
                })();
                """
                
                # Executar script e capturar resultado
                resultado = driver.execute_script(script_preencher)
                
                # Verificar resultado
                if not (resultado and resultado.get('agencia') == '5905'):
                    if log:
                        logger.error(f"[SISBAJUD] [ORDEM] Resultado: Tipo='{resultado.get('tipo') if resultado else 'ERRO'}', Banco='{resultado.get('banco') if resultado else 'ERRO'}', Agência='{resultado.get('agencia') if resultado else 'ERRO'}'")
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
                except Exception:
                    btn_confirmar = None
                
                # Seletor 2: button[color="primary"]
                if not btn_confirmar:
                    try:
                        btn_confirmar = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[color='primary']"))
                        )
                    except Exception:
                        btn_confirmar = None
                
                # Seletor 3: por texto
                if not btn_confirmar:
                    try:
                        btn_confirmar = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirmar')]"))
                        )
                    except Exception:
                        btn_confirmar = None
                
                if btn_confirmar:
                    safe_click(driver, btn_confirmar, 'click')
                    
            except Exception as e:
                if log:
                    logger.error(f"[SISBAJUD]  Erro ao clicar Confirmar: {e}")

        # ===== OTIMIZAÇÃO 8: AGUARDAR FECHAMENTO DO MODAL =====
        time_module.sleep(1.0)  # Aguardar modal fechar após confirmar
        
        # ===== OTIMIZAÇÃO 9: SALVAR COM CLIQUE RÁPIDO =====
        
        try:
            btn_salvar = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@class,'mat-fab')]//mat-icon[contains(@class,'fa-save')]//ancestor::button"))
            )
            safe_click(driver, btn_salvar, 'click')
        except Exception:
            btn_salvar = None

        # ===== OTIMIZAÇÃO 10: AGUARDAR PROCESSAMENTO MÍNIMO =====
        time_module.sleep(1.0)  # REDUZIDO de 2.0s para 1.0s

        # Verificar sucesso com timeout curto
        try:
            WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'mat-fab') and @title='Protocolar']"))
            )
        except Exception as e:
            _ = e

        return True

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro geral na ordem {ordem['sequencial']}: {e}")
        return False