from typing import Any, Optional
import unicodedata
import logging
from Fix import espera
from Fix.core import safe_click, esperar_elemento, aguardar_renderizacao_nativa

logger = logging.getLogger(__name__)


def _normalizar_texto(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize('NFKD', s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _normalizar_tarefa(tarefa: str) -> str:
    if not tarefa:
        return ""
    tarefa_norm = _normalizar_texto(tarefa)
    tarefa_norm = tarefa_norm.replace('preparar expedientes e comunicacoes', 'comunicacoes e expedientes')
    tarefa_norm = tarefa_norm.replace('aguardando cumprimento de acordo', 'controle de acordo')
    return tarefa_norm


def navegar_para_tarefa(
    driver: Any,
    tarefa_destino: str,
    debug: bool = False,
    timeout: int = 30,
    tarefa_atual_conhecida: Optional[str] = None
) -> bool:
    try:
        tarefa_atual = tarefa_atual_conhecida or _obter_tarefa_atual(driver, debug)
        if not tarefa_atual:
            logger.warning('[NAVEGAR_TAREFA] Nao foi possivel identificar tarefa atual')
            return False

        tarefa_atual_norm = _normalizar_tarefa(tarefa_atual)
        tarefa_destino_norm = _normalizar_tarefa(tarefa_destino)

        if tarefa_atual_norm == tarefa_destino_norm:
            return True

        if _deve_interromper_movimento(tarefa_atual_norm, tarefa_destino_norm, debug):
            logger.warning('[NAVEGAR_TAREFA] Movimento interrompido por condicao especial')
            return False

        return _executar_movimento_para_destino(driver, tarefa_atual_norm, tarefa_destino_norm, debug, timeout)
    except Exception as e:
        logger.warning('[NAVEGAR_TAREFA] Erro na navegacao: %s', e)
        return False


def _obter_tarefa_atual(driver: Any, debug: bool) -> Optional[str]:
    try:
        url = getattr(driver, 'current_url', '') or ''
        if 'nomeTarefa=Arquivo+provis' in url:
            return 'Arquivo provisório'
        elif 'nomeTarefa=Arquivo+definitivo' in url:
            return 'Arquivo definitivo'

        return _extrair_tarefa_do_dom(driver)
    except Exception as e:
        logger.warning('[OBTER_TAREFA] Erro ao obter tarefa atual: %s', e)
        return None


def _extrair_tarefa_do_dom(driver: Any) -> Optional[str]:
    try:
        el_tarefa = espera.elemento(driver, 'pje-cabecalho-tarefa h1.titulo-tarefa', teto=1)
        if el_tarefa:
            return (getattr(el_tarefa, 'text', '') or '').strip()
        return None
    except Exception:
        return None


def _deve_interromper_movimento(tarefa_atual: str, tarefa_destino: str, debug: bool) -> bool:
    if 'elaborar' in tarefa_atual or 'assinar' in tarefa_atual:
        return True
    if 'controle de acordo' in tarefa_atual:
        return True
    return False


def _executar_movimento_para_destino(
    driver: Any,
    tarefa_atual: str,
    tarefa_destino: str,
    debug: bool,
    timeout: int
) -> bool:
    if 'analise' in tarefa_atual:
        return _movimento_de_analise(driver, tarefa_destino, debug, timeout)

    movimentos = {
        'conclusao ao magistrado': lambda: _clicar_botao_por_texto(driver, 'cancelar conclusao', debug),
        'comunicacoes e expedientes': lambda: _movimento_comunicacoes(driver, debug),
        'arquivo provisorio': lambda: _movimento_arquivo_provisorio(driver, debug),
        'arquivo definitivo': lambda: _movimento_arquivo_provisorio(driver, debug),
        'aguardando final do sobrestamento': lambda: _movimento_sobrestamento_final(driver, debug),
        'iniciar execucao': lambda: _clicar_botao_por_texto(driver, 'iniciar', debug),
        'liquidacao': lambda: _clicar_botao_por_texto(driver, 'iniciar', debug),
        'remessa': lambda: _clicar_botao_por_texto(driver, 'devolver', debug),
        'prazo vencido': lambda: _encerrar_prazo(driver, debug),
        'transito em julgado': lambda: _clicar_botao_por_texto(driver, 'certidao de transito', debug),
    }

    movimento_func = None
    for termo, func in movimentos.items():
        if termo in tarefa_atual:
            movimento_func = func
            break

    if movimento_func:
        sucesso = movimento_func()
        if sucesso:
            _esperar_transicao(driver, debug)
            return _verificar_e_ir_para_analise(driver, tarefa_destino, debug, timeout)

    return _verificar_e_ir_para_analise(driver, tarefa_destino, debug, timeout)


def _movimento_de_analise(driver: Any, tarefa_destino: str, debug: bool, timeout: int) -> bool:
    try:
        from .movimentos_fluxo import _localizar_botao_destino_movimento

        btn_destino = _localizar_botao_destino_movimento(driver, tarefa_destino, timeout=timeout)
        if not btn_destino:
            logger.warning('[ANALISE] Botao destino "%s" nao encontrado', tarefa_destino)
            return False

        if getattr(btn_destino, 'get_attribute', lambda a: None)('disabled'):
            logger.warning('[ANALISE] Botao destino esta desabilitado')
            return False

        safe_click(driver, btn_destino)
        _esperar_transicao(driver, debug)
        return True
    except Exception as e:
        logger.warning('[ANALISE] Erro no movimento de analise: %s', e)
        return False


def _clicar_botao_por_texto(driver: Any, texto: str, debug: bool = False, timeout: int = 5) -> bool:
    try:
        texto_norm = _normalizar_texto(texto)
        xpath = (
            f"//button[contains(translate(normalize-space(.), "
            f"'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ', "
            f"'abcdefghijklmnopqrstuvwxyzaaaaeeiooouc'), '{texto_norm}')]"
        )
        btn = espera.elemento(driver, xpath, teto=timeout)
        if btn and getattr(btn, 'is_enabled', lambda: True)():
            safe_click(driver, btn)
            return True
        return False
    except Exception:
        return False


def _encerrar_prazo(driver: Any, debug: bool) -> bool:
    try:
        if not _clicar_botao_por_texto(driver, 'encerrar prazo', debug):
            return False
        espera.assentar(driver, 0.5)
        return _clicar_botao_por_texto(driver, 'Sim', debug)
    except Exception as e:
        logger.warning('[ENCERRAR_PRAZO] Erro: %s', e)
        return False


def _verificar_e_ir_para_analise(
    driver: Any, tarefa_destino: str, debug: bool, timeout: int
) -> bool:
    tarefa_atual = _obter_tarefa_atual(driver, debug)
    if tarefa_atual:
        tarefa_norm = _normalizar_tarefa(tarefa_atual)
        if 'analise' in tarefa_norm:
            if 'analise' in _normalizar_tarefa(tarefa_destino):
                return True
            return _movimento_de_analise(driver, tarefa_destino, debug, timeout)
        if _clicar_botao_por_texto(driver, 'analise', debug):
            _esperar_transicao(driver, debug)
            return True
    return False


def _movimento_comunicacoes(driver: Any, debug: bool) -> bool:
    try:
        btn_cancelar = esperar_elemento(driver, "button[aria-label*='cancelar expedientes']", timeout=10)
        if btn_cancelar:
            safe_click(driver, btn_cancelar)
            _esperar_transicao(driver, debug, esperar=False)
            return True
        return False
    except Exception as e:
        logger.warning('[COMUNICACOES] Erro: %s', e)
        return False


def _movimento_arquivo_provisorio(driver: Any, debug: bool) -> bool:
    try:
        btn_arquivo = esperar_elemento(driver, "input[value='Arquivo']", timeout=10)
        if btn_arquivo:
            safe_click(driver, btn_arquivo)
            _esperar_transicao(driver, debug)
            return True
        return False
    except Exception as e:
        logger.warning('[ARQUIVO_PROVISORIO] Erro: %s', e)
        return False


def _movimento_sobrestamento_final(driver: Any, debug: bool) -> bool:
    try:
        btn_encerrar = esperar_elemento(driver, "button[aria-label*='encerrar']", timeout=10)
        if btn_encerrar:
            safe_click(driver, btn_encerrar)
            btn_sim = esperar_elemento(driver, "button[aria-label='Sim']", timeout=5)
            if btn_sim:
                safe_click(driver, btn_sim)
                _esperar_transicao(driver, debug)
                return True
        return False
    except Exception as e:
        logger.warning('[SOBRESTAMENTO_FINAL] Erro: %s', e)
        return False


def _movimento_padrao_para_analise(driver: Any, tarefa_destino: str, debug: bool, timeout: int) -> bool:
    try:
        btn_analise = esperar_elemento(driver, "button[aria-label='Análise']", timeout=10)
        if btn_analise and not getattr(btn_analise, 'get_attribute', lambda a: None)('disabled'):
            safe_click(driver, btn_analise)
            _esperar_transicao(driver, debug)
            return _movimento_de_analise(driver, tarefa_destino, debug, timeout)
        return False
    except Exception as e:
        logger.warning('[PADRAO] Erro no movimento padrao: %s', e)
        return False


def _movimento_para_analise_se_necessario(driver: Any, tarefa_destino: str, debug: bool, timeout: int) -> bool:
    tarefa_atual = _obter_tarefa_atual(driver, debug)
    if tarefa_atual and 'analise' not in _normalizar_tarefa(tarefa_atual):
        return _movimento_padrao_para_analise(driver, tarefa_destino, debug, timeout)
    return True


def _esperar_transicao(driver: Any, debug: bool = False, esperar: bool = True, timeout: int = 8) -> bool:
    try:
        if not esperar:
            return True
        aguardar_renderizacao_nativa(
            driver, 'pje-cabecalho-tarefa h1.titulo-tarefa', modo='sumir', timeout=3
        )
        return aguardar_renderizacao_nativa(
            driver, 'pje-botoes-transicao button', modo='aparecer', timeout=timeout
        )
    except Exception as e:
        logger.warning('[ESPERAR_TRANSICAO] Timeout ou erro: %s', e)
        return False
