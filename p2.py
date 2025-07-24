import sys
import os
from datetime import datetime

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado  
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.  
# Evitar modificações em arquivos não explicitamente mencionados.  
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).  
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem ‘melhorias’ não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente


from Fix import login_pc, driver_notebook, aplicar_filtro_100, indexar_e_processar_lista, extrair_dados_processo, finalizar_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import logging
import os
from Fix import esperar_elemento, safe_click
from Fix import criar_gigs, login_pc, aplicar_filtro_100
from Fix import extrair_documento, esperar_elemento, safe_click, criar_gigs, indexar_e_processar_lista, login_notebook, aplicar_filtro_100
from atos import pesquisas, ato_sobrestamento, ato_180, mov_arquivar, mov_exec, ato_pesqliq, ato_calc2, ato_prev, ato_meios, ato_termoS, ato_termoE
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from Fix import driver_pc, login_pc
from driver_config import criar_driver, login_func

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('pje_automacao.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AutomacaoPJe')

def parse_gigs_param(param):
    """
    Recebe uma string no formato 'dias/responsavel/observacao' e retorna (dias, responsavel, observacao).
    Se não houver responsável, deve ser 'dias/-/observacao'.
    """
    if isinstance(param, str) and param.count('/') >= 2:
        partes = param.split('/', 2)
        try:
            dias = int(partes[0]) if partes[0].isdigit() else 0
        except Exception:
            dias = 0
        responsavel = partes[1].strip()
        observacao = partes[2].strip()
        return dias, responsavel, observacao
    # fallback: dias=0, responsavel='', observacao=param
    return 0, '', param

def checar_anexos_tendo_em_vista():
    """
    Verifica se existem documentos sigilosos em pesquisa patrimonial
    e chama a função apropriada baseada no resultado.
    """
    global driver
    sigiloso = checar_anexos(driver)
    
    if sigiloso == 'nao':
        # Não há documentos sigilosos, chama ato_meios
        ato_meios()
    elif sigiloso == 'sim':
        # Há documentos sigilosos, chama ato_termoE
        ato_termoE()
    else:
        # Caso de erro ou não encontrado
        print(f"checar_anexos retornou valor inesperado: {sigiloso}")
        print("Não foi possível determinar se há documentos sigilosos")

def checar_anexos_instauracao():
    """
    Verifica se existem documentos sigilosos em pesquisa patrimonial
    e chama a função apropriada baseada no resultado.
    """
    global driver
    sigiloso = checar_anexos(driver)
    
    if sigiloso == 'nao':
        # Não há documentos sigilosos, chama ato_meios
        ato_meios()
    elif sigiloso == 'sim':
        # Há documentos sigilosos, chama ato_termoS
        ato_termoS()
    else:
        # Caso de erro ou não encontrado
        print(f"checar_anexos retornou valor inesperado: {sigiloso}")
        print("Não foi possível determinar se há documentos sigilosos")

