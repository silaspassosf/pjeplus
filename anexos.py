# ====================================================
# EXTRATOR DE NÚMERO DE PROCESSO DA PÁGINA PJE
# ====================================================
def extrair_numero_processo_da_pagina(driver, debug=True):
    """
    Tenta extrair o número do processo do cabeçalho da página PJe.
    Se não encontrar, tenta clicar no ícone de copiar e ler do clipboard do sistema (se pyperclip disponível).
    Retorna o número do processo como string ou None.
    """
    try:
        # 1. Tenta extrair do cabeçalho
        try:
            el = driver.find_element(By.CSS_SELECTOR, 'span.texto-numero-processo')
            numero = el.text.strip()
            if numero:
                if debug:
                    print(f'[EXTRATOR] Número de processo encontrado no cabeçalho: {numero}')
                return numero
        except Exception as e:
            if debug:
                print(f'[EXTRATOR] Não encontrou no cabeçalho: {e}')
        # 2. Tenta clicar no ícone de copiar e ler do clipboard
        try:
            icone = driver.find_element(By.CSS_SELECTOR, 'i.far.fa-copy.fa-lg')
            driver.execute_script('arguments[0].click();', icone)
            time.sleep(0.2)
            try:
                import pyperclip
                numero = pyperclip.paste().strip()
                if numero:
                    if debug:
                        print(f'[EXTRATOR] Número de processo obtido via clipboard: {numero}')
                    return numero
            except ImportError:
                if debug:
                    print('[EXTRATOR] pyperclip não disponível para ler clipboard')
        except Exception as e:
            if debug:
                print(f'[EXTRATOR] Não conseguiu clicar no ícone de copiar: {e}')
    except Exception as e:
        if debug:
            print(f'[EXTRATOR] Erro geral: {e}')
    return None
# ====================================================
# WRAPPER ESPECÍFICO: CARTA (JUNTADA DE E-CARTA)
# ====================================================

# ====================================================
# WRAPPER ESPECÍFICO: CARTA (JUNTADA DE E-CARTA)
# ====================================================
def carta_wrapper(
    driver,
    numero_processo=None,
    debug=True,
    ecarta_html=None
):
    """
    Wrapper específico para juntada de e-carta.
    Busca o conteúdo do clipboard.txt para o processo e insere no editor via editor_insert.
    Parâmetros fixos conforme padrão do fluxo:
      tipo: Certidão
      descricao: Rastreamentos e-Carta
      modelo: xs carta
      assinar: nao
      sigilo: nao
      substituir_link: True
    """
    from editor_insert import inserir_html_no_editor_apos_marcador
    from editor_insert import obter_ultimo_conteudo_clipboard
    conteudo = obter_ultimo_conteudo_clipboard(numero_processo, debug=debug)
    
    # Se ecarta_html for fornecido, usar ele diretamente (já é HTML formatado)
    if ecarta_html is not None:
        conteudo = ecarta_html
        
    def inserir_fn(driver, numero_processo=None, debug=True):
        # Usar inserção HTML para preservar formatação - FUNÇÃO LIMPA
        print(f"[CARTA] Inserindo conteúdo HTML: {len(conteudo or '')} caracteres")
        return inserir_html_no_editor_apos_marcador(
            driver=driver, 
            marcador='--',
            html_content=conteudo or '',
            debug=True
        )
    return wrapper_juntada_geral(
        driver=driver,
        tipo='Certidão',
        descricao='Rastreamentos e-Carta',
        modelo='xs carta',
        assinar='nao',
        sigilo='nao',
        inserir_conteudo=inserir_fn,
        coleta_conteudo=None,
        substituir_link=False,
        debug=debug
    )
# ====================================================
def sisb_wrapper(
    driver,
    numero_processo=None,
    debug=True,
    tipo='Certidão',
    descricao='Consulta SISBAJUD',
    modelo='xteim',
    assinar='nao',
    sigilo='sim'
):
    """
    Wrapper específico para juntada de relatório SISBAJUD.
    Busca o conteúdo do relatório armazenado em relatorio_sisbajud.txt e insere no editor.
    Parâmetros customizáveis conforme necessidade do processo.
    """
    import os
    
    def obter_conteudo_relatorio_sisbajud(debug=True):
        """Obtém o conteúdo do relatório SISBAJUD armazenado localmente"""
        try:
            # Buscar arquivo relatorio_sisbajud.txt no diretório do projeto
            relatorio_path = os.path.join(os.path.dirname(__file__), 'relatorio_sisbajud.txt')
            
            if os.path.exists(relatorio_path):
                with open(relatorio_path, 'r', encoding='utf-8') as f:
                    conteudo = f.read().strip()
                
                if debug:
                    print(f'[SISB_WRAPPER] ✅ Relatório carregado: {len(conteudo)} caracteres')
                    print(f'[SISB_WRAPPER] Prévia: {conteudo[:200]}...')
                
                return conteudo
            else:
                if debug:
                    print(f'[SISB_WRAPPER] ❌ Arquivo não encontrado: {relatorio_path}')
                return None
                
        except Exception as e:
            if debug:
                print(f'[SISB_WRAPPER] ❌ Erro ao carregar relatório: {e}')
            return None
    
    def inserir_fn(driver, numero_processo=None, debug=True):
        """Função de inserção do conteúdo SISBAJUD no editor com formatação HTML do PJe"""
        from editor_insert import inserir_html_no_editor_apos_marcador
        import re
        
        # Obter conteúdo do relatório
        conteudo = obter_conteudo_relatorio_sisbajud(debug=debug)
        
        if not conteudo:
            if debug:
                print('[SISB_WRAPPER] ❌ Conteúdo do relatório não disponível')
            return False
        
        # MANTER O HTML FORMATADO - não converter para texto simples
        # O conteúdo já vem com a formatação HTML adequada do PJe
        if debug:
            print('[SISB_WRAPPER] HTML formatado para inserção:')
            print(conteudo[:200] + '...')
        
        # Inserir HTML formatado no editor após marcador '--'
        return inserir_html_no_editor_apos_marcador(
            driver, 
            conteudo,  # Usar HTML formatado completo
            marcador='--', 
            modo='replace', 
            debug=debug
        )
    
    if debug:
        print(f'[SISB_WRAPPER] Iniciando juntada SISBAJUD com modelo: {modelo}')
    
    return wrapper_juntada_geral(
        driver=driver,
        tipo=tipo,
        descricao=descricao,
        modelo=modelo,
        assinar=assinar,
        sigilo=sigilo,
        inserir_conteudo=inserir_fn,
        coleta_conteudo=None,
        substituir_link=False,
        debug=debug
    )

