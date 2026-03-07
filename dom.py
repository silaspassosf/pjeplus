# -*- coding: utf-8 -*-
"""
dom.py - Automação Dom Eletrônico (PJePlus)

Roteiro exato:
1. Driver e login PC (copiar de x.py)
2. Navegar para: https://pje.trt2.jus.br/pjekz/painel/global/todos/lista-processos
3. Aplicar filtros - usar logica e funcoes  de filtrofases e fikltro tarefa em prazo/ciclo2:
fase- conhecimento
chips(nao tarefa) - domicilio eletronico expirado, expedido e erro na transmissao (sao 3 que comçam com domicilio eletronico na lsta)
4. aplicar filtro 100 (mostrar 100 oprocessos)
5. processar lista (como se faz em mandado, por exemplo: abre porcesso, aplica acoes, fecha absas exceto a primeira, volta pra lista abre o proximo, etc)
Antes forma buckets.
5.1 bucket 1 (padrao de aud.py) - nao tem audiencia marcada, independente do tipo.
acao  ao abrir:
def_chip para pagar chips que contenham domicilio eletronico
5.2 bucket 2 - tem audiencia marcada
acoes  ao abrir:
SEMPRE - funcao def_chip para apagar chip que tem termosd ciência expirado ou resposta excedido.
a- tem lembrete com titulo Dom Eletronico:  <mat-panel-title _ngcontent-omj-c525="" class="mat-tooltip-trigger mat-expansion-panel-header-title post-it-titulo" aria-label="Título do Lembrete" aria-describedby="cdk-describedby-message-9" cdk-describedby-host=""> Dom Eletronico </mat-panel-title> - nao fazer mais nada
b- nao tem o lembrete Dom Eletronico:
- criar lembrete com titulo DomicEletr
- é ATOrd ou ACum - pec_orc
-é Asum  - pec_sumc (tb segue a logica de aud.py mas tem que usar as funcoes do projeto atual.)


)
"""
import logging
import time
from typing import List, Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Importar funções de recuperação de acesso negado
from x import verificar_acesso_negado, executar_com_recuperacao, resetar_driver
# Progresso unificado (evitar reprocessar itens já concluídos)
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    processo_ja_executado_unificado,
    marcar_processo_executado_unificado,
)

LIST_URL = 'https://pje.trt2.jus.br/pjekz/painel/global/todos/lista-processos'

def create_driver_and_login():
    """1. Driver e login PC (copiar de x.py)"""
    logger.info('[DOM] Criando driver e fazendo login...')
    try:
        from x import criar_e_logar_driver, DriverType
        driver = criar_e_logar_driver(DriverType.PC_VISIBLE)
        logger.info('[DOM] Driver criado e login realizado com sucesso')
        return driver
    except Exception as e:
        logger.error(f'[DOM] Erro ao criar driver/login: {e}')
        return None

# FLUXO ANTIGO - COMENTADO PARA MANTER HISTÓRICO
# # FLUXO ANTIGO - MANTIDO PARA HISTÓRICO (NÃO EXECUTADO)
def navigate_to_list(driver):
#     """2. Navegar para lista de processos"""
#     logger.info('[DOM] Navegando para lista de processos...')
#     driver.get(LIST_URL)
#     WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody tr.tr-class')))
#     logger.info('[DOM] Navegação concluída')

# # FLUXO ANTIGO - MANTIDO PARA HISTÓRICO (NÃO EXECUTADO)
# def apply_filters(driver):
#     """3. Aplicar filtros na ordem correta"""
#     logger.info('[DOM] Aplicando filtros...')

#     # 3.1 Fase: conhecimento
#     logger.info('[DOM] Aplicando filtro de fase: conhecimento')
#     from Fix.core import filtrofases
#     filtrofases(driver, fases_alvo=['conhecimento'])
#     time.sleep(2)  # Estabilizar

#     # 3.2 Chips: domicilio eletronico (expirado, expedido, erro na transmissao)
#     logger.info('[DOM] Aplicando filtro de chips: domicilio eletronico')
#     filtro_chips(driver, ['domicilio eletronico expirado', 'domicilio eletronico expedido', 'domicilio eletronico erro na transmissao'])
#     time.sleep(2)  # Estabilizar

#     # 3.3 Filtro 100
#     logger.info('[DOM] Aplicando filtro 100 processos por página')
#     from Fix.core import aplicar_filtro_100
#     aplicar_filtro_100(driver)
#     time.sleep(2)  # Estabilizar

#     logger.info('[DOM] Todos os filtros aplicados')

