# sisbajud_teimosinha.py
"""
Automação completa do fluxo ‘Teimosinha’ (SISBAJUD):
1. Navega do menu /minuta até /teimosinha
2. Filtra séries elegíveis
3. Determina o tipo de fluxo (NEGATIVO | DESBLOQUEIO | POSITIVO)
4. Para DESBLOQUEIO/POSITIVO: abre cada série, identifica ordens com bloqueio
5. Preenche tela Desdobrar conforme fluxo (Desbloquear valor | Transferir valor)
6. Registra texto dos bloqueios e totals por parte
7. Chama wrappers/atos externos indicados no fluxo
Todas as funções foram isoladas para facilitar manutenção e testes unitários.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Tuple

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ---------------------------------------------------------------------------------
# CONSTANTES E CONFIGURAÇÕES GERAIS
# ---------------------------------------------------------------------------------
JUÍZ_SOLICITANTE_PADRÃO = "OTAVIO AUGUSTO MACHADO DE OLIVEIRA"
TIPO_CRÉDITO_PADRÃO = "Crédito geral"
BANCO_PADRÃO = "Banco do Brasil"
AGÊNCIA_PADRÃO = "5905"
DIAS_LIMITE_SERIE = 15

# ---------------------------------------------------------------------------------
# 0. UTILITÁRIOS
# ---------------------------------------------------------------------------------
def _esperar_clickável(driver: WebDriver, by: Tuple[str, str], timeout: int = 5):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(by))


def _try_select_option(driver: WebDriver, span_texto: str, timeout: int = 4) -> bool:
    """Clica numa <mat-option> cujo span possui texto igual a `span_texto`."""
    try:
        opc = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//span[@class='mat-option-text' and normalize-space(text())='{span_texto}']")
            )
        )
        opc.click()
        return True
    except TimeoutException:
        return False


def _texto_para_float(texto_moeda: str) -> float:
    """Converte 'R$ 1.234,56' → 1234.56"""
    limpo = (
        texto_moeda.replace("R$", "")
        .replace("\u00a0", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(limpo)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------------
# 1. NAVEGAÇÃO PARA /TEIMOSINHA E APLICAÇÃO DO FILTRO
# ---------------------------------------------------------------------------------
def _abrir_teimosinha(driver: WebDriver, num_processo: str) -> None:
    """Parte 1 do fluxo – navegação a /teimosinha e pesquisa pelo processo."""
    # a) Hamburguer
    _esperar_clickável(
        driver,
        (By.CSS_SELECTOR, "button.btn-hamburger, button[aria-label*='navegação']"),
    ).click()
    time.sleep(0.5)

    # b) Link Teimosinha
    _esperar_clickável(driver, (By.CSS_SELECTOR, "a[href='/teimosinha']")).click()
    WebDriverWait(driver, 5).until(EC.url_contains("/teimosinha"))

    # c) Campo Número do Processo
    inp_proc = _esperar_clickável(
        driver, (By.CSS_SELECTOR, "input[placeholder*='Número do Processo']")
    )
    inp_proc.clear()
    inp_proc.send_keys(num_processo)

    # d) Botão Consultar
    _esperar_clickável(
        driver,
        (By.XPATH, "//button[contains(@class,'mat-fab') and .//mat-icon[contains(@class,'fa-search')]]"),
    ).click()

    # e) Confirma que tabela carregou
    WebDriverWait(driver, 8).until(
        EC.presence_of_element_located(
            (By.XPATH, "//th[normalize-space(text())='ID da série']")
        )
    )


def _listar_series_elegíveis(driver: WebDriver) -> List[Dict[str, Any]]:
    """Retorna lista de séries que atendem aos critérios de situação/data."""
    series: List[Dict[str, Any]] = []
    linhas = driver.find_elements(By.CSS_SELECTOR, "tbody tr.mat-row")

    if not linhas:
        return series

    meses = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
    }
    limite = datetime.now() - timedelta(days=DIAS_LIMITE_SERIE)

    for ln in linhas:
        try:
            id_serie = ln.find_element(By.CSS_SELECTOR, "td[data-label='sequencial']").text.strip()
            situacao = ln.find_element(By.CSS_SELECTOR, "td[data-label='dataFim']").text.strip()
            data_prog_txt = ln.find_element(By.CSS_SELECTOR, "td[data-label='dataProgramada']").text.strip()
            val_bloq_txt = ln.find_element(By.CSS_SELECTOR, "td[data-label='valorBloqueado']").text.strip()
            val_a_bloq_txt = ln.find_element(By.CSS_SELECTOR, "td[data-label='valorBloquear']").text.strip()

            if "encerrada" not in situacao.lower():
                continue

            # Converte data “25 DE AGO DE 2023”
            p = data_prog_txt.upper().split()
            if len(p) < 5:
                continue
            dia, mes, ano = int(p[0]), meses.get(p[2], 1), int(p[4])
            data_prog = datetime(ano, mes, dia)

            if data_prog > limite:
                continue

            serie = dict(
                id_serie=id_serie,
                situacao=situacao,
                data_programada=data_prog,
                valor_bloqueado=_texto_para_float(val_bloq_txt),
                valor_a_bloquear=_texto_para_float(val_a_bloq_txt),
                ln_element=ln,
            )
            series.append(serie)
        except NoSuchElementException:
            continue
    return series


# ---------------------------------------------------------------------------------
# 2. EXTRAÇÃO DE TEXTO DAS SÉRIES + DEFINIÇÃO DO TIPO DE FLUXO
# ---------------------------------------------------------------------------------
def _texto_series(series: List[Dict[str, Any]]) -> Tuple[List[str], float, float]:
    linhas, total_bloq, total_a_bloq = [], 0.0, 0.0
    for s in series:
        linhas.append(
            f"Id da série: {s['id_serie']} - Valor Bloqueado na série: "
            f"R$ {s['valor_bloqueado']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        total_bloq += s["valor_bloqueado"]
        total_a_bloq += s["valor_a_bloquear"]
    if len(series) > 1:
        linhas.append(
            f"Total bloqueado = R$ {total_bloq:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    return linhas, total_bloq, total_a_bloq


def _classificar_fluxo(total_bloq: float, total_a_bloq: float) -> str:
    if total_bloq == 0:
        return "NEGATIVO"
    if total_bloq < 100 and total_a_bloq >= 1000:
        return "DESBLOQUEIO"
    return "POSITIVO"


# ---------------------------------------------------------------------------------
# 3. FUNÇÕES DE APOIO A /DETALHES E /DESDOBRAR
# ---------------------------------------------------------------------------------
def _abrir_nova_aba(driver: WebDriver, url: str) -> None:
    driver.execute_script("window.open(arguments[0],'_blank');", url)
    driver.switch_to.window(driver.window_handles[-1])


def _extrair_ordens(driver: WebDriver) -> List[Dict[str, Any]]:
    """Extrai todas as ordens da tabela na página /detalhes."""
    tbody = _esperar_clickável(driver, (By.CSS_SELECTOR, "table.mat-table tbody"), 10)
    linhas = tbody.find_elements(By.CSS_SELECTOR, "tr.mat-row")
    ordens = []
    for ln in linhas:
        cols = ln.find_elements(By.CSS_SELECTOR, "td")
        if len(cols) < 6:
            continue
        seq = int(cols[0].text.strip())
        data_txt = cols[2].text.strip().split()  # assume dd/mm/aaaa
        dia, mes, ano = map(int, data_txt.split("/"))
        data_ord = datetime(ano, mes, dia)
        valor = _texto_para_float(cols[4].text)
        ordens.append(
            dict(
                sequencial=seq,
                data=data_ord,
                valor_bloquear=valor,
                protocolo=cols[5].text.strip(),
                ln_element=ln,
            )
        )
    ordens.sort(key=lambda o: o["data"])
    return ordens


def _ordens_com_bloqueio(ordens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detecta ordens cujo valor à bloquear diminuiu em relação à ordem seguinte."""
    bloqs = []
    for i in range(len(ordens) - 1):
        if ordens[i]["valor_bloquear"] > ordens[i + 1]["valor_bloquear"]:
            bloqs.append(ordens[i])
    return bloqs


