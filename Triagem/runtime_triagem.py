"""Triagem/runtime_triagem.py
Consolidado dos módulos de runtime da Triagem Inicial.

Este módulo reúne o código ativo de quatro arquivos que antes eram
separados: runner.py, api.py, driver.py e constants.py.

Estrutura:
  Constantes  — valores imutáveis e intervalos de CEP
  Driver      — criação de driver Selenium e login
  API Client  — acesso à API de listas de triagem
  Entrada     — fluxo principal de execução (run_triagem)

Uso:
  from Triagem.runner import run_triagem          # via thin shim (compatibilidade)
  from Triagem.runtime_triagem import run_triagem  # direto

  py -m Triagem.runtime_triagem                    # execução direta
"""
import logging
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from Fix.core import esperar_elemento
from Fix.gigs import criar_comentario, criar_gigs
from Fix.log import log_fim, log_item, log_start
from Fix.progresso_unificado import ProgressoUnificado
from api import PjeApiClient, session_from_driver
from utilitarios_processamento import resultado_falha, resultado_ok, run_batch

logger = logging.getLogger(__name__)


# =============================================================================
# Constantes
# =============================================================================

SALARIO_MINIMO = 1622.00                          # 2026
ALCADA = SALARIO_MINIMO * 2                        # R$ 3.244,00
RITO_SUMARISSIMO_MAX = SALARIO_MINIMO * 40         # R$ 64.880,00

INTERVALOS_CEP_ZONA_SUL = [
    (4307000, 4314999), (4316000, 4477999), (4603000, 4620999),
    (4624000, 4703999), (4708000, 4967999), (5640000, 5642999),
    (5657000, 5665999), (5692000, 5692999), (5703000, 5743999),
    (5745000, 5750999), (5752000, 5895999),
]

INTERVALOS_CEP_ZONA_LESTE = [
    (3125000, 3147999), (3150000, 3156999), (3201000, 3216999),
    (3220000, 3221999), (3224000, 3224999), (3226000, 3272999),
    (3275000, 3295999), (3317000, 3317999), (3333000, 3333999),
    (3335000, 3335999), (3337000, 3338999), (3374000, 3390999),
    (3402000, 3989999), (8010000, 8491999),
]

# Centro Expandido, Zona Norte e Zona Oeste — foro Rui Barbosa de São Paulo
INTERVALOS_CEP_RUI_BARBOSA = [
    # Centro Expandido
    (1001000, 1553999),
    (3001000, 3124999),
    (3149000, 3149999),
    (3157000, 3195999),
    (3222000, 3223999),
    (3225000, 3225999),
    (3273000, 3274999),
    (3301000, 3316999),
    (3318000, 3332999),
    (3334000, 3334999),
    (3336000, 3336999),
    (3340000, 3373999),
    (3401000, 3401999),
    (4001000, 4306999),
    (4315000, 4315999),
    (4501000, 4602999),
    (4621000, 4623999),
    (4704000, 4707999),
    (5001000, 5095999),
    (5102000, 5109999),
    (5114000, 5118999),
    (5301000, 5338999),
    (5343000, 5348999),
    (5401000, 5477999),
    # Zona Norte
    (2001000, 2998999),
    (5101000, 5101999),
    (5110000, 5110999),
    (5112000, 5113999),
    (5119000, 5289999),
    # Zona Oeste
    (5339000, 5340999),
    (5350000, 5399999),
    (5501000, 5639999),
    (5650000, 5656999),
    (5670000, 5691999),
    (5693000, 5693999),
]


# =============================================================================
# Driver
# =============================================================================

def criar_driver_e_logar(driver: Optional[WebDriver] = None) -> Optional[WebDriver]:
    """Cria um driver Selenium e faz login, ou retorna o driver existente."""
    if driver:
        return driver

    from Fix.utils import driver_pc, login_cpf

    drv = driver_pc()
    if not drv:
        return None

    if not login_cpf(drv):
        try:
            drv.quit()
        except Exception:
            pass
        return None

    return drv


# =============================================================================
# API Client
# =============================================================================

URL_LISTA_TRIAGEM = "https://pje.trt2.jus.br/pjekz/painel/global/10/lista-processos"


def _normalizar_lista(dados) -> list:
    """Normaliza resposta da API para uma lista de itens."""
    if isinstance(dados, list):
        return dados
    if isinstance(dados, dict):
        for chave in ('resultado', 'content', 'data', 'conteudo', 'items'):
            if isinstance(dados.get(chave), list):
                return dados[chave]
    return []