# # # def filtro_chips(driver, chips_alvo):
#     """Aplicar filtro de chips usando lógica similar ao filtrofases"""
#     try:
#         # Mapeamento dos nomes dos chips
#         chips_mapeamento = {
#             'domicilio eletronico expirado': 'Domicílio Eletrônico - Prazo de Ciência Expirado',
#             'domicilio eletronico expedido': 'Domicílio Eletrônico - Prazo de Resposta Excedido',
#             'domicilio eletronico erro na transmissao': 'Domicílio Eletrônico - Erro na Transmissão'
#         }

#         chips_alvo_mapeados = [chips_mapeamento.get(chip, chip) for chip in chips_alvo]

#         # Encontrar seletor de chips (similar ao filtrofases)
#         chips_element = None
#         try:
#             chips_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Chips')]")
#         except Exception:
#             try:
#                 seletor = 'span.ng-tns-c82-22.ng-star-inserted'
#                 for elem in driver.find_elements(By.CSS_SELECTOR, seletor):
#                     if 'Chips' in elem.text:
#                         chips_element = elem
#                         break
#             except Exception:
#                 logger.error('[DOM] Não encontrou seletor de chips')
#                 return False

#         if not chips_element:
#             logger.error('[DOM] Elemento chips não encontrado')
#             return False

#         # Clicar para abrir dropdown
#         driver.execute_script("arguments[0].click();", chips_element)
#         time.sleep(1)

#         # Aguardar painel
#         painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
#         painel = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, painel_selector)))

#         # Aguardar opções carregarem
#         time.sleep(2)

#         # Selecionar chips
#         opcoes = painel.find_elements(By.XPATH, ".//mat-option")
#         chips_selecionados = []

#         for chip in chips_alvo_mapeados:
#             for opcao in opcoes:
#                 try:
#                     texto = opcao.text.strip()
#                     if chip in texto and opcao.is_displayed():
#                         driver.execute_script("arguments[0].click();", opcao)
#                         chips_selecionados.append(chip)
#                         time.sleep(0.5)
#                         break
#                 except Exception:
#                     continue

#         # Aplicar filtro
#         try:
#             botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Filtrar"]')
#             driver.execute_script("arguments[0].click();", botao_filtrar)
#             time.sleep(2)
#         except Exception as e:
#             logger.error(f'[DOM] Erro ao clicar filtrar: {e}')
#             return False

#         logger.info(f'[DOM] Chips aplicados: {chips_selecionados}')
#         return len(chips_selecionados) > 0

#     except Exception as e:
#         logger.error(f'[DOM] Erro no filtro_chips: {e}')
#         return False

# # def collect_and_group_items(driver):
    """4. Formar buckets baseado em audiência"""
    logger.info('[DOM] Coletando lista e formando buckets...')

    # Primeiro coletar todas as linhas como WebElements
    linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
    dados = []

    for idx, linha in enumerate(linhas):
        try:
            # Extrair dados da linha usando JavaScript
            js_data = driver.execute_script("""
                var linha = arguments[0];
                var numero = '';
                var linkProcesso = linha.querySelector('pje-descricao-processo a, a[role="link"]');
                if (linkProcesso) {
                    numero = (linkProcesso.innerText || linkProcesso.textContent || '').trim();
                }

                var tem_audiencia = false;
                var audElements = linha.querySelectorAll('td, span, div');
                for (var el of audElements) {
                    var text = (el.innerText || el.textContent || '').trim();
                    if (text.includes('Audiência em:') || text.includes('Audiência')) {
                        tem_audiencia = true;
                        break;
                    }
                }

                var tipo = '';
                var spansTipo = linha.querySelectorAll('pje-descricao-processo span.align-end.ng-star-inserted');
                for (var i = 0; i < spansTipo.length; i++) {
                    var texto = (spansTipo[i].innerText || spansTipo[i].textContent || '').trim();
                    if (texto && (texto.includes('ATOrd') || texto.includes('ATSum') || texto.includes('ACum'))) {
                        tipo = texto;
                        break;
                    }
                }

                var numero_clean = numero.replace(/[^0-9]/g,'');
                return {
                    numero: numero_clean || numero,
                    numero_raw: numero,
                    tem_audiencia: tem_audiencia,
                    tipo: tipo,
                    row_index: arguments[1]
                };
            """, linha, idx)

            dados.append({
                'numero': js_data['numero'],
                'numero_raw': js_data['numero_raw'],
                'tem_audiencia': js_data['tem_audiencia'],
                'tipo': js_data['tipo'],
                'linha': linha,  # WebElement Selenium
                'row_index': js_data['row_index']
            });

        except Exception as e:
            logger.warning(f'[DOM] Erro ao processar linha {idx}: {e}')
            continue

    logger.info(f'[DOM] Coletados {len(dados)} processos')

    bucket1 = [item for item in dados if not item['tem_audiencia']]  # Sem audiência
    bucket2 = [item for item in dados if item['tem_audiencia']]     # Com audiência

    logger.info(f'[DOM] Bucket1 (sem audiência): {len(bucket1)} processos')
    logger.info(f'[DOM] Bucket2 (com audiência): {len(bucket2)} processos')

    return bucket1, bucket2