# -------------------------- Tela DESDOBRAR ---------------------------------------
def _preencher_tela_desdobrar(
    driver: WebDriver,
    fluxo: str,
) -> bool:
    """Preenche os campos na tela /desdobrar de acordo com o fluxo."""
    # Juiz solicitante
    try:
        inp_juiz = _esperar_clickável(driver, (By.CSS_SELECTOR, "input[placeholder*='Juiz']"), 6)
        inp_juiz.clear()
        inp_juiz.send_keys(JUÍZ_SOLICITANTE_PADRÃO + "\n")
    except TimeoutException:
        pass

    # Dropdowns de ação
    selects = driver.find_elements(By.CSS_SELECTOR, "mat-select[name*='acao']")
    opcao = "Desbloquear valor" if fluxo == "DESBLOQUEIO" else "Transferir valor"
    for sel in selects:
        try:
            sel.click()
            if not _try_select_option(driver, opcao):
                _try_select_option(driver, opcao.upper())  # variação de texto
        except Exception:
            continue

    # Botão Salvar
    try:
        _esperar_clickável(
            driver,
            (
                By.XPATH,
                "//button[contains(@class,'mat-fab') "
                "and .//mat-icon[contains(@class,'fa-save')]]",
            ),
            6,
        ).click()
    except TimeoutException:
        return False

    # Esperar botão 'Protocolar' aparecer
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//button[contains(@class,'mat-fab') "
                    "and @title='Protocolar']",
                )
            )
        )
        return True
    except TimeoutException:
        return False


