"""Mandado - Apoio a Fluxos (Outros + Utilitarios)

Consolidado de:
    processamento_outros.py — ramo Oficial de Justica / Outros
    utils_sigilo.py — sigilo de certidao e anexos
    utils_lembrete.py — lembrete de bloqueio
    atos_wrapper.py — wrappers de atos usados por regras

Entrypoint publico: fluxo_mandados_outros()
"""

# ════════════════════════════════════════
# Imports (consolidados dos 4 arquivos)
# ════════════════════════════════════════

import os
import re
from Fix.utils import remover_acentos
from typing import Optional, Any, List, Tuple

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from Fix.abas import validar_conexao_driver
from Fix.extracao import extrair_direto, extrair_documento, criar_lembrete_posit
from Fix.log import logger
from Fix.selenium_base import aguardar_e_clicar

from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj,
    mov_arquivar,
    ato_meiosub,
)


# ════════════════════════════════════════
# 1. atos_wrapper.py — re-export de atos/
# ════════════════════════════════════════

__all__ = [
    'ato_judicial',
    'ato_meios',
    'ato_pesquisas',
    'ato_crda',
    'ato_crte',
    'ato_bloq',
    'ato_idpj',
    'ato_termoE',
    'ato_termoS',
    'ato_edital',
    'pec_idpj',
    'mov_arquivar',
    'ato_meiosub',
]


# ════════════════════════════════════════
# 2. utils_lembrete.py — lembrete de bloqueio
# ════════════════════════════════════════

def lembrete_bloq(driver: WebDriver, debug: bool = False) -> bool:
    """Wrapper compatível - delegado para criar_lembrete_posit genérico."""
    return criar_lembrete_posit(
        driver,
        titulo="Bloqueio pendente",
        conteudo="processar após IDPJ",
        debug=debug
    )


# ════════════════════════════════════════
# 3. utils_sigilo.py — sigilo de certidao e anexos
# ════════════════════════════════════════

def retirar_sigilo(elemento: WebElement, driver: Optional[WebDriver] = None, debug: bool = False) -> bool:
    """
     DIRETO E SIMPLES: Verifica tl-nao-sigiloso (AZUL) antes de qualquer ação.

    Lógica clara:
    1. Busca botão de sigilo
    2. Se TEM tl-nao-sigiloso (azul) → retorna True (JÁ SEM SIGILO)
    3. Se TEM tl-sigiloso (vermelho) → clica para remover
    4. Caso contrário → retorna True (sem sigilo)

    Args:
        elemento: WebElement do documento na timeline
        driver: WebDriver Selenium
        debug: Exibir logs detalhados

    Returns:
        True se sigilo foi removido ou já estava removido, False em erro
    """
    if not elemento:
        return False

    if not driver:
        try:
            if hasattr(elemento, '_parent') and hasattr(elemento._parent, 'execute_script'):
                driver = elemento._parent
            else:
                return False
        except Exception:
            return False

    def _link_documento() -> Optional[WebElement]:
        links = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        if not links:
            return None
        for link in links:
            role = (link.get_attribute('role') or '').lower()
            target = (link.get_attribute('target') or '').lower()
            if role == 'button' or target != '_blank':
                return link
        return links[-1]

    def _tem_sigilo_link() -> bool:
        link = _link_documento()
        if not link:
            return False
        classes = (link.get_attribute('class') or '').lower()
        if debug:
            logger.info(f"[SIGILO_DEBUG] Classes link documento: {classes}")
        return 'is-sigiloso' in classes

    try:
        if not _tem_sigilo_link():
            if debug:
                logger.info('[SIGILO_DEBUG] Link sem is-sigiloso → JÁ SEM SIGILO')
            return True

        btn_sigilo = None
        seletores = [
            'pje-doc-sigiloso button',
            'pje-doc-sigiloso span button',
            'button i.fa-wpexplorer',
            'i.fa-wpexplorer.tl-sigiloso',
            'i.fa-wpexplorer',
        ]
        for seletor in seletores:
            try:
                candidato = elemento.find_element(By.CSS_SELECTOR, seletor)
                if candidato.is_displayed():
                    btn_sigilo = candidato
                    break
            except Exception:
                continue

        if not btn_sigilo:
            if debug:
                logger.error('[SIGILO_DEBUG] Botão de sigilo não encontrado com link is-sigiloso ativo')
            return False

        try:
            driver.execute_script('arguments[0].click();', btn_sigilo)
        except Exception:
            btn_sigilo.click()

        import time
        for _ in range(8):
            time.sleep(0.25)
            try:
                if not _tem_sigilo_link():
                    if debug:
                        logger.info('[SIGILO_DEBUG] ✅ is-sigiloso removido após clique')
                    return True
            except Exception:
                pass

        if debug:
            logger.error('[SIGILO_DEBUG] ❌ Clique executado, mas classe is-sigiloso permaneceu')
        return False

    except Exception as e:
        if debug:
            logger.error(f"[SIGILO_DEBUG] Erro geral: {e}")
        return False


# ── helpers API para identificação de documentos sigilosos ──────────────────

def _extrair_id_processo_da_url(driver: WebDriver) -> Optional[str]:
    """Extrai id_processo numérico da URL atual do PJe (/processo/{id}/)."""
    try:
        m = re.search(r'/processo/(\d+)', driver.current_url)
        return m.group(1) if m else None
    except Exception:
        return None


def _criar_api_client_local(driver: WebDriver):
    """Cria PjeApiClient a partir do driver (lazy import)."""
    try:
        from api.variaveis_client import PjeApiClient, session_from_driver
        sess, trt_host = session_from_driver(driver)
        return PjeApiClient(sess, trt_host, grau=1)
    except Exception:
        return None