def has_dom_eletronico_reminder(driver):
    """Verificar se já existe lembrete Dom Eletronico"""
    try:
        titles = driver.find_elements(By.CSS_SELECTOR, "mat-panel-title.post-it-titulo")
        for title in titles:
            title_text = title.text.strip()
            if "Dom Eletronico" in title_text or "DomicEletr" in title_text or "DomElet" in title_text:
                return True
        return False
    except Exception:
        return False

# def process_bucket1(driver, bucket_items):
    """5.1 Bucket 1: processos sem audiência - def_chip domicilio"""
    logger.info(f'[DOM] Processando Bucket 1: {len(bucket_items)} processos sem audiência')

    if not bucket_items:
        logger.info('[DOM] Bucket 1 vazio')
        return

    def callback_bucket1(driver_detalhes):
        """Callback executado na aba de detalhes do processo"""
        numero = getattr(driver_detalhes, '_numero_processo_lista', 'desconhecido')
        logger.info(f'[DOM][B1][CALLBACK] Executando ações para {numero}')

        # Aplicar def_chip para chips domicilio eletronico
        from atos.movimentos_chips import def_chip
        chips_domicilio = [
            "Domicílio Eletrônico - Prazo de Ciência Expirado",
            "Domicílio Eletrônico - Prazo de Resposta Excedido",
            "Domicílio Eletrônico - Erro na Transmissão"
        ]
        result = def_chip(driver_detalhes, numero_processo=numero, observacao='Remover chips domicilio eletronico', chips_para_remover=chips_domicilio, debug=True)
        logger.info(f'[DOM][B1][CALLBACK] def_chip result: {result}')
        return result

    # Processar bucket usando lógica similar ao indexar_e_processar_lista
    aba_lista = driver.current_window_handle
    processados = 0

    for idx, item in enumerate(bucket_items, 1):
        numero = item['numero']
        linha = item['linha']

        logger.info(f'[DOM][B1] Processando {idx}/{len(bucket_items)}: {numero}')

        # Abrir detalhes do processo
        from Fix.extracao import abrir_detalhes_processo
        if not abrir_detalhes_processo(driver, linha):
            logger.error(f'[DOM][B1] Falha ao abrir detalhes para {numero}')
            continue

        # Aguardar nova aba
        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
        abas = driver.window_handles
        aba_detalhes = [a for a in abas if a != aba_lista][0]
        driver.switch_to.window(aba_detalhes)

        # Executar callback
        try:
            driver._numero_processo_lista = numero
            result = callback_bucket1(driver)
            if result:
                processados += 1
                logger.info(f'[DOM][B1] Callback OK para {numero}')
            else:
                logger.error(f'[DOM][B1] Callback falhou para {numero}')
        except Exception as e:
            logger.error(f'[DOM][B1] Erro no callback para {numero}: {e}')
        finally:
            if hasattr(driver, '_numero_processo_lista'):
                delattr(driver, '_numero_processo_lista')

        # DEBUG: Pausar antes de fechar o primeiro processo
        if idx == 1:
            logger.info(f'[DOM][B1] DEBUG: Pausando antes de fechar o primeiro processo {numero}')
            logger.info(f'[DOM][B1] DEBUG: Verifique a aba de detalhes - pressione Enter para continuar')
            input("DEBUG: Pressione Enter para fechar o processo e continuar...")

        # Fechar aba e voltar para lista
        driver.close()
        driver.switch_to.window(aba_lista)

    logger.info(f'[DOM][B1] Processamento concluído: {processados}/{len(bucket_items)} processos')

def is_processo_100_digital(driver):
    """Verifica se o processo é 100% digital baseado na presença da logo no cabeçalho"""
    try:
        # Seletor CSS da logo do juízo digital conforme mencionado
        logo_juizo = driver.find_elements(By.CSS_SELECTOR, 'img.logo_juizo[alt="Juizo 100% Digital"]')
        return len(logo_juizo) > 0
    except Exception as e:
        logger.warning(f'[DOM] Erro ao verificar se processo é 100% digital: {e}')
        return False

