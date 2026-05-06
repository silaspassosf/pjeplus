import logging
logger = logging.getLogger(__name__)

"""
SISBAJUD Ordens - Processamento de ordens
"""

import time
from datetime import datetime


def _carregar_dados_ordem():
    """
    Helper para carregar dados do processo para processamento de ordens.

    Returns:
        tuple: (dados_processo, numero_processo) ou (None, None) se erro
    """
    try:
        from ..utils import carregar_dados_processo

        # Carregar dados do arquivo
        dados_arquivo = carregar_dados_processo()
        if not dados_arquivo or not isinstance(dados_arquivo, dict):
            return None, None

        # Extrair número do processo
        numero_bruto = dados_arquivo.get('numero')
        if isinstance(numero_bruto, list) and len(numero_bruto) > 0:
            numero_processo = numero_bruto[0]
        elif isinstance(numero_bruto, str) and numero_bruto.strip():
            numero_processo = numero_bruto.strip()
        else:
            return None, None
        return dados_arquivo, numero_processo

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao carregar dados: {e}')
        return None, None


def _extrair_ordens_da_serie(driver, log=True):
    """
    Extrai ordens da página de detalhes da série.

    Args:
        driver: WebDriver do Selenium
        log: Se deve fazer log

    Returns:
        list: Lista de ordens com estrutura {'sequencial', 'data', 'valor_bloquear', 'protocolo', 'linha_el'}
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    ordens = []
    try:
        tabela = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
        )

        linhas = tabela.find_elements(By.CSS_SELECTOR, "tr.mat-row")
        meses = {
            "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
            "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
        }

        for linha in linhas:
            try:
                cols = linha.find_elements(By.CSS_SELECTOR, "td")
                if len(cols) < 6:
                    continue

                sequencial = int(cols[0].text.strip())
                data_txt = cols[2].text.strip()
                protocolo = cols[5].text.strip()

                # Extrair status da ordem (mas NÃO pular ainda - identificar bloqueios primeiro)
                situacao = ""
                try:
                    all_text = ' '.join([c.text for c in cols]).strip()
                    if 'Respondida com minuta' in all_text:
                        situacao = "Respondida com minuta"
                    elif 'Respondida' in all_text:
                        situacao = "Respondida"
                except Exception:
                    situacao = ""

                valor_txt = cols[4].text.strip()

                # Converter data
                data_ordem = None
                if "/" in data_txt:
                    partes = data_txt.split(",")
                    data_parte = partes[0].strip() if len(partes) > 0 else data_txt.strip()
                    data_split = data_parte.split("/")
                    if len(data_split) == 3:
                        try:
                            dia, mes, ano = map(int, data_split)
                            data_ordem = datetime(ano, mes, dia)
                        except Exception as e:
                            continue

                if not data_ordem:
                    continue

                # Converter valor
                try:
                    valor = float(valor_txt.replace("R$", "").replace("\u00a0", "").replace(".", "").replace(",", ".").strip())
                except Exception as e:
                    continue

                ordens.append({
                    "sequencial": sequencial,
                    "data": data_ordem,
                    "valor_bloquear": valor,
                    "protocolo": protocolo,
                    "situacao": situacao,  # Incluir status
                    "linha_el": linha
                })

            except Exception as e:
                if log:
                    logger.error(f"[SISBAJUD] Ignorando linha: erro inesperado - {e}")
                continue

        # Ordenar por data
        ordens.sort(key=lambda x: x["data"])
        return ordens

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD] Erro ao extrair ordens: {e}")
        return []


def _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=True, valor_parcial=None):
    """
    Seleciona a ação correta na página /desdobrar baseado no tipo de fluxo.
    (Implementação completa das linhas 2240-2465)
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from ..utils import safe_click
    
    try:
        # Determinar ação alvo conforme fluxo
        if tipo_fluxo == 'POSITIVO':
            if valor_parcial:
                acao_alvo = 'Transferir valor e desbloquear saldo remanescente'
            else:
                acao_alvo = 'Transferir valor'
        else:  # DESBLOQUEIO
            acao_alvo = 'Desbloquear valor'

        # Aguardar página carregar
        time.sleep(0.5)

        # Buscar todos os mat-selects (pode haver vários na página)
        selects = driver.find_elements(By.CSS_SELECTOR, "mat-select")
        
        if not selects:
            return False

        # Tentar cada dropdown até encontrar a ação
        for idx, select_element in enumerate(selects):
            try:
                # Verificar se o select está visível
                if not select_element.is_displayed():
                    continue
                
                # TÉCNICA DO A.PY: Clicar no parentElement.parentElement para abrir dropdown
                try:
                    # Tentar clicar no parent.parent (técnica a.py)
                    parent_element = driver.execute_script("return arguments[0].parentElement.parentElement;", select_element)
                    if parent_element:
                        safe_click(driver, parent_element, 'click')
                    else:
                        safe_click(driver, select_element, 'click')
                except:
                    # Fallback: clicar direto no elemento
                    safe_click(driver, select_element, 'click')
                
                time.sleep(0.8)  # Aguardar dropdown abrir
                
                # Aguardar opções aparecerem COM RETRY CONSERVADOR
                opcoes = None
                max_tentativas_opcoes = 2
                for tentativa_opcoes in range(max_tentativas_opcoes):
                    try:
                        opcoes = WebDriverWait(driver, 3.0).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
                        )
                        
                        if opcoes and len(opcoes) > 0:
                            break
                        else:
                            if tentativa_opcoes < max_tentativas_opcoes - 1:
                                time.sleep(1.5)
                                    
                    except Exception as e_wait:
                        if tentativa_opcoes < max_tentativas_opcoes - 1:
                            time.sleep(1.5)
                        else:
                            continue
                
                if not opcoes or len(opcoes) == 0:
                    # Fechar dropdown
                    try:
                        driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
                    except:
                        continue
                    time.sleep(0.3)
                    continue

                # LISTAR TODAS AS OPÇÕES PARA DEBUG
                # Iterar opções e verificar texto
                opcao_encontrada = False
                for opc_idx, opcao in enumerate(opcoes):
                    try:
                        texto_opcao = opcao.text.strip()
                        
                        # Para POSITIVO com valor parcial: buscar "remanescente"
                        if tipo_fluxo == 'POSITIVO' and valor_parcial is not None and 'remanescente' in texto_opcao.lower():
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.5)
                            
                            # Preencher valor parcial
                            try:
                                campo_valor = WebDriverWait(driver, 2).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Valor'][prefix='R$ ']"))
                                )
                                campo_valor.clear()
                                # Formatar valor: 258.98 -> "258,98"
                                valor_formatado = f"{valor_parcial:.2f}".replace('.', ',')
                                campo_valor.send_keys(valor_formatado)
                                return True
                            except Exception as e_valor:
                                if log:
                                    logger.error(f"[_aplicar_acao]    Erro ao preencher valor parcial: {e_valor}")
                                return False
                        
                        # Para POSITIVO: buscar "Transferir valor"
                        elif tipo_fluxo == 'POSITIVO' and texto_opcao == 'Transferir valor':
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.3)
                            return True
                        
                        # Para DESBLOQUEIO: buscar "Desbloquear valor"
                        elif tipo_fluxo == 'DESBLOQUEIO' and 'Desbloquear valor' in texto_opcao:
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.3)
                            return True
                            
                    except Exception as e_opcao:
                        if log:
                            logger.error(f"[_aplicar_acao]   Erro ao processar opção {opc_idx+1}: {e_opcao}")
                        continue

                # Nenhuma opção encontrada neste dropdown, fechar e prosseguir
                try:
                    driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.3)
                except:
                    continue
                        
            except Exception as e_dropdown:
                if log:
                    logger.error(f"[_aplicar_acao]  Erro ao processar dropdown #{idx+1}: {e_dropdown}")
                # Fechar dropdown para próxima tentativa
                try:
                    driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
                except:
                    continue
                time.sleep(0.3)
                continue

        # Se chegou aqui, não conseguiu encontrar a ação em nenhum dropdown
        return False

    except Exception as e:
        if log:
            logger.error(f"[_aplicar_acao]  Erro crítico: {e}")
            import traceback
            logger.exception("Erro detectado")
        return False