def checar_anexos(driver, log=True):
    """
    Função que seleciona 'pesquisa patrimonial' na timeline, abre seus anexos,
    verifica se há documentos sigilosos e retorna 'sim' ou 'nao'.
    
    Args:
        driver: WebDriver do Selenium
        log: Boolean para ativar logs detalhados
        
    Returns:
        str: 'sim' se houver anexos sigilosos, 'nao' caso contrário
    """
    if log:
        print('[CHECAR_ANEXOS] Iniciando verificação de anexos sigilosos...')
    
    try:
        # 1. Seleciona "pesquisa patrimonial" na timeline
        if log:
            print('[CHECAR_ANEXOS] 1. Buscando documento "pesquisa patrimonial" na timeline...')
        
        # Busca itens da timeline
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        documento_encontrado = None
        
        for item in itens_timeline:
            try:
                # Busca link do documento
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                texto_documento = link.text.lower()
                
                # Verifica se é pesquisa patrimonial (apenas este termo)
                if 'pesquisa patrimonial' in texto_documento:
                    documento_encontrado = item
                    if log:
                        print(f'[CHECAR_ANEXOS] ✓ Documento encontrado: {link.text}')
                    break  # Para na primeira ocorrência
            except Exception:
                continue
        
        if not documento_encontrado:
            if log:
                print('[CHECAR_ANEXOS] ❌ Documento "pesquisa patrimonial" não encontrado na timeline')
            return 'nao'
        
        # 2. Abre os anexos do documento
        if log:
            print('[CHECAR_ANEXOS] 2. Abrindo anexos do documento...')
        
        btn_anexos = documento_encontrado.find_elements(By.CSS_SELECTOR, "pje-timeline-anexos > div > div")
        if not btn_anexos:
            if log:
                print('[CHECAR_ANEXOS] ❌ Botão de anexos não encontrado')
            return 'nao'
        
        safe_click(driver, btn_anexos[0])
        time.sleep(2)
        
        # 3. Verifica se há documentos sigilosos nos anexos
        if log:
            print('[CHECAR_ANEXOS] 3. Verificando anexos sigilosos...')
        
        anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
        
        if not anexos:
            if log:
                print('[CHECAR_ANEXOS] ❌ Nenhum anexo encontrado')
            return 'nao'
        
        if log:
            print(f'[CHECAR_ANEXOS] ✓ Encontrados {len(anexos)} anexos')
        
        # Tipos de anexos que devem ser considerados sigilosos
        tipos_sigilosos = ["infojud", "doi", "irpf", "ir2022", "ir2023", "ir2024", "dimob", "ecac", "efinanceira", "e-financeira"]
        
        tem_sigiloso = False
        
        for anexo in anexos:
            try:
                texto_anexo = anexo.text.strip().lower()
                if log:
                    print(f'[CHECAR_ANEXOS] Verificando anexo: {texto_anexo}')
                
                # Verifica se é um tipo de anexo sigiloso
                for tipo in tipos_sigilosos:
                    if tipo in texto_anexo:
                        if log:
                            print(f'[CHECAR_ANEXOS] ✓ Anexo sigiloso encontrado: {tipo} em "{texto_anexo}"')
                        
                        # Verifica se já tem sigilo aplicado (ícone vermelho)
                        btn_sigilo = anexo.find_elements(By.CSS_SELECTOR, "i.fa-wpexplorer")
                        if btn_sigilo:
                            if "tl-nao-sigiloso" in btn_sigilo[0].get_attribute("class"):
                                # Ícone azul - não tem sigilo
                                if log:
                                    print(f'[CHECAR_ANEXOS] Anexo sem sigilo aplicado: {texto_anexo}')
                            else:
                                # Ícone vermelho - já tem sigilo
                                tem_sigiloso = True
                                if log:
                                    print(f'[CHECAR_ANEXOS] ✓ Anexo com sigilo já aplicado: {texto_anexo}')
                        else:
                            # Considera sigiloso por tipo, mesmo sem ícone
                            tem_sigiloso = True
                            if log:
                                print(f'[CHECAR_ANEXOS] ✓ Anexo considerado sigiloso por tipo: {texto_anexo}')
                        
                        break  # Para no primeiro tipo encontrado
                        
            except Exception as e:
                if log:
                    print(f'[CHECAR_ANEXOS] Erro ao verificar anexo: {e}')
                continue
        
        # 4. Retorna resultado
        resultado = 'sim' if tem_sigiloso else 'nao'
        if log:
            print(f'[CHECAR_ANEXOS] ✓ Resultado final: {resultado}')
            if tem_sigiloso:
                print('[CHECAR_ANEXOS] Documentos sigilosos encontrados nos anexos')
            else:
                print('[CHECAR_ANEXOS] Nenhum documento sigiloso encontrado nos anexos')
        
        return resultado
        
    except Exception as e:
        if log:
            print(f'[CHECAR_ANEXOS] ❌ Erro durante verificação: {e}')
        return 'nao'

