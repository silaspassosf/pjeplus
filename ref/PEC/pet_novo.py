"""
PEC/pet.py - Processamento de Petições (PJe)
VERSÃO SIMPLIFICADA: Padrão p2b.py - regras simples (lista_regex, acao)
"""

import time
import re
import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any, Callable
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Ajuste de path para importações
sys.path.insert(0, str(Path(__file__).parent.parent))

from Fix.core import com_retry
from Fix.log import logger
from Fix.extracao import criar_gigs, extrair_pdf

# Import de atos/movimentos para análise
try:
    from atos.movimentos import analise_pet
except ImportError:
    analise_pet = None

# Import de atos/wrappers_ato para ato_gen (despacho genérico)
try:
    from atos.wrappers_ato import ato_instc, ato_inste, ato_gen
except ImportError:
    ato_instc = None
    ato_inste = None
    ato_gen = None

# Import de atos/wrappers_ato para ação de perícias
try:
    from atos.wrappers_ato import ato_laudo, ato_esc, ato_escliq, ato_datalocal
except ImportError:
    ato_laudo = None
    ato_esc = None
    ato_escliq = None
    ato_datalocal = None

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

ESCANINHO_URL = "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"

# ============================================================================
# FUNÇÕES DE PROGRESSO (padrão Prazo/p2b.py)
# ============================================================================

def carregar_progresso_pet() -> dict:
    """Carrega progresso salvo do PET."""
    try:
        from Fix.monitoramento_progresso_unificado import carregar_progresso_pet as _carregar
        progresso = _carregar()
        return progresso
    except Exception:
        return {}


def salvar_progresso_pet(progresso: dict) -> None:
    """Salva progresso do PET."""
    try:
        from Fix.monitoramento_progresso_unificado import salvar_progresso_pet as _salvar
        _salvar(progresso)
    except Exception as e:
        print(f'[PET_PROG] Erro ao salvar progresso: {e}')


def marcar_processo_executado_pet(processo_id: str, progresso: dict) -> None:
    """Marca processo como executado no progresso PET."""
    try:
        from Fix.monitoramento_progresso_unificado import marcar_processo_executado_unificado
        marcar_processo_executado_unificado('pet', processo_id, progresso, sucesso=True)
    except Exception as e:
        print(f'[PET_PROG] Erro ao marcar processo: {e}')


def processo_ja_executado_pet(processo_id: str, progresso: dict) -> bool:
    """Verifica se processo já foi executado no PET."""
    return processo_id in progresso.get('processos_executados', [])

# ============================================================================
# ESTRUTURA DE DADOS
# ============================================================================

class PeticaoLinha:
    """Representa uma linha da tabela de petições"""
    def __init__(self, indice: int, numero_processo: str, tipo_peticao: str,
                 descricao: str, tarefa: str, fase: str, data_juntada: str,
                 elemento_html: Optional[WebElement] = None, eh_perito: bool = False,
                 data_audiencia: Optional[str] = None, polo: Optional[str] = None):
        self.indice = indice
        self.numero_processo = numero_processo
        self.tipo_peticao = tipo_peticao
        self.descricao = descricao
        self.tarefa = tarefa
        self.fase = fase
        self.data_juntada = data_juntada
        self.elemento_html = elemento_html
        self.eh_perito = eh_perito  # ✅ Flag se é petição de perito (tem ícone de perito)
        self.data_audiencia = data_audiencia  # ✅ Data da audiência (ex: "10/03/2026 11:35")
        self.polo = polo  # ✅ NOVO: Polo da petição ('ativo' ou 'passivo')
    
    def __repr__(self):
        return f"PeticaoLinha({self.numero_processo} | {self.tipo_peticao} | {self.descricao[:30]}...)"


# ============================================================================
# NORMALIZAÇÃO E REGEX
# ============================================================================

def normalizar_texto(txt: str) -> str:
    """Remove acentos e converte para minúsculas"""
    import unicodedata
    txt = str(txt).lower()
    return ''.join(c for c in unicodedata.normalize('NFD', txt) 
                   if unicodedata.category(c) != 'Mn')


def gerar_regex_flexivel(termo: str) -> re.Pattern:
    """Gera regex flexível (padrão p2b.py)"""
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()
    partes = [re.escape(p) for p in palavras]
    regex = ''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()]*'
    return re.compile(rf"{regex}", re.IGNORECASE)


# ============================================================================
# NAVEGAÇÃO
# ============================================================================

def navegacao_inicial_pet(driver: WebDriver) -> bool:
    """Navega para escaninho e aplica filtros"""
    try:
        print(f"[PET_NAV] Navegando para {ESCANINHO_URL}...")
        driver.get(ESCANINHO_URL)
        time.sleep(2)
        
        print("[PET_NAV] Aplicando filtro de 50 processos...")
        if not aplicar_filtro_50(driver):
            print("[PET_NAV] ⚠️ Filtro 50 pode não ter sido aplicado")
        
        time.sleep(2)
        
        print("[PET_NAV] Reordenando coluna 'Tipo de Petição'...")
        if not reordenar_coluna_tipo_peticao(driver):
            print("[PET_NAV] ⚠️ Coluna pode não ter sido reordenada")
        
        time.sleep(1)
        print("[PET_NAV] ✅ Navegação inicial concluída")
        return True
        
    except Exception as e:
        logger.error(f"[PET_NAV] Erro: {e}")
        return False


def aplicar_filtro_50(driver: WebDriver) -> bool:
    """Aplica filtro de 50 processos por página"""
    try:
        print("[PET_FILTRO] Aplicando filtro de 50 processos...")
        
        def _selecionar():
            try:
                span_20 = driver.find_element(By.XPATH, 
                    "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']")
                
                mat_select = span_20.find_element(By.XPATH, "ancestor::mat-select[@role='combobox']")
                
                # Scroll e clique com JS
                driver.execute_script("arguments[0].scrollIntoView(true);", mat_select)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", mat_select)
                time.sleep(0.5)
                
                # Aguardar overlay
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                overlay = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                time.sleep(0.3)
                
                # Clicar em 50
                opcao_50 = overlay.find_element(By.XPATH, 
                    ".//mat-option[.//span[normalize-space(text())='50']]")
                driver.execute_script("arguments[0].click();", opcao_50)
                time.sleep(1)
                
                print('[PET_FILTRO] ✅ Filtro 50 aplicado')
                return True
            except Exception as e:
                print(f'[PET_FILTRO] ❌ Falha: {e}')
                return False
        
        from Fix.core import com_retry
        resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log=True)
        return resultado
        
    except Exception as e:
        logger.error(f"[PET_FILTRO] Erro: {e}")
        return False


def reordenar_coluna_tipo_peticao(driver: WebDriver) -> bool:
    """Clica na coluna 'Tipo de Petição' para reordenar"""
    try:
        seletores = [
            (By.XPATH, "//th[contains(text(), 'Tipo de Petição')]"),
            (By.XPATH, "//div[contains(text(), 'Tipo de Petição')]"),
            (By.CSS_SELECTOR, "th.mat-header-cell"),
        ]
        
        for by, seletor in seletores:
            try:
                elementos = driver.find_elements(by, seletor)
                for elem in elementos:
                    texto = elem.text.strip() if hasattr(elem, 'text') else ""
                    if "Tipo de Petição" in texto:
                        print("[PET_REORD] Encontrada coluna 'Tipo de Petição'")
                        driver.execute_script("arguments[0].click();", elem)
                        time.sleep(1)
                        return True
            except NoSuchElementException:
                continue
        
        print("[PET_REORD] ⚠️ Coluna 'Tipo de Petição' não encontrada")
        return False
        
    except Exception as e:
        logger.warning(f"[PET_REORD] Erro: {e}")
        return False


# ============================================================================
# VERIFICAÇÃO DE PERITO
# ============================================================================
# Nota: A verificação de ícone de perito e extração de data de audiência
# agora estão integradas na função extrair_tabela_peticoes()


