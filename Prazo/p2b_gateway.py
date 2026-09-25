"""Prazo P2B - Gateway (API + Fluxo + Helpers)

Consolidado de: fluxo_api.py, p2b_api.py, p2b_fluxo.py, p2b_fluxo_helpers.py

Entrypoints publicos:
    testar_gigs_sem_prazo()
    processar_gigs_sem_prazo_p2b()
"""

# ── Imports ──
import importlib.util
import io
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from Fix import espera

# Dependencias externas do modulo Prazo
from .p2b_core import (
    carregar_progresso_p2b, marcar_processo_executado_p2b, normalizar_texto,
    parse_gigs_param, processo_ja_executado_p2b,
)
from .p2b_documentos import _fechar_aba_processo
from .p2b_fluxo_lazy import _lazy_import
from .p2b_fluxo_prescricao import prescreve, analisar_timeline_prescreve_js_puro
from .p2b_documentos import _definir_regras_processamento, _processar_regras_gerais

# Fallback para extrair_dados_processo
try:
    from Fix.extracao import extrair_dados_processo
except Exception:
    extrair_dados_processo = None

logger = logging.getLogger(__name__)

from Fix.variaveis import cliente_para, session_from_driver, url_processo_detalhe
from Fix import espera


class SessaoExpiradaError(Exception):
    """Lançada quando a API retorna 401 — sessão expirada."""
    pass


# ═══════════════════════════════════════════
# 1. p2b_api.py
# ═══════════════════════════════════════════

_TIPOS_RELEVANTES = re.compile(r'^(despacho|decis[aã]o|senten[cç]a|conclus[aã]o)', re.IGNORECASE)


def extrair_documento_relevante(driver: Any) -> Dict[str, Any]:
    """Extrai o primeiro documento relevante via API (/timeline + /documentos/.../conteudo).

    Retorna dict com chaves: sucesso, conteudo, tipo, titulo, id_documento, id_processo, erro
    """

    # 1) obter id_processo da URL
    m = re.search(r'/processo/(\d+)', driver.current_url)
    if not m:
        return _falha('id_processo não detectado na URL: ' + driver.current_url)
    id_processo = m.group(1)

    sess, host = session_from_driver(driver)
    base = f'https://{host}'

    # 2) timeline via API (retry curto para 5xx transitórios do PJe)
    url_timeline = (
        f'{base}/pje-comum-api/api/processos/id/{id_processo}/timeline'
        '?buscarDocumentos=true&buscarMovimentos=false&somenteDocumentosAssinados=false'
    )
    timeline = None
    ultimo_erro = None
    for tentativa in range(3):
        try:
            r = sess.get(url_timeline, timeout=30)
            if r.status_code == 401:
                return _falha('sessao_expirada_401', sessao_expirada=True)
            r.raise_for_status()
            timeline = r.json()
            break
        except Exception as e:
            ultimo_erro = e
            if tentativa < 2:
                espera.assentar(driver, 3, motivo='retry timeline API')
    if timeline is None:
        return _falha(f'timeline HTTP error: {ultimo_erro}')

    doc = next((i for i in timeline if _TIPOS_RELEVANTES.match((i.get('tipo') or '').strip())), None)
    if not doc:
        tipos = list({i.get('tipo', '?') for i in timeline})
        return _falha(f'nenhum documento relevante na timeline. Tipos: {tipos}')

    id_doc = str(doc.get('id') or doc.get('idDocumento') or '')
    tipo = doc.get('tipo', '')
    titulo = doc.get('titulo', '')
    
    # 2.5) Verifica a data do documento (se for < 5 dias, pular)
    data_str = doc.get('dataJuntada') or doc.get('dataCadastro') or doc.get('data')
    dias_idade = None
    if data_str:
        try:
            from datetime import datetime, timezone, timedelta
            from PEC.runtime_pec import _carregar_calendario_dias_uteis
            
            data_str_clean = data_str.replace('Z', '+00:00')
            dt_doc = datetime.fromisoformat(data_str_clean)
            if dt_doc.tzinfo is None:
                dt_doc = dt_doc.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            
            dias_calendario, intervalo = _carregar_calendario_dias_uteis()
            data_atual = dt_doc.date()
            data_fim = now.date()
            
            dias_uteis = 0
            while data_atual < data_fim:
                data_atual += timedelta(days=1)
                dentro_intervalo = intervalo and intervalo[0] <= data_atual <= intervalo[1]
                if dias_calendario and dentro_intervalo:
                    if data_atual in dias_calendario:
                        dias_uteis += 1
                else:
                    if data_atual.weekday() < 5:
                        dias_uteis += 1
                        
            dias_idade = dias_uteis
            logger.info(f'[p2b_api] Data documento: {data_str} -> {dt_doc.isoformat()} (Idade: {dias_idade} dias úteis)')
            
            if dias_idade <= 5:
                logger.info(f'[p2b_api] doc relevante ({tipo}) tem data recente ({data_str}), pulando (<= 5 dias úteis).')
                return _falha('decisao_recente_menos_5_dias', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo, decisao_recente=True, data_extraida=data_str, idade_dias=dias_idade)
        except Exception as e:
            logger.warning(f'[p2b_api] erro ao calcular data do doc {data_str}: {e}')
            
    logger.info(f'[p2b_api] doc relevante: tipo={tipo} id={id_doc} data_extraida={data_str} idade_dias={dias_idade}')

    # 3) download do conteúdo (PDF esperado)
    url_conteudo = f'{base}/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo'
    try:
        r = sess.get(url_conteudo, timeout=60, stream=True)
        r.raise_for_status()
        pdf_bytes = r.content
    except Exception as e:
        return _falha(f'/conteudo download error: {e}', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo)

    if not pdf_bytes or not pdf_bytes.startswith(b'%PDF'):
        return _falha(
            f'/conteudo não é PDF. Content-Type={r.headers.get("content-type")} primeiros bytes={pdf_bytes[:20]!r}',
            id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo,
        )

    # 4) extrair via pdfplumber
    try:
        import pdfplumber
    except Exception:
        return _falha('pdfplumber não instalado. Execute: pip install pdfplumber', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo)

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            paginas = [p.extract_text() or '' for p in pdf.pages]
        texto = '\n\n--- PÁGINA ---\n\n'.join(paginas).strip()
    except Exception as e:
        return _falha(f'pdfplumber erro: {e}', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo)

    if not texto or len(texto) < 20:
        return _falha('PDF sem texto extraível (possivelmente escaneado)', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo)

    logger.info(f'[p2b_api] texto extraído: {len(texto)} chars')
    return {
        'sucesso': True,
        'conteudo': texto,
        'tipo': tipo,
        'titulo': titulo,
        'id_documento': id_doc,
        'id_processo': id_processo,
        'erro': None,
        'data_extraida': data_str,
        'idade_dias': dias_idade,
    }