# ====================================================
# SISBAJUD WRAPPERS
# ====================================================

def wrapper_bloqneg(
    driver,
    numero_processo=None,
    debug=True,
    tipo='Certidão',
    descricao='Consulta sisbajud NEGATIVA',
    modelo='xjsisbneg',
    assinar='nao',
    sigilo='nao'
):
    """
    Wrapper específico para juntada de relatório SISBAJUD NEGATIVO/DESBLOQUEIO.
    Busca o conteúdo do relatório armazenado em relatorio_sisbajud.txt e insere no editor.
    Parâmetros customizáveis conforme necessidade do processo.
    """
    import os
    
    def obter_conteudo_relatorio_sisbajud(debug=True):
        """Obtém o conteúdo do relatório SISBAJUD armazenado localmente"""
        try:
            # Buscar arquivo relatorio_sisbajud.txt no diretório do projeto
            relatorio_path = os.path.join(os.path.dirname(__file__), 'relatorio_sisbajud.txt')
            
            if os.path.exists(relatorio_path):
                with open(relatorio_path, 'r', encoding='utf-8') as f:
                    conteudo = f.read().strip()
                
                if debug:
                    print(f'[WRAPPER_BLOQNEG] ✅ Relatório carregado: {len(conteudo)} caracteres')
                    print(f'[WRAPPER_BLOQNEG] Prévia: {conteudo[:200]}...')
                
                return conteudo
            else:
                if debug:
                    print(f'[WRAPPER_BLOQNEG] ❌ Arquivo não encontrado: {relatorio_path}')
                return None
                
        except Exception as e:
            if debug:
                print(f'[WRAPPER_BLOQNEG] ❌ Erro ao carregar relatório: {e}')
            return None
    
    def inserir_fn(driver, numero_processo=None, debug=True):
        """Função de inserção do conteúdo SISBAJUD no editor com formatação HTML do PJe"""
        from editor_insert import inserir_html_no_editor_apos_marcador
        import re
        
        # Obter conteúdo do relatório
        conteudo = obter_conteudo_relatorio_sisbajud(debug=debug)
        
        if not conteudo:
            if debug:
                print('[WRAPPER_BLOQNEG] ❌ Conteúdo do relatório não disponível')
            return False
        
        # MANTER O HTML FORMATADO - não converter para texto simples
        # O conteúdo já vem com a formatação HTML adequada do PJe
        if debug:
            print('[WRAPPER_BLOQNEG] HTML formatado para inserção:')
            print(conteudo[:200] + '...')
        
        # Inserir HTML formatado no editor após marcador '--'
        return inserir_html_no_editor_apos_marcador(
            driver, 
            conteudo,  # Usar HTML formatado completo
            marcador='--', 
            modo='replace', 
            debug=debug
        )
    
    if debug:
        print(f'[WRAPPER_BLOQNEG] Iniciando juntada SISBAJUD NEGATIVA com modelo: {modelo}')
    
    return wrapper_juntada_geral(
        driver=driver,
        tipo=tipo,
        descricao=descricao,
        modelo=modelo,
        assinar=assinar,
        sigilo=sigilo,
        inserir_conteudo=inserir_fn,
        coleta_conteudo=None,
        substituir_link=False,
        debug=debug
    )

def wrapper_parcial(
    driver,
    numero_processo=None,
    debug=True,
    tipo='Certidão',
    descricao='Consulta sisbajud POSITIVA',
    modelo='xjsisbp',
    assinar='nao',
    sigilo='nao'
):
    """
    Wrapper específico para juntada de relatório SISBAJUD POSITIVO (parcial).
    Busca o conteúdo do relatório armazenado em relatorio_sisbajud.txt e insere no editor.
    Parâmetros customizáveis conforme necessidade do processo.
    """
    import os
    
    def obter_conteudo_relatorio_sisbajud(debug=True):
        """Obtém o conteúdo do relatório SISBAJUD armazenado localmente"""
        try:
            # Buscar arquivo relatorio_sisbajud.txt no diretório do projeto
            relatorio_path = os.path.join(os.path.dirname(__file__), 'relatorio_sisbajud.txt')
            
            if os.path.exists(relatorio_path):
                with open(relatorio_path, 'r', encoding='utf-8') as f:
                    conteudo = f.read().strip()
                
                if debug:
                    print(f'[WRAPPER_PARCIAL] ✅ Relatório carregado: {len(conteudo)} caracteres')
                    print(f'[WRAPPER_PARCIAL] Prévia: {conteudo[:200]}...')
                
                return conteudo
            else:
                if debug:
                    print(f'[WRAPPER_PARCIAL] ❌ Arquivo não encontrado: {relatorio_path}')
                return None
                
        except Exception as e:
            if debug:
                print(f'[WRAPPER_PARCIAL] ❌ Erro ao carregar relatório: {e}')
            return None
    
    def inserir_fn(driver, numero_processo=None, debug=True):
        """Função de inserção do conteúdo SISBAJUD no editor com formatação HTML do PJe"""
        from editor_insert import inserir_html_no_editor_apos_marcador
        import re
        
        # Obter conteúdo do relatório
        conteudo = obter_conteudo_relatorio_sisbajud(debug=debug)
        
        if not conteudo:
            if debug:
                print('[WRAPPER_PARCIAL] ❌ Conteúdo do relatório não disponível')
            return False
        
        # MANTER O HTML FORMATADO - não converter para texto simples
        # O conteúdo já vem com a formatação HTML adequada do PJe
        if debug:
            print('[WRAPPER_PARCIAL] HTML formatado para inserção:')
            print(conteudo[:200] + '...')
        
        # Inserir HTML formatado no editor após marcador '--'
        return inserir_html_no_editor_apos_marcador(
            driver, 
            conteudo,  # Usar HTML formatado completo
            marcador='--', 
            modo='replace', 
            debug=debug
        )
    
    if debug:
        print(f'[WRAPPER_PARCIAL] Iniciando juntada SISBAJUD POSITIVA com modelo: {modelo}')
    
    return wrapper_juntada_geral(
        driver=driver,
        tipo=tipo,
        descricao=descricao,
        modelo=modelo,
        assinar=assinar,
        sigilo=sigilo,
        inserir_conteudo=inserir_fn,
        coleta_conteudo=None,
        substituir_link=False,
        debug=debug
    )

