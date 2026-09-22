"""
Peticao/runtime_pet.py — Runtime consolidado do fluxo G (Peticao)

Consolida: pet.py, orquestrador.py, api_client.py, progresso.py,
           core/utils/utils.py, core/utils/observer.py
"""

from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)

# ============================================================================
# Dependencias — stdlib
# ============================================================================

import io
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

# ============================================================================
# Dependencias — Selenium
# ============================================================================

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

# ============================================================================
# Dependencias — Fix
# ============================================================================

from Fix.extracao import extrair_dados_processo
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    salvar_progresso_unificado,
)
from Fix.selenium_base.wait_operations import esperar_elemento
from Fix.core import aguardar_renderizacao_nativa as _aguardar_renderizacao
from Fix.abas import fechar_abas_extras as _fechar_abas_extras

# ============================================================================
# Dependencias — Peticao
# ============================================================================

# Nota: core/extracao e regras sao importados abaixo via lazy para evitar
# circular import com core/utils/utils.py e core/utils/observer.py via
# helpers -> extracao -> observer (mantidos in-situ).
# As funcoes de core/utils/ sao importadas diretamente de seus modulos
# originais para o mesmo fim.

from Peticao.core.extracao import criar_gigs, extrair_direto, extrair_documento
from Peticao.core.utils.observer import aguardar_renderizacao_nativa
from Peticao.core.utils.utils import criar_driver_e_logar
from Peticao.regras_execucao import (
    _Dados,
    _dados,
    _detectar_acao_analise,
    _executar_acao,
    classificar,
    resolver_acao,
)

# ============================================================================
# Dependencias — projeto raiz
# ============================================================================

from utilitarios_processamento import resultado_falha, resultado_ok


# ============================================================================
# CONFIGURACOES
# ============================================================================

ESCANINHO_URL = "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"
BUCKETS_ORDEM = ['diretos', 'pericias', 'recurso', 'analise']


# ============================================================================
# ENTRADA — run_pet e helpers
# ============================================================================

def _run_pet_ok():
    """Resultado de sucesso padronizado + compatibilidade com _executar_fluxo de x.py."""
    r = resultado_ok()
    r["sucesso"] = True
    return r


def _run_pet_falha(erro: str):
    """Resultado de falha padronizado + compatibilidade com _executar_fluxo de x.py."""
    r = resultado_falha(erro)
    r["sucesso"] = False
    return r


def _abrir_documento_peticao(driver: WebDriver, peticao) -> Optional[object]:
    """Localiza o link viewer pelo id_item (definitivo — sem fallback)."""
    id_doc = getattr(peticao, 'id_item', '') or ''
    if not id_doc:
        logger.error('[PET_ANALISE] id_item ausente — nao e possivel localizar o documento')
        return None

    _aguardar_renderizacao(driver, 'mat-card', modo='aparecer', timeout=8)
    card = esperar_elemento(
        driver,
        f'//mat-card[.//a[contains(@href, "/documento/{id_doc}/")]]',
        timeout=10,
        by=By.XPATH,
    )
    if not card:
        logger.error(f'[PET_ANALISE] mat-card para documento/{id_doc} nao encontrado na timeline')
        return None

    for sel in ('a.tl-documento[accesskey="v"]', 'a.tl-documento[role="button"]', 'a.tl-documento:not([target="_blank"])'):
        try:
            return card.find_element(By.CSS_SELECTOR, sel)
        except Exception:
            continue
    logger.error(f'[PET_ANALISE] Link viewer nao encontrado no card de documento/{id_doc}')
    return None


def _extrair_texto_doc_pet(driver: WebDriver, link) -> Optional[str]:
    """
    Clica no link, aguarda renderizacao e extrai texto via extrair_direto / extrair_documento.
    Mesmo padrao de p2b_fluxo_documentos._extrair_texto_documento.
    """
    link.click()
    try:
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
        logger.error(f'Erro ao extrair texto da peticao: {e}')
        texto = None

    return texto


