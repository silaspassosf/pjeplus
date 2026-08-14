"""
PEC - carta_ecarta_api.py
Substitui a extração DOM (Selenium) de coletar_tabela_ecarta por chamadas HTTP.

Fluxo:
    1. Login único (extrai JSESSIONID do driver Selenium — cache por sessão)
    2. GET consultarProcesso.xhtml?codigo=<processo> → parse HTML → filtra por idPje/data
    3. Para cada linha com rastreio: GET consultarObjeto → POST JSF → extrai eventos
    4. Detecta falsos positivos e corrige STATUS
    5. Retorna mesma estrutura de table_data que o legado espera

Uso: substituir coletar_tabela_ecarta() por coletar_tabela_ecarta_api() em carta_execucao.py
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date as _date, datetime as _datetime
from typing import Optional
from xml.etree import ElementTree as ET

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from Fix import espera

logger = logging.getLogger(__name__)

BASE = "https://aplicacoes1.trt2.jus.br/eCarta-web/"

# ─── Cache de sessão HTTP (login único por execução) ───
_ecarta_session: Optional[requests.Session] = None
_ecarta_logged_in: bool = False

# ─── Padrões de falso positivo ───
RE_DEVOLUCAO = re.compile(
    r'objeto\s+(ser[áa]\s+devolvido|saiu\s+para\s+entrega\s+ao\s+remetente|entregue\s+ao\s+remetente)'
    r'|devolvido\s+ao\s+remetente',
    re.IGNORECASE,
)
RE_STATUS_ENTREGUE = re.compile(r'entregue\s+ao\s+destinat[áa]rio', re.IGNORECASE)
RE_STATUS_DEVOLVIDO = re.compile(r'devolvid[oa]', re.IGNORECASE)


_MESES_PT = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9,
    'outubro': 10, 'novembro': 11, 'dezembro': 12,
}


def _parse_data(texto: str) -> Optional[_date]:
    """
    Parseia data em formato brasileiro (DD/MM/YYYY[ HH:MM[:SS]]), ISO
    (YYYY-MM-DD[THH:MM:SS]) ou por extenso em portugues (ex: "07 de julho de
    2026", como aparece no rodape padrao dos documentos do PJe). Retorna None
    se nao conseguir reconhecer.
    """
    if not texto:
        return None
    texto = texto.strip()

    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return _datetime.strptime(texto, fmt).date()
        except ValueError:
            continue

    m = re.search(
        r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
        texto, re.IGNORECASE,
    )
    if m:
        mes = _MESES_PT.get(m.group(2).lower())
        if mes:
            try:
                return _date(int(m.group(3)), mes, int(m.group(1)))
            except ValueError:
                pass

    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto)
    if m:
        try:
            return _date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto)
    if m:
        try:
            return _date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None


# ═══════════════════════════════════════════════════════════════════
# Login único
# ═══════════════════════════════════════════════════════════════════

def _ecarta_ensure_session(driver: WebDriver, log: bool = True) -> Optional[requests.Session]:
    """
    Garante sessão HTTP autenticada no eCarta.
    - Se já temos sessão ativa, retorna ela.
    - Senão, tenta extrair JSESSIONID do driver (se já logado).
    - Se não tiver cookie, faz login via Selenium uma única vez.
    """
    global _ecarta_session, _ecarta_logged_in

    if _ecarta_session is not None:
        return _ecarta_session

    s = requests.Session()

    # Tenta extrair cookies da sessão atual do Selenium
    try:
        selenium_cookies = driver.get_cookies()
        for c in selenium_cookies:
            if 'trt2' in (c.get('domain', '') or '') or 'ecarta' in (c.get('name', '') or '').lower():
                s.cookies.set(
                    c['name'], c['value'],
                    domain=c.get('domain', ''),
                    path=c.get('path') or '/',
                    secure=bool(c.get('secure', False)),
                )
    except Exception as e:
        if log:
            logger.warning('[CARTA-API] falha ao ler cookies pré-login: %s', e)

    # Testa se a sessão já está autenticada
    try:
        resp = s.get(BASE + 'consultarProcesso.xhtml', timeout=10, allow_redirects=True)
        if 'input_user' not in resp.text and 'login-box' not in resp.text.lower():
            _ecarta_session = s
            _ecarta_logged_in = True
            if log:
                logger.info('[CARTA-API] Sessão HTTP recuperada do driver — já autenticada')
            return s
    except Exception:
        pass

    # ── Login via Selenium (uma única vez) ──
    if log:
        logger.info('[CARTA-API] Abrindo eCarta para login único...')

    original_window = driver.current_window_handle
    original_count = len(driver.window_handles)

    driver.execute_script(f"window.open('{BASE}consultarProcesso.xhtml', '_blank');")
    espera.ate_abas(driver, original_count + 1, teto=5)

    all_windows = driver.window_handles
    if len(all_windows) > 1:
        driver.switch_to.window(all_windows[-1])

    try:
        WebDriverWait(driver, 20).until(
            lambda d: 'ecarta' in (d.current_url or '').lower()
        )
    except TimeoutException:
        pass

    try:
        user_field = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#input_user'))
        )
        user_field.send_keys('s164283')
        driver.find_element(By.CSS_SELECTOR, '#input_password').send_keys('SpFintra861!')
        driver.find_element(By.CSS_SELECTOR, 'input.btn').click()

        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        espera.assentar(driver, 1)

        if log:
            logger.info('[CARTA-API] Login realizado com sucesso')
    except TimeoutException:
        if log:
            logger.warning('[CARTA-API] Tela de login não apareceu — sessão já pode estar ativa')

    # Extrai cookies pós-login
    try:
        selenium_cookies = driver.get_cookies()
        for c in selenium_cookies:
            s.cookies.set(
                c['name'], c['value'],
                domain=c.get('domain', ''),
                path=c.get('path') or '/',
                secure=bool(c.get('secure', False)),
            )
    except Exception as e:
        if log:
            logger.warning('[CARTA-API] falha ao ler/transferir cookies pós-login: %s', e)

    # Fecha a aba de login
    try:
        driver.close()
        driver.switch_to.window(original_window)
    except Exception:
        pass

    _ecarta_session = s
    _ecarta_logged_in = True
    if log:
        logger.info('[CARTA-API] Sessão HTTP inicializada')
    return s


def _ecarta_reset_session():
    """Reseta a sessão (útil se expirar)."""
    global _ecarta_session, _ecarta_logged_in
    _ecarta_session = None
    _ecarta_logged_in = False


# ═══════════════════════════════════════════════════════════════════
# Parsers HTML (sem Selenium)
# ═══════════════════════════════════════════════════════════════════

def _parse_tabela_processo(html: str) -> list[dict]:
    """Extrai linhas da tabela eCarta do HTML bruto."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    tbody = (
        soup.select_one('#main\\:tabDoc_data')
        or soup.select_one('tbody[id$="tabDoc_data"]')
        or soup.select_one('.ui-datatable-data')
    )
    if not tbody:
        return []

    rows = []
    for tr in tbody.find_all('tr', recursive=False):
        tds = tr.find_all('td')
        if len(tds) < 4:
            continue

        get_text = lambda i: tds[i].get_text(strip=True) if i < len(tds) else ''

        # Extrai código de rastreamento
        objetoTd = tds[4] if len(tds) > 4 else None
        rastreio = ''
        rastreio_link = ''
        if objetoTd:
            span = objetoTd.find('span', id=re.compile(r':rastreamento$'))
            if span:
                rastreio = span.get_text(strip=True)
                link_el = span.find_parent('a')
                if link_el and link_el.get('href'):
                    href = link_el['href']
                    rastreio_link = f'https://aplicacoes1.trt2.jus.br{href}' if href.startswith('/') else href
            else:
                link = objetoTd.find('a', href=re.compile(r'consultarObjeto'))
                if link:
                    m = re.search(r'codigo=([^&]+)', link['href'])
                    if m:
                        rastreio = m.group(1)
                        rastreio_link = link['href'] if link['href'].startswith('http') else f'https://aplicacoes1.trt2.jus.br{link["href"]}'

        if not rastreio:
            texto_obj = get_text(4)
            m = re.match(r'([A-Z]{2}\d{9}BR)', texto_obj)
            if m:
                rastreio = m.group(1)
                rastreio_link = f'{BASE}consultarObjeto.xhtml?codigo={rastreio}'

        rows.append({
            'dataEnvio': get_text(0),
            'dataEntrega': get_text(1),
            'idPje': get_text(3),
            'objeto': rastreio or get_text(4),
            'objetoLink': rastreio_link,
            'status': get_text(5),
            'destinatario': get_text(6),
            'orgaoJulgador': get_text(7),
        })

    return rows


