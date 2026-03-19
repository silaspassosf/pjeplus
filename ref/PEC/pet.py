"""
PEC/pet.py - Processamento de Petições (PJe)
Leitura de tabela de petições juntadas + agrupamento em buckets por regras + execução sequencial
"""

import time
import re
import os
import sys
import inspect
import traceback
import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any, Callable, Union
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Ajuste de path para importações quando executado de dentro de PEC/
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports do projeto
from Fix.core import aguardar_e_clicar, esperar_elemento
from Fix.extracao import reindexar_linha, abrir_detalhes_processo, trocar_para_nova_aba
from Fix.abas import validar_conexao_driver, forcar_fechamento_abas_extras
from Fix.log import logger

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

ESCANINHO_URL = "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"
PROGRESSO_FILE = Path("progresso_pet.json")

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

class PeticaoLinha:
    """Representa uma linha da tabela de petições"""
    def __init__(self, indice: int, numero_processo: str, tipo_peticao: str,
                 descricao: str, tarefa: str, fase: str, data_juntada: str,
                 elemento_html: Optional[WebElement] = None):
        self.indice = indice
        self.numero_processo = numero_processo
        self.tipo_peticao = tipo_peticao
        self.descricao = descricao  # Descrição/detalhes da petição
        self.tarefa = tarefa
        self.fase = fase
        self.data_juntada = data_juntada
        self.elemento_html = elemento_html
    
    def __repr__(self):
        desc_short = self.descricao[:30] if self.descricao else "(sem desc)"
        return f"PeticaoLinha({self.numero_processo} | {self.tipo_peticao} | {desc_short}... | {self.tarefa}/{self.fase})"
    
    def gerar_chave_regra(self) -> str:
        """Gera chave para buscar regra correspondente"""
        # Formato: "tipo_peticao|descricao|tarefa|fase" para buscas flexíveis
        partes = []
        if self.tipo_peticao:
            partes.append(self.tipo_peticao.lower().strip())
        if self.descricao:
            partes.append(self.descricao.lower().strip())
        if self.tarefa:
            partes.append(self.tarefa.lower().strip())
        if self.fase:
            partes.append(self.fase.lower().strip())
        return "|".join(partes)


# ============================================================================
# FUNÇÕES DE NAVEGAÇÃO
# ============================================================================

def navegacao_inicial_pet(driver: WebDriver) -> bool:
    """
    Navega para escaninho de petições juntadas e aplica filtros iniciais.
    
    Steps:
    1. Navegar para URL escaninho
    2. Aplicar filtro 100 (visualizar 100 processos)
    3. Clicar coluna "Tipo de Petição" para reordenar
    """
    try:
        # 1. Navegar para escaninho
        print(f"[PET_NAV] Navegando para {ESCANINHO_URL}...")
        driver.get(ESCANINHO_URL)
        time.sleep(2)
        
        # 2. Aplicar filtro 50 (visualizar 50 processos - limite máximo na página de petições)
        print("[PET_NAV] Aplicando filtro de 50 processos...")
        if not aplicar_filtro_50(driver):
            print("[PET_NAV] ⚠️ Filtro 50 pode não ter sido aplicado")
        
        time.sleep(2)  # Aguardar carregamento após aplicar filtro
        
        # 3. Reordenar coluna "Tipo de Petição"
        print("[PET_NAV] Reordenando coluna 'Tipo de Petição'...")
        if not reordenar_coluna_tipo_peticao(driver):
            print("[PET_NAV] ⚠️ Coluna pode não ter sido reordenada")
        
        time.sleep(1)
        print("[PET_NAV] ✅ Navegação inicial concluída")
        return True
        
    except Exception as e:
        logger.error(f"[PET_NAV] Erro na navegação inicial: {e}")
        return False


