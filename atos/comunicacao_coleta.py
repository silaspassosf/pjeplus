import re
from typing import Any
from Fix.core import safe_click_no_scroll
from Fix.browser_suporte import scroll_to_element_safe
from Fix import espera


def executar_coleta_conteudo(driver: Any, config_coleta: Any, debug: bool = False) -> bool:
    try:
        if isinstance(config_coleta, str):
            config = {'tipo': config_coleta}
        else:
            config = config_coleta or {}

        tipo_coleta = config.get('tipo', '')
        parametros = config.get('parametros', None)

        numero_processo = None
        try:
            from PEC.anexos import extrair_numero_processo_da_url
            numero_processo = extrair_numero_processo_da_url(driver)
            if not numero_processo:
                numero_processo = "PROCESSO_DESCONHECIDO"
        except Exception:
            numero_processo = "PROCESSO_DESCONHECIDO"

        sucesso_coleta = False
        if tipo_coleta and tipo_coleta.lower() in ('link_ato', 'link_ato_validacao', 'link_ato_timeline'):
            try:
                from Fix.variaveis import session_from_driver, PjeApiClient, obter_chave_ultimo_despacho_decisao_sentenca
                sess_tmp, trt_tmp = session_from_driver(driver)
                client_tmp = PjeApiClient(sess_tmp, trt_tmp)
                link_validacao, conteudo_condensado = obter_chave_ultimo_despacho_decisao_sentenca(
                    client_tmp, str(numero_processo), driver=driver, incluir_conteudo_condensado=True
                ) or (None, None)
            except Exception:
                link_validacao, conteudo_condensado = None, None

            if link_validacao:
                try:
                    if not str(link_validacao).lower().startswith('http'):
                        base = trt_tmp
                        if not base.startswith('http'):
                            base = 'https://' + base
                        link_validacao = f"{base}/pjekz/validacao/{link_validacao}?instancia=1"
                    from PEC.anexos import salvar_conteudo_clipboard
                    sucesso_coleta = salvar_conteudo_clipboard(conteudo=link_validacao, numero_processo=str(numero_processo), tipo_conteudo="link_ato_validacao", debug=debug)
                    if conteudo_condensado:
                        salvar_conteudo_clipboard(conteudo=conteudo_condensado, numero_processo=str(numero_processo), tipo_conteudo="conteudo_formatado", debug=debug)
                    return True
                except Exception:
                    sucesso_coleta = True

            try:
                from Prazo.p2b_documentos import _encontrar_documento_relevante
                from Fix.core import aguardar_renderizacao_nativa
                doc_encontrado, doc_link, doc_idx = _encontrar_documento_relevante(driver)
                if doc_link:
                    try:
                        scroll_to_element_safe(driver, doc_link)
                        safe_click_no_scroll(driver, doc_link)
                        aguardar_renderizacao_nativa(
                            driver,
                            'div[style="display: block;"] span, a[href*="validacao"], pje-documento-original, pje-visualizador-documento',
                            'aparecer',
                            3,
                        )
                    except Exception:
                        pass
                    link_validacao_dom = None
                    try:
                        for span in espera.elementos(driver, 'div[style="display: block;"] span', teto=1):
                            txt = getattr(span, 'text', '') or ''
                            if 'Número do documento:' in txt:
                                partes = txt.split('Número do documento:')
                                if len(partes) > 1:
                                    num = partes[1].strip()
                                    if num:
                                        link_validacao_dom = f'https://pje.trt2.jus.br/pjekz/validacao/{num}?instancia=1'
                                        break
                        if not link_validacao_dom:
                            for a_el in espera.elementos(driver, 'a[href*="validacao"]', teto=1):
                                href = a_el.get_attribute('href') if hasattr(a_el, 'get_attribute') else ''
                                if href and '/validacao/' in href:
                                    link_validacao_dom = href
                                    break
                    except Exception:
                        link_validacao_dom = None

                    if link_validacao_dom:
                        try:
                            from PEC.anexos import salvar_conteudo_clipboard
                            sucesso_coleta = salvar_conteudo_clipboard(conteudo=link_validacao_dom, numero_processo=str(numero_processo), tipo_conteudo="link_ato_validacao", debug=debug)
                            if sucesso_coleta:
                                return True
                        except Exception:
                            return True
                    else:
                        sucesso_coleta = False
                else:
                    sucesso_coleta = False
            except Exception:
                sucesso_coleta = False

        if not sucesso_coleta:
            try:
                from Fix.utils import executar_coleta_parametrizavel
                sucesso_coleta = executar_coleta_parametrizavel(driver, numero_processo, tipo_coleta, parametros, debug)
            except Exception:
                sucesso_coleta = False

        return bool(sucesso_coleta)
    except Exception:
        return False

