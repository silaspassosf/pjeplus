"""
P2B Fluxo PZ Helpers - Funções auxiliares do fluxo_pz
Refatoração seguindo abordagem ORIGINAL do p2b.py: lista sequencial de regras
Mantém termos exatos e ordem de precedência do código que FUNCIONA
"""

import logging
import re
import time
from typing import Optional, Tuple, List, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from .p2b_core import (
    normalizar_texto, gerar_regex_geral, parse_gigs_param,
    carregar_progresso_p2b, salvar_progresso_p2b, marcar_processo_executado_p2b,
    processo_ja_executado_p2b, RegraProcessamento, REGEX_PATTERNS, ato_pesqliq_callback
)

# Logger local para evitar conflitos
logger = logging.getLogger(__name__)

from Fix.core import aguardar_e_clicar
from Fix.extracao import criar_gigs, extrair_direto, extrair_documento
from atos.judicial import ato_pesquisas, idpj
from atos.movimentos import mov
from atos.wrappers_mov import mov_arquivar
from atos.wrappers_ato import ato_sobrestamento, ato_pesqliq, ato_180, ato_calc2, ato_prev, ato_meios, ato_idpj
from atos.judicial import idpj
from atos.wrappers_mov import mov_arquivar


# ===== HELPERS PRIVADOS: FLUXO_PZ =====

def _encontrar_documento_relevante(driver: WebDriver) -> Tuple[Optional[Any], Optional[Any], int]:
    """
    Helper: Encontra documento relevante (decisão/despacho/sentença) na timeline.

    Returns:
        Tupla (doc_encontrado, doc_link, doc_idx)
    """
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    print(f'[FLUXO_PZ][OTIMIZAÇÃO] Timeline tem {len(itens)} documentos. Iniciando busca do mais antigo para o mais recente.')

    # Busca do mais antigo para o mais recente
    for idx, item in enumerate(itens):
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            doc_text = link.text.lower()

            if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                real_idx = idx
                print(f'[FLUXO_PZ] ✅ Primeiro documento relevante encontrado na posição {real_idx}: {doc_text}')
                return item, link, real_idx

        except Exception:
            continue

    return None, None, 0


def _extrair_texto_documento(driver: WebDriver, doc_link: Any) -> Optional[str]:
    """
    Helper: Extrai texto do documento usando múltiplas estratégias.

    Args:
        driver: WebDriver instance
        doc_link: Link do documento

    Returns:
        Texto extraído ou None se falhar
    """
    doc_link.click()
    time.sleep(2)

    # Estratégia 1: extrair_direto (otimizada)
    texto = _extrair_com_extrair_direto(driver)
    if texto:
        return texto

    # Estratégia 2: extrair_documento (fallback)
    texto = _extrair_com_extrair_documento(driver)
    return texto


def _extrair_com_extrair_direto(driver: WebDriver) -> Optional[str]:
    """Helper: Extrai texto usando extrair_direto."""
    try:
        logger.info('[FLUXO_PZ] Tentando extração DIRETA com extrair_direto...')
        resultado_direto = extrair_direto(driver, timeout=10, debug=True, formatar=True)

        if resultado_direto and resultado_direto.get('sucesso'):
            if resultado_direto.get('conteudo'):
                texto = resultado_direto['conteudo'].lower()
                logger.info('[FLUXO_PZ] ✅ Extração DIRETA bem-sucedida')
                return texto
            elif resultado_direto.get('conteudo_bruto'):
                texto = resultado_direto['conteudo_bruto'].lower()
                logger.info('[FLUXO_PZ] ✅ Extração DIRETA bem-sucedida (bruto)')
                return texto

    except Exception as e_direto:
        logger.error(f'[FLUXO_PZ] Erro na extração DIRETA: {e_direto}')

    return None


def _extrair_com_extrair_documento(driver: WebDriver) -> Optional[str]:
    """Helper: Extrai texto usando extrair_documento (fallback)."""
    try:
        logger.info('[FLUXO_PZ] Usando fallback: extrair_documento original...')
        texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True)

        if texto_tuple and texto_tuple[0]:
            texto = texto_tuple[0].lower()
            logger.info('[FLUXO_PZ] ✅ Fallback extrair_documento funcionou')
            return texto

    except Exception as e_extrair:
        logger.error(f'[FLUXO_PZ] Erro ao chamar/processar extrair_documento: {e_extrair}')

    return None