def aplicar_filtro_50(driver: WebDriver, timeout: int = 10) -> bool:
    """
    Aplica filtro para visualizar 50 processos (limite máximo da página de petições).
    Padrão similar ao aplicar_filtro_100 do Fix.
    
    Clica no select de "Linhas por página" e seleciona opção "50".
    """
    try:
        print("[PET_FILTRO] Aplicando filtro de 50 processos...")
        
        # Função interna para selecionar com múltiplos seletores
        def _selecionar():
            try:
                # Encontrar span com "20" (valor padrão atual)
                span_20 = driver.find_element(By.XPATH, 
                    "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']")
                
                # Encontrar o mat-select pai
                mat_select = span_20.find_element(By.XPATH, "ancestor::mat-select[@role='combobox']")
                
                # Fazer scroll para o elemento estar visível
                driver.execute_script("arguments[0].scrollIntoView(true);", mat_select)
                time.sleep(0.3)
                
                # Clicar usando JavaScript (evita bloqueios de overlay)
                driver.execute_script("arguments[0].click();", mat_select)
                time.sleep(0.5)
                
                # Aguardar overlay aparecer
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                overlay = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                time.sleep(0.3)
                
                # Procurar opção "50"
                opcao_50 = overlay.find_element(By.XPATH, 
                    ".//mat-option[.//span[normalize-space(text())='50']]")
                
                # Clicar na opção usando JavaScript também
                driver.execute_script("arguments[0].click();", opcao_50)
                time.sleep(1)
                
                print('[PET_FILTRO] ✅ Clique real na opção 50 confirmado.')
                return True
            except Exception as e:
                print(f'[PET_FILTRO] ❌ Falha ao clicar em 50: {e}')
                return False
        
        # Aplicar com retry
        from Fix.core import com_retry
        resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log=True)
        
        if resultado:
            logger.info('[PET_FILTRO] Filtro de 50 aplicado com sucesso')
        else:
            logger.error('[PET_FILTRO] Filtro de 50 falhou após todas tentativas')
        
        return resultado
        
    except Exception as e:
        logger.error(f"[PET_FILTRO] Erro ao aplicar filtro de 50: {e}")
        return False
        return False