def callback_bucket2(driver_detalhes, tipo_processo='desconhecido'):
    """Callback executado na aba de detalhes do processo - versão global"""
    numero = getattr(driver_detalhes, '_numero_processo_lista', 'desconhecido')

    logger.info(f'[DOM][B2][CALLBACK] Executando ações para {numero} ({tipo_processo})')

    # SEMPRE: def_chip para ciencia expirado e resposta excedido
    from atos.movimentos_chips import def_chip
    chips_ciencia_resposta = [
        "Domicílio Eletrônico - Prazo de Ciência Expirado",
        "Domicílio Eletrônico - Prazo de Resposta Excedido"
    ]

    # Executar def_chip com debug para ver detalhes
    result_def_chip = def_chip(driver_detalhes, numero_processo=numero, observacao='Remover ciencia expirado e resposta excedido', chips_para_remover=chips_ciencia_resposta, debug=True)
    logger.info(f'[DOM][B2][CALLBACK] def_chip result: {result_def_chip}')

    # Verificar acesso negado após def_chip
    try:
        verificar_acesso_negado(driver_detalhes, f"DOM_{numero}_def_chip")
    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            logger.warning(f'[DOM][B2][CALLBACK] Acesso negado detectado após def_chip - propagando para recuperação')
            raise
        else:
            logger.error(f'[DOM][B2][CALLBACK] Erro inesperado na verificação de acesso negado: {e}')

    # Verificar lembrete Dom Eletronico - só pula criação, NÃO pula PEC
    lembrete_existe = has_dom_eletronico_reminder(driver_detalhes)
    if lembrete_existe:
        logger.info(f'[DOM][B2][CALLBACK] Já tem lembrete Dom Eletronico - pulando criação, mas executando PEC')
    else:
        # CRIAR LEMBRETE DOMICELETR se não existe lembrete Dom Eletronico
        logger.info(f'[DOM][B2][CALLBACK] Criando lembrete DomicEletr')
        from Fix.gigs import criar_lembrete_posit
        lembrete_result = criar_lembrete_posit(
            driver_detalhes,
            titulo="DomicEletr",
            conteudo="Ciência não confirmada - repetido por correio",
            debug=True
        )
        logger.info(f'[DOM][B2][CALLBACK] Lembrete criado: {lembrete_result}')

        # AGUARDAR SALVAMENTO COMPLETO DO LEMBRETE ANTES DE CONTINUAR
        if lembrete_result:
            logger.info(f'[DOM][B2][CALLBACK] Aguardando salvamento completo do lembrete...')
            time.sleep(2)  # Pausa adicional para garantir que o lembrete foi salvo
        else:
            logger.error(f'[DOM][B2][CALLBACK] Falha ao criar lembrete - mas continuando com PEC')

        # Verificar acesso negado após criação do lembrete
        try:
            verificar_acesso_negado(driver_detalhes, f"DOM_{numero}_lembrete")
        except Exception as e:
            if "RESTART_DRIVER" in str(e):
                logger.warning(f'[DOM][B2][CALLBACK] Acesso negado detectado após lembrete - propagando para recuperação')
                raise
            else:
                logger.error(f'[DOM][B2][CALLBACK] Erro inesperado na verificação de acesso negado: {e}')

    # SEMPRE executar PEC independente do lembrete

    # Verificar se o processo é 100% digital
    is_100_digital = is_processo_100_digital(driver_detalhes)
    logger.info(f'[DOM][B2][CALLBACK] Processo é 100% digital: {is_100_digital}')

    # Criar PEC baseado no tipo e se é 100% digital
    if 'ATSum' in tipo_processo:
        if is_100_digital:
            logger.info(f'[DOM][B2][CALLBACK] Criando PEC Sumária 100% digital (pec_sumc)')
            from atos.wrappers_pec import pec_sumc
            pec_wrapper = pec_sumc
        else:
            logger.info(f'[DOM][B2][CALLBACK] Criando PEC Sumária não digital (pec_sumc2)')
            from atos.wrappers_pec import pec_sumc2
            pec_wrapper = pec_sumc2
    else:
        # ATOrd, ACum ou outros tipos
        if is_100_digital:
            logger.info(f'[DOM][B2][CALLBACK] Criando PEC Ordinária 100% digital (pec_ordc)')
            from atos.wrappers_pec import pec_ordc
            pec_wrapper = pec_ordc
        else:
            logger.info(f'[DOM][B2][CALLBACK] Criando PEC Ordinária não digital (pec_ordc2)')
            from atos.wrappers_pec import pec_ordc2
            pec_wrapper = pec_ordc2

    # Verificar abas antes da PEC
    abas_antes = len(driver_detalhes.window_handles)
    logger.info(f'[DOM][B2][CALLBACK] Abas antes da PEC: {abas_antes}')

    result_pec = pec_wrapper(driver_detalhes, debug=True)
    logger.info(f'[DOM][B2][CALLBACK] PEC result: {result_pec}')

    # Verificar acesso negado após execução da PEC
    try:
        verificar_acesso_negado(driver_detalhes, f"DOM_{numero}_pec")
    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            logger.warning(f'[DOM][B2][CALLBACK] Acesso negado detectado após PEC - propagando para recuperação')
            raise
        else:
            logger.error(f'[DOM][B2][CALLBACK] Erro inesperado na verificação de acesso negado: {e}')

    # Verificar abas depois da PEC
    abas_depois = len(driver_detalhes.window_handles)
    logger.info(f'[DOM][B2][CALLBACK] Abas depois da PEC: {abas_depois}')

    if abas_depois <= abas_antes:
        logger.warning(f'[DOM][B2][CALLBACK] AVISO: Nenhuma nova aba foi aberta pela PEC!')
        return False

    return result_pec