def extrair_texto_peticao_via_api(driver: WebDriver, peticao) -> Optional[str]:
    """
    Extrai o texto da peticao via API PJe, sem interacao com a timeline.
    Usa session_from_driver para reutilizar cookies da sessao ativa.
    Retorna texto normalizado em lowercase ou None se falhar.
    """
    id_doc = getattr(peticao, 'id_item', '') or ''
    id_proc = getattr(peticao, 'id_processo', '') or ''
    if not id_doc or not id_proc:
        logger.debug('[PET_API] id_item ou id_processo ausente — sem extracao via API')
        return None

    try:
        from api.variaveis_client import session_from_driver, PjeApiClient
        import pdfplumber
    except ImportError as e:
        logger.debug(f'[PET_API] Dependencia ausente para extracao via API: {e}')
        return None

    try:
        sess, trt_host = session_from_driver(driver)
        client = PjeApiClient(sess, trt_host)
        url = client._url(
            f'/pje-comum-api/api/processos/id/{id_proc}/documentos/id/{id_doc}/conteudo'
        )
        resp = sess.get(url, timeout=30)
        if resp.status_code == 401:
            logger.warning('[PET_API] 401 na API — sessao expirada, usando fallback Selenium')
            return None
        if not resp.ok:
            logger.debug(f'[PET_API] HTTP {resp.status_code} ao buscar conteudo do doc {id_doc}')
            return None
        if 'pdf' not in resp.headers.get('Content-Type', '').lower():
            logger.debug('[PET_API] Resposta nao e PDF — usando fallback Selenium')
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

        logger.info(f'[PET_API] Texto extraido via API: {len(texto)} chars (doc={id_doc})')
        return texto.lower()

    except Exception as e:
        logger.debug(f'[PET_API] Falha na extracao via API: {e}')
        return None


