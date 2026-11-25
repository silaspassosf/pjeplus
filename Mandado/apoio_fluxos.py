"""Mandado - Apoio a Fluxos (Outros + Utilitarios)"""


import os
import re
from Fix.utils import remover_acentos
from typing import Optional, Any, List, Tuple, Dict

from Fix import espera

from Fix.abas import validar_conexao_driver
from Fix.browser_suporte import forcar_fechamento_abas_extras
from Fix.core import (
    _norm,
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
    baixarCP,
    contar_mandados_e_certidoes_oficial,
    extrair_id_processo,
    preencher_campo,
    safe_click_no_scroll,
)
from Fix.facade_publica import ElementoNaoEncontradoError
from Fix.extracao import extrair_direto, extrair_documento, criar_gigs, criar_lembrete_posit
from Fix.log import logger

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
from Fix import espera

# 0. Controle de GIGS por processo (evita duplicidade)

_GIGS_CRIADO_PARA_PROCESSO: set = set()


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


def lembrete_bloq(driver: Any, debug: bool = False) -> bool:
    """Cria GIGS de bloqueio com apenas observação 'BLOQUEIO - processar após IDPJ' (sem prazo ou responsável)."""
    try:
        return bool(criar_gigs(driver, '', '', 'BLOQUEIO - processar após IDPJ', log=debug))
    except Exception as e:
        logger.warning(f'[MANDADO][GIGS_BLOQ] Erro ao criar GIGS de bloqueio: {e}')
        return False


# 3. utils_sigilo.py — sigilo de certidao e anexos

_SEL_INDICADOR_SIGILO = (
    'a.tl-documento.is-sigiloso, '
    'i.tl-sigiloso, i.fa-wpexplorer.tl-sigiloso, '
    'button[name="Retirar sigilo"], button[aria-label*="Retirar sigilo" i], '
    'button[mattooltip*="Retirar sigilo" i]'
)


def _elemento_esta_sigiloso(elemento: Any, debug: bool = False) -> bool:
    """Detecta se um item da timeline ainda está marcado como sigiloso."""
    if not elemento:
        return False
    try:
        links = espera.elementos(elemento, 'a.tl-documento', teto=0.4)
        if links:
            for link in links:
                classes = (link.get_attribute('class') or '').lower()
                if debug:
                    logger.info(f"[SIGILO_DEBUG] Classes link documento: {classes}")
                if 'is-sigiloso' in classes:
                    return True
    except Exception:
        pass

    try:
        if hasattr(elemento, '_handle') and hasattr(elemento._handle, 'query_selector'):
            if elemento._handle.query_selector(_SEL_INDICADOR_SIGILO) is not None:
                return True
        elif hasattr(elemento, 'query_selector'):
            if elemento.query_selector(_SEL_INDICADOR_SIGILO) is not None:
                return True
        else:
            if espera.elementos(elemento, _SEL_INDICADOR_SIGILO, teto=0.25):
                return True
    except Exception:
        pass

    return False


def retirar_sigilo(elemento: Any, driver: Optional[Any] = None, debug: bool = False) -> bool:
    """Remove sigilo de um documento na timeline com verificação e retry."""
    if not elemento:
        return False

    if not driver:
        try:
            if hasattr(elemento, '_parent'):
                driver = elemento._parent
            else:
                return False
        except Exception:
            return False

    try:
        resumo_doc = ((getattr(elemento, 'text', '') or '').strip().splitlines() or [''])[0][:80]
    except Exception:
        resumo_doc = ''

    try:
        if not _elemento_esta_sigiloso(elemento, debug=debug):
            if debug:
                logger.info('[SIGILO_DEBUG] Documento sem sigilo → JÁ SEM SIGILO (%s)', resumo_doc)
            return True

        seletores = [
            'button[name="Retirar sigilo"]',
            'button[aria-label*="Retirar sigilo" i]',
            'button[mattooltip*="Retirar sigilo" i]',
            'pje-doc-sigiloso button',
            'pje-doc-sigiloso span button',
            'i.fa-wpexplorer.tl-sigiloso',
            'button i.fa-wpexplorer',
            'i.fa-wpexplorer',
            'button[name="Inserir sigilo"]',
        ]

        def _buscar_btn() -> Optional[Any]:
            for seletor in seletores:
                try:
                    candidato = espera.elemento(elemento, seletor, teto=0.4)
                    if candidato and getattr(candidato, 'is_displayed', lambda: True)():
                        return candidato
                except Exception:
                    continue
            return None

        for tentativa in range(1, 3):
            btn_sigilo = _buscar_btn()
            if not btn_sigilo:
                if not _elemento_esta_sigiloso(elemento, debug=debug):
                    return True
                logger.warning(
                    '[SIGILO] Botão de retirar sigilo não encontrado (tentativa %d/2): %s',
                    tentativa, resumo_doc,
                )
                espera.assentar(driver, 0.3)
                continue

            try:
                if tentativa == 1:
                    safe_click_no_scroll(driver, btn_sigilo)
                else:
                    btn_sigilo.click()
            except Exception:
                try:
                    if tentativa == 1:
                        btn_sigilo.click()
                    else:
                        safe_click_no_scroll(driver, btn_sigilo)
                except Exception as e_clk:
                    logger.warning(
                        '[SIGILO] Erro ao clicar botão de sigilo (tentativa %d/2) em "%s": %s',
                        tentativa, resumo_doc, e_clk,
                    )

            for _ in range(14):
                try:
                    if not _elemento_esta_sigiloso(elemento, debug=debug):
                        if debug:
                            logger.info('[SIGILO_DEBUG] ✅ Sigilo removido após clique (tentativa %d): %s', tentativa, resumo_doc)
                        return True
                except Exception:
                    pass
                espera.assentar(driver, 0.25)

            if tentativa == 1:
                logger.warning(
                    '[SIGILO] Sigilo ainda ativo após 1ª tentativa — retentando: %s',
                    resumo_doc,
                )

        logger.warning('[SIGILO] ❌ Sigilo permaneceu ativo após 2 tentativas: %s', resumo_doc)
        return False

    except Exception as e:
        logger.warning('[SIGILO] Erro geral ao retirar sigilo (%s): %s', resumo_doc, e)
        return False


def _extrair_id_processo_da_url(driver: Any) -> Optional[str]:
    """ID numérico do processo na URL atual do PJe (`/processo/{id}`)."""
    return extrair_id_processo(driver)


def _criar_api_client_local(driver: Any):
    """Cria PjeApiClient a partir do driver (lazy import)."""
    try:
        from Fix.variaveis import PjeApiClient, session_from_driver
        sess, trt_host = session_from_driver(driver)
        return PjeApiClient(sess, trt_host, grau=1)
    except Exception:
        return None


def _extrair_texto_pdf_bytes(pdf_bytes: bytes, log: bool = False) -> str:
    """Extrai texto completo de bytes de PDF com cascata de engines:"""
    if not pdf_bytes or not pdf_bytes.startswith(b'%PDF'):
        return ""

    import io

    try:
        import pdfplumber
        textos = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for pag in pdf.pages:
                t = pag.extract_text()
                if t:
                    textos.append(t)
        res = '\n'.join(textos).strip()
        if res:
            return res
    except Exception as e:
        if log:
            logger.debug('[PDF_EXTRACT] pdfplumber falhou/ausente: %s', e)

    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        textos = [page.get_text() or '' for page in doc]
        res = '\n'.join(textos).strip()
        if res:
            return res
    except Exception as e:
        if log:
            logger.debug('[PDF_EXTRACT] pymupdf falhou/ausente: %s', e)

    try:
        import pypdfium2
        pdf = pypdfium2.PdfDocument(pdf_bytes)
        textos = [page.get_textpage().get_text_range() or '' for page in pdf]
        res = '\n'.join(textos).strip()
        if res:
            return res
    except Exception as e:
        if log:
            logger.debug('[PDF_EXTRACT] pypdfium2 falhou/ausente: %s', e)

    return ""


