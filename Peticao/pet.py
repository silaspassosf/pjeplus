# Ajuste sys.path para permitir imports do projeto raiz
import sys, os
if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)

"""
PEC/pet.py - Processamento de Petições (PJe)
VERSÃO SIMPLIFICADA: Padrão p2b.py - regras simples (lista_regex, acao)
"""

import re
import json
from pathlib import Path
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from Peticao.core.extracao import criar_gigs, extrair_direto, extrair_documento, extrair_dados_processo
from Prazo.p2b_core import normalizar_texto, gerar_regex_geral
from Fix.selenium_base.wait_operations import esperar_elemento
from Fix.utils_observer import aguardar_renderizacao_nativa as _aguardar_renderizacao

# Import de atos/wrappers_ato para ato_gen (despacho genérico)
try:
    from Peticao.atos.wrappers import ato_instc, ato_inste, ato_gen
except ImportError:
    ato_instc = None
    ato_inste = None
    ato_gen = None

# Import de helpers para funções customizadas
try:
    from Peticao.helpers import checar_habilitacao, agravo_peticao, def_quesitos, contesta_calc
except ImportError:
    checar_habilitacao = None
    agravo_peticao = None
    def_quesitos = None
    contesta_calc = None

# Import de atos/wrappers_ato para ação de perícias
try:
    from Peticao.atos.wrappers import ato_laudo, ato_esc, ato_escliq, ato_datalocal
except ImportError:
    ato_laudo = None
    ato_esc = None
    ato_escliq = None
    ato_datalocal = None

# Import atos de diretos
try:
    from Peticao.atos.wrappers import ato_ceju, ato_respcalc, ato_assistente, ato_concor, ato_prevjud, ato_naocoaf, ato_naosimba, ato_teim, ato_adesivo, ato_homacordo, ato_uber
except ImportError:
    ato_ceju = ato_respcalc = ato_assistente = ato_concor = ato_prevjud = ato_naocoaf = ato_naosimba = ato_teim = ato_adesivo = ato_homacordo = ato_uber = None

try:
    from Peticao.atos.wrappers import ato_ccs, ato_censec, ato_serp, ato_conv
except ImportError:
    ato_ccs = ato_censec = ato_serp = ato_conv = None

# Import do módulo de helpers para checagens personalizadas
try:
    from Peticao.helpers import checar_habilitacao
except ImportError:
    try:
        from Peticao.helpers import checar_habilitacao
    except ImportError:
        checar_habilitacao = None

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

ESCANINHO_URL = "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"

# ============================================================================
# FUNÇÕES DE PROGRESSO (padrão Prazo/p2b.py)
# ============================================================================


# Progresso PET centralizado — sistema unificado (mesmo padrão p2b/pec/mandado)
from Peticao.progresso import (
    carregar_progresso_pet,
    salvar_progresso_pet,
    marcar_processo_executado_pet,
    processo_ja_executado_pet,
)


def _w(fn):
    """Adapta ato (driver) → (driver, item) esperado pelo orquestrador."""
    if fn is None:
        return None
    return lambda driver, _: fn(driver)


def _gigs(dias, resp, obs):
    """Factory: callable (driver, item) que chama criar_gigs(driver, dias, resp, obs)."""
    return lambda driver, _: criar_gigs(driver, dias, resp, obs)


