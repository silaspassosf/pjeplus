from Fix.log import logger
from Fix.extracao_documento import extrair_documento

try:
    from Fix.gigs import criar_gigs
except Exception:
    criar_gigs = None


def analise_argos(driver):
    # Fluxo robusto para análise de mandados do tipo Argos (Pesquisa Patrimonial).
    try:
        # Placeholder para lógica Argos adicional
        pass
    except Exception as e:
        logger.error(f'[ARGOS][ERRO] Falha na análise Argos: {e}')


def tratar_anexos_argos(driver, log=True):
    # Função placeholder, lógica removida conforme solicitado.
    pass


def analise_outros(driver):
    # Fluxo robusto para análise de mandados do tipo Outros (Oficial de Justiça).
    # - Extrai certidão do documento.
    # - Cria GIGS sempre como tipo 'prazo', 0 dias, nome 'Pz mdd'.
    texto = extrair_documento(driver, regras_analise=lambda texto: criar_gigs(driver, 0, 'Pz mdd'))
    if not texto:
        logger.error("[OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
    return texto