def _identificar_ordens_com_bloqueio(ordens, valor_total_bloqueado_serie=None, log=True):
    """
    Identifica ordens que geraram bloqueio usando lógica de diferença de valores.

    Args:
        ordens: Lista de ordens da série
        valor_total_bloqueado_serie: Valor total bloqueado da série (para fallback)
        log: Se deve fazer log

    Returns:
        list: Lista de ordens que têm bloqueio
    """
    bloqueios = []

    if not ordens:
        return bloqueios

    # 1. Detectar bloqueios pela diferença de valor entre ordens consecutivas
    for i in range(len(ordens) - 1):
        valor_atual = ordens[i]["valor_bloquear"]
        valor_posterior = ordens[i + 1]["valor_bloquear"]

        if valor_atual > valor_posterior:
            # Adicionar campo com valor esperado de bloqueio (diferença)
            ordem_com_bloqueio = ordens[i].copy()
            valor_bloqueio = valor_atual - valor_posterior
            ordem_com_bloqueio['valor_bloqueio_esperado'] = valor_bloqueio
            
            # NOVO: Pré-adicionar ao relatório (será atualizado no processamento)
            ordem_com_bloqueio['_relatorio'] = {
                'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
                'valor_esperado': valor_bloqueio,
                'status': 'pendente',  # pendente | processado | erro
                'discriminacao': None   # Será preenchido com dados por executado
            }
            
            bloqueios.append(ordem_com_bloqueio)

    # 2. Verificar última ordem usando diferença de valores
    if len(ordens) > 0:
        ultima_ordem = ordens[-1]
        valor_original_a_bloquear = ordens[0]["valor_bloquear"] if ordens else 0
        valor_efetivamente_bloqueado = valor_total_bloqueado_serie or 0
        valor_ultima_ordem = ultima_ordem["valor_bloquear"]
        diferenca_esperada = valor_original_a_bloquear - valor_efetivamente_bloqueado
        diferenca_absoluta = abs(diferenca_esperada - valor_ultima_ordem)

        if diferenca_absoluta > 0.01:  # Tolerância para arredondamento
            if ultima_ordem not in bloqueios:
                # Adicionar campo com valor esperado de bloqueio
                ordem_com_bloqueio = ultima_ordem.copy()
                ordem_com_bloqueio['valor_bloqueio_esperado'] = diferenca_esperada
                
                # NOVO: Pré-adicionar ao relatório (será atualizado no processamento)
                ordem_com_bloqueio['_relatorio'] = {
                    'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
                    'valor_esperado': diferenca_esperada,
                    'status': 'pendente',
                    'discriminacao': None
                }
                
                bloqueios.append(ordem_com_bloqueio)

    # 3. FALLBACK: Se série tem valor bloqueado mas nenhum bloqueio foi detectado
    if valor_total_bloqueado_serie and valor_total_bloqueado_serie > 0 and len(bloqueios) == 0 and len(ordens) > 0:
        ultima_ordem = ordens[-1]
        # Adicionar campo com valor esperado de bloqueio
        ordem_com_bloqueio = ultima_ordem.copy()
        ordem_com_bloqueio['valor_bloqueio_esperado'] = valor_total_bloqueado_serie
        
        # NOVO: Pré-adicionar ao relatório (será atualizado no processamento)
        ordem_com_bloqueio['_relatorio'] = {
            'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
            'valor_esperado': valor_total_bloqueado_serie,
            'status': 'pendente',
            'discriminacao': None
        }
        
        bloqueios.append(ordem_com_bloqueio)

    return bloqueios