# ====================================================
# UTILITÁRIOS DE FORMATAÇÃO
# ====================================================

def formatar_conteudo_ecarta(html_table):
    """
    Formata o conteúdo HTML extraído do e-carta para inserção adequada no editor.
    """
    return html_table

# ====================================================
# WRAPPER GERAL DE JUNTADA AUTOMÁTICA (PADRÃO ato_judicial)
# ====================================================
def wrapper_juntada_geral(
    driver,
    tipo='Certidão',
    descricao=None,
    sigilo='nao',
    modelo=None,
    inserir_conteudo=None,
    assinar='nao',
    coleta_conteudo=None,
    substituir_link=False,
    debug=True
):
    """
    Wrapper geral para juntada automática, sequencial e parametrizado, inspirado em ato_judicial de atos.py.
    Permite criar wrappers específicos apenas repassando os parâmetros desejados.
    """
    if debug:
        print('[WRAPPER_JUNTADA_GERAL] Iniciando juntada automática...')

    # Passos para abrir tela de juntada
    try:
        # 1. Clicar no menu lateral
        menu_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-bars.icone-botao-menu')))
        menu_btn.click()
        if debug:
            print('[JUNTADA][DEBUG] Menu lateral clicado.')
        time.sleep(1)

        # 2. Clicar em "Anexar Documentos"
        anexar_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Anexar Documentos"]')))
        anexar_btn.click()
        if debug:
            print('[JUNTADA][DEBUG] Botão "Anexar Documentos" clicado.')
        time.sleep(1)

        # 3. Mudar para nova aba e aguardar URL /anexar
        original_window = driver.current_window_handle
        all_windows = driver.window_handles
        if len(all_windows) > 1:
            nova_aba = all_windows[-1]
            driver.switch_to.window(nova_aba)
            if debug:
                print(f'[JUNTADA][DEBUG] Mudou para nova aba: {nova_aba}')
        else:
            if debug:
                print('[JUNTADA][ERRO] Nova aba de anexar não detectada.')
        # Aguarda URL
        WebDriverWait(driver, 10).until(lambda d: '/anexar' in d.current_url)
        if debug:
            print(f'[JUNTADA][DEBUG] URL de anexar detectada: {driver.current_url}')
        time.sleep(2)
    except Exception as e:
        if debug:
            print(f'[JUNTADA][ERRO] Falha ao abrir tela de juntada: {e}')

    # 0. Coleta de conteúdo (opcional)
    if coleta_conteudo:
        try:
            from anexos import extrair_numero_processo_da_url
            from coleta_atos import executar_coleta_parametrizavel
            numero_processo = extrair_numero_processo_da_url(driver)
            print(f'[WRAPPER_JUNTADA_GERAL][COLETA] Iniciando coleta: {coleta_conteudo} | processo: {numero_processo}')
            executar_coleta_parametrizavel(driver, numero_processo, coleta_conteudo, debug=debug)
        except Exception as e:
            print(f'[WRAPPER_JUNTADA_GERAL][COLETA][WARN] Falha ao executar coleta opcional: {e}')
    # 1. Cria juntador
    juntador = create_juntador(driver)
    configuracao = {
        'tipo': tipo,
        'descricao': descricao if descricao else 'Juntada automática',
        'sigilo': sigilo,
        'modelo': modelo,
        'inserir_conteudo': inserir_conteudo,
        'assinar': assinar,
        'coleta_conteudo': coleta_conteudo,
    }
    # 2. Executa juntada principal
    resultado = False
    if hasattr(juntador, 'executar_juntada'):
        resultado = juntador.executar_juntada(configuracao, substituir_link=substituir_link)
    else:
        print('[WRAPPER_JUNTADA_GERAL][ERRO] Objeto juntador não possui método executar_juntada')
    if resultado:
        print('[WRAPPER_JUNTADA_GERAL] ✓ Juntada automática concluída com sucesso!')
    else:
        print('[WRAPPER_JUNTADA_GERAL] ✗ Juntada automática falhou ou foi pulada')
    return resultado
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
import types

# ====================================================
# UTILITÁRIOS DE FORMATAÇÃO
# ====================================================

def formatar_conteudo_ecarta(html_table):
    """
    Formata o conteúdo HTML extraído do e-carta para inserção adequada no editor.
    """
    return html_table

