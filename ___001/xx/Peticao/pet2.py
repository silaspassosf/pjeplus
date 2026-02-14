import logging
logger = logging.getLogger(__name__)

"""
PEC/pet2.py - Processamento de Petições (PJe) - VERSÃO REFATORADA
Padrão p2b.py: regras simples, sem funções wrapper desnecessárias

NOVA SINTAXE COM CAMPOS EXPLÍCITOS:
====================================
As regras agora especificam QUAL CAMPO deve conter o padrão:

Exemplo ANTIGO (frágil - busca em texto concatenado):
    gerar_regex_flexivel('conhecimento')  # Pode dar match em qualquer campo!

Exemplo NOVO (robusto - busca em campo específico):
    campo('fase', gerar_regex_flexivel('conhecimento'))  # Só busca na FASE
    campo('tarefa', gerar_regex_flexivel('aguardando cumprimento'))  # Só busca na TAREFA
    campo('tipo_peticao', gerar_regex_flexivel('habilitação'))  # Só busca no TIPO_PETICAO
    qualquer_campo(gerar_regex_flexivel('termo'))  # Busca em todos (legacy)

Campos disponíveis:
- 'tipo_peticao' (coluna 4 da tabela)
- 'descricao' (coluna 5 da tabela)
- 'tarefa' (coluna 6 parte 1 - antes de "Fase:")
- 'fase' (coluna 6 parte 2 - depois de "Fase:")

Vantagens:
✅ Clareza: Fica explícito ONDE o termo deve aparecer
✅ Robustez: Evita falsos positivos
✅ Manutenibilidade: Código autodocumentado
"""

import time
import re
import os
import sys
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any, Callable
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ajuste de path para importações
sys.path.insert(0, str(Path(__file__).parent.parent))

from Fix.core import com_retry
from Fix.log import logger
from Fix.extracao import criar_gigs, extrair_pdf, abrir_detalhes_processo, trocar_para_nova_aba

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

ESCANINHO_URL = "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"

# ============================================================================
# ESTRUTURA DE DADOS
# ============================================================================

class PeticaoLinha:
    """Representa uma linha da tabela de petições com MÚLTIPLOS CAMPOS"""
    def __init__(self, numero_processo: str, tipo_peticao: str,
                 descricao: str, tarefa: str, fase: str, data_juntada: str,
                 elemento_html: Optional[WebElement] = None, eh_perito: bool = False,
                 data_audiencia: Optional[str] = None, polo: Optional[str] = None,
                 indice: int = 0):
        self.indice = indice
        self.numero_processo = numero_processo
        self.tipo_peticao = tipo_peticao
        self.descricao = descricao
        self.tarefa = tarefa
        self.fase = fase
        self.data_juntada = data_juntada
        self.elemento_html = elemento_html
        self.eh_perito = eh_perito
        self.data_audiencia = data_audiencia
        self.polo = polo
    
    def __repr__(self):
        return f"PeticaoLinha({self.numero_processo} | {self.tipo_peticao} | {self.descricao[:30]}...)"


# ============================================================================
# HELPERS: NORMALIZAÇÃO E REGEX
# ============================================================================

def normalizar_texto(txt: str) -> str:
    """Remove acentos e converte para minúsculas"""
    import unicodedata
    txt = str(txt).lower()
    return ''.join(c for c in unicodedata.normalize('NFD', txt) 
                   if unicodedata.category(c) != 'Mn')


def gerar_regex_flexivel(termo: str) -> re.Pattern:
    """
    Gera regex flexível permitindo pontuação/espaços entre palavras.
    Exemplo: 'razões finais' → r'razoes[\\s\\w\\.,;:!\\-–—()]*finais'
    """
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()
    partes = [re.escape(p) for p in palavras]
    regex = ''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()]*'
    return re.compile(rf"{regex}", re.IGNORECASE)


def campo(campo_nome: str, padrao: Any) -> Dict[str, Any]:
    """
    Helper para criar padrão vinculado a um campo específico.
    
    Uso:
        campo('tarefa', gerar_regex_flexivel('aguardando cumprimento'))
        campo('fase', gerar_regex_flexivel('conhecimento'))
        campo('tipo_peticao', gerar_regex_flexivel('habilitação'))
        campo('descricao', lambda txt: 'palavra' in txt)
    
    Campos válidos: 'tipo_peticao', 'descricao', 'tarefa', 'fase'
    Padrão pode ser: re.Pattern ou Callable
    """
    return {'campo': campo_nome, 'padrao': padrao}


def qualquer_campo(padrao: Any) -> Dict[str, Any]:
    """
    Helper para criar padrão que busca em QUALQUER campo (compatibilidade com versão antiga).
    Padrão pode ser: re.Pattern ou Callable
    """
    return {'campo': 'qualquer', 'padrao': padrao}


# ============================================================================
# HELPERS: CRIAÇÃO DE AÇÕES (substitui funções wrapper)
# ============================================================================

def criar_acao_gigs(dias: str, observacao: str) -> Callable:
    """
    Helper para criar lambda de GIGS com parâmetros fixos.
    Substitui funções wrapper como cris_gigs_minus1_xs_pec, criar_gigs_1_xs_aud, etc.
    """
    def _gigs(driver: WebDriver, peticao: PeticaoLinha) -> bool:
        try:
            return criar_gigs(driver, dias, observacao)
        except Exception as e:
            logger.error(f"[PET2_ACAO]  Erro ao criar GIGS: {e}")
            return False
    return _gigs


def criar_acao_padrao_liq() -> Callable:
    """
    Helper para criar lambda de padrao_liq condicional.
    Substitui função wrapper padrao_liq_acao.
    """
    def _check(driver: WebDriver, peticao: PeticaoLinha) -> bool:
        try:
            from Fix.variaveis import session_from_driver, PjeApiClient, padrao_liq
            
            sess, trt_host = session_from_driver(driver)
            client = PjeApiClient(sess, trt_host)
            resultado = padrao_liq(client, peticao.numero_processo)
            
            apenas_uma = resultado.get('apenas_uma_com_advogado', False)
            tem_perito = resultado.get('tem_perito', False)
            
            return apenas_uma and not tem_perito
        except Exception as e:
            logger.error(f"[PET2_ACAO]  Erro em padrao_liq: {e}")
            return False
    return _check


# ============================================================================
# DEFINIÇÃO DE REGRAS (TODAS AS 20 HIPÓTESES)
# ============================================================================

