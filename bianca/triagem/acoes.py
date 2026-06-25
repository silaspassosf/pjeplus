# -*- coding: utf-8 -*-
"""
bianca/triagem/acoes.py -- Acoes pos-triagem.

Contem:
  - Constantes de regex para deteccao de buckets
  - Funcoes de deteccao de alertas (estilo LEG -- mais robusto)
  - Funcoes de acao pos-triagem por bucket (A/B/C/D)
  - Helpers de navegacao (_abrir_nova_aba, _marcar_aud)

Extraido de triagem_engine.py (linhas 1884-2179).
"""

import re
import time
import traceback
from datetime import datetime as _dt
from pprint import pformat
from typing import Any, Dict, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from Fix.abas import trocar_para_nova_aba
from Fix.core import esperar_elemento, preencher_campo, safe_click
from Fix.headless_helpers import limpar_overlays_headless
from bianca.extracao import criar_comentario, criar_gigs
from bianca.triagem.citacao import def_citacao


def _print_saida_funcao(rotulo: str, valor: Any) -> None:
    if isinstance(valor, str):
        texto = valor
    else:
        texto = pformat(valor, width=120, sort_dicts=False)
    print(f"[TRIAGEM/TRACE] {rotulo} => {texto}")


# =============================================================================
# Padroes para determinar bucket a partir do texto da triagem
# =============================================================================

_RE_BUCKET_PRE = re.compile(
    r'domicilio do reclamante como referencia subsidiaria', re.IGNORECASE)
_RE_BUCKET_B2 = re.compile(
    r'zona sul nao detectado|incompetencia territorial', re.IGNORECASE)
_RE_BUCKET_E = re.compile(r'reclamante menor de idade', re.IGNORECASE)
_RE_BUCKET_C = re.compile(r'B8_PEDIDOS:\s*ALERTA', re.IGNORECASE)
_RE_BUCKET_D = re.compile(r'B1_DOCS:\s*ALERTA', re.IGNORECASE)


# =============================================================================
# Deteccao de alertas (estilo LEG)
# =============================================================================


def _tem_alerta_incompetencia(triagem_txt: str) -> bool:
    """Incompetencia aparece na secao [COMPETENCIA] como 'Zona Sul nao detectado'
    seguida de foro (RUI BARBOSA ou ZONA LESTE).

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se alerta de incompetencia for detectado.
    """
    if not isinstance(triagem_txt, str):
        return False
    t = triagem_txt.lower()
    return (
        "zona sul nao detectado" in t
        or "incompetencia territorial" in t
        or "fora dos intervalos" in t
    )


def _tem_alerta_pedidos_nao_liquidados(triagem_txt: str) -> bool:
    """Verifica alerta de pedidos nao liquidados na secao [Alertas].

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se alerta de pedidos nao liquidados for detectado.
    """
    if not isinstance(triagem_txt, str):
        return False
    in_alertas = False
    for linha in triagem_txt.splitlines():
        s = linha.strip()
        if s == "[Alertas]":
            in_alertas = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[Alertas]":
            in_alertas = False
        if in_alertas and "pedidos liquidados" in s.lower():
            return True
    return False


def _tem_alerta_docs_pessoais(triagem_txt: str) -> bool:
    """Verifica alerta de documentos essenciais faltando na secao [Alertas].

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se alerta de documentos essenciais for detectado.
    """
    if not isinstance(triagem_txt, str):
        return False
    in_alertas = False
    for linha in triagem_txt.splitlines():
        s = linha.strip()
        if s == "[Alertas]":
            in_alertas = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[Alertas]":
            in_alertas = False
        if in_alertas and "documentos essenciais" in s.lower():
            return True
    return False


def _tem_alerta_menor_idade(triagem_txt: str) -> bool:
    """Verifica alerta de reclamante menor de idade na secao [Alertas].

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se alerta de menor de idade for detectado.
    """
    if not isinstance(triagem_txt, str):
        return False
    in_alertas = False
    for linha in triagem_txt.splitlines():
        s = linha.strip()
        if s == "[Alertas]":
            in_alertas = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[Alertas]":
            in_alertas = False
        if in_alertas and "menor de idade" in s.lower():
            return True
    return False


def _tem_alerta_domicilio_autor(triagem_txt: str) -> bool:
    """Verifica se competencia foi definida pelo domicilio do reclamante.

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        True se domicilio do autor for a referencia.
    """
    if not isinstance(triagem_txt, str):
        return False
    return 'domicilio do reclamante como referencia subsidiaria' in triagem_txt.lower()


# =============================================================================
# Determinacao de acao pos-triagem
# =============================================================================


