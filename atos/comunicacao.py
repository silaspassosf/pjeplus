"""atos/comunicacao.py — Orquestrador de comunicações judiciais (PEC/minutas) sobre Playwright."""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from Fix import espera
from Fix.abas import fechar_abas_extras as _fechar_abas_tabs
from Fix.core import aguardar_renderizacao_nativa, esperar_elemento
from Fix.extracao import criar_gigs
from Fix.log import logger
from Play.pjeplay.locators import By
from atos.wrappers_utils import executar_visibilidade_sigilosos_se_necessario

from .comunicacao_coleta import executar_coleta_conteudo
from .comunicacao_destinatarios import (
    contar_linhas_destinatarios,
    detectar_pjdp_processo,
    inserir_destinatarios_pjdp,
    remover_destinatarios_endereco_invalido,
    selecionar_destinatarios,
)
from .comunicacao_finalizacao import alterar_meio_expedicao, salvar_minuta_final
from .comunicacao_navigation import abrir_minutas
from .comunicacao_preenchimento import (
    aguardar_ato_confeccionado,
    aguardar_estabilizacao_para_destinatarios,
    executar_preenchimento_minuta,
)

_WRAPPERS_PJDP = ('pec_ord', 'pec_sum', 'pec_ordv', 'pec_sumv')


def _extrair_observacao_gigs_vencida_xs_pec(driver: Any, debug: bool = False) -> Optional[str]:
    try:
        xpath = "//table[@id='tabela-atividades']//tr[.//i[contains(@class, 'fa-clock') and contains(@class, 'danger')]]//span[contains(@class, 'descricao')]"
        for span in espera.elementos(driver, xpath, teto=1):
            try:
                txt = (getattr(span, 'text', '') or '').strip()
                if not txt or 'xs' not in txt.lower():
                    continue
                return txt[6:].strip() if txt.lower().startswith('prazo:') else txt
            except Exception:
                continue
        return None
    except Exception:
        return None


def _executar_gigs_extra(driver: Any, gigs_extra_efetivo: Any, prazo: int, nome_comunicacao: str) -> None:
    if not gigs_extra_efetivo:
        return
    try:
        if gigs_extra_efetivo is True:
            criar_gigs(driver, prazo, '', nome_comunicacao)
        elif isinstance(gigs_extra_efetivo, (tuple, list)):
            if len(gigs_extra_efetivo) >= 3:
                criar_gigs(driver, *gigs_extra_efetivo[:3])
            elif len(gigs_extra_efetivo) == 2:
                criar_gigs(driver, gigs_extra_efetivo[0], '', gigs_extra_efetivo[1])
            else:
                criar_gigs(driver, gigs_extra_efetivo)
        else:
            criar_gigs(driver, gigs_extra_efetivo)
    except Exception as e:
        logger.info('[GIGS_WRAPPER][ERRO] Falha ao executar criar_gigs antes do fluxo: %s', e)


def _normalizar_status_selecao(resultado_selecao: Any) -> Tuple[str, int]:
    if isinstance(resultado_selecao, dict):
        return resultado_selecao.get('status'), int(resultado_selecao.get('count', 0) or 0)
    if isinstance(resultado_selecao, int):
        return ('ok' if resultado_selecao > 0 else 'empty'), resultado_selecao
    if hasattr(resultado_selecao, 'status'):
        detalhes = getattr(resultado_selecao, 'detalhes', {}) or {}
        return resultado_selecao.status, int(detalhes.get('count', 0) or 0)
    return 'geral', 0


def _fechar_aba_se_extra(driver: Any, aba_original: Any) -> None:
    try:
        handles = getattr(driver, 'window' + '_handles', [])
        if len(handles) > 1 and aba_original in handles:
            _fechar_abas_tabs(driver, aba_original)
    except Exception:
        pass