def _extrair_texto_certidao_via_api(driver: WebDriver, log: bool = True) -> Optional[str]:
    """Extrai o texto COMPLETO da certidão de devolução via API (todas as páginas).

    Baixa o PDF binário pelo endpoint /conteudo e extrai com pdfplumber,
    mesmo approach usado em bianca/triagem/coleta.py. Não depende do PDF
    viewer do PJe (que só renderiza uma página por vez).
    """
    import io as _io

    id_processo = _extrair_id_processo_da_url(driver)
    if not id_processo:
        if log:
            logger.warning('[CERTIDAO_API] id_processo não encontrado na URL')
        return None

    client = _criar_api_client_local(driver)
    if not client:
        if log:
            logger.warning('[CERTIDAO_API] Falha ao criar API client')
        return None

    try:
        timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
        if not timeline:
            if log:
                logger.warning('[CERTIDAO_API] Timeline vazia')
            return None

        import unicodedata
        def _norm(t):
            return unicodedata.normalize('NFD', (t or '').lower()).encode('ascii', 'ignore').decode()

        id_certidao = None
        for doc in timeline:
            if not isinstance(doc, dict):
                continue
            # id numérico (ex: 465383360) — necessário para o endpoint /conteudo
            # idUnicoDocumento é UID alfanumérico (ex: badd6fa) que a API não aceita
            doc_id = str(doc.get('id') or doc.get('idUnicoDocumento') or '')
            if not doc_id:
                continue
            t = _norm(doc.get('tipo', '')) + ' ' + _norm(doc.get('titulo', ''))
            if 'certid' in t and 'devolu' in t:
                id_certidao = doc_id
                if log:
                    logger.info('[CERTIDAO_API] Certidão encontrada: uid=%s', id_certidao)
                break

        if not id_certidao:
            if log:
                logger.warning('[CERTIDAO_API] Certidão de devolução não encontrada na timeline')
            return None

        url_pdf = client._url(
            f'/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_certidao}/conteudo')
        if log:
            logger.info('[CERTIDAO_API] Baixando PDF: %s', url_pdf)
        resp = client.sess.get(url_pdf, timeout=60)
        if resp.status_code != 200:
            if log:
                logger.warning('[CERTIDAO_API] HTTP %s ao baixar PDF', resp.status_code)
            return None

        magic = resp.content[:5] if resp.content else b''
        if magic != b'%PDF-':
            if log:
                logger.warning('[CERTIDAO_API] Resposta não é PDF (magic=%r)', magic)
            return None

        try:
            import pdfplumber
        except ImportError:
            if log:
                logger.warning('[CERTIDAO_API] pdfplumber não instalado')
            return None

        textos = []
        with pdfplumber.open(_io.BytesIO(resp.content)) as pdf:
            for i, pag in enumerate(pdf.pages):
                t = pag.extract_text()
                if t:
                    textos.append(t)
                if log:
                    logger.debug('[CERTIDAO_API] Pág %d: %d chars', i + 1, len(t or ''))

        texto_total = '\n'.join(textos).strip()
        if log:
            logger.info('[CERTIDAO_API] Texto extraído: %d chars, %d páginas', len(texto_total), len(pdf.pages))
        return texto_total if texto_total else None

    except Exception as e:
        if log:
            logger.error('[CERTIDAO_API] Erro: %s', e)
        return None



# ── extração de documentos decisão/despacho via API (igual P2B) ─────────────

def _extrair_documentos_decisao_despacho_api(driver: WebDriver, log: bool = True) -> List[Tuple[str, str, int]]:
	"""Extrai documentos de decisão/despacho via API (timeline → PDF → pdfplumber).

	Mesmo approach do P2B (extrair_documento_relevante em p2b_gateway.py).
	Busca TODOS os documentos despacho/decisão/sentença/conclusão da timeline,
	baixa o PDF de cada um e extrai o texto com pdfplumber.

	Retorna lista de (texto_documento, tipo_documento, idx) — compatível com o
	formato esperado pelo loop de aplicar_regras_argos().

	Limite interno de 3 documentos (igual ao loop DOM original).
	"""
	import io as _io
	import unicodedata

	_TIPOS_RELEVANTES = re.compile(
		r'^(despacho|decis[aã]o|senten[cç]a|conclus[aã]o)',
		re.IGNORECASE,
	)

	def _norm(t):
		return unicodedata.normalize('NFD', (t or '').lower()).encode('ascii', 'ignore').decode()

	id_processo = _extrair_id_processo_da_url(driver)
	if not id_processo:
		if log:
			logger.warning('[ARGOS_API] id_processo não encontrado na URL')
		return []

	client = _criar_api_client_local(driver)
	if not client:
		if log:
			logger.warning('[ARGOS_API] Falha ao criar API client')
		return []

	try:
		timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
		if not timeline:
			if log:
				logger.info('[ARGOS_API] Timeline vazia')
			return []

		# Filtrar documentos relevantes (despacho/decisão/sentença/conclusão)
		docs_relevantes = []
		for i, doc in enumerate(timeline):
			if not isinstance(doc, dict):
				continue
			tipo = (doc.get('tipo') or '').strip()
			if _TIPOS_RELEVANTES.match(tipo):
				docs_relevantes.append((i, doc))

		if not docs_relevantes:
			if log:
				logger.info('[ARGOS_API] Nenhum documento despacho/decisão na timeline')
			return []

		if log:
			logger.info(
				'[ARGOS_API] %d documento(s) despacho/decisão encontrados na timeline',
				len(docs_relevantes),
			)

		resultados = []
		for idx_original, doc in docs_relevantes[:3]:
			id_doc = str(doc.get('id') or doc.get('idDocumento') or '')
			tipo_doc = doc.get('tipo', '')
			if not id_doc:
				continue

			try:
				url_conteudo = client._url(
					f'/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo'
				)
				resp = client.sess.get(url_conteudo, timeout=60)
				if resp.status_code != 200:
					if log:
						logger.warning('[ARGOS_API] HTTP %s ao baixar doc %s', resp.status_code, id_doc)
					continue

				pdf_bytes = resp.content
				if not pdf_bytes or not pdf_bytes.startswith(b'%PDF'):
					if log:
						logger.warning('[ARGOS_API] Doc %s não é PDF (magic=%r)', id_doc, (pdf_bytes or b'')[:5])
					continue

				try:
					import pdfplumber
				except ImportError:
					if log:
						logger.warning('[ARGOS_API] pdfplumber não instalado')
					return resultados  # retorna o que já conseguiu

				textos = []
				with pdfplumber.open(_io.BytesIO(pdf_bytes)) as pdf:
					for pag in pdf.pages:
						t = pag.extract_text()
						if t:
							textos.append(t)

				texto_total = '\n'.join(textos).strip()
				if texto_total:
					if log:
						logger.info(
							'[ARGOS_API] Documento tipo=%s extraído: %d chars, %d páginas',
							tipo_doc,
							len(texto_total),
							len(pdf.pages),
						)
					resultados.append((texto_total, tipo_doc, idx_original))

			except Exception as e:
				if log:
					logger.warning('[ARGOS_API] Erro ao extrair doc %s: %s', id_doc, e)
				continue

		if log:
			logger.info(
				'[ARGOS_API] Extração concluída: %d/%d documentos extraídos',
				len(resultados),
				min(len(docs_relevantes), 3),
			)

		return resultados

	except Exception as e:
		if log:
			logger.error('[ARGOS_API] Erro na extração: %s', e)
		return []