def _extrair_texto_certidao_via_api(driver: Any, log: bool = True) -> Optional[str]:
    """Extrai o texto COMPLETO da certidão de devolução via API (todas as páginas)."""
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

        id_certidao = None
        candidatas = []
        for doc in timeline:
            if not isinstance(doc, dict):
                continue
            doc_id = str(doc.get('id') or doc.get('idUnicoDocumento') or '')
            if not doc_id:
                continue
            t = _norm(doc.get('tipo', '')) + ' ' + _norm(doc.get('titulo', ''))
            if 'certid' in t and 'devolu' in t:
                candidatas.append((doc_id, str(doc.get('data') or doc.get('dataInclusao') or '')[:19], str(doc.get('titulo') or '')[:60]))
                if id_certidao is None:
                    id_certidao = doc_id
                    if log:
                        logger.info('[CERTIDAO_API] Certidão encontrada: uid=%s', id_certidao)
        if log and len(candidatas) > 1:
            logger.warning('[CERTIDAO_API] %d certidões de devolução na timeline (usando a 1ª): %s', len(candidatas), candidatas[:5])

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

        texto_total = _extrair_texto_pdf_bytes(resp.content, log=log)
        if texto_total:
            if log:
                logger.info('[CERTIDAO_API] Texto extraído: %d chars', len(texto_total))
            try:
                import os as _os
                _dir = _os.path.join('logs_execucao', 'certidoes')
                _os.makedirs(_dir, exist_ok=True)
                with open(_os.path.join(_dir, f'{id_processo}_{id_certidao}.txt'), 'w', encoding='utf-8') as _f:
                    _f.write(texto_total)
            except Exception:
                pass
            return texto_total
        else:
            if log:
                logger.warning('[CERTIDAO_API] Não foi possível extrair texto do PDF')
            return None

    except Exception as e:
        if log:
            logger.error('[CERTIDAO_API] Erro: %s', e)
        return None


def _extrair_texto_documento_timeline_api(
    driver: Any,
    match_fn,
    log: bool = True,
    contexto: str = '',
    preferir_ultimo: bool = False,
) -> Optional[str]:
    """Localiza (via timeline API) o documento cujo tipo/título/descrição (já"""
    import io as _io
    import unicodedata

    id_processo = _extrair_id_processo_da_url(driver)
    if not id_processo:
        if log:
            logger.info(f'[MANDADOS][OUTROS][API]{contexto} id_processo não encontrado na URL')
        return None

    client = _criar_api_client_local(driver)
    if not client:
        if log:
            logger.info(f'[MANDADOS][OUTROS][API]{contexto} Falha ao criar API client')
        return None

    try:
        timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
        if not timeline:
            if log:
                logger.info(f'[MANDADOS][OUTROS][API]{contexto} Timeline vazia')
            return None

        id_doc = None
        candidatos = []
        for doc in timeline:
            if not isinstance(doc, dict):
                continue
            tipo_norm = _norm(doc.get('tipo', ''))
            titulo_norm = _norm(doc.get('titulo', ''))
            descricao_bruta = (
                doc.get('descricao') or doc.get('descricaoModelo')
                or doc.get('descricaoPeticao') or doc.get('nomeTipoProcessoDocumento') or ''
            )
            descricao_norm = _norm(descricao_bruta)
            if match_fn(tipo_norm, titulo_norm, descricao_norm):
                id_doc = str(doc.get('id') or doc.get('idDocumento') or '')
                if log:
                    logger.info(
                        f'[MANDADOS][OUTROS][API]{contexto} Documento localizado: id=%s tipo=%s titulo=%s desc=%s',
                        id_doc, doc.get('tipo'), doc.get('titulo'), descricao_bruta or None)
                candidatos.append((id_doc, doc))
                if not preferir_ultimo:
                    break

        if candidatos and preferir_ultimo:
            # último documento juntado), mas a ordem da lista não é contrato: escolher
            candidatos.sort(key=lambda par: str(
                par[1].get('dataJuntada') or par[1].get('dataCadastro')
                or par[1].get('data') or ''))
            id_doc, doc_escolhido = candidatos[-1]
            if log:
                logger.info(
                    f'[MANDADOS][OUTROS][API]{contexto} Documento mais recente escolhido: '
                    'id=%s (%d candidato(s), data=%s)',
                    id_doc, len(candidatos),
                    doc_escolhido.get('dataJuntada') or doc_escolhido.get('dataCadastro')
                    or doc_escolhido.get('data') or '?')

        if not id_doc:
            if log:
                logger.info(f'[MANDADOS][OUTROS][API]{contexto} Nenhum documento correspondente na timeline')
            return None

        url_pdf = client._url(f'/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo')
        resp = client.sess.get(url_pdf, timeout=60)
        if resp.status_code != 200:
            if log:
                logger.warning(f'[MANDADOS][OUTROS][API]{contexto} HTTP %s ao baixar PDF', resp.status_code)
            return None

        magic = resp.content[:5] if resp.content else b''
        if magic != b'%PDF-':
            if log:
                logger.warning(f'[MANDADOS][OUTROS][API]{contexto} Resposta não é PDF (magic=%r)', magic)
            return None

        texto_total = _extrair_texto_pdf_bytes(resp.content, log=log)
        if texto_total:
            if log:
                logger.info(f'[MANDADOS][OUTROS][API]{contexto} Texto extraído: %d chars', len(texto_total))
            return texto_total
        else:
            if log:
                logger.warning(f'[MANDADOS][OUTROS][API]{contexto} Falha ao extrair texto do PDF')
            return None

    except Exception as e:
        if log:
            logger.info(f'[MANDADOS][OUTROS][API]{contexto} Erro: {e}')
        return None


def _eh_certidao_oficial_justica(tipo_norm: str, titulo_norm: str, descricao_norm: str) -> bool:
    """Reconhece a Certidão de Oficial de Justiça pelo modelo do sistema."""
    from Fix.documentos_cp import _cp_eh_certidao_oj
    return _cp_eh_certidao_oj(
        f'{tipo_norm} {titulo_norm} {descricao_norm}'.strip()
    )


def _extrair_texto_certidao_oficial_via_api(driver: Any, log: bool = True) -> Optional[str]:
    """Extrai o texto da certidão de Oficial de Justiça (documento atual) via API."""
    return _extrair_texto_documento_timeline_api(
        driver,
        match_fn=_eh_certidao_oficial_justica,
        log=log,
        contexto='[CERTIDAO]',
        preferir_ultimo=True,
    )


def _localizar_texto_mandado_anterior_via_api(driver: Any, log: bool = True) -> Optional[str]:
    """Localiza e extrai o texto do mandado (tipo/título 'Mandado') mais recente
    na timeline via API — substitui a busca por ícone de gavel + autor no DOM."""
    return _extrair_texto_documento_timeline_api(
        driver,
        match_fn=lambda tipo, titulo, descricao: (
            ('mandado' in tipo or 'mandado' in titulo)
            and 'certidao' not in tipo and 'certidao' not in titulo
        ),
        log=log,
        contexto='[MANDADO_ANTERIOR]',
    )


def _localizar_mandado_anterior_timeline_api(driver: Any, log: bool = True) -> Optional[Dict[str, Any]]:
    """Localiza o documento do mandado anterior na timeline via API."""
    import unicodedata

    id_processo = _extrair_id_processo_da_url(driver)
    if not id_processo:
        if log:
            logger.info('[MANDADOS][OUTROS][API] id_processo não encontrado na URL')
        return None

    client = _criar_api_client_local(driver)
    if not client:
        if log:
            logger.info('[MANDADOS][OUTROS][API] Falha ao criar API client')
        return None

    try:
        timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
        if not timeline:
            if log:
                logger.info('[MANDADOS][OUTROS][API] Timeline vazia ao buscar mandado anterior')
            return None

        for doc in timeline:
            if not isinstance(doc, dict):
                continue
            tipo_norm = _norm(doc.get('tipo', ''))
            titulo_norm = _norm(doc.get('titulo', ''))
            desc_norm = _norm(doc.get('descricao', ''))
            if (
                ('mandado' in tipo_norm or 'mandado' in titulo_norm or 'mandado' in desc_norm)
                and 'certidao' not in tipo_norm
                and 'certidao' not in titulo_norm
                and 'certidao' not in desc_norm
            ):
                if log:
                    logger.info(
                        '[MANDADOS][OUTROS][API] Mandado anterior localizado na timeline: id=%s tipo=%s titulo=%s desc=%s',
                        doc.get('id'), doc.get('tipo'), doc.get('titulo'), doc.get('descricao')
                    )
                return doc

        return None
    except Exception as e:
        if log:
            logger.warning('[MANDADOS][OUTROS][API] Erro ao buscar mandado anterior na timeline: %s', e)
        return None


