import time
import re
from typing import Any


def executar_coleta_conteudo(driver, config_coleta, debug=False) -> bool:
    """Executa a coleta de conteúdo parametrizável usada pela comunicação orquestrada.
    Retorna True se a coleta teve sucesso (ou link obtido), False caso contrário.
    """
    try:
        # Normaliza config para dict
        if isinstance(config_coleta, str):
            config = {'tipo': config_coleta}
        else:
            config = config_coleta or {}

        tipo_coleta = config.get('tipo', '')
        parametros = config.get('parametros', None)

        # Extrair número do processo via PEC.anexos se disponível
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
            # Tenta API via Fix.variaveis
            try:
                from Fix.variaveis import session_from_driver, PjeApiClient, obter_chave_ultimo_despacho_decisao_sentenca
                sess_tmp, trt_tmp = session_from_driver(driver)
                client_tmp = PjeApiClient(sess_tmp, trt_tmp)
                link_validacao = obter_chave_ultimo_despacho_decisao_sentenca(client_tmp, str(numero_processo), driver=driver)
            except Exception:
                link_validacao = None

            if link_validacao:
                try:
                    if not str(link_validacao).lower().startswith('http'):
                        base = trt_tmp
                        if not base.startswith('http'):
                            base = 'https://' + base
                        link_validacao = f"{base}/pjekz/validacao/{link_validacao}?instancia=1"
                    from PEC.anexos import salvar_conteudo_clipboard
                    sucesso_coleta = salvar_conteudo_clipboard(conteudo=link_validacao, numero_processo=str(numero_processo), tipo_conteudo=f"link_ato_validacao", debug=debug)
                    if sucesso_coleta:
                        return True
                    else:
                        return True
                except Exception:
                    sucesso_coleta = True

            # Fallback DOM/timeline
            try:
                from Prazo.p2b_fluxo_helpers import _encontrar_documento_relevante
                doc_encontrado, doc_link, doc_idx = _encontrar_documento_relevante(driver)
                if doc_link:
                    try:
                        driver.execute_script('arguments[0].scrollIntoView(true);', doc_link)
                        time.sleep(0.5)
                        driver.execute_script('arguments[0].click();', doc_link)
                        time.sleep(1)
                    except Exception:
                        pass
                    try:
                        link_validacao_dom = driver.execute_script("""
                            var spans = document.querySelectorAll('div[style="display: block;"] span');
                            for (var i = 0; i < spans.length; i++) {
                                var text = spans[i].textContent.trim();
                                if (text.includes('Número do documento:')) {
                                    var numero = text.split('Número do documento:')[1].trim();
                                    if (numero) {
                                        return 'https://pje.trt2.jus.br/pjekz/validacao/' + numero + '?instancia=1';
                                    }
                                }
                            }
                            var links = document.querySelectorAll('a[href*="validacao"]');
                            for (var i = 0; i < links.length; i++) {
                                var href = links[i].getAttribute('href');
                                if (href && href.includes('/validacao/')) {
                                    return href;
                                }
                            }
                            return null;
                        """)
                    except Exception:
                        link_validacao_dom = None

                    if link_validacao_dom:
                        try:
                            from PEC.anexos import salvar_conteudo_clipboard
                            sucesso_coleta = salvar_conteudo_clipboard(conteudo=link_validacao_dom, numero_processo=str(numero_processo), tipo_conteudo=f"link_ato_validacao", debug=debug)
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