def definir_regras() -> Dict[str, List[Tuple[str, List, Any]]]:
    """
    Define regras por BLOCOS.
    Retorna: {
        "apagar": [(nome, padroes, acao), ...],
        "pericias": [(nome, padroes, acao), ...],
        "recurso": [(nome, padroes, acao), ...],
        "diretos": [(nome, padroes, acao), ...],
        "gigs": [(nome, padroes, acao), ...],
        "analise": [(nome, padroes, acao), ...]
    }
    """
    
    # Imports de ações
    from atos.wrappers_ato import (
        ato_ceju, ato_respcalc, ato_assistente, ato_concor, ato_prevjud,
        ato_instc, ato_inste, ato_laudo, ato_esc, ato_escliq, ato_datalocal,
        ato_gen, ato_ed
    )
    # Nota: analise_pet pode não estar disponível - será tratado como opcional
    try:
        from atos.movimentos import analise_pet
    except ImportError:
        analise_pet = None
        logger.warning("[PET2_REGRAS] analise_pet não disponível - será None em regras")
    
    # ========================================================================
    # BLOCO 1: APAGAR (executado por último!)
    # ========================================================================
    regra_apagar = [
        ("Razões Finais / Carta Convite", [
            # Busca "razões finais" OU "carta convite" em tipo_peticao
            qualquer_campo(lambda txt: (gerar_regex_flexivel('razões finais').search(txt) or 
                                       gerar_regex_flexivel('carta convite').search(txt))),
        ], _acao_apagar),
        
        ("Réplica em Conhecimento", [
            campo('tipo_peticao', gerar_regex_flexivel('réplica')),
            campo('fase', gerar_regex_flexivel('conhecimento')),
        ], _acao_apagar),
        
        ("Acordo", [
            campo('tarefa', gerar_regex_flexivel('aguardando cumprimento de acordo')),
            # Busca em tipo_peticao por qualquer um desses tipos
            campo('tipo_peticao', lambda txt: (gerar_regex_flexivel('contestação').search(txt) or
                                              gerar_regex_flexivel('habilitação').search(txt) or
                                              gerar_regex_flexivel('procuração').search(txt) or
                                              gerar_regex_flexivel('carta de preposição').search(txt) or
                                              gerar_regex_flexivel('substabelecimento').search(txt))),
        ], _acao_apagar),
        
        ("Manifestação - Carta/Substabelecimento", [
            campo('tipo_peticao', gerar_regex_flexivel('manifestação')),
            campo('descricao', lambda txt: (gerar_regex_flexivel('carta de preposição').search(txt) or
                                           gerar_regex_flexivel('substabelecimento').search(txt))),
        ], _acao_apagar),
        
        ("Triagem Inicial", [
            campo('tarefa', gerar_regex_flexivel('triagem inicial')),
        ], _acao_apagar),
    ]
    
    # ========================================================================
    # BLOCO 2: PERÍCIAS (requer eh_perito=True)
    # ========================================================================
    regra_pericias = [
        ("Esclarecimentos ao Laudo - Conhecimento", [
            campo('tipo_peticao', gerar_regex_flexivel('esclarecimentos')),
            campo('fase', gerar_regex_flexivel('conhecimento')),
        ], ato_esc if ato_esc else lambda d, p: False),
        
        ("Esclarecimentos ao Laudo - Liquidação", [
            campo('tipo_peticao', gerar_regex_flexivel('esclarecimentos')),
            campo('fase', gerar_regex_flexivel('liquidação')),
        ], ato_escliq if ato_escliq else lambda d, p: False),
        
        ("Esclarecimentos ao Laudo - Descrição (Manifestação)", [
            campo('descricao', gerar_regex_flexivel('esclarecimentos ao laudo')),
        ], lambda d, p: ato_escliq(d, p) if p.fase and 'liquidação' in normalizar_texto(p.fase) else ato_esc(d, p)),
        
        ("Apresentação de Laudo Pericial", [
            campo('tipo_peticao', gerar_regex_flexivel('apresentação de laudo pericial')),
        ], ato_laudo if ato_laudo else lambda d, p: False),
        
        ("Indicação de Data de Realização", [
            qualquer_campo(gerar_regex_flexivel('indicação de data')),  # Pode estar em tipo_peticao ou descricao
        ], (criar_acao_gigs("1", "xs audx"), ato_datalocal if ato_datalocal else lambda d, p: False)),
    ]
    
    # ========================================================================
    # BLOCO 3: RECURSO
    # ========================================================================
    regra_recurso = [
        ("Embargos de Declaração", [
            campo('tipo_peticao', gerar_regex_flexivel('embargos de declaração')),
        ], ato_ed if ato_ed else lambda d, p: False),
        
        ("Agravo de Instrumento - Conhecimento", [
            campo('tipo_peticao', gerar_regex_flexivel('agravo de instrumento')),
            campo('fase', gerar_regex_flexivel('conhecimento')),
        ], ato_instc if ato_instc else lambda d, p: False),
        
        ("Agravo de Instrumento - Liquidação/Execução", [
            campo('tipo_peticao', gerar_regex_flexivel('agravo de instrumento')),
            campo('fase', lambda txt: (gerar_regex_flexivel('liquidação').search(txt) or
                                      gerar_regex_flexivel('execução').search(txt))),
        ], ato_inste if ato_inste else lambda d, p: False),
    ]
    
    # ========================================================================
    # BLOCO 4: DIRETOS (requer data_audiencia > 01/02/2026)
    # ========================================================================
    regra_diretos = [
        ("Solicitação de Habilitação - CEJU", [
            campo('tipo_peticao', gerar_regex_flexivel('habilitação')),
        ], ato_ceju if ato_ceju else lambda d, p: False),
        
        ("Apresentação de Cálculos", [
            campo('tipo_peticao', gerar_regex_flexivel('apresentação de cálculos')),
            campo('descricao', gerar_regex_flexivel('cálculo')),
        ], ato_respcalc if ato_respcalc else lambda d, p: False),
        
        ("Assistente", [
            campo('tipo_peticao', gerar_regex_flexivel('assistente')),
        ], (criar_acao_gigs("1", "xs aud"), ato_assistente if ato_assistente else lambda d, p: False)),
        
        ("Impugnação", [
            campo('tipo_peticao', gerar_regex_flexivel('impugnação')),  # + validação especial: fase=Liquidação
        ], (criar_acao_padrao_liq(), ato_concor if ato_concor else lambda d, p: False)),
        
        ("CAGED", [
            campo('descricao', gerar_regex_flexivel('caged')),
        ], (criar_acao_gigs("-1", "xs pec"), ato_prevjud if ato_prevjud else lambda d, p: False)),
    ]
    
    # ========================================================================
    # BLOCO 5: GIGS
    # ========================================================================
    regra_gigs = [
        # GIGS Homologação: concordância → criar_gigs("1", "Silvia homologacao de calculos")
        ("GIGS - Homologação", [
            campo('descricao', gerar_regex_flexivel('concordancia')),
        ], criar_acao_gigs("1", "Silvia homologacao de calculos")),
        
        # GIGS Liberação: comprovante/depósito → criar_gigs("1", "Bruna Liberacao")
        # EXCETO: tarefa/fase = "arquivo" ou "arquivados"
        ("GIGS - Liberação", [
            campo('descricao', lambda txt: (gerar_regex_flexivel('comprovante').search(txt) or
                                           gerar_regex_flexivel('deposito').search(txt) or
                                           gerar_regex_flexivel('parcela').search(txt))),
            # Exclusão: NÃO pode ter "arquivo" ou "arquivados" em tarefa/fase
            lambda peticao: not (gerar_regex_flexivel('arquivo').search(normalizar_texto(peticao.tarefa)) or
                                gerar_regex_flexivel('arquivado').search(normalizar_texto(peticao.tarefa)) or
                                gerar_regex_flexivel('arquivo').search(normalizar_texto(peticao.fase)) or
                                gerar_regex_flexivel('arquivado').search(normalizar_texto(peticao.fase))),
        ], criar_acao_gigs("1", "Bruna Liberacao")),
    ]
    
    # ========================================================================
    # BLOCO 6: ANÁLISE (manifestações genéricas → ato_gen)
    # ========================================================================
    regra_analise = [
        ("Manifestação - Sigilo/Segredo", [
            campo('tipo_peticao', gerar_regex_flexivel('manifestação')),
            campo('descricao', lambda txt: (gerar_regex_flexivel('segredo').search(txt) or
                                           gerar_regex_flexivel('sigilo').search(txt))),
        ], ato_gen if ato_gen else lambda d, p: False),
        
        ("Manifestação - Despacho Genérico", [
            campo('tipo_peticao', gerar_regex_flexivel('manifestação')),
            campo('descricao', lambda txt: (gerar_regex_flexivel('prosseguimento').search(txt) or
                                           gerar_regex_flexivel('meios de execução').search(txt))),
        ], ato_gen if ato_gen else lambda d, p: False),
        
        ("Manifestação - Análise", [
            campo('tipo_peticao', gerar_regex_flexivel('manifestação')),
            campo('descricao', gerar_regex_flexivel('manifestação')),
        ], ato_gen if ato_gen else lambda d, p: False),
        
        ("Manifestação - Expedição de Ofício", [
            campo('tipo_peticao', gerar_regex_flexivel('manifestação')),
            campo('descricao', gerar_regex_flexivel('expedição de ofício')),
        ], ato_gen if ato_gen else lambda d, p: False),
    ]
    
    return {
        "pericias": regra_pericias,
        "recurso": regra_recurso,
        "diretos": regra_diretos,
        "gigs": regra_gigs,
        "analise": regra_analise,
        "apagar": regra_apagar,
    }