def create_juntador(driver):
    """Cria um objeto simples com driver e métodos vinculados aos helpers existentes."""
    ns = types.SimpleNamespace(driver=driver)
    # Bind helpers
    try:
        ns._escolher_opcao_gigs = types.MethodType(globals().get('_escolher_opcao_gigs'), ns)
    except Exception:
        pass
    try:
        ns._preencher_input_gigs = types.MethodType(globals().get('_preencher_input_gigs'), ns)
    except Exception:
        pass
    try:
        ns._clicar_elemento_gigs = types.MethodType(globals().get('_clicar_elemento_gigs'), ns)
    except Exception:
        pass
    try:
        ns._selecionar_modelo_gigs = types.MethodType(globals().get('_selecionar_modelo_gigs'), ns)
    except Exception:
        pass
    # Bind flows
    ns.executar_juntada_ate_editor = types.MethodType(executar_juntada_ate_editor, ns)
    try:
        ns.executar_juntada = types.MethodType(globals().get('executar_juntada'), ns)
    except Exception:
        pass
    return ns

def executar_juntada_ate_editor(self, configuracao):
    """
    Executa a juntada até o ponto em que o editor está disponível e o modelo foi inserido,
    mas NÃO clica em Salvar. Retorna True se sucesso, False se falha.
    """
    driver = self.driver
    modelo = configuracao.get('modelo', '').strip().upper()
    if modelo == 'PDF':
        print('[JUNTADA][ERRO] Não faz sentido juntar PDF nesse fluxo!')
        return False

    print('[JUNTADA][DEBUG] Executando juntada até o editor estar pronto')

    try:
        print('[JUNTADA][DEBUG] Abrindo interface de anexação...')

        # 0.1. Clique no menu (ícone hambúrguer)
        print('[JUNTADA][DEBUG] Clicando no menu hambúrguer...')
        menu_icon = driver.find_element(By.CSS_SELECTOR, 'i[class*="fa-bars"].icone-botao-menu')
        driver.execute_script("arguments[0].click();", menu_icon)
        time.sleep(1)

        # 0.2. Clique em "Anexar Documentos"
        print('[JUNTADA][DEBUG] Clicando em "Anexar documentos"...')
        btn_anexar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Anexar Documentos"]')
        driver.execute_script("arguments[0].click();", btn_anexar)
        time.sleep(2)

        # 0.3. Aguarda nova aba/janela e muda para ela
        print('[JUNTADA][DEBUG] Mudando para aba de anexação...')
        all_windows = driver.window_handles
        if len(all_windows) > 1:
            driver.switch_to.window(all_windows[-1])
            time.sleep(2)
            current_url = driver.current_url
            print(f'[JUNTADA][DEBUG] URL atual: {current_url}')
            if '/anexar' not in current_url:
                print('[JUNTADA][AVISO] URL não contém /anexar, mas prosseguindo...')
        else:
            print('[JUNTADA][DEBUG] Nova aba não detectada, prosseguindo na mesma aba...')

        time.sleep(3)

        tipo = configuracao.get('tipo', 'Certidão')
        print(f'[JUNTADA][DEBUG] Preenchendo Tipo de Documento: {tipo}')
        if not self._escolher_opcao_gigs('input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento'):
            return False

        descricao = configuracao.get('descricao', '')
        if descricao:
            print(f'[JUNTADA][DEBUG] Preenchendo Descrição: {descricao}')
            if not self._preencher_input_gigs('input[aria-label="Descrição"]', descricao, 'Descrição'):
                return False

        sigilo = configuracao.get('sigilo', 'nao').lower()
        if 'sim' in sigilo:
            print('[JUNTADA][DEBUG] Ativando sigilo')
            if not self._clicar_elemento_gigs('input[name="sigiloso"]', 'Sigilo'):
                return False

        modelo_original = configuracao.get('modelo', '')
        if modelo_original:
            print(f'[JUNTADA][DEBUG] Selecionando e inserindo modelo: {modelo_original}')
            if not self._selecionar_modelo_gigs(modelo_original):
                return False
            print('[JUNTADA][DEBUG] Aguardando modelo ser inserido no editor...')
            time.sleep(3)

        print('[JUNTADA][DEBUG] Verificando se editor está disponível após inserção do modelo...')

        seletores_editor = [
            'div[aria-label="Conteúdo principal. Alt+F10 para acessar a barra de tarefas"].area-conteudo.ck.ck-content.ck-editor__editable',
            '.area-conteudo.ck.ck-content.ck-editor__editable.ck-rounded-corners.ck-editor__editable_inline',
            '.area-conteudo.ck-editor__editable[contenteditable="true"]',
            '.ck-editor__editable[contenteditable="true"]',
            'div.fr-element[contenteditable="true"]',
            '[contenteditable="true"]'
        ]

        editor_encontrado = None
        for i, seletor in enumerate(seletores_editor):
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                print(f'[JUNTADA][DEBUG] Seletor {i+1} "{seletor}": {len(elementos)} elementos')
                if elementos:
                    editor_encontrado = elementos[0]
                    print(f'[JUNTADA][DEBUG] ✓ Editor encontrado com seletor: {seletor}')
                    print(f'[JUNTADA][DEBUG] Editor visível: {editor_encontrado.is_displayed()}')
                    print(f'[JUNTADA][DEBUG] Editor habilitado: {editor_encontrado.is_enabled()}')
                    conteudo = editor_encontrado.get_attribute('innerHTML')
                    print(f'[JUNTADA][DEBUG] Conteúdo do editor (primeiros 200 chars): {conteudo[:200]}...')
                    if 'marker-yellow' in conteudo and 'link' in conteudo:
                        print('[JUNTADA][DEBUG] ✓ Editor contém termo "link" marcado em amarelo!')
                    elif conteudo.strip() and len(conteudo) > 100:
                        print('[JUNTADA][DEBUG] ✓ Editor contém conteúdo do modelo inserido')
                    else:
                        print('[JUNTADA][AVISO] Editor parece vazio - modelo pode não ter sido inserido')
                    break
            except Exception as e:
                print(f'[JUNTADA][DEBUG] Erro com seletor {i+1}: {e}')
                continue

        if not editor_encontrado:
            print('[JUNTADA][ERRO] Nenhum editor encontrado com os seletores disponíveis!')
            return False

        print('[JUNTADA][DEBUG] ✓ Editor disponível para manipulação')
        return True

    except Exception as e:
        print(f'[JUNTADA][ERRO] Erro ao executar juntada até o editor: {e}')
        return False