def _criar_cliente(driver: WebDriver) -> Optional[PjeApiClient]:
    """Cria um PjeApiClient autenticado a partir do driver."""
    try:
        sess, trt_host = session_from_driver(driver)
        return PjeApiClient(sess, trt_host)
    except Exception as exc:
        logger.error('[TRIAGEM/API] Erro ao preparar sessao autenticada: %s', exc)
        return None


def _buscar_paginado_patch(
    client: PjeApiClient,
    payload_base: Dict[str, Any],
    tam_pagina: int,
) -> Dict[str, Any]:
    """Busca paginada via PATCH no endpoint de agrupamento de tarefas."""
    todos: List[Dict[str, Any]] = []
    pg = 1
    limite = 50

    while pg <= limite:
        payload = dict(payload_base)
        payload['pagina'] = pg
        payload['tamanhoPagina'] = tam_pagina

        resposta = client.gateway_patch(
            '/pje-comum-api/api/agrupamentotarefas/10/processos',
            json_data=payload,
            timeout=60,
        )

        if not resposta.get('ok'):
            erro = resposta.get('error') or {}
            return {
                'erro': "HTTP_%s" % (resposta.get('status') or '0'),
                'detalhe': erro.get('message') or '',
                'resultado': todos,
                'pagina': pg,
            }

        data = resposta.get('data')
        lista = _normalizar_lista(data)
        if not lista:
            return {'resultado': todos}

        todos.extend(lista)
        total_pags = 1
        if isinstance(data, dict):
            total_pags = data.get('qtdPaginas') or data.get('totalPaginas') or 1

        if pg >= total_pags or len(lista) < tam_pagina:
            total = data.get('totalRegistros') if isinstance(data, dict) else None
            return {'resultado': todos, 'total': total or len(todos)}

        pg += 1

    return {'resultado': todos, 'aviso': 'limite_paginas'}


def buscar_lista_triagem(driver: WebDriver) -> List[Dict[str, Any]]:
    """Busca todos os itens da fila via API Gateway (PATCH paginado)."""
    client = _criar_cliente(driver)
    if not client:
        return []

    res = _buscar_paginado_patch(
        client,
        payload_base={
            'subCaixa': None,
            'tipoAtividade': None,
            'processos': None,
            'nomeConclusoMagistrado': None,
            'usuarioResponsavel': None,
            'faseProcessualString': None,
            'numeroProcesso': None,
            'juizoDigital': None,
        },
        tam_pagina=100,
    )

    if not res:
        logger.warning('[TRIAGEM/API] execute_async_script retornou None')
        return []

    if res.get('erro'):
        logger.error('[TRIAGEM/API] Erro do fetch JS: %s', res['erro'])
        return []

    if res.get('aviso'):
        logger.warning('[TRIAGEM/API] Aviso: %s', res['aviso'])

    lista = res.get('resultado', [])
    logger.info('[TRIAGEM/API] Total bruto: %s itens', len(lista))
    return lista


def _is_triagem_inicial(item: Dict) -> bool:
    """Verifica se o item pertence à fila 'Triagem Inicial'."""
    tarefa = item.get('tarefa') or ''
    if isinstance(tarefa, dict):
        tarefa = str(tarefa.get('nome') or tarefa.get('descricao') or '')
    return 'triagem inicial' in str(tarefa).lower()


def _numero_cnj(item: Dict) -> str:
    """Extrai o número CNJ do item."""
    return str(item.get('numeroProcesso') or item.get('numero') or item.get('id') or '')


def enriquecer_processo(item: Dict) -> Optional[Dict]:
    """Enriquece um item bruto da lista com metadados processados."""
    id_proc = item.get('id') or item.get('idProcesso')
    numero = _numero_cnj(item)
    if not id_proc:
        return None

    tipo = str(item.get('classeJudicial') or '').upper()
    digital = item.get('juizoDigital') is True or item.get('juizoDigital') == 'true'
    tem_aud = bool(item.get('dataProximaAudiencia'))

    bucket = 'D' if 'HTE' in tipo else ('A' if not tem_aud else ('B' if digital else 'C'))
    return {
        'numero': numero,
        'id_processo': id_proc,
        'tipo': tipo,
        'digital': digital,
        'tem_audiencia': tem_aud,
        'bucket': bucket,
    }