class _Dados:
    """
    Wrapper sobre dadosatuais.json (gravado por extrair_dados_processo antes de cada ação).
    Expõe condições nomeadas reutilizáveis nas regras de classificação.
    Sem chamada de rede — usa apenas o JSON já presente em disco.
    """
    def __init__(self):
        self._d: dict = {}
        try:
            p = Path('dadosatuais.json')
            if p.exists():
                self._d = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass

    # ---- acessores básicos ----
    def fase(self) -> str:
        return normalizar_texto(self._d.get('labelFaseProcessual') or '')

    def reus(self) -> list:
        return self._d.get('reu') or []

    def terceiros(self) -> list:
        return self._d.get('terceiro') or []

    def autores(self) -> list:
        return self._d.get('autor') or []

    # ---- condições reutilizáveis ----
    def um_reu_com_advogado(self) -> bool:
        """Exatamente 1 réu com advogado preenchido."""
        reus = self.reus()
        return (
            len(reus) == 1
            and bool(reus[0].get('advogado', {}).get('nome', '').strip())
        )

    def sem_perito_terceiro(self) -> bool:
        """Nenhum terceiro com 'perito' no nome."""
        return not any(
            'perito' in str(t.get('nome', '')).lower()
            for t in self.terceiros()
        )

    def sem_perito_rogerio(self) -> bool:
        """Nenhum perito chamado Rogério nas partes extraídas."""
        def nome_partes() -> list[str]:
            nomes = []
            for pessoa in self.autores() + self.reus() + self.terceiros():
                nomes.append(str(pessoa.get('nome', '')).lower())
            return nomes

        return not any(
            'rogerio' in nome
            for nome in nome_partes()
        )


def _dados() -> _Dados:
    """Lê dadosatuais.json e retorna wrapper com condições prontas."""
    return _Dados()


def _cond_impugnacao_liq(item) -> bool:
    """
    Condição para ato_concor em Impugnação (Liquidação):
    - tipo_peticao: contém 'impugnacao'
    - fase: contém 'liquidacao'
    - dadosatuais: exatamente 1 réu com advogado
    - dadosatuais: nenhum terceiro-perito
    """
    tipo = normalizar_texto(item.tipo_peticao or '')
    if 'impugnacao' not in tipo or 'liquidacao' not in _nfase(item):
        return False
    d = _dados()
    return d.um_reu_com_advogado() and d.sem_perito_terceiro() and d.sem_perito_rogerio()


def _executar_acao(driver, item, acao) -> bool:
    if isinstance(acao, tuple):
        for f in acao:
            if callable(f) and not f(driver, item):
                return False
        return True
    return acao(driver, item) if callable(acao) else False


def _detectar_acao_analise(texto: str, dados: _Dados):
    if not texto:
        return None

    texto = normalizar_texto(texto)
    if 'ccs' in texto and 'censec' in texto and 'infojud' in texto:
        return (_gigs("1", "", "xs cumprir"), _w(ato_conv)) if ato_conv else (_gigs("1", "", "xs cumprir"),)
    if 'censec' in texto and 'ccs' not in texto:
        return (_gigs("1", "", "xs censec"), _w(ato_censec)) if ato_censec else (_gigs("1", "", "xs censec"),)
    if 'ccs' in texto:
        return (_gigs("1", "", "xs ccs"), _w(ato_ccs)) if ato_ccs else (_gigs("1", "", "xs ccs"),)
    if any(x in texto for x in ['plataformas digitais', 'uber', 'ifood']):
        return (_w(ato_uber),) if ato_uber else None
    if 'crcjud' in texto or 'crc-jud' in texto or 'crc jud' in texto:
        return (_gigs("1", "", "xs serp"), _w(ato_serp)) if ato_serp else (_gigs("1", "", "xs serp"),)
    if 'discordancia aos esclarecimentos' in texto or 'discordância aos esclarecimentos' in texto:
        return 'flag_apagar'
    if 'assistente tecnico' in texto or 'assistente técnico' in texto:
        return (_w(ato_assistente),)
    if 'comprovante de pagamento' in texto and 'execucao' in dados.fase():
        return (_gigs("-1", "", "Bruna Liberação"),)
    return None


# ============================================================================
# CLASSIFICAÇÃO — campos da API → nome do bucket
# ============================================================================

def _nfase(item) -> str:
    return normalizar_texto(item.fase or '')