def executar_juntada(self, configuracao, substituir_link=False):
    """
    Executa a juntada automática de anexos com base na configuração fornecida.
    Implementação baseada no gigs-plugin.js acao_bt_aaAnexar
    """
    try:
        driver = self.driver
        
        print(f'[JUNTADA][DEBUG] Iniciando juntada com configuração: {configuracao}')

        # Coleta de conteúdo (opcional) no início
        try:
            coleta_conteudo = configuracao.get('coleta_conteudo')
            if coleta_conteudo:
                from anexos import extrair_numero_processo_da_url
                from coleta_atos import executar_coleta_parametrizavel
                numero_processo_atual = extrair_numero_processo_da_url(driver)
                print(f'[JUNTADA][COLETA] Iniciando coleta: {coleta_conteudo} | processo: {numero_processo_atual}')
                executar_coleta_parametrizavel(driver, numero_processo_atual, coleta_conteudo, debug=True)
        except Exception as e:
            print(f'[JUNTADA][COLETA][WARN] Falha ao executar coleta opcional: {e}')
        
        # 1. Preencher Tipo de Documento (padrão GIGS escolherOpcaoTeste)
        tipo = configuracao.get('tipo', 'Certidão')
        if not self._escolher_opcao_gigs('input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento'):
            return False

        # 2. Preencher Descrição (padrão GIGS preencherInput)
        descricao = configuracao.get('descricao', '')
        if descricao:
            if not self._preencher_input_gigs('input[aria-label="Descrição"]', descricao, 'Descrição'):
                return False

        # 3. Configurar Sigilo (padrão GIGS clicarBotao)
        sigilo = configuracao.get('sigilo', 'nao').lower()
        if 'sim' in sigilo:
            if not self._clicar_elemento_gigs('input[name="sigiloso"]', 'Sigilo'):
                return False

        # 4. Selecionar Modelo (padrão GIGS - filtro + inserir)
        modelo = configuracao.get('modelo', '')
        if modelo:
            if not self._selecionar_modelo_gigs(modelo):
                return False

        # 4.5. Inserção de conteúdo no editor (opcional), após inserir modelo e antes de salvar
        try:
            inserir_conteudo = configuracao.get('inserir_conteudo')
            if inserir_conteudo:
                print('[JUNTADA][INSERIR] Executando inserção de conteúdo no editor...')
                inserir_fn = inserir_conteudo
                if isinstance(inserir_conteudo, str):
                    try:
                        from editor_insert import inserir_link_ato_validacao
                        if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                            inserir_fn = inserir_link_ato_validacao
                    except Exception as _e:
                        print(f"[JUNTADA][INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}")
                # Número do processo atual
                try:
                    from anexos import extrair_numero_processo_da_url
                    numero_processo_atual = extrair_numero_processo_da_url(driver)
                except Exception:
                    numero_processo_atual = None
                ok = False
                try:
                    print(f"[JUNTADA][INSERIR][DEBUG] Tentando chamar inserir_fn com driver, numero_processo e debug")
                    print(f"[JUNTADA][INSERIR][DEBUG] Função: {inserir_fn}")
                    print(f"[JUNTADA][INSERIR][DEBUG] Driver: {driver}")
                    print(f"[JUNTADA][INSERIR][DEBUG] Numero processo: {numero_processo_atual}")
                    ok = inserir_fn(driver=driver, numero_processo=numero_processo_atual, debug=True)
                except TypeError as te:
                    print(f"[JUNTADA][INSERIR][DEBUG] TypeError, tentando apenas driver e numero_processo: {te}")
                    try:
                        ok = inserir_fn(driver, numero_processo_atual)
                    except Exception as e2:
                        print(f"[JUNTADA][INSERIR][DEBUG] Erro na segunda tentativa: {e2}")
                        print(f"[JUNTADA][INSERIR][DEBUG] Tentando apenas driver: {e2}")
                        ok = inserir_fn(driver)
                except Exception as e:
                    print(f"[JUNTADA][INSERIR][DEBUG] Erro na primeira tentativa: {e}")
                    print(f"[JUNTADA][INSERIR][DEBUG] Tentando apenas driver e numero_processo")
                    try:
                        ok = inserir_fn(driver, numero_processo_atual)
                    except Exception as e2:
                        print(f"[JUNTADA][INSERIR][DEBUG] Erro na segunda tentativa: {e2}")
                        print(f"[JUNTADA][INSERIR][DEBUG] Tentando apenas driver")
                        ok = inserir_fn(driver)
                print(f"[JUNTADA][INSERIR] Resultado da inserção: {'✓' if ok else '✗'}")
                
                # 4.6. VERIFICAR SE INSERÇÃO FOI BEM-SUCEDIDA ANTES DE SALVAR
                if not ok:
                    print('[JUNTADA][ERRO] Inserção de conteúdo falhou! Cancelando juntada.')
                    return False
                else:
                    print('[JUNTADA][INFO] Inserção bem-sucedida, prosseguindo com salvamento.')
                    
            elif substituir_link:
                # Compat: caminho antigo de substituição
                print('[JUNTADA][DEBUG] Aguardando modelo carregar para substituir link...')
                time.sleep(3)
                if not substituir_link_por_clipboard_anexos(driver, debug=True):
                    print('[JUNTADA][ERRO] Falha na substituição do link!')
                    return False
                print('[JUNTADA][DEBUG] Aguardando processamento da substituição...')
                time.sleep(2)
        except Exception as e:
            print(f"[JUNTADA][INSERIR][WARN] Erro durante inserção opcional: {e}")

        # 5. ÚNICO SALVAMENTO - após modelo inserido e substituição (se aplicável)
        print('[JUNTADA] Salvando documento final...')
        if not self._clicar_elemento_gigs('button[aria-label="Salvar"]', 'Salvar documento'):
            print('[JUNTADA][ERRO] Falha no salvamento principal!')
            return False

        # 5.1. AGUARDAR SALVAMENTO SER PROCESSADO
        print('[JUNTADA] Aguardando processamento do salvamento...')
        time.sleep(2)
        
        # 5.2. VERIFICAR SE SALVAMENTO FOI EFETIVO
        try:
            # Verificar se botão Salvar ainda está disponível (indica que precisa salvar novamente)
            salvar_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
            if salvar_btn.is_enabled():
                print('[JUNTADA][WARN] Documento ainda não salvo, tentando novamente...')
                driver.execute_script("arguments[0].click();", salvar_btn)
                time.sleep(2)
        except:
            print('[JUNTADA][INFO] Botão Salvar não disponível - documento já salvo')

        # 6. Assinar se necessário (padrão GIGS)
        if configuracao.get('assinar', 'nao').lower() == 'sim':
            print('[JUNTADA][DEBUG] Aguardando 3 segundos após salvamento antes de assinar...')
            time.sleep(3)
            if not self._clicar_elemento_gigs('button[aria-label="Assinar documento e juntar ao processo"]', 'Assinar'):
                return False

        print('[JUNTADA][OK] Juntada concluída com sucesso!')
        return True
        
    except Exception as e:
        print(f'[JUNTADA][ERRO] Erro na juntada: {e}')
        return False