def _determinar_acao_pos_triagem(triagem_txt: str) -> Tuple[str, None]:
    """Determina o bucket e acao a partir do texto da triagem.

    Implementacao inline dos patterns do alerta_registry.
    Prioridade: pre_bucket > b2_incompetencia > c_pedidos > d_docs > b1_normal.

    Args:
        triagem_txt: Texto completo da analise de triagem.

    Returns:
        Tuple (bucket_str, None).
    """
    if not triagem_txt:
        return 'b1_normal', None
    if _RE_BUCKET_PRE.search(triagem_txt):
        return 'pre_bucket', None
    if _RE_BUCKET_B2.search(triagem_txt):
        return 'b2_incompetencia', None
    if _RE_BUCKET_E.search(triagem_txt):
        return 'e_menor', None
    if _RE_BUCKET_C.search(triagem_txt):
        return 'c_pedidos', None
    if _RE_BUCKET_D.search(triagem_txt):
        return 'd_docs', None
    return 'b1_normal', None


def _aplicar_acao_pos_triagem(
    driver: WebDriver,
    numero: str,
    processo_info: Dict,
    triagem_txt: str,
) -> Tuple[bool, Optional[str]]:
    """Decide e executa a acao pos-triagem com base nos alertas identificados.

    Usa _determinar_acao_pos_triagem() para identificar o bucket e
    despacha para a funcao de acao correspondente.

    Args:
        driver: WebDriver Selenium.
        numero: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.
        triagem_txt: Texto da analise de triagem.

    Returns:
        Tuple[bool, Optional[str]]: (sucesso, status_line).
    """
    if not triagem_txt or (isinstance(triagem_txt, str) and triagem_txt.startswith("ERRO")):
        print(f"[TRIAGEM/ACOES][{numero}] triagem com erro -- sem acao")
        return False, None

    bucket, _ = _determinar_acao_pos_triagem(triagem_txt)

    # Pre-bucket: competencia por domicilio do autor → GIGS observacao
    if bucket == 'pre_bucket':
        # Reavaliar sem pre_bucket para obter bucket real
        if _RE_BUCKET_B2.search(triagem_txt):
            bucket = 'b2_incompetencia'
        elif _RE_BUCKET_C.search(triagem_txt):
            bucket = 'c_pedidos'
        elif _RE_BUCKET_D.search(triagem_txt):
            bucket = 'd_docs'
        else:
            bucket = 'b1_normal'

    if bucket == 'b2_incompetencia':
        print(f"[TRIAGEM/ACOES][{numero}] b2 -- incompetencia territorial → processo nao processado")
        return True, None
    if bucket == 'e_menor':
        print(f"[TRIAGEM/ACOES][{numero}] e_menor -- reclamante menor de idade → intimar MPT, processo nao processado")
        return True, None
    if bucket == 'c_pedidos':
        print(f"[TRIAGEM/ACOES][{numero}] c -- pedidos nao liquidados → placeholder despacho liquidar")
        return True, None
    if bucket == 'd_docs':
        print(f"[TRIAGEM/ACOES][{numero}] d -- falta de documentos pessoais → placeholder apresentar doc")
        return True, None

    # b1: sem alertas criticos → execucao normal de buckets
    bucket_proc = processo_info.get("bucket", "C")
    print(f"[TRIAGEM/ACOES][{numero}] b1 -- sem alertas → bucket {bucket_proc} (execucao normal)")
    if bucket_proc == "A":
        ok, status = acao_bucket_a(driver, numero, processo_info)
        return ok, status
    if bucket_proc == "B":
        ok, status = acao_bucket_b(driver, numero, processo_info)
        return ok, status
    if bucket_proc == "C":
        ok, status = acao_bucket_c(driver, numero, processo_info)
        return ok, status
    if bucket_proc == "D":
        ok, status = acao_bucket_d(driver, numero, processo_info)
        return ok, status
    if bucket_proc == "CP":
        print(f"[TRIAGEM/ACOES][{numero}] CP -- Carta Precatória (comentario ja registrado)")
        return True, None

    print(f"[TRIAGEM/ACOES][{numero}] bucket desconhecido '{bucket_proc}'")
    return False, None


# =============================================================================
# Helpers de navegacao
# =============================================================================


def _abrir_nova_aba(
    driver: WebDriver,
    url: str,
    aba_origem: str,
    url_fragmento: Optional[str] = None,
    timeout: int = 10,
) -> Optional[str]:
    """Abre nova aba e aguarda carregamento.

    Args:
        driver: WebDriver Selenium.
        url: URL a abrir.
        aba_origem: Handle da aba de origem.
        url_fragmento: Fragmento opcional para confirmar carregamento.
        timeout: Timeout em segundos.

    Returns:
        Handle da nova aba, ou None em caso de falha.
    """
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                abas = driver.window_handles
                for h in abas:
                    if h == aba_origem:
                        continue
                    driver.switch_to.window(h)
                    if not url_fragmento:
                        return h
                    try:
                        if url_fragmento in (driver.current_url or ""):
                            return h
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(0.2)
        return trocar_para_nova_aba(driver, aba_origem)
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ _abrir_nova_aba: {type(e).__name__}: {e}")
        return None