def _falha(msg: str, **extra) -> Dict[str, Any]:
    logger.warning(f'[p2b_api] {msg}')
    return {'sucesso': False, 'conteudo': None, 'tipo': None, 'titulo': None, 'id_documento': None, 'id_processo': None, 'erro': msg, **extra}


def processar_processo_por_id_api(driver: Any, id_processo: int, host: str = 'pje.trt2.jus.br') -> Dict[str, Any]:
    """Abre detalhe do processo e tenta localizar+extrair documento relevante.

    Retorna dicionário com o resultado da extração e metadados.
    """
    detalhe_url = f'https://{host}/pjekz/processo/{id_processo}/detalhe/'
    logger.info(f'[P2B_API] Abrindo processo id={id_processo} url={detalhe_url}')

    try:
        driver.get(detalhe_url)
    except Exception as e:
        return {'sucesso': False, 'erro': 'nav_failure', 'mensagem': str(e)}

    # pequena espera para carregar timeline
    espera.assentar(driver, 1.5)

    # Usar exclusivamente o pipeline API-based (timeline -> conteudo -> pdfplumber)
    try:
        resultado = extrair_documento_relevante(driver)
    except Exception as e:
        return {'sucesso': False, 'erro': 'extracao_exception', 'mensagem': str(e)}

    if not resultado or not resultado.get('sucesso'):
        return {'sucesso': False, 'erro': 'nenhum_documento_relevante', 'info': resultado}

    return {
        'sucesso': True,
        'metodo': 'api_pdfplumber',
        'conteudo': resultado.get('conteudo'),
        'info': {k: v for k, v in resultado.items() if k not in ('conteudo',)},
        'indice': 0,
    }


# ═══════════════════════════════════════════
# 2. p2b_fluxo_helpers.py
# ═══════════════════════════════════════════

GIGS_API_MAX_WORKERS = 20


def _abrir_tarefa_e_tentar_iniciar_execucao(driver: Any, timeout: int = 10) -> bool:
    """Abre a tarefa mais recente usando o helper geral do projeto e clica em 'Iniciar execução' se existir."""
    url_atual = driver.current_url or ''
    if '/tarefa/' not in url_atual:
        try:
            from atos.movimentos_fluxo import abrir_tarefa_por_api

            if not abrir_tarefa_por_api(driver, timeout=timeout):
                return False
        except Exception as e:
            logger.warning('[FLUXO_PZ] inicar_exec: falha ao abrir tarefa via helper geral: %s', e)
            return False

    try:
        from Fix.core import aguardar_renderizacao_nativa, safe_click_no_scroll
        seletor = "button[aria-label='Iniciar execução'], button[aria-label='Iniciar execucao']"
        aguardar_renderizacao_nativa(driver, seletor, modo='aparecer', timeout=min(8, timeout))

        btn = espera.elemento(driver, seletor, teto=min(8, timeout))
        if btn:
            is_disabled = (
                btn.get_attribute('disabled') is not None
                or 'mat-button-disabled' in (btn.get_attribute('class') or '')
                or getattr(btn, 'is_enabled', lambda: True)() is False
            )
            if not is_disabled:
                safe_click_no_scroll(driver, btn)
                try:
                    aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', modo='aparecer', timeout=min(6, timeout))
                except Exception:
                    pass
                return True
            else:
                logger.info('[FLUXO_PZ] inicar_exec: botão "Iniciar execução" detectado, porém inativo')
                return False
        return False
    except Exception:
        return False