def _escolher_opcao_gigs(self, seletor, valor, nome_campo):
    """Implementa escolherOpcaoTeste do gigs-plugin.js"""
    try:
        driver = self.driver
        
        # 1. Encontra o campo
        campo = driver.find_element(By.CSS_SELECTOR, seletor)
        
        # 2. Clica no elemento pai para abrir dropdown (padrão GIGS)
        parent_element = campo.find_element(By.XPATH, '../..')
        driver.execute_script("arguments[0].click();", parent_element)
        time.sleep(1)
        
        # 3. Aguarda opções aparecerem e clica na desejada
        wait = WebDriverWait(driver, 10)
        opcoes = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']")))
        
        for opcao in opcoes:
            if valor.lower() in opcao.text.lower():
                driver.execute_script("arguments[0].click();", opcao)
                print(f'[JUNTADA][DEBUG] {nome_campo} selecionado: {valor}')
                return True
        
        print(f'[JUNTADA][ERRO] Opção "{valor}" não encontrada em {nome_campo}')
        return False
        
    except Exception as e:
        print(f'[JUNTADA][ERRO] Falha ao selecionar {nome_campo}: {e}')
        return False

def _preencher_input_gigs(self, seletor, valor, nome_campo):
    """Implementa preencherInput do gigs-plugin.js"""
    try:
        driver = self.driver
        
        # Encontra o elemento
        campo = driver.find_element(By.CSS_SELECTOR, seletor)
        
        # Implementa exatamente como no gigs-plugin.js usando JavaScript
        resultado = driver.execute_script("""
            const elemento = arguments[0];
            const valor = arguments[1];
            
            // Focus no elemento (JavaScript, não WebElement)
            elemento.focus();
            
            // Define valor usando Object.getOwnPropertyDescriptor (padrão GIGS)
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(elemento, valor);
            
            // Dispara eventos exatos do GIGS
            function triggerEvent(el, eventType) {
                const event = new Event(eventType, {bubbles: true, cancelable: true});
                el.dispatchEvent(event);
            }
            
            triggerEvent(elemento, 'input');
            triggerEvent(elemento, 'change');
            triggerEvent(elemento, 'dateChange');
            triggerEvent(elemento, 'keyup');
            
            // Simula Enter (padrão GIGS)
            const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
            elemento.dispatchEvent(enterEvent);
            
            // Blur no elemento
            elemento.blur();
            
            return true;
        """, campo, valor)
        
        print(f'[JUNTADA][DEBUG] {nome_campo} preenchido: {valor}')
        return True
        
    except Exception as e:
        print(f'[JUNTADA][ERRO] Falha ao preencher {nome_campo}: {e}')
        return False