def desmarcar_100(driver: WebDriver, id_processo: str) -> Optional[str]:
    aba_detalhe = driver.current_window_handle
    url_retificar = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/retificar"

    nova_aba = _abrir_nova_aba(driver, url_retificar, aba_detalhe, url_fragmento="/retificar")
    if not nova_aba:
        return None

    # Checar acesso-negado antes de prosseguir
    try:
        url_atual = driver.current_url or ""
        if "acesso-negado" in url_atual.lower():
            print(f"[TRIAGEM/ACOES] ⚠ desmarcar_100: acesso negado ({url_atual}) — fechando aba")
            driver.close()
            driver.switch_to.window(aba_detalhe)
            return None
    except Exception:
        pass

    try:
        step_carac = esperar_elemento(
            driver,
            "mat-step-header[aria-posinset='4']",
            by=By.CSS_SELECTOR,
            timeout=15,
        )
        if not step_carac:
            raise Exception("Step 'Caracteristicas' nao encontrado")

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", step_carac)
        safe_click(driver, step_carac)
        time.sleep(1)

        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10,
        )
        if not toggle:
            raise Exception("Toggle Juizo 100% digital nao encontrado")

        if "mat-checked" in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            
            # Aguardar primeiro painel de expansão aparecer
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            
            # 1. Localizar e clicar "Sim" no primeiro painel
            # "Tem certeza de que deseja retirar essa marcação?"
            try:
                primeiro_painel = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//mat-expansion-panel//mat-panel-title[contains(normalize-space(.), 'Tem certeza de que deseja retirar')]"
                    ))
                )
                btn_sim = primeiro_painel.find_element(
                    By.XPATH,
                    "./ancestor::mat-expansion-panel//mat-action-row//button[.//span[contains(normalize-space(.), 'Sim')]]"
                )
                safe_click(driver, btn_sim)
                time.sleep(0.5)
            except Exception as e:
                raise Exception(f"Primeiro painel ou botao 'Sim' nao encontrado: {e}")
            
            # 2. Aguardar segundo painel aparecer e clicar "Não"
            # "Confirma a inclusão do movimento correspondente no processo?"
            try:
                segundo_painel = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//mat-expansion-panel//mat-panel-title[contains(normalize-space(.), 'Confirma a inclusão do movimento')]"
                    ))
                )
                btn_nao = segundo_painel.find_element(
                    By.XPATH,
                    "./ancestor::mat-expansion-panel//mat-action-row//button[.//span[contains(normalize-space(.), 'Não')]]"
                )
                safe_click(driver, btn_nao)
                time.sleep(0.5)
            except Exception as e:
                raise Exception(f"Segundo painel ou botao 'Nao' nao encontrado: {e}")
            
            time.sleep(0.5)
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital']:not(.mat-checked)",
                by=By.CSS_SELECTOR,
                timeout=10,
            )
            time.sleep(1)
        return nova_aba
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ desmarcar_100: {type(e).__name__}: {e}")
        return nova_aba


def remarcar_100_pos_aud(driver: WebDriver) -> None:
    try:
        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10,
        )
        if not toggle:
            raise Exception("Toggle Juizo 100% digital nao encontrado")

        if "mat-checked" not in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            
            # Aguardar painel de expansão aparecer
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            
            # Localizar e clicar "Não" no painel de confirmação
            # "Confirma a inclusão do movimento correspondente no processo?"
            try:
                painel = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//mat-expansion-panel//mat-panel-title[contains(normalize-space(.), 'Confirma a inclusão do movimento')]"
                    ))
                )
                btn_sim = painel.find_element(
                    By.XPATH,
                    "./ancestor::mat-expansion-panel//mat-action-row//button[.//span[contains(normalize-space(.), 'Sim')]]"
                )
                safe_click(driver, btn_sim)
                time.sleep(0.5)
            except Exception as e:
                raise Exception(f"Painel ou botao 'Nao' nao encontrado em remarcar: {e}")
            
            time.sleep(0.5)
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital'].mat-checked",
                by=By.CSS_SELECTOR,
                timeout=10,
            )
            time.sleep(1)
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ remarcar_100_pos_aud: {type(e).__name__}: {e}")


_MESES_PT = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