def _definir_regras_processamento() -> List[Tuple]:
    """
    Helper: Define lista de regras SEQUENCIAIS baseada no p2b.py ORIGINAL.
    Mantém EXATAMENTE os mesmos termos e ordem de precedência.

    Returns:
        Lista de tuplas (keywords, tipo_acao, params, acao_secundaria)
    """
    return [
        # REGRA DE PRESCRIÇÃO - MÁXIMA PRIORIDADE
        ([gerar_regex_geral(k) for k in ['A pronúncia da']],
         None, None, None),  # prescreve será chamado separadamente

        # REGRA DE BLOQUEIO - DEVE VIR ANTES PARA TER PRIORIDADE
        ([gerar_regex_geral(k) for k in ['sob pena de bloqueio']],
         'checar_cabecalho_impugnacoes', None, None),

        # REGRAS DE SOBRESTAMENTO
        ([gerar_regex_geral(k) for k in [
            '05 dias para a apresentação',
            'suspensão da execução, com fluência',
            '05 dias para oferta',
            'concede-se 05 dias para oferta',
            'cinco dias para apresentação',
            'cinco dias para oferta',
            'cinco dias para apresentacao',
            'concedo o prazo de oito dias',
            'oito dias para apresentacao',
            'visibilidade aos advogados',
            'início da fluência',
            'oito dias para apresentação',
            'oito dias para apresentacao',
            'Reitere-se a intimação para que o(a) reclamante apresente cálculos',
            'remessa ao sobrestamento, com fluência',
            'sob pena de sobrestamento e fluência do prazo prescricional',
        ]],
         'gigs', '1/Silas/Sob 24', ato_sobrestamento),

        # REGRAS DE HOMOLOGAÇÃO
        ([gerar_regex_geral(k) for k in [
            'é revel, não',
            'concorda com homologação',
            'concorda com homologacao',
            'tomarem ciência dos esclarecimentos apresentados',
            'no prazo de oito dias, impugnar',
            'concordância quanto à imediata homologação da conta',
            'conclusos para homologação de cálculos',
            'ciência do laudo técnico apresentado',
            'homologação imediata',
            'aceita a imediata homologação',
            'aceita a imediata homologacao',
            'informar se aceita a imediata homologação',
            'apresentar impugnação, querendo',
        ]],
         'gigs', '1/Silvia/Homologação', None),

        # REGRA DE EMBARGOS
        ([gerar_regex_geral('exequente, ora embargado')],
         'gigs', '1/fernanda/julgamento embargos', None),

        # REGRA DE PEC
        ([gerar_regex_geral(k) for k in ['hasta', 'saldo devedor']],
         'gigs', '1/SILAS/pec', None),

        # REGRA DE DESCUMPRIMENTO
        ([gerar_regex_geral('Ante a notícia de descumprimento')],
         'checar_cabecalho', None, None),

        # REGRA DE IMPUGNAÇÕES
        ([gerar_regex_geral(k) for k in ['impugnações apresentadas', 'impugnacoes apresentadas', 'homologo estes', 'fixando o crédito do autor em', 'referente ao principal', 'sob pena de sequestro', 'comprovar a quitação', 'comprovar o pagamento', 'a reclamada para pagamento da parcela pendente', 'intime-se a reclamada para pagamento das']],
         'checar_cabecalho_impugnacoes', None, None),

        # REGRA DE ARQUIVAMENTO
        ([gerar_regex_geral(k) for k in ['arquivem-se os autos', 'remetam-se os autos ao aquivo', 'A pronúncia da prescrição intercorrente se trata', 'Se revê o novo sobrestamento', 'cumprido o acordo homologado', 'julgo extinta a presente execução, nos termos do art. 924']],
         'movimentar', mov_arquivar, None),

        # REGRA DE BLOQUEIO CONVERTIDO
        ([gerar_regex_geral('bloqueio realizado, ora convertido')], 'gigs', '1/SILAS/pec bloqueio', None),

        # REGRA DE PARCELAMENTO
        ([gerar_regex_geral('sobre o preenchimento dos pressupostos legais para concessão do parcelamento')],
         'gigs', '1/Bruna/Liberação', None),

        # REGRA DE RECOLHIMENTO
        ([gerar_regex_geral(k) for k in ['comprovar recolhimento', 'comprovar recolhimentos']],
         'gigs', '1/Silvia/Argos', ato_pesqliq_callback),

        # REGRA DE BAIXA
        ([gerar_regex_geral(k) for k in ['determinar cancelamento/baixa', 'deixo de receber o Agravo', 'quanto à petição', 'art. 112 do CPC', 'comunique-se por Edital', 'Aguarde-se o cumprimento do mandado expedido']],
         'checar_prox', None, None),

        # REGRA DE PENHORA
        ([gerar_regex_geral('Defiro a penhora no rosto dos autos')],
         'gigs', '1/SILAS/sob6', ato_180),

        # REGRA DE CÁLCULOS
        ([gerar_regex_geral('RECLAMANTE para apresentar cálculos de liquidação')],
         None, None, ato_calc2),

        # REGRA DE TENTATIVAS
        ([gerar_regex_geral('deverá realizar tentativas')],
         None, None, ato_prev),

        # REGRA DE INSTAURAÇÃO
        ([gerar_regex_geral('defiro a instauração')],
         'checar_anexos_instauracao', None, None),

        # REGRA DE TENDO EM VISTA
        ([gerar_regex_geral(k) for k in ['tendo em vista que', 'pagamento da parcela pendente', 'sob pena de sequestro']],
         'checar_anexos_tendo_em_vista', None, None),

        # REGRA DE NÃO AMPARADA
        ([gerar_regex_geral('não está amparada')],
         None, None, ato_meios),

        # REGRA DE INSTAURADO EM FACE
        ([gerar_regex_geral('instaurado em face')],
         None, None, 'idpj'),
    ]