def _aplicar_troca_modelo(driver: Any, modelo_troca: Optional[str], debug: bool, log_fn: Callable) -> None:
    from atos.comunicacao_finalizacao import _contar_linhas_correios, trocar_modelo_minuta
    from atos.comunicacao_preenchimento import aguardar_fechamento_dialogo_elaboracao, finalizar_minuta

    qtd_correios = _contar_linhas_correios(driver)
    if qtd_correios <= 0:
        log_fn("[COMUNICACAO][ORQUESTRA] Nenhuma linha de Correios detectada — mantendo modelo original")
        return

    log_fn(f"[COMUNICACAO][ORQUESTRA] Trocando modelo ({qtd_correios} linha(s) Correios detectada(s))")
    if not trocar_modelo_minuta(driver, modelo_troca=modelo_troca, debug=debug, log=log_fn):
        return

    try:
        esperar_elemento(driver, 'tbody.cdk-drop-list tr.cdk-drag', timeout=15, by=By.CSS_SELECTOR)
    except Exception as e:
        log_fn(f"[COMUNICACAO][ORQUESTRA][WARN] Erro ao aguardar estabilização: {e}")

    if not aguardar_fechamento_dialogo_elaboracao(driver, log=log_fn, timeout=2):
        log_fn("[COMUNICACAO][ORQUESTRA] Finalizando minuta pendente após troca de modelo")
        if not finalizar_minuta(driver, log=log_fn):
            raise Exception('finalizar_minuta falhou após troca de modelo — ato não finalizado')


def comunicacao_judicial(
    driver: Any,
    tipo_expediente: str,
    prazo: int,
    nome_comunicacao: str,
    sigilo: str,
    modelo_nome: str,
    trocar_modelo: bool = False,
    assinar: bool = False,
    **kwargs,
) -> bool:
    """Função direta para compatibilidade; delega para make_comunicacao_wrapper."""
    wrapper_func = make_comunicacao_wrapper(
        tipo_expediente=tipo_expediente,
        prazo=prazo,
        nome_comunicacao=nome_comunicacao,
        sigilo=sigilo,
        modelo_nome=modelo_nome,
        subtipo=kwargs.get('subtipo'),
        descricao=kwargs.get('descricao'),
        tipo_prazo=kwargs.get('tipo_prazo', 'dias uteis'),
        gigs_extra=kwargs.get('gigs_extra'),
        coleta_conteudo=kwargs.get('coleta_conteudo'),
        inserir_conteudo=kwargs.get('inserir_conteudo'),
        cliques_polo_passivo=kwargs.get('cliques_polo_passivo', 1),
        destinatarios=kwargs.get('destinatarios', 'extraido'),
        mudar_expediente=kwargs.get('mudar_expediente'),
        checar_sp=kwargs.get('checar_sp'),
        endereco_tipo=kwargs.get('endereco_tipo'),
        trocar_modelo=trocar_modelo,
        assinar=kwargs.get('assinar', assinar),
        remover_endereco_invalido=kwargs.get('remover_endereco_invalido'),
        pjdp=kwargs.get('pjdp'),
        wrapper_name=kwargs.get('wrapper_name'),
    )
    debug_value = kwargs.pop('debug', False)
    terceiro_value = kwargs.pop('terceiro', False)
    return wrapper_func(driver, debug=debug_value, terceiro=terceiro_value, **kwargs)


