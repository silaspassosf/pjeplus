import time
from Fix.extracao import criar_gigs
from Fix.log import logger
from Fix.core import esperar_elemento, aguardar_renderizacao_nativa
from Fix.abas import fechar_abas_extras as _fechar_abas_tabs
from Fix import espera
from Play.pjeplay.locators import By
from .comunicacao_navigation import abrir_minutas
from .comunicacao_coleta import executar_coleta_conteudo
from .comunicacao_preenchimento import executar_preenchimento_minuta, aguardar_ato_confeccionado, aguardar_estabilizacao_para_destinatarios
from .comunicacao_destinatarios import (
    selecionar_destinatarios,
    remover_destinatarios_endereco_invalido,
    contar_linhas_destinatarios,
    inserir_destinatarios_pjdp,
    detectar_pjdp_processo,
)
from .comunicacao_finalizacao import alterar_meio_expedicao, salvar_minuta_final
from atos.wrappers_utils import executar_visibilidade_sigilosos_se_necessario
from typing import Optional, Any, Callable, Union, List, Dict, Tuple


def _extrair_observacao_gigs_vencida_xs_pec(driver: Any, debug: bool = False) -> Optional[str]:
    try:
        spans = espera.elementos(driver, "//table[@id='tabela-atividades']//tr[.//i[contains(@class, 'fa-clock') and contains(@class, 'danger')]]//span[contains(@class, 'descricao')]", teto=1)
        for span in spans:
            try:
                texto_descricao = (getattr(span, 'text', '') or '').strip()
                if not texto_descricao:
                    continue
                texto_lower = texto_descricao.lower()
                if 'xs' not in texto_lower:
                    continue
                if texto_lower.startswith('prazo:'):
                    texto_descricao = texto_descricao[6:].strip()
                return texto_descricao
            except Exception:
                continue
        return None
    except Exception:
        return None