# ============================================================================
# EXTRAÇÃO
# ============================================================================

def extrair_tabela_peticoes(driver: WebDriver) -> List[PeticaoLinha]:
    """
    Extrai tabela de petições com TODOS os dados:
    - Número do processo (TD[1])
    - Data de juntada (TD[3])
    - Tipo de petição (TD[4])
    - Descrição (TD[5])
    - Tarefa + Fase (TD[6])
    - Ícone de perito (i.fa-user.icone-perito)
    - Data de audiência (div.sobrescrito "Audiência em: ...")
    """
    try:
        print("[PET_EXTR] Aguardando tabela carregar...")
        time.sleep(2)
        
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.cdk-drag")
        print(f"[PET_EXTR] Encontradas {len(linhas)} linhas na tabela")
        
        peticoes = []
        for idx, linha in enumerate(linhas, 1):
            try:
                tds = linha.find_elements(By.TAG_NAME, "td")
                if not tds:
                    continue
                
                # Inicializar todos os campos
                numero_processo = ""
                tipo_peticao = ""
                descricao = ""
                tarefa = ""
                fase = ""
                data_juntada = ""
                eh_perito = False
                data_audiencia = None
                polo = None  # ✅ Novo campo para polo
                
                # ========== EXTRAÇÃO DE DADOS ==========
                
                # TD[1]: Número do processo
                if len(tds) > 1:
                    texto_td1 = tds[1].text.strip()
                    match_proc = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto_td1)
                    numero_processo = match_proc.group(0) if match_proc else ""
                
                # TD[3]: Data de juntada
                if len(tds) > 3:
                    texto_td3 = tds[3].text.strip()
                    data_juntada = texto_td3 if re.match(r'\d{2}/\d{2}/\d{4}', texto_td3) else ""
                
                # TD[4]: Tipo de petição
                if len(tds) > 4:
                    tipo_peticao = tds[4].text.strip()
                
                # TD[5]: Descrição
                if len(tds) > 5:
                    descricao = tds[5].text.strip()
                
                # TD[6]: Tarefa + Fase (separadas por "Fase:")
                if len(tds) > 6:
                    texto_td6 = tds[6].text.strip()
                    if "Fase:" in texto_td6:
                        partes = texto_td6.split("Fase:")
                        tarefa = partes[0].strip()
                        fase = partes[1].strip() if len(partes) > 1 else ""
                    else:
                        tarefa = texto_td6.strip()
                
                # ✅ NOVO: Extrair ícone de perito da linha
                try:
                    icone = linha.find_element(By.CSS_SELECTOR, "i.fa-user.icone-perito")
                    eh_perito = True
                except NoSuchElementException:
                    eh_perito = False
                
                # ✅ NOVO: Extrair data de audiência da linha
                try:
                    div_aud = linha.find_element(By.CSS_SELECTOR, "div.sobrescrito")
                    texto_aud = div_aud.text.strip()
                    if "Audiência em:" in texto_aud:
                        data_audiencia = texto_aud.split("Audiência em:")[-1].strip()
                except NoSuchElementException:
                    data_audiencia = None
                
                # ✅ NOVO: Extrair polo (ativo/passivo) da linha
                try:
                    icone_ativo = linha.find_element(By.CSS_SELECTOR, "i.icone-polo-ativo")
                    polo = "ativo"  # Verde
                except NoSuchElementException:
                    try:
                        icone_passivo = linha.find_element(By.CSS_SELECTOR, "i.icone-polo-passivo")
                        polo = "passivo"  # Laranja
                    except NoSuchElementException:
                        polo = None
                
                # ========== CRIAR OBJETO ==========
                if numero_processo:
                    peticao = PeticaoLinha(
                        indice=idx,
                        numero_processo=numero_processo,
                        tipo_peticao=tipo_peticao,
                        descricao=descricao,
                        tarefa=tarefa,
                        fase=fase,
                        data_juntada=data_juntada,
                        elemento_html=linha,
                        eh_perito=eh_perito,
                        data_audiencia=data_audiencia,
                        polo=polo  # ✅ Novo campo
                    )
                    peticoes.append(peticao)
                    
                    # Log com emojis indicativos
                    icone_str = "‍⚖️" if eh_perito else "  "
                    aud_str = f" {data_audiencia}" if data_audiencia else ""
                    polo_str = "🟢" if polo == "ativo" else ("🟠" if polo == "passivo" else "⚪")
                    print(f"[PET_EXTR] {idx}. {numero_processo} | {tipo_peticao[:20]} {icone_str} {aud_str} {polo_str}")

                
            except Exception as e:
                logger.warning(f"[PET_EXTR] Erro na linha {idx}: {e}")
                continue
        
        print(f"[PET_EXTR] ✅ {len(peticoes)} petições extraídas")
        return peticoes
        
    except Exception as e:
        logger.error(f"[PET_EXTR] Erro: {e}")
        return []


# ============================================================================
# REGRAS E AÇÕES (PADRÃO P2B.PY)
# ============================================================================