# def process_bucket2(driver, bucket_items):
    """5.2 Bucket 2: processos com audiência - processamento individual"""
    logger.info(f'[DOM] Processando Bucket 2: {len(bucket_items)} processos com audiência')

    if not bucket_items:
        logger.info('[DOM] Bucket 2 vazio')
        return

    # Processar bucket usando lógica direta
    aba_lista = driver.current_window_handle
    processados = 0

    for idx, item in enumerate(bucket_items, 1):
        numero = item['numero']
        linha = item['linha']
        tipo = item.get('tipo', '')

        logger.info(f'[DOM][B2] Processando {idx}/{len(bucket_items)}: {numero} ({tipo})')

        # Abrir detalhes do processo
        from Fix.extracao import abrir_detalhes_processo
        if not abrir_detalhes_processo(driver, linha):
            logger.error(f'[DOM][B2] Falha ao abrir detalhes para {numero}')
            continue

        # Aguardar nova aba
        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
        abas = driver.window_handles
        aba_detalhes = [a for a in abas if a != aba_lista][0]
        driver.switch_to.window(aba_detalhes)

        # Executar callback
        try:
            driver._numero_processo_lista = numero
            result = callback_bucket2(driver, tipo)
            if result:
                processados += 1
                logger.info(f'[DOM][B2] Callback OK para {numero}')
            else:
                logger.error(f'[DOM][B2] Callback falhou para {numero}')
        except Exception as e:
            logger.error(f'[DOM][B2] Erro no callback para {numero}: {e}')
        finally:
            if hasattr(driver, '_numero_processo_lista'):
                delattr(driver, '_numero_processo_lista')

        # Fechar aba e voltar para lista
        driver.close()
        driver.switch_to.window(aba_lista)

    logger.info(f'[DOM][B2] Processamento concluído: {processados}/{len(bucket_items)} processos')

def navigate_to_activities_and_filter(driver):
    """Navegar para atividades e aplicar filtro dom.e (copiado do fluxo prazo)"""
    try:
        from Fix import aplicar_filtro_100, safe_click, esperar_elemento
        from selenium.webdriver.common.by import By
        from Fix import aguardar_e_clicar
        from selenium.webdriver.common.keys import Keys

        # 1. Navegar para painel de atividades
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        driver.get(url_atividades)
        WebDriverWait(driver, 10).until(EC.url_contains('atividades'))
        logger.info('[DOM] Navegado para painel de atividades')

        # 1.1. Remover chip "Vencidas" se existir (antes dos filtros)
        try:
            chips = driver.find_elements(By.CSS_SELECTOR, 'mat-chip')
            removido = False
            for chip in chips:
                if 'Vencidas' in chip.text:
                    btns = chip.find_elements(By.CSS_SELECTOR, 'button.chips-icone-fechar')
                    for btn in btns:
                        try:
                            if safe_click(driver, btn, timeout=5, log=False):
                                logger.info('[DOM] Chip Vencidas removido.')
                                removido = True
                                break
                        except Exception as e:
                            logger.warning(f'[DOM] Erro ao clicar no botão de fechar chip Vencidas: {e}')
                    if removido:
                        break
            if not removido:
                logger.info('[DOM] Chip Vencidas não encontrado ou já removido.')
        except Exception as e:
            logger.warning(f'[DOM] Erro ao verificar/remover chip Vencidas: {e}')

        # 3. Aplicar filtro dom.e (como P2B faz com xs - sem selecionar "Sem prazo")
        # Clicar no ícone fa-pen
        btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=10)
        if btn_fa_pen:
            safe_click(driver, btn_fa_pen)

        # Preencher campo descrição com dom.e
        campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=10)
        if campo_descricao:
            campo_descricao.clear()
            campo_descricao.send_keys('dom.e')
            campo_descricao.send_keys(Keys.ENTER)
            logger.info('[DOM] Filtro dom.e aplicado no painel de atividades')
            # Aguardar aplicação do filtro
            time.sleep(3)

        # Aplicar filtro 100
        aplicar_filtro_100(driver)
        logger.info('[DOM] Filtro 100 aplicado')
        # Aguardar estabilização após filtro 100
        time.sleep(2)

    except Exception as e:
        logger.error(f'[DOM] Erro na navegação para atividades: {e}')
        return False

    return True


