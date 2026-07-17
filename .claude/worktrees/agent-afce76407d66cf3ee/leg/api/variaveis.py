# Caminho para o geckodriver.exe (necessário para Fix/drivers/lifecycle.py)
import os
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'geckodriver.exe')
if not os.path.exists(GECKODRIVER_PATH):
    # Fallback: tenta no diretório pai
    GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), '..', 'geckodriver.exe')
# Re-exportações diretas — sem wrappers intermediários
from Fix.variaveis_client import PjeApiClient, session_from_driver
from Fix.variaveis_resolvers import (
    obter_codigo_validacao_documento,
    obter_peca_processual_da_timeline,
    resolver_variavel,
    get_all_variables,
    obter_chave_ultimo_despacho_decisao_sentenca,
)
from Fix.variaveis_helpers import (
    obter_gigs_com_fase,
    obter_texto_documento,
    buscar_atividade_gigs_por_observacao,
    obter_todas_atividades_gigs_com_observacao,
    padrao_liq,
    verificar_bndt,
)