def _mandado_contem_penhora(doc_mandado: Dict[str, Any]) -> bool:
    """Verifica se tipo, título, descrição ou nome do mandado anterior contém 'penhora'."""
    if not isinstance(doc_mandado, dict):
        return False

    texto_combinado = " ".join([
        str(doc_mandado.get('tipo') or ''),
        str(doc_mandado.get('titulo') or ''),
        str(doc_mandado.get('descricao') or ''),
        str(doc_mandado.get('nome') or ''),
        str(doc_mandado.get('descricaoComplementar') or ''),
        str(doc_mandado.get('complemento') or ''),
    ])
    return 'penhor' in _norm(texto_combinado)


def _mandado_eh_pagamento(doc_mandado: Dict[str, Any]) -> bool:
    """Verifica se o mandado anterior é Mandado de Pagamento (falso positivo para 'penhora')."""
    if not isinstance(doc_mandado, dict):
        return False

    texto_combinado = " ".join([
        str(doc_mandado.get('tipo') or ''),
        str(doc_mandado.get('titulo') or ''),
        str(doc_mandado.get('descricao') or ''),
        str(doc_mandado.get('nome') or ''),
        str(doc_mandado.get('descricaoComplementar') or ''),
        str(doc_mandado.get('complemento') or ''),
    ])
    return 'pagamento' in _norm(texto_combinado)


def _verificar_mandado_anterior_pagamento_dom(driver: Any) -> bool:
    """Fallback no DOM: verifica se o mandado anterior na timeline é de pagamento."""
    try:
        if hasattr(driver, 'page') and driver.page:
            return bool(driver.page.evaluate("""() => {
                const links = document.querySelectorAll('a.tl-documento');
                for (let i = 0; i < links.length; i++) {
                    const txt = (links[i].innerText || '').toLowerCase();
                    if (txt.includes('mandado') && !txt.includes('certid')) {
                        return txt.includes('pagamento');
                    }
                }
                return false;
            }"""))
    except Exception:
        pass
    return False


def _verificar_mandado_anterior_penhora_dom(driver: Any) -> bool:
    """Fallback no DOM: varre os links tl-documento procurando mandado anterior com 'penhora'."""
    try:
        if hasattr(driver, 'page') and driver.page:
            return bool(driver.page.evaluate("""() => {
                const links = document.querySelectorAll('a.tl-documento');
                for (let i = 0; i < links.length; i++) {
                    const txt = (links[i].innerText || '').toLowerCase();
                    if (txt.includes('mandado') && !txt.includes('certid')) {
                        if (txt.includes('penhor')) return true;
                    }
                }
                return false;
            }"""))
    except Exception:
        pass
    return False


def _extrair_documentos_decisao_despacho_api(driver: Any, log: bool = True) -> List[Tuple[str, str, int]]:
	"""Extrai documentos de decisão/despacho via API (timeline → PDF → pdfplumber)."""
	import io as _io
	import unicodedata

	_TIPOS_RELEVANTES = re.compile(
		r'^(despacho|decis[aã]o|senten[cç]a|conclus[aã]o)',
		re.IGNORECASE,
	)

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

				texto_total = _extrair_texto_pdf_bytes(pdf_bytes, log=log)
				if texto_total:
					if log:
						logger.info(
							'[ARGOS_API] Documento tipo=%s extraído: %d chars',
							tipo_doc,
							len(texto_total),
						)
					resultados.append((texto_total, tipo_doc, idx_original))
				else:
					if log:
						logger.warning('[ARGOS_API] Não foi possível extrair texto do doc %s', id_doc)

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


def _identificar_uids_sigilosos_por_api(driver: Any, log: bool = False) -> Optional[List[str]]:
    """Consulta timeline via API e retorna UIDs de docs sigilosos."""
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

        docs = [item for item in timeline if item.get('idUnicoDocumento')]
        if not docs:
            return []

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
    documentos_sequenciais: List[Any], uid: str
) -> Optional[Any]:
    """Retorna o elemento de documentos_sequenciais cujo link contém o uid."""
    uid_norm = (uid or '').strip().lower()
    if not uid_norm:
        return None

    for elem in documentos_sequenciais:
        try:
            links = espera.elementos(elem, 'a[href]', teto=0.5)
            for link in links:
                href = (link.get_attribute('href') or '').lower()
                if uid_norm in href:
                    return elem
        except Exception:
            continue
    return None


def _baixar_texto_doc_api(client: Any, id_processo: str, doc: dict, log: bool = False) -> Optional[str]:
    """Baixa o PDF de um documento da timeline via API e extrai seu texto."""
    id_doc = str(doc.get('id') or doc.get('idDocumento') or '')
    if not id_doc or not hasattr(client, 'sess') or not hasattr(client, '_url'):
        return None
    try:
        url_conteudo = client._url(
            f'/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo'
        )
        resp = client.sess.get(url_conteudo, timeout=30)
        if resp.status_code != 200:
            return None
        pdf_bytes = resp.content
        if not pdf_bytes or not pdf_bytes.startswith(b'%PDF'):
            return None
        return _extrair_texto_pdf_bytes(pdf_bytes, log=log) or None
    except Exception:
        return None


def _elemento_contem_uid(elem: Any, uid: str) -> bool:
    """Verifica se o item da timeline no DOM corresponde ao `idUnicoDocumento` informado."""
    uid_norm = (uid or '').strip().lower()
    if not uid_norm:
        return False
    try:
        if uid_norm in (getattr(elem, 'text', '') or '').lower():
            return True
    except Exception:
        pass
    try:
        links = espera.elementos(elem, 'a[href]', teto=0.2)
        for link in links or []:
            if uid_norm in (link.get_attribute('href') or '').lower():
                return True
    except Exception:
        pass
    return False


