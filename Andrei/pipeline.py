"""
Andrei/pipeline.py — Orquestrador principal do pipeline de peticoes.

Equivalente standalone de Peticao/runtime_pet.py.
Sem dependencias de Fix.*, Triagem.*, Peticao.*, atos.*, core.*, Prazo.*
ou utilitarios_processamento. Apenas stdlib, selenium e Andrei.* modules.
"""

import io
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from Andrei.config import ESCANINHO_URL
from Andrei.driver import (
    criar_driver_e_logar,
    criar_driver,
    aguardar_login_manual,
)
from Andrei.utils_selenium import (
    esperar_elemento,
    aguardar_renderizacao_nativa,
    fechar_abas_extras,
)
from Andrei.extracao import (
    extrair_dados_processo,
    extrair_direto,
    extrair_documento,
    criar_gigs,
)
from Andrei.regras import (
    _dados,
    _detectar_acao_analise,
    _executar_acao,
    classificar,
    resolver_acao,
)
from Andrei.helpers import (
    apagar,
    configurar_recovery_driver,
    handle_exception_with_recovery,
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES
# ============================================================================

BUCKETS_ORDEM = ['diretos', 'pericias', 'recurso', 'analise']
_CAMINHO_DADOS = 'Andrei/dadosatuais.json'


# ============================================================================
# HELPERS DE RESULTADO (inline, sem import de utilitarios_processamento)
# ============================================================================

def resultado_ok(**dados) -> dict:
    """Resultado de sucesso padronizado."""
    return {"ok": True, "erro": None, "dados": dados}


def resultado_falha(erro, **dados) -> dict:
    """Resultado de falha padronizado."""
    return {"ok": False, "erro": str(erro), "dados": dados}


# ============================================================================
# PeticaoItem
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


# ============================================================================
# PeticaoAPIClient — busca peticoes do escaninho via JS
# ============================================================================

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
    """Busca peticoes do escaninho via JavaScript direto no navegador."""

    def fetch(self, driver: WebDriver, tamanho_pagina: int = 100) -> List[PeticaoItem]:
        try:
            driver.set_script_timeout(60)
            res = driver.execute_async_script(_JS_FETCH, tamanho_pagina)
        finally:
            try:
                driver.set_script_timeout(30)
            except Exception:
                pass

        if not res or res.get('erro'):
            logger.warning("[PET_API] %s", (res or {}).get('erro', 'sem_resposta'))
            return []

        dados = res.get('resultado', [])
        logger.info("[PET_API] %d peticoes via '%s'", len(dados), res.get('endpoint', '?'))
        return [_normalizar(raw) for raw in dados if raw]


def _normalizar(raw: dict) -> PeticaoItem:
    """Converte dict da API em PeticaoItem."""
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
# FUNCOES AUXILIARES — extracao de documentos
# ============================================================================

def _abrir_documento_peticao(driver: WebDriver, peticao) -> Optional[Any]:
    """Localiza o link viewer pelo id_item no mat-card da timeline."""
    id_doc = getattr(peticao, 'id_item', '') or ''
    if not id_doc:
        logger.error("[PET_ANALISE] id_item ausente — nao e possivel localizar o documento")
        return None

    aguardar_renderizacao_nativa(driver, 'mat-card', modo='aparecer', timeout=8)
    card = esperar_elemento(
        driver,
        f'//mat-card[.//a[contains(@href, "/documento/{id_doc}/")]]',
        timeout=10,
        by=By.XPATH,
    )
    if not card:
        logger.error("[PET_ANALISE] mat-card para documento/%s nao encontrado na timeline", id_doc)
        return None

    for sel in ('a.tl-documento[accesskey="v"]', 'a.tl-documento[role="button"]',
                'a.tl-documento:not([target="_blank"])'):
        try:
            return card.find_element(By.CSS_SELECTOR, sel)
        except Exception:
            continue
    logger.error("[PET_ANALISE] Link viewer nao encontrado no card de documento/%s", id_doc)
    return None


def _extrair_texto_doc_pet(driver: WebDriver, link) -> Optional[str]:
    """Clica no link, aguarda renderizacao e extrai texto."""
    link.click()
    try:
        aguardar_renderizacao_nativa(
            driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2
        )
    except Exception:
        pass

    try:
        resultado = extrair_direto(driver, timeout=10, debug=False, formatar=True)
        if resultado and resultado.get('sucesso'):
            texto = (resultado.get('conteudo') or resultado.get('conteudo_bruto') or '')
            if texto:
                texto = texto.lower()
            else:
                texto = None
        else:
            texto_str = extrair_documento(driver, regras_analise=None, timeout=10, log=False)
            if texto_str:
                texto = texto_str.lower()
            else:
                texto = None
    except Exception as e:
        logger.error("Erro ao extrair texto da peticao: %s", e)
        texto = None

    return texto


def extrair_texto_peticao_via_api(driver: WebDriver, peticao) -> Optional[str]:
    """Extrai o texto da peticao via API PJe sem interacao com a timeline."""
    id_doc = getattr(peticao, 'id_item', '') or ''
    id_proc = getattr(peticao, 'id_processo', '') or ''
    if not id_doc or not id_proc:
        logger.debug("[PET_API] id_item ou id_processo ausente — sem extracao via API")
        return None

    try:
        from Andrei.api_client import session_from_driver, PjeApiClient
        import pdfplumber  # type: ignore[import-untyped]
    except ImportError as e:
        logger.debug("[PET_API] Dependencia ausente para extracao via API: %s", e)
        return None

    try:
        sess, trt_host = session_from_driver(driver)
        client = PjeApiClient(sess, trt_host)
        url = client._url(
            f'/pje-comum-api/api/processos/id/{id_proc}/documentos/id/{id_doc}/conteudo'
        )
        resp = sess.get(url, timeout=30)

        if resp.status_code == 401:
            logger.warning("[PET_API] 401 na API — sessao expirada, usando fallback Selenium")
            return None
        if not resp.ok:
            logger.debug("[PET_API] HTTP %s ao buscar conteudo do doc %s", resp.status_code, id_doc)
            return None
        if 'pdf' not in resp.headers.get('Content-Type', '').lower():
            logger.debug("[PET_API] Resposta nao e PDF — usando fallback Selenium")
            return None

        textos = []
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            for pag in pdf.pages:
                t = pag.extract_text()
                if t:
                    textos.append(t)

        texto = '\n'.join(textos).strip()
        if not texto:
            logger.debug("[PET_API] PDF sem texto nativo — usando fallback Selenium")
            return None

        logger.info("[PET_API] Texto extraido via API: %d chars (doc=%s)", len(texto), id_doc)
        return texto.lower()

    except Exception as e:
        logger.debug("[PET_API] Falha na extracao via API: %s", e)
        return None


# ============================================================================
# ANALISE DE PETICAO
# ============================================================================

def analise_pet(driver: WebDriver, peticao) -> bool:
    """Analise de peticao: extrai texto via API ou Selenium, aplica regras."""
    logger.info("[PET_ANALISE] Iniciando analise_pet — %s", peticao.numero_processo)

    try:
        extrair_dados_processo(driver, caminho_json=_CAMINHO_DADOS, debug=False)
    except Exception as e:
        logger.warning("[PET_ANALISE] Falha ao extrair dados: %s", e)

    texto = extrair_texto_peticao_via_api(driver, peticao)

    if not texto:
        logger.info("[PET_ANALISE] Fallback Selenium")
        link = _abrir_documento_peticao(driver, peticao)
        if not link:
            logger.error("[PET_ANALISE] Nenhum documento encontrado")
            return False
        texto = _extrair_texto_doc_pet(driver, link)

    if not texto:
        logger.error("[PET_ANALISE] Falha na extracao de conteudo")
        return False

    dados = _dados()
    acao_analise = _detectar_acao_analise(texto, dados)
    if acao_analise == 'flag_apagar':
        logger.warning("[PET_ANALISE] flag_apagar — sinalizar para apagar")
        return False
    if acao_analise:
        try:
            if _executar_acao(driver, peticao, acao_analise):
                return True
        except Exception as e:
            logger.error("[PET_ANALISE] Erro ao executar acao: %s", e)

    logger.info("[PET_ANALISE] Fallback: criando GIGS (sem filtro reconhecido)")
    try:
        criar_gigs(driver, '', '', 'Analise - sem filtro reconhecido')
        return True
    except Exception as e:
        logger.error("[PET_ANALISE] Erro ao criar GIGS fallback: %s", e)
    return False


# ============================================================================
# CLASSIFICACAO E ABERTURA DE PROCESSO
# ============================================================================

def _classificar(itens: List) -> Dict[str, list]:
    """Classifica itens em buckets usando o registry de regras."""
    buckets: Dict[str, list] = {nome: [] for nome in BUCKETS_ORDEM}
    for item in itens:
        bucket = classificar(item)
        buckets.setdefault(bucket, []).append(item)
    return buckets


def _abrir_processo(driver: WebDriver, item) -> bool:
    """Abre o processo no PJe pelo id_processo ou numero."""
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


# ============================================================================
# EXECUCAO POR BUCKET
# ============================================================================

def _executar_bucket_normal(driver: WebDriver, nome: str, itens: list) -> Dict[str, int]:
    """Buckets que requerem abertura individual do processo."""
    stats = {'sucesso': 0, 'erro': 0}

    for item in itens:
        acao = resolver_acao(item, driver)

        if not acao:
            logger.warning("[PET_EXEC] Sem acao para %s em '%s'",
                           getattr(item, 'numero_processo', '?'), nome)
            continue

        logger.info("[PET_EXEC] %s | %s | %s", nome,
                    getattr(item, 'numero_processo', '?'),
                    getattr(item, 'tipo_peticao', '?'))
        try:
            _abrir_processo(driver, item)
            extrair_dados_processo(driver, caminho_json=_CAMINHO_DADOS, debug=False)
            ok = _executar_acao(driver, item, acao)
            if ok:
                stats['sucesso'] += 1
            else:
                stats['erro'] += 1
        except RuntimeError:
            raise
        except Exception as e:
            logger.error("[PET_EXEC] %s: %s", getattr(item, 'numero_processo', '?'), e)
            stats['erro'] += 1
        finally:
            fechar_abas_extras(driver)

    return stats


def _executar_bucket_analise(driver: WebDriver, itens: list) -> Dict[str, int]:
    """Analise: sempre chama analise_pet para cada item."""
    stats = {'sucesso': 0, 'erro': 0}
    for item in itens:
        logger.info("[PET_EXEC] analise | %s | %s",
                    getattr(item, 'numero_processo', '?'),
                    getattr(item, 'tipo_peticao', '?'))
        try:
            _abrir_processo(driver, item)
            extrair_dados_processo(driver, caminho_json=_CAMINHO_DADOS, debug=False)
            ok = analise_pet(driver, item)
            if ok:
                stats['sucesso'] += 1
            else:
                stats['erro'] += 1
        except RuntimeError:
            raise
        except Exception as e:
            logger.error("[PET_EXEC] analise %s: %s",
                         getattr(item, 'numero_processo', '?'), e)
            stats['erro'] += 1
        finally:
            fechar_abas_extras(driver)
    return stats


def _executar_bucket_apagar(itens: list) -> Dict[str, int]:
    """Apagar: sem abertura de processo, registra em delete.js."""
    stats = {'sucesso': 0, 'erro': 0}
    for item in itens:
        try:
            apagar(getattr(item, 'numero_processo', ''), getattr(item, 'id_item', ''))
            logger.info("[PET_APAG] %s | id_doc=%s",
                        getattr(item, "numero_processo", "?"),
                        getattr(item, "id_item", "?"))
            stats['sucesso'] += 1
        except Exception as e:
            logger.error("[PET_APAG] %s: %s", getattr(item, "numero_processo", "?"), e)
            stats['erro'] += 1
    return stats


# ============================================================================
# BOOKMARKLET — consolidacao de delete.js
# ============================================================================

def extrair_processos_delete():
    """Extrai processos de delete.js no diretorio Andrei/."""
    delete_file = Path(__file__).parent / "delete.js"
    if not delete_file.exists():
        logger.error("delete.js nao encontrado em %s", delete_file)
        return {}

    delete_processes = {}
    try:
        with open(delete_file, 'r', encoding='utf-8') as f:
            content = f.read()

        start_marker = 'const delete_processes = {'
        end_marker = '};'
        start = content.find(start_marker)
        if start != -1:
            start += len(start_marker)
            end = content.find(end_marker, start)
            if end != -1:
                json_str = content[start:end].strip()
                if json_str:
                    if not json_str.startswith('{'):
                        json_str = '{' + json_str + '}'
                    try:
                        delete_processes = json.loads(json_str)
                    except Exception:
                        pass

        if not delete_processes:
            for linha in content.split('\n'):
                linha = linha.strip()
                if linha and not linha.startswith('//') and not linha.startswith('javascript:'):
                    try:
                        dado = json.loads(linha)
                        if isinstance(dado, dict):
                            delete_processes.update(dado)
                    except Exception:
                        if linha.isdigit():
                            delete_processes[linha] = True

    except Exception as e:
        logger.error("Erro ao ler delete.js: %s", e)

    return delete_processes


def gerar_bookmarklet_apagar(processos):
    """Gera bookmarklet JavaScript com os processos extraidos."""
    delete_json = json.dumps(processos, ensure_ascii=False, separators=(',', ':'))
    checkbox_selector = json.dumps(
        'input[type="checkbox"], mat-checkbox input, input.mat-checkbox-input',
        ensure_ascii=False,
    )

    bookmarklet = (
        'javascript:(function(){'
        'const dp=' + delete_json + ';'
        'function norm(s){return(s||"").toLowerCase().trim();}'
        'function sub(a,b){return!b||a.includes(b)||b.includes(a);}'
        'function matchLinha(num,tipoHtml,descHtml,hrefHtml){'
        'var entradas=dp[num];'
        'if(!entradas)return false;'
        'if(!Array.isArray(entradas))return true;'
        'return entradas.some(function(e){'
        'if(e.id_doc){'
        'return hrefHtml.includes("/"+e.id_doc+"/");'
        '}'
        'var t=norm(e.tipo),d=norm(e.desc);'
        'return sub(tipoHtml,t)&&sub(descHtml,d);'
        '});'
        '}'
        'console.log("[DEL] Iniciando selecao...");'
        'var linhas=document.querySelectorAll("tr.cdk-drag,tr[data-row],tr.ng-star-inserted");'
        'var selecionados=0;'
        'linhas.forEach(function(linha){'
        'try{'
        'var a=linha.querySelector("pje-descricao-processo a,td pje-descricao-processo a");'
        'if(!a||!a.textContent)return;'
        'var num=a.textContent.trim();'
        'if(!dp.hasOwnProperty(num))return;'
        'var eTipo=linha.querySelector("span.texto-preto");'
        'var tipoHtml=eTipo?norm(eTipo.textContent):"";'
        'var aDesc=linha.querySelector("a[accesskey=\\"v\\"] span");'
        'var descHtml=aDesc?norm(aDesc.textContent):"";'
        'var aVis=linha.querySelector("a[accesskey=\\"v\\"]");'
        'var hrefHtml=aVis?(aVis.href||aVis.getAttribute("href")||""):"";'
        'if(!matchLinha(num,tipoHtml,descHtml,hrefHtml))return;'
        'var cb=linha.querySelector(' + checkbox_selector + ');'
        'if(cb){cb.click();selecionados++;'
        'var docId=hrefHtml.match(/\\/documento\\/(\\d+)\\//);'
        'console.log("[DEL] OK:",num,"| doc_id:",docId?docId[1]:"?","| tipo:",tipoHtml);}'
        '}catch(e){console.error("[DEL] erro linha:",e);}'
        '});'
        'alert("Selecionados: "+selecionados+"\\nClique no lixao para remover.");'
        '})();'
    )
    return bookmarklet


def consolidar_delete_com_bookmarklet():
    """Consolida delete.js e insere bookmarklet ao final."""
    processos = extrair_processos_delete()
    if not processos:
        logger.warning("Nenhum processo encontrado em delete.js")
        return False

    logger.info("Processos extraidos: %s", len(processos))
    bookmarklet = gerar_bookmarklet_apagar(processos)

    delete_file = Path(__file__).parent / "delete.js"
    with open(delete_file, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    linhas_limpas = [
        l for l in conteudo.split('\n')
        if not l.strip().startswith('javascript:')
    ]
    conteudo_novo = '\n'.join(linhas_limpas).rstrip() + '\n' + bookmarklet + '\n'

    with open(delete_file, 'w', encoding='utf-8') as f:
        f.write(conteudo_novo)

    logger.info("Bookmarklet inserido ao final de delete.js")
    logger.info("Arquivo: %s", delete_file.absolute())
    return True


# ============================================================================
# ANDREIORQUESTRADOR
# ============================================================================

class AndreiOrquestrador:
    """Orquestrador do pipeline de peticoes."""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.itens: List[PeticaoItem] = []
        self.buckets: Dict[str, list] = {}

    def carregar_itens(self) -> List[PeticaoItem]:
        """Carrega peticoes do escaninho via PeticaoAPIClient."""
        self.itens = PeticaoAPIClient().fetch(self.driver)
        logger.info("[PET_ORQ] %d peticoes carregadas", len(self.itens))
        return self.itens

    def classificar_itens(self) -> Dict[str, list]:
        """Classifica itens em buckets."""
        self.buckets = _classificar(self.itens)
        logger.info("[PET_ORQ] Distribuicao por bucket:")
        for nome in ['apagar'] + BUCKETS_ORDEM:
            qtd = len(self.buckets.get(nome, []))
            if qtd:
                logger.info("  %s: %d", nome, qtd)
        return self.buckets

    def executar(self, dry_run: bool = False) -> Dict[str, int]:
        """Executa o pipeline completo de peticoes.

        Args:
            dry_run: Se True, apenas carrega e classifica sem executacoes.

        Returns:
            Dict com total, sucesso, erro.
        """
        logger.info("=" * 60)
        logger.info("[PET_ORQ] Iniciando pipeline peticoes")

        self.carregar_itens()
        if not self.itens:
            logger.info("[PET_ORQ] Nenhuma peticao encontrada")
            return {'total': 0, 'sucesso': 0, 'erro': 0}

        self.classificar_itens()

        if dry_run:
            return {'total': len(self.itens), 'sucesso': 0, 'erro': 0}

        # Apagar: executa imediatamente, sem abrir processos
        apagar_itens = self.buckets.get('apagar', [])
        if apagar_itens:
            logger.info("[PET_ORQ] Apagar: %d itens -> delete.js", len(apagar_itens))
            _executar_bucket_apagar(apagar_itens)

        # Executar sempre na ordem padrao dos buckets
        ordem = [n for n in BUCKETS_ORDEM if self.buckets.get(n)]
        stats = {'total': len(self.itens), 'sucesso': 0, 'erro': 0}

        for nome_bucket in ordem:
            itens_bucket = self.buckets.get(nome_bucket, [])
            if not itens_bucket:
                continue
            logger.info("\n[PET_ORQ] >>> Bucket \"%s\" (%d itens)", nome_bucket, len(itens_bucket))
            try:
                if nome_bucket == 'analise':
                    r = _executar_bucket_analise(self.driver, itens_bucket)
                else:
                    r = _executar_bucket_normal(self.driver, nome_bucket, itens_bucket)
                stats['sucesso'] += r['sucesso']
                stats['erro'] += r['erro']
            except RuntimeError as e:
                if 'RESTART_PET' in str(e):
                    logger.error("[RESTART] %s", e)
                    raise
                stats['erro'] += 1

        logger.info("\n[PET_ORQ] Total: %d | Sucesso: %d | Erro: %d",
                    stats["total"], stats["sucesso"], stats["erro"])

        if apagar_itens:
            logger.info('[PET_ORQ] Consolidando delete.js e gerando bookmarklet')
            consolidar_delete_com_bookmarklet()

        logger.info("=" * 60)
        return stats


def executar_fluxo_pet(driver: WebDriver) -> bool:
    """Entry point do pipeline de peticoes (compativel com x.py)."""
    try:
        orq = AndreiOrquestrador(driver)
        stats = orq.executar()
        return stats['erro'] == 0
    except RuntimeError as e:
        if 'RESTART_PET' in str(e):
            raise
        logger.error("[PET_FLUXO] Erro fatal: %s", e)
        return False


# ============================================================================
# run_pet — entrada principal
# ============================================================================

def run_pet(driver: Optional[WebDriver] = None) -> dict:
    """Cria driver, faz login e executa o pipeline completo de peticoes.

    Args:
        driver: WebDriver opcional ja logado. Se None, cria novo.

    Returns:
        Dict com resultado da execucao (ok, erro, dados, sucesso).
    """
    # NOTA: Se o driver cair durante execucao, recovery requer login manual.
    # Nao suporta execucao desassistida por enquanto.
    configurar_recovery_driver(criar_driver, aguardar_login_manual)

    if driver is None:
        driver = criar_driver_e_logar()
        if driver is None:
            logger.error("[PET] Falha ao obter driver (abortando)")
            return resultado_falha("Falha ao obter driver", sucesso=False)

    logger.info("[PET] Navegando para %s", ESCANINHO_URL)
    try:
        driver.get(ESCANINHO_URL)
    except Exception:
        try:
            driver.quit()
        except Exception:
            pass
        logger.warning("[PET] Driver caiu ao navegar; recriando sessao...")
        driver = criar_driver_e_logar()
        if driver is None:
            logger.error("[PET] Falha ao recuperar driver")
            return resultado_falha("Falha ao recuperar driver", sucesso=False)
        driver.get(ESCANINHO_URL)

    try:
        ok = executar_fluxo_pet(driver)
        if ok:
            return resultado_ok(sucesso=True)
        return resultado_falha("executar_fluxo_pet retornou False", sucesso=False)
    except Exception as e:
        novo_driver = handle_exception_with_recovery(e, driver, 'PET_RUN')
        if novo_driver:
            logger.warning("[PET] Acesso negado detectado; driver recuperado, reiniciando fluxo...")
            try:
                ok = executar_fluxo_pet(novo_driver)
                if ok:
                    return resultado_ok(sucesso=True)
                return resultado_falha(
                    "executar_fluxo_pet retornou False apos recuperacao", sucesso=False
                )
            except Exception as e2:
                logger.error("[PET] Falha ao reiniciar fluxo apos recuperacao: %s", e2)
                return resultado_falha(str(e2), sucesso=False)
        logger.error("[PET] Erro geral no run_pet: %s", e)
        return resultado_falha(str(e), sucesso=False)


# ============================================================================
# MAIN GUARD
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("[PET] Executando como script")
    run_pet()
