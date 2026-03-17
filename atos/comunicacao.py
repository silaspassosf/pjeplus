import time
from Fix.extracao import criar_gigs
from Fix.log import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .comunicacao_navigation import abrir_minutas
from .comunicacao_coleta import executar_coleta_conteudo
from .comunicacao_preenchimento import executar_preenchimento_minuta
from .comunicacao_destinatarios import selecionar_destinatarios
from .comunicacao_finalizacao import alterar_meio_expedicao, salvar_minuta_final, limpar_destinatarios_existentes
from typing import Optional, Any, Callable, Union, List, Dict, Tuple
from selenium.webdriver.remote.webdriver import WebDriver


def _extrair_observacao_gigs_vencida_xs_pec(driver: WebDriver, debug: bool = False) -> Optional[str]:
    """Extrai observação da linha GIGS vencida (ícone vermelho) com XS e PEC."""
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, '#tabela-atividades tbody tr')
        for linha in linhas:
            try:
                icone_vermelho = linha.find_elements(By.CSS_SELECTOR, 'i.fa-clock.danger, i.danger.fa-clock')
                if not icone_vermelho:
                    continue

                span_descricao = linha.find_element(By.CSS_SELECTOR, 'span.descricao')
                texto_descricao = (span_descricao.text or '').strip()
                if not texto_descricao:
                    continue

                texto_lower = texto_descricao.lower()
                if 'xs' not in texto_lower:
                    continue

                if texto_lower.startswith('prazo:'):
                    texto_descricao = texto_descricao[6:].strip()

                if debug:
                    logger.info(f"[COMUNICACAO][GIGS] Observação extraída para destinatário informado: {texto_descricao}")
                return texto_descricao
            except Exception:
                continue

        if debug:
            logger.info('[COMUNICACAO][GIGS] Nenhuma linha vencida com XS+PEC encontrada no painel')
        return None
    except Exception as e:
        if debug:
            logger.info(f"[COMUNICACAO][GIGS][ERRO] Falha ao extrair observação do painel: {e}")
        return None