def _abrir_tarefa(driver: Any, timeout: int = 10) -> bool:
    """Abre a tarefa mais recente na mesma aba, sem clicar em "Iniciar execução".

    Usado nos caminhos em que a execução NÃO deve ser iniciada (ex.: liquidação
    ainda não homologada, que roda o wrapper de liquidação).
    """
    if '/tarefa/' in (getattr(driver, 'current_url', '') or ''):
        return True
    try:
        from atos.movimentos_fluxo import abrir_tarefa_por_api
        return bool(abrir_tarefa_por_api(driver, timeout=timeout))
    except Exception as e:
        logger.warning('[FLUXO_PZ] inicar_exec: falha ao abrir tarefa: %s', e)
        return False


def obter_fase_processual(driver, caminho_json: str = 'dadosatuais.json', debug: bool = False) -> Optional[str]:
    """
    Extrai dados do processo via `extrair_dados_processo` (Fix.extracao) e retorna
    o valor de `labelFaseProcessual` presente em `caminho_json`.

    Retorna `None` em caso de falha ou se o campo não existir.
    """
    try:
        if extrair_dados_processo:
            extrair_dados_processo(driver, caminho_json=caminho_json, debug=debug)
    except Exception as e:
        logger.debug(f'[FLUXO_PZ] extrair_dados_processo falhou: {e}')

    p = Path(caminho_json)
    if not p.exists():
        logger.debug(f'[FLUXO_PZ] obter_fase_processual: {caminho_json} não encontrado')
        return None

    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        fase = data.get('labelFaseProcessual')
        if isinstance(fase, str):
            return fase.strip()
        return None
    except Exception as e:
        logger.debug(f'[FLUXO_PZ] Erro ao ler {caminho_json}: {e}')
        return None


# Movimento CNJ que homologa a liquidação (api/apis.md §5) — define o roteamento
MOV_HOMOLOGADA_LIQUIDACAO = 50047

# GIGS criada quando a liquidação homologada ainda não tem crédito registrado
GIGS_OBS_REGISTRAR_OBRIGACAO = 'registrar obrigação'
CREDITO_MOCK = '0,01'
SCRIPTS_DIR = Path(__file__).parent / 'scripts'


def _tem_homologacao_liquidacao(client, id_processo: str) -> bool:
    """True se a timeline tem o movimento 50047 (Homologada a Liquidação)."""
    itens = client.timeline(id_processo, buscarDocumentos=False, buscarMovimentos=True) or []
    for item in itens:
        try:
            if int(item.get('codEvento') or 0) == MOV_HOMOLOGADA_LIQUIDACAO:
                return True
        except (TypeError, ValueError):
            pass
        if 'homologada a liquidacao' in normalizar_texto(str(item.get('titulo') or '')):
            return True
    return False


def decidir_rota_iniciar_exec(client, id_processo: str) -> Optional[str]:
    """Decide o caminho do `inicar_exec` só com API — sem checar botão.

    - fase já é execução                                       → 'pesquisas'
    - fase liquidação/homologação SEM movimento 50047           → 'pesqliq'
    - liquidação homologada (50047) COM obrigações registradas  → 'executar_pesquisas'
    - liquidação homologada (50047) SEM obrigações registradas  → 'mock_pesquisas'

    Devolve `None` quando a API não responde ou a fase não é reconhecida — nesse
    caso o chamador cai no fallback antigo (botão "Iniciar execução" + fase do
    `dadosatuais.json`).
    """
    try:
        dados = client.processo_por_id(id_processo) or {}
        fase = str(dados.get('labelFaseProcessual') or dados.get('faseProcessual') or '').lower()

        if 'execu' in fase:
            return 'pesquisas'

        if 'liquid' in fase or 'homolog' in fase:
            if not _tem_homologacao_liquidacao(client, id_processo):
                return 'pesqliq'
            obrigacoes = client.obrigacoes_pagar(id_processo)
            if isinstance(obrigacoes, list) and obrigacoes:
                return 'executar_pesquisas'
            return 'mock_pesquisas'

        logger.info('[FLUXO_PZ] inicar_exec: fase processual nao reconhecida (%r)', fase)
    except Exception as e:
        logger.warning('[FLUXO_PZ] inicar_exec: decisao por API falhou: %s', e)
    return None


