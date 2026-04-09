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

# Import de atos/wrappers_ato para ato_gen (despacho genérico)
try:
    from Peticao.atos.wrappers import ato_instc, ato_inste, ato_gen
except ImportError:
    ato_instc = None
    ato_inste = None
    ato_gen = None

# Import de helpers para funções customizadas
try:
    from Peticao.helpers import checar_habilitacao, agravo_peticao, def_quesitos
except ImportError:
    checar_habilitacao = None
    agravo_peticao = None
    def_quesitos = None

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


# Progresso PET centralizado
from Peticao.monitoramento.progresso import (
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
        ('diretos',  'calculos' in tipo,                                           (_w(ato_respcalc),)),
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


def analise_pet(driver: WebDriver, peticao) -> bool:
    """
    Análise de petição via último documento da timeline (padrão p2b):
    1. Abre o último item da timeline (PDF mais recente)
    2. Extrai texto via extrair_direto / extrair_documento
    3. Fallback: ato_gen (Despacho Genérico)
    """
    logger.info('[PET_ANALISE] Iniciando analise_pet — %s', peticao.numero_processo)

    try:
        extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
    except Exception as e:
        logger.warning('[PET_ANALISE] Falha ao extrair dados do processo antes da análise: %s', e)

    link = _abrir_ultimo_documento_timeline(driver)
    if not link:
        logger.error('[PET_ANALISE] Nenhum documento encontrado na timeline')
        return False

    texto = _extrair_texto_doc_pet(driver, link)
    if not texto:
        # Tentar extração direta novamente (padrão p2b)
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
            logger.error(f'[PET_ANALISE] Erro na extração de conteúdo: {e}')
            texto = None
        if not texto:
            logger.error('[PET_ANALISE] Falha na extracao de conteudo')
            return False

    dados = _dados()
    acao_analise = _detectar_acao_analise(texto, dados)
    if acao_analise == 'flag_apagar':
        logger.warning('[PET_ANALISE] Discordância aos esclarecimentos detectada — sinalizar para apagar')
        return False
    if acao_analise:
        try:
            if _executar_acao(driver, peticao, acao_analise):
                return True
        except Exception as e:
            logger.error('[PET_ANALISE] Erro ao executar ação de análise: %s', e)

    # Fallback: ato_gen (Despacho Genérico)
    logger.info('[PET_ANALISE] Executando ato_gen (despacho genérico)')
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
    from Fix.utils import driver_pc as _driver_pc, login_cpf as _login_cpf, configurar_recovery_driver
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

    return executar_fluxo_pet(drv)


if __name__ == '__main__':
    print('[PET] executando como script')
    run_pet()
