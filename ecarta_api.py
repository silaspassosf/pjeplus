"""
eCarta API — cliente HTTP puro (sem Selenium) para consulta de processos e rastreamentos.

Fluxo:
    1. GET consultarProcesso.xhtml?codigo=<processo> → tabela de intimações
    2. Para cada linha com código de rastreio:
       a. GET consultarObjeto.xhtml?codigo=<rastreio> → extrai ViewState
       b. POST JSF parcial → extrai histórico de eventos (tabDetalhesObjeto)
    3. Detecta falsos positivos: "entregue ao destinatário" que na verdade é devolução
    4. Gera relatório corrigido

Uso:
    from ecarta_api import gerar_relatorio_ecarta
    import requests

    s = requests.Session()
    # Injete cookies de uma sessão autenticada no eCarta:
    s.cookies.set('JSESSIONID', 'xxxxxxxxxxxxxxxx', domain='aplicacoes1.trt2.jus.br')
    # ou carregue de arquivo:
    # for cookie in carregar_cookies_netscape('cookies.txt'):
    #     s.cookies.set(cookie.name, cookie.value, domain=cookie.domain)

    relatorio = gerar_relatorio_ecarta(s, '1000813-97.2016.5.02.0703')
    print(relatorio)
"""

from __future__ import annotations

import re
import json
import logging
import time
from datetime import datetime
from typing import Optional
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)

BASE = "https://aplicacoes1.trt2.jus.br/eCarta-web/"

# ─── Constantes de detecção de falso positivo ───

# Se qualquer um destes aparecer no histórico, o status real é DEVOLVIDO,
# mesmo que o status resumido da tabela diga "Objeto entregue ao destinatário"
PADROES_DEVOLUCAO = [
    re.compile(r'objeto\s+ser[aá]\s+devolvido\s+ao\s+remetente', re.IGNORECASE),
    re.compile(r'objeto\s+saiu\s+para\s+entrega\s+ao\s+remetente', re.IGNORECASE),
    re.compile(r'objeto\s+entregue\s+ao\s+remetente', re.IGNORECASE),
    re.compile(r'devolvido\s+ao\s+remetente', re.IGNORECASE),
]

# Se o status da tabela já indica devolução explicitamente
PADROES_STATUS_DEVOLVIDO = [
    re.compile(r'devolvid[oa]', re.IGNORECASE),
]

# Se o status indica entrega ao destinatário (candidato a falso positivo)
PADROES_STATUS_ENTREGUE = [
    re.compile(r'entregue\s+ao\s+destinat[aá]rio', re.IGNORECASE),
]


# ═══════════════════════════════════════════════════════════════════
# Helpers de parse
# ═══════════════════════════════════════════════════════════════════

def _extrair_viewstate(html: str) -> str:
    """Extrai javax.faces.ViewState do HTML."""
    m = re.search(r'name="javax\.faces\.ViewState"[^>]+value="([^"]+)"', html)
    return m.group(1) if m else ''