def execute_list_with_bucket2_callback(driver):
    """Executar lista com callback do bucket 2 (checar lembrete, apagar chips, PEC)

    Melhorias adicionadas:
    - garante navegação para a lista quando necessário
    - utiliza monitoramento unificado por item
    - aplica delays anti-rate entre itens
    """
    try:
        from Fix import indexar_processos, abrir_detalhes_processo, reindexar_linha
        from Fix.abas import trocar_para_nova_aba

        # Verificar se estamos no painel de atividades; preferir esse fluxo
        try:
            cur = (driver.current_url or '').lower()
            if 'atividades' in cur:
                logger.info('[DOM] Executando fluxo no painel de atividades (dom.e)')
            elif 'lista-processos' in cur:
                logger.info('[DOM] Página é a lista de processos — prosseguindo com indexação (compatível)')
            else:
                logger.info('[DOM] Página atual não é painel de atividades nem lista; navegando para painel de atividades e aplicando filtro dom.e')
                if not navigate_to_activities_and_filter(driver):
                    logger.error('[DOM] Falha ao navegar para painel de atividades')
                    return False
                time.sleep(1)
        except Exception as _e:
            logger.debug(f'[DOM] Erro no pre-check de página: {_e}')

        # 1. Indexar processos
        processos = indexar_processos(driver)
        if not processos:
            logger.warning('[DOM] Nenhum processo encontrado na lista')
            return False

        logger.info(f'[DOM] {len(processos)} processos encontrados para processamento')

        # 2. Processar lista usando função utilitária padronizada com corte em erros críticos
        aba_lista_original = driver.current_window_handle

        # Converter lista de processos para formato esperado pela função utilitária
        lista_itens = [{"id": proc_id, "linha": linha} for proc_id, linha in processos]

        def processar_item_dom(driver_param, item):
            # Usar monitoramento unificado para pular itens já processados e marcar progresso
            from Fix.monitoramento_progresso_unificado import executar_com_monitoramento_unificado

            proc_id = item["id"]
            sucesso, numero = executar_com_monitoramento_unificado(
                'm1',
                driver_param,
                proc_id,
                processar_processo_dom,
                proc_id,
                item["linha"],
                aba_lista_original,
                suppress_load_log=True
            )

            # Pequeno delay entre itens para reduzir chance de rate-limit / ACESSO_NEGADO
            try:
                time.sleep(1.25)
            except Exception:
                pass

            return bool(sucesso)

        # Usar função padronizada que interrompe automaticamente em erros críticos
        from utilitarios_processamento import executar_processamento_iterativo_com_corte_em_erro_critico
        resultados = executar_processamento_iterativo_com_corte_em_erro_critico(
            driver=driver,
            nome_modulo="DOM",
            lista_itens=lista_itens,
            funcao_processamento_item=processar_item_dom,
            max_tentativas_recuperacao=2
        )

        # Verificar se foi interrompido por erro crítico
        if resultados["interrompido_por_erro_critico"]:
            logger.error(f'[DOM] Processamento interrompido por erro crítico - {resultados["erros"]} erros em {resultados["total_itens"]} itens')
            return False

        logger.info(f'[DOM] Processamento concluído: {resultados["processados"]} sucesso, {resultados["erros"]} erros')
        return resultados["erros"] == 0

    except Exception as e:
        logger.error(f'[DOM] Erro na execução da lista: {e}')
        return False