def _extrair_data_hora_pauta(linha) -> tuple:
    """Extrai data e horário da linha da Tabela de Horários Vagos.

    Usa seletores específicos baseados na estrutura real:
      - Data: 2ª coluna (td.centralizado:nth-child(2) span)
      - Horário: 3ª coluna (td.centralizado:nth-child(3) span)
    """
    try:
        data_span = linha.find_element(
            By.CSS_SELECTOR,
            "td.centralizado.td-class:nth-child(2) span.ng-star-inserted"
        )
        hora_span = linha.find_element(
            By.CSS_SELECTOR,
            "td.centralizado.td-class:nth-child(3) span.ng-star-inserted"
        )
        data_str = data_span.text.strip()
        hora_str = hora_span.text.strip()
        if not data_str or not hora_str:
            raise ValueError(f"Data='{data_str}' ou hora='{hora_str}' vazias")
        return data_str, hora_str
    except Exception as e:
        raise ValueError(f"Falha ao extrair data/hora da linha: {e}")


def _navegar_calendario_para_data(driver: WebDriver, data_str: str) -> None:
    """Navega o calendario mensal ate a data alvo e clica no dia.

    Args:
        driver: WebDriver Selenium.
        data_str: Data no formato "DD/MM/YYYY".
    """
    alvo = _dt.strptime(data_str, "%d/%m/%Y")
    hoje = _dt.today()
    delta = (alvo.year - hoje.year) * 12 + (alvo.month - hoje.month)
    print(f"[CALENDARIO] Navegando para {data_str}. Hoje: {hoje}. Delta meses: {delta}")

    # Log do mês inicial exibido (capturar título do calendário)
    try:
        current_heading = driver.find_element(By.CSS_SELECTOR, ".cal-header h2").text
        print(f"[CALENDARIO] Heading inicial: {current_heading}")
    except:
        print("[CALENDARIO] Não foi possível ler heading inicial")

    for i in range(delta):
        btn_next = esperar_elemento(driver, "#next", by=By.CSS_SELECTOR, timeout=10)
        if not btn_next:
            raise Exception("Botao proximo mes nao encontrado")
        safe_click(driver, btn_next)
        time.sleep(0.3)
        # Log após cada clique
        try:
            h2 = driver.find_element(By.CSS_SELECTOR, ".cal-header h2").text
            print(f"[CALENDARIO] Após clique {i+1}: {h2}")
        except:
            pass

    mes_nome = _MESES_PT[alvo.month - 1]
    heading_xpath = f"//h2[contains(normalize-space(.), '{mes_nome}, {alvo.year}')]"
    heading = esperar_elemento(driver, heading_xpath, by=By.XPATH, timeout=10)
    if not heading:
        raise Exception(f"Heading do mes '{mes_nome}, {alvo.year}' nao encontrado")
    print(f"[CALENDARIO] Heading confirmado: {heading.text}")

    dia_str = str(alvo.day)
    # Usar XPath mais específico: célula que contém o número do dia exato e não está em heading
    dia_cell_xpath = (
        f"//span[contains(@class,'cal-day-cell') and "
        f".//label[normalize-space(.)='{dia_str}'] and "
        f"not(ancestor::div[contains(@class,'cal-day-heading')])]"
    )
    dia_cell = esperar_elemento(driver, dia_cell_xpath, by=By.XPATH, timeout=10)
    if not dia_cell:
        raise Exception(f"Celula do dia {dia_str} nao encontrada")

    # Log para ver qual dia está sendo clicado
    print(f"[CALENDARIO] Clicando no dia {dia_str}. Atributos: class={dia_cell.get_attribute('class')}")
    dia_cell.location_once_scrolled_into_view
    safe_click(driver, dia_cell)
    time.sleep(0.8)

    # Verificar confirmação – usar formato DD/MM/YYYY
    dia_fmt = alvo.strftime("%d/%m/%Y")
    confirm_xpath = f"//h2[contains(normalize-space(.), '{dia_fmt}')]"
    confirm = esperar_elemento(driver, confirm_xpath, by=By.XPATH, timeout=10)
    if not confirm:
        # fallback: pode estar em outro elemento
        print("[CALENDARIO] Confirmação não encontrada pelo h2, verificando tabela...")
        # Verificar se a tabela agora mostra apenas linhas com essa data
        linhas_data = driver.find_elements(
            By.XPATH,
            f"//tr[.//td[@class='centralizado td-class'][2]//span[normalize-space(.)='{dia_fmt}']]"
        )
        if len(linhas_data) == 0:
            raise Exception(f"Dia {dia_fmt} não refletido na tabela após clique")
        print(f"[CALENDARIO] Tabela agora contém {len(linhas_data)} linhas com data {dia_fmt}")
    else:
        print(f"[CALENDARIO] Confirmação visual encontrada: {confirm.text}")