def reordenar_coluna_tipo_peticao(driver: WebDriver, timeout: int = 10) -> bool:
    """
    Clica na coluna "Tipo de Petição" para reordenar a tabela.
    
    A coluna é um <div> com atributos específicos contendo "Tipo de Petição".
    Precisa clicar no header da coluna para reordenar.
    """
    try:
        # Procurar pela coluna Tipo de Petição
        seletores = [
            (By.XPATH, "//*[contains(text(), 'Tipo de Petição')]"),
            (By.XPATH, "//div[contains(@class, 'th-') and contains(text(), 'Tipo de Petição')]"),
            (By.CSS_SELECTOR, "div.th-elemento-class"),  # Procurar todas as colunas headers
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
        logger.error(f"[PET_REORD] Erro ao reordenar coluna: {e}")
        return False


# ============================================================================
# EXTRAÇÃO DE TABELA
# ============================================================================

def extrair_tabela_peticoes(driver: WebDriver) -> List[PeticaoLinha]:
    """
    Extrai todas as linhas da tabela de petições.
    
    Seletor: tr.cdk-drag (linhas da tabela Material)
    Colunas: 
    - Índice 0: Ícone/Botão detalhes
    - Índice 1: Número do processo
    - Índice 2: Tipo de Petição
    - Índice 3: Tarefa - Fase
    - Índice 4: Data de Juntada
    """
    peticoes = []
    
    try:
        # Aguardar tabela carregar
        print("[PET_EXTR] Aguardando tabela carregar...")
        time.sleep(2)
        
        # Encontrar linhas
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.cdk-drag")
        print(f"[PET_EXTR] Encontradas {len(linhas)} linhas na tabela")
        
        for idx, linha in enumerate(linhas, 1):
            try:
                # Extrair células
                tds = linha.find_elements(By.TAG_NAME, "td")
                if not tds:
                    continue
                
                # Extrair informações
                numero_processo = ""
                tipo_peticao = ""
                tarefa_fase_texto = ""
                data_juntada = ""
                
                # Extrair de índices específicos (confirmado em test_html_struct.py)
                # TD[1]: Processo (formato: "Abrir a tarefa... processo: XXXXXXX-XX.XXXX.X.XX.XXXX...")
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
                descricao = ""
                if len(tds) > 5:
                    descricao = tds[5].text.strip()
                
                # TD[6]: Tarefa + Fase (separados por "Fase:")
                tarefa = ""
                fase = ""
                if len(tds) > 6:
                    texto_td6 = tds[6].text.strip()
                    if "Fase:" in texto_td6:
                        partes = texto_td6.split("Fase:")
                        tarefa = partes[0].strip()
                        fase = partes[1].strip() if len(partes) > 1 else ""
                    else:
                        tarefa = texto_td6.strip()
                
                # Criar objeto PeticaoLinha
                if numero_processo:
                    peticao = PeticaoLinha(
                        indice=idx,
                        numero_processo=numero_processo,
                        tipo_peticao=tipo_peticao,
                        descricao=descricao,
                        tarefa=tarefa,
                        fase=fase,
                        data_juntada=data_juntada,
                        elemento_html=linha
                    )
                    peticoes.append(peticao)
                    
                    print(f"[PET_EXTR] {idx}. {numero_processo} | {tipo_peticao} | {descricao[:30]}...")
                    print(f"           Tarefa: {tarefa} | Fase: {fase}")
                
            except Exception as e:
                logger.warning(f"[PET_EXTR] Erro ao processar linha {idx}: {e}")
                continue
        
        print(f"[PET_EXTR] ✅ Total de {len(peticoes)} petições extraídas")
        return peticoes
        
    except Exception as e:
        logger.error(f"[PET_EXTR] Erro na extração de tabela: {e}")
        return []


# ============================================================================
# PROGRESSÃO (pet.json)
# ============================================================================

def carregar_progresso_pet() -> Dict[str, Any]:
    """Carrega progresso de pet.json"""
    try:
        if Path("pet.json").exists():
            with open("pet.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"[PET_PROG] Erro ao carregar pet.json: {e}")
    
    # Retornar estrutura vazia se não existir
    return {
        "ultima_atualizacao": "",
        "blocos_executados": []
    }


def salvar_progresso_pet(progresso: Dict[str, Any]) -> None:
    """Salva progresso em pet.json"""
    try:
        progresso['ultima_atualizacao'] = datetime.now().isoformat()
        with open("pet.json", "w", encoding="utf-8") as f:
            json.dump(progresso, f, ensure_ascii=False, indent=2)
        logger.info(f"[PET_PROG] ✅ Progresso salvo em pet.json")
    except Exception as e:
        logger.error(f"[PET_PROG] ❌ Erro ao salvar pet.json: {e}")


def marcar_hipotese_executada(bloco_id: str, hipotese_id: str, numero_processo: str, sucesso: bool = True) -> None:
    """Marca um processo como executado em uma hipótese"""
    progresso = carregar_progresso_pet()
    
    for bloco in progresso.get('blocos_executados', []):
        if bloco['bloco_id'] == bloco_id:
            for hipotese in bloco.get('hipoteses', []):
                if hipotese['hipotese_id'] == hipotese_id:
                    if sucesso:
                        hipotese['processos_executados'].append(numero_processo)
                        hipotese['status'] = 'completo' if len(hipotese.get('processos_executados', [])) > 0 else 'em_progresso'
                    else:
                        hipotese['processos_falhados'].append(numero_processo)
                    
                    salvar_progresso_pet(progresso)
                    return


def definir_regras_apagar() -> List[Tuple[Dict[str, Any], Callable]]:
    """
    Define as regras de APAGAR (limpeza de petições) com suas 3 hipóteses.
    
    Retorna lista de tuplas: (condicoes, acao)
    - condicoes: dict com regex/validadores para tipo, descricao, tarefa, fase
    - acao: função callback a executar
    
    Padrão: identico a p2b.py - uma única função de execução com múltiplos pares (regra->acao)
    """
    
    regras = [
        # HIPÓTESE 1: Razões Finais
        {
            'hipotese_id': 'RAZOES_FINAIS',
            'hipotese_nome': 'Razões Finais',
            'condicoes': {
                'tipo': gerar_regex_flexivel('razões finais'),
                'descricao': gerar_regex_flexivel('razões finais'),
                'tarefa': None,  # Sem restrição
                'fase': None     # Sem restrição
            },
            'acao': acao_apagar
        },
        # HIPÓTESE 2: Réplica em Conhecimento
        {
            'hipotese_id': 'REPLICA_CONHECIMENTO',
            'hipotese_nome': 'Réplica (Fase: Conhecimento)',
            'condicoes': {
                'tipo': gerar_regex_flexivel('réplica'),
                'descricao': gerar_regex_flexivel('réplica'),
                'tarefa': None,  # Sem restrição
                'fase': lambda f: normalizar_texto(f) == normalizar_texto('conhecimento')  # Restrição: fase = Conhecimento
            },
            'acao': acao_apagar
        },
        # HIPÓTESE 3: Acordos (Contestação/Habilitação/Preposição/Substabelecimento)
        {
            'hipotese_id': 'ACORDO',
            'hipotese_nome': 'Acordo (Tarefa: Cumprimento)',
            'condicoes': {
                'tipo': lambda t: any(gerar_regex_flexivel(x).search(normalizar_texto(t)) for x in 
                                     ['contestação', 'habilitação', 'preposição', 'substabelecimento']),
                'descricao': None,  # Sem restrição
                'tarefa': lambda t: normalizar_texto(t) == normalizar_texto('aguardando cumprimento de acordo'),
                'fase': None  # Sem restrição
            },
            'acao': acao_apagar
        },
        # HIPÓTESE 4: Manifestação + Carta de Preposição
        {
            'hipotese_id': 'MANIFESTACAO_CARTA_PREPOSICAO',
            'hipotese_nome': 'Manifestação - Carta de Preposição',
            'condicoes': {
                'tipo': gerar_regex_flexivel('manifestação'),
                'descricao': gerar_regex_flexivel('carta de preposição'),
                'tarefa': None,  # Sem restrição
                'fase': None     # Sem restrição
            },
            'acao': acao_apagar
        },
        # HIPÓTESE 5: Manifestação + Substabelecimento sem reserva
        {
            'hipotese_id': 'MANIFESTACAO_SUBSTABELECIMENTO',
            'hipotese_nome': 'Manifestação - Substabelecimento sem reserva',
            'condicoes': {
                'tipo': gerar_regex_flexivel('manifestação'),
                'descricao': gerar_regex_flexivel('substabelecimento sem reserva'),
                'tarefa': None,  # Sem restrição
                'fase': None     # Sem restrição
            },
            'acao': acao_apagar
        }
    ]
    
    return regras


def verifica_condicoes(peticao: PeticaoLinha, condicoes: Dict[str, Any]) -> bool:
    """
    Verifica se uma petição satisfaz todas as condições de uma regra.
    
    Args:
        peticao: PeticaoLinha
        condicoes: dict com 'tipo', 'descricao', 'tarefa', 'fase'
                   - regex.Pattern: testa match
                   - callable: testa resultado == True
                   - None: sem restrição (sempre True)
    
    Returns:
        True se todas as condições passam
    """
    
    # Validar tipo
    if condicoes.get('tipo') is not None:
        validador = condicoes['tipo']
        if isinstance(validador, re.Pattern):
            if not validador.search(normalizar_texto(peticao.tipo_peticao)):
                return False
        elif callable(validador):
            if not validador(peticao.tipo_peticao):
                return False
    
    # Validar descrição
    if condicoes.get('descricao') is not None:
        validador = condicoes['descricao']
        if isinstance(validador, re.Pattern):
            if not validador.search(normalizar_texto(peticao.descricao)):
                return False
        elif callable(validador):
            if not validador(peticao.descricao):
                return False
    
    # Validar tarefa
    if condicoes.get('tarefa') is not None:
        validador = condicoes['tarefa']
        if isinstance(validador, re.Pattern):
            if not validador.search(normalizar_texto(peticao.tarefa)):
                return False
        elif callable(validador):
            if not validador(peticao.tarefa):
                return False
    
    # Validar fase
    if condicoes.get('fase') is not None:
        validador = condicoes['fase']
        if isinstance(validador, re.Pattern):
            if not validador.search(normalizar_texto(peticao.fase)):
                return False
        elif callable(validador):
            if not validador(peticao.fase):
                return False
    
    return True


# ============================================================================
# REGRAS E AÇÕES
# ============================================================================

def normalizar_texto(txt: str) -> str:
    """Normaliza texto para comparações (lowercase, sem acentos)"""
    import unicodedata
    txt = txt.lower().strip()
    # Remove acentos
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt


def gerar_regex_flexivel(termo: str) -> re.Pattern:
    """Gera regex flexível para um termo (padrão p2b.py)"""
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()
    partes = [re.escape(p) for p in palavras]
    
    regex = ''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()]*'
    
    return re.compile(rf"{regex}", re.IGNORECASE)


def acao_apagar(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """
    Ação: APAGAR petição da tabela.
    
    Steps:
    1. Localizar linha do processo na tabela
    2. Clicar ícone trash: <i class="fas fa-trash-alt icone-tamanho-18"></i>
    3. Confirmar com ESPAÇO
    """
    try:
        # Aguardar tabela estar visível
        time.sleep(0.5)
        
        # Localizar a linha do processo
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.cdk-drag")
        linha_encontrada = None
        
        for linha in linhas:
            tds = linha.find_elements(By.TAG_NAME, "td")
            if len(tds) > 1:
                texto_td1 = tds[1].text.strip()
                if peticao.numero_processo in texto_td1:
                    linha_encontrada = linha
                    break
        
        if not linha_encontrada:
            logger.warning(f"[PET_APAG] Linha não encontrada para {peticao.numero_processo}")
            return False
        
        # Localizar ícone trash na linha
        try:
            trash_icon = linha_encontrada.find_element(By.CSS_SELECTOR, "i.fa-trash-alt")
        except NoSuchElementException:
            logger.warning(f"[PET_APAG] Ícone trash não encontrado em {peticao.numero_processo}")
            return False
        
        # Clicar no trash
        print(f"[PET_APAG] Clicando lixeira de {peticao.numero_processo}...")
        driver.execute_script("arguments[0].scrollIntoView(true);", trash_icon)
        time.sleep(0.3)
        trash_icon.click()
        time.sleep(0.5)
        
        # Confirmar com ESPAÇO
        print(f"[PET_APAG] Confirmando exclusão com ESPAÇO...")
        from selenium.webdriver.common.keys import Keys
        driver.switch_to.active_element().send_keys(Keys.SPACE)
        time.sleep(1)
        
        print(f"[PET_APAG] ✅ {peticao.numero_processo} apagado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"[PET_APAG] ❌ Erro ao apagar {peticao.numero_processo}: {e}")
        return False


def agrupar_por_hipotese(peticoes: List[PeticaoLinha]) -> Dict[str, Dict[str, List[PeticaoLinha]]]:
    """
    Agrupa petições por hipótese da regra APAGAR.
    
    Retorna:
    {
        'RAZOES_FINAIS': [...peticoes...],
        'REPLICA_CONHECIMENTO': [...peticoes...],
        'ACORDO': [...peticoes...]
    }
    """
    regras = definir_regras_apagar()
    grupos = {}
    
    for regra in regras:
        hipotese_id = regra['hipotese_id']
        condicoes = regra['condicoes']
        
        # Encontrar petições que satisfazem essa hipótese
        peticoes_hipotese = []
        for peticao in peticoes:
            if verifica_condicoes(peticao, condicoes):
                peticoes_hipotese.append(peticao)
        
        grupos[hipotese_id] = {
            'hipotese_nome': regra['hipotese_nome'],
            'peticoes': peticoes_hipotese,
            'acao': regra['acao']
        }
    
    return grupos


def executar_grupo_apagar(driver: WebDriver, grupos_hipoteses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executa a regra APAGAR sequencialmente por hipótese.
    
    Steps:
    1. Para cada hipótese em ordem
    2. Para cada petição na hipótese
    3. Executar ação_apagar
    4. Atualizar progresso em pet.json
    5. Log estruturado por hipótese
    """
    
    resultado = {
        'bloco': 'APAGAR',
        'bloco_nome': 'Limpeza de Petições',
        'hipoteses_processadas': [],
        'total_apagados': 0,
        'total_erros': 0
    }
    
    print("\n" + "="*80)
    print("[PET_APAG] INICIANDO EXECUÇÃO: Limpeza de Petições")
    print("="*80)
    
    for hipotese_id, hipotese_dados in grupos_hipoteses.items():
        hipotese_nome = hipotese_dados['hipotese_nome']
        peticoes = hipotese_dados['peticoes']
        acao = hipotese_dados['acao']
        
        print(f"\n[PET_APAG] HIPÓTESE: {hipotese_nome}")
        print(f"[PET_APAG]   Processos encontrados: {len(peticoes)}")
        
        hipotese_resultado = {
            'hipotese_id': hipotese_id,
            'hipotese_nome': hipotese_nome,
            'total': len(peticoes),
            'executados': 0,
            'falhados': 0,
            'processos_executados': [],
            'processos_falhados': []
        }
        
        # Executar cada petição
        for idx, peticao in enumerate(peticoes, 1):
            print(f"[PET_APAG]   [{idx}/{len(peticoes)}] {peticao.numero_processo}...", end=" ")
            
            try:
                sucesso = acao(driver, peticao)
                
                if sucesso:
                    print("✅")
                    hipotese_resultado['executados'] += 1
                    hipotese_resultado['processos_executados'].append(peticao.numero_processo)
                    marcar_hipotese_executada('APAGAR', hipotese_id, peticao.numero_processo, sucesso=True)
                    resultado['total_apagados'] += 1
                else:
                    print("❌")
                    hipotese_resultado['falhados'] += 1
                    hipotese_resultado['processos_falhados'].append(peticao.numero_processo)
                    marcar_hipotese_executada('APAGAR', hipotese_id, peticao.numero_processo, sucesso=False)
                    resultado['total_erros'] += 1
                
            except Exception as e:
                print(f"❌ ({e})")
                hipotese_resultado['falhados'] += 1
                hipotese_resultado['processos_falhados'].append(peticao.numero_processo)
                resultado['total_erros'] += 1
                logger.error(f"[PET_APAG] Erro ao processar {peticao.numero_processo}: {e}")
        
        # Atualizar status da hipótese
        if hipotese_resultado['falhados'] == 0 and hipotese_resultado['executados'] > 0:
            hipotese_resultado['status'] = 'completo'
        elif hipotese_resultado['executados'] > 0:
            hipotese_resultado['status'] = 'com_erros'
        else:
            hipotese_resultado['status'] = 'nao_iniciado'
        
        print(f"[PET_APAG]   Resultado: {hipotese_resultado['executados']} apagados, {hipotese_resultado['falhados']} erros")
        resultado['hipoteses_processadas'].append(hipotese_resultado)
    
    # Resumo final
    print("\n" + "="*80)
    print(f"[PET_APAG] ✅ EXECUÇÃO FINALIZADA")
    print(f"[PET_APAG]   Total apagados: {resultado['total_apagados']}")
    print(f"[PET_APAG]   Total erros: {resultado['total_erros']}")
    print("="*80 + "\n")
    
    return resultado


# ============================================================================
# FLUXO PRINCIPAL
# ============================================================================

def executar_fluxo_pet(driver: WebDriver) -> bool:
    """
    Orquestrador principal do fluxo PET:
    1. Navegação inicial
    2. Extração de tabela
    3. Agrupamento por hipótese
    4. Execução do grupo APAGAR
    """
    try:
        print("\n" + "="*80)
        print("INICIANDO FLUXO PET (Petições Juntadas)")
        print("="*80 + "\n")
        
        # 1. Navegação
        if not navegacao_inicial_pet(driver):
            print("[PET] ❌ Falha na navegação inicial")
            return False
        
        # 2. Extração
        peticoes = extrair_tabela_peticoes(driver)
        if not peticoes:
            print("[PET] ❌ Nenhuma petição extraída")
            return False
        
        print(f"[PET] ✅ {len(peticoes)} petições extraídas")
        
        # 3. Agrupamento por hipótese (REGRA APAGAR)
        grupos_hipoteses = agrupar_por_hipotese(peticoes)
        
        # 4. Executar grupo APAGAR
        resultado_apagar = executar_grupo_apagar(driver, grupos_hipoteses)
        
        print("[PET] ✅ Fluxo completado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"[PET] Erro no fluxo principal: {e}")
        traceback.print_exc()
        return False


if __name__ == '__main__':
    """
    Execução standalone de pet.py
    """
    from Prazo.prov import criar_driver
    from Fix.utils import login_cpf
    from Fix.core import finalizar_driver
    
    driver = None
    try:
        print('[PET] Iniciando fluxo de petições...')
        
        # Criar driver
        driver = criar_driver(headless=False)
        if not driver:
            print('[PET] ❌ Falha ao criar driver')
            exit(1)
        
        # Login
        print('[PET] Realizando login...')
        if not login_cpf(driver):
            print('[PET] ❌ Falha no login')
            exit(1)
        
        # Executar fluxo
        sucesso = executar_fluxo_pet(driver)
        
        if sucesso:
            print('[PET] ✅ Fluxo finalizado com sucesso')
        else:
            print('[PET] ❌ Fluxo falhou')
            exit(1)
            
    except Exception as e:
        print(f'[PET] ❌ Erro: {e}')
        traceback.print_exc()
        exit(1)
    finally:
        if driver:
            try:
                finalizar_driver(driver)
                print('[PET] Driver fechado')
            except Exception:
                pass

if __name__ == "__main__":
    print("[PET] Módulo PEC/pet.py carregado")
    print("[PET] Use executar_fluxo_pet(driver) para iniciar o processamento")