def processar_processo_dom(driver, proc_id, linha, aba_lista_original):
    """
    Processa um único processo DOM com recuperação de acesso negado.

    Args:
        driver: WebDriver instance
        proc_id: ID do processo
        linha: Elemento da linha na tabela
        aba_lista_original: Handle da aba da lista

    Returns:
        bool: True se processado com sucesso
    """
    try:
        logger.info(f'[DOM] Processando processo: {proc_id}')

        # --- PROGRESSO UNIFICADO: pular itens já processados ou marcados com erro
        try:
            progresso = carregar_progresso_unificado('m1', suppress_load_log=True)
            if processo_ja_executado_unificado(proc_id, progresso):
                logger.info(f'[DOM] Processo {proc_id} já registrado como executado; pulando')
                return True
            if processo_tem_erro_unificado(proc_id, progresso):
                logger.info(f'[DOM] Processo {proc_id} previamente marcado com erro — será reprocessado')
        except Exception as _e:
            logger.debug(f'[DOM] Não foi possível consultar progresso unificado: {_e}')

        # Reindexar linha se necessário (cuidar de erros de conexão)
        from Fix import reindexar_linha
        try:
            linha.is_displayed()
            linha_atual = linha
        except Exception as _e:
            try:
                linha_atual = reindexar_linha(driver, proc_id)
            except Exception as re_e:
                msg = str(re_e)
                logger.error(f'[DOM] Erro geral na reindexação: {msg}')
                if 'Tried to run command without establishing a connection' in msg or 'disconnected' in msg.lower():
                    # Forçar reinício do driver
                    raise Exception(f'RESTART_DRIVER: reindex_failed ({msg})')
                return False

            if not linha_atual:
                logger.error(f'[DOM] Não foi possível reindexar linha para {proc_id}')
                return False

        # Abrir detalhes do processo (tratar possíveis desconexões)
        from Fix.extracao import abrir_detalhes_processo
        try:
            if not abrir_detalhes_processo(driver, linha_atual):
                logger.error(f'[DOM] Falha ao abrir detalhes para {proc_id}')
                return False
        except Exception as e_open:
            msg = str(e_open)
            logger.error(f'[DOM] Erro ao abrir detalhes para {proc_id}: {msg}')
            if 'Tried to run command without establishing a connection' in msg or 'disconnected' in msg.lower():
                raise Exception(f'RESTART_DRIVER: abrir_detalhes_failed ({msg})')
            return False

        # Aguardar nova aba
        from Fix.abas import trocar_para_nova_aba
        try:
            nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
        except Exception as e_tab:
            msg = str(e_tab)
            logger.error(f'[DOM] Erro ao trocar para nova aba em {proc_id}: {msg}')
            if 'Tried to run command without establishing a connection' in msg or 'disconnected' in msg.lower():
                raise Exception(f'RESTART_DRIVER: trocar_para_nova_aba_failed ({msg})')
            return False

        if not nova_aba:
            logger.error(f'[DOM] Nova aba não carregou para {proc_id}')
            return False

        # Extrair tipo do processo da aba de detalhes (mais confiável)
        tipo_processo = 'ATOrd'  # padrão
        try:
            # Aguardar o cabeçalho do processo carregar
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-cabecalho-processo'))
            )

            # Extrair tipo do cabeçalho do processo
            tipo_js = driver.execute_script("""
                var cabecalho = document.querySelector('pje-cabecalho-processo');
                if (cabecalho) {
                    var spansTipo = cabecalho.querySelectorAll('pje-descricao-processo span.align-end.ng-star-inserted');
                    for (var i = 0; i < spansTipo.length; i++) {
                        var texto = (spansTipo[i].innerText || spansTipo[i].textContent || '').trim();
                        if (texto && (texto.includes('ATOrd') || texto.includes('ATSum') || texto.includes('ACum'))) {
                            return texto;
                        }
                    }
                }
                return '';
            """)

            if tipo_js:
                tipo_processo = tipo_js.strip()
                logger.info(f'[DOM] Tipo identificado na aba de detalhes: {tipo_processo}')
            else:
                logger.warning(f'[DOM] Tipo não identificado na aba de detalhes para {proc_id}, usando padrão ATOrd')
                tipo_processo = 'ATOrd'
        except Exception as e:
            logger.warning(f'[DOM] Erro ao extrair tipo da aba de detalhes para {proc_id}: {e}, usando padrão ATOrd')
            tipo_processo = 'ATOrd'

        # Executar callback do bucket 2
        try:
            driver._numero_processo_lista = proc_id
            result = callback_bucket2(driver, tipo_processo)
            if result:
                logger.info(f'[DOM] Callback OK para {proc_id}')
                # Marcar como executado no progresso unificado
                try:
                    progresso = carregar_progresso_unificado('m1', suppress_load_log=True)
                    marcar_processo_executado_unificado('m1', proc_id, progresso, sucesso=True)
                except Exception as _e:
                    logger.debug(f'[DOM] Falha ao marcar progresso como executado: {_e}')
                return True
            else:
                logger.error(f'[DOM] Callback falhou para {proc_id}')
                # Marcar como erro no progresso unificado
                try:
                    progresso = carregar_progresso_unificado('m1', suppress_load_log=True)
                    marcar_processo_executado_unificado('m1', proc_id, progresso, sucesso=False)
                except Exception as _e:
                    logger.debug(f'[DOM] Falha ao marcar progresso como erro: {_e}')
                return False
        except Exception as e:
            # Se é RESTART_DRIVER, propagar para recuperação
            if "RESTART_DRIVER" in str(e):
                logger.warning(f'[DOM] Acesso negado detectado no callback para {proc_id} - propagando para recuperação')
                raise
            # Outras exceções são erros do callback
            logger.error(f'[DOM] Erro no callback para {proc_id}: {e}')
            return False
        finally:
            if hasattr(driver, '_numero_processo_lista'):
                delattr(driver, '_numero_processo_lista')

    except Exception as e:
        msg = str(e)
        logger.error(f'[DOM] Erro geral no processamento de {proc_id}: {msg}')
        # Se detectamos perda de conexão do WebDriver, propagar para recuperação global
        if 'Tried to run command without establishing a connection' in msg or 'RESTART_DRIVER' in msg or 'disconnected' in msg.lower():
            raise Exception(f'RESTART_DRIVER: {msg}')
        return False
    finally:
        # Gerenciar abas após processamento (fechar todas exceto lista)
        _gerenciar_abas_apos_processo_dom(driver, aba_lista_original)