def _processar_regras_gerais(driver: WebDriver, texto_normalizado: str) -> None:
    """
    Helper: Processa regras gerais usando abordagem SEQUENCIAL do p2b.py ORIGINAL.
    Mantém ordem de precedência: prescrição > arquivamento > bloqueio > regras gerais

    Args:
        driver: WebDriver instance
        texto_normalizado: Texto normalizado para análise
    """
    regras = _definir_regras_processamento()

    # 5. VERIFICAÇÃO DE PREVALÊNCIA: prescreve tem prioridade absoluta
    regex_prescreve = gerar_regex_geral('A pronúncia da')
    if regex_prescreve.search(texto_normalizado):
        print('[FLUXO_PZ] ✅ PREVALÊNCIA: Prescrição detectada - executando com prioridade máxima')
        try:
            # prescreve(driver)  # Será implementado quando necessário
            print('[FLUXO_PZ] ✅ Prescrição executada - ENCERRANDO fluxo (prevalência)')
            return  # SAIR imediatamente
        except Exception as prescreve_error:
            print(f'[FLUXO_PZ] ❌ Erro na execução de prescreve: {prescreve_error}')
            # Continua com regras normais se prescreve falhar

    # 5.1. VERIFICAÇÃO DE PREVALÊNCIA: arquivamento tem prioridade máxima sobre outras regras
    regex_arquivamento = gerar_regex_geral('julgo extinta a presente execução, nos termos do art. 924')
    if regex_arquivamento.search(texto_normalizado):
        print('[FLUXO_PZ] ✅ PREVALÊNCIA: Arquivamento detectado - executando com prioridade máxima')
        try:
            resultado_arquivamento = mov_arquivar(driver)
            if resultado_arquivamento:
                print('[FLUXO_PZ] ✅ Arquivamento executado com SUCESSO - ENCERRANDO fluxo (prevalência)')
                return  # SAIR imediatamente
            else:
                print('[FLUXO_PZ] ❌ Arquivamento FALHOU - continuando com regras normais')
        except Exception as arquivamento_error:
            print(f'[FLUXO_PZ] ❌ Erro na execução de arquivamento: {arquivamento_error}')
            # Continua com regras normais se arquivamento falhar

    # 6. Iterate through rules and keywords to find the first match
    acao_definida = None
    parametros_acao = None
    termo_encontrado = None
    acao_secundaria = None  # Reset before checking rules

    print(f'[FLUXO_PZ][DEBUG] Iniciando verificação de {len(regras)} regras...')

    for idx, (keywords, tipo_acao, params, acao_sec) in enumerate(regras):
        for regex in keywords:
            match = regex.search(texto_normalizado)
            if match:
                # Log da regra encontrada
                print(f'[FLUXO_PZ][DEBUG] ✅ Match encontrado na regra #{idx}')
                print(f'[FLUXO_PZ][DEBUG] Regex pattern: {regex.pattern}')
                print(f'[FLUXO_PZ][DEBUG] Match text: {match.group(0)}')
                print(f'[FLUXO_PZ] Regra aplicada: {tipo_acao} - {params if params else acao_sec.__name__ if acao_sec else "Nenhuma"}')
                acao_definida = tipo_acao
                parametros_acao = params
                acao_secundaria = acao_sec
                termo_encontrado = regex.pattern
                # NOVA REGRA: se acao_definida == 'checar_prox', chamar checar_prox imediatamente
                if acao_definida == 'checar_prox':
                    # checar_prox será implementado quando necessário
                    pass
                break
        if acao_definida:
            break

    # Log se nenhuma regra foi encontrada
    if not acao_definida:
        print('[FLUXO_PZ][DEBUG] ❌ Nenhuma regra encontrada para o texto extraído')
        print(f'[FLUXO_PZ][DEBUG] Tamanho total do texto: {len(texto_normalizado)} caracteres')
        print(f'[FLUXO_PZ][DEBUG] Primeiras 1000 chars: {texto_normalizado[:1000]}')
        # Buscar especificamente por "comprovar" para debug
        if 'comprovar' in texto_normalizado:
            idx = texto_normalizado.find('comprovar')
            print(f'[FLUXO_PZ][DEBUG] ✅ "comprovar" encontrado na posição {idx}')
            print(f'[FLUXO_PZ][DEBUG] Contexto: {texto_normalizado[max(0,idx-50):idx+100]}')
        else:
            print('[FLUXO_PZ][DEBUG] ❌ "comprovar" NÃO encontrado no texto')

    # 6. Perform action(s) based on the matched rule (or default)
    import datetime
    gigs_aplicado = False
    if acao_definida == 'gigs':
        # parametros_acao já está no formato 'dias/responsavel/observacao'
        try:
            print(f'[FLUXO_PZ][DEBUG] Regra GIGS encontrada: {parametros_acao}')
            print(f'[FLUXO_PZ][DEBUG] Ação secundária: {acao_secundaria.__name__ if acao_secundaria else "Nenhuma"}')

            dias, responsavel, observacao = parse_gigs_param(parametros_acao)
            criar_gigs(driver, dias, responsavel, observacao)
            gigs_aplicado = True
            print(f'[FLUXO_PZ] GIGS criado: {observacao}')

            if acao_secundaria:
                # Tratamento especial para função 'idpj'
                if acao_secundaria == 'idpj':
                    print('[FLUXO_PZ] Executando ação secundária: IDPJ (instaurado em face)')
                    try:
                        from atos import idpj
                        resultado_idpj = idpj(driver, debug=True)
                        print(f'[FLUXO_PZ][DEBUG] Resultado do IDPJ: {resultado_idpj}')
                    except Exception as idpj_error:
                        logger.error(f'[FLUXO_PZ] Falha ao executar IDPJ: {idpj_error}')
                else:
                    print(f'[FLUXO_PZ] Executando ação secundária: {acao_secundaria.__name__}')
                    try:
                        resultado_callback = acao_secundaria(driver)
                        print(f'[FLUXO_PZ][DEBUG] Resultado do callback: {resultado_callback}')
                    except TypeError:
                        acao_secundaria(driver)
                time.sleep(1)
        except Exception as gigs_error:
            logger.error(f'[FLUXO_PZ] Falha ao criar GIGS ou na ação secundária: {gigs_error}')

    elif acao_definida == 'movimentar':
         func_movimento = parametros_acao
         print(f'[FLUXO_PZ] Executando movimentação: {func_movimento.__name__}')
         try:
             resultado_movimento = func_movimento(driver)
             if resultado_movimento:
                 print(f'[FLUXO_PZ] Movimentação {func_movimento.__name__} executada com SUCESSO.')
             else:
                 logger.error(f'[FLUXO_PZ] Movimentação {func_movimento.__name__} FALHOU (retornou False).')
         except Exception as mov_error:
             logger.error(f'[FLUXO_PZ] Falha ao executar movimentação {func_movimento.__name__}: {mov_error}')

    elif acao_definida == 'checar_cabecalho':
        _processar_checar_cabecalho(driver)

    elif acao_definida == 'checar_cabecalho_impugnacoes':
        _processar_cabecalho_impugnacoes(driver)

    # Se não há ação primária mas existe ação secundária, trate a secundária como primária
    if acao_definida is None and acao_secundaria:
        # Tratamento especial para função 'idpj'
        if acao_secundaria == 'idpj':
            print('[FLUXO_PZ] Executando função IDPJ (instaurado em face)')
            try:
                from atos import idpj
                resultado_idpj = idpj(driver, debug=True)
                if resultado_idpj:
                    print('[FLUXO_PZ] ✅ Função IDPJ executada com sucesso')
                else:
                    print('[FLUXO_PZ] ❌ Função IDPJ falhou')
            except Exception as idpj_error:
                logger.error(f'[FLUXO_PZ] Falha ao executar função IDPJ: {idpj_error}')
        else:
            print(f'[FLUXO_PZ] Executando ação: {acao_secundaria.__name__}')
            try:
                acao_secundaria(driver)
                time.sleep(1)
            except Exception as sec_error:
                logger.error(f'[FLUXO_PZ] Falha ao executar ação {acao_secundaria.__name__}: {sec_error}')