def _identificar_uids_sigilosos_por_api(driver: WebDriver, log: bool = False) -> Optional[List[str]]:
    """Consulta timeline via API e retorna UIDs de docs sigilosos.

    Candidatos: certidão de devolução + 4 documentos mais recentes.
    Retorna None em caso de falha da API, lista vazia se sucesso mas nenhum sigiloso.
    """
    id_processo = _extrair_id_processo_da_url(driver)
    if not id_processo:
        if log:
            logger.info('[SIGILO_API] id_processo não encontrado na URL — usando fallback DOM')
        return None

    client = _criar_api_client_local(driver)
    if not client:
        if log:
            logger.info('[SIGILO_API] Falha ao criar API client — usando fallback DOM')
        return None

    try:
        timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
        if not timeline:
            return []

        # Apenas itens com idUnicoDocumento (documentos, não movimentos)
        docs = [item for item in timeline if item.get('idUnicoDocumento')]
        if not docs:
            return []

        # Separar certidão de devolução dos demais
        certidao = None
        outros: List[dict] = []
        for doc in docs:
            tipo = (doc.get('tipo') or '').lower()
            titulo = (doc.get('titulo') or '').lower()
            if ('certid' in tipo and 'devolu' in tipo) or ('certid' in titulo and 'devolu' in titulo):
                if certidao is None:
                    certidao = doc
            else:
                outros.append(doc)

        # Candidatos: certidão de devolução + 4 mais recentes (timeline já ordenada)
        candidatos: List[dict] = []
        if certidao:
            candidatos.append(certidao)
        candidatos.extend(outros[:4])

        # UIDs com sigilo=True
        uids_sigilosos: List[str] = []
        for doc in candidatos:
            tem_sigilo = (
                doc.get('sigiloso')
                or doc.get('sigilo')
                or doc.get('isSigiloso')
                or doc.get('isSignificant')
            )
            if tem_sigilo:
                uid = str(doc.get('idUnicoDocumento', ''))
                if uid:
                    uids_sigilosos.append(uid)
                    if log:
                        logger.info(
                            f'[SIGILO_API] Sigiloso via API: {doc.get("tipo")} uid={uid}'
                        )

        if log:
            logger.info(
                f'[SIGILO_API] {len(uids_sigilosos)} documento(s) sigilosos identificados via API'
            )
        return uids_sigilosos

    except Exception as e:
        if log:
            logger.info(f'[SIGILO_API] Erro ao consultar timeline: {e} — usando fallback DOM')
        return None


def _encontrar_elemento_por_uid(
    documentos_sequenciais: List[WebElement], uid: str
) -> Optional[WebElement]:
    """Retorna o WebElement de documentos_sequenciais cujo link contém o uid."""
    uid_norm = (uid or '').strip().lower()
    if not uid_norm:
        return None

    for elem in documentos_sequenciais:
        try:
            links = elem.find_elements(By.CSS_SELECTOR, 'a[href]')
            for link in links:
                href = (link.get_attribute('href') or '').lower()
                if uid_norm in href:
                    return elem
        except Exception:
            continue
    return None


# ── identificação de documentos sequenciais via API ─────────────────────────