def _regras(item, driver=None):
    """Tabela única: (bucket, condição, ações).
    Ordem = prioridade. Primeiro match define bucket E ação.
    ações=None → apagar (sem abrir processo) ou analise (orquestrador trata).
    checar_habilitacao só avaliado quando driver disponível.
    """
    tipo   = normalizar_texto(item.tipo_peticao or '')
    desc   = normalizar_texto(item.descricao or '')
    tarefa = normalizar_texto(item.tarefa or '')
    f      = _nfase(item)
    perito = getattr(item, 'eh_perito', False)

    return [
        # ── APAGAR (sem driver, sem abrir processo) ───────────────────────
        ('apagar',   'parecer do assistente' in desc,                                                      None),
        ('apagar',   'razoes finais' in tipo or 'carta convite' in tipo,                                    None),
        ('apagar',   'conhecimento' in f and 'manifestacao' in tipo and any(x in desc for x in ['replica', 'razoes finais', 'preposicao', 'substabelecimento']), None),
        ('apagar',   'replica' in tipo and 'conhecimento' in f,                                             None),
        ('apagar',   'aguardando cumprimento de acordo' in tarefa,                                          None),
        ('apagar',   'manifestacao' in tipo and any(x in desc for x in ['carta de preposicao', 'substabelecimento']), None),
        ('apagar',   'triagem inicial' in f,                                                                None),
        ('apagar',   'contestacao' in tipo and 'conhecimento' in f,                                        None),
        # ── PERICIAS ──────────────────────────────────────────────────────
        ('pericias', perito and 'esclarecimentos' in tipo and 'liquidacao' in f,  (_w(ato_escliq),)),
        ('pericias', perito and 'esclarecimentos' in tipo,                         (_w(ato_esc),)),
        ('pericias', perito and 'apresentacao de laudo pericial' in tipo,          (_w(ato_laudo),)),
        ('pericias', perito and 'indicacao de data' in tipo,                       (_gigs("-1", "", "xs aud"), _w(ato_datalocal))),
        ('pericias', perito,                                                        (_w(ato_laudo),)),
        # ── RECURSO ───────────────────────────────────────────────────────
        ('recurso',  'agravo de instrumento' in tipo and ('liquidacao' in f or 'execucao' in f), (_w(ato_inste),)),
        ('recurso',  'agravo de instrumento' in tipo,                                             (_w(ato_instc),)),
        ('recurso',  'agravo de peticao' in tipo,                                                 (lambda driver, item: checar_habilitacao(item, driver) if 'habilitacao' in tipo else agravo_peticao(item, driver),)),
        # ── DIRETOS ───────────────────────────────────────────────────────
        ('diretos',  'habilitacao' in tipo,                                        (lambda driver, item: checar_habilitacao(item, driver),)),
        ('diretos',  'ratificacao do acordo' in desc or 'ratificação do acordo' in desc, (_w(ato_homacordo),)),
        ('diretos',  'conhecimento' in f and ('quesitos' in tipo or 'quesitos' in desc), (lambda driver, item: def_quesitos(item, driver),)),
        ('diretos',  'coaf' in desc,                                               (_w(ato_naocoaf),)),
        ('diretos',  'simba' in desc,                                              (_w(ato_naosimba),)),
        ('diretos',  'teimosinha' in desc or 'sisbajud' in desc,                    (_gigs("1", "", "xs teimosinha"), _w(ato_teim))),
        ('diretos',  'recurso adesivo' in tipo,                                   (_w(ato_adesivo),)),
        ('diretos',  'calculos' in tipo,                                           (lambda driver, item: contesta_calc(item, driver),) if contesta_calc else (_w(ato_respcalc),)),
        ('diretos',  'assistente' in tipo,                                         (_gigs("1", "", "xs aud"), _w(ato_assistente)) if ato_assistente else (_gigs("1", "", "xs aud"),)),
        ('diretos',  _cond_impugnacao_liq(item),                                 (_w(ato_concor),)),
        ('diretos',  'caged' in desc,                                              (_gigs("-1", "", "xs pec"), _w(ato_prevjud)) if ato_prevjud else (_gigs("-1", "", "xs pec"),)),
        ('diretos',  'concordancia' in desc and 'liquidacao' in f,               (_gigs("1", "Silas", "Homologação"),)),
        ('diretos',  bool(re.search(r'comprovante|deposito|pagamento|guia', desc)), (_gigs("-1", "", "Bruna Liberação"),)),
        # ── ANALISE (fallback) ────────────────────────────────────────────
        ('analise',  True,                                                        None),
    ]