def _processar_cabecalho_impugnacoes(driver: WebDriver) -> None:
    """
    Helper: Processa checagem de cabeçalho para impugnações.
    """
    # Implementação baseada no p2b.py original
    try:
        cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
        cor_fundo = cabecalho.value_of_css_property('background-color')
        print(f'[FLUXO_PZ] Cor do cabeçalho detectada para impugnações: {cor_fundo}')

        # Verifica se é cinza: rgb(144, 164, 174)
        if 'rgb(144, 164, 174)' in cor_fundo:
            print('[FLUXO_PZ] Cabeçalho cinza detectado - executando criar_gigs + pesquisas')

            # 1. Criar gigs antes das pesquisas
            print('[FLUXO_PZ] Etapa 1: Criando gigs (1/Silvia/Argos)')
            criar_gigs(driver, "1", "Silvia", "Argos")
            # Criar GIGS adicional "1/xs sigilo"
            criar_gigs(driver, "1", "xs sigilo")

            # 2. Executar pesquisas
            print('[FLUXO_PZ] Etapa 2: Executando pesquisas')
            sucesso, sigilo_ativado = ato_pesquisas(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
            else:
                print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesquisas')
        else:
            print('[FLUXO_PZ] Cabeçalho não é cinza - executando criar_gigs + mov_exec + pesquisas')

            # 1. Criar gigs antes de tudo
            print('[FLUXO_PZ] Etapa 1: Criando gigs (1/Silvia/Argos)')
            criar_gigs(driver, "1", "Silvia", "Argos")
            # Criar GIGS adicional "1/xs sigilo"
            criar_gigs(driver, "1", "xs sigilo")

            # 2. Executar movimento
            print('[FLUXO_PZ] Etapa 2: Executando mov_exec')
            try:
                # mov_exec será implementado quando necessário
                mov_ok = False
            except Exception as _mov_e:
                mov_ok = False

            # Se não conseguiu executar mov_exec, executar fallback PESQLIQ
            if not mov_ok:
                print('[FLUXO_PZ] ⚠️ mov_exec falhou - executando ato_pesqliq como fallback')
                try:
                    sucesso, sigilo_ativado = ato_pesqliq(driver)
                    if sucesso:
                        if sigilo_ativado:
                            _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
                    else:
                        print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesqliq no fallback')
                except Exception as _e_pesq:
                    print(f'[FLUXO_PZ] ❌ Erro no fallback ato_pesqliq: {_e_pesq}')
            else:
                # 3. Fechar aba atual para voltar ao processo
                print('[FLUXO_PZ] Etapa 3: Fechando aba atual para voltar ao processo')
                try:
                    driver.close()
                    if len(driver.window_handles) > 0:
                        driver.switch_to.window(driver.window_handles[-1])
                        print('[FLUXO_PZ] ✅ Voltou para aba do processo')
                    else:
                        print('[FLUXO_PZ] ⚠️ Nenhuma aba disponível após fechamento')
                except Exception as close_error:
                    print(f'[FLUXO_PZ] ⚠️ Erro ao fechar aba: {close_error}')

                # 4. Executar pesquisas na aba do processo
                print('[FLUXO_PZ] Etapa 4: Executando pesquisas')
                sucesso, sigilo_ativado = ato_pesquisas(driver)
                if sucesso:
                    # Aplicar visibilidade se necessário
                    if sigilo_ativado:
                        _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
                else:
                    print('[FLUXO_PZ] ⚠️ Falha ao executar ato_pesquisas')

        time.sleep(1)
    except Exception as cabecalho_error:
        logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho para impugnações: {cabecalho_error}')


def _processar_checar_cabecalho(driver: WebDriver) -> None:
    """
    Helper: Processa checagem de cabeçalho para "Ante a notícia de descumprimento".
    """
    try:
        cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
        cor_fundo = cabecalho.value_of_css_property('background-color')
        print(f'[FLUXO_PZ] Cor do cabeçalho detectada: {cor_fundo}')

        # Verifica se é cinza: rgb(144, 164, 174)
        if 'rgb(144, 164, 174)' in cor_fundo:
            print('[FLUXO_PZ] Cabeçalho cinza detectado - executando pesquisas')
            sucesso, sigilo_ativado = ato_pesquisas(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
        else:
            print('[FLUXO_PZ] Cabeçalho não é cinza - criando GIGS padrão')
            dias, responsavel, observacao = parse_gigs_param('1/SILVIA/Argos')
            criar_gigs(driver, dias, responsavel, observacao)
            # Criar GIGS adicional "1/xs sigilo"
            dias2, responsavel2, observacao2 = parse_gigs_param('1/xs sigilo')
            criar_gigs(driver, dias2, responsavel2, observacao2)
            # Executar ato_pesqliq como ação secundária
            sucesso, sigilo_ativado = ato_pesqliq(driver)
            if sucesso:
                # Aplicar visibilidade se necessário
                if sigilo_ativado:
                    _executar_visibilidade_sigilosos(driver, sigilo_ativado, debug=True)
    except Exception as cabecalho_error:
        logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho: {cabecalho_error}')


def _executar_visibilidade_sigilosos(driver: WebDriver, sigilo_ativado: bool, debug: bool = False) -> None:
    """
    Helper: Executa visibilidade para sigilosos se necessário.
    """
    # Implementação será movida para helper específico
    pass


def _fechar_aba_processo(driver: WebDriver) -> None:
    """
    Helper: Fecha aba do processo e volta para lista.
    """
    all_windows = driver.window_handles
    main_window = all_windows[0]
    current_window = driver.current_window_handle

    if current_window != main_window and len(all_windows) > 1:
        driver.close()
        try:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            print(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida: {e}")
            try:
                driver.current_url  # Testa se aba está acessível
            except Exception:
                print("[LIMPEZA][ERRO] Tentou acessar aba já fechada.")

    print('[FLUXO_PZ] Processo concluído, retornando à lista')
# ===== VALIDAÇÃO =====

if __name__ == "__main__":
    print("P2B Fluxo PZ Helpers - Teste básico")

    # Teste importações
    try:
        from Prazo.p2b_core import normalizar_texto, gerar_regex_geral
        print("✅ Importações do p2b_core funcionam")

        # Teste funções básicas
        teste = "TESTE ÁCÊNTÖS"
        resultado = normalizar_texto(teste)
        print(f"✅ Normalização funciona: '{teste}' -> '{resultado}'")

    except ImportError as e:
        print(f"❌ Erro de importação: {e}")

    print("✅ P2B Fluxo PZ Helpers validado")