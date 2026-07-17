import logging

logger = logging.getLogger(__name__)

"""
SISB Minutas - Relatorio
"""


def _gerar_relatorio_minuta(driver, numero_processo):
    """Helper para gerar relatorio da minuta."""
    try:
        from ..core import coletar_dados_minuta_sisbajud
        dados_relatorio = coletar_dados_minuta_sisbajud(driver)
        if dados_relatorio:
            try:
                from PEC.anexos import salvar_conteudo_clipboard

                sucesso = salvar_conteudo_clipboard(
                    conteudo=dados_relatorio,
                    numero_processo=numero_processo or "SISBAJUD",
                    tipo_conteudo="sisbajud_minuta",
                    debug=True
                )

                _ = sucesso

                protocolo = None
                try:
                    url = driver.current_url
                    import re
                    match = re.search(r'/(\d{10,})/', url)
                    if match:
                        protocolo = match.group(1)
                except Exception:
                    pass

                return {
                    'protocolo': protocolo,
                    'tipo': 'bloqueio',
                    'repeticao': 'sim',
                    'conteudo': dados_relatorio
                }
            except Exception as e:
                logger.error(f'[SISBAJUD]  Erro ao salvar relatorio: {e}')
                return None
        return None

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao gerar relatorio: {e}')
        return None