def _encontrar_slot_dia(driver: WebDriver, hora_str: str) -> None:
    """Clica no botao Designar Audiencia na linha com o horario especificado.

    O horario ja foi extraido da linha correta (rito filtrado na tabela inicial),
    portanto e unico na pauta diaria -- sem necessidade de filtrar por tipo.

    Args:
        driver: WebDriver Selenium.
        hora_str: Horario no formato "HH:MM".
    """
    print(f"[SLOT] Procurando slot com horário '{hora_str}'")
    # Primeiro, registrar todas as linhas visíveis para diagnóstico
    try:
        todas_linhas = driver.find_elements(By.XPATH, "//tr[.//span[contains(@class,'ng-star-inserted')]]")
        for idx, tr in enumerate(todas_linhas):
            texto = tr.text[:120]
            print(f"Linha {idx}: {texto}")
    except:
        pass

    linha_xpath = f"//tr[.//span[normalize-space(.)='{hora_str}']]"
    linha = esperar_elemento(driver, linha_xpath, by=By.XPATH, timeout=15)
    if not linha:
        raise Exception(f"Linha com horario '{hora_str}' nao encontrada na pauta diaria")

    # Log detalhado da linha selecionada
    print(f"[SLOT] Linha encontrada: {linha.text[:200]}")
    # Clica no botão com aria-label "Designar Audiência"
    btn_plus = linha.find_element(
        By.XPATH,
        ".//button[contains(@aria-label,'Designar')] | .//i[contains(@class,'fa-plus-circle')]/ancestor::button",
    )
    print(f"[SLOT] Clicando no botão designar")
    safe_click(driver, btn_plus)


def _tem_audiencia_marcada(driver: WebDriver, processo_info: Optional[Dict] = None) -> bool:
    """Verifica se o processo tem audiência marcada.

    Fonte primária: campo `tem_audiencia` (derivado de `dataProximaAudiencia`) em
    processo_info, preenchido via API antes de abrir o processo. Essa fonte é
    mais confiável que o DOM porque o campo vem direto do servidor PJe.

    Fallback (quando processo_info indisponível): inspeciona `dt#audiencias` no
    DOM e valida presença de data/hora concretos.
    """
    # --- Fonte primária: API (processo_info) ---
    if processo_info is not None:
        tem = bool(processo_info.get('tem_audiencia', False))
        print(f"[TRIAGEM] _tem_audiencia_marcada via API: tem_audiencia={tem} "
              f"(dataProximaAudiencia={processo_info.get('dataProximaAudiencia', 'N/A')})")
        return tem

    # --- Fallback: DOM ---
    try:
        dt = driver.find_element(By.CSS_SELECTOR, "dt#audiencias")
        if not dt.is_displayed():
            return False

        parent_text = ""
        try:
            parent = dt.find_element(By.XPATH, "./ancestor::*[1]")
            parent_text = (parent.text or "").strip()
        except Exception:
            parent_text = (dt.text or "").strip()

        if not parent_text:
            return False

        re_data = re.search(r"\b\d{2}/\d{2}/\d{4}\b", parent_text)
        re_hora = re.search(r"\b\d{2}:\d{2}\b", parent_text)

        # aud_kw removido: o rotulo do proprio dt#audiencias (ex: "Audiencia(s):")
        # sempre contem a palavra, causando falso positivo. So considerar TRUE
        # se houver data/hora concreta de audiencia.
        return bool(re_data or re_hora)
    except Exception:
        return False


