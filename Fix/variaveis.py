import logging
logger = logging.getLogger(__name__)

"""Fix.variaveis

Módulo auxiliar para resolver, via API PJe, as mesmas variáveis que a
extensão `gigs-plugin.js` expõe ao editor. O objetivo é permitir que
os scripts Python do projeto importem chamadas prontas para obter
valores (ex.: chave de validação de um documento, idUnicoDocumento,
partes do processo, valores de execução etc.) sem depender da
extensão no navegador.

IMPORTANTE:
- Estas chamadas assumem execução em ambiente já autenticado no PJe
    (sessão real com cookies válidos). Use `session_from_driver(driver)`
    ou construa um `requests.Session` com os cookies do navegador.

Chamadas / funções principais disponíveis neste módulo:

- `PjeApiClient(session, trt_host, grau=1)` : cliente leve para chamadas
    PJe. Métodos úteis:
    - `timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)`
    - `documento_por_id(id_processo, id_documento, ...)`
    - `processo_por_id(id_processo)`
    - `partes(id_processo)`
    - `calculos(id_processo)`
    - `pericias(id_processo)`
    - `execucao_gigs(id_processo)`
    - `debitos_trabalhistas_bndt(id_processo)` : obtém partes no BNDT

- `session_from_driver(driver, grau=1)` : helper que cria um
    `requests.Session` copiando cookies de um Selenium `WebDriver` e
    retornando também o `trt_host` (domínio PJe). Use quando estiver
    executando automação Selenium já logada.

- `obter_codigo_validacao_documento(client, id_processo, id_documento)` :
    replica a construção do plugin para a "chave de validação" do
    documento (mesmo algoritmo do `obterCodigoValidacaoDocumento` JS).

- `obter_peca_processual_da_timeline(client, id_processo, tipo_label, modo)` :
    busca na timeline do processo o documento do tipo (`tipo_label`, ex.:
    'Sentença','Despacho') e retorna conforme `modo` ('chave'|'id'|'anexos'|'raw').

- `resolver_variavel(client, id_processo, variavel)` : recebe tokens no
    formato `"[maisPje:últimaSentença:chave]"` ou `'últimaSentença:chave'`
    e resolve para o valor correspondente (facilita porting direto das
    variáveis da extensão para chamadas Python).

- `get_all_variables(client, id_processo)` : resolve em lote o conjunto
    de variáveis mais comuns usadas pela extensão (ex.: exequente,
    executado, valorDivida, últimas peças do timeline com `:id/:chave/:anexos`,
    perito, telefone do exequente, etc.) e retorna um dicionário.

- `verificar_bndt(client, id_processo)` : verifica se há partes cadastradas
    no BNDT e retorna informações formatadas (baseado em verificarBNDT do a.py).

Exemplo mínimo de uso (Selenium + ambiente autenticado):

```py
from Fix.variaveis import session_from_driver, PjeApiClient, resolver_variavel, verificar_bndt

sess, trt = session_from_driver(driver)
client = PjeApiClient(sess, trt)

chave = resolver_variavel(client, id_processo='1234567-89.2024.5.01.0000', variavel='[maisPje:últimaSentença:chave]')

# Verificar BNDT
resultado_bndt = verificar_bndt(client, '1234567')
if resultado_bndt['tem_partes']:
    logger.info(f"Encontradas {resultado_bndt['quantidade']} partes no BNDT")
    for nome in resultado_bndt['partes']:
        logger.info(f"  - {nome}")
```

Integração: importe as funções que precisar em outros scripts do
projeto (por exemplo `from Fix.variaveis import resolver_variavel, get_all_variables`).
"""
from typing import Optional, Any, Dict, List, Tuple
import requests
import re
import html as _html
from urllib.parse import urlparse
import os

# Caminho para o geckodriver.exe
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'geckodriver.exe')
if not os.path.exists(GECKODRIVER_PATH):
    # Fallback: tenta no diretório pai
    GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), '..', 'geckodriver.exe')

class PjeApiClient:
    """Wrapper para Fix.variaveis_client.PjeApiClient."""
    def __new__(cls, *args, **kwargs):
        from Fix.variaveis_client import PjeApiClient as _impl
        return _impl(*args, **kwargs)


def obter_gigs_com_fase(client: PjeApiClient, id_processo: str) -> Optional[Dict[str, Any]]:
    """Wrapper para Fix.variaveis_helpers.obter_gigs_com_fase."""
    from Fix.variaveis_helpers import obter_gigs_com_fase as _impl
    return _impl(client, id_processo)


def session_from_driver(driver, grau: int = 1) -> Tuple[requests.Session, str]:
    """Wrapper para Fix.variaveis_client.session_from_driver."""
    from Fix.variaveis_client import session_from_driver as _impl
    return _impl(driver, grau=grau)


def obter_codigo_validacao_documento(client: PjeApiClient, id_processo: str, id_documento: str) -> Optional[str]:
    """Wrapper para Fix.variaveis_resolvers.obter_codigo_validacao_documento."""
    from Fix.variaveis_resolvers import obter_codigo_validacao_documento as _impl
    return _impl(client, id_processo, id_documento)