def analise_pet(driver: WebDriver, peticao) -> bool:
    """
    Analise de peticao:
    1. Extrai texto via API PJe (sem abrir documento no browser)
    2. Fallback: abre documento na timeline via Selenium
    3. Aplica regras; fallback final: criar_gigs
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

    logger.info('[PET_ANALISE] Fallback: criando GIGS (sem filtro reconhecido)')
    try:
        criar_gigs(driver, '', '', 'Analise - sem filtro reconhecido')
        return True
    except Exception as e:
        logger.error('[PET_ANALISE] Erro ao criar GIGS fallback: %s', e)
    return False


def run_pet(driver=None):
    """Cria driver, faz login e executa o pipeline completo de peticoes."""
    from Fix.utils import driver_pc as _driver_pc, login_cpf as _login_cpf, configurar_recovery_driver, handle_exception_with_recovery

    configurar_recovery_driver(_driver_pc, _login_cpf)

    drv = criar_driver_e_logar(driver)
    if not drv:
        logger.error('[PET] Falha ao obter driver (abortando)')
        return _run_pet_falha("Falha ao obter driver")

    logger.info(f'[PET] Navegando para {ESCANINHO_URL}')
    try:
        drv.get(ESCANINHO_URL)
    except Exception:
        try:
            drv.quit()
        except Exception:
            pass
        logger.warning('[PET] Driver caiu ao navegar; recriando sessao...')
        drv = criar_driver_e_logar()
        if not drv:
            logger.error('[PET] Falha ao recuperar driver')
            return _run_pet_falha("Falha ao recuperar driver")
        drv.get(ESCANINHO_URL)

    try:
        ok = executar_fluxo_pet(drv)
        return _run_pet_ok() if ok else _run_pet_falha("executar_fluxo_pet retornou False")
    except Exception as e:
        novo_drv = handle_exception_with_recovery(e, drv, 'PET_RUN')
        if novo_drv:
            logger.warning('[PET] Acesso negado detectado; driver recuperado, reiniciando fluxo...')
            try:
                ok = executar_fluxo_pet(novo_drv)
                return _run_pet_ok() if ok else _run_pet_falha("executar_fluxo_pet retornou False apos recuperacao")
            except Exception as e2:
                logger.error(f'[PET] Falha ao reiniciar fluxo apos recuperacao: {e2}')
                return _run_pet_falha(str(e2))
        logger.error(f'[PET] Erro geral no run_pet: {e}')
        return _run_pet_falha(str(e))


# ============================================================================
# ORQUESTRACAO
# ============================================================================

def _classificar(itens: List) -> Dict[str, list]:
    buckets: Dict[str, list] = {nome: [] for nome in BUCKETS_ORDEM}
    for item in itens:
        bucket = classificar(item)
        buckets.setdefault(bucket, []).append(item)
    return buckets


def _abrir_processo(driver: WebDriver, item) -> bool:
    id_proc = getattr(item, 'id_processo', None) or getattr(item, 'numero_processo', '')
    numero_limpo = ''.join(filter(str.isdigit, str(id_proc)))
    url = (f"https://pje.trt2.jus.br/pjekz/processo/{numero_limpo}/detalhe"
           if len(numero_limpo) == 20
           else f"https://pje.trt2.jus.br/pjekz/processo/{id_proc}/detalhe")
    driver.get(url)
    WebDriverWait(driver, 15).until(
        lambda d: d.execute_script('return document.readyState') == 'complete'
    )
    if 'acesso-negado' in driver.current_url.lower():
        raise RuntimeError(f"RESTART_PET: acesso negado - {getattr(item, 'numero_processo', '?')}")
    return True


def _executar_bucket_normal(driver: WebDriver, nome: str, itens: list,
                            progresso: dict) -> Dict[str, int]:
    """Buckets que requerem abertura individual do processo."""
    stats = {'sucesso': 0, 'erro': 0}
    quesitos_consolidado = False

    for item in itens:
        if processo_ja_executado_pet(getattr(item, 'numero_processo', ''), progresso):
            logger.info(f"[SKIP] {getattr(item, 'numero_processo', '?')}")
            stats['sucesso'] += 1
            continue

        acao = resolver_acao(item, driver)

        if not acao:
            logger.warning(f"[PET_EXEC] Sem acao para {getattr(item, 'numero_processo', '?')} em '{nome}'")
            continue

        logger.info(f"[PET_EXEC] {nome} | {getattr(item, 'numero_processo', '?')} | {getattr(item, 'tipo_peticao', '?')}")
        try:
            _abrir_processo(driver, item)
            extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
            ok = _executar_acao(driver, item, acao)
            if ok:
                marcar_processo_executado_pet(getattr(item, 'numero_processo', ''), progresso)
                stats['sucesso'] += 1
            else:
                stats['erro'] += 1
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"[PET_EXEC] {getattr(item, 'numero_processo', '?')}: {e}")
            stats['erro'] += 1
        finally:
            _fechar_abas_extras(driver)

        # Se processamos um item de quesitos e ainda nao consolidamos, fazer agora
        if nome == 'diretos' and not quesitos_consolidado and (
            'quesitos' in (getattr(item, 'tipo_peticao', '') or '')
            or 'quesitos' in (getattr(item, 'descricao', '') or '')
        ):
            logger.info('[PET_EXEC] Quesitos processado -> consolidando delete.js')
            _consolidar_delete_bookmarklet()
            quesitos_consolidado = True

    return stats


def _executar_bucket_analise(driver: WebDriver, itens: list,
                             progresso: dict) -> Dict[str, int]:
    """Analise: sempre chama analise_pet, independente de hipotese."""
    stats = {'sucesso': 0, 'erro': 0}
    for item in itens:
        if processo_ja_executado_pet(getattr(item, 'numero_processo', ''), progresso):
            logger.info(f"[SKIP] {getattr(item, 'numero_processo', '?')}")
            stats['sucesso'] += 1
            continue
        logger.info(f"[PET_EXEC] analise | {getattr(item, 'numero_processo', '?')} | {getattr(item, 'tipo_peticao', '?')}")
        try:
            _abrir_processo(driver, item)
            extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
            ok = analise_pet(driver, item)
            if ok:
                marcar_processo_executado_pet(getattr(item, 'numero_processo', ''), progresso)
                stats['sucesso'] += 1
            else:
                stats['erro'] += 1
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"[PET_EXEC] analise {getattr(item, 'numero_processo', '?')}: {e}")
            stats['erro'] += 1
        finally:
            _fechar_abas_extras(driver)
    return stats


def _executar_bucket_apagar(itens: list) -> Dict[str, int]:
    """Apagar: sem abertura de processo — registra em delete.js apenas com id_doc."""
    from Peticao.helpers import apagar
    stats = {'sucesso': 0, 'erro': 0}
    for item in itens:
        try:
            apagar(getattr(item, 'numero_processo', ''), getattr(item, 'id_item', ''))
            logger.info(f'[PET_APAG] {getattr(item, "numero_processo", "?")} | id_doc={getattr(item, "id_item", "?")!r}')
            stats['sucesso'] += 1
        except Exception as e:
            logger.error(f'[PET_APAG] {getattr(item, "numero_processo", "?")}: {e}')
            stats['erro'] += 1
    return stats


def _consolidar_delete_bookmarklet():
    """Consolida delete.js apos habilitacao e gera bookmarklet."""
    try:
        from Peticao.suporte_pet import consolidar_delete_com_bookmarklet
        consolidar_delete_com_bookmarklet()
        logger.info('[PET_ORQ] delete.js consolidado e bookmarklet gerado')
    except Exception as e:
        logger.warning(f'[PET_ORQ] Falha ao consolidar delete.js: {e}')


class PETOrquestrador:
    """Orquestrador do pipeline de peticoes."""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.progresso: dict = carregar_progresso_pet()

    def executar(self, dry_run: bool = False) -> Dict[str, int]:
        logger.info('=' * 60)
        logger.info('[PET_ORQ] Iniciando pipeline peticoes')

        itens = PeticaoAPIClient().fetch(self.driver)
        if not itens:
            logger.info('[PET_ORQ] Nenhuma peticao encontrada')
            return {'total': 0, 'sucesso': 0, 'erro': 0}

        logger.info(f'[PET_ORQ] {len(itens)} peticoes carregadas')
        buckets = _classificar(itens)

        logger.info('[PET_ORQ] Distribuicao por bucket:')
        for nome in ['apagar'] + BUCKETS_ORDEM:
            qtd = len(buckets.get(nome, []))
            if qtd:
                logger.info(f'  {nome}: {qtd}')

        if dry_run:
            return {'total': len(itens), 'sucesso': 0, 'erro': 0}

        # Apagar: executa imediatamente, sem abrir processos
        apagar_itens = buckets.get('apagar', [])
        if apagar_itens:
            logger.info(f'[PET_ORQ] Apagar: {len(apagar_itens)} itens -> delete.js')
            _executar_bucket_apagar(apagar_itens)

        # Executar sempre na ordem padrao dos buckets
        ordem = [n for n in BUCKETS_ORDEM if buckets.get(n)]
        stats = {'total': len(itens), 'sucesso': 0, 'erro': 0}

        for nome_bucket in ordem:
            itens_bucket = buckets.get(nome_bucket, [])
            if not itens_bucket:
                continue
            logger.info(f'\n[PET_ORQ] >>> Bucket "{nome_bucket}" ({len(itens_bucket)} itens)')
            try:
                if nome_bucket == 'analise':
                    r = _executar_bucket_analise(self.driver, itens_bucket, self.progresso)
                else:
                    r = _executar_bucket_normal(self.driver, nome_bucket, itens_bucket,
                                                self.progresso)
                stats['sucesso'] += r['sucesso']
                stats['erro'] += r['erro']
            except RuntimeError as e:
                if 'RESTART_PET' in str(e):
                    logger.error(f'[RESTART] {e}')
                    raise
                stats['erro'] += 1

        if apagar_itens:
            logger.info('[PET_ORQ] Consolidando delete.js e gerando bookmarklet')
            _consolidar_delete_bookmarklet()

        logger.info(f'\n[PET_ORQ] Total: {stats["total"]} | '
                    f'Sucesso: {stats["sucesso"]} | Erro: {stats["erro"]}')
        logger.info('=' * 60)
        return stats


def executar_fluxo_pet(driver: WebDriver) -> bool:
    """Entry point do pipeline de peticoes (compativel com x.py)."""
    try:
        orq = PETOrquestrador(driver)
        stats = orq.executar()
        return stats['erro'] == 0
    except RuntimeError as e:
        if 'RESTART_PET' in str(e):
            raise
        logger.error(f'[PET_FLUXO] Erro fatal: {e}')
        return False


# ============================================================================
# API CLIENT — PeticaoAPIClient, PeticaoItem
# ============================================================================

@dataclass
class PeticaoItem:
    """Modelo de dados para item de peticao do escaninho."""
    numero_processo: str
    tipo_peticao: str
    descricao: str
    tarefa: str
    fase: str
    data_juntada: str
    eh_perito: bool = False
    parte: str = ""
    id_processo: str = ""
    id_item: str = ""
    data_audiencia: Optional[str] = None
    polo: Optional[str] = None

    @property
    def texto_classificacao(self) -> str:
        return f"{self.tipo_peticao} {self.descricao} {self.tarefa} {self.fase}"


_JS_FETCH = """
const tamPag   = arguments[0] || 100;
const callback = arguments[1];