def _marcar_aud(
    driver: WebDriver,
    numero_processo: str,
    rito: str,
    aba_retorno: str,
):
    """Marca audiencia no sistema de pauta do PJe."""
    aba_origem = driver.current_window_handle
    url_pauta = f"https://pje.trt2.jus.br/pjekz/pauta-audiencias?maisPje=true&numero={numero_processo}&rito={rito}&fase=Conhecimento"
    aba_aud = _abrir_nova_aba(driver, url_pauta, aba_origem, url_fragmento="/pauta-audiencias")
    if not aba_aud:
        return False

    sucesso = False
    try:
        esperar_elemento(driver, "mat-card.card-pauta", by=By.CSS_SELECTOR, timeout=15)

        # Determina o nome do rito para buscar na primeira coluna
        rito_texto = "Una (rito sumaríssimo)" if rito.upper() == 'ATSUM' else "Una"

        # XPath que encontra a linha onde a primeira coluna contém exatamente o texto do rito
        linha_xpath = (
            f"//tr[.//td[1]//span[normalize-space(.)='{rito_texto}']]"
        )
        linha = esperar_elemento(driver, linha_xpath, by=By.XPATH, timeout=10)
        if not linha:
            # fallback: tenta apenas o início do texto (ex: "Una" sem parênteses)
            fallback_texto = "Una"
            linha_xpath = f"//tr[.//td[1]//span[starts-with(normalize-space(.), '{fallback_texto}')]]"
            linha = esperar_elemento(driver, linha_xpath, by=By.XPATH, timeout=5)
        if not linha:
            raise Exception("Linha de pauta não encontrada para o rito especificado")

        print(f"[TRIAGEM/ACOES] Linha encontrada: {linha.text[:200]}...")
        print(f"[TRIAGEM/ACOES] Extraindo data/hora...")

        data_str, hora_str = _extrair_data_hora_pauta(linha)
        print(f"[MARCAR_AUD] Dados extraídos: data={data_str}, hora={hora_str}")
        _navegar_calendario_para_data(driver, data_str)
        _encontrar_slot_dia(driver, hora_str)

        modal = esperar_elemento(driver, "mat-dialog-container", by=By.CSS_SELECTOR, timeout=10)
        if not modal:
            raise Exception("Modal de audiencia nao encontrado")

        input_num = modal.find_element(By.CSS_SELECTOR, "input#inputNumeroProcesso")
        valor_atual = (input_num.get_attribute('value') or '').strip()
        if not valor_atual:
            try:
                safe_click(driver, input_num)
                input_num.clear()
                input_num.send_keys(numero_processo)
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    input_num,
                )
            except Exception:
                preencher_campo(driver, "#inputNumeroProcesso", numero_processo)
        time.sleep(0.8)

        btn_confirmar = esperar_elemento(
            driver,
            "//mat-dialog-container//button[.//span[normalize-space(.)='Confirmar']]",
            by=By.XPATH,
            timeout=10,
        )
        if not btn_confirmar:
            raise Exception("Botao Confirmar nao encontrado")
        safe_click(driver, btn_confirmar)
        time.sleep(1)

        modal_confirmado = esperar_elemento(
            driver,
            "div.container-conteudo h4",
            by=By.CSS_SELECTOR,
            timeout=10,
        )
        if not modal_confirmado:
            raise Exception("Confirmacao de designacao de audiencia nao encontrada no dialogo")

        btn_fechar = esperar_elemento(
            driver,
            "div.container-botoes button",
            by=By.CSS_SELECTOR,
            timeout=10,
        )
        if not btn_fechar:
            raise Exception("Botao Fechar nao encontrado na confirmacao")
        safe_click(driver, btn_fechar)
        time.sleep(0.5)
        sucesso = True
    except Exception as e:
        print(f"[TRIAGEM/ACOES] ❌ _marcar_aud: {type(e).__name__}: {e}")
    finally:
        if sucesso:
            try:
                driver.close()
            except Exception:
                pass
            try:
                if aba_retorno in driver.window_handles:
                    driver.switch_to.window(aba_retorno)
            except Exception:
                pass
    return sucesso


# =============================================================================
# Acoes por bucket
# =============================================================================