def _extrair_tabela_processo(html: str) -> list[dict]:
    """
    Extrai linhas da tabela principal (main:tabDoc_data) do consultarProcesso.xhtml
    ou consultarObjeto.xhtml.

    Colunas: dataEnvio, dataEntrega, processo, idPje, objeto, status, destinatario, orgaoJulgador
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Seletores em ordem de prioridade
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

        # Extrai código de rastreamento (XX999999999BR) da célula do objeto
        objetoTd = tds[4] if len(tds) > 4 else None
        rastreio = ''
        rastreio_link = ''
        if objetoTd:
            # Tenta achar span com id terminado em :rastreamento
            span = objetoTd.find('span', id=re.compile(r':rastreamento$'))
            if span:
                rastreio = span.get_text(strip=True)
                link_el = span.find_parent('a')
                if link_el and link_el.get('href'):
                    href = link_el['href']
                    rastreio_link = f'https://aplicacoes1.trt2.jus.br{href}' if href.startswith('/') else href
            else:
                # Tenta achar link direto
                link = objetoTd.find('a', href=True)
                if link:
                    href = link['href']
                    if 'consultarObjeto.xhtml?codigo=' in href:
                        m = re.search(r'codigo=([^&]+)', href)
                        if m:
                            rastreio = m.group(1)
                            rastreio_link = f'https://aplicacoes1.trt2.jus.br{href}' if href.startswith('/') else href

        # Se não achou rastreio no formato, pega texto bruto
        if not rastreio:
            texto_objeto = get_text(4)
            m = re.match(r'([A-Z]{2}\d{9}BR)', texto_objeto)
            if m:
                rastreio = m.group(1)
                rastreio_link = f'{BASE}consultarObjeto.xhtml?codigo={rastreio}'

        rows.append({
            'dataEnvio': get_text(0),
            'dataEntrega': get_text(1),
            'processo': get_text(2),
            'idPje': get_text(3),
            'objeto': rastreio or get_text(4),
            'objetoLink': rastreio_link,
            'status': get_text(5),
            'destinatario': get_text(6),
            'orgaoJulgador': get_text(7),
        })

    return rows


def _extrair_eventos_do_xml_partial(xml_text: str) -> list[dict]:
    """
    Extrai eventos de rastreamento do XML <partial-response> retornado pelo POST JSF.

    Retorna lista de {dataEvento, descricao, cidadeUf}.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        logger.warning('Falha ao parsear XML do partial-response')
        return []

    # Namespace default do JSF (se houver)
    ns = 'http://xmlns.jcp.org/jsf/partial'

    for update in root.findall(f'.//{{{ns}}}update') or root.findall('update'):
        update_id = update.get('id', '')
        if update_id != 'detalhesObjeto':
            continue

        # O conteúdo do <update> é HTML escapado ou CDATA
        inner_html = update.text or ''
        # Tenta parsear como CDATA
        for child in update:
            if child.tag == f'{{{ns}}}CDATA' or child.tag == 'CDATA':
                inner_html = child.text or ''
                break
            inner_html += ET.tostring(child, encoding='unicode')

        if not inner_html:
            continue

        # Parse do HTML interno
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
            texto_primeira = tds[0].get_text(strip=True)
            if 'Nenhum resultado' in texto_primeira:
                continue

            # Descrição: junta texto dos spans e <br> com separador
            descricao_td = tds[1]
            partes = []
            for content in descricao_td.contents:
                if hasattr(content, 'get_text'):
                    partes.append(content.get_text(strip=True))
                elif isinstance(content, str):
                    partes.append(content.strip())
            descricao = ' | '.join(p for p in partes if p)

            eventos.append({
                'dataEvento': tds[0].get_text(strip=True),
                'descricao': descricao or tds[1].get_text(' | ', strip=True),
                'cidadeUf': tds[2].get_text(strip=True) if len(tds) > 2 else '',
            })

        return eventos

    return []


# ═══════════════════════════════════════════════════════════════════
# Chamadas HTTP
# ═══════════════════════════════════════════════════════════════════

def consultar_processo(session: requests.Session, numero_processo: str) -> list[dict]:
    """
    GET consultarProcesso.xhtml?codigo=<numero_processo>
    Retorna lista de rows da tabela eCarta.
    """
    url = f'{BASE}consultarProcesso.xhtml?codigo={numero_processo}'
    logger.info(f'[eCarta] GET {url}')
    t0 = time.time()

    resp = session.get(url, timeout=30)
    dur = time.time() - t0
    logger.info(f'[eCarta] GET processo → {resp.status_code} ({len(resp.text)} chars, {dur:.1f}s)')

    resp.raise_for_status()

    # Detecta tela de login
    if 'input_user' in resp.text or 'login-box' in resp.text.lower():
        raise RuntimeError(
            'Sessão não autenticada no eCarta. Forneça cookies de uma sessão ativa '
            '(JSESSIONID).'
        )

    rows = _extrair_tabela_processo(resp.text)
    logger.info(f'[eCarta] {len(rows)} linhas extraídas da tabela de processo')
    return rows