def _preencher_credito_mock_js(driver: Any, valor: str, placeholder: str = 'Crédito do demandante') -> bool:
    """Preenche o campo monetário com a estratégia de teclado do `debito.js`."""
    page = getattr(driver, 'page', None)
    if page is None:
        logger.warning('[FLUXO_PZ] credito_mock: driver sem page (motor nao suportado)')
        return False

    try:
        from Fix.scripts import carregar_js
        script = carregar_js('credito_mock.js', SCRIPTS_DIR)
    except Exception as e:
        logger.warning('[FLUXO_PZ] credito_mock: falha ao carregar JS: %s', e)
        return False
    if not script:
        logger.warning('[FLUXO_PZ] credito_mock: JS nao encontrado em %s', SCRIPTS_DIR)
        return False

    try:
        res = page.evaluate(script, {'valor': valor, 'placeholder': placeholder}) or {}
    except Exception as e:
        logger.warning('[FLUXO_PZ] credito_mock: falha ao preencher "%s": %s', placeholder, e)
        return False

    if not res.get('ok'):
        logger.warning('[FLUXO_PZ] credito_mock: %s', res.get('motivo') or 'preenchimento falhou')
        return False
    logger.info('[FLUXO_PZ] credito_mock: "%s" = %s', placeholder, res.get('valor'))
    return True


def registrar_credito_mock_0_01(driver: Any, id_processo: str) -> bool:
    """Registra R$ 0,01 como crédito do demandante (obrigação de pagar).

    Replica o fluxo do `Script/modules/debito/registrar_debito.js`:
      /obrigacao-pagar/{id}/cadastro → marca Credor e Devedor → Próximo →
      /inclusao → Data do Cálculo (hoje) + Crédito do demandante (0,01) → Salvar,
    e fecha a aba de obrigações ao final.
    """
    from urllib.parse import urlparse
    from datetime import datetime
    from Fix.browser_suporte import abrir_url_nova_aba, forcar_fechamento_abas_extras
    from Fix.core import safe_click_no_scroll, preencher_campo

    aba_principal = getattr(driver, 'current_window_handle', None)
    host = urlparse(getattr(driver, 'current_url', '') or '').netloc
    if not host:
        logger.warning('[FLUXO_PZ] credito_mock: host nao detectado na URL atual')
        return False

    url = f'https://{host}/pjekz/obrigacao-pagar/{id_processo}/cadastro'
    if not abrir_url_nova_aba(driver, url):
        logger.warning('[FLUXO_PZ] credito_mock: falha ao abrir %s', url)
        return False

    try:
        # 1) /cadastro — marcar as partes (Credor e Devedor) e avançar
        if not espera.ate_aparecer(driver, 'table.t-class', teto=15):
            logger.warning('[FLUXO_PZ] credito_mock: tabela de partes nao apareceu')
            return False

        for papel in ('Credor', 'Devedor'):
            xpath = (
                "//tbody//tr[contains(@class,'tr-class')]"
                f"[.//span[contains(@class,'mat-select-min-line')][normalize-space(.)='{papel}']]"
                "//input[@type='checkbox']"
            )
            checkbox = espera.elemento(driver, xpath, teto=5)
            if checkbox:
                safe_click_no_scroll(driver, checkbox)
            else:
                logger.warning('[FLUXO_PZ] credito_mock: checkbox de %s nao encontrado', papel)

        btn_proximo = espera.elemento(driver, "//button[@name='proximo']", teto=10)
        if not btn_proximo:
            logger.warning('[FLUXO_PZ] credito_mock: botao Proximo nao encontrado')
            return False
        safe_click_no_scroll(driver, btn_proximo)

        # 2) /inclusao — Data do Cálculo (hoje) + Crédito do demandante (0,01)
        if not espera.ate_aparecer(driver, 'input[data-placeholder="Crédito do demandante"]', teto=20):
            logger.warning('[FLUXO_PZ] credito_mock: formulario de inclusao nao abriu')
            return False
        preencher_campo(
            driver,
            'input[data-placeholder="Data do Cálculo"]',
            datetime.now().strftime('%d/%m/%Y'),
        )
        if not _preencher_credito_mock_js(driver, CREDITO_MOCK):
            return False

        # 3) Salvar o registro
        btn_salvar = espera.elemento(driver, "//button[@name='salvar']", teto=10)
        if not btn_salvar:
            logger.warning('[FLUXO_PZ] credito_mock: botao Salvar nao encontrado')
            return False
        safe_click_no_scroll(driver, btn_salvar)
        espera.assentar(driver, 1.0, motivo='registro do credito mock')
        logger.info('[FLUXO_PZ] credito_mock: crédito %s registrado (processo %s)', CREDITO_MOCK, id_processo)
        return True
    except Exception as e:
        logger.error('[FLUXO_PZ] credito_mock: erro no registro: %s', e)
        return False
    finally:
        if aba_principal:
            forcar_fechamento_abas_extras(driver, aba_principal)