def buscar_documentos_sequenciais_via_api(driver: Any, log: bool = True) -> tuple:
    """Identifica documentos do bloco ARGOS via API + DOM e retorna (elementos, uids_sigilosos)."""
    from .regras import casa_regra_argos

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

        def _eh_ato_api(doc: dict) -> bool:
            tipo_n = _norm(doc.get('tipo', ''))
            if tipo_n:
                return ('decis' in tipo_n or 'despach' in tipo_n) and 'certid' not in tipo_n and 'intimac' not in tipo_n
            titulo_n = _norm(doc.get('titulo', ''))
            return ('decis' in titulo_n or 'despach' in titulo_n) and 'certid' not in titulo_n and 'intimac' not in titulo_n

        # A timeline do PJe vem da mais recente para a mais antiga (idx=0 mais recente).
        # Ancorar na certidão de devolução mais recente e localizar a primeira
        # Decisão/Despacho anterior a ela cujo conteúdo bate com as regras Argos.
        idxs_cert_todos = []
        idxs_ato_todos = []
        for i, doc in enumerate(docs):
            t = _norm(doc.get('tipo', '')) + ' ' + _norm(doc.get('titulo', ''))
            if 'certid' in t and 'devolu' in t:
                idxs_cert_todos.append(i)
            elif _eh_ato_api(doc):
                idxs_ato_todos.append(i)

        if not idxs_cert_todos:
            if log:
                logger.info('[SEQUENCIAIS_API] Certidao de devolucao nao encontrada na API')
            return [], []

        idx_cert = None
        atos_apos_cert: List[int] = []
        for cand_cert in idxs_cert_todos:
            atos = [i for i in idxs_ato_todos if i > cand_cert]
            if atos:
                idx_cert = cand_cert
                atos_apos_cert = atos
                break

        if idx_cert is None or not atos_apos_cert:
            if log:
                logger.info('[SEQUENCIAIS_API] Decisao/Despacho anterior à certidao nao encontrada na API')
            return [], []

        # Localiza a primeira Decisão/Despacho anterior à certidão que bate com
        # as regras Argos — ela é a âncora real do bloco (atravessa atos intermediários).
        idx_decisao = None
        pos_ato_ancora = 0
        regra_ancora = None
        for pos, cand_ato in enumerate(atos_apos_cert[:5]):
            doc_ato = docs[cand_ato]
            texto_ato = _baixar_texto_doc_api(client, id_processo, doc_ato, log=False)
            if not texto_ato:
                continue
            regra = casa_regra_argos(doc_ato.get('tipo', ''), texto_ato)
            if regra:
                idx_decisao = cand_ato
                pos_ato_ancora = pos
                regra_ancora = regra
                break

        if idx_decisao is None:
            idx_decisao = atos_apos_cert[0]
            pos_ato_ancora = 0

        uid_ancora = str(docs[idx_decisao].get('idUnicoDocumento') or '')

        def _tem_sigilo_api(doc: dict) -> bool:
            return bool(
                doc.get('sigiloso') or doc.get('sigilo')
                or doc.get('isSigiloso') or doc.get('isSignificant')
            )

        if log:
            logger.info(
                '[SEQUENCIAIS_API] Bloco ancorado: certidao idx=%d (%d total) -> ato idx=%d (%s, uid=%s, regra=%s)',
                idx_cert, len(idxs_cert_todos), idx_decisao,
                docs[idx_decisao].get('tipo', '?'), uid_ancora, regra_ancora or 'fallback_primeiro_ato',
            )

        bloco_idx = [idx_cert] + list(range(idx_cert + 1, idx_decisao)) + [idx_decisao]
        uids_sigilosos: List[str] = [
            docs[i]['idUnicoDocumento'] for i in bloco_idx if _tem_sigilo_api(docs[i])
        ]
        if log and uids_sigilosos:
            logger.debug('[SEQUENCIAIS_API] %d uid(s) sigilosos no bloco', len(uids_sigilosos))

        espera.elemento(driver, 'li.tl-item-container', teto=5, visivel=False)

        elementos = espera.elementos(driver, 'li.tl-item-container', teto=5)
        if log:
            logger.debug('[SEQUENCIAIS_API] %d li.tl-item-container no DOM', len(elementos))
        if not elementos:
            return [], []

        textos_dom = [_norm(elem.text.strip()) for elem in elementos]
        idxs_cert_dom = []
        idxs_ato_dom = []
        for idx, t_dom in enumerate(textos_dom):
            if 'certidao de devolucao' in t_dom:
                idxs_cert_dom.append(idx)
            elif 'decisao(' in t_dom or 'despacho(' in t_dom:
                idxs_ato_dom.append(idx)

        if not idxs_cert_dom:
            if log:
                logger.info('[SEQUENCIAIS_API] DOM: Certidao de devolucao nao localizada')
            return [], []

        idx_cert_dom = None
        atos_dom_apos: List[int] = []
        for cand_cert in idxs_cert_dom:
            atos = [idx for idx in idxs_ato_dom if idx > cand_cert]
            if atos:
                idx_cert_dom = cand_cert
                atos_dom_apos = atos
                break

        if idx_cert_dom is None or not atos_dom_apos:
            if log:
                logger.info('[SEQUENCIAIS_API] DOM: Decisao/Despacho anterior à certidao nao localizada')
            return [], []

        # Mapeia a âncora real no DOM: 1) match direto por uid_ancora; 2) posição
        # ordinal equivalente; 3) fallback para o primeiro ato anterior à certidão.
        idx_decisao_dom = next(
            (idx for idx in atos_dom_apos if _elemento_contem_uid(elementos[idx], uid_ancora)),
            None,
        )
        if idx_decisao_dom is None:
            idx_decisao_dom = (
                atos_dom_apos[pos_ato_ancora]
                if pos_ato_ancora < len(atos_dom_apos)
                else atos_dom_apos[0]
            )

        if log:
            logger.info(
                '[SEQUENCIAIS_API] DOM: bloco ancorado certidao idx=%d (%d total) -> ato idx=%d (uid=%s)',
                idx_cert_dom, len(idxs_cert_dom), idx_decisao_dom, uid_ancora,
            )

        _TERMOS_MEIO_DOM = {
            'certidao_devolucao': ['certidao de devolucao'],
            'certidao_expedicao': ['certidao de expedicao'],
            'certidao_pesquisa':  ['certidao de pesquisa patrimonial'],
            'planilha':           ['planilha de atualizacao', 'planilha de calculo'],
            'ordem_pesquisa':     ['ordem de pesquisa'],
            'intimacao':          ['intimacao('],
        }

        resultado: List[Any] = [elementos[idx_cert_dom]]

        for idx in range(idx_cert_dom + 1, idx_decisao_dom):
            texto = textos_dom[idx]
            matched = False
            for nome, palavras in _TERMOS_MEIO_DOM.items():
                if any(palavra in texto for palavra in palavras):
                    resultado.append(elementos[idx])
                    matched = True
                    if log:
                        logger.debug('[SEQUENCIAIS_API] DOM: %s idx=%d', nome, idx)
                    break
            if matched:
                continue
            if ('decisao(' in texto or 'despacho(' in texto) and _elemento_esta_sigiloso(elementos[idx]):
                resultado.append(elementos[idx])

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


def _classificar_doc_argos(texto: str) -> str:
    t = _norm(texto or '')
    if 'certidao de devolucao' in t:
        return 'certidao_devolucao'
    if 'certidao de pesquisa patrimonial' in t:
        return 'certidao_pesquisa'
    if 'certidao de expedicao' in t:
        return 'certidao_expedicao'
    if 'planilha de atualizacao' in t or 'planilha de calculo' in t:
        return 'planilha'
    if 'ordem de pesquisa' in t:
        return 'ordem_pesquisa'
    if 'intimacao' in t:
        return 'intimacao'
    if 'decisao' in t:
        return 'decisao'
    if 'despacho' in t:
        return 'despacho'
    return 'documento'