def buscar_documentos_sequenciais_via_api(driver: WebDriver, log: bool = True) -> tuple:
    """Identifica documentos do bloco ARGOS via API + DOM e retorna (elementos, uids_sigilosos).

    Estratégia hibrida:
    1. API confirma quais documentos existem (certidao, decisao, etc.) e extrai
       UIDs sigilosos.
    2. DOM localiza os WebElements por matching de texto (mesmo algoritmo de
       buscar_documentos_sequenciais em Fix/core.py), sem depender de UIDs que
       nao correspondem aos hrefs do DOM.

    uids_sigilosos: UIDs cujo campo sigiloso=True na API (para passar direto a
    retirar_sigilo_fluxo_argos e evitar segunda chamada à API).

    Retorna ([], []) em caso de falha — caller deve usar fallback DOM.
    """
    import unicodedata

    def _norm(t: str) -> str:
        return unicodedata.normalize('NFD', (t or '').lower()).encode('ascii', 'ignore').decode()

    id_processo = _extrair_id_processo_da_url(driver)
    if not id_processo:
        return [], []

    client = _criar_api_client_local(driver)
    if not client:
        return [], []

    try:
        timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
        if log:
            _tl_shape = type(timeline).__name__ if timeline is not None else 'None'
            _tl_len = len(timeline) if isinstance(timeline, list) else '?'
            logger.info('[SEQUENCIAIS_API] timeline HTTP ok=%s  shape=%s  n=%s', timeline is not None, _tl_shape, _tl_len)
            if isinstance(timeline, list) and timeline:
                logger.debug('[SEQUENCIAIS_API] keys[0]=%s', list(timeline[0].keys()))
        if not timeline:
            return [], []

        docs = [item for item in timeline if item.get('idUnicoDocumento')]
        if not docs:
            return [], []

        # Certidão de devolução — mais recente (primeira na timeline)
        idx_cert = None
        for i, doc in enumerate(docs):
            t = _norm(doc.get('tipo', '')) + ' ' + _norm(doc.get('titulo', ''))
            if 'certid' in t and 'devolu' in t:
                idx_cert = i
                if log:
                    logger.debug('[SEQUENCIAIS_API] certidao_devolucao idx=%d uid=%s', i, doc['idUnicoDocumento'])
                break

        if idx_cert is None:
            if log:
                logger.info('[SEQUENCIAIS_API] Certidao de devolucao nao encontrada na API')
            return [], []

        # Decisão — primeira após certidão de devolução
        idx_decisao = None
        for i in range(idx_cert + 1, len(docs)):
            t = _norm(docs[i].get('tipo', '')) + ' ' + _norm(docs[i].get('titulo', ''))
            if 'decis' in t and 'certid' not in t:
                idx_decisao = i
                if log:
                    logger.debug('[SEQUENCIAIS_API] decisao idx=%d uid=%s', i, docs[i]['idUnicoDocumento'])
                break

        if idx_decisao is None:
            if log:
                logger.info('[SEQUENCIAIS_API] Decisao nao encontrada apos certidao na API')
            return [], []

        # UIDs sigilosos (campo sigiloso da API) — para repassar a retirar_sigilo
        def _tem_sigilo_api(doc: dict) -> bool:
            return bool(
                doc.get('sigiloso') or doc.get('sigilo')
                or doc.get('isSigiloso') or doc.get('isSignificant')
            )

        # UIDs sigilosos dentro do bloco (para hint em retirar_sigilo_fluxo_argos)
        bloco_idx = [idx_cert] + list(range(idx_cert + 1, idx_decisao)) + [idx_decisao]
        uids_sigilosos: List[str] = [
            docs[i]['idUnicoDocumento'] for i in bloco_idx if _tem_sigilo_api(docs[i])
        ]
        if log and uids_sigilosos:
            logger.debug('[SEQUENCIAIS_API] %d uid(s) sigilosos no bloco', len(uids_sigilosos))

        # Localizar no DOM por matching de texto (mesmo algoritmo de
        # buscar_documentos_sequenciais em Fix/core.py).
        # API ja confirmou que os documentos existem; agora encontramos os
        # WebElements correspondentes pelo conteudo textual, sem depender de
        # UIDs que nao batem com os hrefs do DOM.
        try:
            WebDriverWait(driver, 5).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')) > 0
            )
        except Exception:
            pass

        elementos = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if log:
            logger.debug('[SEQUENCIAIS_API] %d li.tl-item-container no DOM', len(elementos))
        if not elementos:
            return [], []

        # Encontrar certidao de devolucao por texto no DOM
        idx_cert_dom = None
        for idx, elem in enumerate(elementos):
            texto = _norm(elem.text.strip())
            if 'certidao de devolucao' in texto:
                idx_cert_dom = idx
                if log:
                    logger.debug('[SEQUENCIAIS_API] DOM: certidao_devolucao idx=%d', idx)
                break

        if idx_cert_dom is None:
            if log:
                logger.info('[SEQUENCIAIS_API] Certidao de devolucao nao localizada no DOM')
            return [], []

        # Encontrar decisao apos certidao por texto no DOM
        idx_decisao_dom = None
        for idx in range(idx_cert_dom + 1, len(elementos)):
            texto = _norm(elementos[idx].text.strip())
            if 'decisao(' in texto:
                idx_decisao_dom = idx
                if log:
                    logger.debug('[SEQUENCIAIS_API] DOM: decisao idx=%d', idx)
                break

        if idx_decisao_dom is None:
            if log:
                logger.info('[SEQUENCIAIS_API] Decisao nao localizada no DOM')
            return [], []

        resultado: List[WebElement] = [elementos[idx_cert_dom]]

        # Documentos do meio (entre certidao e decisao)
        _TERMOS_MEIO_DOM = {
            'certidao_expedicao': ['certidao de expedicao'],
            'planilha':           ['planilha de atualizacao'],
            'intimacao':          ['intimacao('],
        }
        for idx in range(idx_cert_dom + 1, idx_decisao_dom):
            texto = _norm(elementos[idx].text.strip())
            for nome, palavras in _TERMOS_MEIO_DOM.items():
                for palavra in palavras:
                    if palavra in texto:
                        resultado.append(elementos[idx])
                        if log:
                            logger.debug('[SEQUENCIAIS_API] DOM: %s idx=%d', nome, idx)
                        break

        resultado.append(elementos[idx_decisao_dom])

        if log:
            logger.info('[SEQUENCIAIS_API] %d documento(s) identificados via API+DOM', len(resultado))

        if len(resultado) >= 2:
            return resultado, uids_sigilosos
        return [], []

    except Exception as e:
        if log:
            logger.info('[SEQUENCIAIS_API] Erro: %s — fallback para DOM', e)
        return [], []