def checar_prox(driver, itens, doc_idx, regras, texto_normalizado):
    """
    Checa se há próximo documento relevante na timeline e retorna (doc_encontrado, doc_link, doc_idx) se houver.
    Executa apenas uma vez por chamada.
    """
    doc_encontrado = None
    doc_link = None
    next_idx = doc_idx + 1
    if next_idx < len(itens):
        for idx, item in enumerate(itens[next_idx:], next_idx):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = any('otavio' in mag.get_attribute('aria-label').lower() or 'mariana' in mag.get_attribute('aria-label').lower() for mag in mag_icons)
                if mag_ok:
                    doc_encontrado = item
                    doc_link = link
                    doc_idx = idx
                    break
            except Exception:
                continue
    return doc_encontrado, doc_link, doc_idx

def fluxo_pz(driver):
    """
    Processa prazos detalhados em processos abertos.
    Usa extrair_documento para obter texto, analisa regras,
    cria GIGS parametrizadas, executa atos sequenciais e fecha aba.
    """
    acao_secundaria = None
    texto = None # Initialize texto as None    # 1. Seleciona documento relevante (decisão, despacho ou sentença)
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    doc_encontrado = None
    doc_link = None
    doc_idx = 0
    while True:
        for idx, item in enumerate(itens[doc_idx:], doc_idx):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = any('otavio' in mag.get_attribute('aria-label').lower() or 'mariana' in mag.get_attribute('aria-label').lower() for mag in mag_icons)
                if mag_ok:
                    doc_encontrado = item
                    doc_link = link
                    doc_idx = idx
                    break
            except Exception:
                continue
        
        if not doc_encontrado or not doc_link:
            logger.error('[FLUXO_PZ] Nenhum documento relevante encontrado.')
            return

        doc_link.click()
        time.sleep(2) # Wait for panel/URL to load
        
        # 2. Extrair texto usando a função de Fix.py
        import datetime
        texto_tuple = None # Initialize tuple variable
        try:
            texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True) # timeout reduzido
            if texto_tuple and texto_tuple[0]:
                texto = texto_tuple[0].lower()
            else:
                logger.error('[FLUXO_PZ] extrair_documento retornou None ou texto vazio.')
                texto = None
        except Exception as e_extrair:
            logger.error(f'[FLUXO_PZ] Erro ao chamar/processar extrair_documento: {e_extrair}')
            texto = None
        
        if not texto:
            logger.error('[FLUXO_PZ] Não foi possível extrair o texto do documento via extrair_documento.')
            return
        
        # Log do texto extraído (início apenas)
        log_texto = texto[:200] + '...' if len(texto) > 200 else texto
        print(f'[FLUXO_PZ] Texto extraído: {log_texto}')

        # 4. Define as regras com parâmetros e ações sequenciais
        def remover_acentos(txt):
            import unicodedata
            return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

        def normalizar_texto(txt):
            return remover_acentos(txt.lower())

        texto_normalizado = normalizar_texto(texto)

        def gerar_regex_geral(termo):
            # Remove acentos e deixa minúsculo para o termo
            termo_norm = normalizar_texto(termo)
            # Divide termo em palavras
            palavras = termo_norm.split()
            # Monta regex permitindo pontuação, vírgula, etc. entre as palavras
            partes = [re.escape(p) for p in palavras]
            # Entre cada palavra, aceita qualquer quantidade de espaços, pontuação, vírgula, etc.
            regex = r''
            for i, parte in enumerate(partes):
                regex += parte
                if i < len(partes) - 1:                regex += r'[\s\.,;:!\-–—]*'
            # Permite o trecho em qualquer lugar do texto (texto antes/depois)
            return re.compile(rf"{regex}", re.IGNORECASE)

        regras = [
            ([gerar_regex_geral(k) for k in [
                '05 dias para a apresentação',
                '05 dias para oferta',
                'concede-se 05 dias para oferta',
                'cinco dias para apresentação',
                'cinco dias para oferta',
                'cinco dias para apresentacao',
                'concedo cinco dias',
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
             'gigs', '1/Silas/Sobrestamento', ato_sobrestamento),
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
                'informar se aceita a imediata homologacao',
            ]],
             'gigs', '1/Silvia/Homologação', None),
            ([gerar_regex_geral('exequente, ora embargado')],
             'gigs', '1/fernanda/julgamento embargos', None),
            ([gerar_regex_geral(k) for k in ['hasta', 'saldo devedor']],
             'gigs', '1/SILAS/pec', None),
            ([gerar_regex_geral('Ante a notícia de descumprimento')],
             'checar_cabecalho', None, None),
            ([gerar_regex_geral(k) for k in ['impugnações apresentadas', 'impugnacoes apresentadas', 'homologo estes', 'fixando o crédito do autor em', 'referente ao principal', 'sob pena de sequestro', 'comprovar a quitação', 'comprovar o pagamento', 'a reclamada para pagamento da parcela pendente', 'intime-se a reclamada para pagamento das']],
             'checar_cabecalho_impugnacoes', None, None),          
            ([gerar_regex_geral(k) for k in ['arquivem-se os autos', ' remetam-se os autos ao aquivo', 'A pronúncia da prescrição intercorrente se trata', 'Se revê o novo sobrestamento', 'cumprido o acordo homologado', 'julgo extinta a presente execução, nos termos do art. 924']],
             'movimentar', mov_arquivar, None),
            ([gerar_regex_geral(k) for k in ['bloqueio realizado, ora convertido']], 'gigs', '1/SILAS/pec bloqueio', None),
            ([gerar_regex_geral(k) for k in ['sobre o preenchimento dos pressupostos legais para concessão do parcelamento']],
             'gigs', '1/Bruna/Liberação', None),
            ([gerar_regex_geral(k) for k in ['comprovar o recolhimento', 'comprovar os recolhimentos']],
             'gigs', '1/Silvia/Argos', ato_pesqliq),
            ([gerar_regex_geral(k) for k in ['determinar cancelamento/baixa', 'deixo de receber o Agravo', 'quanto à petição', 'art. 112 do CPC', 'comunique-se por Edital']],
             'checar_prox', None, None),
            ([gerar_regex_geral(k) for k in ['Defiro a penhora no rosto dos autos']],
             'gigs', '1/SILAS/sob6', ato_180),
            ([gerar_regex_geral(k) for k in ['RECLAMANTE para apresentar cálculos de liquidação']],
             None, None, ato_calc2),
            ([gerar_regex_geral('deverá realizar tentativas')],
             None, None, ato_prev),
            ([gerar_regex_geral('defiro a instauração')],
             'checar_anexos_instauracao', None, None),
            ([gerar_regex_geral('tendo em vista que')],
             'checar_anexos_tendo_em_vista', None, None),
        ]
        # ...restante do código...
        if 'bloqueio de valores realizado, ora' in texto:
            try:
                # 0. Extrair dados do processo
                from Fix import extrair_dados_processo
                dados_processo = extrair_dados_processo(driver)
                  # Verificação simplificada de advogados (dados detalhados salvos em JSON)
                parte_sem_advogado = False
                partes_passivas = []
                if dados_processo and 'partes' in dados_processo:
                    partes_data = dados_processo['partes']
                    if isinstance(partes_data, dict):
                        partes_passivas = partes_data.get('passivas', [])
                    elif isinstance(partes_data, list):
                        partes_passivas = partes_data
                    else:
                        partes_passivas = []
                    partes_sem_advogado = [p for p in partes_passivas if not p.get('representantes')]
                    parte_sem_advogado = len(partes_sem_advogado) > 0                
                # Verificar item mais recente da timeline
                itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                primeiro_item = itens[0] if itens else None
                
                if primeiro_item:
                    primeiro_item_text = primeiro_item.text.lower()
                    
                    # Hipótese 1: GIGS Bruna - Liberação
                    if any(termo in primeiro_item_text for termo in ['edital', 'certidão de oficial de justiça', 'certidao de oficial de justica']):
                        print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação')
                        dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                        criar_gigs(driver, dias, responsavel, observacao)
                    elif 'intimação' in primeiro_item_text or 'intimacao' in primeiro_item_text:
                        # Verificar se é intimação de correio via carta()
                        from carta import carta
                        carta_result = carta(driver)
                        if carta_result:  # Se carta() encontrou intimação de correio
                            print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação (correio)')
                            dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                            criar_gigs(driver, dias, responsavel, observacao)
                        else:
                            # Verificar se há despacho anterior na timeline para condição "xs pec bloqueio"
                            despacho_encontrado = False
                            if len(itens) > 1:  # Verificar se há mais itens na timeline
                                for i, item_timeline in enumerate(itens[1:], 1):  # Começar do segundo item
                                    item_text = item_timeline.text.lower()
                                    if 'despacho' in item_text:
                                        despacho_encontrado = True
                                        break
                            # Hipótese 2: parte sem advogado + despacho → GIGS "xs pec bloqueio"
                            if parte_sem_advogado and despacho_encontrado:
                                print('[FLUXO_PZ] Regra: Bloqueio realizado - SILAS/pec bloqueio')
                                dias, responsavel, observacao = parse_gigs_param('1/SILAS/pec bloqueio')
                                criar_gigs(driver, dias, responsavel, observacao)
                            else:
                                print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação (padrão)')
                                dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                                criar_gigs(driver, dias, responsavel, observacao)
                    else:
                        # Hipótese 2: verificar despacho + parte sem advogado
                        if parte_sem_advogado and 'despacho' in primeiro_item_text:
                            print('[FLUXO_PZ] Regra: Bloqueio realizado - xs/pec bloqueio')
                            dias, responsavel, observacao = parse_gigs_param('1/xs/pec bloqueio')
                            criar_gigs(driver, dias, responsavel, observacao)
                        else:
                            print('[FLUXO_PZ] Regra: Bloqueio realizado - Bruna/Liberação (caso padrão)')
                            dias, responsavel, observacao = parse_gigs_param('1/Bruna/Liberação')
                            criar_gigs(driver, dias, responsavel, observacao)
                
                return
            except Exception as bloqueio_error:
                logger.error(f'[FLUXO_PZ] Erro na regra especial de bloqueio: {bloqueio_error}')
                raise

        # 5. Iterate through rules and keywords to find the first match
        acao_definida = None
        parametros_acao = None
        termo_encontrado = None
        acao_secundaria = None  # Reset before checking rules
        for keywords, tipo_acao, params, acao_sec in regras:
            for regex in keywords:
                match = regex.search(texto_normalizado)
                if match:
                    # Log da regra encontrada
                    print(f'[FLUXO_PZ] Regra aplicada: {tipo_acao} - {params if params else acao_sec.__name__ if acao_sec else "Nenhuma"}')
                    acao_definida = tipo_acao
                    parametros_acao = params
                    acao_secundaria = acao_sec
                    termo_encontrado = regex.pattern
                    # NOVA REGRA: se acao_definida == 'checar_prox', chamar checar_prox imediatamente
                    if acao_definida == 'checar_prox':
                        prox_doc_encontrado, prox_doc_link, prox_doc_idx = checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
                        if prox_doc_encontrado and prox_doc_link:
                            print(f'[FLUXO_PZ] Regra de cancelamento/baixa: buscando próximo documento relevante')
                            doc_encontrado = prox_doc_encontrado
                            doc_link = prox_doc_link
                            doc_idx = prox_doc_idx
                            break
                    break
            if acao_definida:
                break        # 6. Perform action(s) based on the matched rule (or default)
        import datetime
        gigs_aplicado = False
        if acao_definida == 'gigs':
            # parametros_acao já está no formato 'dias/responsavel/observacao'
            try:
                dias, responsavel, observacao = parse_gigs_param(parametros_acao)
                criar_gigs(driver, dias, responsavel, observacao)
                gigs_aplicado = True
                print(f'[FLUXO_PZ] GIGS criado: {observacao}')
                if acao_secundaria:
                    print(f'[FLUXO_PZ] Executando ação secundária: {acao_secundaria.__name__}')
                    try:
                        acao_secundaria(driver)
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
                     return  # Sai da função sem log de sucesso
                 time.sleep(1) # Pause after movement
             except Exception as mov_error:
                 logger.error(f'[FLUXO_PZ] Falha ao executar movimentação {func_movimento.__name__}: {mov_error}')
                 return  # Sai da função sem log de sucesso
        elif acao_definida == 'checar_cabecalho':
            # Nova regra: verificar cor do cabeçalho para "Ante a notícia de descumprimento"
            try:
                cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
                cor_fundo = cabecalho.value_of_css_property('background-color')
                print(f'[FLUXO_PZ] Cor do cabeçalho detectada: {cor_fundo}')
                
                # Verifica se é cinza: rgb(144, 164, 174)
                if 'rgb(144, 164, 174)' in cor_fundo:
                    print('[FLUXO_PZ] Cabeçalho cinza detectado - executando pesquisas')
                    pesquisas(driver)
                else:
                    print('[FLUXO_PZ] Cabeçalho não é cinza - criando GIGS padrão')
                    dias, responsavel, observacao = parse_gigs_param('1/SILVIA/Argos')
                    criar_gigs(driver, dias, responsavel, observacao)
                    # Executar ato_pesqliq como ação secundária
                    ato_pesqliq(driver)
                
                time.sleep(1)
            except Exception as cabecalho_error:
                logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho: {cabecalho_error}')
                # Fallback: criar GIGS padrão
                print('[FLUXO_PZ] Fallback - criando GIGS padrão')
                dias, responsavel, observacao = parse_gigs_param('1/SILVIA/Argos')
                criar_gigs(driver, dias, responsavel, observacao)
        elif acao_definida == 'checar_cabecalho_impugnacoes':
            # Nova regra: verificar cor do cabeçalho para "impugnações apresentadas"
            try:
                cabecalho = driver.find_element(By.CSS_SELECTOR, 'mat-card.resumo-processo')
                cor_fundo = cabecalho.value_of_css_property('background-color')
                print(f'[FLUXO_PZ] Cor do cabeçalho detectada para impugnações: {cor_fundo}')
                
                # Verifica se é cinza: rgb(144, 164, 174)
                if 'rgb(144, 164, 174)' in cor_fundo:
                    print('[FLUXO_PZ] Cabeçalho cinza detectado - executando pesquisas')
                    pesquisas(driver)
                else:
                    print('[FLUXO_PZ] Cabeçalho não é cinza - executando mov_exec + pesquisas')
                    mov_exec(driver)
                    pesquisas(driver)
                
                time.sleep(1)
            except Exception as cabecalho_error:
                logger.error(f'[FLUXO_PZ] Erro ao verificar cor do cabeçalho para impugnações: {cabecalho_error}')
                # Fallback: executar mov_exec + pesquisas
                print('[FLUXO_PZ] Fallback - executando mov_exec + pesquisas')
                mov_exec(driver)
                pesquisas(driver)
        # Se não há ação primária mas existe ação secundária, trate a secundária como primária
        if acao_definida is None and acao_secundaria:
            print(f'[FLUXO_PZ] Executando ação: {acao_secundaria.__name__}')
            try:
                acao_secundaria(driver)
                time.sleep(1)
            except Exception as sec_error:
                logger.error(f'[FLUXO_PZ] Falha ao executar ação {acao_secundaria.__name__}: {sec_error}')        # NOVA LÓGICA: buscar o próximo documento relevante APENAS se a ação primária for 'checar_prox'
        if acao_definida == 'checar_prox':
            prox_doc_encontrado, prox_doc_link, prox_doc_idx = checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
            if prox_doc_encontrado and prox_doc_link:
                print(f'[FLUXO_PZ] Trecho localizado. Buscando próximo documento relevante')
                doc_encontrado = prox_doc_encontrado
                doc_link = prox_doc_link
                doc_idx = prox_doc_idx
                continue  # repete o while para o próximo documento
        break  # se não encontrou ou acabou a timeline, encerra
    # Fim do while True    # Fechar a aba após o processamento do fluxo_pz (sem usar try/finally)
    all_windows = driver.window_handles
    main_window = all_windows[0]
    current_window = driver.current_window_handle

    if current_window != main_window and len(all_windows) > 1:
        driver.close()
        # Troca para uma aba válida após fechar
        try:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
            else:
                print("[LIMPEZA][ERRO] Nenhuma aba restante para alternar.")
        except Exception as e:
            print(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida após fechar: {e}")
        # Testa se a aba está realmente acessível
        from selenium.common.exceptions import NoSuchWindowException
        try:
            _ = driver.current_url
        except NoSuchWindowException:
            print("[LIMPEZA][ERRO] Tentou acessar uma aba já fechada.")
    
    print('[FLUXO_PZ] Processo concluído, retornando à lista')

def fluxo_prazo(driver):
    """
    Executa o fluxo de prazo: Itera processos, chama fluxo_pz para cada um.
    """
    from Fix import indexar_e_processar_lista # Keep this import

    print('[FLUXO_PRAZO] Iniciando processamento da lista de processos')

    def callback_processo(driver_processo):
        """
        Callback para executar fluxo_pz no processo aberto.
        fluxo_pz handles analysis, actions (primary & secondary), and tab closing.
        """
        try:
            fluxo_pz(driver_processo) # Call the main function for the process tab
        except Exception as callback_error:
            logger.error(f'[FLUXO_PRAZO] ERRO no fluxo_pz: {callback_error}')
            raise  # Re-raise para que o indexar_e_processar_lista saiba que houve erro
        
        time.sleep(1)  # Pausa para evitar race condition/travamento entre processamentos

    # Chama indexar_e_processar_lista com o callback definido
    indexar_e_processar_lista(driver, callback_processo) # Use the correct processing function

    print('[FLUXO_PRAZO] Processamento da lista concluído')

def navegar_para_atividades(driver):
    """
    Navega para a tela de atividades do GIGS clicando no ícone .fa-tags.
    """
    try:
        # Navegação por clique no ícone .fa-tags
        print("[NAVEGAR] Procurando ícone .fa-tags...")
        tag_icon = esperar_elemento(driver, ".fa-tags", timeout=20)
        if not tag_icon:
            print("[ERRO] Ícone .fa-tags não encontrado!")
            return
        safe_click(driver, tag_icon)
        print("[NAVEGAR] Ícone .fa-tags clicado.")

        # Aguarda o carregamento da tela de atividades
        esperar_elemento(driver, ".classe-unica-da-tela-atividades", timeout=20)
        print("[OK] Na tela de atividades do GIGS. Continue o fluxo normalmente...")
    except Exception as e:
        print(f"[ERRO] Falha ao navegar para a tela de atividades: {e}")

# Updated to use driver_notebook and login_notebook from Fix.py.
from Fix import login_notebook, driver_notebook

def esperar_url(driver, url_esperada, timeout=30):
    """
    Espera até a URL do driver ser igual à url_esperada ou até o timeout.
    Retorna True se a URL for atingida, False caso contrário.
    """
    import time
    start = time.time()
    while time.time() - start < timeout:
        if driver.current_url == url_esperada:
            return True
        time.sleep(0.5)
    return False

def esperar_url_conter(driver, trecho_url, timeout=60):
    import time
    start = time.time()
    while time.time() - start < timeout:
        if trecho_url in driver.current_url:
            return True
        time.sleep(0.5)
    return False

# Updated the executar_fluxo function to use the new driver and login function.
def executar_fluxo(driver):
    """
    Executa o fluxo completo de navegação, filtro e processamento, usando o driver já autenticado.
    """
    try:
        # Maximizar a janela do navegador
        driver.maximize_window()
        driver.execute_script("document.body.style.zoom='70%'")
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        driver.get(url_atividades)
        if not esperar_url(driver, url_atividades, timeout=30):
            logger.error(f'[NAVEGAR] Timeout aguardando URL {url_atividades}. URL atual: {driver.current_url}')
            raise Exception(f'Timeout aguardando URL {url_atividades}')
        from Fix import aplicar_filtro_100
        try:
            # 3. Aplicar filtro de 100 itens por página
            if not aplicar_filtro_100(driver):
                raise Exception('Falha ao aplicar filtro de 100 itens por página')
            time.sleep(2)
            # Passo 1: Remover chip "Vencidas"
            chip_removal_success = False
            for tentativa in range(3):
                try:
                    time.sleep(0.5)
                    chip_remove_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[ngclass="chips-icone-fechar"][mattooltip="Remover filtro"]'))
                    )
                    try:
                        chip_remove_button.is_displayed()
                    except StaleElementReferenceException:
                        continue
                    safe_click(driver, chip_remove_button)
                    chip_removal_success = True
                    break
                except StaleElementReferenceException as e:
                    time.sleep(1)
                except Exception as e:
                    if tentativa < 2:
                        time.sleep(1)
                    else:
                        logger.error('[FILTRO] Falha ao remover chip após 3 tentativas.')
                        raise
            if not chip_removal_success:
                raise Exception("Falha na remoção do chip 'Vencidas'")
            # Passo 2: Clicar no ícone fa-pen
            btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=15)
            safe_click(driver, btn_fa_pen)
            # Passo 3: Aplicar filtro "xs"
            campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=15)
            campo_descricao.clear()
            campo_descricao.send_keys('xs')
            campo_descricao.send_keys(Keys.ENTER)
            logger.info('[FILTRO] Filtro xs aplicado com sucesso.')
            time.sleep(3)
        except Exception as e:            logger.error(f'[FILTRO] Erro na sequência de filtros: {e}')
            # Não raise aqui: tentaremos processar a lista mesmo assim
            
        # 5. Executar fluxo de prazo
        logger.info('[FLUXO_PRAZO] Iniciando processamento da lista de processos')
        try:
            fluxo_prazo(driver)
            logger.info('[FLUXO_PRAZO] Processamento da lista concluído')
        except Exception as e:
            logger.error(f'[FLUXO_PRAZO] Erro ao processar lista: {e}')
    except Exception as e:
        logger.error(f'[EXECUCAO] {e}')
    finally:
        try:
            finalizar_driver(driver)
        except Exception as e:
            logger.error(f'[EXECUCAO] Falha ao fechar o driver: {e}')