def comunicacao_judicial(
    driver: Any,
    tipo_expediente: str,
    prazo: int,
    nome_comunicacao: str,
    sigilo: str,
    modelo_nome: str,
    trocar_modelo: bool = False,
    assinar: bool = False,
    **kwargs
) -> bool:
    """Função direta (não-wrapper) para manter compatibilidade com código existente."""
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
        wrapper_name=kwargs.get('wrapper_name')
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
    pjdp: Optional[Union[bool, str]] = False
) -> Callable[[Any, bool, Any], bool]:
    def wrapper(
        driver: Any,
        numero_processo: Optional[str] = None,
        observacao: Optional[str] = None,
        destinatarios_override: Optional[List[Dict[str, Any]]] = None,
        debug: bool = False,
        **overrides: Any
    ) -> bool:
        """Wrapper que aceita overrides genéricos e repassa quaisquer parâmetros fornecidos"""
        _aba_original = driver.current_window_handle

        destinatarios_param = destinatarios_override if destinatarios_override is not None else (
            overrides.get('destinatarios') if 'destinatarios' in overrides else destinatarios
        )

        gigs_extra_efetivo = overrides.get('gigs_extra', gigs_extra)
        if gigs_extra_efetivo:
            try:
                if gigs_extra_efetivo is True:
                    criar_gigs(driver, prazo, '', nome_comunicacao)
                elif isinstance(gigs_extra_efetivo, (tuple, list)):
                    if len(gigs_extra_efetivo) >= 3:
                        dias_uteis, responsavel, observacao_gigs = gigs_extra_efetivo[:3]
                        criar_gigs(driver, dias_uteis, responsavel, observacao_gigs)
                    elif len(gigs_extra_efetivo) == 2:
                        dias_uteis, observacao_gigs = gigs_extra_efetivo
                        criar_gigs(driver, dias_uteis, '', observacao_gigs)
                    else:
                        criar_gigs(driver, gigs_extra_efetivo)
                else:
                    criar_gigs(driver, gigs_extra_efetivo)
            except Exception as e:
                try:
                    logger.info(f'[GIGS_WRAPPER][ERRO] Falha ao executar criar_gigs antes do fluxo: {e}')
                except Exception:
                    pass

        call_kwargs = {
            'driver': driver,
            'tipo_expediente': tipo_expediente,
            'prazo': prazo,
            'nome_comunicacao': nome_comunicacao,
            'sigilo': sigilo,
            'modelo_nome': modelo_nome,
            'subtipo': overrides.get('subtipo', subtipo),
            'descricao': overrides.get('descricao', descricao if descricao else nome_comunicacao),
            'tipo_prazo': overrides.get('tipo_prazo', tipo_prazo),
            # Evitar repassar gigs_extra para não duplicar criação
            'gigs_extra': None,
            'coleta_conteudo': overrides.get('coleta_conteudo', overrides.get('coleta_conteudo_', coleta_conteudo)),
            'inserir_conteudo': overrides.get('inserir_conteudo', overrides.get('inserir_conteudo_', inserir_conteudo)),
            'cliques_polo_passivo': overrides.get('cliques_polo_passivo', cliques_polo_passivo),
            'destinatarios': destinatarios_param,
            'mudar_expediente': overrides.get('mudar_expediente', mudar_expediente),
            'checar_sp': overrides.get('checar_sp', overrides.get('checar_sp_', checar_sp)),
            'endereco_tipo': overrides.get('endereco_tipo', endereco_tipo),
            'debug': debug,
            'terceiro': overrides.get('terceiro', terceiro_default),
            'trocar_modelo': overrides.get('trocar_modelo', trocar_modelo),
            'modelo_troca_correios': overrides.get('modelo_troca_correios', modelo_troca_correios),
            'remover_endereco_invalido': overrides.get(
                'remover_endereco_invalido',
                remover_endereco_invalido if remover_endereco_invalido is not None else (
                    False if (wrapper_name == 'pec_exeq' or modelo_nome == 'xsexeq') else True
                )
            ),
            'pjdp': (overrides.get('pjdp', pjdp) if wrapper_name in ('pec_ord', 'pec_sum', 'pec_ordv', 'pec_sumv') else False),
            'wrapper_name': wrapper_name
        }

        if wrapper_name in ('pec_ord', 'pec_sum', 'pec_ordv', 'pec_sumv') and 'pjdp' not in overrides and not call_kwargs.get('pjdp'):
            try:
                if detectar_pjdp_processo(driver):
                    call_kwargs['pjdp'] = True
                    logger.info(f"[COMUNICACAO][PJDP] PJDP detectada automaticamente para wrapper {wrapper_name}")
            except Exception as e_pjdp:
                logger.warning(f"[COMUNICACAO][PJDP][WARN] Falha na detecção automática de PJDP: {e_pjdp}")

        log_fn = overrides.get('log', logger.info)

        try:
            if coleta_conteudo:
                log_fn(f"[COMUNICACAO][ORQUESTRA] Executando coleta de conteúdo na aba detalhes para {nome_comunicacao}")
                executar_coleta_conteudo(driver, coleta_conteudo, debug=debug)

            log_fn(f"[COMUNICACAO][ORQUESTRA] Abrindo minutas para {nome_comunicacao}")
            sucesso_abertura = abrir_minutas(driver, debug=debug)
            if not sucesso_abertura:
                raise Exception("Falha ao abrir tela de minutas")

            log_fn("[COMUNICACAO][ORQUESTRA] Executando preenchimento da minuta")
            executar_preenchimento_minuta(
                driver=driver,
                tipo_expediente=tipo_expediente,
                prazo=prazo,
                nome_comunicacao=nome_comunicacao,
                subtipo=subtipo,
                descricao=call_kwargs.get('descricao'),
                tipo_prazo=tipo_prazo,
                sigilo=sigilo,
                modelo_nome=modelo_nome,
                inserir_conteudo=inserir_conteudo,
                finalizar=True,
                debug=debug,
                log=log_fn
            )

            #      antes de escolher destinatários (evita corrida de cliques).
            if destinatarios_param is not None:
                if not aguardar_estabilizacao_para_destinatarios(driver, log=log_fn):
                    raise Exception('Painel de destinatários não ficou pronto (barreira) — seleção abortada')

            log_fn("[COMUNICACAO][ORQUESTRA] Selecionando destinatários")
            resultado_selecao = selecionar_destinatarios(
                driver=driver,
                destinatarios=destinatarios_param,
                cliques_polo_passivo=call_kwargs.get('cliques_polo_passivo', 1),
                cliques_informado=cliques_informado,
                debug=debug,
                log=log_fn,
                observacao=observacao,
                numero_processo=numero_processo,
                terceiro=call_kwargs.get('terceiro', False),
            )

            if destinatarios_param is not None and destinatarios_param != '':
                status = None
                count = 0
                if isinstance(resultado_selecao, dict):
                    status = resultado_selecao.get('status')
                    count = int(resultado_selecao.get('count', 0) or 0)
                else:
                    if isinstance(resultado_selecao, int):
                        status = 'ok' if resultado_selecao > 0 else 'empty'
                        count = resultado_selecao
                    elif hasattr(resultado_selecao, 'status'):
                        status = resultado_selecao.status
                        detalhes = getattr(resultado_selecao, 'detalhes', {}) or {}
                        count = int(detalhes.get('count', 0) or 0)
                    else:
                        status = 'geral'

                if status == 'ok' and count > 0:
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Status: {count} destinatário(s) selecionado(s) pelo módulo.")
                elif status == 'empty':
                    log_fn("[COMUNICACAO][ORQUESTRA] Status: Nenhum destinatário validado. Fallback acionado internamente.")
                else:
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Status: {status} selection route concluded.")

                if status in ('ok', 'fallback', 'geral') or count > 0:
                    linhas_ok = aguardar_renderizacao_nativa(
                        driver, 'tbody.cdk-drop-list tr.cdk-drag', 'aparecer', 15
                    )
                    if not linhas_ok:
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
                            terceiro=call_kwargs.get('terceiro', False),
                        )
                        linhas_ok = aguardar_renderizacao_nativa(
                            driver, 'tbody.cdk-drop-list tr.cdk-drag', 'aparecer', 15
                        )
                        if not linhas_ok:
                            raise Exception('Destinatários não adicionados ao ato (tabela vazia pós-seleção)')
                    log_fn('[COMUNICACAO][ORQUESTRA] Destinatários confirmados na tabela')

                log_fn("[COMUNICACAO][ORQUESTRA] Aguardando estabilização pós-seleção de destinatários (LEGADO L2363)...")
                espera.pausa(driver, 3.0, motivo='estabilizacao pos-selecao destinatarios (LEGADO L2363)')
                espera.assentar(driver, 1.0, motivo='estabilizacao angular pos-destinatarios')

                if status in ('ok', 'fallback', 'geral') or count > 0:
                    try:
                        ok_icone = aguardar_renderizacao_nativa(
                            driver,
                            'i.pec-icone-verde-ato-individual-tabela-destinatarios, pje-pec-tabela-destinatarios i[aria-label="Ato confeccionado"]',
                            modo='aparecer',
                            timeout=10
                        )
                        if ok_icone:
                            log_fn("[COMUNICACAO][ORQUESTRA] Ícone verde individual detectado — Salvar habilitado.")
                        else:
                            log_fn("[COMUNICACAO][ORQUESTRA] Ícone verde não detectado em 10s — prosseguindo (Salvar verificará).")
                    except Exception as e:
                        log_fn(f"[COMUNICACAO][ORQUESTRA] Erro ao aguardar renderização: {e}")

            resolved_endereco_tipo = call_kwargs.get('endereco_tipo') or endereco_tipo
            if not resolved_endereco_tipo and (call_kwargs.get('mudar_expediente') or mudar_expediente):
                resolved_endereco_tipo = 'correios'

            if resolved_endereco_tipo and 'correio' in str(resolved_endereco_tipo).lower():
                log_fn(f"[COMUNICACAO][ORQUESTRA] Alterando meio de expedição para correios (endereco_tipo={resolved_endereco_tipo})")
                _tipo_prazo = str(call_kwargs.get('tipo_prazo') or 'dias uteis').lower()
                _restabelecer = 'uteis' in _tipo_prazo or 'corridos' in _tipo_prazo
                alterar_meio_expedicao(
                    driver,
                    debug=debug,
                    log=log_fn,
                    wrapper_name=wrapper_name,
                    vincular_primeiro_endereco=call_kwargs.get('vincular_primeiro_endereco'),
                    restabelecer_prazo=_restabelecer,
                    prazo_dias=prazo,
                )

            # Requisito obrigatório: verificar a tabela após destinatários/meio de expedição e antes de salvar,
            remover_invalido = call_kwargs.get('remover_endereco_invalido', True)
            if remover_invalido:
                log_fn("[COMUNICACAO][ORQUESTRA] Verificando e removendo destinatários com endereço inválido...")
                remover_destinatarios_endereco_invalido(driver, log=log_fn, debug=debug)
            else:
                log_fn(f"[COMUNICACAO][ORQUESTRA] Exclusão de endereço inválido desativada para {wrapper_name or nome_comunicacao} (remover_endereco_invalido=False)")

            if call_kwargs.get('trocar_modelo'):
                from atos.comunicacao_finalizacao import trocar_modelo_minuta, _contar_linhas_correios
                qtd_correios = _contar_linhas_correios(driver)
                if qtd_correios > 0:
                    modelo_troca = call_kwargs.get('modelo_troca_correios')
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Trocando modelo ({qtd_correios} linha(s) Correios detectada(s))")
                    trocou = trocar_modelo_minuta(driver, modelo_troca=modelo_troca, debug=debug, log=log_fn)

                    if trocou:
                        log_fn("[COMUNICACAO][ORQUESTRA] Aguardando estabilização após troca de modelo...")
                        try:
                            esperar_elemento(driver, 'tbody.cdk-drop-list tr.cdk-drag', timeout=15, by=By.CSS_SELECTOR)
                            log_fn("[COMUNICACAO][ORQUESTRA] Página estabilizada pós-troca de modelo")
                        except Exception as e:
                            log_fn(f"[COMUNICACAO][ORQUESTRA][WARN] Erro ao aguardar estabilização: {e}")

                        from atos.comunicacao_preenchimento import aguardar_fechamento_dialogo_elaboracao, finalizar_minuta
                        if not aguardar_fechamento_dialogo_elaboracao(driver, log=log_fn, timeout=2):
                            log_fn("[COMUNICACAO][ORQUESTRA] Finalizando minuta pendente após troca de modelo")
                            if not finalizar_minuta(driver, log=log_fn):
                                raise Exception('finalizar_minuta falhou após troca de modelo — ato não finalizado')
                else:
                    log_fn("[COMUNICACAO][ORQUESTRA] Nenhuma linha de Correios detectada (destinatários por Sistema/Domicílio) — mantendo modelo original")

            _pjdp_val = call_kwargs.get('pjdp', False)
            pjdp_permitido = (wrapper_name in ('pec_ord', 'pec_sum', 'pec_ordv', 'pec_sumv'))
            pjdp_ativo = pjdp_permitido and (str(_pjdp_val).strip().lower() in ('true', 'on', '1', 'yes', 's', 'sim') if _pjdp_val is not None else False)
            if pjdp_ativo:
                log_fn(f"[COMUNICACAO][ORQUESTRA] Flag PJDP ativa para {wrapper_name} — executando inserção manual de PJDP nos destinatários...")
                inserir_destinatarios_pjdp(driver, log=log_fn, debug=debug)

            if remover_invalido:
                removidos_finais = remover_destinatarios_endereco_invalido(driver, log=log_fn, debug=debug)
                if removidos_finais > 0:
                    log_fn(f"[COMUNICACAO][ORQUESTRA] {removidos_finais} destinatário(s) adicional(is) com endereço inválido removido(s)")

            total_destinatarios_restantes = contar_linhas_destinatarios(driver)
            if total_destinatarios_restantes == 0:
                log_fn("[COMUNICACAO][ORQUESTRA][WARN] Tabela de destinatários vazia — salvamento não pode prosseguir")
                return False

            log_fn("[COMUNICACAO][ORQUESTRA] Salvando minuta final")
            _assinar_efetivo = bool(overrides.get('assinar', assinar))
            salvou_ok = salvar_minuta_final(
                driver,
                sigilo,
                debug=debug,
                log=log_fn,
                executar_visibilidade=False,
                assinar=_assinar_efetivo,
                remover_endereco_invalido=remover_invalido
            )
            if not salvou_ok:
                log_fn("[COMUNICACAO][ORQUESTRA][ERRO] Falha ao salvar/assinar minuta final.")
                return False

            try:
                handles = getattr(driver, 'window_handles', [])
                if len(handles) > 1 and _aba_original in handles:
                    _fechar_abas_tabs(driver, _aba_original)
            except Exception:
                pass

            if str(sigilo).lower() in ("sim", "true", "1"):
                try:
                    log_fn('[COMUNICACAO][ORQUESTRA] Executando visibilidade_sigilosos após fechamento da aba de minutas')
                    executar_visibilidade_sigilosos_se_necessario(driver, True, debug=debug)
                    log_fn('[COMUNICACAO][ORQUESTRA] Visibilidade extra aplicada por sigilo positivo.')
                except Exception as e_vis:
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Falha ao aplicar visibilidade extra após fechar aba: {e_vis}")

            log_fn(f"[COMUNICACAO][ORQUESTRA] Fluxo concluído com sucesso para {nome_comunicacao}")
            return True

        except Exception as e:
            log_fn(f"[COMUNICACAO][ORQUESTRA][ERRO] Falha no fluxo: {e}")
            return False
        finally:
            try:
                handles = getattr(driver, 'window_handles', [])
                if len(handles) > 1 and _aba_original in handles:
                    _fechar_abas_tabs(driver, _aba_original)
            except Exception:
                pass

    if wrapper_name:
        wrapper.__name__ = wrapper_name
    wrapper.modelo_nome = modelo_nome
    wrapper.trocar_modelo = trocar_modelo
    wrapper.modelo_troca_correios = modelo_troca_correios
    wrapper.endereco_tipo = endereco_tipo
    wrapper.pjdp = pjdp

    return wrapper


from .regras import registry