def acao_bucket_a(
    driver: WebDriver,
    numero_processo: str,
    processo_info: Dict,
) -> Tuple[bool, Optional[str]]:
    """Bucket A: processo sem audiencia marcada e sem 100% digital.

    Acoes:
      1. Analisa citacao (polo passivo + domicilio eletronico)
      2. Cria GIGS com observacoes de citacao
      3. Cria GIGS de marcacao de audiencia
      4. Registra comentario sobre a acao executada

    Args:
        driver: WebDriver Selenium.
        numero_processo: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.

    Returns:
        True se todas as acoes foram executadas com sucesso.
    """
    # --- VERIFICAÇÃO EM TEMPO REAL ---
    if _tem_audiencia_marcada(driver, processo_info):
        print(f"[TRIAGEM/A] Processo {numero_processo} já possui audiência marcada. Pulando marcação.")
        return True, "Já possui audiência"
    # --- FIM VERIFICAÇÃO ---

    try:
        tipo = (processo_info.get('tipo') or '').upper().strip()
        tem_100 = bool(processo_info.get('digital', processo_info.get('tem_100', False)))
        numero_formatado = processo_info.get('numero')
        id_processo = str(processo_info.get('id_processo') or '')
        if not numero_formatado or not id_processo:
            print(f"[TRIAGEM/A] ❌ Falha ao extrair numero/ID do processo {numero_processo}")
            return False, None

        rito = 'ATSum' if tipo == 'ATSUM' else 'ATOrd'

        if not tem_100:
            print(f"[TRIAGEM/A] Processo {numero_processo} sem 100% digital. Marcando audiencia antes do despacho.")

            limpar_overlays_headless(driver)

            citacao_a = def_citacao(driver, processo_info)
            _print_saida_funcao(f"def_citacao[{numero_processo}]", citacao_a)
            if not citacao_a.get('sucesso', True):
                print(f"[TRIAGEM/A] Polo passivo vazio -- abortando GIGS para {numero_processo}")
                return False, None

            for obs in citacao_a['gigs_obs']:
                try:
                    criar_gigs(driver, "1", "Bianca", obs)
                except Exception as e:
                    print(f"[TRIAGEM/A] ❌ Erro ao criar GIGS ({obs}): {e}")

            marcou_aud = _marcar_aud(driver, numero_formatado, rito, driver.current_window_handle)
            _print_saida_funcao(f"_marcar_aud[{numero_processo}]", marcou_aud)
            if not marcou_aud:
                print(f"[TRIAGEM/A] ❌ Marcacao de audiencia falhou para {numero_processo}. Despacho abortado.")
                return False, None

            limpar_overlays_headless(driver)

            try:
                from bianca.atos_utils import ato_unap
                print(f"[TRIAGEM/A] Executando ato_unap para {numero_processo}")
                resultado_ato = ato_unap(driver, debug=True)
                _print_saida_funcao(f"ato_unap[{numero_processo}]", resultado_ato)
                ok = bool(resultado_ato)
                return ok, "Sem aud - marcado e despachado?" if ok else None
            except Exception as e:
                print(f"[TRIAGEM/A] ⚠ Erro ao executar ato_unap: {e}")
                return False, None

        if tipo not in ['ATORD', 'ATSUM', 'ACUM', 'ACCUM']:
            print(f"[TRIAGEM/A] Processo {numero_processo} nao atende criterios de rito. Pulando.")
            return True, "Sem aud - marcado e despachado?"

        aba_retificar = desmarcar_100(driver, id_processo)
        _print_saida_funcao(f"desmarcar_100[{numero_processo}]", aba_retificar)
        if not aba_retificar:
            print(f"[TRIAGEM/A] ❌ Nao foi possivel abrir/usar aba retificar")
            return False, None

        marcou_aud = _marcar_aud(driver, numero_formatado, rito, aba_retificar)
        _print_saida_funcao(f"_marcar_aud[{numero_processo}]", marcou_aud)
        if not marcou_aud:
            print(f"[TRIAGEM/A] ❌ Marcacao de audiencia falhou para {numero_processo}. Despacho abortado.")
            return False, None

        try:
            if aba_retificar in driver.window_handles:
                driver.switch_to.window(aba_retificar)
                remarcar_100_pos_aud(driver)
                driver.close()
        except Exception as e:
            print(f"[TRIAGEM/A] ⚠ Erro ao finalizar retificar: {e}")

        try:
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if '/detalhe' in (driver.current_url or ''):
                    break
        except Exception:
            pass

        limpar_overlays_headless(driver)

        citacao_a2 = def_citacao(driver, processo_info)
        _print_saida_funcao(f"def_citacao_pos_aud[{numero_processo}]", citacao_a2)
        if not citacao_a2.get('sucesso', True):
            print(f"[TRIAGEM/A] Polo passivo vazio apos triagem -- abortando GIGS para {numero_processo}")
            return False, None

        for obs in citacao_a2['gigs_obs']:
            try:
                criar_gigs(driver, "1", "Bianca", obs)
            except Exception as e:
                print(f"[TRIAGEM/A] ❌ Erro ao criar GIGS pos-aud ({obs}): {e}")

        try:
            from bianca.atos_utils import ato_100
            print(f"[TRIAGEM/A] Executando ato_100 para {numero_processo}")
            resultado_ato = ato_100(driver, debug=True)
            _print_saida_funcao(f"ato_100[{numero_processo}]", resultado_ato)
        except Exception as e:
            print(f"[TRIAGEM/A] ⚠ Erro ao executar ato_100: {e}")

        return True, "Sem aud - marcado e despachado?"
    except Exception as e:
        print(f"[TRIAGEM/A] ❌ Erro na acao: {e}")
        traceback.print_exc()
        return False, None