def buscar_painel_com_filtros(
    driver: WebDriver,
    fase: str = None,
    sub_caixa: list = None,
    tipo_atividade: list = None,
    usuario_responsavel: str = None,
    juizo_digital: bool = None,
    numero_processo: str = None,
    tam_pagina: int = 100,
) -> List[Dict[str, Any]]:
    """Busca processos no Painel Global filtrando por fase + chips.

    Args:
        driver: WebDriver Selenium autenticado
        fase: "Conhecimento", "Execução", "Liquidação" ou None
        sub_caixa: lista de nomes de sub-caixa ou None
        tipo_atividade: lista de tipos de atividade ou None
        usuario_responsavel: nome do usuário responsável ou None
        juizo_digital: True/False/None para filtrar por juízo digital
        numero_processo: número do processo ou None
        tam_pagina: itens por página (padrão: 100)

    Returns:
        Lista de dicionários com os processos encontrados
    """
    filtros = {
        'fase': fase,
        'sub_caixa': sub_caixa,
        'tipo_atividade': tipo_atividade,
        'usuario_responsavel': usuario_responsavel,
        'juizo_digital': juizo_digital,
        'numero': numero_processo,
    }

    client = _criar_cliente(driver)
    if not client:
        return []

    payload_base = {
        'subCaixa': filtros.get('sub_caixa') or None,
        'tipoAtividade': filtros.get('tipo_atividade') or None,
        'processos': None,
        'nomeConclusoMagistrado': None,
        'usuarioResponsavel': filtros.get('usuario_responsavel') or None,
        'faseProcessualString': filtros.get('fase') or None,
        'numeroProcesso': filtros.get('numero') or None,
        'juizoDigital': filtros.get('juizo_digital') if filtros.get('juizo_digital') is not None else None,
    }

    res = _buscar_paginado_patch(client, payload_base=payload_base, tam_pagina=tam_pagina)

    if not res:
        logger.warning('[TRIAGEM/API] execute_async_script retornou None')
        return []

    if res.get('erro'):
        logger.error('[TRIAGEM/API] Erro: %s', res['erro'])
        return []

    lista = res.get('resultado', [])
    if res.get('aviso'):
        logger.warning('[TRIAGEM/API] Aviso: %s', res['aviso'])

    logger.info('[TRIAGEM/API] Total de itens: %s (relatados: %s)',
                len(lista), res.get('total', len(lista)))
    return lista


# =============================================================================
# Entrada — Fluxo principal de execução
# =============================================================================

_progresso = ProgressoUnificado("TRIAGEM")


def _criar_driver_e_logar(driver: Optional[WebDriver]) -> Optional[WebDriver]:
    """Wrapper que delega à função criar_driver_e_logar local."""
    return criar_driver_e_logar(driver)


def _acao_b1_normal(driver: WebDriver, numero: str, processo_info: Dict) -> bool:
    """b1 — sem alertas críticos: execução normal via buckets locais."""
    from Triagem.acoes import acao_bucket_a, acao_bucket_b, acao_bucket_c, acao_bucket_d

    bucket = processo_info.get("bucket", "C")
    logger.debug("[TRIAGEM][%s] b1 — sem alertas → bucket %s (execucao normal)", numero, bucket)

    if bucket == "A":
        return acao_bucket_a(driver, numero, processo_info)
    if bucket == "B":
        return acao_bucket_b(driver, numero, processo_info)
    if bucket == "C":
        return acao_bucket_c(driver, numero, processo_info)
    if bucket == "D":
        return acao_bucket_d(driver, numero, processo_info)

    logger.warning("[TRIAGEM][%s] bucket desconhecido '%s' — sem acao", numero, bucket)
    return False


def _acao_b2_incompetencia(driver: WebDriver, numero: str, processo_info: Dict) -> bool:
    """b2 — incompetência territorial: sem nenhuma ação."""
    logger.debug("[TRIAGEM][%s] b2 — incompetencia territorial → processo nao processado", numero)
    return True


def _acao_c_pedidos(driver: WebDriver, numero: str, processo_info: Dict) -> bool:
    """c — pedidos não liquidados: placeholder de despacho para liquidar."""
    logger.debug("[TRIAGEM][%s] c — pedidos nao liquidados → placeholder despacho liquidar (TODO)", numero)
    return True


def _acao_d_docs(driver: WebDriver, numero: str, processo_info: Dict) -> bool:
    """d — falta de documentos pessoais: placeholder de apresentação de documento."""
    logger.debug("[TRIAGEM][%s] d — falta de documentos pessoais → placeholder apresentar doc (TODO)", numero)
    return True