def consultar_detalhes_rastreio(session: requests.Session, codigo_rastreio: str) -> list[dict]:
    """
    Fluxo completo para obter histórico de eventos de um rastreamento:
        1. GET consultarObjeto.xhtml?codigo=<rastreio>
        2. POST JSF parcial para obter <partial-response> com detalhesObjeto
        3. Extrai eventos

    Retorna lista de {dataEvento, descricao, cidadeUf}.
    """
    # ── Etapa 1: GET da página ──
    url = f'{BASE}consultarObjeto.xhtml?codigo={codigo_rastreio}'
    logger.info(f'[eCarta] GET objeto {url}')
    t0 = time.time()

    resp = session.get(url, timeout=30)
    dur_get = time.time() - t0
    logger.info(f'[eCarta] GET objeto → {resp.status_code} ({len(resp.text)} chars, {dur_get:.1f}s)')
    resp.raise_for_status()

    viewstate = _extrair_viewstate(resp.text)
    if not viewstate:
        logger.warning(f'[eCarta] ViewState não encontrado para rastreio {codigo_rastreio}')
        return []

    # Verifica se há link de rastreamento (main:tabDoc:N:rastreamento)
    indices = []
    for m in re.finditer(r'id="main:tabDoc:(\d+):rastreamento"', resp.text):
        indices.append(int(m.group(1)))

    if not indices:
        logger.warning(f'[eCarta] Nenhum link rastreamento encontrado para {codigo_rastreio}')
        # Tenta extrair eventos diretamente do HTML (caso já venham inline)
        return _extrair_eventos_inline(resp.text)

    # ── Etapa 2: POST JSF para cada índice ──
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

        logger.info(f'[eCarta] POST JSF source={source}')
        t1 = time.time()
        post_resp = session.post(
            f'{BASE}consultarObjeto.xhtml',
            data=body,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'Faces-Request': 'partial/ajax',
            },
            timeout=30,
        )
        dur_post = time.time() - t1
        logger.info(f'[eCarta] POST JSF → {post_resp.status_code} ({len(post_resp.text)} chars, {dur_post:.1f}s)')
        post_resp.raise_for_status()

        eventos = _extrair_eventos_do_xml_partial(post_resp.text)
        if eventos:
            todos_eventos.extend(eventos)
        else:
            logger.warning(f'[eCarta] Nenhum evento extraído do POST para índice {idx}')

        # Pequeno delay entre requests
        time.sleep(0.15)

    return todos_eventos