def retirar_sigilo_fluxo_argos(driver: Any, documentos_sequenciais: List[Any], log: bool = True, debug: bool = False, uids_sigilosos_hint: Optional[List[str]] = None) -> dict:
    """FUNÇÃO ÚNICA PARA TODO O FLUXO DE REMOÇÃO DE SIGILO DO ARGOS"""
    from core.resultado_execucao import ResultadoExecucao
    if not documentos_sequenciais:
        return ResultadoExecucao(sucesso=False, status='FALHA', erro='nenhum_documento', detalhes={'etapa_erro': 'nenhum_documento'})

    resultado = {
        'sucesso': True,
        'certidao_devolucao': None,
        'demais_documentos': [],
        'total_processados': 0,
    }

    def _resumo(el: Any) -> str:
        try:
            return ((getattr(el, 'text', '') or '').strip().splitlines() or [''])[0][:70]
        except Exception:
            return ''

    certidao_encontrada = None
    for doc in documentos_sequenciais:
        try:
            if 'certidao de devolucao' in _norm(getattr(doc, 'text', '') or ''):
                certidao_encontrada = doc
                break
        except Exception:
            continue

    if not certidao_encontrada:
        resultado['certidao_devolucao'] = {'status': 'nao_encontrada'}
    else:
        if not _elemento_esta_sigiloso(certidao_encontrada, debug=debug):
            resultado['certidao_devolucao'] = {'status': 'ja_sem_sigilo'}
        elif retirar_sigilo(certidao_encontrada, driver, debug=debug):
            resultado['certidao_devolucao'] = {'status': 'removido'}
            resultado['total_processados'] += 1
            logger.info('[SIGILO_ARGOS] Sigilo removido (certidao_devolucao): %s', _resumo(certidao_encontrada))
        else:
            resultado['certidao_devolucao'] = {'status': 'erro'}
            resultado['sucesso'] = False
            logger.warning('[SIGILO_ARGOS] Falha ao remover sigilo (certidao_devolucao): %s', _resumo(certidao_encontrada))

    visitados_ids = {id(certidao_encontrada)} if certidao_encontrada is not None else set()
    demais_elementos: List[tuple[str, Any]] = []
    for elem in documentos_sequenciais:
        if id(elem) in visitados_ids:
            continue
        visitados_ids.add(id(elem))
        tipo_nome = _classificar_doc_argos(getattr(elem, 'text', '') or '')
        demais_elementos.append((tipo_nome, elem))

    for tipo_nome, elemento in demais_elementos:
        if not _elemento_esta_sigiloso(elemento, debug=debug):
            resultado['demais_documentos'].append({'tipo': tipo_nome, 'status': 'ja_sem_sigilo'})
        elif retirar_sigilo(elemento, driver, debug=debug):
            resultado['demais_documentos'].append({'tipo': tipo_nome, 'status': 'removido'})
            resultado['total_processados'] += 1
            logger.info('[SIGILO_ARGOS] Sigilo removido (%s): %s', tipo_nome, _resumo(elemento))
        else:
            resultado['demais_documentos'].append({'tipo': tipo_nome, 'status': 'erro'})
            resultado['sucesso'] = False
            logger.warning('[SIGILO_ARGOS] Falha ao remover sigilo (%s): %s', tipo_nome, _resumo(elemento))

    todos_bloco: List[tuple[str, Any]] = []
    if certidao_encontrada is not None:
        todos_bloco.append(('certidao_devolucao', certidao_encontrada))
    todos_bloco.extend(demais_elementos)

    remanescentes = []
    for tipo_nome, elemento in todos_bloco:
        if _elemento_esta_sigiloso(elemento, debug=debug):
            logger.warning('[SIGILO_ARGOS] Documento ainda sigiloso na verificação (%s) — retentando: %s', tipo_nome, _resumo(elemento))
            if retirar_sigilo(elemento, driver, debug=debug):
                resultado['total_processados'] += 1
                logger.info('[SIGILO_ARGOS] Sigilo removido na verificação (%s): %s', tipo_nome, _resumo(elemento))
            else:
                remanescentes.append((tipo_nome, _resumo(elemento)))
                resultado['sucesso'] = False

    if remanescentes:
        logger.warning('[SIGILO_ARGOS] %d documento(s) permaneceram sigilosos após verificação: %s', len(remanescentes), remanescentes)
    elif log:
        logger.info(
            '[SIGILO_ARGOS] Concluído: %d documento(s) tiveram sigilo removido (%d verificados no bloco)',
            resultado['total_processados'], len(todos_bloco),
        )
    return resultado


def retirar_sigilo_certidao_devolucao_primeiro(driver: Any, documentos_sequenciais: List[Any], log: bool = True) -> bool:
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna apenas status da certidão."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    cert_status = resultado.get('certidao_devolucao', {}).get('status', 'erro')
    return cert_status in ['removido', 'ja_sem_sigilo', 'nao_encontrada']


def retirar_sigilo_demais_documentos_especificos(driver, documentos_sequenciais, log=True):
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna lista de demais documentos."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    return resultado.get('demais_documentos', [])


def retirar_sigilo_documentos_especificos(driver, documentos_sequenciais, log=True):
    """FUNÇÃO EFICIENTE - Remove sigilo APENAS dos documentos específicos fornecidos:"""
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

    if log:
        for doc in documentos_processados:
            status_icon = "" if doc['status'] == 'sucesso' else "" if doc['status'] == 'erro' else ""

    return documentos_processados


def _allow_mandado_atos() -> bool:
    return os.environ.get('PJE_ALLOW_MANDADO_ATOS', '1').lower() in ('1', 'true', 'yes', 'y')

ALLOW_MANDADO_ATOS = _allow_mandado_atos()

PADRAO_CANCELAMENTO = (
    "ordem de cancelamento total",
)

PADRAO_POSITIVO = (
    "citei",
    "intimei",
    "recebeu o mandado",
    "ficou ciente",
    "de tudo ficou ciente",
    "onde citei",
    "onde intimei",
    "ocasiao em que citei",
    "ocasiao em que intimei",
    "ato continuo, citei",
    "ato continuo citei",
    "ato continuo, intimei",
    "ato continuo intimei",
    "ali, citei",
    "ali citei",
    "ali, intimei",
    "ali intimei",
    "procedi a intimacao",
    "procedi a citacao",
    "procedi a entrega do mandado",
    "procedi a penhora",
    "penhorei",
    "citacao positiva",
    "intimacao positiva",
    "dei o destinatario por",
    "dei a destinaria por",
    "realizei a citacao",
    "realizei a intimacao",
    "realizei a penhora",
    "realizei a entrega do mandado",
    "citando para comparecer",
    "intimando para comparecer",
    "citacao realizada",
    "intimacao realizada",
    "citacao efetivada",
    "intimacao efetivada",
)

PADRAO_HIPOTESE_NEGATIVA_PENHORA = (
    "deixei de proceder a penhora",
    "deixo de realizar a penhora",
    "penhora negativa",
    "nao encontrei bens",
    "padrao de vida",
    "padrao medio de vida",
    "padrao media de vida",
)

PADRAO_NEGATIVO = (
    "certidao negativa",
    "citacao negativa",
    "intimacao negativa",
    "nao localizado",
    "resultado negativo",
    "diligencias negativas",
    "diligencia negativa",
    "nao encontrado",
    "deixei de citar",
    "deixei de efetuar",
    "deixei de comparecer",
    "deixei de intimar",
    "deixei de penhorar",
    "deixo de realizar",
    "nao logrei exito",
    "desconhecido no local",
    "desconhecida no local",
    "nao esta instalada",
    "nao estava instalada",
    "nao foi possivel efetuar",
    "parou de responder",
    "nao foi possivel localizar",
) + PADRAO_HIPOTESE_NEGATIVA_PENHORA


def _normalizar_certidao(texto: Optional[str]) -> str:
    """Remove acentos, lowercase e colapsa espacos irregulares (quebras de"""
    if not texto:
        return ''
    try:
        base = remover_acentos(texto)
    except Exception:
        base = texto
    return re.sub(r'\s+', ' ', base.lower()).strip()


def ultimo_mdd(driver: Any, log: bool = True) -> Tuple[Optional[str], Optional[Any]]:
    """Busca o último mandado na timeline (item com texto começando por 'Mandado' e ícone de gavel) e retorna (nom..."""
    try:
        if not validar_conexao_driver(driver, contexto="MDD_INICIO"):
            if log:
                logger.error('[MDD][ERRO_FATAL] Driver em estado inválido ao buscar mandado')
            return None, None

        itens = espera.elementos(driver, 'li.tl-item-container', teto=5)

        if not itens:
            if log:
                logger.warning('[MDD][ALERTA] Nenhum item encontrado na timeline')
            return None, None

        for idx, item in enumerate(itens):
            try:
                if idx % 10 == 0 and idx > 0:
                    if not validar_conexao_driver(driver, contexto=f"MDD_LOOP_{idx}"):
                        if log:
                            logger.error(f'[MDD][ERRO_FATAL] Driver em estado inválido durante loop (item {idx})')
                        return None, None

                link_el = espera.elemento(item, 'a.tl-documento:not([target="_blank"])', teto=0.5)
                link = aguardar_e_clicar(driver, link_el, timeout=1) if link_el else None
                if not link:
                    continue

                doc_text = link.text.strip().lower()
                if doc_text.startswith('mandado'):
                    icones = espera.elementos(item, 'i.fa-gavel', teto=0.5)
                    if not icones:
                        continue
                    nome_autor = None
                    try:
                        assinatura = espera.elemento(item, '.assinatura, .autor, .assinante, .nome-assinatura', teto=0.5)
                        if assinatura:
                            nome_autor = assinatura.text.strip()
                    except Exception:
                        pass
                    if not nome_autor:
                        try:
                            spans = espera.elementos(item, 'span', teto=0.5)
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

        if not validar_conexao_driver(driver, contexto="MDD_FIM"):
            if log:
                logger.error('[MDD][ERRO_FATAL] Driver em estado inválido ao finalizar busca de mandado')
            return None, None

        return None, None
    except Exception as e:
        if log:
            logger.error(f'[MDD][ERRO] Falha ao buscar último mandado: {e}')
        return None, None