def _aplicar_acao_pos_triagem(
    driver: WebDriver,
    numero: str,
    processo_info: Dict,
    triagem_txt: str,
) -> bool:
    """Decide e executa ação pós-triagem com base nos alertas.

    Usa determinar_acao_pos_triagem() do registry de regras para
    identificar o bucket correspondente e então despacha para a
    função de ação adequada.
    """
    from Triagem.regras import alerta_registry, determinar_acao_pos_triagem

    if not triagem_txt or (isinstance(triagem_txt, str) and triagem_txt.startswith("ERRO")):
        logger.warning("[TRIAGEM][%s] triagem com erro — sem acao", numero)
        return False

    # 1. Determinar bucket via registry
    bucket, _ = determinar_acao_pos_triagem(triagem_txt)

    # 2. Pré-bucket: competência por domicílio do autor → GIGS observação
    if bucket == 'pre_bucket':
        try:
            criar_gigs(driver, "", "", "Competencia definida por domicilio do autor - aguardar excecao")
            logger.debug("[TRIAGEM][%s] GIGS domicilio do autor criado", numero)
        except Exception as e:
            logger.error("ERRO em _aplicar_acao_pos_triagem: Erro ao criar GIGS domicilio autor: %s", e)
        # Reavaliar sem o pre_bucket para obter o bucket real
        bucket = 'b1_normal'
        for bn in ('b2_incompetencia', 'c_pedidos', 'd_docs'):
            for p, b, _ in alerta_registry.all_rules():
                if b == bn and p.search(triagem_txt):
                    bucket = bn
                    break
            if bucket != 'b1_normal':
                break

    # 3. Despachar para a ação correspondente
    if bucket == 'b2_incompetencia':
        return _acao_b2_incompetencia(driver, numero, processo_info)
    if bucket == 'c_pedidos':
        return _acao_c_pedidos(driver, numero, processo_info)
    if bucket == 'd_docs':
        return _acao_d_docs(driver, numero, processo_info)
    # b1: sem alertas críticos → execução normal de buckets
    return _acao_b1_normal(driver, numero, processo_info)