# ── função principal ─────────────────────────────────────────────────────────

def retirar_sigilo_fluxo_argos(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True, debug: bool = False, uids_sigilosos_hint: Optional[List[str]] = None) -> dict:
    """
     FUNÇÃO ÚNICA PARA TODO O FLUXO DE REMOÇÃO DE SIGILO DO ARGOS

    Respeita a ORDEM OBRIGATÓRIA do fluxo ARGOS:
    1º - Certidão de devolução (PRIMEIRO)
    2º - Demais documentos: certidão expedição, intimação, decisão, planilha

    Estratégia: identifica documentos sigilosos via API (atributo sigilo +
    uid), e usa o uid para localizar o elemento DOM correto antes de clicar.
    Fallback para varredura de texto no DOM se a API não responder.

    Args:
        driver: WebDriver Selenium
        documentos_sequenciais: Lista de WebElements dos documentos
        log: Exibir logs detalhados
        debug: Ativar modo debug com detalhes das classes CSS

    Returns:
        dict com status de cada etapa e documentos processados
    """
    from core.resultado_execucao import ResultadoExecucao
    if not documentos_sequenciais:
        return ResultadoExecucao(sucesso=False, status='FALHA', erro='nenhum_documento', detalhes={'etapa_erro': 'nenhum_documento'})

    resultado = {
        'sucesso': True,
        'certidao_devolucao': None,
        'demais_documentos': [],
        'total_processados': 0
    }

    # =======================================================
    # CAMINHO 1: Identificação via API (atributo sigilo + uid)
    # =======================================================
    if uids_sigilosos_hint:
        uids_sigilosos = uids_sigilosos_hint
    else:
        uids_sigilosos = _identificar_uids_sigilosos_por_api(driver, log=log)

    if uids_sigilosos:
        if log:
            logger.info(f'[SIGILO_ARGOS] API: {len(uids_sigilosos)} uid(s) sigilosos para processar')
        for uid in uids_sigilosos:
            elemento = _encontrar_elemento_por_uid(documentos_sequenciais, uid)
            if not elemento:
                if log:
                    logger.info(f'[SIGILO_ARGOS] uid={uid} não localizado no DOM — pulando')
                continue
            if debug:
                logger.info(f'[SIGILO_ARGOS][DEBUG] Processando uid={uid}')
            if retirar_sigilo(elemento, driver, debug=debug):
                if log:
                    logger.info(f'[SIGILO_ARGOS] Sigilo removido uid={uid}')
                resultado['total_processados'] += 1
            else:
                if log:
                    logger.error(f'[SIGILO_ARGOS] Falha ao remover sigilo uid={uid}')
                resultado['sucesso'] = False

        if log:
            logger.info(
                f'[SIGILO_ARGOS] Concluído (via API): {resultado["total_processados"]} documento(s) processados'
            )
        return resultado

    # =======================================================
    # CAMINHO 2: Fallback — varredura de texto no DOM (legado)
    # =======================================================
    if log:
        logger.info('[SIGILO_ARGOS] API indisponível — usando varredura de texto no DOM (fallback)')

    # ETAPA 1: CERTIDÃO DE DEVOLUÇÃO
    certidao_encontrada = None
    for doc in reversed(documentos_sequenciais):
        try:
            texto = doc.text.strip().lower()
            if "certidão de devolução" in texto or "certidao de devolucao" in texto:
                certidao_encontrada = doc
                break
        except Exception:
            continue

    if not certidao_encontrada:
        resultado['certidao_devolucao'] = {'status': 'nao_encontrada'}
    else:
        links_doc = certidao_encontrada.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        tem_sigilo = False
        if links_doc:
            link_correto = next(
                (l for l in links_doc if (l.get_attribute('role') or '').lower() == 'button'
                 or (l.get_attribute('target') or '').lower() != '_blank'),
                links_doc[-1]
            )
            tem_sigilo = 'is-sigiloso' in (link_correto.get_attribute('class') or '')
            if debug:
                logger.info(f'[SIGILO_ARGOS][DEBUG] certidao classes={link_correto.get_attribute("class")} sigiloso={tem_sigilo}')

        if not tem_sigilo:
            resultado['certidao_devolucao'] = {'status': 'ja_sem_sigilo'}
        elif retirar_sigilo(certidao_encontrada, driver, debug=debug):
            resultado['certidao_devolucao'] = {'status': 'removido'}
            resultado['total_processados'] += 1
        else:
            resultado['certidao_devolucao'] = {'status': 'erro'}
            resultado['sucesso'] = False

    # ETAPA 2: DEMAIS DOCUMENTOS (certidão expedição, intimação, decisão, planilha)
    _tipos = {
        'certidao_expedicao': (['certidão de expedição', 'certidao de expedicao'], 1),
        'intimacao':          (['intimação(', 'intimacao(', 'intimação', 'intimacao'], 3),
        'decisao':            (['decisão', 'decisao'], 1),
        'planilha':           (['planilha de atualização', 'planilha de atualizacao'], 1),
    }
    encontrados: dict = {k: [] for k in _tipos}

    idx_decisao = None
    for idx, elem in enumerate(documentos_sequenciais):
        texto = elem.text.strip().lower()
        if 'decisão(' in texto or 'decisao(' in texto:
            idx_decisao = idx
            break

    if idx_decisao is None:
        if log:
            logger.info('[SIGILO_ARGOS] Decisão não encontrada no DOM')
        return resultado

    for idx in range(1, idx_decisao):
        texto = documentos_sequenciais[idx].text.strip().lower()
        for tipo_nome, (palavras, limite) in _tipos.items():
            if len(encontrados[tipo_nome]) >= limite:
                continue
            for palavra in palavras:
                if palavra in texto:
                    encontrados[tipo_nome].append(documentos_sequenciais[idx])
                    break

    # Adicionar a decisão
    encontrados['decisao'].append(documentos_sequenciais[idx_decisao])

    for tipo_nome, elems in encontrados.items():
        for elemento in elems:
            links_doc = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
            tem_sigilo = False
            if links_doc:
                link_correto = next(
                    (l for l in links_doc if (l.get_attribute('role') or '').lower() == 'button'
                     or (l.get_attribute('target') or '').lower() != '_blank'),
                    links_doc[-1]
                )
                tem_sigilo = 'is-sigiloso' in (link_correto.get_attribute('class') or '')
                if debug:
                    logger.info(f'[SIGILO_ARGOS][DEBUG] {tipo_nome} sigiloso={tem_sigilo}')

            if not tem_sigilo:
                resultado['demais_documentos'].append({'tipo': tipo_nome, 'status': 'ja_sem_sigilo'})
            elif retirar_sigilo(elemento, driver, debug=debug):
                resultado['demais_documentos'].append({'tipo': tipo_nome, 'status': 'removido'})
                resultado['total_processados'] += 1
            else:
                resultado['demais_documentos'].append({'tipo': tipo_nome, 'status': 'erro'})
                resultado['sucesso'] = False

    if log:
        logger.info(
            f'[SIGILO_ARGOS] Concluído (fallback DOM): {resultado["total_processados"]} documento(s) processados'
        )
    return resultado