# ---------------------------------------------------------------------------------
# 4. PROCESSAMENTO DE UMA ORDEM (menu → Desdobrar → preencher → fechar)
# ---------------------------------------------------------------------------------
def _processar_ordem(driver: WebDriver, ordem: Dict[str, Any], fluxo: str) -> bool:
    """Executa todas as etapas para uma única ordem."""
    ln = ordem["ln_element"]
    # Abrir menu
    try:
        ln.find_element(By.CSS_SELECTOR, "mat-icon.fa-ellipsis-h").click()
        _esperar_clickável(driver, (By.CSS_SELECTOR, "div.mat-menu-panel"))
    except Exception:
        return False

    # Clicar em Desdobrar
    try:
        _esperar_clickável(
            driver, (By.XPATH, "//button//span[contains(text(),'Desdobrar')]")
        ).click()
    except TimeoutException:
        return False

    # Aguarda URL /desdobrar
    try:
        WebDriverWait(driver, 8).until(EC.url_contains("/desdobrar"))
    except TimeoutException:
        return False

    # Preencher tela
    sucesso = _preencher_tela_desdobrar(driver, fluxo)

    # Fecha aba da ordem
    driver.close()
    driver.switch_to.window(driver.window_handles[-1])
    return sucesso


# ---------------------------------------------------------------------------------
# 5. PROCESSAR UMA SÉRIE COMPLETA
# ---------------------------------------------------------------------------------
def _processar_serie(
    driver: WebDriver,
    serie: Dict[str, Any],
    fluxo: str,
    registro_partes: Dict[str, float],
) -> None:
    """Abre a série, processa ordens relevantes e acumula registro por parte."""
    id_serie = serie["id_serie"]
    _abrir_nova_aba(driver, f"https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes")

    if not EC.url_contains("/detalhes")(driver):
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
        return

    # Extrai ordens + identifica bloqueios
    ordens = _extrair_ordens(driver)
    ordens_bloq = _ordens_com_bloqueio(ordens)

    # Registros de bloqueio por parte (parse simplificado do HTML da parte)
    for o in ordens_bloq:
        # Parte encontra-se no cabeçalho expansion-panel acima da ordem
        try:
            panel = o["ln_element"].find_element(By.XPATH, "./ancestor::mat-expansion-panel[2]")
            parte_nome = panel.find_element(By.CSS_SELECTOR, ".col-reu-dados-nome-pessoa").text.strip()
        except Exception:
            parte_nome = "Parte não identificada"
        registro_partes[parte_nome] += o["valor_bloquear"]

        _processar_ordem(driver, o, fluxo)

    # Fecha a aba /detalhes
    driver.close()
    driver.switch_to.window(driver.window_handles[-1])


# ---------------------------------------------------------------------------------
# 6. FUNÇÃO PRINCIPAL EXTERNAMENTE VISÍVEL
# ---------------------------------------------------------------------------------
def processar_teimosinha(
    driver: WebDriver,
    num_processo: str,
    ato_wrappers: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Entrada ÚNICA para o sistema externo:
    - `driver`  : driver SISBAJUD já logado
    - `num_processo`: string com número CNJ
    - `ato_wrappers`: dict com funções externas {positivo, negativo, desbloqueio, atos_medio, atos_parcial}
    Retorna dicionário‐relatório com:
       texto_series, fluxo, registro_partes, series_processadas
    """
    _abrir_teimosinha(driver, num_processo)
    series = _listar_series_elegíveis(driver)

    if not series:
        return {"erro": "Não há teimosinha para processar"}

    linhas_texto, total_bloq, total_a_bloq = _texto_series(series)
    fluxo = _classificar_fluxo(total_bloq, total_a_bloq)

    # Acumula registros por parte durante processamento
    registro_partes = defaultdict(float)

    if fluxo in ("DESBLOQUEIO", "POSITIVO"):
        for serie in series:
            if serie["valor_bloqueado"] > 0:
                _processar_serie(driver, serie, fluxo, registro_partes)

    # Fecha driver SISBAJUD (continuação no PJe)
    driver.quit()

    # ---- Invoca wrappers externos conforme fluxo ----
    if fluxo == "NEGATIVO":
        ato_wrappers["negativo"]()
        ato_wrappers["meios"]()
    elif fluxo == "DESBLOQUEIO":
        ato_wrappers["negativo"]()
        ato_wrappers["meios"]()
    else:  # POSITIVO
        ato_wrappers["positivo"]()
        ato_wrappers["parcial"]()

    # ---- Monta registro textual final ----
    texto_reg_partes = []
    for parte, valor in registro_partes.items():
        linha = f"{parte}: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        texto_reg_partes.append(linha)

    return {
        "texto_series": linhas_texto,
        "fluxo": fluxo,
        "registro_partes": texto_reg_partes,
        "series_processadas": [s["id_serie"] for s in series],
    }