def inicar_exec(driver, texto_normalizado: Optional[str] = None):
    """Helper: cria duas GIGS padrão, decide a rota por API e executa o wrapper.

    1) cria GIG '1/Ana Lucia/Argos'  (try independente)
    2) cria GIG '1//xs sigilo'       (try independente — não bloqueado por falha do 1)
    3) rota decidida SÓ por API (`decidir_rota_iniciar_exec`):
       'pesquisas'          → fase já é execução: ato_pesquisas (caminho definido)
       'pesqliq'            → liquidação SEM movimento 50047: ato_pesqliq
       'executar_pesquisas' → liquidação homologada COM obrigações: inicia execução + ato_pesquisas
       'mock_pesquisas'     → liquidação homologada SEM obrigações: GIGS de observação +
                              crédito mock 0,01 → inicia execução + ato_pesquisas
       None                 → API indisponível: fallback (botão "Iniciar execução" + fase)

    Retorna o resultado da ação executada (tupla ou bool).
    """
    m = _lazy_import()
    criar_gigs = m.get('criar_gigs')
    ato_pesquisas = m.get('ato_pesquisas')
    ato_pesqliq = m.get('ato_pesqliq')
    resultado = (False, False)

    if texto_normalizado:
        logger.debug('[FLUXO_PZ] inicar_exec texto_normalizado comprimento=%d', len(texto_normalizado))

    # 1) GIGS Argos — try isolado
    if criar_gigs:
        try:
            d, r, o = parse_gigs_param('1/Ana Lucia/Argos')
            criar_gigs(driver, d, r, o)
        except Exception as e:
            logger.error('[FLUXO_PZ] inicar_exec: falha ao criar GIGS Argos: %s', e)

        # 2) GIGS xs sigilo — try isolado (não depende do anterior)
        try:
            d2, r2, o2 = parse_gigs_param('1//xs sigilo')
            criar_gigs(driver, d2, r2, o2)
        except Exception as e:
            logger.error('[FLUXO_PZ] inicar_exec: falha ao criar GIGS xs sigilo: %s', e)

    # 3) Rota decidida SÓ por API (fase + movimento 50047 + obrigações a pagar).
    id_processo = None
    rota = None
    try:
        from Fix.core import extrair_id_processo

        id_processo = extrair_id_processo(driver)
        if id_processo:
            rota = decidir_rota_iniciar_exec(cliente_para(driver), id_processo)
            logger.info('[FLUXO_PZ] inicar_exec: rota por API=%s (id_processo=%s)', rota, id_processo)
    except Exception as e:
        logger.warning('[FLUXO_PZ] inicar_exec: roteamento por API indisponivel (%s)', e)

    # 3.1) Fallback (API fora/fase desconhecida): abre a tarefa, tenta o botão
    #      "Iniciar execução" e roteia pela fase do dadosatuais.json (comportamento antigo).
    if rota is None:
        mov_ok = False
        try:
            mov_ok = _abrir_tarefa_e_tentar_iniciar_execucao(driver, timeout=10)
            if mov_ok:
                logger.info('[FLUXO_PZ] inicar_exec: Iniciar execução clicado com sucesso (fallback)')
            else:
                logger.info('[FLUXO_PZ] inicar_exec: Iniciar execução não disponível, roteando por fase (fallback)')
        except Exception as e:
            logger.info('[FLUXO_PZ] inicar_exec: checagem direta de Iniciar execução falhou (%s)', e)

        if mov_ok:
            rota = 'pesquisas'
        else:
            fase_lower = ''
            try:
                fase_lower = (obter_fase_processual(driver) or '').lower()
            except Exception:
                pass
            rota = 'pesqliq' if ('liquid' in fase_lower or 'homolog' in fase_lower) else 'pesquisas'

    # 3.2) Liquidação ainda não homologada → wrapper de liquidação.
    #      Aqui NÃO se clica "Iniciar execução": a execução não deve começar.
    if rota == 'pesqliq':
        _abrir_tarefa(driver)
        if ato_pesqliq:
            resultado = ato_pesqliq(driver, sigilo=True)
        return resultado

    # 3.3) Liquidação homologada SEM crédito registrado → GIGS de observação + mock 0,01.
    if rota == 'mock_pesquisas' and id_processo:
        if criar_gigs:
            try:
                criar_gigs(driver, observacao=GIGS_OBS_REGISTRAR_OBRIGACAO)
            except Exception as e:
                logger.error('[FLUXO_PZ] inicar_exec: falha ao criar GIGS "%s": %s',
                             GIGS_OBS_REGISTRAR_OBRIGACAO, e)
        registrar_credito_mock_0_01(driver, id_processo)

    # 3.4) Rotas de pesquisa: garante a tarefa aberta e roda o ato de pesquisas.
    #      Quando é caso de INICIAR a execução (liquidação homologada), tenta o botão;
    #      quando a fase já é execução, apenas abre a tarefa.
    try:
        if rota in ('executar_pesquisas', 'mock_pesquisas'):
            if not _abrir_tarefa_e_tentar_iniciar_execucao(driver, timeout=10):
                logger.info('[FLUXO_PZ] inicar_exec: botão "Iniciar execução" indisponível — seguindo para o ato')
        else:
            _abrir_tarefa(driver)
    except Exception as e:
        logger.info('[FLUXO_PZ] inicar_exec: abertura de tarefa falhou (%s) — seguindo para o ato', e)

    try:
        if ato_pesquisas:
            resultado = ato_pesquisas(driver, sigilo=True)
    except Exception as e:
        logger.error('[FLUXO_PZ] inicar_exec: erro ao executar ato_pesquisas: %s', e)

    # aplicar visibilidade se necessário
    try:
        sucesso, sigilo_ativado = resultado if isinstance(resultado, tuple) else (bool(resultado), False)
    except Exception:
        sucesso, sigilo_ativado = (False, False)

    # Visibilidade é aplicada pelo próprio `ato_judicial` quando o wrapper
    # foi configurado com `atribuir_visibilidade_autor=True`. Não executar
    # aqui para evitar duplicação.

    return resultado