def retirar_sigilo_certidao_devolucao_primeiro(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True) -> bool:
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna apenas status da certidão."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    cert_status = resultado.get('certidao_devolucao', {}).get('status', 'erro')
    return cert_status in ['removido', 'ja_sem_sigilo', 'nao_encontrada']


def retirar_sigilo_demais_documentos_especificos(driver, documentos_sequenciais, log=True):
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna lista de demais documentos."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    return resultado.get('demais_documentos', [])


def retirar_sigilo_documentos_especificos(driver, documentos_sequenciais, log=True):
    """
     FUNÇÃO EFICIENTE - Remove sigilo APENAS dos documentos específicos fornecidos:
    Os documentos_sequenciais já vêm filtrados da buscar_documentos_sequenciais()
    MÁXIMO 5 documentos: 1 certidão devolução, 1 certidão expedição, 1 intimação, 1 decisão, 1 planilha

    NADA MAIS que isso - SEM VARRER TIMELINE INTEIRA!
    """
    if not documentos_sequenciais:
        return []

    #  EFICIÊNCIA: Os documentos já vêm filtrados, apenas remover sigilo diretamente
    documentos_processados = []
    total_processados = 0

    #  PROCESSAMENTO DIRETO: Remove sigilo apenas dos documentos fornecidos
    for i, elemento in enumerate(documentos_sequenciais):
        try:
            texto = elemento.text.strip()[:50] if elemento.text else f"DOCUMENTO_{i+1}"

            resultado_sigilo = retirar_sigilo(elemento, driver)

            if resultado_sigilo:
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'sucesso'
                })
                total_processados += 1
            else:
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'falha'
                })

        except Exception as e:
            if log:
                logger.error(f"[SIGILO_ESPECÍFICO]  Erro ao processar documento {i+1}: {e}")
            documentos_processados.append({
                'indice': i+1,
                'texto': texto if 'texto' in locals() else f"DOCUMENTO_{i+1}",
                'status': 'erro',
                'erro': str(e)
            })

    #  RELATÓRIO FINAL
    if log:
        for doc in documentos_processados:
            status_icon = "" if doc['status'] == 'sucesso' else "" if doc['status'] == 'erro' else ""

    return documentos_processados


# ════════════════════════════════════════
# 4. processamento_outros.py — ramo Oficial de Justica / Outros
# ════════════════════════════════════════

# Controla se o fluxo de "outros" pode automaticamente invocar atos
# Defina a variável de ambiente PJE_ALLOW_MANDADO_ATOS=1 para permitir
ALLOW_MANDADO_ATOS = os.environ.get('PJE_ALLOW_MANDADO_ATOS', '0').lower() in ('1', 'true', 'yes', 'y')