def _extrair_viewstate(html: str) -> str:
    m = re.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', html)
    return m.group(1) if m else ''


def _fetch_detalhes_rastreio(session: requests.Session, codigo_rastreio: str) -> list[dict]:
    """
    GET consultarObjeto → POST JSF → parse eventos.
    Retorna lista de {dataEvento, descricao, cidadeUf}.
    """
    # Etapa 1: GET
    url = f'{BASE}consultarObjeto.xhtml?codigo={codigo_rastreio}'
    resp = session.get(url, timeout=30)
    html = resp.text

    viewstate = _extrair_viewstate(html)
    if not viewstate:
        return []

    indices = [int(m.group(1)) for m in re.finditer(r'id="main:tabDoc:(\d+):rastreamento"', html)]
    if not indices:
        return []

    # Etapa 2: POST JSF
    todos_eventos = []
    for idx in indices:
        source = f'main:tabDoc:{idx}:rastreamento'
        body = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': source,
            'javax.faces.partial.execute': source,
            'javax.faces.partial.render': 'detalhesObjeto',
            source: source,
            'main': 'main',
            'javax.faces.ViewState': viewstate,
        }

        post_resp = session.post(
            f'{BASE}consultarObjeto.xhtml',
            data=body,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'Faces-Request': 'partial/ajax',
            },
            timeout=30,
        )

        eventos = _parse_partial_response(post_resp.text)
        if eventos:
            todos_eventos.extend(eventos)

        time.sleep(0.15)

    return todos_eventos