def acao_apagar(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Executa ação de apagar petição"""
    try:
        time.sleep(0.5)
        
        # Localizar linha
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.cdk-drag")
        linha_encontrada = None
        
        for linha in linhas:
            tds = linha.find_elements(By.TAG_NAME, "td")
            if len(tds) > 1:
                if peticao.numero_processo in tds[1].text.strip():
                    linha_encontrada = linha
                    break
        
        if not linha_encontrada:
            logger.warning(f"[PET_APAG] Linha não encontrada: {peticao.numero_processo}")
            return False
        
        # Clicar trash
        try:
            trash_icon = linha_encontrada.find_element(By.CSS_SELECTOR, "i.fa-trash-alt")
        except NoSuchElementException:
            logger.warning(f"[PET_APAG] Trash não encontrado: {peticao.numero_processo}")
            return False
        
        driver.execute_script("arguments[0].click();", trash_icon)
        time.sleep(0.5)
        
        # Confirmar com SPACE
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.SPACE)
        time.sleep(1)
        
        logger.info(f"[PET_APAG] ✅ Apagada: {peticao.numero_processo}")
        return True
        
    except Exception as e:
        logger.error(f"[PET_APAG] Erro: {e}")
        return False


def acao_pericias_com_data(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """
    Ação composta para Indicação de Data de Realização:
    1. Chama criar_gigs(driver, "1,xs audx") para extrair GIGs
    2. Em seguida, chama ato_datalocal para criar despacho
    Segue o padrão de p2b.py onde ações podem chamar múltiplas funções em sequência.
    """
    try:
        print(f"[PET_ACAO] Iniciando ação composta para {peticao.numero_processo}")
        
        # Ação 1: criar_gigs
        print(f"[PET_ACAO]   1. Executando criar_gigs(driver, '1,xs audx')...")
        try:
            resultado_gigs = criar_gigs(driver, "1,xs audx")
            print(f"[PET_ACAO]      ✅ criar_gigs executado")
        except Exception as e:
            print(f"[PET_ACAO]      ⚠️ criar_gigs falhou: {e}")
            resultado_gigs = False
        
        time.sleep(0.5)
        
        # Ação 2: ato_datalocal
        print(f"[PET_ACAO]   2. Executando ato_datalocal...")
        try:
            resultado_ato = ato_datalocal(driver, peticao) if ato_datalocal else False
            print(f"[PET_ACAO]      ✅ ato_datalocal executado")
            return resultado_ato
        except Exception as e:
            print(f"[PET_ACAO]      ⚠️ ato_datalocal falhou: {e}")
            return False
            
    except Exception as e:
        logger.error(f"[PET_ACAO] Erro em acao_pericias_com_data: {e}")
        return False


def acao_gigs(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """
    Ação genérica para GIGS: analisa descrição e chama criar_gigs com parâmetros apropriados.
    Formato: criar_gigs(driver, prazo, observacao)
    - Se contém "concordancia": usa criar_gigs(driver, "1", "Silvia homologacao de calculos")
    - Se contém "comprovante" ou "deposito": usa criar_gigs(driver, "1", "Bruna Liberacao")
    """
    try:
        texto_normalizado = normalizar_texto(peticao.descricao)
        print(f"[PET_ACAO] Iniciando ação GIGS para {peticao.numero_processo}")
        
        # Decidir parâmetros baseado na descrição
        if re.search(r'concordancia', texto_normalizado):
            prazo = "1"
            observacao = "Silvia homologacao de calculos"
            tipo = "Homologação"
        elif re.search(r'comprovante|deposito', texto_normalizado):
            prazo = "1"
            observacao = "Bruna Liberacao"
            tipo = "Liberação"
        else:
            print(f"[PET_ACAO]      ⚠️ Descrição não corresponde a nenhum padrão GIGS")
            return False
        
        print(f"[PET_ACAO]   [{tipo}] Executando criar_gigs(driver, '{prazo}', '{observacao}')...")
        try:
            resultado = criar_gigs(driver, prazo, observacao)
            print(f"[PET_ACAO]      ✅ criar_gigs executado com sucesso")
            return resultado
        except Exception as e:
            print(f"[PET_ACAO]      ⚠️ criar_gigs falhou: {e}")
            return False
            
    except Exception as e:
        logger.error(f"[PET_ACAO] Erro em acao_gigs: {e}")
        return False


def criar_gigs_1_xs_aud(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Wrapper para criar_gigs(driver, '1', 'xs aud')"""
    try:
        print(f"[PET_ACAO] Criando GIGS: 1,xs aud")
        resultado = criar_gigs(driver, "1", "xs aud")
        if resultado:
            print(f"[PET_ACAO]   ✅ GIGS criado")
        else:
            print(f"[PET_ACAO]   ⚠️ Falha ao criar GIGS")
        return resultado
    except Exception as e:
        print(f"[PET_ACAO]   ❌ Erro: {e}")
        return False


def cris_gigs_minus1_xs_pec(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Wrapper para criar_gigs(driver, '-1', 'xs pec') para CAGED"""
    try:
        print(f"[PET_ACAO] Criando GIGS: -1, xs pec")
        resultado = criar_gigs(driver, "-1", "xs pec")
        if resultado:
            print(f"[PET_ACAO]   ✅ GIGS criado")
        else:
            print(f"[PET_ACAO]   ⚠️ Falha ao criar GIGS")
        return resultado
    except Exception as e:
        print(f"[PET_ACAO]   ❌ Erro: {e}")
        return False


def padrao_liq_acao(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """
    Ação para Impugnação (Liquidação):
    1. Chama padrao_liq() via API para verificar condições
    2. Se apenas_uma_com_advogado=True E tem_perito=False → retorna True (deixa tupla executar ato_concor)
    3. Caso contrário → retorna False (não executa ato_concor)
    
    Condição para executar ato_concor:
    - Exatamente 1 reclamada com advogado
    - NÃO tem perito Rogerio
    """
    try:
        print(f"[PET_ACAO] Verificando condições de Impugnação (padrao_liq)")
        
        # Obter dados do processo via API
        from Fix.variaveis import session_from_driver, PjeApiClient, padrao_liq
        
        sess, trt_host = session_from_driver(driver)
        client = PjeApiClient(sess, trt_host)
        
        # Extrair ID do processo (usar numero_processo da petição)
        id_processo = peticao.numero_processo
        
        resultado = padrao_liq(client, id_processo)
        
        apenas_uma = resultado.get('apenas_uma_com_advogado', False)
        tem_perito = resultado.get('tem_perito', False)
        
        print(f"[PET_ACAO]   apenas_uma_com_advogado: {apenas_uma}")
        print(f"[PET_ACAO]   tem_perito: {tem_perito}")
        
        # Condição: apenas_uma_com_advogado=True E tem_perito=False
        deve_executar_concor = apenas_uma and not tem_perito
        
        if deve_executar_concor:
            print(f"[PET_ACAO]   ✅ Condição atendida - executará ato_concor")
            return True
        else:
            print(f"[PET_ACAO]   ⚠️ Condição NÃO atendida - NÃO executará ato_concor")
            return False
            
    except Exception as e:
        print(f"[PET_ACAO]   ❌ Erro em padrao_liq_acao: {e}")
        return False


def definir_regras() -> Dict[str, List[Tuple[str, List, Callable]]]:
    """
    Define 5 REGRAS separadas:
    - REGRA 1: APAGAR (5 hipóteses)
    - REGRA 2: RECURSO (suas próprias hipóteses)
    - REGRA 3: PERÍCIAS (suas próprias hipóteses)
    
    Cada regra possui suas hipóteses com padrões e ação associada.
    """
    
    regra_apagar_hipoteses = [
        # HIPÓTESE 1: Razões Finais + Carta Convite
        (
            "Razões Finais / Carta Convite",
            [
                lambda txt: (gerar_regex_flexivel('razões finais').search(txt) or 
                           gerar_regex_flexivel('carta convite').search(txt)),
                lambda txt: (gerar_regex_flexivel('razões finais').search(txt) or 
                           gerar_regex_flexivel('carta convite').search(txt)),
            ]
        ),
        # HIPÓTESE 2: Réplica em Conhecimento
        (
            "Réplica em Conhecimento",
            [
                gerar_regex_flexivel('réplica'),
                gerar_regex_flexivel('réplica'),
                gerar_regex_flexivel('conhecimento'),
            ]
        ),
        # HIPÓTESE 3: Acordo (apenas tipos específicos: Contestação, Habilitação, Procuração, Carta de preposição, Substabelecimento)
        (
            "Acordo",
            [
                gerar_regex_flexivel('aguardando cumprimento de acordo'),  # Tarefa
                lambda txt: (gerar_regex_flexivel('contestação').search(txt) or
                           gerar_regex_flexivel('habilitação').search(txt) or
                           gerar_regex_flexivel('procuração').search(txt) or
                           gerar_regex_flexivel('carta de preposição').search(txt) or
                           gerar_regex_flexivel('substabelecimento').search(txt)),  # Tipo de petição
            ]
        ),
        # HIPÓTESE 4: Manifestação + Carta de Preposição / Substabelecimento
        (
            "Manifestação - Carta/Substabelecimento",
            [
                gerar_regex_flexivel('manifestação'),
                lambda txt: (gerar_regex_flexivel('carta de preposição').search(txt) or
                           gerar_regex_flexivel('substabelecimento').search(txt)),
            ]
        ),
        # HIPÓTESE 5: Triagem Inicial (apenas tarefa)
        (
            "Triagem Inicial",
            [
                gerar_regex_flexivel('triagem inicial'),
            ]
        ),
    ]
    
    regra_recurso_hipoteses = [
        # HIPÓTESE 1: Agravo de Instrumento + Fase Conhecimento
        (
            "Agravo de Instrumento - Conhecimento",
            [
                gerar_regex_flexivel('agravo de instrumento'),
                gerar_regex_flexivel('conhecimento'),
            ]
        ),
        # HIPÓTESE 2: Agravo de Instrumento + Fase Liquidação/Execução
        (
            "Agravo de Instrumento - Liquidação/Execução",
            [
                gerar_regex_flexivel('agravo de instrumento'),
                lambda txt: (gerar_regex_flexivel('liquidação').search(txt) or 
                           gerar_regex_flexivel('execução').search(txt)),
            ]
        ),
    ]
    
    regra_pericias_hipoteses = [
        # HIPÓTESE 1: Esclarecimentos ao Laudo + Fase Conhecimento (MAIS ESPECÍFICA - TESTADA PRIMEIRA)
        # Se tem "esclarecimentos" E "conhecimento" → ato_esc
        (
            "Esclarecimentos ao Laudo - Conhecimento",
            [
                gerar_regex_flexivel('esclarecimentos'),
                gerar_regex_flexivel('conhecimento'),
            ]
        ),
        # HIPÓTESE 2: Esclarecimentos ao Laudo + Fase Liquidação (MAIS ESPECÍFICA - TESTADA SEGUNDA)
        # Se tem "esclarecimentos" E "liquidação" → ato_escliq
        (
            "Esclarecimentos ao Laudo - Liquidação",
            [
                gerar_regex_flexivel('esclarecimentos'),
                gerar_regex_flexivel('liquidação'),
            ]
        ),
        # HIPÓTESE 3: Apresentação de Laudo Pericial (MENOS ESPECÍFICA - TESTADA TERCEIRA)
        # Se tem "apresentação de laudo pericial" → ato_laudo
        (
            "Apresentação de Laudo Pericial",
            [
                gerar_regex_flexivel('apresentação de laudo pericial'),
            ]
        ),
        # HIPÓTESE 4: Indicação de Data de Realização (ESPECÍFICA - TESTADA QUARTA)
        # Se tem "indicação de data" → acao_pericias_com_data
        (
            "Indicação de Data de Realização",
            [
                gerar_regex_flexivel('indicação de data'),
            ]
        ),
    ]
    
    regra_analise_hipoteses = [
        # HIPÓTESE 1: Manifestação + (prosseguimento ou meios de execução) - DESPACHO GENÉRICO
        (
            "Manifestação - Despacho Genérico",
            [
                gerar_regex_flexivel('manifestação'),
                lambda txt: (gerar_regex_flexivel('prosseguimento').search(txt) or 
                           gerar_regex_flexivel('meios de execução').search(txt)),
            ]
        ),
        # HIPÓTESE 2: Manifestação + descrição manifestação
        (
            "Manifestação - Análise",
            [
                gerar_regex_flexivel('manifestação'),
                gerar_regex_flexivel('manifestação'),
            ]
        ),
        # HIPÓTESE 3: Manifestação + expedição de ofício
        (
            "Manifestação - Expedição de Ofício",
            [
                gerar_regex_flexivel('manifestação'),
                gerar_regex_flexivel('expedição de ofício'),
            ]
        ),
    ]
    
    regra_gigs_hipoteses = [
        # HIPÓTESE 1: GIGS genérica - concordancia ou comprovante (quitação, pagamento, depósito, etc.)
        (
            "GIGS - Homologação/Liberação",
            [
                lambda txt: (gerar_regex_flexivel('concordancia').search(txt) or 
                           gerar_regex_flexivel('comprovante').search(txt) or
                           gerar_regex_flexivel('deposito').search(txt) or
                           gerar_regex_flexivel('parcela').search(txt)),
            ]
        ),
    ]
    
    # Converter para tuplas com ações
    regra_apagar = [
        (nome, padroes, acao_apagar)
        for nome, padroes in regra_apagar_hipoteses
    ]
    
    # Para recurso, mapeia cada hipótese com sua ação específica
    acoes_recurso = [
        ato_instc if ato_instc else lambda driver, pet: False,  # Hipótese 1: Conhecimento
        ato_inste if ato_inste else lambda driver, pet: False,  # Hipótese 2: Liquidação/Execução
    ]
    
    regra_recurso = [
        (nome, padroes, acao)
        for (nome, padroes), acao in zip(regra_recurso_hipoteses, acoes_recurso)
    ]
    
    # Para perícias, mapeia cada hipótese com sua ação específica
    acoes_pericias = [
        ato_esc if ato_esc else lambda driver, pet: False,          # Hipótese 1: Esclarecimentos - Conhecimento (PRIMEIRO)
        ato_escliq if ato_escliq else lambda driver, pet: False,    # Hipótese 2: Esclarecimentos - Liquidação (SEGUNDO)
        ato_laudo if ato_laudo else lambda driver, pet: False,      # Hipótese 3: Laudo (TERCEIRO)
        acao_pericias_com_data,                                     # Hipótese 4: Data de Realização (criar_gigs + ato_datalocal)
    ]
    
    regra_pericias = [
        (nome, padroes, acao)
        for (nome, padroes), acao in zip(regra_pericias_hipoteses, acoes_pericias)
    ]
    
    # Para análise, mapeia com as ações apropriadas
    acao_despacho = ato_gen if ato_gen else lambda driver, pet: False
    acoes_analise = [
        acao_despacho,  # Hipótese 1: Manifestação - Despacho Genérico
        analise_pet,    # Hipótese 2: Manifestação - Análise
        analise_pet,    # Hipótese 3: Manifestação - Expedição de Ofício
    ]
    
    regra_analise = [
        (nome, padroes, acao)
        for (nome, padroes), acao in zip(regra_analise_hipoteses, acoes_analise)
    ]
    
    # Para GIGS, mapeia com a ação apropriada
    acoes_gigs = [
        acao_gigs,  # Hipótese 1: GIGS - Homologação/Liberação (ação decide parâmetro)
    ]
    
    regra_gigs = [
        (nome, padroes, acao)
        for (nome, padroes), acao in zip(regra_gigs_hipoteses, acoes_gigs)
    ]
    
    # ✅ NOVO: REGRA DIRETOS - Habilitação + Cálculos + Assistente + Impugnação
    regra_diretos_hipoteses = [
        # HIPÓTESE 1: Solicitação de Habilitação + Data de audiência após 01/02/2026
        (
            "Solicitação de Habilitação - CEJU",
            [
                gerar_regex_flexivel('habilitação'),
            ]
        ),
        # HIPÓTESE 2: Apresentação de Cálculos
        (
            "Apresentação de Cálculos",
            [
                gerar_regex_flexivel('apresentação de cálculos'),
                gerar_regex_flexivel('cálculo'),
            ]
        ),
        # HIPÓTESE 3: Admissão de Assistentes
        (
            "Assistente",
            [
                gerar_regex_flexivel('assistente'),
            ]
        ),
        # HIPÓTESE 4: Impugnação (Liquidação + padrão_liq)
        (
            "Impugnação",
            [
                gerar_regex_flexivel('impugnação'),
            ]
        ),
        # HIPÓTESE 5: CAGED (Previdenciário)
        (
            "CAGED",
            [
                gerar_regex_flexivel('caged'),
            ]
        ),
    ]
    
    # Para diretos, serão usadas ações diretas e tuplas de ações
    try:
        from atos.wrappers_ato import ato_ceju, ato_respcalc, ato_assistente, ato_concor, ato_prevjud
    except ImportError:
        ato_ceju = None
        ato_respcalc = None
        ato_assistente = None
        ato_concor = None
        ato_prevjud = None
    
    acoes_diretos = [
        ato_ceju if ato_ceju else lambda driver, pet: False,  # Hipótese 1: Habilitação CEJU
        ato_respcalc if ato_respcalc else lambda driver, pet: False,  # Hipótese 2: Apresentação de Cálculos
        (criar_gigs_1_xs_aud, ato_assistente) if ato_assistente else lambda driver, pet: False,  # Hipótese 3: Assistente (tupla: criar_gigs + ato_assistente)
        (padrao_liq_acao, ato_concor) if ato_concor else lambda driver, pet: False,  # Hipótese 4: Impugnação (tupla: padrao_liq + ato_concor condicional)
        (cris_gigs_minus1_xs_pec, ato_prevjud) if ato_prevjud else lambda driver, pet: False,  # Hipótese 5: CAGED (tupla: cris_gigs -1/xs pec + ato_prevjud)
    ]
    
    regra_diretos = [
        (nome, padroes, acao)
        for (nome, padroes), acao in zip(regra_diretos_hipoteses, acoes_diretos)
    ]
    
    return {
        "apagar": regra_apagar,
        "recurso": regra_recurso,
        "pericias": regra_pericias,
        "diretos": regra_diretos,  # ✅ NOVO
        "gigs": regra_gigs,  # GIGS deve ser checada ANTES de ANÁLISE (ambas têm "Manifestação")
        "analise": regra_analise,
    }


def verifica_peticao_contra_hipotese(peticao: PeticaoLinha, padroes: List) -> bool:
    """Verifica se petição bate com uma hipótese"""
    texto = normalizar_texto(
        f"{peticao.tipo_peticao} {peticao.descricao} {peticao.tarefa} {peticao.fase}"
    )
    
    for padrao in padroes:
        # Se for regex Pattern
        if isinstance(padrao, re.Pattern):
            if not padrao.search(texto):
                return False
        # Se for callable (função lambda)
        elif callable(padrao):
            if not padrao(texto):
                return False
        # Senão, trata como regex simples
        else:
            return False
    
    return True


def verifica_peticao_pericias(peticao: PeticaoLinha, padroes: List) -> bool:
    """
    Verifica se petição bate com hipótese de PERÍCIAS.
    
    Além dos padrões normais, PERICIAS requer:
    ✅ Que seja uma petição de perito (eh_perito=True)
    ✅ E que bata com os padrões textuais
    """
    # VALIDAÇÃO 1: Deve ser petição de perito
    if not peticao.eh_perito:
        return False
    
    # VALIDAÇÃO 2: Deve bater com os padrões
    return verifica_peticao_contra_hipotese(peticao, padroes)


def verifica_peticao_diretos(peticao: PeticaoLinha, padroes: List) -> bool:
    """
    Verifica se petição bate com hipótese de DIRETOS.
    
    Para DIRETOS, além dos padrões normais, requer:
    ✅ Bater com padrões textuais (tipo de petição)
    ✅ Ter data de audiência (data_audiencia não-nula)
    ✅ A data de audiência ser APÓS 01/02/2026
    ✅ Para "Impugnação": fase DEVE ser "Liquidação"
    """
    # VALIDAÇÃO 1: Deve bater com os padrões textuais
    if not verifica_peticao_contra_hipotese(peticao, padroes):
        return False
    
    # VALIDAÇÃO 2: Deve ter data de audiência
    if not peticao.data_audiencia:
        return False
    
    # VALIDAÇÃO 3: A data de audiência deve ser APÓS 01/02/2026
    try:
        from datetime import datetime
        # Extrair apenas a data (sem hora)
        data_str = peticao.data_audiencia.split()[0]  # "10/03/2026 11:35" → "10/03/2026"
        data_aud = datetime.strptime(data_str, "%d/%m/%Y")
        data_limite = datetime.strptime("01/02/2026", "%d/%m/%Y")
        
        if data_aud < data_limite:
            return False
    except Exception as e:
        logger.warning(f"[PET_DIRETOS] Erro ao comparar datas: {e}")
        return False
    
    # VALIDAÇÃO 4: Para "Impugnação", a fase deve ser "Liquidação"
    # Verificar qual hipótese bate
    for hipotese_nome, hipotese_padroes in [
        ("Habilitação", [gerar_regex_flexivel('habilitação')]),
        ("Cálculos", [gerar_regex_flexivel('apresentação de cálculos'), gerar_regex_flexivel('cálculo')]),
        ("Assistente", [gerar_regex_flexivel('assistente')]),
        ("Impugnação", [gerar_regex_flexivel('impugnação')]),
    ]:
        if verifica_peticao_contra_hipotese(peticao, hipotese_padroes):
            if hipotese_nome == "Impugnação":
                # Para Impugnação, a fase DEVE ser "Liquidação"
                if peticao.fase and 'liquidação' in peticao.fase.lower():
                    return True
                else:
                    logger.warning(f"[PET_DIRETOS] Impugnação requer fase Liquidação, mas fase={peticao.fase}")
                    return False
            else:
                # Para outras hipóteses, qualquer fase com data válida é aceita
                return True
    
    return False


def agrupar_por_regra(peticoes: List[PeticaoLinha]) -> Dict[str, Any]:
    """
    Agrupa petições pelas 3 REGRAS e identifica qual HIPÓTESE cada uma corresponde.
    
    Retorna: {
        "apagar": {...},
        "despacho_generico": {...},
        "recurso": {...}
    }
    """
    regras = definir_regras()
    resultado = {}
    
    # Inicializar estrutura para cada regra
    for nome_regra, hipoteses in regras.items():
        resultado[nome_regra] = {
            "peticoes_por_hipotese": {},
            "peticoes_sem_hipotese": [],
            "total": 0
        }
        for nome_hipotese, padroes, acao in hipoteses:
            resultado[nome_regra]["peticoes_por_hipotese"][nome_hipotese] = []
    
    # Agrupar petições em cada regra
    for peticao in peticoes:
        agrupada = False
        
        for nome_regra, hipoteses in regras.items():
            for nome_hipotese, padroes, acao in hipoteses:
                # ✅ Para PERÍCIAS, usar validação específica com ícone de perito
                if nome_regra == "pericias":
                    if verifica_peticao_pericias(peticao, padroes):
                        resultado[nome_regra]["peticoes_por_hipotese"][nome_hipotese].append(peticao)
                        agrupada = True
                        break
                # ✅ Para DIRETOS, usar validação específica com data de audiência
                elif nome_regra == "diretos":
                    if verifica_peticao_diretos(peticao, padroes):
                        resultado[nome_regra]["peticoes_por_hipotese"][nome_hipotese].append(peticao)
                        agrupada = True
                        break
                else:
                    if verifica_peticao_contra_hipotese(peticao, padroes):
                        resultado[nome_regra]["peticoes_por_hipotese"][nome_hipotese].append(peticao)
                        agrupada = True
                        break
            
            if agrupada:
                break  # Uma petição só pode pertencer a uma regra
        
        # Se não foi agrupada em nenhuma regra
        if not agrupada:
            # Adicionar à primeira regra como "sem hipótese" (padrão: apagar)
            resultado["apagar"]["peticoes_sem_hipotese"].append(peticao)
    
    # Calcular totais
    for nome_regra in resultado.keys():
        for pets_da_hipotese in resultado[nome_regra]["peticoes_por_hipotese"].values():
            resultado[nome_regra]["total"] += len(pets_da_hipotese)
        resultado[nome_regra]["total"] += len(resultado[nome_regra]["peticoes_sem_hipotese"])
    
    return resultado


def _abrir_detalhe_petição(driver: WebDriver, peticao: PeticaoLinha) -> Tuple[bool, Optional[str]]:
    """
    Abre a aba de detalhes de uma petição.
    
    Fluxo:
    1. Guarda handle da aba original (lista)
    2. Clica no ícone de detalhes da petição
    3. Aguarda nova aba abrir
    4. Retorna (sucesso, handle_aba_lista)
    """
    try:
        # 1. Guardar aba original (lista)
        aba_lista = driver.current_window_handle
        
        # 2. Clica no detalhes
        if not peticao.elemento_html:
            print(f"[PET_PROC]   ❌ Sem elemento HTML para {peticao.numero_processo}")
            return False, aba_lista
        
        from Fix.extracao import abrir_detalhes_processo
        if not abrir_detalhes_processo(driver, peticao.elemento_html):
            print(f"[PET_PROC]   ❌ Falha ao clicar em detalhes de {peticao.numero_processo}")
            return False, aba_lista
        
        time.sleep(1)
        
        # 3. Aguardar nova aba abrir
        from Fix.extracao import trocar_para_nova_aba
        nova_aba = trocar_para_nova_aba(driver, aba_lista)
        if not nova_aba:
            print(f"[PET_PROC]   ❌ Falha ao abrir aba de detalhes de {peticao.numero_processo}")
            return False, aba_lista
        
        time.sleep(2)  # Aguardar carregamento
        return True, aba_lista
        
    except Exception as e:
        print(f"[PET_PROC]   ❌ Erro ao abrir detalhes: {e}")
        return False, None


def _fechar_e_voltar_lista(driver: WebDriver, aba_lista: str) -> bool:
    """
    Fecha a aba de detalhes e volta para a aba de lista.
    
    Fluxo:
    1. Fecha a aba atual (detalhes)
    2. Muda para aba de lista
    """
    try:
        # 1. Fechar aba de detalhes
        driver.close()
        time.sleep(0.5)
        
        # 2. Voltar para aba de lista
        driver.switch_to.window(aba_lista)
        time.sleep(1)
        return True
        
    except Exception as e:
        print(f"[PET_PROC]   ❌ Erro ao fechar aba: {e}")
        return False


def _processar_petição_completa(driver: WebDriver, peticao: PeticaoLinha, acao: Callable) -> bool:
    """
    Processa uma petição de forma completa:
    1. Abre aba de detalhes
    2. Executa a ação
    3. Fecha aba e volta para lista
    
    Retorna True se bem-sucedido, False caso contrário.
    """
    print(f"[PET_PROC] {peticao.numero_processo}...")
    
    # Abre aba de detalhes
    sucesso_abertura, aba_lista = _abrir_detalhe_petição(driver, peticao)
    if not sucesso_abertura or not aba_lista:
        return False
    
    try:
        # Executa a ação
        if not isinstance(acao, tuple):
            acao = (acao,)  # Converter para tuple se for função simples
        
        sucesso_acao = _executar_acoes_sequenciais(driver, peticao, acao)
        
        # Fecha aba e volta para lista
        if not _fechar_e_voltar_lista(driver, aba_lista):
            print(f"[PET_PROC]   ⚠️ Falha ao fechar aba, mas tentaremos continuar")
        
        return sucesso_acao
        
    except Exception as e:
        print(f"[PET_PROC]   ❌ Erro ao processar: {e}")
        # Tentar voltar para lista mesmo com erro
        try:
            _fechar_e_voltar_lista(driver, aba_lista)
        except:
            pass
        return False


def _executar_acao_unica(driver: WebDriver, peticao: PeticaoLinha, acao: Callable) -> bool:
    """Executa uma ação simples"""
    return acao(driver, peticao)


def _executar_acoes_sequenciais(driver: WebDriver, peticao: PeticaoLinha, acoes: Tuple[Callable, ...]) -> bool:
    """Executa múltiplas ações em sequência"""
    resultado = True
    for i, acao in enumerate(acoes, 1):
        try:
            print(f"[PET_EXEC]       └─ Ação {i}/{len(acoes)}...")
            if callable(acao):
                resultado = acao(driver, peticao)
                if not resultado:
                    print(f"[PET_EXEC]         ❌ Falha na ação {i}")
                    return False
            time.sleep(0.5)
        except Exception as e:
            print(f"[PET_EXEC]         ❌ Erro na ação {i}: {e}")
            return False
    return resultado


def _executar_acao(driver: WebDriver, peticao: PeticaoLinha, acao) -> bool:
    """
    Executa uma ação que pode ser:
    - Uma função simples: acao(driver, peticao)
    - Uma tupla de funções: (func1, func2, ...) executadas em sequência
    """
    if isinstance(acao, tuple):
        return _executar_acoes_sequenciais(driver, peticao, acao)
    else:
        return _executar_acao_unica(driver, peticao, acao)


def executar_regras(driver: WebDriver, peticoes: List[PeticaoLinha]) -> bool:
    """Executa os 5 BLOCOS com todas suas hipóteses (APAGAR por último)"""
    try:
        resultado = agrupar_por_regra(peticoes)
        regras = definir_regras()
        
        # BLOCO 1: PERÍCIAS
        print(f"\n[PET_EXEC] ===== BLOCO 1: PERÍCIAS =====")
        regra_pericias = resultado["pericias"]
        print(f"[PET_EXEC] Total: {regra_pericias['total']}")
        
        # Pega as hipóteses do BLOCO 1 com suas ações
        hipoteses_pericias = {nome: acao for nome, padroes, acao in regras["pericias"]}
        
        for nome_hipotese, peticoes_da_hipotese in regra_pericias["peticoes_por_hipotese"].items():
            if not peticoes_da_hipotese:
                print(f"[PET_EXEC]   • {nome_hipotese}: -")
                continue
            
            print(f"[PET_EXEC]   • {nome_hipotese}: {len(peticoes_da_hipotese)}")
            acao = hipoteses_pericias.get(nome_hipotese)
            
            sucesso = 0
            for peticao in peticoes_da_hipotese:
                if acao and _processar_petição_completa(driver, peticao, acao):
                    sucesso += 1
                time.sleep(0.5)
            
            print(f"[PET_EXEC]     └─ {sucesso}/{len(peticoes_da_hipotese)} processadas")
        
        # BLOCO 2: GIGS
        print(f"\n[PET_EXEC] ===== BLOCO 2: GIGS =====")
        regra_gigs = resultado.get("gigs", {"total": 0, "peticoes_por_hipotese": {}})
        print(f"[PET_EXEC] Total: {regra_gigs['total']}")
        
        # Pega as hipóteses do BLOCO 2 com suas ações
        hipoteses_gigs = {nome: acao for nome, padroes, acao in regras.get("gigs", [])}
        
        for nome_hipotese, peticoes_da_hipotese in regra_gigs["peticoes_por_hipotese"].items():
            if not peticoes_da_hipotese:
                print(f"[PET_EXEC]   • {nome_hipotese}: -")
                continue
            
            print(f"[PET_EXEC]   • {nome_hipotese}: {len(peticoes_da_hipotese)}")
            acao = hipoteses_gigs.get(nome_hipotese)
            
            sucesso = 0
            for peticao in peticoes_da_hipotese:
                if acao and _processar_petição_completa(driver, peticao, acao):
                    sucesso += 1
                time.sleep(0.5)
            
            print(f"[PET_EXEC]     └─ {sucesso}/{len(peticoes_da_hipotese)} homologadas")
        
        # BLOCO 3: RECURSO
        print(f"\n[PET_EXEC] ===== BLOCO 3: RECURSO =====")
        regra_recurso = resultado["recurso"]
        print(f"[PET_EXEC] Total: {regra_recurso['total']}")
        
        # Pega as hipóteses do BLOCO 3 com suas ações
        hipoteses_recurso = {nome: acao for nome, padroes, acao in regras["recurso"]}
        
        for nome_hipotese, peticoes_da_hipotese in regra_recurso["peticoes_por_hipotese"].items():
            if not peticoes_da_hipotese:
                print(f"[PET_EXEC]   • {nome_hipotese}: -")
                continue
            
            print(f"[PET_EXEC]   • {nome_hipotese}: {len(peticoes_da_hipotese)}")
            acao = hipoteses_recurso.get(nome_hipotese)
            
            sucesso = 0
            for peticao in peticoes_da_hipotese:
                if acao and _processar_petição_completa(driver, peticao, acao):
                    sucesso += 1
                time.sleep(0.5)
            
            print(f"[PET_EXEC]     └─ {sucesso}/{len(peticoes_da_hipotese)} processadas")
        
        # BLOCO 4: DIRETOS (Habilitação com CEJU)
        print(f"\n[PET_EXEC] ===== BLOCO 4: DIRETOS =====")
        regra_diretos = resultado.get("diretos", {"total": 0, "peticoes_por_hipotese": {}})
        print(f"[PET_EXEC] Total: {regra_diretos['total']}")
        
        # Pega as hipóteses do BLOCO 4 com suas ações
        hipoteses_diretos = {nome: acao for nome, padroes, acao in regras.get("diretos", [])}
        
        for nome_hipotese, peticoes_da_hipotese in regra_diretos["peticoes_por_hipotese"].items():
            if not peticoes_da_hipotese:
                print(f"[PET_EXEC]   • {nome_hipotese}: -")
                continue
            
            print(f"[PET_EXEC]   • {nome_hipotese}: {len(peticoes_da_hipotese)}")
            acao = hipoteses_diretos.get(nome_hipotese)
            
            sucesso = 0
            for peticao in peticoes_da_hipotese:
                if acao and _processar_petição_completa(driver, peticao, acao):
                    sucesso += 1
                time.sleep(0.5)
            
            print(f"[PET_EXEC]     └─ {sucesso}/{len(peticoes_da_hipotese)} processadas")
        
        # BLOCO 5: ANÁLISE
        print(f"\n[PET_EXEC] ===== BLOCO 5: ANÁLISE =====")
        regra_analise = resultado.get("analise", {"total": 0, "peticoes_por_hipotese": {}})
        print(f"[PET_EXEC] Total: {regra_analise['total']}")
        
        # Pega as hipóteses do BLOCO 5 com suas ações
        hipoteses_analise = {nome: acao for nome, padroes, acao in regras.get("analise", [])}
        
        for nome_hipotese, peticoes_da_hipotese in regra_analise["peticoes_por_hipotese"].items():
            if not peticoes_da_hipotese:
                print(f"[PET_EXEC]   • {nome_hipotese}: -")
                continue
            
            print(f"[PET_EXEC]   • {nome_hipotese}: {len(peticoes_da_hipotese)}")
            acao = hipoteses_analise.get(nome_hipotese)
            
            sucesso = 0
            for peticao in peticoes_da_hipotese:
                if acao and _processar_petição_completa(driver, peticao, acao):
                    sucesso += 1
                time.sleep(0.5)
            
            print(f"[PET_EXEC]     └─ {sucesso}/{len(peticoes_da_hipotese)} analisadas")
        
        # BLOCO 0: APAGAR (executado por último para evitar mudança de índices)
        print(f"\n[PET_EXEC] ===== BLOCO 0: APAGAR (POR ÚLTIMO) =====")
        regra_apagar = resultado["apagar"]
        print(f"[PET_EXEC] Total: {regra_apagar['total']}")
        
        # Pega as hipóteses do BLOCO 0 com suas ações
        hipoteses_apagar = {nome: acao for nome, padroes, acao in regras["apagar"]}
        
        for nome_hipotese, peticoes_da_hipotese in regra_apagar["peticoes_por_hipotese"].items():
            if not peticoes_da_hipotese:
                print(f"[PET_EXEC]   • {nome_hipotese}: -")
                continue
            
            print(f"[PET_EXEC]   • {nome_hipotese}: {len(peticoes_da_hipotese)}")
            acao = hipoteses_apagar.get(nome_hipotese)
            
            sucesso = 0
            for peticao in peticoes_da_hipotese:
                if acao and _executar_acao(driver, peticao, acao):
                    sucesso += 1
                time.sleep(0.5)
            
            print(f"[PET_EXEC]     └─ {sucesso}/{len(peticoes_da_hipotese)} apagadas")
        
        return True
        
    except Exception as e:
        logger.error(f"[PET_EXEC] Erro: {e}")
        return False


# ============================================================================
# ANÁLISE DE PETIÇÃO (extrai PDF + decide ação)
# ============================================================================

def localizar_ultima_peticao(driver: WebDriver) -> Optional[WebElement]:
    """
    Localiza a última petição juntada (com background amarelo/khaki).
    Retorna o elemento do card ou None.
    """
    try:
        # Procura por elementos com background amarelo/khaki
        # Padrão: <li ... id="doc_XXXXX" ... style="background-color: rgb(...)"
        # seguido por <mat-card ... style="background-color: khaki;" ou similar
        
        elementos = driver.find_elements(By.XPATH, '//li[@id and @style*="background"]')
        
        if elementos:
            # Retorna o último elemento encontrado
            return elementos[-1]
        
        # Alternativa: procurar por mat-card com khaki/amarelo
        cards = driver.find_elements(By.XPATH, '//mat-card[contains(@style, "background")]')
        if cards:
            return cards[-1]
        
        return None
    except Exception as e:
        logger.error(f"[PET_ANALISE] Erro ao localizar última petição: {e}")
        return None


def extrair_conteudo_peticao(driver: WebDriver, elemento: WebElement) -> Optional[str]:
    """
    Extrai o conteúdo da petição usando extrair_pdf.
    Simula clique no elemento para abrir e extrai conteúdo.
    """
    try:
        print("[PET_ANALISE] Abrindo petição...")
        
        # Tentar clicar no elemento para abrir
        try:
            elemento.click()
        except:
            # Se não conseguir clicar, tenta scroll até o elemento
            driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
            time.sleep(0.3)
            elemento.click()
        
        time.sleep(1)  # Aguardar carregamento do documento
        
        # Extrair PDF
        print("[PET_ANALISE] Extraindo conteúdo PDF...")
        texto = extrair_pdf(driver, log=False)
        
        if texto:
            print(f"[PET_ANALISE] ✅ Conteúdo extraído ({len(texto)} caracteres)")
            preview = texto[:150].replace('\n', ' ').strip()
            print(f"[PET_ANALISE] Preview: {preview}...")
            return texto
        else:
            print("[PET_ANALISE] ❌ Falha na extração de conteúdo")
            return None
    
    except Exception as e:
        logger.error(f"[PET_ANALISE] Erro ao extrair conteúdo: {e}")
        return False


def definir_regras_analise() -> List[Tuple[str, List[str], Callable]]:
    """
    Define regras de análise para decidir ação baseada no conteúdo extraído.
    Padrão como em p2b.py: (descricao, [padroes_regex], acao)
    """
    
    regras = [
        (
            "Análise com Perícia",
            [
                r'períc',
                r'laudo',
                r'expert',
                r'prova técnica',
            ],
            ato_laudo
        ),
        (
            "Análise com Recurso",
            [
                r'agrav',
                r'apelação',
                r'embarg',
            ],
            ato_instc
        ),
        (
            "Análise com Despacho",
            [
                r'despacho',
                r'conclusão',
                r'análise',
            ],
            despacho_generico
        ),
    ]
    
    return regras


def analise_pet(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """
    Análise de petição juntada:
    1. Localiza última petição (com background amarelo)
    2. Extrai conteúdo via PDF
    3. Analisa conteúdo via regex (padrão p2b.py)
    4. Executa ação apropriada
    """
    try:
        print("\n[PET_ANALISE] ===== ANÁLISE DE PETIÇÃO =====")
        
        # Passo 1: Localizar última petição
        print("[PET_ANALISE] Localizando última petição...")
        elemento = localizar_ultima_peticao(driver)
        
        if not elemento:
            print("[PET_ANALISE] ⚠️ Nenhuma petição encontrada para análise")
            return False
        
        print("[PET_ANALISE] ✅ Petição localizada")
        
        # Passo 2: Extrair conteúdo
        conteudo = extrair_conteudo_peticao(driver, elemento)
        
        if not conteudo:
            print("[PET_ANALISE] ❌ Falha na extração de conteúdo")
            return False
        
        # Passo 3: Analisar via regex e executar ação
        print("[PET_ANALISE] Analisando conteúdo...")
        regras = definir_regras_analise()
        
        texto_normalizado = normalizar_texto(conteudo)
        acao_executada = False
        
        for nome_regra, padroes, acao in regras:
            # Verificar se algum padrão bate
            match = False
            for padrao in padroes:
                if re.search(padrao, texto_normalizado, re.IGNORECASE):
                    match = True
                    break
            
            if match:
                print(f"[PET_ANALISE] ✅ Regra detectada: {nome_regra}")
                
                # Executar ação
                if acao and callable(acao):
                    try:
                        print(f"[PET_ANALISE] Executando ação: {acao.__name__ if hasattr(acao, '__name__') else str(acao)}")
                        
                        # Criar PeticaoLinha fictícia para ação
                        peticao_dummy = PeticaoLinha(
                            indice=0,
                            numero_processo="ANÁLISE",
                            tipo_peticao="Análise",
                            descricao=nome_regra,
                            tarefa="",
                            fase="",
                            data_juntada="",
                            elemento_html=None,
                            eh_perito=False,
                            polo=None
                        )
                        
                        resultado = acao(driver, peticao_dummy)
                        if resultado:
                            print(f"[PET_ANALISE] ✅ Ação executada com sucesso")
                            acao_executada = True
                            break
                        else:
                            print(f"[PET_ANALISE] ⚠️ Ação retornou False")
                    except Exception as e:
                        print(f"[PET_ANALISE] ⚠️ Erro ao executar ação: {e}")
                else:
                    print(f"[PET_ANALISE] ⚠️ Ação não disponível")
        
        if not acao_executada:
            print("[PET_ANALISE] ⚠️ Nenhuma regra encontrada - executando ato_gen (Despacho Genérico)")
            if ato_gen:
                try:
                    peticao_dummy = PeticaoLinha(
                        indice=0,
                        numero_processo="ANÁLISE",
                        tipo_peticao="Análise",
                        descricao="Despacho Genérico",
                        tarefa="",
                        fase="",
                        data_juntada="",
                        elemento_html=None,
                        eh_perito=False,
                        polo=None
                    )
                    resultado = ato_gen(driver, peticao_dummy)
                    if resultado:
                        print(f"[PET_ANALISE] ✅ ato_gen executado com sucesso")
                        acao_executada = True
                    else:
                        print(f"[PET_ANALISE] ⚠️ ato_gen retornou False")
                except Exception as e:
                    print(f"[PET_ANALISE] ⚠️ Erro ao executar ato_gen: {e}")
            else:
                print("[PET_ANALISE] ⚠️ ato_gen não disponível")
        
        if not acao_executada:
            print("[PET_ANALISE] ⚠️ Nenhuma ação foi executada")
            return False
        
        print("[PET_ANALISE] ✅ Análise concluída com sucesso")
        return True
    
    except Exception as e:
        logger.error(f"[PET_ANALISE] Erro geral: {e}")
        return False


# ============================================================================
# FLUXO PRINCIPAL
# ============================================================================

def executar_fluxo_pet(driver: WebDriver) -> bool:
    """Executa fluxo completo: navegar -> extrair -> agrupar -> executar (com rastreamento de progresso)"""
    try:
        # 0. Carregar progresso
        print("[PET] Carregando progresso...")
        progresso = carregar_progresso_pet()
        
        # 1. Navegar
        if not navegacao_inicial_pet(driver):
            print("[PET] ❌ Falha na navegação")
            return False
        
        # 2. Extrair
        peticoes = extrair_tabela_peticoes(driver)
        if not peticoes:
            print("[PET] ❌ Nenhuma petição encontrada")
            return False
        
        print(f"[PET] ✅ Extraídas {len(peticoes)} petições")
        
        # 2.5 Filtrar petições não executadas
        peticoes_nao_executadas = []
        for pet in peticoes:
            if not processo_ja_executado_pet(pet.numero_processo, progresso):
                peticoes_nao_executadas.append(pet)
            else:
                print(f"[PET_PROG] Processo {pet.numero_processo} já executado, pulando...")
        
        if not peticoes_nao_executadas:
            print("[PET] Todos os processos já foram executados!")
            return True
        
        print(f"[PET] {len(peticoes) - len(peticoes_nao_executadas)} processos pulados (já executados)")
        print(f"[PET] {len(peticoes_nao_executadas)} processos para executar")
        
        # 3. Agrupar e mostrar resultado
        resultado = agrupar_por_regra(peticoes_nao_executadas)
        
        # Função para simplificar número do processo
        def simplificar_processo(numero_processo):
            """
            Simplifica: 1001100-55.2019.5.02.0703 -> 1100-55
            Remove primeiros dígitos repetidos e a parte final de data/tribunal
            """
            if '.' in numero_processo:
                numero_processo = numero_processo.split('.')[0]
            if '-' in numero_processo:
                num_parte, resto = numero_processo.split('-')
                num_parte = str(int(num_parte) % 1000000)
                return f"{num_parte}-{resto}"
            return numero_processo
        
        # Log das 5 REGRAS (apenas linhas com hipóteses)
        print(f"\n[PET] ===== AGRUPAMENTO POR REGRAS =====")
        
        regras_ordem = ["apagar", "recurso", "pericias", "gigs", "analise"]
        totais = {}
        
        for idx, nome_regra in enumerate(regras_ordem, 1):
            regra = resultado[nome_regra]
            total = regra["total"]
            totais[nome_regra] = total
            
            if total > 0:
                print(f"\n[PET] REGRA {idx}: {nome_regra.upper()}")
                
                for nome_hipotese, pets in regra["peticoes_por_hipotese"].items():
                    if pets:
                        procs_simplificados = [simplificar_processo(pet.numero_processo) for pet in pets]
                        procs_str = ', '.join(procs_simplificados[:10])
                        if len(procs_simplificados) > 10:
                            procs_str += f', +{len(procs_simplificados) - 10} mais'
                        print(f"[PET]   {nome_hipotese}: {procs_str}")
        
        # Resumo
        print(f"\n[PET] ===== RESUMO =====")
        total_geral = sum(totais.values())
        print(f"[PET] Total extraído: {len(peticoes)} | Total agrupado: {total_geral}")
        for idx, nome_regra in enumerate(regras_ordem, 1):
            if totais[nome_regra] > 0:
                print(f"[PET]   REGRA {idx} [{nome_regra.upper()}]: {totais[nome_regra]}")
        
        # 4. Executar
        print("\n[PET] Executando regras...")
        if not executar_regras(driver, peticoes_nao_executadas):
            print("[PET] ⚠️ Erro durante execução")
            return False
        
        # 4.5 Marcar processos como executados
        print("\n[PET] Marcando processos como executados...")
        for pet in peticoes_nao_executadas:
            marcar_processo_executado_pet(pet.numero_processo, progresso)
        salvar_progresso_pet(progresso)
        print(f"[PET_PROG] {len(peticoes_nao_executadas)} processos marcados como executados")
        
        # 5. Análise de petição juntada (a última)
        print("\n[PET] Executando análise de petição...")
        peticao_analise = PeticaoLinha(
            indice=0,
            numero_processo="ANÁLISE",
            tipo_peticao="Análise",
            descricao="Análise final",
            tarefa="",
            fase="",
            data_juntada="",
            elemento_html=None,
            eh_perito=False,
            polo=None
        )
        if not analise_pet(driver, peticao_analise):
            print("[PET] ⚠️ Análise não executada ou falhou")
        
        print("[PET] ✅ Fluxo completado")
        return True
        
    except Exception as e:
        logger.error(f"[PET] Erro: {e}")
        return False


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print('[PET] Módulo PEC/pet.py carregado')
    print('[PET] Use executar_fluxo_pet(driver) para iniciar')
    
    from Prazo.prov import criar_driver
    from Fix.utils import login_cpf
    from Fix.core import finalizar_driver
    
    driver = None
    try:
        print('[PET] Criando driver...')
        driver = criar_driver(headless=False)
        if not driver:
            print('[PET] ❌ Falha ao criar driver')
            exit(1)
        
        print('[PET] Fazendo login...')
        if not login_cpf(driver):
            print('[PET] ❌ Falha no login')
            exit(1)
        
        print('[PET] Iniciando fluxo...')
        sucesso = executar_fluxo_pet(driver)
        
        if sucesso:
            print('[PET] ✅ Sucesso')
        else:
            print('[PET] ❌ Falha')
            exit(1)
            
    except Exception as e:
        print(f'[PET] ❌ Erro: {e}')
        exit(1)
    finally:
        if driver:
            try:
                finalizar_driver(driver)
            except:
                pass