def _gerenciar_abas_apos_processo_dom(driver: WebDriver, aba_lista_original: str):
    """
    Helper: Gerencia abas após processamento de um processo no DOM.
    Fecha todas as abas exceto a da lista original.

    Args:
        driver: WebDriver instance
        aba_lista_original: Handle da aba da lista
    """
    try:
        # Verificar handles válidos
        try:
            handles = list(driver.window_handles)
        except Exception as _e:
            logger.error(f'[DOM] Driver desconectado ao ler window_handles: {_e}')
            raise Exception(f'RESTART_DRIVER: driver_disconnect ({_e})')

        if aba_lista_original not in handles:
            logger.error(f'[DOM] Aba da lista não está mais disponível')
            raise Exception(f'RESTART_DRIVER: aba_lista_original_missing')

        # Fechar outras abas com cuidado
        for handle in handles:
            if handle == aba_lista_original:
                continue
            try:
                driver.switch_to.window(handle)
                time.sleep(0.25)  # pequena pausa antes de fechar
                driver.close()
                logger.info(f'[DOM] Aba fechada: {handle[:20]}...')
            except Exception as e:
                # Problema ao manipular aba — tratar como perda de driver se for erro de conexão
                msg = str(e)
                logger.warning(f'[DOM] Erro ao fechar aba {handle[:20]}...: {msg}')
                if 'Tried to run command without establishing a connection' in msg or 'disconnected' in msg.lower():
                    raise Exception(f'RESTART_DRIVER: {msg}')
                # caso contrário, continuar tentando fechar as demais abas
                continue

        # Retornar à aba da lista e aguardar estabilização do DOM
        try:
            driver.switch_to.window(aba_lista_original)
        except Exception as e:
            logger.error(f'[DOM] Falha ao retornar para aba da lista: {e}')
            raise Exception(f'RESTART_DRIVER: switch_to_failed ({e})')

        # Pequena espera para evitar rate-limit e dar tempo ao SPA atualizar a lista
        time.sleep(2.0)
        try:
            WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.cdk-drag')))
        except Exception:
            logger.debug('[DOM] Timeout: tabela de processos pode não estar visível imediatamente (seguindo)')

        logger.info(f'[DOM] Retornado à aba da lista')

    except Exception as e:
        # Propagar RESTART_DRIVER para que o orquestrador reinicie o driver
        if 'RESTART_DRIVER' in str(e):
            raise
        logger.error(f'[DOM] Falha ao gerenciar abas: {e}')
        raise

def main():
    """Fluxo principal seguindo o roteiro exato"""
    logger.info('[DOM] === INICIANDO DOM.PY ===')

    # 1. Driver e login
    driver = create_driver_and_login()
    if not driver:
        logger.error('[DOM] Abortando - driver não criado')
        return False

    try:
        # 2. Navegar para atividades e aplicar filtros
        navigate_to_activities_and_filter(driver)

        # 3. Executar lista com callback do bucket 2
        execute_list_with_bucket2_callback(driver)

        logger.info('[DOM] === EXECUÇÃO CONCLUÍDA COM SUCESSO ===')
        return True

    except Exception as e:
        logger.error(f'[DOM] Erro geral: {e}')
        return False

    finally:
        if driver:
            try:
                driver.quit()
                logger.info('[DOM] Driver fechado')
            except:
                pass

if __name__ == '__main__':
    main()