def classificar(item) -> str:
    """Bucket pelo primeiro match em _regras (sem driver — pura API)."""
    for bucket, cond, _ in _regras(item):
        if cond:
            return bucket
    return 'analise'


def resolver_acao(item, driver=None):
    """Ação pelo primeiro match em _regras."""
    for _, cond, acao in _regras(item, driver):
        if cond:
            return acao
    return None


def _abrir_ultimo_documento_timeline(driver: WebDriver):
    """
    Retorna o link (<a>) do primeiro item da timeline (mais recente),
    iterando sobre li.tl-item-container.
    """
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    for item in itens:
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            return link
        except Exception:
            continue
    return None


def _abrir_documento_peticao(driver: WebDriver, peticao) -> Optional[object]:
    """Localiza o link viewer pelo id_item (definitivo — sem fallback)."""
    id_doc = getattr(peticao, 'id_item', '') or ''
    if not id_doc:
        logger.error('[PET_ANALISE] id_item ausente — não é possível localizar o documento')
        return None

    _aguardar_renderizacao(driver, 'mat-card', modo='aparecer', timeout=8)
    card = esperar_elemento(
        driver,
        f'//mat-card[.//a[contains(@href, "/documento/{id_doc}/")]]',
        timeout=10,
        by=By.XPATH,
    )
    if not card:
        logger.error(f'[PET_ANALISE] mat-card para documento/{id_doc} não encontrado na timeline')
        return None

    for sel in ('a.tl-documento[accesskey="v"]', 'a.tl-documento[role="button"]', 'a.tl-documento:not([target="_blank"])'):
        try:
            return card.find_element(By.CSS_SELECTOR, sel)
        except Exception:
            continue
    logger.error(f'[PET_ANALISE] Link viewer não encontrado no card de documento/{id_doc}')
    return None


def _extrair_texto_doc_pet(driver: WebDriver, link) -> Optional[str]:
    """
    Clica no link, aguarda renderização e extrai texto via extrair_direto / extrair_documento.
    Mesmo padrão de p2b_fluxo_documentos._extrair_texto_documento.
    """
    global logger
    link.click()
    try:
        from Peticao.core.utils.observer import aguardar_renderizacao_nativa
        aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
    except Exception:
        pass

    try:
        resultado = extrair_direto(driver, timeout=10, debug=False, formatar=True)
        if resultado and resultado.get('sucesso'):
            if resultado.get('conteudo'):
                texto = resultado['conteudo'].lower()
            elif resultado.get('conteudo_bruto'):
                texto = resultado['conteudo_bruto'].lower()
            else:
                texto = None
        else:
            texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=False)
            if texto_tuple and texto_tuple[0]:
                texto = texto_tuple[0].lower()
            else:
                texto = None
    except Exception as e:
        logger.error(f'Erro ao extrair texto da petição: {e}')
        texto = None

    return texto


def extrair_texto_peticao_via_api(driver: WebDriver, peticao) -> Optional[str]:
    """
    Extrai o texto da petição via API PJe, sem interação com a timeline.
    Usa session_from_driver para reutilizar cookies da sessão ativa.
    Retorna texto normalizado em lowercase ou None se falhar.
    """
    id_doc = getattr(peticao, 'id_item', '') or ''
    id_proc = getattr(peticao, 'id_processo', '') or ''
    if not id_doc or not id_proc:
        logger.debug('[PET_API] id_item ou id_processo ausente — sem extração via API')
        return None

    try:
        from Fix.variaveis_client import session_from_driver, PjeApiClient
        import io
        import pdfplumber
    except ImportError as e:
        logger.debug(f'[PET_API] Dependência ausente para extração via API: {e}')
        return None

    try:
        sess, trt_host = session_from_driver(driver)
        client = PjeApiClient(sess, trt_host)
        url = client._url(
            f'/pje-comum-api/api/processos/id/{id_proc}/documentos/id/{id_doc}/conteudo'
        )
        resp = sess.get(url, timeout=30)
        if resp.status_code == 401:
            logger.warning('[PET_API] 401 na API — sessão expirada, usando fallback Selenium')
            return None
        if not resp.ok:
            logger.debug(f'[PET_API] HTTP {resp.status_code} ao buscar conteúdo do doc {id_doc}')
            return None
        if 'pdf' not in resp.headers.get('Content-Type', '').lower():
            logger.debug('[PET_API] Resposta não é PDF — usando fallback Selenium')
            return None

        textos = []
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            for pag in pdf.pages:
                t = pag.extract_text()
                if t:
                    textos.append(t)

        texto = '\n'.join(textos).strip()
        if not texto:
            logger.debug('[PET_API] PDF sem texto nativo (provavelmente imagem) — usando fallback Selenium')
            return None

        logger.info(f'[PET_API] Texto extraído via API: {len(texto)} chars (doc={id_doc})')
        return texto.lower()

    except Exception as e:
        logger.debug(f'[PET_API] Falha na extração via API: {e}')
        return None