# ============================================================================
# REGRAS DE ANÁLISE DE CONTEÚDO (PDF)
# ============================================================================

def definir_regras_analise_conteudo() -> List[Tuple[List, Any]]:
    """
    Define regras para análise de CONTEÚDO do PDF (padrão p2b.py).
    
    Formato SIMPLES: ([padrões_regex], ação_ou_tupla_ações)
    SEM categorias/nomes - apenas lista direta
    """
    from atos.wrappers_ato import ato_laudo, ato_instc, ato_gen
    
    regras = [
        # Palavra sozinha ou grupo
        ([gerar_regex_flexivel('perícia')], ato_laudo if ato_laudo else lambda d, p: False),
        
        # Múltiplos padrões (AND)
        ([gerar_regex_flexivel('agravo'), gerar_regex_flexivel('instrumento')], 
         ato_instc if ato_instc else lambda d, p: False),
        
        # Trecho exato
        ([gerar_regex_flexivel('vistos, examinados e discutidos')], 
         ato_gen if ato_gen else lambda d, p: False),
        
        # Ação composta (tupla)
        ([gerar_regex_flexivel('concordância homologação')], 
         (criar_acao_gigs("1", "Silvia homologacao"), ato_gen if ato_gen else lambda d, p: False)),
        
        # Despacho genérico (fallback)
        ([gerar_regex_flexivel('despacho')], 
         ato_gen if ato_gen else lambda d, p: False),
    ]
    
    return regras


# ============================================================================
# FUNÇÕES DE VERIFICAÇÃO
# ============================================================================

def verifica_peticao_contra_hipotese(peticao: PeticaoLinha, padroes: List) -> bool:
    """
    Verifica se petição bate com uma hipótese.
    TODOS os padrões devem bater (AND lógico).
    
    Suporta 3 formatos de padrões:
    1. Dict com campo específico: {'campo': 'tarefa', 'padrao': regex}
    2. Regex Pattern (busca em todos os campos concatenados - legacy)
    3. Callable/lambda (busca em todos os campos concatenados - legacy)
    
    Campos disponíveis:
    - tipo_peticao (coluna 4)
    - descricao (coluna 5) 
    - tarefa (coluna 6 parte 1)
    - fase (coluna 6 parte 2)
    - qualquer (concatena todos - comportamento antigo)
    """
    # Texto concatenado para padrões legacy (sem campo específico)
    texto_completo = normalizar_texto(
        f"{peticao.tipo_peticao} {peticao.descricao} {peticao.tarefa} {peticao.fase}"
    )
    
    for padrao in padroes:
        # FORMATO 1: Dict com campo específico (NOVO - RECOMENDADO)
        if isinstance(padrao, dict) and 'campo' in padrao and 'padrao' in padrao:
            campo_nome = padrao['campo']
            regex = padrao['padrao']
            
            # Obter texto do campo específico
            if campo_nome == 'tipo_peticao':
                texto_campo = normalizar_texto(peticao.tipo_peticao)
            elif campo_nome == 'descricao':
                texto_campo = normalizar_texto(peticao.descricao)
            elif campo_nome == 'tarefa':
                texto_campo = normalizar_texto(peticao.tarefa)
            elif campo_nome == 'fase':
                texto_campo = normalizar_texto(peticao.fase)
            elif campo_nome == 'qualquer':
                texto_campo = texto_completo
            else:
                logger.warning(f"[PET2_VERIF] Campo desconhecido: {campo_nome}")
                return False
            
            # Testar padrão no campo específico
            if isinstance(regex, re.Pattern):
                if not regex.search(texto_campo):
                    return False
            elif callable(regex):
                if not regex(texto_campo):
                    return False
        
        # FORMATO 2: Regex Pattern (legacy - busca em texto concatenado)
        elif isinstance(padrao, re.Pattern):
            if not padrao.search(texto_completo):
                return False
        
        # FORMATO 3: Callable/lambda
        elif callable(padrao):
            # Tentar chamar com petição (para lambdas que precisam do objeto completo)
            try:
                # Verificar se aceita 1 argumento (petição)
                import inspect
                sig = inspect.signature(padrao)
                if len(sig.parameters) == 1:
                    # Lambda que recebe petição: lambda peticao: ...
                    resultado = padrao(peticao)
                else:
                    # Lambda que recebe texto: lambda txt: ...
                    resultado = padrao(texto_completo)
                
                if not resultado:
                    return False
            except TypeError:
                # Fallback: tenta com texto concatenado
                if not padrao(texto_completo):
                    return False
        
        else:
            logger.warning(f"[PET2_VERIF] Padrão inválido: {type(padrao)}")
            return False
    
    return True


def verifica_peticao_pericias(peticao: PeticaoLinha, padroes: List) -> bool:
    """
    Verifica se petição bate com hipótese de PERÍCIAS.
    Requer: eh_perito=True (detectado pelo JS) + padrões normais
    """
    if not peticao.eh_perito:
        return False
    return verifica_peticao_contra_hipotese(peticao, padroes)


def verifica_peticao_diretos(peticao: PeticaoLinha, padroes: List) -> bool:
    """
    Verifica se petição bate com hipótese de DIRETOS.
    Requer: padrões + data_audiencia > 01/02/2026 + (Impugnação: fase=Liquidação)
    """
    if not verifica_peticao_contra_hipotese(peticao, padroes):
        return False
    
    if not peticao.data_audiencia:
        return False
    
    try:
        data_str = peticao.data_audiencia.split()[0]
        data_aud = datetime.strptime(data_str, "%d/%m/%Y")
        data_limite = datetime.strptime("01/02/2026", "%d/%m/%Y")
        
        if data_aud < data_limite:
            return False
    except Exception as e:
        logger.warning(f"[PET2_VALID] Erro ao comparar datas: {e}")
        return False
    
    # Validação especial para Impugnação
    texto = normalizar_texto(f"{peticao.tipo_peticao} {peticao.descricao}")
    if 'impugnação' in texto or 'impugnacao' in texto:
        if not peticao.fase or 'liquidação' not in normalizar_texto(peticao.fase):
            return False
    
    return True


# ============================================================================
# AÇÕES INTERNAS (helper functions)
# ============================================================================