def _parse_partial_response(xml_text: str) -> list[dict]:
    """Extrai eventos do <partial-response> JSF."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    for update in root.findall('.//update') or root.findall('update'):
        if update.get('id') != 'detalhesObjeto':
            continue
        inner_html = update.text or ''
        if not inner_html:
            continue

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(inner_html, 'html.parser')
        tbody = (
            soup.select_one('#tabDetalhesObjeto_data')
            or soup.select_one('tbody[id$="tabDetalhesObjeto_data"]')
        )
        if not tbody:
            continue

        eventos = []
        for tr in tbody.find_all('tr', recursive=False):
            tds = tr.find_all('td')
            if len(tds) < 2:
                continue
            if 'Nenhum resultado' in tds[0].get_text(strip=True):
                continue

            desc_parts = []
            for node in tds[1].children:
                if hasattr(node, 'get_text'):
                    desc_parts.append(node.get_text(strip=True))
                elif isinstance(node, str):
                    desc_parts.append(node.strip())
            descricao = ' | '.join(p for p in desc_parts if p) or tds[1].get_text(' | ', strip=True)

            eventos.append({
                'dataEvento': tds[0].get_text(strip=True),
                'descricao': descricao,
                'cidadeUf': tds[2].get_text(strip=True) if len(tds) > 2 else '',
            })
        return eventos

    return []


# ═══════════════════════════════════════════════════════════════════
# Classificação de falso positivo
# ═══════════════════════════════════════════════════════════════════

def _classificar_status(status_original: str, eventos: list[dict]) -> tuple[str, Optional[str]]:
    """Determina o status real considerando o histórico de eventos.
    
    Returns:
        (status, evidencia) onde evidencia é None ou "data — descrição" do evento de devolução
    """
    if RE_STATUS_DEVOLVIDO.search(status_original):
        return 'DEVOLVIDO', None

    if not eventos:
        return status_original or 'SEM_EVENTOS', None

    for ev in eventos:
        if RE_DEVOLUCAO.search(ev.get('descricao', '')):
            evidencia = f"{ev.get('dataEvento', '')} — {ev.get('descricao', '')}"
            return 'DEVOLVIDO', evidencia

    if RE_STATUS_ENTREGUE.search(status_original):
        return 'ENTREGUE', None

    return status_original or 'INDETERMINADO', None


# ═══════════════════════════════════════════════════════════════════
# Substituição direta de coletar_tabela_ecarta
# ═══════════════════════════════════════════════════════════════════

def coletar_tabela_ecarta_api(
    driver: WebDriver,
    process_number: str,
    intimation_ids: list[str],
    log: bool = True,
    data_referencia: Optional[str] = None,
) -> list[dict]:
    """
    Substitui coletar_tabela_ecarta() — mesma entrada, mesma saída,
    mas usa HTTP (requests) em vez de Selenium para extrair a tabela.

    Adiciona auditoria de rastreamentos e correção de falsos positivos.

    Args:
        data_referencia: data da intimação detectada no PJe (qualquer formato
            aceito por _parse_data). Quando presente, é o critério PRIMÁRIO de
            seleção: pega todas as linhas do eCarta com dataEnvio >= essa data
            (não só ==, pra cobrir o eCarta processar o envio com 1-2 dias de
            atraso em relação ao registro da intimação no PJe). Isso existe
            porque uma intimação especifica pode nao ter side no eCarta (ex:
            destinatario sem endereco -> "Expediente enviado por outro meio" —
            eCarta nunca gera carta pra ela), mas as OUTRAS cartas do mesmo
            lote/dia continuam validas e nao podem se perder por causa disso.
            Se data_referencia não for parseável ou não for passada, cai no
            comportamento legado (correlação por substring de idPje).

    Returns:
        list[dict] com:
            ID_PJE, RASTREAMENTO, DESTINATARIO, DATA_ENVIO, DATA_ENTREGA, STATUS
        O campo STATUS já vem corrigido (falsos positivos detectados).
    """
    if not intimation_ids:
        return []

    # Re-obter número do processo (comportamento legado)
    try:
        from PEC.carta_utils import _obter_numero_processo as _obter_numero_processo
        numero_atual = _obter_numero_processo(driver, log)
        if numero_atual and process_number != numero_atual:
            if log:
                logger.info(f'[CARTA-API] process_number sobrescrito: {process_number} -> {numero_atual}')
            process_number = numero_atual
    except Exception:
        pass

    if not process_number:
        if log:
            logger.error('[CARTA-API] Número do processo não disponível')
        return []

    t_start = time.time()
    if log:
        logger.info(
            f'[CARTA-API] START — process={process_number} | '
            f'intimation_ids={intimation_ids}'
        )

    # ── Garante sessão HTTP ──
    session = _ecarta_ensure_session(driver, log=log)
    if not session:
        if log:
            logger.error('[CARTA-API] Falha ao obter sessão HTTP')
        return []

    # ── Etapa 1: GET tabela do processo ──
    url = f'{BASE}consultarProcesso.xhtml?codigo={process_number}'
    if log:
        logger.info(f'[CARTA-API] GET {url}')

    t1 = time.time()
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        if log:
            logger.error(f'[CARTA-API] Erro HTTP: {e}')
        _ecarta_reset_session()
        return []

    dur_get = time.time() - t1
    html = resp.text

    if 'input_user' in html or 'login-box' in html.lower():
        if log:
            logger.error('[CARTA-API] Sessão expirada — resetando')
        _ecarta_reset_session()
        return []

    # ── Etapa 2: Parse da tabela ──
    todas_rows = _parse_tabela_processo(html)
    if log:
        logger.info(
            f'[CARTA-API] {len(todas_rows)} linhas extraídas '
            f'(GET: {dur_get:.1f}s)'
        )

    if not todas_rows:
        return []

    # ── Etapa 3: Selecionar linhas-alvo ──
    # Preferencia: data de referencia detectada no PJe (>= essa data, cobre
    # atraso de processamento do eCarta e sobrevive a intimacoes individuais
    # sem correspondente no eCarta). Fallback: correlacao legada por idPje.
    data_ref_parsed = _parse_data(data_referencia) if data_referencia else None

    if data_ref_parsed:
        linhas_para_auditar = []
        for row in todas_rows:
            data_row = _parse_data(row.get('dataEnvio', ''))
            if data_row is not None and data_row >= data_ref_parsed:
                linhas_para_auditar.append(row)

        if log:
            logger.info(
                f'[CARTA-API] Selecao por DATA (>= {data_referencia}): '
                f'{len(linhas_para_auditar)} linha(s) de {len(todas_rows)}'
            )

        if not linhas_para_auditar:
            if log:
                logger.info('[CARTA-API] Nenhuma linha nesta data ou mais recente')
            return []
    else:
        if log:
            logger.info('[CARTA-API] Sem data_referencia utilizavel — usando correlacao legada por idPje')

        datas_correlacionadas = []
        for row in todas_rows:
            id_pje = row.get('idPje', '')
            if not id_pje:
                continue
            for iid in intimation_ids:
                if not iid:
                    continue
                if iid in id_pje or id_pje in iid:
                    data_envio = row.get('dataEnvio', '')
                    if data_envio and data_envio not in datas_correlacionadas:
                        datas_correlacionadas.append(data_envio)
                    if log:
                        logger.info(
                            f'[CARTA-API] CORRELAÇÃO: ID_PJE={id_pje} '
                            f'↔ intimação={iid} (data {data_envio})'
                        )
                    break

        if not datas_correlacionadas:
            if log:
                logger.info('[CARTA-API] Nenhuma correlação encontrada (nem por data, nem por idPje)')
            return []

        if log:
            logger.info(f'[CARTA-API] Datas correlacionadas (legado): {datas_correlacionadas}')

        linhas_para_auditar = [
            row for row in todas_rows
            if row.get('dataEnvio', '') in datas_correlacionadas
        ]

    # ── Etapa 4: Auditar rastreamentos das linhas selecionadas ──
    table_data = []

    if log:
        com_rastreio = sum(1 for r in linhas_para_auditar if re.match(r'^[A-Z]{2}\d{9}BR$', r.get('objeto', '')))
        logger.info(
            f'[CARTA-API] {len(linhas_para_auditar)} linhas na(s) data(s) alvo, '
            f'{com_rastreio} com rastreio para auditar'
        )

    for row in linhas_para_auditar:
        rastreio = row.get('objeto', '')
        status_original = row.get('status', '')
        status_final = status_original
        evidencia_devolucao = None

        # Auditar apenas se tem código de rastreio e status sugere "entregue"
        if re.match(r'^[A-Z]{2}\d{9}BR$', rastreio):
            try:
                eventos = _fetch_detalhes_rastreio(session, rastreio)
            except Exception as e:
                if log:
                    logger.warning(f'[CARTA-API] Erro ao auditar {rastreio}: {e}')
                eventos = []

            if eventos:
                status_final, evidencia_devolucao = _classificar_status(status_original, eventos)
                if log:
                    falso = (
                        RE_STATUS_ENTREGUE.search(status_original)
                        and status_final == 'DEVOLVIDO'
                    )
                    if falso:
                        logger.info(
                            f'[CARTA-API] ⚠️ FALSO POSITIVO: {rastreio} — '
                            f'tabela dizia "entregue" mas histórico mostra devolução'
                        )

        rastreamento_final = row.get('objetoLink', '') or rastreio
        table_data.append({
            'ID_PJE': row.get('idPje', ''),
            'RASTREAMENTO': rastreamento_final,
            'DESTINATARIO': row.get('destinatario', ''),
            'DATA_ENVIO': row.get('dataEnvio', ''),
            'DATA_ENTREGA': row.get('dataEntrega', ''),
            'STATUS': status_final,
            'EVIDENCIA': evidencia_devolucao,
        })

    dur_total = time.time() - t_start
    if log:
        falsos = sum(
            1 for r in table_data
            if RE_STATUS_DEVOLVIDO.search(r.get('STATUS', ''))
            and not RE_STATUS_DEVOLVIDO.search(
                next(
                    (orig.get('status', '') for orig in todas_rows
                     if orig.get('idPje') == r.get('ID_PJE')),
                    '',
                )
            )
        )
        logger.info(
            f'[CARTA-API] DONE — {len(table_data)} registros, '
            f'{falsos} falso(s) positivo(s) corrigido(s) '
            f'(total: {dur_total:.1f}s)'
        )

    return table_data