def analise_pet(driver: WebDriver, peticao) -> bool:
    """
    Análise de petição:
    1. Extrai texto via API PJe (sem abrir documento no browser)
    2. Fallback: abre documento na timeline via Selenium
    3. Aplica regras; fallback final: ato_gen
    """
    logger.info('[PET_ANALISE] Iniciando analise_pet — %s', peticao.numero_processo)

    try:
        extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
    except Exception as e:
        logger.warning('[PET_ANALISE] Falha ao extrair dados: %s', e)

    texto = extrair_texto_peticao_via_api(driver, peticao)

    if not texto:
        logger.info('[PET_ANALISE] Fallback Selenium')
        link = _abrir_documento_peticao(driver, peticao)
        if not link:
            logger.error('[PET_ANALISE] Nenhum documento encontrado')
            return False
        texto = _extrair_texto_doc_pet(driver, link)

    if not texto:
        logger.error('[PET_ANALISE] Falha na extracao de conteudo')
        return False

    dados = _dados()
    acao_analise = _detectar_acao_analise(texto, dados)
    if acao_analise == 'flag_apagar':
        logger.warning('[PET_ANALISE] flag_apagar — sinalizar para apagar')
        return False
    if acao_analise:
        try:
            if _executar_acao(driver, peticao, acao_analise):
                return True
        except Exception as e:
            logger.error('[PET_ANALISE] Erro ao executar acao: %s', e)

    logger.info('[PET_ANALISE] Executando ato_gen (despacho generico)')
    if ato_gen:
        try:
            ato_gen(driver)
            return True
        except Exception as e:
            logger.error('[PET_ANALISE] Erro no ato_gen: %s', e)
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_pet(driver=None):
    """Cria driver, faz login e executa o pipeline completo de petições."""
    from Fix.utils import driver_pc as _driver_pc, login_cpf as _login_cpf, configurar_recovery_driver, handle_exception_with_recovery
    from Peticao.core.utils import criar_driver_e_logar
    from Peticao.orquestrador import executar_fluxo_pet

    configurar_recovery_driver(_driver_pc, _login_cpf)

    drv = criar_driver_e_logar(driver)
    if not drv:
        print('[PET] Falha ao obter driver (abortando)')
        return None

    print(f'[PET] Navegando para {ESCANINHO_URL}')
    try:
        drv.get(ESCANINHO_URL)
    except Exception:
        try:
            drv.quit()
        except Exception:
            pass
        print('[PET] Driver caiu ao navegar; recriando sessão...')
        drv = criar_driver_e_logar()
        if not drv:
            print('[PET] Falha ao recuperar driver')
            return None
        drv.get(ESCANINHO_URL)

    try:
        return executar_fluxo_pet(drv)
    except Exception as e:
        novo_drv = handle_exception_with_recovery(e, drv, 'PET_RUN')
        if novo_drv:
            print('[PET] Acesso negado detectado; driver recuperado, reiniciando fluxo...')
            try:
                return executar_fluxo_pet(novo_drv)
            except Exception as e2:
                print(f'[PET] Falha ao reiniciar fluxo após recuperação: {e2}')
                return None
        print(f'[PET] Erro geral no run_pet: {e}')
        return None


if __name__ == '__main__':
    print('[PET] executando como script')
    run_pet()