def main():
    driver = criar_driver(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return
    if not login_func(driver):
        print('[ERRO] Falha no login. Encerrando script.')
        finalizar_driver(driver)
        return
    print('[P2] Login realizado com sucesso.')
    executar_fluxo(driver)

def processar_p2(driver_existente=None):
    """
    Função principal que executa o fluxo do p2.py.
    Aceita um driver existente ou cria um novo se nenhum for fornecido.
    
    Args:
        driver_existente: Driver do Selenium já configurado e logado (opcional)
    """
    driver = driver_existente
    should_quit = False
    
    try:
        if not driver:
            driver = criar_driver()
            login_func(driver)
            should_quit = True  # Só fecha o driver se foi criado aqui
        executar_fluxo(driver)
        return True
    except Exception as e:
        logger.error(f'[PROCESSAR_P2] Erro: {e}')
        return False
    finally:
        if should_quit and driver:
            finalizar_driver(driver)

if __name__ == "__main__":
    processar_p2()  # Quando executado diretamente, cria seu próprio driver

class AutomacaoP2:
    def __init__(self):
        self.driver = None
        self.etapa_atual = None

    def iniciar(self):
        try:
            from Fix import driver_pc
            self.driver = driver_pc(headless=False)
            if not self.driver:
                logging.error('[AutomacaoP2] Falha ao iniciar o driver.')
                return False
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro ao iniciar driver: {e}')
            return False

    def login(self):
        self.etapa_atual = 'login'
        try:
            from Fix import login_pc
            if not login_pc(self.driver):
                logging.error('[AutomacaoP2] Falha no login.')
                return False
            logging.info('[AutomacaoP2] Login realizado com sucesso.')
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro no login: {e}')
            return False

    def executar_fluxo(self):
        self.etapa_atual = 'fluxo_principal'
        try:
            if not self.driver:
                if not self.iniciar():
                    return False
            if not self.login():
                return False
            executar_fluxo(self.driver)
            return True
        except Exception as e:
            logging.error(f'[AutomacaoP2] Erro ao executar fluxo: {e}')
            return False

    def reiniciar_etapa(self):
        logging.info(f'[AutomacaoP2] Reiniciando etapa: {self.etapa_atual}')
        # Implementar lógica de reinício se necessário

    def finalizar(self):
        if self.driver:
            try:
                finalizar_driver(self.driver)
                logging.info('[AutomacaoP2] Driver finalizado.')
            except Exception as e:
                logging.error(f'[AutomacaoP2] Erro ao finalizar driver: {e}')