def _executar_acoes_padrao_negativo(driver: Any, texto_lower: str, log: bool = True) -> None:
    """Ações adicionais quando a certidão reconhece o padrão NEGATIVO."""
    logger.info("Padrão de mandado NEGATIVO encontrado no texto.")

    ato_meios_executado = False

    def _chamar_ato_meios(motivo: str) -> None:
        nonlocal ato_meios_executado
        if ato_meios_executado:
            if log:
                logger.info(f'[MANDADOS][OUTROS] ato_meios() já executado para esta certidão — pulando novo acionamento ({motivo})')
            return
        if not _allow_mandado_atos():
            logger.info(f'[MANDADOS][OUTROS] atos automáticos desabilitados (PJE_ALLOW_MANDADO_ATOS=0) — pulando ato_meios() ({motivo})')
            return
        aba_atual = driver.current_window_handle
        handles_antes = set(getattr(driver, 'window_handles', []))
        logger.info(f'[MANDADOS][OUTROS] Invocando ato_meios() ({motivo})')
        try:
            res = ato_meios(driver)
            sucesso = res[0] if isinstance(res, (tuple, list)) else bool(res)
            if sucesso:
                ato_meios_executado = True
                logger.info(f'[MANDADOS][OUTROS] ato_meios() executado com sucesso ({motivo})')
            else:
                logger.warning(f'[MANDADOS][OUTROS] ato_meios() retornou falha ({motivo})')
        except Exception as e:
            logger.error(f'[MANDADOS][OUTROS] erro em ato_meios() ({motivo}): {e}')
        finally:
            try:
                for h in list(getattr(driver, 'window_handles', [])):
                    if h not in handles_antes:
                        try:
                            driver.switch_to.window(h)
                            driver.close()
                        except Exception:
                            pass
                if aba_atual in getattr(driver, 'window_handles', []):
                    driver.switch_to.window(aba_atual)
            except Exception as e_aba:
                logger.error(f'[MANDADOS][OUTROS] Falha ao normalizar abas após ato_meios ({motivo}): {e_aba}')

    logger.info('[MANDADOS][OUTROS] padrao_negativo detectado — localizando mandado anterior via API timeline')
    doc_mandado_ant = _localizar_mandado_anterior_timeline_api(driver, log=log)

    if doc_mandado_ant and _mandado_eh_pagamento(doc_mandado_ant):
        desc_pag = doc_mandado_ant.get('titulo') or doc_mandado_ant.get('descricao') or doc_mandado_ant.get('tipo') or ''
        logger.info(
            '[MANDADOS][OUTROS] Mandado anterior é de PAGAMENTO (%s) — negativo sem ato_meios (apenas GIGS xs1)',
            desc_pag,
        )
        return
    if not doc_mandado_ant and _verificar_mandado_anterior_pagamento_dom(driver):
        logger.info('[MANDADOS][OUTROS] Mandado anterior é de PAGAMENTO (DOM) — negativo sem ato_meios (apenas GIGS xs1)')
        return

    frase_hipotese_negativa = next((p for p in PADRAO_HIPOTESE_NEGATIVA_PENHORA if p in texto_lower), None)
    if frase_hipotese_negativa:
        _chamar_ato_meios(f'hipótese negativa de penhora: "{frase_hipotese_negativa}"')

    if 'penhora' in texto_lower:
        _chamar_ato_meios('certidão negativa de mandado de penhora')

    if doc_mandado_ant and _mandado_contem_penhora(doc_mandado_ant):
        desc_info = doc_mandado_ant.get('descricao') or doc_mandado_ant.get('titulo') or doc_mandado_ant.get('tipo') or ''
        _chamar_ato_meios(f'descrição do mandado anterior contém penhora: "{desc_info}"')
    elif not doc_mandado_ant and _verificar_mandado_anterior_penhora_dom(driver):
        _chamar_ato_meios('descrição do mandado anterior contém penhora (detectado via DOM)')

    texto_mandado_ant = _localizar_texto_mandado_anterior_via_api(driver, log=log)

    if texto_mandado_ant and 'penhora' in texto_mandado_ant.lower():
        _chamar_ato_meios('do mandado anterior (conteúdo do PDF)')

    if "penhora de bens" in texto_lower:
        _chamar_ato_meios('penhora de bens')
    elif "deixei de penhorar" in texto_lower:
        _chamar_ato_meios('deixei de penhorar')


def _classificar_certidao_oficial(texto: str) -> Optional[str]:
    """Classifica o texto da certidão de Oficial de Justiça."""
    texto_lower = _normalizar_certidao(texto)

    if any(p in texto_lower for p in PADRAO_CANCELAMENTO):
        return 'cancelamento'
    if any(p in texto_lower for p in PADRAO_POSITIVO):
        return 'positivo'
    if any(p in texto_lower for p in PADRAO_NEGATIVO):
        return 'negativo'
    return None