def _clicar_elemento_gigs(self, seletor, nome_elemento):
    """Implementa clicarBotao do gigs-plugin.js com múltiplas tentativas"""
    try:
        driver = self.driver
        
        # Lista de seletores alternativos para botão Salvar
        if 'Salvar' in nome_elemento:
            seletores = [
                'button[aria-label="Salvar"]',
            'button[mat-raised-button][color="primary"][aria-label="Salvar"]',
            'button.mat-raised-button.mat-primary[aria-label="Salvar"]',
            'button.mat-focus-indicator.mat-raised-button.mat-button-base.mat-primary[aria-label="Salvar"]',
            'button:contains("Salvar")',
            '[aria-label="Salvar"]'
        ]
        # Lista de seletores alternativos para botão Assinar
        elif 'Assinar' in nome_elemento:
            seletores = [
                'button[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-fab[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-focus-indicator.mat-fab.mat-button-base.mat-accent[aria-label="Assinar documento e juntar ao processo"]',
                'button[mat-fab].mat-accent[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-fab .fa-pen-nib',
                'button:contains("Assinar")',
                '[aria-label*="Assinar"]'
            ]
        else:
            seletores = [seletor]
        
        for i, sel in enumerate(seletores):
            try:
                print(f'[JUNTADA][DEBUG] Tentando seletor {i + 1}: {sel}')
                
                # Tenta encontrar o elemento
                if ':contains(' in sel:
                    # Para seletores com :contains, usar JavaScript
                    elemento = driver.execute_script("""
                        const buttons = document.querySelectorAll('button');
                        return Array.from(buttons).find(btn => 
                            btn.textContent.trim().toLowerCase().includes('salvar') ||
                            btn.getAttribute('aria-label') === 'Salvar'
                        );
                    """)
                else:
                    elementos = driver.find_elements(By.CSS_SELECTOR, sel)
                    elemento = elementos[0] if elementos else None
                
                if elemento:
                    print(f'[JUNTADA][DEBUG] Elemento encontrado com seletor {i + 1}: {sel}')
                    
                    # Múltiplas tentativas de clique
                    for tentativa in range(3):
                        try:
                            # Scroll para o elemento
                            driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                            time.sleep(0.5)
                            
                            # Verifica se elemento é clicável
                            if elemento.is_enabled() and elemento.is_displayed():
                                # Tenta clique JavaScript
                                driver.execute_script("arguments[0].click();", elemento)
                                print(f'[JUNTADA][DEBUG] ✅ Clique realizado: {nome_elemento} (seletor {i+1}, tentativa {tentativa + 1})')
                                return True
                            else:
                                print(f'[JUNTADA][DEBUG] Elemento não clicável (enabled: {elemento.is_enabled()}, visible: {elemento.is_displayed()})')
                            
                        except Exception as e:
                            if tentativa < 2:  # Não é a última tentativa
                                print(f'[JUNTADA][DEBUG] Tentativa {tentativa + 1} falhou para {nome_elemento}: {e}')
                                time.sleep(1)
                            else:
                                print(f'[JUNTADA][AVISO] Todas as tentativas falharam para {nome_elemento} com seletor {sel}: {e}')
                else:
                    print(f'[JUNTADA][DEBUG] Elemento não encontrado com seletor {i + 1}: {sel}')
                    
            except Exception as e:
                if i < len(seletores) - 1:  # Não é o último seletor
                    print(f'[JUNTADA][DEBUG] Seletor {i + 1} "{sel}" falhou: {e}')
                    continue
                else:
                    print(f'[JUNTADA][ERRO] Último seletor "{sel}" falhou: {e}')
        
        print(f'[JUNTADA][ERRO] Todos os seletores falharam para {nome_elemento}')
        return False
        
    except Exception as e:
        print(f'[JUNTADA][ERRO] Falha geral ao clicar {nome_elemento}: {e}')
        return False

def _selecionar_modelo_gigs(self, modelo):
    """Seleciona e insere o modelo exatamente como em comunicacao_judicial (atos.py)."""
    try:
        driver = self.driver
        wait = WebDriverWait(driver, 15)

        print(f'[JUNTADA][DEBUG] Selecionando modelo (modo atos.py): {modelo}')

        # 1) Preenche filtro como em atos.py (focus + value + eventos + ENTER)
        campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
        driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, modelo)
        for ev in ['input', 'change', 'keyup']:
            driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
        campo_filtro_modelo.send_keys(Keys.ENTER)
        print('[JUNTADA][DEBUG] Filtro aplicado e ENTER enviado')

        # 2) Clica no item destacado .nodo-filtrado (sem fallback para evitar modelo errado)
        seletor_item_filtrado = '.nodo-filtrado'
        nodo = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_item_filtrado)))
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', nodo)
        driver.execute_script('arguments[0].click();', nodo)
        print('[JUNTADA][DEBUG] Clique em nodo-filtrado realizado')

        # 3) Aguarda preview e localiza botão Inserir (seletor de atos.py)
        seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
        btn_inserir = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_btn_inserir)))
        time.sleep(0.6)

        # 4) Inserir com tecla ESPAÇO (padrão MaisPje)
        btn_inserir.send_keys(Keys.SPACE)
        print('[JUNTADA][DEBUG] Modelo inserido pressionando ESPAÇO (padrão atos.py)')

        # 5) Pequeno aguardo para o editor receber o conteúdo
        time.sleep(2)
        return True
    except Exception as e:
        print(f'[JUNTADA][ERRO] Falha ao selecionar/inserir modelo (modo atos.py): {e}')
        return False

# ====================================================
# UTILITÁRIOS DE EDITOR
# ====================================================