def ultimo_mdd(driver: WebDriver, log: bool = True) -> Tuple[Optional[str], Optional[Any]]:
    """
    Busca o último mandado na timeline (item com texto começando por 'Mandado' e ícone de gavel) e retorna (nome_autor, elemento_mandado).
    Versão robusta com verificações de conectividade.
    """
    try:
        # Verificação inicial de conexão
        if not validar_conexao_driver(driver, contexto="MDD_INICIO"):
            if log:
                logger.error('[MDD][ERRO_FATAL] Driver em estado inválido ao buscar mandado')
            return None, None

        # Usando aguardar_e_clicar ao invés de find_elements direto para maior robustez
        timeline = aguardar_e_clicar(driver, 'ul.timeline-container', timeout=5)
        if not timeline:
            if log:
                logger.error('[MDD][ERRO] Timeline não encontrada, tentando método direto')
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        else:
            itens = timeline.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')

        if not itens:
            if log:
                logger.warning('[MDD][ALERTA] Nenhum item encontrado na timeline')
            return None, None

        for idx, item in enumerate(itens):
            try:
                # Verificação periódica de conexão durante loop
                if idx % 10 == 0 and idx > 0:  # Verificar a cada 10 itens para não impactar performance
                    if not validar_conexao_driver(driver, contexto=f"MDD_LOOP_{idx}"):
                        if log:
                            logger.error(f'[MDD][ERRO_FATAL] Driver em estado inválido durante loop (item {idx})')
                        return None, None

                # Usa wait com timeout curto para não prejudicar performance
                link = aguardar_e_clicar(driver, item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'), timeout=1)
                if not link:
                    continue

                doc_text = link.text.strip().lower()
                if doc_text.startswith('mandado'):
                    # Procura ícone de gavel (fa-gavel)

                    icones = item.find_elements(By.CSS_SELECTOR, 'i.fa-gavel')
                    if not icones:
                        continue  # Não é mandado assinado por oficial
                    # Procura nome do autor próximo ao link ou assinatura
                    nome_autor = None
                    # Tenta encontrar assinatura padrão
                    try:
                        assinatura = item.find_element(By.CSS_SELECTOR, '.assinatura, .autor, .assinante, .nome-assinatura')
                        nome_autor = assinatura.text.strip()
                    except Exception:
                        # Fallback: procura texto logo após o link
                        try:
                            spans = item.find_elements(By.CSS_SELECTOR, 'span')
                            for s in spans:
                                s_text = s.text.strip()
                                if s_text and s_text.lower() != doc_text:
                                    nome_autor = s_text
                                    break
                        except Exception:
                            pass
                    return nome_autor, item
            except Exception as e:
                if log:
                    logger.error(f'[MDD][DEBUG] Erro ao processar item {idx}: {e}')
                continue

        # Verificação final de conexão
        if not validar_conexao_driver(driver, contexto="MDD_FIM"):
            if log:
                logger.error('[MDD][ERRO_FATAL] Driver em estado inválido ao finalizar busca de mandado')
            return None, None

        return None, None
    except Exception as e:
        if log:
            logger.error(f'[MDD][ERRO] Falha ao buscar último mandado: {e}')
        return None, None


def fluxo_mandados_outros(driver: WebDriver, log: bool = True) -> None:
    """
    Processa o fluxo de mandados não-Argos (Oficial de Justiça).
    1. Verifica se é certidão de oficial através do cabeçalho
    2. Extrai e analisa o texto da certidão
    3. Verifica padrões de mandado positivo/negativo
    4. Cria GIGS ou executa atos conforme resultado
    """
    try:
        # Usa aguardar_e_clicar mais robusto ao invés de find_element direto
        cabecalho = aguardar_e_clicar(driver, ".cabecalho-conteudo .mat-card-title", timeout=5, retornar_elemento=True)
        if not cabecalho:
            if log:
                logger.warning('[MANDADOS][OUTROS][ALERTA] Cabeçalho não encontrado. Tentando fallback.')
            cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")

        titulo_documento = cabecalho.text.lower()
        if log:
            logger.info(f"[MANDADOS][OUTROS] Cabeçalho detectado: {cabecalho.text}")

        eh_certidao_oficial = any(p in titulo_documento for p in [
            "certidão de oficial",
            "certidão de oficial de justiça"
        ])

        if not eh_certidao_oficial:
            return

    except Exception as e:
        if log:
            logger.error(f"[MANDADOS][OUTROS][ERRO] Erro ao verificar cabeçalho: {e}. Criando GIGS fallback.")
        # REMOVIDO: GIGS 0/PZ MDD considerado inútil

        # Fechamento simples sem verificações excessivas (igual ao ARGOS)
        return

    def analise_padrao(texto):
        # Diagnostic: confirmar entrada em analise_padrao
        logger.info('[MANDADOS][OUTROS] ENTER analise_padrao()')
        # Normalizar texto removendo acentos para facilitar matching
        try:
            texto_norm = remover_acentos(texto)
        except Exception as e:
            logger.info(f'[MANDADOS][OUTROS] analise_padrao: falha na normalizacao: {e}')
            texto_norm = texto
        texto_lower = texto_norm.lower()
        if log:
            logger.info(f"[MANDADOS][OUTROS] Texto (normalizado) para análise (len={len(texto_lower)}):\n{texto_lower[:800]}\n---Fim do documento---")

        padrao_positivo = any(p in texto_lower for p in [
            "citei",
            "intimei",
            "recebeu o mandado",
            "de tudo ficou ciente"
            "procedi à intimação",
            "procedi à citação",
            "procedi à entrega do mandado",
            "procedi à penhora",
            "penhorei"

        ])
        padrao_negativo = any(p in texto_lower for p in [
            "não localizado",
            "resultado negativo",
            "diligencias negativas",
            "diligência negativa",
            "não encontrado",
            "deixei de citar",
            "deixei de efetuar",
            "deixei de comparacer",
            "deixei de intimar",
            "deixei de penhorar",
            "não logrei êxito",
            "desconhecido no local",
            "não foi possível efetuar"
            "parou de responder",
            "não foi possível localizar",
        ])

        padrao_cancelamento_total = any(p in texto_lower for p in [
            "ordem de cancelamento total",
        ])
        if padrao_cancelamento_total:
            return None

        if padrao_positivo:
            pass
        elif padrao_negativo:
            if log:
                logger.info("Padrão de mandado NEGATIVO encontrado no texto.")  # NOVA REGRA: localizar mandado anterior na timeline, extrair conteúdo e, se contiver 'penhora', chamar ato_meios
                logger.info('[MANDADOS][OUTROS] padrao_negativo detectado — invocando ultimo_mdd()')
                autor_ant, elemento_ant = ultimo_mdd(driver, log=log)
                if elemento_ant:
                    try:
                        link_ant = elemento_ant.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        # Comportamento idêntico ao p2b: abrir link, aguardar estabilização e chamar extrair_direto
                        try:
                            aguardar_e_clicar(driver, link_ant)
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", link_ant)
                            except Exception:
                                pass
                        # Usar WebDriverWait ao invés de time.sleep
                        from Fix.core import wait_for_page_load
                        wait_for_page_load(driver, timeout=5)
                        try:
                            texto_mandado_ant_result = extrair_direto(driver, timeout=10, debug=True, formatar=True)
                        except Exception:
                            texto_mandado_ant_result = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
                        texto_mandado_ant = texto_mandado_ant_result.get('conteudo', '') if texto_mandado_ant_result and texto_mandado_ant_result.get('sucesso') else None
                        if texto_mandado_ant and 'penhora' in texto_mandado_ant.lower():
                            if not ALLOW_MANDADO_ATOS:
                                logger.info('[MANDADOS][OUTROS] atos automáticos desabilitados (PJE_ALLOW_MANDADO_ATOS=0) — pulando ato_meios()')
                            else:
                                logger.info('[MANDADOS][OUTROS] Invocando ato_meios() (do mandado anterior)')
                                try:
                                    ato_meios(driver)
                                    logger.info('[MANDADOS][OUTROS] ato_meios() retornou')
                                except Exception as e:
                                    logger.error(f'[MANDADOS][OUTROS] erro em ato_meios(): {e}')
                    except Exception as e:
                        if log:
                            logger.error(f"Falha ao processar mandado anterior: {e}")
            # Verifica se contém "penhora de bens" no texto
            if "penhora de bens" in texto_lower:
                if not ALLOW_MANDADO_ATOS:
                    logger.info('[MANDADOS][OUTROS] atos automáticos desabilitados — pulando ato_meios() (penhora de bens)')
                else:
                    logger.info('[MANDADOS][OUTROS] Invocando ato_meios() (penhora de bens)')
                    try:
                        ato_meios(driver)
                        logger.info('[MANDADOS][OUTROS] ato_meios() retornou')
                    except Exception as e:
                        logger.error(f'[MANDADOS][OUTROS] erro em ato_meios(): {e}')
            elif "deixei de penhorar" in texto_lower:
                if not ALLOW_MANDADO_ATOS:
                    logger.info('[MANDADOS][OUTROS] atos automáticos desabilitados — pulando ato_meios() (deixei de penhorar)')
                else:
                    logger.info('[MANDADOS][OUTROS] Invocando ato_meios() (deixei de penhorar)')
                    try:
                        ato_meios(driver)
                        logger.info('[MANDADOS][OUTROS] ato_meios() retornou')
                    except Exception as e:
                        logger.error(f'[MANDADOS][OUTROS] erro em ato_meios(): {e}')
            else:
                # Busca último mandado na timeline
                autor, elemento = ultimo_mdd(driver, log=log)
                if autor:
                    if 'silas passos' in autor.lower():
                        if not ALLOW_MANDADO_ATOS:
                            logger.info('[MANDADOS][OUTROS] atos automáticos desabilitados — pulando ato_edital()')
                        else:
                            logger.info('[MANDADOS][OUTROS] Invocando ato_edital()')
                            try:
                                ato_edital(driver)
                                logger.info('[MANDADOS][OUTROS] ato_edital() retornou')
                            except Exception as e:
                                logger.error(f'[MANDADOS][OUTROS] erro em ato_edital(): {e}')
                    else:
                        pass
                else:
                    pass
        else:
            pass
    try:
        # ALWAYS emit a short diagnostic log before attempting extraction
        logger.info('[MANDADOS][OUTROS] Invocando extrair_direto() (debug ON para diagnóstico)')
        texto_result = extrair_direto(driver, timeout=10, debug=True, formatar=True)
        logger.info(f'[MANDADOS][OUTROS] extrair_direto returned (diagnostic): {bool(texto_result and texto_result.get("sucesso"))}')
    except Exception as e:
        logger.error(f'[MANDADOS][OUTROS] extrair_direto falhou: {e}')
        texto_result = None

    if not texto_result or not texto_result.get('sucesso'):
        if log:
            logger.info('[MANDADOS][OUTROS] extrair_direto não retornou conteúdo; usando extrair_documento() fallback')
        texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
        texto = texto_tuple[0] if texto_tuple and texto_tuple[0] else None
    else:
        texto = texto_result.get('conteudo', '')
    # Diagnostic: confirmar atribuição de texto
    logger.info(f'[MANDADOS][OUTROS] Texto atribuído len={len(texto) if texto else 0}')
    if not texto:
        if log:
            logger.error("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
    if log:
        logger.info(f"[MANDADOS][OUTROS] Texto extraído (primeiros 200 chars): {texto[:200].replace(chr(10),' ')}")
    logger.info('[MANDADOS][OUTROS] Chamando analise_padrao()')
    # Analisar o texto extraído e executar ações padrão (positivo/negativo/cancelamento)
    try:
        analise_padrao(texto)
        logger.info('[MANDADOS][OUTROS] analise_padrao returned')
    except Exception as e:
        if log:
            logger.error(f"[MANDADOS][OUTROS][ERRO] Falha na análise padrão: {e}")
    return
