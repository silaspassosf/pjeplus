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

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

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

from Fix.variaveis import url_processo_detalhe


# ═══════════════════════════════════════════
# 1. p2b_api.py
# ═══════════════════════════════════════════

_TIPOS_RELEVANTES = re.compile(r'^(despacho|decis[aã]o|senten[cç]a|conclus[aã]o)', re.IGNORECASE)


def extrair_documento_relevante(driver: WebDriver) -> Dict[str, Any]:
    """Extrai o primeiro documento relevante via API (/timeline + /documentos/.../conteudo).

    Retorna dict com chaves: sucesso, conteudo, tipo, titulo, id_documento, id_processo, erro
    """
    from api.variaveis_client import session_from_driver

    # 1) obter id_processo da URL
    m = re.search(r'/processo/(\d+)', driver.current_url)
    if not m:
        return _falha('id_processo não detectado na URL: ' + driver.current_url)
    id_processo = m.group(1)

    sess, host = session_from_driver(driver)
    base = f'https://{host}'

    # 2) timeline via API
    url_timeline = (
        f'{base}/pje-comum-api/api/processos/id/{id_processo}/timeline'
        '?buscarDocumentos=true&buscarMovimentos=false&somenteDocumentosAssinados=false'
    )
    try:
        r = sess.get(url_timeline, timeout=30)
        r.raise_for_status()
        timeline = r.json()
    except Exception as e:
        return _falha(f'timeline HTTP error: {e}')

    doc = next((i for i in timeline if _TIPOS_RELEVANTES.match((i.get('tipo') or '').strip())), None)
    if not doc:
        tipos = list({i.get('tipo', '?') for i in timeline})
        return _falha(f'nenhum documento relevante na timeline. Tipos: {tipos}')

    id_doc = str(doc.get('id') or doc.get('idDocumento') or '')
    tipo = doc.get('tipo', '')
    titulo = doc.get('titulo', '')
    logger.info(f'[p2b_api] doc relevante: tipo={tipo} id={id_doc}')

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
    }


def _falha(msg: str, **extra) -> Dict[str, Any]:
    logger.warning(f'[p2b_api] {msg}')
    return {'sucesso': False, 'conteudo': None, 'tipo': None, 'titulo': None, 'id_documento': None, 'id_processo': None, 'erro': msg, **extra}


def processar_processo_por_id_api(driver: WebDriver, id_processo: int, host: str = 'pje.trt2.jus.br') -> Dict[str, Any]:
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
    time.sleep(1.5)

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


def _abrir_tarefa_e_tentar_iniciar_execucao(driver: WebDriver, timeout: int = 10) -> bool:
    """Abre a tarefa mais recente na mesma aba e clica em 'Iniciar execução' se existir."""
    url_atual = driver.current_url or ''
    match = re.search(r'^(https://[^/]+)/pjekz/processo/(\d+)', url_atual)
    if '/tarefa/' not in url_atual:
        if not match:
            return False
        base, id_processo = match.groups()
        try:
            dados = driver.execute_async_script(
                """
                const done = arguments[arguments.length - 1];
                fetch(arguments[0], {credentials: 'include'})
                    .then(r => r.json())
                    .then(j => done(Array.isArray(j) ? j[0] : j))
                    .catch(e => done({__erro: String(e)}));
                """,
                f"{base}/pje-comum-api/api/processos/id/{id_processo}/tarefas?maisRecente=true"
            )
            id_tarefa = None if not isinstance(dados, dict) else (dados.get('id') or dados.get('idTarefa'))
            if dados.get('__erro') or not id_tarefa:
                return False
            driver.get(f'{base}/pjekz/processo/{id_processo}/tarefa/{id_tarefa}')
        except Exception as e:
            logger.warning('[FLUXO_PZ] inicar_exec: falha ao abrir tarefa na mesma aba: %s', e)
            return False

    try:
        from Fix.core import aguardar_renderizacao_nativa
        aguardar_renderizacao_nativa(
            driver,
            "button[aria-label='Iniciar execução'], button[aria-label='Iniciar execucao']",
            modo='aparecer',
            timeout=min(8, timeout)
        )
    except Exception:
        pass

    try:
        estado = driver.execute_script(
            """
            const seletor = "button[aria-label='Iniciar execução'], button[aria-label='Iniciar execucao']";
            const botoes = Array.from(document.querySelectorAll(seletor));

            function visivel(el) {
                if (!el) return false;
                const st = window.getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return st.display !== 'none' && st.visibility !== 'hidden' && r.width > 0 && r.height > 0;
            }

            const visiveis = botoes.filter(visivel);
            const ativo = visiveis.find(btn => (
                !btn.disabled
                && btn.getAttribute('disabled') === null
                && !btn.classList.contains('mat-button-disabled')
            ));

            if (ativo) {
                ativo.scrollIntoView({block: 'center'});
                ativo.click();
                return { clicked: true, status: 'ativo' };
            }

            const inativo = visiveis.find(btn => (
                btn.disabled
                || btn.getAttribute('disabled') !== null
                || btn.classList.contains('mat-button-disabled')
            ));

            if (inativo) {
                return { clicked: false, status: 'inativo' };
            }

            return { clicked: false, status: visiveis.length ? 'visivel_sem_estado' : 'nao_encontrado' };
            """
        )

        clicou = bool(isinstance(estado, dict) and estado.get('clicked'))
        if not clicou and isinstance(estado, dict) and estado.get('status') == 'inativo':
            logger.info('[FLUXO_PZ] inicar_exec: botão "Iniciar execução" detectado, porém inativo')

        if clicou:
            try:
                from Fix.core import aguardar_renderizacao_nativa
                aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', modo='aparecer', timeout=min(6, timeout))
            except Exception:
                pass
        return clicou
    except Exception:
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