def fluxo_mandados_outros(
    driver: Any, log: bool = True, com_texto: bool = False
) -> Optional[Any]:
    """Processa a certidão de Oficial de Justiça já aberta (fluxo Outros/não-Argos)."""
    texto = None
    try:
        texto = _extrair_texto_certidao_oficial_via_api(driver, log=log)
    except Exception as e:
        logger.info(f'[MANDADOS][OUTROS][API] Extração via API levantou exceção: {e}')

    if not texto:
        if log:
            logger.info('[MANDADOS][OUTROS] API sem resultado — usando extrair_direto() (DOM)')
        try:
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

    logger.info(f'[MANDADOS][OUTROS] Texto atribuído len={len(texto) if texto else 0}')
    if not texto:
        if log:
            logger.error("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return (None, '') if com_texto else None
    if log:
        logger.info(f"[MANDADOS][OUTROS] Texto extraído (primeiros 200 chars): {texto[:200].replace(chr(10),' ')}")

    regra = _classificar_certidao_oficial(texto)
    logger.info(f'[MANDADOS][OUTROS] Regra reconhecida: {regra or "nenhuma"}')

    # O ato_meios NAO roda mais aqui (ver docstring): a ordem correta e'
    texto_lower = _normalizar_certidao(texto) if regra == 'negativo' else ''

    return (regra, texto_lower) if com_texto else regra


def _criar_gigs_xs1_uma_vez(driver: Any, numero_processo: str, log: bool = True) -> None:
    """Cria a GIGS sem prazo (xs1) na aba /detalhe, uma única vez por processo."""

    if numero_processo in _GIGS_CRIADO_PARA_PROCESSO:
        if log:
            logger.info(f'[MANDADOS][OUTROS] GIGS já criado para #{numero_processo}. Pulando criação.')
        return
    try:
        url_atual = (getattr(driver, 'current_url', '') or '').lower()
        if 'acesso-negado' in url_atual or 'login' in url_atual:
            if log:
                logger.warning(f'[MANDADOS][OUTROS] URL inválida antes de criar GIGS ({url_atual[:80]}) — tentando recuperar sessão...')
            from Mandado.entrada_api import _recuperar_sessao
            if _recuperar_sessao(driver):
                from Fix.variaveis import url_processo_detalhe
                from Fix.core import wait_for_page_load
                driver.get(url_processo_detalhe(numero_processo))
                wait_for_page_load(driver, timeout=10)

        ok = bool(criar_gigs(driver, dias_uteis="1", responsavel="", observacao="xs1", log=log))
        if ok:
            _GIGS_CRIADO_PARA_PROCESSO.add(numero_processo)
            if log:
                logger.info(f'[MANDADOS][OUTROS] GIGS xs1 criado com sucesso para #{numero_processo}')
        else:
            if log:
                logger.warning(f'[MANDADOS][OUTROS] criar_gigs xs1 retornou False para #{numero_processo}')
    except Exception as e:
        if log:
            logger.error(f'[MANDADOS][OUTROS] Falha ao criar GIGS xs1 para #{numero_processo}: {e}')


def _apagar_mandado_do_escaninho(
    driver: Any,
    numero_processo: str,
    escaninho_handle: str,
    log: bool = True,
) -> bool:
    """Fecha a aba /detalhe e remove o mandado da lista do escaninho."""
    if getattr(driver, 'current_window_handle', None) != escaninho_handle:
        try:
            driver.close()
        except Exception:
            pass

    handles_restantes = list(getattr(driver, 'window_handles', []))
    if escaninho_handle in handles_restantes:
        driver.switch_to.window(escaninho_handle)
    elif handles_restantes:
        driver.switch_to.window(handles_restantes[0])
        from Fix.variaveis import url_escaninho
        if "escaninho/documentos-internos" not in (getattr(driver, 'current_url', '') or ''):
            try:
                driver.get(url_escaninho)
                wait_for_page_load(driver, timeout=10)
                from Mandado.entrada_api import ativar_filtro_mandados_devolvidos
                ativar_filtro_mandados_devolvidos(driver)
            except Exception:
                pass

    url_esc = (getattr(driver, 'current_url', '') or '').lower()
    if 'acesso-negado' in url_esc or 'login' in url_esc:
        if log:
            logger.warning(f'[MANDADOS][OUTROS] Escaninho em URL inválida ({url_esc[:80]}) — recuperando sessão...')
        from Mandado.entrada_api import _recuperar_sessao
        if _recuperar_sessao(driver):
            from Fix.variaveis import url_escaninho
            from Fix.core import wait_for_page_load
            from Mandado.fluxo_ui import ativar_filtro_mandados_devolvidos
            try:
                driver.get(url_escaninho)
                wait_for_page_load(driver, timeout=10)
                ativar_filtro_mandados_devolvidos(driver)
            except Exception:
                pass

    try:
        lixeira_xpath = (
            f"//tr[contains(., '{numero_processo}')]"
            "//button[@aria-label='Remover documento marcados' or @mattooltip='Remover documento' "
            "or contains(@aria-label, 'Remover documento') or contains(@aria-label, 'Remover')]"
        )
        lixeiras = espera.elementos(driver, lixeira_xpath, teto=3)
        if not lixeiras:
            lixeiras = espera.elementos(
                driver,
                f"//table//tr[contains(., '{numero_processo}')]//button[contains(@aria-label, 'Remover') or contains(@mattooltip, 'Remover')]",
                teto=2
            )

        if not lixeiras:
            if log:
                logger.warning(f'[MANDADOS][OUTROS] Lixeira não encontrada no escaninho para #{numero_processo}')
            return False

        safe_click_no_scroll(driver, lixeiras[0])
        if log:
            logger.info(f'[MANDADOS][OUTROS] Lixeira clicada para #{numero_processo}')

        aguardar_renderizacao_nativa(driver, 'mat-dialog-container, .cdk-overlay-pane', modo='aparecer', timeout=3)
        botoes_confirmacao = espera.elementos(
            driver, "//mat-dialog-container//button[contains(., 'Sim') or contains(., 'Confirmar') or contains(., 'Remover')] | //button[contains(., 'Sim') or contains(., 'Confirmar') or contains(., 'Remover')]", teto=2
        )
        for btn in botoes_confirmacao:
            if getattr(btn, 'is_displayed', lambda: True)():
                safe_click_no_scroll(driver, btn)
                if log:
                    logger.info(f'[MANDADOS][OUTROS] Remoção confirmada para #{numero_processo}')
                break

        aguardar_renderizacao_nativa(driver, 'mat-dialog-container, .cdk-overlay-pane', modo='sumir', timeout=3)
        return True
    except Exception as e:
        if log:
            logger.error(f'[MANDADOS][OUTROS] Falha ao apagar #{numero_processo} do escaninho: {e}')
        return False


def arquivar_mandado_outros_reconhecido(
    driver: Any,
    numero_processo: str,
    escaninho_handle: str,
    log: bool = True,
    ao_meios_texto: Optional[str] = None,
) -> bool:
    """Ação padrão para QUALQUER regra reconhecida no fluxo Outros (cancelamento,"""
    _criar_gigs_xs1_uma_vez(driver, numero_processo, log)

    if ao_meios_texto:
        try:
            _executar_acoes_padrao_negativo(driver, ao_meios_texto, log=log)
        except Exception as e:
            logger.error(f"[MANDADOS][OUTROS][ERRO] Falha ao executar ações do padrão negativo: {e}")

    return _apagar_mandado_do_escaninho(driver, numero_processo, escaninho_handle, log)


def arquivar_mandado_positivo_reconhecido(
    driver: Any,
    numero_processo: str,
    escaninho_handle: str,
    log: bool = True,
) -> bool:
    """Ação do fluxo POSITIVO (Outros): GIGS xs1 + GIGS sem prazo (dados do mandado) + apagar do escaninho."""
    _criar_gigs_xs1_uma_vez(driver, numero_processo, log)

    nome = None
    try:
        texto = _extrair_texto_certidao_oficial_via_api(driver, log=log)
        nome = _extrair_nome_destinatario_certidao(texto) if texto else None
    except Exception as e:
        if log:
            logger.error(f'[MANDADOS][OUTROS][POSITIVO] Falha ao extrair destinatário da certidão de #{numero_processo}: {e}')

    conteudo_gigs = f'Mandado positivo ({nome}) - já alterado endereço na autuação.' if nome else 'Mandado positivo - já alterado endereço na autuação.'
    if log:
        if nome:
            logger.info(f'[MANDADOS][OUTROS][POSITIVO] Destinatário identificado: {nome}')
        else:
            logger.warning(f'[MANDADOS][OUTROS][POSITIVO] Destinatário não identificado na certidão de #{numero_processo} — usando texto padrão.')

    try:
        if log:
            logger.info(f'[MANDADOS][OUTROS][POSITIVO] Registrando GIGS sem prazo com dados: "{conteudo_gigs}"')
        gigs_ok = bool(criar_gigs(driver, "", "", conteudo_gigs, log=log))
        if gigs_ok:
            if log:
                logger.info(f'[MANDADOS][OUTROS][POSITIVO] GIGS sem prazo criado com sucesso para #{numero_processo}')
        else:
            if log:
                logger.warning(f'[MANDADOS][OUTROS][POSITIVO] GIGS sem prazo retornou False para #{numero_processo}')
    except Exception as e:
        if log:
            logger.error(f'[MANDADOS][OUTROS][POSITIVO] Erro ao registrar GIGS sem prazo para #{numero_processo}: {e}')

    return _apagar_mandado_do_escaninho(driver, numero_processo, escaninho_handle, log)


def _extrair_nome_destinatario_certidao(texto: Optional[str]) -> Optional[str]:
    """Extrai o nome do destinatário da certidão de Oficial de Justiça."""
    if not texto:
        return None
    m = re.search(r'DESTINAT[ÁA]RIO\s*:?\s*([^\n]+)', texto, re.IGNORECASE)
    if not m:
        return None
    nome = m.group(1).strip().strip(':').strip()
    nome = nome.rstrip('.,;')
    return nome.strip() or None


def _montar_conteudo_lembrete_mdd(existente: Optional[str], novo_nome: str) -> str:
    """Monta o conteúdo do lembrete 'mdd positivo'."""
    sufixo = ' - já alterado endereço na autuação.'
    nome = (novo_nome or '').strip()
    if not nome:
        return f'Mandado positivo{sufixo}'

    atual = (existente or '').strip()
    if not atual:
        return f'Mandado positivo ({nome}){sufixo}'

    padrao_sufixo = re.compile(
        r'\s*-\s*j[aá] alterado endere[cç]o na autua[cç][aã]o\.?\s*$',
        re.IGNORECASE,
    )
    corpo = padrao_sufixo.sub('', atual).strip(' ,-')
    corpo = re.sub(r'^\s*mandado\s+positivo\s*\(?', '', corpo, flags=re.IGNORECASE)
    corpo = re.sub(r'\)?\s*$', '', corpo)
    partes = [
        p.strip()
        for p in corpo.split(',')
        if p.strip() and re.search(r'[A-Za-zÀ-ÿ]', p)
    ]

    chave_novo = _normalizar_certidao(nome)
    if not any(_normalizar_certidao(p) == chave_novo for p in partes):
        partes.append(nome)

    if not partes:
        return f'Mandado positivo ({nome}){sufixo}'
    return f"Mandado positivo ({', '.join(partes)}){sufixo}"


def _localizar_lembrete_mdd(driver: Any, log: bool = True) -> Optional[Any]:
    """Localiza o painel do lembrete 'mdd positivo' no pje-visualizador-post-its."""
    try:
        espera.ate_aparecer(driver, 'pje-visualizador-post-its .post-it-set', teto=3)
    except Exception:
        pass

    try:
        paineis = espera.elementos(
            driver,
            'pje-visualizador-post-its .post-it-set mat-expansion-panel, .post-it-set mat-expansion-panel',
            teto=2,
        )
    except Exception as e:
        if log:
            logger.warning(f'[LEMBRETE][MDD] Falha ao listar lembretes: {e}')
        return None

    alvo = _normalizar_certidao('mdd positivo')
    for painel in paineis:
        try:
            titulo_el = espera.elemento(painel, '.post-it-titulo', teto=0.5)
            if titulo_el and _normalizar_certidao(titulo_el.text.strip()) == alvo:
                return painel
        except Exception:
            continue
    return None


def _editar_lembrete_conteudo(driver: Any, painel: Any, novo_conteudo: str, log: bool = True) -> bool:
    """Edita o conteúdo de um lembrete existente (mesmo modal do criar)."""
    try:
        btn_editar = None
        try:
            btn_editar = espera.elemento(painel, 'button[aria-label="Editar Lembrete"]', teto=0.5)
        except Exception:
            pass
        if not btn_editar:
            try:
                cabecalho = espera.elemento(painel, 'mat-expansion-panel-header', teto=0.5)
                if cabecalho:
                    safe_click_no_scroll(driver, cabecalho)
                    espera.assentar(driver, 0.5)
                    btn_editar = espera.elemento(painel, 'button[aria-label="Editar Lembrete"]', teto=0.5)
            except Exception:
                if log:
                    logger.warning('[LEMBRETE][MDD] Botão "Editar Lembrete" não encontrado no painel.')
                return False
        if btn_editar:
            safe_click_no_scroll(driver, btn_editar)
        else:
            return False
    except Exception as e:
        if log:
            logger.warning(f'[LEMBRETE][MDD] Não foi possível abrir a edição do lembrete: {e}')
        return False

    try:
        espera.ate_aparecer(driver, '#conteudoPostit', teto=5)
        preencher_campo(driver, '#conteudoPostit', novo_conteudo, log=log)
    except Exception as e:
        if log:
            logger.warning(f'[LEMBRETE][MDD] Falha ao preencher o conteúdo do lembrete: {e}')
        return False

    seletores_salvar = [
        'button[color="primary"]',
        '.mat-raised-button:not([disabled])',
        'button[type="submit"]',
    ]
    for seletor in seletores_salvar:
        try:
            if aguardar_e_clicar(driver, seletor, timeout=3, log=False):
                break
        except Exception:
            continue
    if not espera.ate_sumir(driver, '#conteudoPostit', teto=4):
        espera.assentar(driver, 0.8, motivo='[LEMBRETE][MDD] dialogo ainda aberto apos salvar')
    if log:
        logger.info(f'[LEMBRETE][MDD] Lembrete "mdd positivo" atualizado: {novo_conteudo}')
    return True


_CP_SAUDACAO_RE = re.compile(
    r'[oa]\s*\(?\s*a?\s*\)?\s*exm[oa]\s*\(?\s*a?\s*\)?\.?\s*juiz\s*\(?\s*a?\s*\)?\s*do\s*trabalho'
)


def _extrair_ementa_mandado(texto: str) -> str:
    normalizado = _normalizar_certidao(texto)
    match = _CP_SAUDACAO_RE.search(normalizado)
    return normalizado[:match.start()] if match else normalizado


def fluxo_mandados_cp(
    driver: Any,
    numero_processo: str,
    escaninho_handle: str,
    log: bool = True,
) -> Optional[str]:
    """Processa o Fluxo CP (processo com cabecalho 'CartPrecCiv') no ramo"""
    from atos.anexos.anexos_wrappers import anex_devcp

    logger.info(f'[MANDADOS][CP] === INICIO Fluxo CP === processo=#{numero_processo}')

    texto_mandado = _localizar_texto_mandado_anterior_via_api(driver, log=log)
    if not texto_mandado:
        logger.error(f'[MANDADOS][CP] #{numero_processo}: falha ao localizar texto do mandado via API — abortando')
        return None

    ementa = _extrair_ementa_mandado(texto_mandado)
    contem_penhora = 'penhora' in ementa
    logger.info(f'[MANDADOS][CP] #{numero_processo}: ementa contem "penhora"={contem_penhora}')

    def _incompleto(motivo: str) -> str:
        logger.info(f'[MANDADOS][CP] #{numero_processo}: fluxo incompleto ({motivo}) — GIGS xs1 + apagar do escaninho')
        arquivar_mandado_outros_reconhecido(
            driver, numero_processo=numero_processo, escaninho_handle=escaninho_handle, log=log,
        )
        return 'incompleto'

    if contem_penhora:
        texto_lower = _normalizar_certidao(texto_mandado)
        bate_negativo = any(p in texto_lower for p in PADRAO_NEGATIVO)
        logger.info(f'[MANDADOS][CP] #{numero_processo}: padrao NEGATIVO reconhecido no mandado={bate_negativo}')
        if not bate_negativo:
            return _incompleto('penhora positiva — sem padrao negativo')

    try:
        qtd_mandados, qtd_certidoes = contar_mandados_e_certidoes_oficial(
            driver, log=log, numero_processo=numero_processo
        )
    except ElementoNaoEncontradoError as e:
        logger.error(f'[MANDADOS][CP] #{numero_processo}: falha ao contar mandados/certidoes: {e}')
        return None

    logger.info(f'[MANDADOS][CP] #{numero_processo}: mandados={qtd_mandados} certidoes_oficial={qtd_certidoes}')
    if qtd_mandados != qtd_certidoes:
        return _incompleto('contagem mandados/certidoes divergente')

    logger.info(f'[MANDADOS][CP] #{numero_processo}: fluxo completo — baixarCP + juntada devcp + mov arquivar')
    try:
        if not baixarCP(driver, log=log, numero_processo=numero_processo):
            logger.error(f'[MANDADOS][CP] #{numero_processo}: baixarCP() retornou False — abortando')
            return None
    except ElementoNaoEncontradoError as e:
        logger.error(f'[MANDADOS][CP] #{numero_processo}: baixarCP() falhou: {e}')
        return None

    aba_processo = driver.current_window_handle
    sucesso_juntada = anex_devcp(driver, numero_processo=numero_processo, debug=log)
    try:
        forcar_fechamento_abas_extras(driver, aba_processo)
    except Exception as e_aba:
        logger.error(f'[MANDADOS][CP] #{numero_processo}: falha ao normalizar abas após anex_devcp(): {e_aba}')

    if not sucesso_juntada:
        logger.error(f'[MANDADOS][CP] #{numero_processo}: anex_devcp() falhou')
        return None

    if not mov_arquivar(driver):
        logger.error(f'[MANDADOS][CP] #{numero_processo}: mov_arquivar() falhou')
        return None

    logger.info(f'[MANDADOS][CP] #{numero_processo}: fluxo completo concluido com sucesso')
    return 'completo'