def run_triagem(driver: Optional[WebDriver] = None) -> Optional[Dict[str, Any]]:
    """Fluxo principal de triagem.

    Espelha a estrutura de aud.run_aud():
      1. Cria/usa driver e faz login
      2. Busca lista Triagem Inicial via API
      3. Filtra processos já executados (progresso.json)
      4. Para cada processo pendente: triagem → comentário → ação pós-triagem
    """
    from Fix.utils import configurar_recovery_driver, driver_pc, handle_exception_with_recovery, login_cpf

    configurar_recovery_driver(driver_pc, login_cpf)

    log_start('TRIAGEM')

    drv = _criar_driver_e_logar(driver)
    if not drv:
        logger.error("ERRO em run_triagem: Falha ao obter driver")
        return None

    try:
        logger.debug("[TRIAGEM] Navegando para %s", URL_LISTA_TRIAGEM)
        drv.get(URL_LISTA_TRIAGEM)
        time.sleep(3)

        # 1. Buscar lista
        itens_brutos = buscar_lista_triagem(drv)
        if not itens_brutos:
            logger.error("ERRO em run_triagem: API nao retornou itens — verificar sessao ou endpoint")
            return {"sucesso": False, "erro": "Lista vazia"}

        triagem_itens = [i for i in itens_brutos if _is_triagem_inicial(i)]
        if not triagem_itens:
            logger.debug("[TRIAGEM] Campo tarefa nao identificou Triagem Inicial — usando todos os itens")
            triagem_itens = itens_brutos

        lista = [p for p in (enriquecer_processo(i) for i in triagem_itens) if p]
        if not lista:
            logger.error("ERRO em run_triagem: Nenhum processo enriquecido")
            return {"sucesso": False, "erro": "Nenhum processo enriquecido"}

        logger.info("[TRIAGEM] %s processos de Triagem Inicial (de %s brutos)", len(lista), len(itens_brutos))

        # 2. Processar via engine run_batch
        progresso = _progresso.carregar_progresso()
        handle_principal = drv.current_window_handle

        def _fechar_abas_extras():
            """Fecha abas extras mantendo apenas a principal."""
            try:
                for h in list(drv.window_handles):
                    if h != handle_principal:
                        try:
                            drv.switch_to.window(h)
                            drv.close()
                        except Exception:
                            pass
                drv.switch_to.window(handle_principal)
            except Exception:
                pass

        def should_skip(proc):
            return _progresso.processo_ja_executado(proc.get("numero"), progresso)

        def open_item(proc):
            numero = proc.get("numero", "?")
            id_processo = proc.get("id_processo")
            if not id_processo:
                return resultado_falha("Sem id_processo")
            try:
                url = "https://pje.trt2.jus.br/pjekz/processo/%s/detalhe/" % id_processo
                drv.get(url)
                esperar_elemento(drv, "pje-cabecalho-processo,pje-timeline",
                                 by=By.CSS_SELECTOR, timeout=15)
                return resultado_ok()
            except Exception as e:
                return resultado_falha(str(e))
            finally:
                _fechar_abas_extras()

        def execute_item(proc):
            from Triagem.service import triagem_peticao

            numero = proc.get("numero", "?")
            try:
                log_item('TRIAGEM', numero)

                # Executar triagem
                logger.debug("[TRIAGEM][%s] Executando triagem_peticao...", numero)
                triagem_txt = triagem_peticao(drv)
                proc["triagem"] = triagem_txt

                # Filtro crítico 401 — não registrar progresso
                if isinstance(triagem_txt, str) and triagem_txt.startswith("ERRO: ERRO_CRITICO_401"):
                    logger.error("ERRO em run_triagem: ERRO 401 — sessao rejeitada, pular sem registrar (%s)", numero)
                    return resultado_falha("ERRO_CRITICO_401", critical=True)

                # Registrar comentário com resultado da triagem
                if triagem_txt:
                    try:
                        observacao = "BIANCA - TRIAGEM\n\n%s" % triagem_txt
                        sucesso_cmt = criar_comentario(drv, observacao)
                        if not sucesso_cmt:
                            logger.warning("[TRIAGEM][%s] Comentario pode nao ter sido salvo", numero)
                    except Exception as e:
                        logger.error("ERRO em run_triagem: Falha ao registrar comentario (%s): %s", numero, e)
                        traceback.print_exc()

                # Barreira: aguardar tabela de atividades GIGS pronta
                from Fix.utils_observer import aguardar_renderizacao_nativa as _aguardar
                _aguardar(drv, 'pje-gigs-lista-atividades button', 'aparecer', 8)

                # Aplicar ação pós-triagem baseada em alertas
                ok = False
                try:
                    ok = _aplicar_acao_pos_triagem(drv, numero, proc, triagem_txt)
                except Exception as e:
                    logger.error("ERRO em run_triagem: Erro na acao pos-triagem (%s): %s", numero, e)
                    traceback.print_exc()

                return resultado_ok() if ok else resultado_falha("Acao pos-triagem falhou")

            except Exception as e:
                return resultado_falha(str(e))
            finally:
                _fechar_abas_extras()

        def persist_result(proc, result):
            numero = proc.get("numero", "?")
            dados = result.get('dados') or {}
            if dados.get('critical'):
                # Não registrar progresso para erros críticos de sessão (401)
                return
            ok = result.get('ok', False)
            _progresso.marcar_processo_executado(
                numero, "SUCESSO" if ok else "FALHA", None, progresso)

        batch_result = run_batch(
            items=lista,
            should_skip=should_skip,
            open_item=open_item,
            execute_item=execute_item,
            persist_result=persist_result,
        )

        ok_count = batch_result['sucesso']
        total_count = batch_result['sucesso'] + batch_result['falha']
        logger.info("[TRIAGEM] OK: %s processos triados (%s sucesso, %s falha)", total_count, ok_count, total_count - ok_count)

        resumo = {
            "sucesso": batch_result['sucesso'] > 0 or len(lista) == 0,
            "processados": total_count,
            "sucesso_count": batch_result['sucesso'],
            "total": len(lista),
        }
        log_fim('TRIAGEM', resumo)
        return resumo

    except Exception as e:
        novo = None
        try:
            from Fix.utils import handle_exception_with_recovery
            novo = handle_exception_with_recovery(e, drv, "TRIAGEM_RUN")
        except Exception:
            pass
        if not novo:
            logger.error("ERRO em run_triagem: Erro fatal: %s", e)
            traceback.print_exc()
        return None


if __name__ == "__main__":
    # Garante imports do projeto raiz
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    logger.debug("[TRIAGEM] Executando como script")
    resultado = run_triagem(None)
    logger.debug("[TRIAGEM] Resultado: %s", resultado)