function asArray(d) {
  if (!d) return [];
  if (Array.isArray(d)) return d;
  if (Array.isArray(d.resultado)) return d.resultado;
  if (d.resultado && Array.isArray(d.resultado.conteudo)) return d.resultado.conteudo;
  if (Array.isArray(d.conteudo)) return d.conteudo;
  if (Array.isArray(d.dados)) return d.dados;
  return [];
}

(async function () {
  var base = location.origin;
  var hdrs = { 'Accept': 'application/json' };
  var ep   = base + '/pje-comum-api/api/escaninhos/peticoesjuntadas';
  try {
    var r = await fetch(ep + '?pagina=1&tamanhoPagina=' + tamPag + '&ordenacaoCrescente=true',
                        { credentials: 'include', headers: hdrs });
    if (!r.ok) { callback({ erro: 'STATUS_' + r.status, resultado: [] }); return; }
    var data  = await r.json();
    var todos = asArray(data);
    if (!todos.length) { callback({ erro: 'SEM_DADOS', resultado: [] }); return; }
    var totalPags = (data.totalPaginas || data.quantidadePaginas) || 1;
    for (var pg = 2; pg <= Math.min(totalPags, 10); pg++) {
      try {
        var r2 = await fetch(ep + '?pagina=' + pg + '&tamanhoPagina=' + tamPag + '&ordenacaoCrescente=true',
                             { credentials: 'include', headers: hdrs });
        if (r2.ok) todos = todos.concat(asArray(await r2.json()));
      } catch (e) { break; }
    }
    callback({ endpoint: 'peticoesjuntadas', resultado: todos });
  } catch (e) {
    callback({ erro: 'ASYNC_ERR: ' + e.message, resultado: [] });
  }
})();
"""


class PeticaoAPIClient:
    """Busca peticoes do escaninho via JavaScript direto."""

    def fetch(self, driver: WebDriver, tamanho_pagina: int = 100) -> list:
        try:
            driver.set_script_timeout(60)
            res = driver.execute_async_script(_JS_FETCH, tamanho_pagina)
        finally:
            try:
                driver.set_script_timeout(30)
            except Exception:
                pass

        if not res or res.get('erro'):
            logger.warning(f"[PET_API] {(res or {}).get('erro', 'sem_resposta')}")
            return []

        dados = res.get('resultado', [])
        logger.info(f"[PET_API] {len(dados)} peticoes via '{res.get('endpoint', '?')}'")
        return [_normalizar(raw) for raw in dados if raw]


def _normalizar(raw: dict) -> PeticaoItem:
    proc = raw.get('processo') or raw.get('processoJudicial') or {}
    numero = (proc.get('numero') or proc.get('numeroProcesso') or
              raw.get('numeroProcesso') or raw.get('nrProcesso') or '')

    polo_raw = (raw.get('poloPeticionante') or '').upper()
    polo_label = ('Ativo'    if 'ATIVO'     in polo_raw else
                  'Passivo'  if 'PASSIVO'   in polo_raw else
                  'Terceiro' if 'TERCEIRO'  in polo_raw else polo_raw)
    polo_key   = ('ativo'    if 'ATIVO'     in polo_raw else
                  'passivo'  if 'PASSIVO'   in polo_raw else None)
    papel = (raw.get('nomePapelUsuarioDocumento') or '').strip()
    parte = f"{polo_label} ({papel})" if polo_label and papel else polo_label or papel

    tarefa_obj = raw.get('tarefa') or raw.get('tarefaAtual')
    if not isinstance(tarefa_obj, dict):
        tarefa_obj = {}
    tarefa = (raw.get('nomeTarefa') or tarefa_obj.get('nome') or
              tarefa_obj.get('descricao') or '')

    return PeticaoItem(
        numero_processo=numero,
        tipo_peticao=(raw.get('nomeTipoProcessoDocumento') or raw.get('nomeTipoPeticao') or
                      raw.get('descricaoTipoPeticao') or raw.get('tipoPeticao') or ''),
        descricao=(raw.get('descricao') or raw.get('descricaoPeticao') or ''),
        tarefa=tarefa,
        fase=(raw.get('faseProcessual') or raw.get('fase') or raw.get('nomeFase') or
              proc.get('fase') or ''),
        data_juntada=(raw.get('dataJuntada') or raw.get('dataCadastro') or ''),
        eh_perito=(papel.lower() == 'perito'),
        parte=parte,
        polo=polo_key,
        id_processo=(proc.get('id') or proc.get('idProcesso') or raw.get('idProcesso') or ''),
        id_item=(raw.get('idDocumento') or raw.get('idPeticao') or raw.get('id') or ''),
    )


# ============================================================================
# PROGRESSO — tracking de progresso para PET
# ============================================================================

def carregar_progresso_pet() -> dict:
    """Carrega progresso salvo do PET."""
    try:
        return carregar_progresso_unificado('pet')
    except Exception:
        return {}


def salvar_progresso_pet(progresso: dict) -> None:
    """Salva progresso do PET."""
    try:
        salvar_progresso_unificado('pet', progresso)
    except Exception:
        pass


def marcar_processo_executado_pet(processo_id: str, progresso: dict) -> None:
    """Marca processo como executado no progresso PET."""
    try:
        marcar_processo_executado_unificado('pet', processo_id, progresso, sucesso=True)
    except Exception:
        pass


def processo_ja_executado_pet(processo_id: str, progresso: dict) -> bool:
    """Verifica se processo ja foi executado no PET."""
    try:
        return processo_ja_executado_unificado(processo_id, progresso)
    except Exception:
        return False


# ============================================================================
# MAIN GUARD
# ============================================================================

if __name__ == '__main__':
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))
    logger.info('[PET] executando como script')
    run_pet()