def inicar_exec(driver, texto_normalizado: Optional[str] = None):
    """Helper: cria duas GIGS padrão, tenta Iniciar execução e roteia ato.

    1) cria GIG '1/Ana Lucia/Argos'      (try independente)
    2) cria GIG '1//xs sigilo'            (try independente — não bloqueado por falha do 1)
    3) abre a tarefa mais recente na mesma aba e tenta clicar 'Iniciar execução'
       - sucesso → ato_pesquisas (processo já está em execução)
       - falha   → roteia por fase:
           'liquid'/'homolog' → ato_pesqliq
           caso contrário     → ato_pesquisas

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

    # 3) Abrir a tarefa na mesma aba e tentar clicar "Iniciar execução" diretamente.
    # Se o botão não existir, manter o roteamento por fase atual.
    mov_ok = False
    try:
        mov_ok = _abrir_tarefa_e_tentar_iniciar_execucao(driver, timeout=10)
        if mov_ok:
            logger.info('[FLUXO_PZ] inicar_exec: Iniciar execução clicado com sucesso')
        else:
            logger.info('[FLUXO_PZ] inicar_exec: Iniciar execução não disponível, roteando por fase')
    except Exception as e:
        logger.info('[FLUXO_PZ] inicar_exec: checagem direta de Iniciar execução falhou (%s), roteando por fase', e)

    try:
        if mov_ok:
            # Processo movido para execução → ato_pesquisas (forçar sigilo)
            if ato_pesquisas:
                resultado = ato_pesquisas(driver, sigilo=True)
        else:
            # Fallback: rotear por fase processual
            fase_lower = ''
            try:
                fase = obter_fase_processual(driver)
                fase_lower = (fase or '').lower()
            except Exception:
                pass

            if ('liquid' in fase_lower or 'homolog' in fase_lower) and ato_pesqliq:
                # Chamadas em fallback também devem forçar sigilo
                resultado = ato_pesqliq(driver, sigilo=True)
            elif ato_pesquisas:
                resultado = ato_pesquisas(driver, sigilo=True)
    except Exception as e:
        logger.error('[FLUXO_PZ] inicar_exec: erro no roteamento: %s', e)

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


def fluxo_pz(driver: WebDriver) -> None:
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
        _processar_regras_gerais(driver, texto_normalizado, 0)
    except Exception as e:
        logger.error('[FLUXO_PZ] Erro ao processar regras: %s', e)

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

    def open_item(item):
        """Navega para o detalhe do processo na mesma aba, fechando abas extras."""
        try:
            abas = driver.window_handles
            if len(abas) > 1:
                aba_principal = abas[0]
                for aba in abas[1:]:
                    try:
                        driver.switch_to.window(aba)
                        driver.close()
                    except Exception:
                        pass
                driver.switch_to.window(aba_principal)
        except Exception:
            pass

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
        except Exception as e:
            logger.error(f'[PRAZO_API] Erro ao executar fluxo_pz para processo {item.get("numero")}: {e}')
            return resultado_falha(str(e))

    def persist_result(item, result):
        if result.get('ok'):
            chave = item.get('chave') or item.get('numero') or str(item.get('id', ''))
            if chave:
                marcar_processo_executado_p2b(chave, progresso)
                logger.info(f'[PRAZO_API] Processo {item.get("numero")} processado com sucesso (fluxo_pz)')

    stats = run_batch(
        items=itens,
        should_skip=should_skip,
        open_item=open_item,
        execute_item=execute_item,
        persist_result=persist_result,
    )

    falhas = [{'numero': r['item'].get('numero'), 'erro': r['erro']} for r in stats['itens'] if r['status'] == 'falha']

    return {
        'sucesso': stats['falha'] == 0,
        'total': total_encontrado,
        'processados': stats['sucesso'],
        'falhas': falhas,
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