def obter_peca_processual_da_timeline(client: PjeApiClient, id_processo: str, tipo_label: str, modo: str = 'chave', itens_timeline: Optional[List[Dict]] = None) -> Optional[str]:
    """Wrapper para Fix.variaveis_resolvers.obter_peca_processual_da_timeline."""
    from Fix.variaveis_resolvers import obter_peca_processual_da_timeline as _impl
    return _impl(client, id_processo, tipo_label, modo=modo, itens_timeline=itens_timeline)


def resolver_variavel(client: PjeApiClient, id_processo: str, variavel: str) -> Optional[str]:
    """Wrapper para Fix.variaveis_resolvers.resolver_variavel."""
    from Fix.variaveis_resolvers import resolver_variavel as _impl
    return _impl(client, id_processo, variavel)


def get_all_variables(client: PjeApiClient, id_processo: str) -> Dict[str, Optional[str]]:
    """Wrapper para Fix.variaveis_resolvers.get_all_variables."""
    from Fix.variaveis_resolvers import get_all_variables as _impl
    return _impl(client, id_processo)


def obter_chave_ultimo_despacho_decisao_sentenca(client: PjeApiClient, id_processo: str, tipos: Optional[List[str]] = None, itens_timeline: Optional[List[Dict]] = None) -> Optional[str]:
    """Wrapper para Fix.variaveis_resolvers.obter_chave_ultimo_despacho_decisao_sentenca."""
    from Fix.variaveis_resolvers import obter_chave_ultimo_despacho_decisao_sentenca as _impl
    return _impl(client, id_processo, tipos=tipos, itens_timeline=itens_timeline)


def obter_texto_documento(client: PjeApiClient, id_processo: str, id_documento: str) -> Optional[str]:
    """Wrapper para Fix.variaveis_helpers.obter_texto_documento."""
    from Fix.variaveis_helpers import obter_texto_documento as _impl
    return _impl(client, id_processo, id_documento)


def buscar_atividade_gigs_por_observacao(client: PjeApiClient, id_processo: str, observacao_patterns: List[str], prazo_aberto: bool = True) -> Optional[Dict[str, Any]]:
    """Wrapper para Fix.variaveis_helpers.buscar_atividade_gigs_por_observacao."""
    from Fix.variaveis_helpers import buscar_atividade_gigs_por_observacao as _impl
    return _impl(client, id_processo, observacao_patterns, prazo_aberto=prazo_aberto)


def obter_todas_atividades_gigs_com_observacao(client: PjeApiClient, id_processo: str, observacao_patterns: List[str], prazo_aberto: bool = True) -> List[Dict[str, Any]]:
    """Wrapper para Fix.variaveis_helpers.obter_todas_atividades_gigs_com_observacao."""
    from Fix.variaveis_helpers import obter_todas_atividades_gigs_com_observacao as _impl
    return _impl(client, id_processo, observacao_patterns, prazo_aberto=prazo_aberto)


def padrao_liq(client: PjeApiClient, id_processo: str, nome_perito: str = 'ROGERIO') -> Dict[str, bool]:
    """Wrapper para Fix.variaveis_helpers.padrao_liq."""
    from Fix.variaveis_helpers import padrao_liq as _impl
    return _impl(client, id_processo, nome_perito=nome_perito)


def verificar_bndt(client: PjeApiClient, id_processo: str) -> Dict[str, Any]:
    """Wrapper para Fix.variaveis_helpers.verificar_bndt."""
    from Fix.variaveis_helpers import verificar_bndt as _impl
    return _impl(client, id_processo)

# ==========================================
# EXEMPLO DE USO - CONSULTA BNDT
# ==========================================
"""
Exemplo de uso das funções BNDT:

# 1. Uso básico com Selenium WebDriver
from Fix.variaveis import session_from_driver, PjeApiClient, verificar_bndt

# Assumindo que você já tem um driver autenticado no PJe
sess, trt = session_from_driver(driver)
client = PjeApiClient(sess, trt)

# Verificar BNDT de um processo
resultado = verificar_bndt(client, id_processo='1234567')

if resultado['tem_partes']:
        for nome in resultado['partes']:
        logger.info(f"   - {nome}")
    logger.info(f"\nMensagem completa:\n{resultado['mensagem']}")
else:
    
# 2. Uso direto do método da API
partes_bndt = client.debitos_trabalhistas_bndt('1234567')
if partes_bndt:
    for parte in partes_bndt:
        logger.info(f"Parte: {parte.get('nomeParte')}")
        # Acessar outros campos retornados pela API
        logger.info(f"  CPF/CNPJ: {parte.get('cpfCnpj', 'N/A')}")
        logger.info(f"  Valor: {parte.get('valorDevido', 'N/A')}")
else:
    logger.info("Nenhuma parte no BNDT ou erro na consulta")

# 3. Integração em fluxo de trabalho
def processar_com_verificacao_bndt(driver, id_processo):
    sess, trt = session_from_driver(driver)
    client = PjeApiClient(sess, trt)
    
    resultado_bndt = verificar_bndt(client, id_processo)
    
    if resultado_bndt.get('erro'):
        logger.info(f"Erro ao consultar BNDT: {resultado_bndt['erro']}")
        return False
    
    if resultado_bndt['tem_partes']:
        # Executar ação específica se há partes no BNDT
                # ... seu código aqui
        return True
    else:
        logger.info(" Processo sem partes no BNDT - seguindo fluxo normal")
        return False
"""