# ═══════════════════════════════════════════
# 3. p2b_fluxo.py
# ═══════════════════════════════════════════


def fluxo_pz(driver: Any) -> None:
    """
    Processa prazos detalhados em processos abertos.

    Usa extrair_documento para obter texto, analisa regras,
    cria GIGS parametrizadas, executa atos sequenciais e fecha aba.

    Refatoração: 761→40 linhas, aninhamento 6→2 níveis
    Padrão: Orchestrator + 8 Helpers privados
    """
    # Extrai documento relevante através do pipeline API+pdfplumber
    resultado = extrair_documento_relevante(driver)
    if not resultado or not resultado.get('sucesso'):
        if (resultado or {}).get('sessao_expirada'):
            raise SessaoExpiradaError('API retornou 401 — sessao expirada')
            
        if (resultado or {}).get('decisao_recente'):
            logger.info('[FLUXO_PZ] Decisão recente (< 5 dias), executando mov_int Aguardando Prazo e pulando.')
            mov_ok = False
            try:
                from atos.movimentos_fluxo import movimentar_inteligente
                mov_ok = movimentar_inteligente(driver, 'Aguardando Prazo')
            except Exception as e:
                logger.error(f'[FLUXO_PZ] Erro ao mover processo para Aguardando Prazo (decisão recente): {e}')
                
            try:
                _fechar_aba_processo(driver)
            except Exception:
                pass
            
            # Se movimento falhou, retorna False; caso contrário, sucesso
            return bool(mov_ok)
            
        logger.info('[FLUXO_PZ] Nenhum documento relevante extraído: %s', (resultado or {}).get('erro'))
        try:
            _fechar_aba_processo(driver)
        except Exception:
            pass
        return False

    texto = resultado.get('conteudo') or ''

    # Formatar/extrair texto com utilitário se disponível
    try:
        from Fix.extracao import _extrair_formatar_texto
        texto_formatado = _extrair_formatar_texto(texto)
    except Exception:
        texto_formatado = texto

    # Normalizar e aplicar regras
    texto_normalizado = normalizar_texto(texto_formatado)
    try:
        resultado_regras = _processar_regras_gerais(driver, texto_normalizado, 0)
        # resultado_regras pode ser:
        # - True: regra casou e ações completaram com sucesso
        # - False: regra casou mas alguma ação falhou (ex: mov_arquivar retornou False)
        # - None: nenhuma regra casou
        # - tuple: resultado de checar_prox
        
        if resultado_regras is False:
            logger.warning('[FLUXO_PZ] Regra casou mas ação falhou (retornou False)')
            try:
                _fechar_aba_processo(driver)
            except Exception:
                pass
            return False
    except Exception as e:
        logger.error('[FLUXO_PZ] Erro ao processar regras: %s', e)
        try:
            _fechar_aba_processo(driver)
        except Exception:
            pass
        return False

    # Fechar aba/processo e retornar
    try:
        _fechar_aba_processo(driver)
    except Exception:
        pass

    return True


# ═══════════════════════════════════════════
# 4. fluxo_api.py
# ═══════════════════════════════════════════

_API_CORE_TYPES = None