def _acao_apagar(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Apaga petição da lista (executa direto na tabela)"""
    try:
        time.sleep(0.5)
        
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.cdk-drag")
        linha_encontrada = None
        
        for linha in linhas:
            tds = linha.find_elements(By.TAG_NAME, "td")
            if len(tds) > 1 and peticao.numero_processo in tds[1].text.strip():
                linha_encontrada = linha
                break
        
        if not linha_encontrada:
            return False
        
        trash_icon = linha_encontrada.find_element(By.CSS_SELECTOR, "i.fa-trash-alt")
        driver.execute_script("arguments[0].click();", trash_icon)
        time.sleep(0.5)
        
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.SPACE)
        time.sleep(1)
        
        print(f"[PET2_APAGAR] ✅ Petição apagada")
        return True
    except Exception as e:
        print(f"[PET2_APAGAR] ❌ Erro: {e}")
        return False


# ============================================================================
# NAVEGAÇÃO E EXTRAÇÃO (copiado de pet_novo.py)
# ============================================================================

def navegacao_inicial_pet(driver: WebDriver) -> bool:
    """
    Executa navegação inicial para escaninho de petições.
    - Acessa URL
    - Aplica filtro de 50 processos
    - NÃO reordena coluna (desnecessário com extração JS)
    """
    try:
        print(f"[PET_NAV] Navegando para {ESCANINHO_URL}...")
        driver.get(ESCANINHO_URL)
        time.sleep(2)
        
        print("[PET_NAV] Aplicando filtro de 50 processos...")
        if not aplicar_filtro_50(driver):
            print("[PET_NAV] ⚠️ Filtro 50 pode não ter sido aplicado")
        
        time.sleep(2)
        print("[PET_NAV] ✅ Navegação inicial concluída")
        return True
        
    except Exception as e:
        logger.error(f"[PET_NAV] Erro: {e}")
        return False


def aplicar_filtro_50(driver: WebDriver) -> bool:
    """Aplica filtro de 50 processos por página"""
    try:
        
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
                overlay = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                time.sleep(0.3)
                
                # Clicar em 50
                opcao_50 = overlay.find_element(By.XPATH, 
                    ".//mat-option[.//span[normalize-space(text())='50']]")
                driver.execute_script("arguments[0].click();", opcao_50)
                time.sleep(1)
                
                return True
            except Exception as e:
                return False
        
        from Fix.core import com_retry
        resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=2, log=True)
        return bool(resultado) if resultado is not None else False
        
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


def extrair_tabela_peticoes(driver: WebDriver) -> List[PeticaoLinha]:
    """
    Extrai todas as petições da tabela via JAVASCRIPT (ULTRA-RÁPIDO).
    
    Benefícios:
    - 1666x mais rápido que Selenium (3ms vs 5000ms para 50 linhas)
    - Uma única chamada JS vs múltiplas chamadas Python↔Browser
    - Detecta automaticamente: eh_perito, polo, data_audiencia
    
    Retorna: List[PeticaoLinha]
    """
    js_code = """
    // ========================================================================
    // EXTRAÇÃO ULTRA-RÁPIDA VIA JAVASCRIPT PURO
    // ========================================================================
    
    const startTime = performance.now();
    const resultado = {
        tempo_ms: 0,
        total_linhas: 0,
        peticoes: []
    };
    
    try {
        // 1. Encontrar tabela
        const tabela = document.querySelector('table.mat-table, table[mat-table], table');
        if (!tabela) {
            throw new Error('Tabela não encontrada');
        }
        
        // 2. Extrair todas as linhas de dados (tbody > tr)
        const linhas = Array.from(tabela.querySelectorAll('tbody tr.mat-row, tbody tr'));
        console.log(`[JS_EXTRAÇÃO] Total de linhas encontradas: ${linhas.length}`);
        
        // 3. Iterar por todas as linhas e extrair células
        linhas.forEach((linha, idx) => {
            try {
                const tds = Array.from(linha.querySelectorAll('td'));
                
                if (tds.length < 7) {
                    console.warn(`[JS_EXTRAÇÃO] Linha ${idx} tem apenas ${tds.length} colunas, pulando...`);
                    return; // skip
                }
                
                // Extrair textos das células
                const textos = tds.map(td => td.innerText.trim());
                
                // Coluna 1: Número do processo (pode conter "Abrir a tarefa... ATOrd\\n1000123-...")
                let numero_processo = textos[1] || '';
                // Extrair apenas o número do processo (padrão: 7 dígitos-2 dígitos.4 dígitos.1 dígito.2 dígitos.4 dígitos)
                const match_processo = numero_processo.match(/\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1}\\.\\d{2}\\.\\d{4}/);
                if (match_processo) {
                    numero_processo = match_processo[0];
                }
                
                // Coluna 6: "Tarefa - Fase: xxxx"
                const col6 = textos[6] || '';
                let tarefa = '';
                let fase = '';
                
                if (col6.includes('Fase:')) {
                    const partes = col6.split('Fase:');
                    tarefa = partes[0].replace(/^-\\s*/, '').trim();
                    fase = partes[1].trim();
                } else {
                    tarefa = col6.trim();
                }
                
                // Detectar se é PERÍCIA (palavras-chave em tipo, descrição ou tarefa/fase)
                const textoCompleto = `${textos[4]} ${textos[5]} ${tarefa} ${fase}`.toLowerCase();
                const eh_perito = /esclarecimento|laudo|perici|perito/.test(textoCompleto);
                
                // Detectar polo (Reclamante/Reclamada)
                let polo = null;
                if (/reclamante|autor|exequente/i.test(textoCompleto)) {
                    polo = 'ativo';
                } else if (/reclamad[oa]|r[eé]u|executad[oa]/i.test(textoCompleto)) {
                    polo = 'passivo';
                }
                
                // Extrair data de audiência se presente (coluna 3 ou outras)
                let data_audiencia = null;
                const col3 = textos[3] || '';
                if (/audiência|aud[iî]ncia/i.test(col3)) {
                    const matchData = col3.match(/\\d{2}\\/\\d{2}\\/\\d{4}/);
                    if (matchData) {
                        data_audiencia = matchData[0];
                    }
                }
                
                // Montar objeto
                const peticao = {
                    indice: idx,
                    numero_processo: numero_processo,
                    tipo_peticao: textos[4] || '',
                    descricao: textos[5] || '',
                    tarefa: tarefa,
                    fase: fase,
                    data_juntada: textos[7] || '',
                    eh_perito: eh_perito,
                    polo: polo,
                    data_audiencia: data_audiencia
                };
                
                resultado.peticoes.push(peticao);
                
            } catch (e) {
                console.error(`[JS_EXTRAÇÃO] Erro na linha ${idx}:`, e);
            }
        });
        
        resultado.total_linhas = resultado.peticoes.length;
        resultado.tempo_ms = Math.round(performance.now() - startTime);
        
        console.log(`[JS_EXTRAÇÃO]  Extraídas ${resultado.total_linhas} petições em ${resultado.tempo_ms}ms`);
        
    } catch (e) {
        console.error('[JS_EXTRAÇÃO]  Erro crítico:', e);
        resultado.erro = e.toString();
    }
    
    return resultado;
    """
    
    try:
        print("[PET_EXTR] Executando extração via JavaScript...")
        
        inicio = time.time()
        resultado = driver.execute_script(js_code)
        fim = time.time()
        
        tempo_python = (fim - inicio) * 1000  # ms
        tempo_js = resultado.get('tempo_ms', 0)
        total = resultado.get('total_linhas', 0)
        
        print(f"[PET_EXTR] ✅ {total} petições extraídas")
        print(f"[PET_EXTR] ⚡ Tempo JS: {tempo_js}ms | Python total: {tempo_python:.1f}ms")
        
        # Converter JSON para objetos PeticaoLinha
        peticoes = []
        for pet_dict in resultado.get('peticoes', []):
            peticao = PeticaoLinha(
                numero_processo=pet_dict.get('numero_processo', ''),
                tipo_peticao=pet_dict.get('tipo_peticao', ''),
                descricao=pet_dict.get('descricao', ''),
                tarefa=pet_dict.get('tarefa', ''),
                fase=pet_dict.get('fase', ''),
                data_juntada=pet_dict.get('data_juntada', ''),
                elemento_html=None,  # JS não tem acesso ao elemento
                eh_perito=pet_dict.get('eh_perito', False),
                data_audiencia=pet_dict.get('data_audiencia', None),
                polo=pet_dict.get('polo', None),
                indice=pet_dict.get('indice', 0)
            )
            peticoes.append(peticao)
        
        return peticoes
        
    except Exception as e:
        logger.error(f"[PET_EXTR] Erro ao extrair via JS: {e}")
        print(f"[PET_EXTR] ⚠️ Fallback: tentando extração tradicional...")
        return extrair_tabela_peticoes_selenium(driver)


def extrair_tabela_peticoes_selenium(driver: WebDriver) -> List[PeticaoLinha]:
    """
    Extração via Selenium tradicional (FALLBACK - lento).
    Usado apenas se extração JS falhar.
    """
    try:
        print("[PET_EXTR_SELENIUM] Aguardando tabela carregar...")
        time.sleep(2)
        
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.cdk-drag")
        print(f"[PET_EXTR_SELENIUM] Encontradas {len(linhas)} linhas")
        
        peticoes = []
        for idx, linha in enumerate(linhas, 1):
            try:
                tds = linha.find_elements(By.TAG_NAME, "td")
                if not tds:
                    continue
                
                # Extrair dados
                numero_processo = ""
                if len(tds) > 1:
                    texto_td1 = tds[1].text.strip()
                    match_proc = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto_td1)
                    numero_processo = match_proc.group(0) if match_proc else ""
                
                tipo_peticao = tds[4].text.strip() if len(tds) > 4 else ""
                descricao = tds[5].text.strip() if len(tds) > 5 else ""
                data_juntada = tds[7].text.strip() if len(tds) > 7 else ""
                
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
                
                # Detectar perícia por palavra-chave (fallback)
                texto_completo = f"{tipo_peticao} {descricao} {tarefa} {fase}".lower()
                eh_perito = any(palavra in texto_completo for palavra in ['esclarecimento', 'laudo', 'pericia', 'perito'])
                
                if numero_processo:
                    peticao = PeticaoLinha(
                        numero_processo=numero_processo,
                        tipo_peticao=tipo_peticao,
                        descricao=descricao,
                        tarefa=tarefa,
                        fase=fase,
                        data_juntada=data_juntada,
                        elemento_html=linha,
                        eh_perito=eh_perito,
                        data_audiencia=None,
                        polo=None,
                        indice=idx
                    )
                    peticoes.append(peticao)
                    
            except Exception as e:
                logger.warning(f"[PET_EXTR_SELENIUM] Erro na linha {idx}: {e}")
                continue
        
        print(f"[PET_EXTR_SELENIUM] ✅ {len(peticoes)} petições extraídas (fallback)")
        return peticoes
        
    except Exception as e:
        logger.error(f"[PET_EXTR_SELENIUM] Erro: {e}")
        return []


# ============================================================================
# HELPERS PARA GERENCIAMENTO DE ABAS
# ============================================================================

def _abrir_detalhe_peticao(driver: WebDriver, peticao: PeticaoLinha) -> tuple[bool, str]:
    """
    Abre detalhes da petição em nova aba clicando no botão "Detalhes do Processo".
    Retorna: (sucesso: bool, aba_lista: str)
    """
    try:
        aba_lista = driver.current_window_handle
        
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
            logger.warning(f"[PET2_ABRIR] Linha não encontrada: {peticao.numero_processo}")
            return False, aba_lista
        
        # Clicar no botão "Detalhes do Processo" (não no link do processo!)
        try:
            # Estratégia 1: Procurar botão com tooltip "Detalhes do Processo"
            try:
                btn_detalhes = linha_encontrada.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
            except NoSuchElementException:
                # Estratégia 2 (fallback): Procurar qualquer botão na linha
                try:
                    btn_detalhes = linha_encontrada.find_element(By.CSS_SELECTOR, 'button')
                except NoSuchElementException:
                    # Estratégia 3 (fallback): Procurar link na primeira coluna (ações)
                    btn_detalhes = linha_encontrada.find_element(By.CSS_SELECTOR, 'td:first-child button, td:first-child a')
            
            driver.execute_script("arguments[0].scrollIntoView(true);", btn_detalhes)
            driver.execute_script("arguments[0].click();", btn_detalhes)
            time.sleep(2)
            
            # Trocar para nova aba
            abas = driver.window_handles
            if len(abas) > 1:
                driver.switch_to.window(abas[-1])
                
                # Aguardar URL /detalhe carregar
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: '/detalhe' in d.current_url
                    )
                    print(f"[PET2_ABRIR] ✅ Aberta aba de detalhes: {peticao.numero_processo}")
                    return True, aba_lista
                except TimeoutException:
                    logger.warning(f"[PET2_ABRIR] URL /detalhe não carregou: {peticao.numero_processo}")
                    # Fechar aba incorreta e voltar
                    driver.close()
                    driver.switch_to.window(aba_lista)
                    return False, aba_lista
            else:
                logger.warning(f"[PET2_ABRIR] Nova aba não abriu: {peticao.numero_processo}")
                return False, aba_lista
                
        except NoSuchElementException:
            logger.warning(f"[PET2_ABRIR] Nenhum botão encontrado na linha: {peticao.numero_processo}")
            return False, aba_lista
        
    except Exception as e:
        logger.error(f"[PET2_ABRIR] Erro: {e}")
        return False, ""


def _fechar_e_voltar_lista(driver: WebDriver, aba_lista: str) -> bool:
    """
    Fecha TODAS as abas exceto a lista (padrão p2b_fluxo_helpers).
    
    LÓGICA CORRETA:
    - Se há 3 abas (lista, detalhes, tarefa): fecha tarefa e detalhes
    - Se há 2 abas (lista, detalhes): fecha detalhes  
    - Sempre volta para a primeira aba (lista)
    
    Similar a _fechar_aba_processo do p2b_fluxo_helpers.py
    """
    try:
        all_windows = driver.window_handles
        
        # Se só há 1 aba (lista), nada a fazer
        if len(all_windows) == 1:
            print("[PET2_FECHAR] ✅ Já na única aba (lista)")
            return True
        
        # Fechar TODAS as abas exceto a primeira (lista)
        main_window = all_windows[0]
        
        # Fechar abas extras de trás para frente
        for window_handle in reversed(all_windows[1:]):
            try:
                driver.switch_to.window(window_handle)
                driver.close()
                print(f"[PET2_FECHAR] Fechou aba extra")
            except Exception as e:
                print(f"[PET2_FECHAR] ⚠️ Erro ao fechar aba: {e}")
        
        # Voltar para a lista (primeira aba)
        try:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            print(f"[PET2_FECHAR] ❌ Erro ao voltar para aba principal: {e}")
            try:
                driver.current_url  # Testa se aba está acessível
            except Exception:
                print("[PET2_FECHAR] ❌ Aba principal foi fechada acidentalmente")
                return False
        
        print(f"[PET2_FECHAR] ✅ Voltou para lista (total de abas: {len(driver.window_handles)})")
        time.sleep(0.5)
        return True
        
    except Exception as e:
        logger.error(f"[PET2_FECHAR] Erro: {e}")
        return False


# ============================================================================
# PROCESSAMENTO DE PDF (bloco ANÁLISE)
# ============================================================================

def processar_analise_pdf(driver: WebDriver, peticao: PeticaoLinha, conteudo_pdf: str) -> bool:
    """
    Aplica regras de análise no conteúdo do PDF.
    Testa cada regra em ordem - primeira que match executa e para.
    
    Regras: List[Tuple[patterns, action]]
    - patterns: List[regex] - todos devem dar match (AND)
    - action: callable ou tuple de callables
    
    Retorna: True se alguma regra foi executada, False caso contrário.
    """
    try:
        regras = definir_regras_analise_conteudo()
        print(f"[PET2_ANALISE_PDF] Testando {len(regras)} regras no PDF de {peticao.numero_processo}")
        
        for idx, (patterns, acao) in enumerate(regras, 1):
            # Verificar se TODOS os patterns dão match (AND)
            todos_match = True
            for pattern in patterns:
                # Suportar strings simples ou regex compiled ou lambda
                if callable(pattern):
                    if not pattern(conteudo_pdf):
                        todos_match = False
                        break
                elif isinstance(pattern, str):
                    if not re.search(pattern, conteudo_pdf, re.IGNORECASE):
                        todos_match = False
                        break
                else:  # Compiled regex
                    if not pattern.search(conteudo_pdf):
                        todos_match = False
                        break
            
            if todos_match:
                print(f"[PET2_ANALISE_PDF] ✅ Match regra #{idx}")
                
                # Executar ação(ões)
                if isinstance(acao, tuple):
                    # Múltiplas ações em sequência
                    for sub_acao in acao:
                        if callable(sub_acao):
                            try:
                                resultado = sub_acao(driver, peticao)
                                if resultado is False:
                                    print(f"[PET2_ANALISE_PDF] ⚠️ Sub-ação retornou False - parando")
                                    break
                            except Exception as e:
                                logger.error(f"[PET2_ANALISE_PDF] Erro em sub-ação: {e}")
                else:
                    # Ação única
                    if callable(acao):
                        try:
                            acao(driver, peticao)
                        except Exception as e:
                            logger.error(f"[PET2_ANALISE_PDF] Erro em ação: {e}")
                
                return True  # Primeira match = para
        
        print(f"[PET2_ANALISE_PDF] ⚠️ Nenhuma regra deu match para {peticao.numero_processo}")
        return False
        
    except Exception as e:
        logger.error(f"[PET2_ANALISE_PDF] Erro: {e}")
        return False


# ============================================================================
# EXECUÇÃO DE AÇÃO (lógica por bloco)
# ============================================================================

def _executar_acao_completa(driver: WebDriver, peticao: PeticaoLinha, bloco: str, acao: Any) -> bool:
    """
    Executa ação completa dependendo do bloco:
    
    - APAGAR: executa diretamente na lista (já implementado em _acao_apagar)
    - PERÍCIAS/RECURSO/DIRETOS/GIGS: abre processo → executa ação → fecha TODAS as abas
    - ANÁLISE: abre processo → extrai PDF → testa regras PDF → executa → fecha TODAS as abas
    
    IMPORTANTE: Garante que SEMPRE fecha todas as abas exceto a lista, mesmo que
    o wrapper abra uma terceira aba (tarefa/comunicações).
    
    Retorna: True se executado com sucesso, False caso contrário.
    """
    try:
        # ========== BLOCO APAGAR (direto na lista) ==========
        if bloco == "apagar":
            return _acao_apagar(driver, peticao)
        
        # ========== BLOCO ANÁLISE (precisa extrair PDF) ==========
        if bloco == "analise":
            # Abrir detalhes
            sucesso_abrir, aba_lista = _abrir_detalhe_peticao(driver, peticao)
            if not sucesso_abrir:
                logger.warning(f"[PET2_EXEC] Falha ao abrir detalhes: {peticao.numero_processo}")
                return False
            
            try:
                # Aguardar botão de exportar PDF carregar
                print(f"[PET2_EXEC] Aguardando botão .fa-file-export...")
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.fa-file-export'))
                    )
                    print(f"[PET2_EXEC] ✅ Botão .fa-file-export encontrado")
                except TimeoutException:
                    logger.warning(f"[PET2_EXEC] Timeout aguardando botão .fa-file-export: {peticao.numero_processo}")
                    _fechar_e_voltar_lista(driver, aba_lista)
                    return False
                
                # Extrair PDF
                print(f"[PET2_EXEC] Extraindo PDF de {peticao.numero_processo}...")
                conteudo_pdf = extrair_pdf(driver)
                if not conteudo_pdf:
                    logger.warning(f"[PET2_EXEC] PDF vazio: {peticao.numero_processo}")
                    _fechar_e_voltar_lista(driver, aba_lista)
                    return False
                
                # Processar PDF com regras de análise
                resultado = processar_analise_pdf(driver, peticao, conteudo_pdf)
                
                # IMPORTANTE: Fechar TODAS as abas (PDF pode ter aberto tarefa)
                _fechar_e_voltar_lista(driver, aba_lista)
                return resultado
                
            except Exception as e:
                logger.error(f"[PET2_EXEC] Erro em análise PDF: {e}")
                _fechar_e_voltar_lista(driver, aba_lista)
                return False
        
        # ========== OUTROS BLOCOS (abre → executa → fecha TODAS as abas) ==========
        # Registrar número de abas ANTES de abrir detalhes
        abas_antes = len(driver.window_handles)
        print(f"[PET2_EXEC] Abas antes de abrir detalhes: {abas_antes}")
        
        # Abrir detalhes
        sucesso_abrir, aba_lista = _abrir_detalhe_peticao(driver, peticao)
        if not sucesso_abrir:
            logger.warning(f"[PET2_EXEC] Falha ao abrir detalhes: {peticao.numero_processo}")
            return False
        
        try:
            # Registrar número de abas DEPOIS de abrir detalhes (deve ser 2: lista + detalhes)
            abas_apos_detalhes = len(driver.window_handles)
            print(f"[PET2_EXEC] Abas após abrir detalhes: {abas_apos_detalhes}")
            
            # Executar ação(ões) - podem abrir nova aba (tarefa)
            if isinstance(acao, tuple):
                # Múltiplas ações em sequência
                for sub_acao in acao:
                    if callable(sub_acao):
                        try:
                            resultado = sub_acao(driver, peticao)
                            if resultado is False:
                                print(f"[PET2_EXEC] ⚠️ Sub-ação retornou False - parando sequência")
                                break
                        except Exception as e:
                            logger.error(f"[PET2_EXEC] Erro em sub-ação: {e}")
            else:
                # Ação única
                if callable(acao):
                    try:
                        acao(driver, peticao)
                    except Exception as e:
                        logger.error(f"[PET2_EXEC] Erro em ação: {e}")
            
            # Registrar número de abas DEPOIS da ação (pode ter aberto tarefa = 3 abas)
            abas_apos_acao = len(driver.window_handles)
            print(f"[PET2_EXEC] Abas após executar ação: {abas_apos_acao}")
            
            # IMPORTANTE: Fechar TODAS as abas exceto lista (fecha detalhes E tarefa se houver)
            _fechar_e_voltar_lista(driver, aba_lista)
            
            # Confirmar que voltou para lista (deve ter apenas 1 aba)
            abas_final = len(driver.window_handles)
            print(f"[PET2_EXEC] Abas após fechar: {abas_final}")
            
            if abas_final != 1:
                logger.warning(f"[PET2_EXEC] ⚠️ Esperado 1 aba (lista), mas há {abas_final} abas")
            
            return True
            
        except Exception as e:
            logger.error(f"[PET2_EXEC] Erro ao executar ação: {e}")
            # Garantir limpeza mesmo com erro
            _fechar_e_voltar_lista(driver, aba_lista)
            return False
        
    except Exception as e:
        logger.error(f"[PET2_EXEC] Erro geral: {e}")
        return False


# ============================================================================
# MOTOR DE EXECUÇÃO SIMPLIFICADO (padrão p2b.py)
# ============================================================================

def classificar_peticoes(peticoes: List[PeticaoLinha], regras_dict: Dict[str, List]) -> Dict[str, List]:
    """
    CLASSIFICAÇÃO APENAS - não executa ações!
    
    Para cada petição, testa hipóteses em ordem e MARCA bloco+ação.
    Retorna dicionário agrupado por bloco: {bloco: [(peticao, hipotese, acao), ...]}
    
    LÓGICA DE PRIORIDADE:
    1. Testa PERÍCIAS, RECURSO, DIRETOS (prioritários)
    2. Se nenhum deu match → testa GIGS (fallback)
    3. Se nenhum deu match → testa ANÁLISE
    4. Por último → testa APAGAR
    """
    try:
        # Ordem: prioritários, depois gigs (fallback), depois análise, por último apagar
        blocos_prioritarios = ["pericias", "recurso", "diretos"]
        blocos_fallback = ["gigs"]
        blocos_finais = ["analise", "apagar"]
        
        ordem_blocos = blocos_prioritarios + blocos_fallback + blocos_finais
        classificadas = {bloco: [] for bloco in ordem_blocos}
        sem_match = []
        
        print(f"\n[PET2_CLASS] Classificando {len(peticoes)} petições...")
        print(f"[PET2_CLASS] Lógica: Prioritários (perícias/recurso/diretos) → Fallback (gigs) → Análise → Apagar")
        
        for peticao in peticoes:
            classificou = False
            
            # ETAPA 1: Testa blocos prioritários (perícias, recurso, diretos)
            for bloco in blocos_prioritarios:
                if bloco not in regras_dict:
                    continue
                
                hipoteses = regras_dict[bloco]
                
                for nome_hipotese, patterns, acao in hipoteses:
                    # Verificar match
                    if bloco == "pericias":
                        match = verifica_peticao_pericias(peticao, patterns)
                    elif bloco == "diretos":
                        match = verifica_peticao_diretos(peticao, patterns)
                    else:
                        match = verifica_peticao_contra_hipotese(peticao, patterns)
                    
                    if match:
                        classificadas[bloco].append((peticao, nome_hipotese, acao))
                        classificou = True
                        break
                
                if classificou:
                    break
            
            # Se já classificou nos prioritários, pula os demais
            if classificou:
                continue
            
            # ETAPA 2: Se não deu match nos prioritários → testa GIGS (fallback)
            for bloco in blocos_fallback:
                if bloco not in regras_dict:
                    continue
                
                hipoteses = regras_dict[bloco]
                
                for nome_hipotese, patterns, acao in hipoteses:
                    match = verifica_peticao_contra_hipotese(peticao, patterns)
                    
                    if match:
                        classificadas[bloco].append((peticao, nome_hipotese, acao))
                        classificou = True
                        break
                
                if classificou:
                    break
            
            # Se já classificou em GIGS, pula os demais
            if classificou:
                continue
            
            # ETAPA 3: Se não deu match em nenhum prioritário nem GIGS → testa análise e apagar
            for bloco in blocos_finais:
                if bloco not in regras_dict:
                    continue
                
                hipoteses = regras_dict[bloco]
                
                for nome_hipotese, patterns, acao in hipoteses:
                    match = verifica_peticao_contra_hipotese(peticao, patterns)
                    
                    if match:
                        classificadas[bloco].append((peticao, nome_hipotese, acao))
                        classificou = True
                        break
                
                if classificou:
                    break
            
            if not classificou:
                sem_match.append(peticao)
        
        # Log agrupado por bloco
        for bloco in ordem_blocos:
            if classificadas[bloco]:
                print(f"\n[{bloco.upper()}] {len(classificadas[bloco])} petições:")
                for pet, hip, _ in classificadas[bloco]:
                    print(f"  • {pet.numero_processo} | {hip}")
        
        if sem_match:
            print(f"\n[SEM MATCH] {len(sem_match)} petições:")
            for pet in sem_match:
                print(f"  • {pet.numero_processo} | {pet.tipo_peticao}")
        
        print()
        return classificadas
        
    except Exception as e:
        logger.error(f"[PET2_CLASS] Erro: {e}")
        return {}


def executar_classificadas(driver: WebDriver, classificadas: Dict[str, List]) -> Dict[str, int]:
    """
    EXECUÇÃO APENAS - recebe petições já classificadas!
    
    IMPORTANTE: Processa UM por vez e RE-EXTRAI a lista após cada execução
    para garantir que os elementos HTML estejam atualizados.
    
    Retorna: Dict {bloco: quantidade_executada}
    """
    try:
        contadores = {}
        ordem_blocos = ["pericias", "recurso", "diretos", "gigs", "analise", "apagar"]
        
        print(f"\n[PET2_EXEC] Executando ações por bloco...")
        
        for bloco in ordem_blocos:
            if bloco not in classificadas or not classificadas[bloco]:
                continue
            
            petlist = classificadas[bloco]
            print(f"\n[PET2_EXEC] ──── BLOCO: {bloco.upper()} ({len(petlist)} petições) ────")
            
            sucesso_bloco = 0
            erro_bloco = 0
            
            # Processar uma petição por vez
            for idx, (peticao, nome_hipotese, acao) in enumerate(petlist, 1):
                print(f"\n[PET2_EXEC] [{idx}/{len(petlist)}] {peticao.numero_processo}")
                print(f"[PET2_EXEC]   Hipótese: {nome_hipotese}")
                
                # RE-EXTRAIR lista para atualizar elementos HTML
                print(f"[PET2_EXEC] Re-extraindo lista para atualizar elementos...")
                peticoes_atualizadas = extrair_tabela_peticoes(driver)
                
                # Encontrar petição atualizada pelo número do processo
                peticao_atualizada = None
                for pet in peticoes_atualizadas:
                    if pet.numero_processo == peticao.numero_processo:
                        peticao_atualizada = pet
                        break
                
                if not peticao_atualizada:
                    print(f"[PET2_EXEC] ⚠️ Petição {peticao.numero_processo} não encontrada na lista atualizada")
                    erro_bloco += 1
                    continue
                
                # Executar ação completa com elemento atualizado
                sucesso = _executar_acao_completa(driver, peticao_atualizada, bloco, acao)
                if sucesso:
                    sucesso_bloco += 1
                    print(f"[PET2_EXEC]   ✅ Executado com sucesso")
                else:
                    erro_bloco += 1
                    print(f"[PET2_EXEC]   ⚠️ Falha na execução")
                
                # Aguardar um pouco antes do próximo
                time.sleep(1)
            
            contadores[bloco] = sucesso_bloco
            print(f"\n[PET2_EXEC] ──── {bloco.upper()}: {sucesso_bloco} sucesso, {erro_bloco} erro ────")
        
        return contadores
        
    except Exception as e:
        logger.error(f"[PET2_EXEC] Erro: {e}")
        return {}


# ============================================================================
# PAGINAÇÃO
# ============================================================================

def clicar_proxima_pagina(driver: WebDriver) -> bool:
    """
    Clica no botão 'Próxima página' e aguarda carregamento.
    Retorna True se conseguiu avançar, False se não há mais páginas.
    """
    try:
        print("[PET2_PAG] Procurando botão 'Próxima página'...")
        
        # Botão: <button aria-label="Próximo"><i class="fa fa-chevron-right"></i></button>
        botao = driver.find_element(By.CSS_SELECTOR, 
            "button[aria-label='Próximo'] i.fa-chevron-right")
        
        # Verificar se está desabilitado (não há mais páginas)
        botao_parent = botao.find_element(By.XPATH, "ancestor::button")
        if botao_parent.get_attribute("disabled"):
            print("[PET2_PAG] ⚠️ Botão desabilitado - última página alcançada")
            return False
        
        # Clicar
        driver.execute_script("arguments[0].click();", botao_parent)
        print("[PET2_PAG] ✅ Clicou em 'Próxima página'")
        
        # Aguardar carregamento (spinner ou tabela atualizar)
        time.sleep(3)
        
        return True
        
    except NoSuchElementException:
        print("[PET2_PAG] ⚠️ Botão 'Próxima página' não encontrado")
        return False
    except Exception as e:
        logger.error(f"[PET2_PAG] Erro: {e}")
        return False


def processar_peticoes_escaninho(driver: WebDriver) -> Dict[str, int]:
    """
    Função principal para processar petições no escaninho.
    
    Fluxo completo:
    1. Navega para escaninho (filtro 50, reordena coluna) - UMA VEZ
    2. Loop de páginas:
       a) Extrai tabela de petições
       b) Define regras de processamento
       c) Executa regras (motor simplificado)
       d) Clica em 'Próxima página'
       e) Repete até não haver mais páginas
    3. Retorna relatório consolidado
    
    Retorna: Dict com contadores {bloco: quantidade_executada}
    """
    try:
        print("\n" + "="*70)
        print("PROCESSAMENTO DE PETIÇÕES (PJe) - VERSÃO REFATORADA pet2.py")
        print("="*70 + "\n")
        
        # 1. Navegação inicial (apenas 1 vez)
        print("[PET2_MAIN] ETAPA 1: Navegação inicial...")
        if not navegacao_inicial_pet(driver):
            logger.error("[PET2_MAIN] Falha na navegação inicial")
            return {}
        
        # 2. Definir regras (apenas 1 vez)
        print("\n[PET2_MAIN] ETAPA 2: Definindo regras...")
        regras_dict = definir_regras()
        total_hipoteses = sum(len(hipoteses) for hipoteses in regras_dict.values())
        print(f"[PET2_MAIN] ✅ {len(regras_dict)} blocos, {total_hipoteses} hipóteses definidas")
        
        # 3. Loop de páginas
        print("\n[PET2_MAIN] ETAPA 3: Processando páginas...")
        resultado_total = {}
        pagina = 1
        
        while True:
            print(f"\n{'='*70}")
            print(f"PÁGINA {pagina}")
            print(f"{'='*70}")
            
            # 3a. Extração
            print(f"\n[PET2_MAIN] Extraindo petições da página {pagina}...")
            peticoes = extrair_tabela_peticoes(driver)
            if not peticoes:
                print(f"[PET2_MAIN] ⚠️ Nenhuma petição na página {pagina}")
                break
            
            # 3b. Classificar petições (SEM executar)
            print(f"\n[PET2_MAIN] Classificando petições da página {pagina}...")
            classificadas = classificar_peticoes(peticoes, regras_dict)
            
            # 3c. Executar ações (já classificadas)
            print(f"\n[PET2_MAIN] Executando ações da página {pagina}...")
            resultado_pagina = executar_classificadas(driver, classificadas)
            
            # Consolidar resultados
            for bloco, qtd in resultado_pagina.items():
                resultado_total[bloco] = resultado_total.get(bloco, 0) + qtd
            
            # 3c. Próxima página
            print(f"\n[PET2_MAIN] Tentando avançar para página {pagina + 1}...")
            if not clicar_proxima_pagina(driver):
                print("[PET2_MAIN] ✅ Todas as páginas processadas")
                break
            
            pagina += 1
        
        print("\n" + "="*70)
        print("PROCESSAMENTO CONCLUÍDO")
        print(f"Total de páginas processadas: {pagina}")
        print("="*70 + "\n")
        
        return resultado_total
        
    except Exception as e:
        logger.error(f"[PET2_MAIN] Erro fatal: {e}")
        return {}


# ============================================================================
# CONFIGURAÇÕES VT - DRIVERS EMBUTIDOS (padrão 2.py)
# ============================================================================

# Caminho do geckodriver - usa o da raiz do projeto
GECKODRIVER_PATH = os.path.join(str(Path(__file__).parent.parent), 'geckodriver.exe')
if not os.path.exists(GECKODRIVER_PATH):
    # Fallback: tenta em Fix/
    GECKODRIVER_PATH = os.path.join(str(Path(__file__).parent.parent), 'Fix', 'geckodriver.exe')

# Firefox Developer Edition
FIREFOX_BINARY = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
FIREFOX_BINARY_ALT = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'

# Perfis VT
VT_PROFILE_PJE = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
VT_PROFILE_PJE_ALT = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'


def criar_driver_vt(headless=False):
    """
    Cria driver Firefox para PJE - Perfil VT (padrão 2.py)
    Tenta: FIREFOX_BINARY → FIREFOX_BINARY_ALT
    Tenta: VT_PROFILE_PJE → VT_PROFILE_PJE_ALT → sem perfil
    Configurações anti-throttling incluídas
    """
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    
    # Verifica se geckodriver existe
    if not os.path.exists(GECKODRIVER_PATH):
        print(f"[DRIVER_VT_PJE] ❌ ERRO CRÍTICO: Geckodriver não encontrado em {GECKODRIVER_PATH}")
        return None
    
    # Define qual binário tentar
    firefox_binaries = [FIREFOX_BINARY, FIREFOX_BINARY_ALT]
    firefox_bin_usado = None
    
    # Encontra o primeiro binário que existe
    for bin_path in firefox_binaries:
        if os.path.exists(bin_path):
            firefox_bin_usado = bin_path
            break
    
    if not firefox_bin_usado:
        print(f"[DRIVER_VT_PJE] ❌ ERRO CRÍTICO: Nenhum binário Firefox encontrado")
        print(f"  Tentei: {firefox_binaries}")
        return None
    
    print(f"[DRIVER_VT_PJE] Usando binário: {firefox_bin_usado}")
    
    # Tenta criar com perfil primário
    try:
        options = Options()
        
        if headless:
            options.add_argument('-headless')
        
        options.binary_location = firefox_bin_usado
        
        # Tenta primeiro com o perfil primário
        if os.path.exists(VT_PROFILE_PJE):
            options.profile = VT_PROFILE_PJE
            print(f"[DRIVER_VT_PJE] Usando perfil primário: {VT_PROFILE_PJE}")
        elif os.path.exists(VT_PROFILE_PJE_ALT):
            options.profile = VT_PROFILE_PJE_ALT
            print(f"[DRIVER_VT_PJE] Usando perfil alternativo: {VT_PROFILE_PJE_ALT}")
        else:
            print(f"[DRIVER_VT_PJE] ⚠️ Nenhum perfil encontrado, usando temporário")
        
        # Configurações anti-automação
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        
        # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
        options.set_preference("dom.min_background_timeout_value", 0)
        options.set_preference("dom.timeout.throttling_delay", 0)
        options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
        
        # Configurações de performance
        options.set_preference("browser.startup.homepage", "about:blank")
        options.set_preference("startup.homepage_welcome_url", "about:blank")
        options.set_preference("browser.startup.page", 0)
        
        # Desabilitar telemetria
        options.set_preference("datareporting.healthreport.uploadEnabled", False)
        options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
        options.set_preference("toolkit.telemetry.enabled", False)
        
        service = Service(executable_path=GECKODRIVER_PATH)
        driver = webdriver.Firefox(options=options, service=service)
        driver.implicitly_wait(10)
        driver.maximize_window()
        
        # Ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[DRIVER_VT_PJE] ✅ Driver VT PJE criado com sucesso")
        return driver
        
    except Exception as e:
        print(f"[DRIVER_VT_PJE] ⚠️ Erro ao criar driver com perfil: {e}")
        print("[DRIVER_VT_PJE] 🔄 Tentando criar driver SEM perfil (fallback)...")
        
        # Fallback: tenta sem perfil
        try:
            options = Options()
            
            if headless:
                options.add_argument('-headless')
            
            options.binary_location = firefox_bin_usado
            
            # Configurações anti-automação
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference('useAutomationExtension', False)
            
            # ===== ANTI-THROTTLING =====
            options.set_preference("dom.min_background_timeout_value", 0)
            options.set_preference("dom.timeout.throttling_delay", 0)
            options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
            
            # Configurações de performance
            options.set_preference("browser.startup.homepage", "about:blank")
            options.set_preference("startup.homepage_welcome_url", "about:blank")
            options.set_preference("browser.startup.page", 0)
            
            # Desabilitar telemetria
            options.set_preference("datareporting.healthreport.uploadEnabled", False)
            options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
            options.set_preference("toolkit.telemetry.enabled", False)
            
            service = Service(executable_path=GECKODRIVER_PATH)
            driver = webdriver.Firefox(options=options, service=service)
            driver.implicitly_wait(10)
            driver.maximize_window()
            
            # Ocultar webdriver
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("[DRIVER_VT_PJE] ✅ Driver VT PJE criado com sucesso (fallback sem perfil)")
            return driver
        
        except Exception as e2:
            print(f"[DRIVER_VT_PJE] ❌ Erro crítico ao criar driver (fallback falhou): {e2}")
            return None


# ============================================================================
# PONTO DE ENTRADA PARA TESTES
# ============================================================================

def main():
    """
    Função main para execução direta do módulo (testes).
    Usa driver VT conforme padrão 2.py
    """
    from Fix.utils import login_cpf
    
    print("\n" + "="*70)
    print("MODO DE TESTE: Executando pet2.py diretamente (Driver VT)")
    print("="*70 + "\n")
    
    driver = None
    try:
        # Setup do driver VT
        print("[MAIN] Inicializando driver VT...")
        driver = criar_driver_vt(headless=False)
        
        if not driver:
            print("[MAIN] ❌ Falha ao criar driver")
            return
        
        print("[MAIN] ✅ Driver VT criado com sucesso")
        
        # Login
        print("\n[MAIN] Realizando login...")
        if not login_cpf(driver):
            print("[MAIN] ❌ Falha no login")
            return
        
        print("[MAIN] ✅ Login realizado com sucesso")
        
        # Executar processamento
        print("\n[MAIN] Iniciando processamento de petições...")
        resultado = processar_peticoes_escaninho(driver)
        
        # Mostrar resultado
        print("\n" + "="*70)
        print("RESULTADO FINAL:")
        print("="*70)
        if resultado:
            for bloco, qtd in resultado.items():
                if qtd > 0:
                    print(f"  {bloco.upper()}: {qtd} petições processadas")
        else:
            print("  Nenhuma petição processada")
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n[MAIN] ⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"[MAIN] ❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\n[MAIN] Fechando driver...")
            try:
                driver.quit()
                print("[MAIN] ✅ Driver fechado")
            except:
                pass


if __name__ == "__main__":
    main()