def make_comunicacao_wrapper(
    tipo_expediente: str,
    prazo: int,
    nome_comunicacao: str,
    sigilo: str,
    modelo_nome: str,
    subtipo: Optional[str] = None,
    descricao: Optional[str] = None,
    tipo_prazo: str = 'dias uteis',
    gigs_extra: Optional[Union[bool, Tuple, List, Any]] = None,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    cliques_polo_passivo: int = 1,
    cliques_informado: int = 2,
    destinatarios: str = 'extraido',
    mudar_expediente: Optional[bool] = None,
    checar_sp: Optional[bool] = None,
    endereco_tipo: Optional[str] = None,
    trocar_modelo: bool = False,
    wrapper_name: Optional[str] = None,
    terceiro_default: bool = False,
    assinar: bool = False,
    modelo_troca_correios: Optional[str] = None,
    remover_endereco_invalido: Optional[bool] = None,
    pjdp: Optional[Union[bool, str]] = False,
) -> Callable[[Any, bool, Any], bool]:
    """Cria wrapper reutilizável para expedição/comunicação judicial."""

    def wrapper(
        driver: Any,
        numero_processo: Optional[str] = None,
        observacao: Optional[str] = None,
        destinatarios_override: Optional[List[Dict[str, Any]]] = None,
        debug: bool = False,
        **overrides: Any,
    ) -> bool:
        aba_original = driver.current_window_handle
        destinatarios_param = (
            destinatarios_override
            if destinatarios_override is not None
            else overrides.get('destinatarios', destinatarios)
        )
        _executar_gigs_extra(driver, overrides.get('gigs_extra', gigs_extra), prazo, nome_comunicacao)

        remover_default = False if (wrapper_name == 'pec_exeq' or modelo_nome == 'xsexeq') else True
        remover_invalido = overrides.get(
            'remover_endereco_invalido',
            remover_endereco_invalido if remover_endereco_invalido is not None else remover_default,
        )
        pjdp_efetivo = overrides.get('pjdp', pjdp) if wrapper_name in _WRAPPERS_PJDP else False
        if wrapper_name in _WRAPPERS_PJDP and 'pjdp' not in overrides and not pjdp_efetivo:
            try:
                if detectar_pjdp_processo(driver):
                    pjdp_efetivo = True
                    logger.info("[COMUNICACAO][PJDP] PJDP detectada automaticamente para %s", wrapper_name)
            except Exception as e_pjdp:
                logger.warning("[COMUNICACAO][PJDP][WARN] Falha na detecção automática de PJDP: %s", e_pjdp)

        descricao_efetiva = overrides.get('descricao', descricao or nome_comunicacao)
        tipo_prazo_efetivo = overrides.get('tipo_prazo', tipo_prazo)
        cliques_passivo_efetivo = overrides.get('cliques_polo_passivo', cliques_polo_passivo)
        terceiro_efetivo = overrides.get('terceiro', terceiro_default)
        log_fn = overrides.get('log', logger.info)

        try:
            # 0. Coleta de conteúdo na aba /detalhe antes de abrir minutas.
            if coleta_conteudo:
                log_fn(f"[COMUNICACAO][ORQUESTRA] Executando coleta de conteúdo na aba detalhes para {nome_comunicacao}")
                executar_coleta_conteudo(driver, coleta_conteudo, debug=debug)

            log_fn(f"[COMUNICACAO][ORQUESTRA] Abrindo minutas para {nome_comunicacao}")
            if not abrir_minutas(driver, debug=debug):
                raise Exception("Falha ao abrir tela de minutas")

            log_fn("[COMUNICACAO][ORQUESTRA] Executando preenchimento da minuta")
            executar_preenchimento_minuta(
                driver=driver,
                tipo_expediente=tipo_expediente,
                prazo=prazo,
                nome_comunicacao=nome_comunicacao,
                subtipo=subtipo,
                descricao=descricao_efetiva,
                tipo_prazo=tipo_prazo_efetivo,
                sigilo=sigilo,
                modelo_nome=modelo_nome,
                inserir_conteudo=inserir_conteudo,
                finalizar=True,
                debug=debug,
                log=log_fn,
            )

            # Barreira antes dos destinatários: dialog de modelo fechado + UI estável.
            if destinatarios_param is not None:
                if not aguardar_estabilizacao_para_destinatarios(driver, log=log_fn):
                    raise Exception('Painel de destinatários não ficou pronto (barreira) — seleção abortada')

            log_fn("[COMUNICACAO][ORQUESTRA] Selecionando destinatários")
            resultado_selecao = selecionar_destinatarios(
                driver=driver,
                destinatarios=destinatarios_param,
                cliques_polo_passivo=cliques_passivo_efetivo,
                cliques_informado=cliques_informado,
                debug=debug,
                log=log_fn,
                observacao=observacao,
                numero_processo=numero_processo,
                terceiro=terceiro_efetivo,
            )

            if destinatarios_param is not None and destinatarios_param != '':
                status, count = _normalizar_status_selecao(resultado_selecao)
                log_fn(f"[COMUNICACAO][ORQUESTRA] Status seleção: {status} (count={count})")

                if status in ('ok', 'fallback', 'geral') or count > 0:
                    if not aguardar_renderizacao_nativa(driver, 'tbody.cdk-drop-list tr.cdk-drag', 'aparecer', 15):
                        log_fn('[COMUNICACAO][ORQUESTRA][WARN] Tabela sem destinatários — reenviando clique (1x)')
                        selecionar_destinatarios(
                            driver=driver,
                            destinatarios=destinatarios_param,
                            cliques_polo_passivo=1,
                            cliques_informado=cliques_informado,
                            debug=debug,
                            log=log_fn,
                            observacao=observacao,
                            numero_processo=numero_processo,
                            terceiro=terceiro_efetivo,
                        )
                        if not aguardar_renderizacao_nativa(driver, 'tbody.cdk-drop-list tr.cdk-drag', 'aparecer', 15):
                            raise Exception('Destinatários não adicionados ao ato (tabela vazia pós-seleção)')

                espera.pausa(driver, 3.0, motivo='estabilizacao pos-selecao destinatarios')
                espera.assentar(driver, 1.0, motivo='estabilizacao angular pos-destinatarios')

                if status in ('ok', 'fallback', 'geral') or count > 0:
                    try:
                        aguardar_renderizacao_nativa(
                            driver,
                            'i.pec-icone-verde-ato-individual-tabela-destinatarios, pje-pec-tabela-destinatarios i[aria-label="Ato confeccionado"]',
                            modo='aparecer',
                            timeout=10,
                        )
                    except Exception as e:
                        log_fn(f"[COMUNICACAO][ORQUESTRA] Erro ao aguardar renderização: {e}")

            # Alteração para Correios vem ANTES da limpeza de endereço inválido para vincular envelope.
            resolved_end = overrides.get('endereco_tipo', endereco_tipo)
            if not resolved_end and overrides.get('mudar_expediente', mudar_expediente):
                resolved_end = 'correios'
            if resolved_end and 'correio' in str(resolved_end).lower():
                tp = str(tipo_prazo_efetivo or 'dias uteis').lower()
                alterar_meio_expedicao(
                    driver,
                    debug=debug,
                    log=log_fn,
                    wrapper_name=wrapper_name,
                    vincular_primeiro_endereco=overrides.get('vincular_primeiro_endereco'),
                    restabelecer_prazo=('uteis' in tp or 'corridos' in tp),
                    prazo_dias=prazo,
                )

            if remover_invalido:
                remover_destinatarios_endereco_invalido(driver, log=log_fn, debug=debug)

            if overrides.get('trocar_modelo', trocar_modelo):
                _aplicar_troca_modelo(driver, overrides.get('modelo_troca_correios', modelo_troca_correios), debug, log_fn)

            pjdp_ativo = (
                wrapper_name in _WRAPPERS_PJDP
                and pjdp_efetivo is not None
                and str(pjdp_efetivo).strip().lower() in ('true', 'on', '1', 'yes', 's', 'sim')
            )
            if pjdp_ativo:
                inserir_destinatarios_pjdp(driver, log=log_fn, debug=debug)

            if remover_invalido:
                remover_destinatarios_endereco_invalido(driver, log=log_fn, debug=debug)

            if contar_linhas_destinatarios(driver) == 0:
                log_fn("[COMUNICACAO][ORQUESTRA][WARN] Tabela de destinatários vazia — salvamento abortado")
                return False

            salvou_ok = salvar_minuta_final(
                driver,
                sigilo,
                debug=debug,
                log=log_fn,
                executar_visibilidade=False,
                assinar=bool(overrides.get('assinar', assinar)),
                remover_endereco_invalido=remover_invalido,
            )
            if not salvou_ok:
                log_fn("[COMUNICACAO][ORQUESTRA][ERRO] Falha ao salvar/assinar minuta final.")
                return False

            _fechar_aba_se_extra(driver, aba_original)

            if str(sigilo).lower() in ('sim', 'true', '1'):
                try:
                    executar_visibilidade_sigilosos_se_necessario(driver, True, debug=debug)
                except Exception as e_vis:
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Falha ao aplicar visibilidade extra após fechar aba: {e_vis}")

            log_fn(f"[COMUNICACAO][ORQUESTRA] Fluxo concluído com sucesso para {nome_comunicacao}")
            return True
        except Exception as e:
            log_fn(f"[COMUNICACAO][ORQUESTRA][ERRO] Falha no fluxo: {e}")
            return False
        finally:
            _fechar_aba_se_extra(driver, aba_original)

    if wrapper_name:
        wrapper.__name__ = wrapper_name
    wrapper.modelo_nome = modelo_nome
    wrapper.trocar_modelo = trocar_modelo
    wrapper.modelo_troca_correios = modelo_troca_correios
    wrapper.endereco_tipo = endereco_tipo
    wrapper.pjdp = pjdp
    return wrapper


from .regras import registry  # noqa: E402, F401