def _extrair_eventos_inline(html: str) -> list[dict]:
    """Fallback: tenta extrair eventos diretamente do HTML da página."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    tbody = (
        soup.select_one('#tabDetalhesObjeto_data')
        or soup.select_one('tbody[id$="tabDetalhesObjeto_data"]')
    )
    if not tbody:
        return []

    eventos = []
    for tr in tbody.find_all('tr', recursive=False):
        tds = tr.find_all('td')
        if len(tds) < 2:
            continue
        if 'Nenhum resultado' in tds[0].get_text(strip=True):
            continue
        eventos.append({
            'dataEvento': tds[0].get_text(strip=True),
            'descricao': tds[1].get_text(' | ', strip=True),
            'cidadeUf': tds[2].get_text(strip=True) if len(tds) > 2 else '',
        })
    return eventos


# ═══════════════════════════════════════════════════════════════════
# Detecção de falsos positivos
# ═══════════════════════════════════════════════════════════════════

def _status_contem(texto: str, padroes: list[re.Pattern]) -> bool:
    return any(p.search(texto) for p in padroes)


def _eventos_contem(eventos: list[dict], padroes: list[re.Pattern]) -> bool:
    """Verifica se algum evento (descricao) casa com algum dos padrões."""
    for ev in eventos:
        desc = ev.get('descricao', '')
        for p in padroes:
            if p.search(desc):
                return True
    return False


def classificar_status(row: dict, eventos: list[dict]) -> str:
    """
    Classifica o status real de uma intimação, considerando o histórico de eventos.

    Retorna:
        'ENTREGUE'     — realmente entregue ao destinatário
        'DEVOLVIDO'    — devolvido ao remetente (possível falso positivo corrigido)
        'SEM_EVENTOS'  — sem eventos para auditar (mantém status original)
        outro           — status original da tabela
    """
    status_original = row.get('status', '')

    # Se já está marcado como devolvido na tabela, mantém
    if _status_contem(status_original, PADROES_STATUS_DEVOLVIDO):
        return 'DEVOLVIDO'

    # Se não tem eventos para auditar, retorna o status original
    if not eventos:
        # Se o status original diz "entregue" mas não temos eventos, marcamos como suspeito
        if _status_contem(status_original, PADROES_STATUS_ENTREGUE):
            return 'ENTREGUE_SEM_AUDITORIA'
        return status_original or 'SEM_EVENTOS'

    # Verifica se o histórico contém evidências de devolução
    if _eventos_contem(eventos, PADROES_DEVOLUCAO):
        return 'DEVOLVIDO'

    # Se o status original diz "entregue" e não há evidência de devolução, é entrega real
    if _status_contem(status_original, PADROES_STATUS_ENTREGUE):
        return 'ENTREGUE'

    return status_original or 'INDETERMINADO'


# ═══════════════════════════════════════════════════════════════════
# Relatório
# ═══════════════════════════════════════════════════════════════════

def gerar_relatorio_ecarta(
    session: requests.Session,
    numero_processo: str,
    auditar_rastreamentos: bool = True,
) -> dict:
    """
    Fluxo completo: processo → tabela eCarta → detalhes de rastreamento → relatório.

    Args:
        session: requests.Session com cookies de autenticação
        numero_processo: número CNJ do processo (ex: '1000813-97.2016.5.02.0703')
        auditar_rastreamentos: se True, faz POST JSF para obter histórico detalhado
                               de cada rastreamento e detectar falsos positivos

    Returns:
        dict com:
            - processo: número do processo
            - total_linhas: total de linhas na tabela eCarta
            - linhas_com_rastreio: quantas têm código de rastreamento
            - linhas_auditadas: quantas tiveram eventos extraídos
            - falsos_positivos: quantas "entregues" eram na verdade "devolvidas"
            - resultados: lista de dicts com dados completos de cada linha
            - conteudo_formatado: string formatada (estilo relatório atual)
            - resumo: string com sumário
    """
    logger.info(f'[eCarta] === INÍCIO relatório para {numero_processo} ===')
    t_total = time.time()

    # ── Etapa 1: Tabela do processo ──
    rows = consultar_processo(session, numero_processo)

    if not rows:
        return {
            'processo': numero_processo,
            'total_linhas': 0,
            'linhas_com_rastreio': 0,
            'linhas_auditadas': 0,
            'falsos_positivos': 0,
            'resultados': [],
            'conteudo_formatado': '(sem dados no eCarta)',
            'resumo': 'Nenhum dado encontrado no eCarta para este processo.',
        }

    # ── Etapa 2: Para cada linha com rastreio, auditar ──
    linhas_com_rastreio = 0
    linhas_auditadas = 0
    falsos_positivos = 0
    resultados = []

    for row in rows:
        rastreio = row.get('objeto', '')
        is_rastreio_valido = bool(re.match(r'^[A-Z]{2}\d{9}BR$', rastreio))

        resultado = dict(row)  # cópia
        resultado['eventos'] = []
        resultado['status_real'] = row.get('status', '')
        resultado['falso_positivo'] = False

        if is_rastreio_valido:
            linhas_com_rastreio += 1

            if auditar_rastreamentos:
                try:
                    eventos = consultar_detalhes_rastreio(session, rastreio)
                except Exception as e:
                    logger.error(f'[eCarta] Erro ao auditar {rastreio}: {e}')
                    eventos = []

                resultado['eventos'] = eventos

                if eventos:
                    linhas_auditadas += 1

                status_real = classificar_status(row, eventos)
                resultado['status_real'] = status_real

                # Detecta falso positivo: tabela diz "entregue" mas eventos mostram devolução
                status_original = row.get('status', '')
                if (
                    _status_contem(status_original, PADROES_STATUS_ENTREGUE)
                    and status_real == 'DEVOLVIDO'
                ):
                    resultado['falso_positivo'] = True
                    falsos_positivos += 1
            else:
                resultado['status_real'] = row.get('status', '')
        else:
            # Sem rastreio (ex: "Carta Simples", "Indisponível")
            resultado['status_real'] = row.get('status', '')

        resultados.append(resultado)

    # ── Etapa 3: Gerar conteúdo formatado ──
    conteudo_formatado = _formatar_resultados(resultados, numero_processo)

    # Resumo
    partes_resumo = [f'Processo: {numero_processo}']
    partes_resumo.append(f'Total de intimações no eCarta: {len(rows)}')
    partes_resumo.append(f'Com rastreamento: {linhas_com_rastreio}')
    if auditar_rastreamentos:
        partes_resumo.append(f'Auditadas (eventos extraídos): {linhas_auditadas}')
        if falsos_positivos:
            partes_resumo.append(f'⚠️ FALSOS POSITIVOS CORRIGIDOS: {falsos_positivos}')
        else:
            partes_resumo.append('Nenhum falso positivo detectado')
    else:
        partes_resumo.append('(auditoria de rastreamentos desabilitada)')

    dur_total = time.time() - t_total
    partes_resumo.append(f'Tempo total: {dur_total:.1f}s')

    return {
        'processo': numero_processo,
        'total_linhas': len(rows),
        'linhas_com_rastreio': linhas_com_rastreio,
        'linhas_auditadas': linhas_auditadas,
        'falsos_positivos': falsos_positivos,
        'resultados': resultados,
        'conteudo_formatado': conteudo_formatado,
        'resumo': '\n'.join(partes_resumo),
    }


def _formatar_resultados(resultados: list[dict], numero_processo: str) -> str:
    """Formata os resultados no estilo do relatório atual de carta."""
    blocos = []
    for i, r in enumerate(resultados, 1):
        linhas = []
        linhas.append(f"    Id Pje: {r.get('idPje', '')}")

        rastreamento = r.get('objetoLink', '') or r.get('objeto', '')
        if rastreamento:
            if rastreamento.startswith('http'):
                linhas.append(f'    Rastreamento: {rastreamento}')
            else:
                linhas.append(f'    Rastreamento: {rastreamento}')
        else:
            linhas.append('    Rastreamento: Indisponivel')

        linhas.append(f"    Destinatario: {r.get('destinatario', '')}")
        envio = r.get('dataEnvio', '') or 'Indisponivel'
        linhas.append(f'    Data do envio: {envio}')
        entrega = r.get('dataEntrega', '') or 'Indisponivel'
        linhas.append(f'    Data da entrega: {entrega}')

        # Status com correção de falso positivo
        status_exibido = r.get('status_real', r.get('status', ''))
        if r.get('falso_positivo'):
            status_exibido = f'{status_exibido} ⚠️ (tabela dizia "Objeto entregue ao destinatário", mas histórico mostra DEVOLUÇÃO)'
        linhas.append(f'    Status: {status_exibido}')

        # Se tem eventos, mostra os mais relevantes
        eventos = r.get('eventos', [])
        if eventos:
            linhas.append('    Histórico de eventos:')
            for ev in eventos:
                linhas.append(f'      {ev["dataEvento"]} — {ev["descricao"]} ({ev["cidadeUf"]})')

        bloco = '\n'.join(linhas)
        if i < len(resultados):
            bloco += '\n' + '-' * 50
        blocos.append(bloco)

    return '\n\n'.join(blocos)


# ═══════════════════════════════════════════════════════════════════
# Teste rápido
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

    if len(sys.argv) < 3:
        print('Uso: py ecarta_api.py <JSESSIONID> <numero_processo>')
        print('Ex:  py ecarta_api.py A1B2C3D4... 1000813-97.2016.5.02.0703')
        sys.exit(1)

    jsessionid = sys.argv[1]
    processo = sys.argv[2]

    s = requests.Session()
    s.cookies.set('JSESSIONID', jsessionid, domain='aplicacoes1.trt2.jus.br')
    # Tenta também como cookie de sessão genérico
    s.cookies.set('JSESSIONID', jsessionid, domain='.trt2.jus.br')

    rel = gerar_relatorio_ecarta(s, processo)

    print('=' * 60)
    print(rel['resumo'])
    print('=' * 60)
    print(rel['conteudo_formatado'])

    # Salva JSON para inspeção
    json_path = f'ecarta_{processo.replace(".", "_").replace("-", "_")}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rel, f, ensure_ascii=False, indent=2, default=str)
    print(f'\n[JSON salvo em {json_path}]')