def comunicacao_judicial(
    driver: WebDriver,
    tipo_expediente: str, 
    prazo: int, 
    nome_comunicacao: str, 
    sigilo: str, 
    modelo_nome: str, 
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
        endereco_tipo=kwargs.get('endereco_tipo')
    )
    return wrapper_func(driver, debug=kwargs.get('debug', False), terceiro=kwargs.get('terceiro', False), **kwargs)

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
    wrapper_name: Optional[str] = None,  # Nome específico para __name__
    terceiro_default: bool = False
) -> Callable[[WebDriver, bool, Any], bool]:
    def wrapper(
        driver: WebDriver,
        numero_processo: Optional[str] = None,
        observacao: Optional[str] = None,
        destinatarios_override: Optional[List[Dict[str, Any]]] = None,
        debug: bool = False,
        **overrides: Any
    ) -> bool:
        """
        Wrapper que aceita overrides genéricos e repassa quaisquer parâmetros fornecidos
        diretamente para `comunicacao_judicial`, tratando `mudar_expediente` como um
        parâmetro comum (como `descricao`, `prazo`, etc.).
        """
        # Resolve destinatários override explicitamente se presente
        destinatarios_param = destinatarios_override if destinatarios_override is not None else (
            overrides.get('destinatarios') if 'destinatarios' in overrides else destinatarios
        )

        # Se o wrapper foi configurado com gigs_extra, executá-lo ANTES do início do fluxo
        if gigs_extra:
            try:
                if gigs_extra is True:
                    criar_gigs(driver, prazo, '', nome_comunicacao)
                elif isinstance(gigs_extra, (tuple, list)):
                    if len(gigs_extra) >= 3:
                        dias_uteis, responsavel, observacao_gigs = gigs_extra[:3]
                        criar_gigs(driver, dias_uteis, responsavel, observacao_gigs)
                    elif len(gigs_extra) == 2:
                        dias_uteis, observacao_gigs = gigs_extra
                        criar_gigs(driver, dias_uteis, '', observacao_gigs)
                    else:
                        criar_gigs(driver, gigs_extra)
                else:
                    criar_gigs(driver, gigs_extra)
            except Exception as e:
                try:
                    logger.info(f'[GIGS_WRAPPER][ERRO] Falha ao executar criar_gigs antes do fluxo: {e}')
                except Exception:
                    pass

        # Construir kwargs a serem repassados para comunicacao_judicial
        # Se o modo for 'informado' — primeiro garantir que os dados do processo
        # estejam disponíveis (populando dadosatuais.json), depois extrair a
        # observação dos GIGS. Isso permite que a comparação entre observação
        # e os dados do processo seja feita com os dados já carregados.
        dados_processo_wrapper = None
        if destinatarios_param == 'informado':
            try:
                from Fix.extracao_processo import extrair_dados_processo
                logger.info('[COMUNICACAO][ORQUESTRA] Extraindo dados do processo ANTES da leitura da observação (informado)')
                dados_processo_wrapper = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                logger.info(f"[COMUNICACAO][ORQUESTRA] extrair_dados_processo retornou tipo={type(dados_processo_wrapper)}; reu_count={len(dados_processo_wrapper.get('reu', [])) if isinstance(dados_processo_wrapper, dict) else 'N/A'}")
            except Exception as e:
                logger.info(f"[COMUNICACAO][ORQUESTRA][WARN] Falha ao extrair dados antes da observação: {e}")

            observacao_gigs = _extrair_observacao_gigs_vencida_xs_pec(driver, debug=debug)
            if observacao_gigs:
                observacao = observacao_gigs
            else:
                if not observacao or not (isinstance(observacao, str) and observacao.strip()):
                    logger.info('[COMUNICACAO][GIGS][WARN] Observação não localizada para informado - fallback polo passivo 2x')
                    destinatarios_param = 'polo_passivo_2x'
                else:
                    logger.info('[COMUNICACAO][GIGS] Observação fornecida será usada para seleção de destinatários')

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
            # Passa adiante quaisquer flags de controle (mudar_expediente, checar_sp) diretamente
            'mudar_expediente': mudar_expediente,
            'checar_sp': overrides.get('checar_sp', overrides.get('checar_sp_', checar_sp)),
            'endereco_tipo': endereco_tipo,
            'debug': debug,
            'terceiro': overrides.get('terceiro', terceiro_default)
        }

        # Executar fluxo de comunicação orquestrado pelos módulos especializados
        try:
            # 0. Executar coleta de conteúdo PRIMEIRO (na aba /detalhe)
            if coleta_conteudo:
                logger.info(f"[COMUNICACAO][ORQUESTRA] Executando coleta de conteúdo na aba detalhes para {nome_comunicacao}")
                executar_coleta_conteudo(driver, coleta_conteudo, debug=debug)

            # 1. Abrir minutas (após coleta)
            logger.info(f"[COMUNICACAO][ORQUESTRA] Abrindo minutas para {nome_comunicacao}")
            sucesso_abertura = abrir_minutas(driver, debug=debug)
            if not sucesso_abertura:
                raise Exception("Falha ao abrir tela de minutas")

            # 1.5. REMOVIDO: Limpeza de destinatários (causava travamento)
            # limpar_destinatarios_existentes(driver, debug=debug)

            # 2. Executar preenchimento da minuta
            logger.info("[COMUNICACAO][ORQUESTRA] Executando preenchimento da minuta")
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
                debug=debug,
                log=logger.info if debug else None
            )

            # 3. Selecionar destinatários (1 clique apenas)
            logger.info("[COMUNICACAO][ORQUESTRA] Selecionando destinatários")
            selecionar_destinatarios(
                driver=driver,
                destinatarios=destinatarios_param,
                cliques_polo_passivo=call_kwargs.get('cliques_polo_passivo', 1),
                cliques_informado=cliques_informado,
                debug=debug,
                log=logger.info if debug else None,
                observacao=observacao,
                numero_processo=numero_processo,
                terceiro=call_kwargs.get('terceiro', False),
                dados_processo=dados_processo_wrapper
            )

            # 3.5. AGUARDAR destinatários serem adicionados à tabela (CRÍTICO!)
            # Modos que precisam aguardar: todos exceto None
            aguardar_destinatarios = destinatarios_param is not None and destinatarios_param != ''
            
            # Modos que usam CLIQUE NO BOTÃO (têm spinner): polo_passivo, polo_ativo, primeiro
            # NÃO incluir 'extraido'/'informado' - eles só clicar botão se fallback
            aguardar_spinner = destinatarios_param in ['polo_passivo', 'polo_passivo_2x', 'polo_ativo']
            
            if aguardar_destinatarios:
                logger.info("[COMUNICACAO][ORQUESTRA] Aguardando destinatários serem adicionados à tabela...")
                from Fix.utils_sleep import aguardar_loading_sumir
                
                # DETECTAR spinner APENAS se for modo com clique
                if aguardar_spinner:
                    logger.info("[COMUNICACAO][ORQUESTRA] Aguardando spinner de carregamento após seleção...")
                    
                    # Spinner que SEMPRE aparece após clique no polo passivo
                    spinner_polo_passivo = 'div[class*="container-loading"] mat-progress-spinner'
                    
                    try:
                        # Verificar se o spinner aparece rapidamente
                        spinner_element = WebDriverWait(driver, 2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, spinner_polo_passivo))
                        )
                        logger.info("[COMUNICACAO][SPINNER] Spinner de carregamento detectado após polo passivo")
                        
                        # Aguardar o spinner específico sumir (timeout reduzido para não quebrar sessão)
                        aguardar_loading_sumir(driver, seletor_loading=spinner_polo_passivo, timeout=3)
                        logger.info("[COMUNICACAO][SPINNER] Spinner de carregamento sumiu")
                        
                    except Exception as e:
                        logger.info(f"[COMUNICACAO][SPINNER] Spinner específico não detectado ({str(e)[:50]}...) - prosseguindo")
                
                # Aguardar destinatários na tabela (reduzido para evitar timeout de sessão)
                max_espera_dest = 5 if destinatarios_param in ['extraido', 'informado'] else 10
                tempo_espera = 0
                while tempo_espera < max_espera_dest:
                    linhas_tabela = driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')
                    if len(linhas_tabela) > 0:
                        logger.info(f"[COMUNICACAO][ORQUESTRA] {len(linhas_tabela)} destinatário(s) adicionado(s) à tabela")
                        break
                    time.sleep(0.5)
                    tempo_espera += 0.5
                
                if tempo_espera >= max_espera_dest:
                    logger.warning("[COMUNICACAO][ORQUESTRA] Timeout aguardando destinatários na tabela")
                else:
                    logger.info(f"[COMUNICACAO][ORQUESTRA] Destinatários confirmados na tabela em {tempo_espera:.1f}s")

            # 4. Alterar meio de expedição se necessário
            if endereco_tipo == 'correios':
                logger.info("[COMUNICACAO][ORQUESTRA] Alterando meio de expedição para correios")
                alterar_meio_expedicao(driver, debug=debug, log=logger.info if debug else None)

            # 5. Salvar minuta final
            logger.info("[COMUNICACAO][ORQUESTRA] Salvando minuta final")
            salvar_minuta_final(driver, sigilo, debug=debug, log=logger.info if debug else None)

            logger.info(f"[COMUNICACAO][ORQUESTRA] Fluxo concluído com sucesso para {nome_comunicacao}")
            return True

        except Exception as e:
            logger.error(f"[COMUNICACAO][ORQUESTRA][ERRO] Falha no fluxo: {e}")
            raise
    
    # Definir nome específico do wrapper se fornecido
    if wrapper_name:
        wrapper.__name__ = wrapper_name
    
    return wrapper