def acao_bucket_b(
    driver: WebDriver,
    numero_processo: str,
    processo_info: Dict,
) -> Tuple[bool, Optional[str]]:
    """Bucket B: processo com audiencia e 100% digital.

    Acoes:
      1. Analisa citacao (polo passivo + domicilio eletronico)
      2. Cria GIGS com observacoes de citacao
      3. Registra comentario sobre a acao executada

    Args:
        driver: WebDriver Selenium.
        numero_processo: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.

    Returns:
        True se todas as acoes foram executadas com sucesso.
    """
    # --- VERIFICAÇÃO EM TEMPO REAL (B) ---
    if not _tem_audiencia_marcada(driver, processo_info):
        print(f"[TRIAGEM/B] Processo {numero_processo} não possui audiência (embora esperado). Forçando bucket A.")
        return acao_bucket_a(driver, numero_processo, processo_info)
    # --- FIM VERIFICAÇÃO ---

    try:
        citacao_b = def_citacao(driver, processo_info)
        _print_saida_funcao(f"def_citacao[{numero_processo}]", citacao_b)
        if not citacao_b.get('sucesso', True):
            print(f"[TRIAGEM/B] Polo passivo vazio -- abortando GIGS para {numero_processo}")
            return False, None

        for obs in citacao_b['gigs_obs']:
            try:
                criar_gigs(driver, "1", "Bianca", obs)
            except Exception as e:
                print(f"[TRIAGEM/B] ❌ Erro ao criar GIGS ({obs}): {e}")

        # ato_100
        try:
            from bianca.atos_utils import ato_100
            print(f"[TRIAGEM/B] Executando ato_100 para {numero_processo}")
            resultado_ato = ato_100(driver, debug=True)
            _print_saida_funcao(f"ato_100[{numero_processo}]", resultado_ato)
        except Exception as e:
            print(f"[TRIAGEM/B] ⚠ Erro ao executar ato_100: {e}")

        return True, "100% digital - despachado?"
    except Exception as e:
        print(f"[TRIAGEM/B] ❌ Erro na acao: {e}")
        traceback.print_exc()
        return False, None


def acao_bucket_c(
    driver: WebDriver,
    numero_processo: str,
    processo_info: Dict,
) -> Tuple[bool, Optional[str]]:
    """Bucket C: processo com audiencia, sem 100% digital.

    Acoes:
      1. Analisa citacao
      2. Executa PEC wrappers (pec_ord, pec_sum, pec_ordc, pec_sumc)
      3. Se PEC ok, executa mov_aud

    Args:
        driver: WebDriver Selenium.
        numero_processo: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.

    Returns:
        True se todas as acoes foram executadas com sucesso.
    """
    # --- VERIFICACAO EM TEMPO REAL (C) ---
    if not _tem_audiencia_marcada(driver, processo_info):
        print(f"[TRIAGEM/C] Processo {numero_processo} nao possui audiencia (classificado como C por engano). Forcando bucket A.")
        return acao_bucket_a(driver, numero_processo, processo_info)
    # --- FIM VERIFICACAO ---

    try:
        from bianca.atos_utils import pec_ord, pec_sum, pec_ordc, pec_sumc, mov_aud
        _PEC_MAP = {'pec_ord': pec_ord, 'pec_sum': pec_sum,
                    'pec_ordc': pec_ordc, 'pec_sumc': pec_sumc}

        citacao_c = def_citacao(driver, processo_info)
        _print_saida_funcao(f"def_citacao[{numero_processo}]", citacao_c)
        if not citacao_c.get('sucesso', True):
            print(f"[TRIAGEM/C] Polo passivo vazio -- abortando PEC para {numero_processo}")
            return False, None

        ok = False
        for pec_nome in citacao_c['pec_wrappers']:
            pec_fn = _PEC_MAP.get(pec_nome)
            if pec_fn:
                print(f"[TRIAGEM/C] Executando {pec_nome} para {numero_processo}")
                try:
                    resultado_pec = pec_fn(driver, debug=True)
                    _print_saida_funcao(f"{pec_nome}[{numero_processo}]", resultado_pec)
                    ok = bool(resultado_pec) or ok
                except Exception as e:
                    print(f"[TRIAGEM/C] Erro em {pec_nome}: {e}")
            else:
                print(f"[TRIAGEM/C] PEC wrapper '{pec_nome}' nao encontrado no _PEC_MAP")

        if ok:
            print(f"[TRIAGEM/C] Executando mov_aud para {numero_processo}")
            resultado_mov = mov_aud(driver, debug=True)
            _print_saida_funcao(f"mov_aud[{numero_processo}]", resultado_mov)
            result = bool(resultado_mov)
            return result, "Direto - citado?" if result else None
        return False, None
    except Exception as e:
        print(f"[TRIAGEM/C] Erro na acao: {e}")
        traceback.print_exc()
        return False, None


def acao_bucket_d(
    driver: WebDriver,
    numero_processo: str,
    processo_info: Dict,
) -> Tuple[bool, Optional[str]]:
    """Bucket D: processo HTE (habilitacao de credor).

    Acoes:
      1. Cria GIGS informativa sobre habilitacao
      2. Registra comentario

    Args:
        driver: WebDriver Selenium.
        numero_processo: Numero CNJ do processo.
        processo_info: Dict com metadados do processo.

    Returns:
        True se todas as acoes foram executadas com sucesso.
    """
    try:
        return True, None
    except Exception as e:
        print(f"[TRIAGEM/D] ❌ Erro na acao: {e}")
        traceback.print_exc()
        return False, None