def substituir_marcador_por_conteudo(driver, conteudo_customizado=None, debug=True, marcador="--"):
    """
    Função simples para localizar marcador (ex: "--") e colar conteúdo após ele.
    Simula ação manual: clique no final da linha + Ctrl+V
    Args:
        driver: Selenium WebDriver
        debug: Se deve exibir logs
        conteudo_customizado: Conteúdo específico para usar (se None, usa clipboard/arquivo)
        marcador: Texto a ser localizado (padrão: "--")
    """
    if debug:
        print(f"[SUBST_MARCADOR] Iniciando colagem após marcador '{marcador}'...")
    
    try:
        # 1. Determina qual conteúdo usar
        conteudo_para_usar = None
        fonte_conteudo = ""
        
        if conteudo_customizado:
            conteudo_para_usar = conteudo_customizado
            fonte_conteudo = "conteudo_customizado"
            if debug:
                print(f"[SUBST_MARCADOR] Usando conteúdo customizado: {len(conteudo_customizado)} chars")
        else:
            # Carrega conteúdo do clipboard/arquivo
            import os
            def carregar_clipboard_arquivo():
                try:
                    clipboard_file = "clipboard.txt"
                    if os.path.exists(clipboard_file):
                        with open(clipboard_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        if debug:
                            print(f"[SUBST_MARCADOR] Carregado do arquivo: {len(content)} chars")
                        return content
                    return None
                except Exception as e:
                    if debug:
                        print(f"[SUBST_MARCADOR] Erro ao carregar arquivo: {e}")
                    return None
            
            conteudo_para_usar = carregar_clipboard_arquivo()
            fonte_conteudo = "clipboard_arquivo"
        
        if not conteudo_para_usar:
            print("[SUBST_MARCADOR] ✗ Nenhum conteúdo disponível para colar")
            return False
        
        # ===== SUBSTITUIÇÃO TEMPORARIAMENTE DESABILITADA =====
        # TODO: Comentado para implementar sistema parametrizável de clipboard
        # A substituição será reativada após implementação do sistema de coleta sequencial
        
        # ORIGINAL: 2. Executa substituição COM DEBUG MELHORADO
        # resultado = driver.execute_script("""
        #     ... código JavaScript de substituição ...
        # """, conteudo_para_usar, fonte_conteudo, marcador)
        
        print(f"[SUBST_MARCADOR] ⚠️ SUBSTITUIÇÃO DESABILITADA TEMPORARIAMENTE")
        print(f"[SUBST_MARCADOR] Conteúdo disponível mas não será substituído ainda")
        print(f"[SUBST_MARCADOR] Fonte: {fonte_conteudo}, Tamanho: {len(conteudo_para_usar)} chars")
        
        # Simula sucesso para não quebrar o fluxo
        resultado = {"sucesso": True, "modo": "desabilitado"}
        
        if debug:
            print(f"[SUBST_MARCADOR] Resultado da colagem: {resultado}")
        
        # 3. Verifica resultado
        if resultado and resultado.get('sucesso'):
            print("[SUBST_MARCADOR] ✅ FUNÇÃO CONCLUÍDA (modo desabilitado)")
            return True
        else:
            print("[SUBST_MARCADOR] ✗ Falha na função")
            return False
            
    except Exception as e:
        if debug:
            print(f"[SUBST_MARCADOR] ✗ Erro geral: {e}")
        return False


# ===== NOVAS FUNÇÕES PARA SISTEMA PARAMETRIZÁVEL =====

def salvar_conteudo_clipboard(conteudo, numero_processo, tipo_conteudo="generico", debug=True):
    """
    Salva conteúdo no clipboard.txt em formato simplificado: apenas PROCESSO e CONTEÚDO.

    Observação: O parâmetro tipo_conteudo é mantido para compatibilidade, mas não é mais
    persistido no arquivo. O histórico permanece por entradas sequenciais.

    Args:
        conteudo: O conteúdo a ser salvo
        numero_processo: Número do processo (obrigatório)
        tipo_conteudo: Tipo do conteúdo (informativo)
        debug: Se deve exibir logs
    """
    import os

    if debug:
        print(f"[CLIPBOARD] Salvando conteúdo tipo '{tipo_conteudo}'...")

    try:
        # Validar número do processo
        if not numero_processo:
            raise ValueError("Número do processo é obrigatório e deve ser fornecido pela função chamadora")

        # Preparar o registro (formato novo: somente PROCESSO + CONTEÚDO)
        separador = "=" * 50
        registro = (
            "\n" +
            separador + "\n" +
            f"PROCESSO: {numero_processo}\n" +
            separador + "\n" +
            f"{conteudo}\n" +
            separador + "\n\n"
        )

        # Salvar no arquivo (modo append para manter histórico)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        clipboard_file = os.path.join(base_dir, "clipboard.txt")
        os.makedirs(base_dir, exist_ok=True)
        with open(clipboard_file, 'a', encoding='utf-8', newline='') as f:
            f.write(registro)
            f.flush()

        if debug:
            print(f"[CLIPBOARD] ✅ Conteúdo salvo: {len(conteudo)} chars")
            print(f"[CLIPBOARD] ✅ Processo: {numero_processo}")
            print(f"[CLIPBOARD] ✅ Tipo (informativo): {tipo_conteudo}")
            print(f"[CLIPBOARD] ✅ Arquivo: {clipboard_file}")

        return True

    except Exception as e:
        if debug:
            try:
                print(f"[CLIPBOARD] ✗ Erro ao salvar: {e}")
                import os as _os
                print(f"[CLIPBOARD] CWD: {_os.getcwd()}")
                base_dir = _os.path.dirname(_os.path.abspath(__file__))
                print(f"[CLIPBOARD] Destino esperado: {_os.path.join(base_dir, 'clipboard.txt')}")
            except Exception:
                pass
        return False


def extrair_numero_processo_da_url(driver):
    """
    Extrai o número do processo da URL atual.

    Args:
        driver: Selenium WebDriver

    Returns:
        str: Número do processo ou identificação alternativa
    """
    try:
        import re
        url_atual = driver.current_url

        # Padrões para diferentes URLs do PJe
        padroes = [
            r'processo/(\d+)',           # /processo/123456
            r'processoTrfId=(\d+)',      # ?processoTrfId=123456
            r'numeroProcesso=(\d+)',     # ?numeroProcesso=123456
            r'idProcesso=(\d+)',         # ?idProcesso=123456
        ]

        for padrao in padroes:
            match = re.search(padrao, url_atual)
            if match:
                return match.group(1)

        # Se não encontrou por regex, tenta extrair da URL
        if 'pje' in url_atual.lower():
            partes = url_atual.split('/')
            for parte in partes:
                if parte.isdigit() and len(parte) > 6:  # Assume número do processo > 6 dígitos
                    return parte

        return f"URL_{hash(url_atual) % 10000}"  # Fallback: hash da URL

    except Exception as e:
        return f"ERRO_{str(e)[:20]}"