def _api_core_types():
    global _API_CORE_TYPES
    if _API_CORE_TYPES is not None:
        return _API_CORE_TYPES

    core_path = Path(__file__).resolve().parents[1] / 'api' / 'variaveis_client.py'
    spec = importlib.util.spec_from_file_location('pjeplus_api_variaveis_client_runtime', str(core_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f'[PRAZO_API] Nao foi possivel carregar API Core: {core_path}')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _API_CORE_TYPES = (module.PjeApiClient, module.session_from_driver)
    return _API_CORE_TYPES


def _criar_api_client(driver):
    pje_api_client_cls, session_from_driver_fn = _api_core_types()
    sess, trt_host = session_from_driver_fn(driver)
    return pje_api_client_cls(sess, trt_host, grau=1)


def _buscar_relatorio_atividades(client, tamanho_pagina: int) -> List[dict]:
    params_base = {
        'filtrarAtividadesSemPrazo': 'false',
        'filtrarAtividadesSemPrazoConcluidas': 'false',
        'ordenacaoCrescente': 'true',
        'filtrarPorDestinatario': 'false',
        'filtrarPorLocalizacao': 'false',
    }

    itens_total: List[dict] = []
    pagina = 1
    limite_paginas = 200

    for _ in range(limite_paginas):
        params = dict(params_base)
        params['pagina'] = pagina
        params['tamanhoPagina'] = tamanho_pagina

        resposta = client.gateway_get('/pje-gigs-api/api/relatorioatividades/', params=params, timeout=20)
        if not resposta.get('ok'):
            erro = (resposta.get('error') or {}).get('message') or 'sem_resposta'
            raise RuntimeError(f"Fluxo API XS1 falhou: {erro}")

        payload = resposta.get('data')
        if isinstance(payload, dict):
            itens = payload.get('resultado') or payload.get('dados') or []
            qtd_paginas = payload.get('qtdPaginas') or payload.get('totalPaginas') or payload.get('totalPages')
            if not isinstance(itens, list):
                itens = []
        elif isinstance(payload, list):
            itens = payload
            qtd_paginas = None
        else:
            itens = []
            qtd_paginas = None

        itens_total.extend(itens)

        if isinstance(qtd_paginas, int):
            if pagina >= qtd_paginas:
                return itens_total
        elif len(itens) < tamanho_pagina:
            return itens_total

        pagina += 1

    raise RuntimeError(f"Fluxo API XS1 falhou: limite de paginas atingido ({limite_paginas})")


def gerar_script_gigs_xs1(tamanho_pagina: int = 100) -> str:
    """Compatibilidade legado: script JS descontinuado, fluxo usa API Core em Python."""
    return "// Deprecated: use testar_gigs_xs1(driver, tamanho_pagina)"


def testar_gigs_xs1(driver, tamanho_pagina: int = 100) -> List[dict]:
    """Retorna atividades XS1 via API Core (gateway + paginacao compartilhada)."""
    client = _criar_api_client(driver)
    all_items = _buscar_relatorio_atividades(client, tamanho_pagina=tamanho_pagina)

    xs1 = []
    for item in all_items:
        tipo_obj = item.get('tipoAtividade') or {}
        tipo = tipo_obj.get('descricao') or tipo_obj.get('nome') or ''
        observacao = str(item.get('observacao') or '')
        texto = f"{tipo} {observacao}".lower()
        if 'xs1' in texto:
            xs1.append(item)

    return xs1


def gerar_script_gigs_sem_prazo(tamanho_pagina: int = 100) -> str:
    """Compatibilidade: wrapper para gerar_script_gigs_xs1."""
    return gerar_script_gigs_xs1(tamanho_pagina=tamanho_pagina)


def testar_gigs_sem_prazo(driver, tamanho_pagina: int = 100) -> List[dict]:
    """Compatibilidade: wrapper para testar_gigs_xs1."""
    return testar_gigs_xs1(driver, tamanho_pagina=tamanho_pagina)


def processar_gigs_sem_prazo_p2b(driver, tamanho_pagina: int = 100, max_processos: int = 0):
    """Executa o fluxo P2B usando API GIGS sem prazo + 'XS' e engine run_batch.

    Substitui apenas a etapa de navegação/listagem onde D em x.py chamava fluxo_prazo.
    Ações por processo continuam sendo executadas via fluxo_pz (mesma lógica de processos).
    """
    from utilitarios_processamento import run_batch, resultado_ok, resultado_falha
    from Fix.core import wait_for_page_load

    progresso = carregar_progresso_p2b()
    atividades = testar_gigs_xs1(driver, tamanho_pagina=tamanho_pagina)
    total_encontrado = len(atividades)
    if total_encontrado == 0:
        logger.info('[PRAZO_API] Nenhuma atividade XS1 encontrada')
        return {'sucesso': True, 'total': 0, 'processados': 0}

    logger.info(f'[PRAZO_API] GIGS XS1 encontrados: {total_encontrado}')

    # ── Normalizar itens, aplicando limite max_processos sobre a lista original
    itens = []
    for idx, item in enumerate(atividades, start=1):
        if max_processos and idx > max_processos:
            break

        processo_obj = item.get('processo') or {}
        id_processo = (processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id'))
        numero = (processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero'))

        if not id_processo:
            logger.warning(f'[PRAZO_API] Item {idx} sem id_processo, pulando (numero_recuperado={numero})')
            continue

        chave_progresso = numero or str(id_processo)
        itens.append({'id': id_processo, 'numero': numero, 'chave': chave_progresso})

    logger.info(f'[PRAZO_API] Processos a serem executados: {[p.get("numero") for p in itens]}')

    # ── Callbacks do engine
    def should_skip(item):
        chave = item.get('chave') or item.get('numero') or str(item.get('id', ''))
        if chave and processo_ja_executado_p2b(chave, progresso):
            logger.info(f'[PRAZO_API] Processo {chave} ja executado, pulando')
            return True
        return False

    # ── Interrupção manual do usuário ──
    # Se as abas sumirem DE NOVO depois da 1ª recriação, o browser foi fechado
    # manualmente — abortar o batch (critical) em vez de forçar a abertura de
    # novas abas para prosseguir indevidamente.
    recriacoes_aba = 0

    def open_item(item):
        """Navega para o detalhe do processo na mesma aba, fechando abas extras."""
        from Fix.abas import validar_conexao_driver, fechar_abas_extras
        if not validar_conexao_driver(driver):
            return resultado_falha('browser_fechado_manualmente', critical=True)
        try:
            fechar_abas_extras(driver)
        except Exception as e:
            logger.warning(f'[PRAZO_API] Falha ao gerenciar abas residuais: {e}')
            if not validar_conexao_driver(driver):
                return resultado_falha('browser_fechado_manualmente', critical=True)

        id_processo = item['id']
        detalhe_url = url_processo_detalhe(id_processo)
        logger.info(f'[PRAZO_API] Abrindo processo id={id_processo} numero={item.get("numero")}')
        driver.get(detalhe_url)
        try:
            wait_for_page_load(driver, timeout=20)
        except Exception:
            pass
        return resultado_ok()

    def execute_item(item):
        """Executa fluxo_pz no processo aberto."""
        try:
            ok = fluxo_pz(driver)
            if ok:
                return resultado_ok()
            else:
                return resultado_falha("fluxo_pz_nao_executou")
        except SessaoExpiradaError as e:
            logger.warning(f'[PRAZO_API] Sessao expirada (401) no processo {item.get("numero")}: {e}')
            return resultado_falha("sessao_expirada_401", critical=True)
        except Exception as e:
            msg = str(e)
            # Erro de nível browser/context (aba morta em toda a chain) — não é
            # falha do processo: parar o batch imediatamente.
            if 'has been closed' in msg:
                logger.warning(f'[PRAZO_API] Browser fechado durante execucao do processo {item.get("numero")} — interrompendo batch: {msg}')
                return resultado_falha('browser_fechado_manualmente', critical=True)
            logger.error(f'[PRAZO_API] Erro ao executar fluxo_pz para processo {item.get("numero")}: {e}')
            return resultado_falha(str(e))

    def persist_result(item, result):
        chave = item.get('chave') or item.get('numero') or str(item.get('id', ''))
        if result.get('ok'):
            if chave:
                marcar_processo_executado_p2b(chave, progresso)
                logger.info(f'[PRAZO_API] Processo {item.get("numero")} processado com sucesso (fluxo_pz)')
        else:
            # Nao marca como executado (sera retentado), mas deixa rastro no log.
            logger.warning(
                f'[PRAZO_API] Processo {item.get("numero")} NAO concluido '
                f'({result.get("erro") or "motivo desconhecido"}) — nao marcado; '
                f'sera retentado na proxima execucao')

    stats = run_batch(
        items=itens,
        should_skip=should_skip,
        open_item=open_item,
        execute_item=execute_item,
        persist_result=persist_result,
        stop_on_critical=True,
    )

    falhas = [{'numero': r['item'].get('numero'), 'erro': r['erro']} for r in stats['itens'] if r['status'] == 'falha']

    return {
        'sucesso': stats['falha'] == 0,
        'total': total_encontrado,
        'processados': stats['sucesso'],
        'falhas': falhas,
        'critical_stop': stats.get('critical_stop', False),
        'critical_reason': stats.get('critical_reason'),
    }


# ═══════════════════════════════════════════
# VALIDAÇÃO / TESTE
# ═══════════════════════════════════════════

if __name__ == "__main__":
    logger.info('Prazo.p2b_gateway: funcoes disponiveis: fluxo_pz, processar_gigs_sem_prazo_p2b, testar_gigs_sem_prazo')

    # Teste importações
    try:
        from Prazo.p2b_core import normalizar_texto, gerar_regex_geral

        teste = "TESTE ÁCÊNTÖS"
        resultado = normalizar_texto(teste)
        logger.info('normalizar_texto OK: "%s" -> "%s"', teste, resultado)

    except ImportError as e:
        logger.error("Erro de importacao: %s", e)
