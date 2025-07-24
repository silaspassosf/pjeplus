from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time

class JuntadaAutomatica:
    def executar_juntada_ate_editor(self, configuracao):
        """
        Executa a juntada até o ponto em que o editor está disponível e o modelo foi inserido,
        mas NÃO clica em Salvar. Retorna True se sucesso, False se falha.
        """
        from selenium.webdriver.support.ui import WebDriverWait
        import time
        driver = self.driver
        modelo = configuracao.get('modelo', '').strip().upper()
        if modelo == 'PDF':
            print('[JUNTADA][ERRO] Não faz sentido juntar PDF nesse fluxo!')
            return False
        url_atual = driver.current_url
        print(f'[JUNTADA][DEBUG] Navegando para anexar através dos botões do menu (até editor)')
        try:
            menu_button = driver.find_element(By.CSS_SELECTOR, 'button#botao-menu[aria-label="Menu do processo"]')
            menu_button.click()
            time.sleep(1)
            print('[JUNTADA][DEBUG] Menu do processo aberto')
        except Exception as e:
            print(f'[JUNTADA][ERRO] Não foi possível abrir o menu do processo: {e}')
            return False
        try:
            anexar_button = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Anexar Documentos"]')
            anexar_button.click()
            time.sleep(2)
            print('[JUNTADA][DEBUG] Botão "Anexar documentos" clicado')
        except Exception as e:
            print(f'[JUNTADA][ERRO] Não foi possível clicar em "Anexar documentos": {e}')
            return False
        print('[JUNTADA][DEBUG] Aguardando nova aba de anexar...')
        time.sleep(3)
        abas_depois = driver.window_handles
        if len(abas_depois) > 1:
            nova_aba = abas_depois[-1]
            print(f'[JUNTADA][DEBUG] Nova aba detectada. Total de abas: {len(abas_depois)}')
        else:
            print('[JUNTADA][ERRO] Nova aba de anexar não foi aberta.')
            return False
        try:
            driver.switch_to.window(nova_aba)
            time.sleep(2)
            print('[JUNTADA][DEBUG] Foco mudado para nova aba de anexar')
        except Exception as e:
            print(f'[JUNTADA][ERRO] Não foi possível trocar para nova aba de anexar: {e}')
            return False
        if not re.search(r'/anexar$', driver.current_url):
            print(f'[JUNTADA][ERRO] URL inesperada após abrir aba de anexar: {driver.current_url}')
            return False
        print(f'[JUNTADA][DEBUG] Nova aba de anexar confirmada: {driver.current_url}')
        try:
            tipo = configuracao.get('tipo', 'Certidão')
            if not self.preencher_campo_robusto(['input[aria-label="Tipo de Documento"]'], tipo, 'Tipo de Documento'):
                print('[JUNTADA][ERRO] Não foi possível preencher o campo Tipo de Documento.')
                return False
            descricao = configuracao.get('descricao', '')
            if descricao:
                if not self.preencher_campo_robusto(['input[aria-label="Descrição"]'], descricao, 'Descrição'):
                    print('[JUNTADA][ERRO] Não foi possível preencher o campo Descrição.')
                    return False
            sigilo = configuracao.get('sigilo', 'nao').lower()
            if 'sim' in sigilo:
                if not self.clicar_elemento_robusto(['input[name="sigiloso"]'], 'Sigilo'):
                    print('[JUNTADA][ERRO] Não foi possível ativar sigilo.')
                    return False
                print("[JUNTADA][DEBUG] Sigilo aplicado.")
            modelo = configuracao.get('modelo', '')
            if modelo:
                if not self.selecionar_modelo_gigs(modelo):
                    print('[JUNTADA][ERRO] Não foi possível selecionar o modelo.')
                    return False
            # Aguarda o editor aparecer
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            editor = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element"))
            )
            print('[JUNTADA][DEBUG] Editor disponível para substituição.')
            return True
        except Exception as e:
            print(f'[JUNTADA][ERRO] Falha geral até o editor: {e}')
            return False
    """
    Classe responsável por gerenciar a juntada automática de anexos, com fluxo robusto inspirado em ato_judicial.
    """
    def __init__(self, driver):
        self.driver = driver

    def executar_juntada(self, configuracao, substituir_link=False):
        """
        Executa a juntada automática de anexos com base na configuração fornecida.
        Se modelo for 'PDF', chama fluxo de juntada direta de PDF, senão segue fluxo normal.
        
        Args:
            configuracao: Dicionário com configurações da juntada
            substituir_link: Se True, procura por "link" amarelo e substitui por clipboard após carregar modelo
        """
        from selenium.webdriver.support.ui import WebDriverWait
        import time
        driver = self.driver
        modelo = configuracao.get('modelo', '').strip().upper()
        if modelo == 'PDF':
            caminho_pdf = configuracao.get('caminho_pdf')
            if not caminho_pdf:
                print('[JUNTADA][PDF][ERRO] Caminho do PDF não informado na configuração!')
                return False
            return self.juntar_pdf_direto(caminho_pdf, configuracao)
        url_atual = driver.current_url
        print(f'[JUNTADA][DEBUG] Navegando para anexar através dos botões do menu')
        
        # 1. Clique no botão de menu do processo
        try:
            menu_button = driver.find_element(By.CSS_SELECTOR, 'button#botao-menu[aria-label="Menu do processo"]')
            menu_button.click()
            time.sleep(1)
            print('[JUNTADA][DEBUG] Menu do processo aberto')
        except Exception as e:
            print(f'[JUNTADA][ERRO] Não foi possível abrir o menu do processo: {e}')
            return False
        
        # 2. Clique no botão "Anexar documentos"
        try:
            anexar_button = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Anexar Documentos"]')
            anexar_button.click()
            time.sleep(2)
            print('[JUNTADA][DEBUG] Botão "Anexar documentos" clicado')
        except Exception as e:
            print(f'[JUNTADA][ERRO] Não foi possível clicar em "Anexar documentos": {e}')
            return False
        
        # 3. Aguarda nova aba e muda o foco
        print('[JUNTADA][DEBUG] Aguardando nova aba de anexar...')
        time.sleep(3)  # Aguarda a aba ser criada
        
        abas_depois = driver.window_handles
        if len(abas_depois) > 1:
            # Nova aba foi criada - pega a última aba
            nova_aba = abas_depois[-1]
            print(f'[JUNTADA][DEBUG] Nova aba detectada. Total de abas: {len(abas_depois)}')
        else:
            print('[JUNTADA][ERRO] Nova aba de anexar não foi aberta.')
            return False
        
        try:
            driver.switch_to.window(nova_aba)
            time.sleep(2)
            print('[JUNTADA][DEBUG] Foco mudado para nova aba de anexar')
        except Exception as e:
            print(f'[JUNTADA][ERRO] Não foi possível trocar para nova aba de anexar: {e}')
            return False
        
        # 4. Confirma se está na URL correta (/anexar)
        if not re.search(r'/anexar$', driver.current_url):
            print(f'[JUNTADA][ERRO] URL inesperada após abrir aba de anexar: {driver.current_url}')
            return False
        print(f'[JUNTADA][DEBUG] Nova aba de anexar confirmada: {driver.current_url}')

        try:
            # 1. Preencher Tipo de Documento
            tipo = configuracao.get('tipo', 'Certidão')
            if not self.preencher_campo_robusto(['input[aria-label="Tipo de Documento"]'], tipo, 'Tipo de Documento'):
                print('[JUNTADA][ERRO] Não foi possível preencher o campo Tipo de Documento.')
                return False

            # 2. Preencher Descrição
            descricao = configuracao.get('descricao', '')
            if descricao:
                if not self.preencher_campo_robusto(['input[aria-label="Descrição"]'], descricao, 'Descrição'):
                    print('[JUNTADA][ERRO] Não foi possível preencher o campo Descrição.')
                    return False

            # 3. Configurar Sigilo
            sigilo = configuracao.get('sigilo', 'nao').lower()
            if 'sim' in sigilo:
                if not self.clicar_elemento_robusto(['input[name="sigiloso"]'], 'Sigilo'):
                    print('[JUNTADA][ERRO] Não foi possível ativar sigilo.')
                    return False
                print("[JUNTADA][DEBUG] Sigilo aplicado.")

            # 4. Selecionar Modelo (se houver) - padrão GIGS usando inputFiltro
            modelo = configuracao.get('modelo', '')
            if modelo:
                if not self.selecionar_modelo_gigs(modelo):
                    print('[JUNTADA][ERRO] Não foi possível selecionar o modelo.')
                    return False

            # 4.5. Substituir "link" por clipboard se solicitado
            if substituir_link:
                self.substituir_link_amarelo()

            # 5. Realizar a juntada (Salvar)
            if not self.clicar_elemento_robusto(['button[aria-label="Salvar"]'], 'Salvar'):
                print('[JUNTADA][ERRO] Não foi possível clicar em Salvar.')
                return False
            print("[JUNTADA][OK] Documento salvo com sucesso.")

            # 6. Assinar, se necessário
            if configuracao.get('assinar', 'nao').lower() == 'sim':
                if not self.clicar_elemento_robusto(['button[aria-label="Assinar documento e juntar ao processo"]'], 'Assinar'):
                    print('[JUNTADA][ERRO] Não foi possível assinar o documento.')
                    return False
                print("[JUNTADA][OK] Documento assinado com sucesso.")

            # 7. Visibilidade extra se sigilo
            aplicar_visibilidade_se_necessario(self.driver, configuracao.get('sigilo', 'nao'))
            print('[JUNTADA][OK] Fluxo de juntada finalizado com sucesso.')
            return True
        except Exception as e:
            print(f'[JUNTADA][ERRO] Falha geral na juntada: {e}')
            return False

    def preencher_campo_robusto(self, seletores, valor, nome_campo):
        for seletor in seletores:
            try:
                campo = self.driver.find_element(By.CSS_SELECTOR, seletor)
                if campo.is_displayed() and campo.is_enabled():
                    # Para campos de dropdown - padrão GIGS escolherOpcaoTeste
                    if 'Tipo de Documento' in nome_campo or 'Modelo' in nome_campo:
                        # 1. Clica no elemento pai para abrir o dropdown (padrão GIGS)
                        parent_element = campo.find_element(By.XPATH, './../..')
                        self.driver.execute_script("arguments[0].click();", parent_element)
                        time.sleep(1)
                        
                        # 2. Clica na opção específica usando mat-option (padrão GIGS clicarBotao)
                        try:
                            # Aguarda as opções aparecerem
                            wait = WebDriverWait(self.driver, 10)
                            opcoes = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']")))
                            
                            # Procura pela opção que contém o texto
                            opcao_encontrada = None
                            for opcao in opcoes:
                                if valor.lower() in opcao.text.lower():
                                    opcao_encontrada = opcao
                                    break
                            
                            if opcao_encontrada:
                                self.driver.execute_script("arguments[0].click();", opcao_encontrada)
                                print(f'[JUNTADA][DEBUG] {nome_campo} selecionado: {valor}')
                                return True
                            else:
                                print(f'[JUNTADA][WARN] Opção {valor} não encontrada em {nome_campo}')
                                return False
                                
                        except Exception as e:
                            print(f'[JUNTADA][WARN] Falha ao selecionar {valor} em {nome_campo}: {e}')
                            return False
                    else:
                        # Campos normais de texto
                        campo.clear()
                        campo.send_keys(valor)
                        print(f'[JUNTADA][DEBUG] {nome_campo} preenchido: {valor}')
                        return True
            except Exception as e:
                print(f'[JUNTADA][WARN] Falha ao preencher {nome_campo} com seletor {seletor}: {e}')
        return False

    def clicar_elemento_robusto(self, seletores, nome_elemento):
        for seletor in seletores:
            try:
                elemento = self.driver.find_element(By.CSS_SELECTOR, seletor)
                if elemento.is_displayed() and elemento.is_enabled():
                    self.driver.execute_script("arguments[0].click();", elemento)
                    print(f'[JUNTADA][DEBUG] Clique em {nome_elemento} realizado via seletor: {seletor}')
                    return True
            except Exception as e:
                print(f'[JUNTADA][WARN] Falha ao tentar clicar em {nome_elemento} com seletor {seletor}: {e}')
        return False

    def selecionar_modelo_gigs(self, modelo):
        """
        Seleciona modelo seguindo exatamente o padrão do atos.py ato_judicial
        """
        try:
            print(f'[JUNTADA][DEBUG] Selecionando modelo atos.py: {modelo}')
            
            # 1. Foco e preenchimento do filtro (padrão atos.py)
            try:
                from selenium.webdriver.common.keys import Keys
                campo_filtro_modelo = self.driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
                self.driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                self.driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, modelo)
                
                # Dispara eventos como no atos.py
                for ev in ['input', 'change', 'keyup']:
                    self.driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
                
                # Simula Enter
                campo_filtro_modelo.send_keys(Keys.ENTER)
                print(f'[JUNTADA][DEBUG] Modelo "{modelo}" preenchido via JS e ENTER pressionado no filtro.')
                
            except Exception as e:
                print(f'[JUNTADA][ERRO] Falha ao preencher filtro: {e}')
                return False
            
            # 2. Seleciona o modelo filtrado destacado (padrão atos.py)
            try:
                seletor_item_filtrado = '.nodo-filtrado'
                wait = WebDriverWait(self.driver, 15)
                nodo = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_item_filtrado)))
                if not nodo:
                    print('[JUNTADA][ERRO] Nodo do modelo não encontrado!')
                    return False
                
                self.driver.execute_script("arguments[0].click();", nodo)
                print('[JUNTADA][DEBUG] Clique em nodo-filtrado realizado!')
                
            except Exception as e:
                print(f'[JUNTADA][ERRO] Falha ao clicar no nodo filtrado: {e}')
                return False
            
            # 3. Aguarda e clica no botão inserir modelo (padrão atos.py)
            try:
                seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
                wait = WebDriverWait(self.driver, 15)
                btn_inserir = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_btn_inserir)))
                if not btn_inserir:
                    print('[JUNTADA][ERRO] Botão de inserir modelo não encontrado!')
                    return False
                
                time.sleep(0.6)
                # Pressiona ESPAÇO para inserir o modelo (padrão atos.py)
                from selenium.webdriver.common.keys import Keys
                btn_inserir.send_keys(Keys.SPACE)
                print('[JUNTADA][DEBUG] Modelo inserido pressionando ESPAÇO no botão Inserir (padrão atos.py).')
                
                time.sleep(2)  # Aguarda inserção
                return True
                
            except Exception as e:
                print(f'[JUNTADA][ERRO] Falha ao inserir modelo: {e}')
                return False
                
        except Exception as e:
            print(f'[JUNTADA][ERRO] Falha geral na seleção do modelo: {e}')
            return False

    def substituir_palavra_por_clipboard(self, palavra_chave="link", seletor_editor="div.fr-element"):
        """
        Substitui uma palavra-chave no editor pelo conteúdo da área de transferência.
        Inspirado na funcionalidade de pec_decisao.
        
        Args:
            palavra_chave (str): Palavra a ser substituída (padrão: "link")
            seletor_editor (str): Seletor do editor de texto (padrão: "div.fr-element")
        
        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            print(f'[JUNTADA][DEBUG] Substituindo "{palavra_chave}" pelo conteúdo da área de transferência...')
            
            # 1. Obter conteúdo da área de transferência
            clipboard_content = self.driver.execute_script("""
                return navigator.clipboard.readText().then(text => text).catch(err => '');
            """)
            
            if not clipboard_content:
                print('[JUNTADA][WARN] Área de transferência vazia ou inacessível')
                return False
                
            print(f'[JUNTADA][DEBUG] Conteúdo da área de transferência: {clipboard_content[:100]}...')
            
            # 2. Localizar o editor
            try:
                wait = WebDriverWait(self.driver, 10)
                editor = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, seletor_editor)))
                print(f'[JUNTADA][DEBUG] Editor encontrado: {seletor_editor}')
            except Exception as e:
                print(f'[JUNTADA][ERRO] Editor não encontrado: {e}')
                return False
            
            # 3. Substituir palavra-chave pelo conteúdo da área de transferência
            substituicao_script = f"""
                var editor = arguments[0];
                var palavraChave = arguments[1];
                var novoTexto = arguments[2];
                
                // Função para substituir texto preservando formatação
                function substituirTexto(elemento) {{
                    if (elemento.nodeType === Node.TEXT_NODE) {{
                        if (elemento.textContent.includes(palavraChave)) {{
                            elemento.textContent = elemento.textContent.replace(new RegExp(palavraChave, 'g'), novoTexto);
                            return true;
                        }}
                    }} else {{
                        var substituiu = false;
                        for (var i = 0; i < elemento.childNodes.length; i++) {{
                            if (substituirTexto(elemento.childNodes[i])) {{
                                substituiu = true;
                            }}
                        }}
                        return substituiu;
                    }}
                    return false;
                }}
                
                // Executa a substituição
                var resultado = substituirTexto(editor);
                
                // Dispara eventos para notificar mudanças
                if (resultado) {{
                    var eventos = ['input', 'change', 'keyup'];
                    eventos.forEach(function(tipoEvento) {{
                        var evt = new Event(tipoEvento, {{bubbles: true}});
                        editor.dispatchEvent(evt);
                    }});
                }}
                
                return resultado;
            """
            
            resultado = self.driver.execute_script(substituicao_script, editor, palavra_chave, clipboard_content)
            
            if resultado:
                print(f'[JUNTADA][DEBUG] Substituição realizada com sucesso: "{palavra_chave}" → conteúdo da área de transferência')
                return True
            else:
                print(f'[JUNTADA][WARN] Palavra-chave "{palavra_chave}" não encontrada no editor')
                return False
                
        except Exception as e:
            print(f'[JUNTADA][ERRO] Falha na substituição por clipboard: {e}')
            return False

    def juntar_pdf_direto(self, caminho_pdf, configuracao):
        """
        Realiza a juntada direta de um arquivo PDF, preenchendo os campos necessários e anexando o arquivo.
        Args:
            caminho_pdf (str): Caminho absoluto do arquivo PDF a ser juntado.
            configuracao (dict): Parâmetros da juntada (tipo, descricao, sigilo, modelo, assinar, etc).
        Returns:
            bool: True se sucesso, False se falha.
        """
        print(f"[JUNTADA][PDF][DEBUG] Iniciando juntada direta de PDF: {caminho_pdf}")
        try:
            # 1. Preencher Tipo de Documento
            tipo = configuracao.get('tipo', 'Documento')
            if not self.preencher_campo_robusto(['input[aria-label="Tipo de Documento"]'], tipo, 'Tipo de Documento'):
                print('[JUNTADA][PDF][ERRO] Não foi possível preencher o campo Tipo de Documento.')
                return False

            # 2. Preencher Descrição
            descricao = configuracao.get('descricao', '')
            if descricao:
                if not self.preencher_campo_robusto(['input[aria-label="Descrição"]'], descricao, 'Descrição'):
                    print('[JUNTADA][PDF][ERRO] Não foi possível preencher o campo Descrição.')
                    return False

            # 3. Configurar Sigilo
            sigilo = configuracao.get('sigilo', 'nao').lower()
            if 'sim' in sigilo:
                if not self.clicar_elemento_robusto(['input[name="sigiloso"]'], 'Sigilo'):
                    print('[JUNTADA][PDF][ERRO] Não foi possível ativar sigilo.')
                    return False
                print("[JUNTADA][PDF][DEBUG] Sigilo aplicado.")

            # 4. Upload do PDF
            seletores_upload = [
                'input[type="file"]',
                'input[accept="application/pdf"]',
                'input[aria-label*="Arquivo"]',
            ]
            upload_ok = False
            for seletor in seletores_upload:
                try:
                    campo_upload = self.driver.find_element(By.CSS_SELECTOR, seletor)
                    if campo_upload.is_displayed() and campo_upload.is_enabled():
                        campo_upload.send_keys(caminho_pdf)
                        print(f'[JUNTADA][PDF][DEBUG] Upload do PDF realizado via seletor: {seletor}')
                        upload_ok = True
                        break
                except Exception as e:
                    print(f'[JUNTADA][PDF][WARN] Falha ao tentar upload com seletor {seletor}: {e}')
            if not upload_ok:
                print('[JUNTADA][PDF][ERRO] Não foi possível realizar o upload do PDF.')
                return False

            # 5. Salvar
            if not self.clicar_elemento_robusto(['button[aria-label="Salvar"]'], 'Salvar'):
                print('[JUNTADA][PDF][ERRO] Não foi possível clicar em Salvar.')
                return False
            print("[JUNTADA][PDF][OK] Documento PDF salvo com sucesso.")

            # 6. Assinar, se necessário
            if configuracao.get('assinar', 'nao').lower() == 'sim':
                if not self.clicar_elemento_robusto(['button[aria-label="Assinar documento e juntar ao processo"]'], 'Assinar'):
                    print('[JUNTADA][PDF][ERRO] Não foi possível assinar o documento.')
                    return False
                print("[JUNTADA][PDF][OK] Documento assinado com sucesso.")

            # 7. Visibilidade extra se sigilo
            aplicar_visibilidade_se_necessario(self.driver, configuracao.get('sigilo', 'nao'))
            print('[JUNTADA][PDF][OK] Fluxo de juntada direta de PDF finalizado com sucesso.')
            return True
        except Exception as e:
            print(f'[JUNTADA][PDF][ERRO] Falha geral na juntada direta de PDF: {e}')
            return False

    def substituir_link_amarelo(self):
        """
        Substitui o texto "link" (marcado em amarelo) pelo conteúdo do clipboard usando JavaScript,
        sem tentar colar via send_keys, para evitar problemas de foco e seleção.
        """
        try:
            # Aguarda o modelo carregar
            time.sleep(3)
            print("[JUNTADA] Procurando elemento 'link' amarelo para substituir via JS...")
            # Usa método robusto já existente
            resultado = self.substituir_palavra_por_clipboard(palavra_chave="link", seletor_editor="div.fr-element")
            if resultado:
                print("[JUNTADA] ✓ Substituição de 'link' realizada com sucesso via JS")
                return True
            else:
                print("[JUNTADA] ⚠ Não foi possível substituir 'link' via JS")
                return False
        except Exception as e:
            print(f"[JUNTADA] ⚠ Erro ao tentar substituir 'link' via JS: {e}")
            return False

def aplicar_visibilidade_se_necessario(driver, sigilo, log=True):
def make_anexo_wrapper(
    tipo="Certidão",
    descricao="",
    sigilo="nao",
    modelo="",
    assinar="nao",
    substituir_link=False
):
    """
    Função que gera wrapper para anexos seguindo padrão do atos.py make_comunicacao_wrapper.
    """
    def wrapper(driver, debug=False, **kwargs):
        """
        Wrapper function que aceita parâmetros adicionais para compatibilidade.
        Args:
            driver: Selenium WebDriver instance
            debug: Se deve exibir logs detalhados
            **kwargs: Parâmetros adicionais (ex: log, ecarta_html) - pode ser usado para substituir o link
        """
        config = {
            "tipo": tipo,
            "descricao": descricao,
            "sigilo": sigilo,
            "modelo": modelo,
            "assinar": assinar,
            "visibilidade": "sim"
        }
        juntador = JuntadaAutomatica(driver)
        ecarta_html = kwargs.get("ecarta_html")
        if substituir_link and ecarta_html:
            try:
                # 1. Executa juntada até o modelo ser inserido, mas NÃO clica em Salvar ainda
                resultado = juntador.executar_juntada_ate_editor(config)
                if not resultado:
                    print("[JUNTADA][EXTRA][ERRO] Falha ao chegar até o editor para substituição!")
                    return False
                # 2. Substitui 'link' pelo HTML
                print("[JUNTADA][EXTRA] Substituindo 'link' pelo conteúdo passado via argumento (sem clipboard)...")
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                try:
                    editor = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".ck-editor__editable[contenteditable='true']"))
                    )
                except Exception:
                    editor = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element"))
                    )
                # Aqui você pode adicionar a lógica de substituição do HTML conforme necessário
                # ...existing code...
            except Exception as e:
                print(f"[JUNTADA][EXTRA][ERRO] Falha geral no fluxo de substituição: {e}")
                return False
        else:
            return juntador.executar_juntada(config, substituir_link=substituir_link)
    return wrapper

def make_anexo_wrapper(
    tipo="Certidão",
    descricao="",
    sigilo="nao",
    modelo="",
    assinar="nao",
    substituir_link=False
):
    """
    Função que gera wrapper para anexos seguindo padrão do atos.py make_comunicacao_wrapper.
    """
    def wrapper(driver, debug=False, **kwargs):
        """
        Wrapper function que aceita parâmetros adicionais para compatibilidade.
        Args:
            driver: Selenium WebDriver instance
            debug: Se deve exibir logs detalhados
            **kwargs: Parâmetros adicionais (ex: log, ecarta_html) - pode ser usado para substituir o link
        """
        config = {
            "tipo": tipo,
            "descricao": descricao,
            "sigilo": sigilo,
            "modelo": modelo,
            "assinar": assinar,
            "visibilidade": "sim"
        }
        juntador = JuntadaAutomatica(driver)
        ecarta_html = kwargs.get("ecarta_html")
        if substituir_link and ecarta_html:
            try:
                # 1. Executa juntada até o modelo ser inserido, mas NÃO clica em Salvar ainda
                resultado = juntador.executar_juntada_ate_editor(config)
                if not resultado:
                    print("[JUNTADA][EXTRA][ERRO] Falha ao chegar até o editor para substituição!")
                    return False
                # 2. Substitui 'link' pelo HTML
                print("[JUNTADA][EXTRA] Substituindo 'link' pelo conteúdo passado via argumento (sem clipboard)...")
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                try:
                    editor = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".ck-editor__editable[contenteditable='true']"))
                    )
                except Exception:
                    editor = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element"))
                    )
                # Aqui você pode adicionar a lógica de substituição do HTML conforme necessário
                # ...existing code...
            except Exception as e:
                print(f"[JUNTADA][EXTRA][ERRO] Falha geral no fluxo de substituição: {e}")
                return False
        else:
            return juntador.executar_juntada(config, substituir_link=substituir_link)
    return wrapper



# Factory para wrappers de automação de anexos
def make_anexo_wrapper(nome, classe):
    def wrapper(*args, **kwargs):
        return classe(*args, **kwargs)
    wrapper.__name__ = nome
    return wrapper

# Wrapper exportado para importação externa
rastreaamento = make_anexo_wrapper("rastreaamento", JuntadaAutomatica)

def debug_editor_completo_anexos(driver, log=True):
    """
    Debug completo do editor para localizar seletores e estrutura do conteúdo.
    Identifica especificamente o texto "link" marcado com fundo amarelo.
    Versão específica para anexos.py.
    """
    if log:
        print("[DEBUG_EDITOR_ANEXOS] Iniciando análise completa do editor...")
    try:
        # 1. Verifica se o editor principal existe
        editor_wrapper = driver.find_elements(By.CSS_SELECTOR, 'div.editor-wrapper')
        if log:
            print(f"[DEBUG_EDITOR_ANEXOS] Editor wrappers encontrados: {len(editor_wrapper)}")
        # 2. Localiza área de conteúdo editável (diferentes tipos de editor)
        seletores_editor = [
            '.area-conteudo.ck.ck-content.ck-editor__editable',  # CKEditor (current)
            'div.fr-element',  # FroalaEditor
            '.ck-editor__editable',  # CKEditor alternativo
            '[contenteditable="true"]'  # Genérico
        ]
        area_conteudo = None
        for seletor in seletores_editor:
            elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
            if elementos:
                area_conteudo = elementos[0]
                if log:
                    print(f"[DEBUG_EDITOR_ANEXOS] Editor encontrado com seletor: {seletor}")
                break
        if log:
            print(f"[DEBUG_EDITOR_ANEXOS] Áreas de conteúdo editável: {1 if area_conteudo else 0}")
        if area_conteudo:
            conteudo_html = area_conteudo.get_attribute('innerHTML')
            if log:
                print(f"[DEBUG_EDITOR_ANEXOS] HTML interno da área editável:")
                print(f"[DEBUG_EDITOR_ANEXOS] {conteudo_html[:500]}...")
        # 3. Busca especificamente por texto marcado (fundo amarelo)
        elementos_marcados = driver.find_elements(By.CSS_SELECTOR, 'mark.marker-yellow')
        if log:
            print(f"[DEBUG_EDITOR_ANEXOS] Elementos com marca amarela encontrados: {len(elementos_marcados)}")
        for i, elemento in enumerate(elementos_marcados):
            texto = elemento.text
            if log:
                print(f"[DEBUG_EDITOR_ANEXOS] Marca {i+1}: '{texto}'")
                print(f"[DEBUG_EDITOR_ANEXOS] HTML: {elemento.get_attribute('outerHTML')}")
                print(f"[DEBUG_EDITOR_ANEXOS] Visível: {elemento.is_displayed()}")
        # 4. Busca por "link" em diferentes contextos
        seletores_link = [
            'mark.marker-yellow',
            'mark[class*="yellow"]',
            '*[contains(text(), "link")]'
        ]
        for seletor in seletores_link:
            try:
                if 'contains' in seletor:
                    # XPath para texto
                    elementos = driver.find_elements(By.XPATH, f"//*[contains(text(), 'link')]")
                else:
                    # CSS Selector
                    elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                if log:
                    print(f"[DEBUG_EDITOR_ANEXOS] Seletor '{seletor}': {len(elementos)} elementos")
                for elem in elementos:
                    if 'link' in elem.text.lower():
                        if log:
                            print(f"[DEBUG_EDITOR_ANEXOS] ✓ Encontrado 'link' em: {elem.text}")
                            print(f"[DEBUG_EDITOR_ANEXOS] ✓ Seletor usado: {seletor}")
                            print(f"[DEBUG_EDITOR_ANEXOS] ✓ HTML: {elem.get_attribute('outerHTML')}")
            except Exception as e:
                if log:
                    print(f"[DEBUG_EDITOR_ANEXOS] ⚠ Erro no seletor '{seletor}': {e}")
        # 5. Análise DOM específica para o padrão identificado
        if log:
            print(f"[DEBUG_EDITOR_ANEXOS] Analisando estrutura DOM específica...")
        # Baseado no HTML fornecido: <mark class="marker-yellow">"link"</mark>
        try:
            mark_elements = driver.find_elements(By.CSS_SELECTOR, 'mark.marker-yellow')
            for mark in mark_elements:
                texto_completo = mark.text
                if log:
                    print(f"[DEBUG_EDITOR_ANEXOS] Mark encontrado: '{texto_completo}'")
                    print(f"[DEBUG_EDITOR_ANEXOS] Parent element: {mark.find_element(By.XPATH, '..').tag_name}")
                    print(f"[DEBUG_EDITOR_ANEXOS] Parent class: {mark.find_element(By.XPATH, '..').get_attribute('class')}")
                # Verifica se contém "link"
                if '"link"' in texto_completo or 'link' in texto_completo.lower():
                    if log:
                        print(f"[DEBUG_EDITOR_ANEXOS] ✓ ELEMENTO ALVO IDENTIFICADO!")
                        print(f"[DEBUG_EDITOR_ANEXOS] ✓ Texto: '{texto_completo}'")
                        print(f"[DEBUG_EDITOR_ANEXOS] ✓ Seletor CSS: mark.marker-yellow")
                        print(f"[DEBUG_EDITOR_ANEXOS] ✓ XPath: //mark[@class='marker-yellow']")
                    return mark  # Retorna o elemento encontrado
        except Exception as e:
            if log:
                print(f"[DEBUG_EDITOR_ANEXOS] ⚠ Erro na análise DOM específica: {e}")
        # 6. Teste de JavaScript para acessar conteúdo
        if log:
            print(f"[DEBUG_EDITOR_ANEXOS] Testando acesso via JavaScript...")
        try:
            # Executa JavaScript para encontrar elementos
            js_result = driver.execute_script("""
                // Busca por todos os elementos mark com classe marker-yellow
                var marks = document.querySelectorAll('mark.marker-yellow');
                var results = [];
                for (var i = 0; i < marks.length; i++) {
                    var mark = marks[i];
                    results.push({
                        text: mark.textContent,
                        innerHTML: mark.innerHTML,
                        outerHTML: mark.outerHTML,
                        className: mark.className,
                        visible: mark.offsetParent !== null
                    });
                }
                return results;
            """)
            if log:
                print(f"[DEBUG_EDITOR_ANEXOS] Resultado JavaScript: {js_result}")
            for result in js_result:
                if 'link' in result['text'].lower():
                    if log:
                        print(f"[DEBUG_EDITOR_ANEXOS] ✓ JS encontrou elemento alvo: {result}")
        except Exception as e:
            if log:
                print(f"[DEBUG_EDITOR_ANEXOS] ⚠ Erro no JavaScript: {e}")
        if log:
            print(f"[DEBUG_EDITOR_ANEXOS] Análise completa finalizada.")
        return None
    except Exception as e:
        if log:
            print(f"[DEBUG_EDITOR_ANEXOS] ✗ Erro geral na análise: {e}")
        return None

def substituir_link_por_clipboard_anexos(driver, debug=True):
    """
    Função específica para substituir "link" por conteúdo do clipboard
    com debug detalhado. Versão para anexos.py.
    """
    if debug:
        print("[SUBST_LINK_ANEXOS] Iniciando substituição de 'link' por clipboard...")
    
    try:
        # 1. Primeiro executa debug completo
        if debug:
            print("[SUBST_LINK_ANEXOS] Executando debug completo do editor...")
        elemento_alvo = debug_editor_completo_anexos(driver, log=debug)
        
        # 2. Busca específica pelo elemento mark.marker-yellow
        if debug:
            print("[SUBST_LINK_ANEXOS] Buscando elemento mark.marker-yellow...")
            
        mark_elements = driver.find_elements(By.CSS_SELECTOR, 'mark.marker-yellow')
        
        if not mark_elements:
            if debug:
                print("[SUBST_LINK_ANEXOS] ✗ Nenhum elemento mark.marker-yellow encontrado")
            return False
            
        # 3. Identifica o elemento que contém "link"
        elemento_link = None
        for mark in mark_elements:
            texto = mark.text
            if debug:
                print(f"[SUBST_LINK_ANEXOS] Analisando mark: '{texto}'")
                
            if '"link"' in texto or 'link' in texto.lower():
                elemento_link = mark
                if debug:
                    print(f"[SUBST_LINK_ANEXOS] ✓ Elemento alvo encontrado: '{texto}'")
                break
        
        if not elemento_link:
            if debug:
                print("[SUBST_LINK_ANEXOS] ✗ Elemento contendo 'link' não encontrado")
            return False
        
        # 4. Executa substituição via JavaScript com clipboard
        if debug:
            print("[SUBST_LINK_ANEXOS] Executando substituição via JavaScript...")
            
        resultado = driver.execute_script("""
            return new Promise((resolve) => {
                // Função para substituir texto preservando formatação
                function substituirTextoPreservandoFormatacao(elemento, textoAntigo, textoNovo) {
                    // Percorre todos os nós filhos
                    function percorrerNos(node) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            if (node.textContent.includes(textoAntigo)) {
                                node.textContent = node.textContent.replace(textoAntigo, textoNovo);
                                return true;
                            }
                        } else {
                            for (let child of node.childNodes) {
                                if (percorrerNos(child)) return true;
                            }
                        }
                        return false;
                    }
                    
                    return percorrerNos(elemento);
                }
                
                // Tenta acessar clipboard
                if (navigator.clipboard && navigator.clipboard.readText) {
                    navigator.clipboard.readText()
                        .then(clipboardText => {
                            console.log('[SUBST_LINK_ANEXOS] Clipboard lido:', clipboardText);
                            
                            // Encontra elemento mark.marker-yellow
                            const marks = document.querySelectorAll('mark.marker-yellow');
                            let substituido = false;
                            
                            for (const mark of marks) {
                                if (mark.textContent.includes('link')) {
                                    console.log('[SUBST_LINK_ANEXOS] Substituindo em:', mark.textContent);
                                    
                                    // Preserva as aspas se existirem
                                    let textoCompleto = mark.textContent;
                                    let novoTexto;
                                    
                                    if (textoCompleto.includes('"link"')) {
                                        novoTexto = textoCompleto.replace('"link"', '"' + clipboardText + '"');
                                    } else {
                                        novoTexto = textoCompleto.replace('link', clipboardText);
                                    }
                                    
                                    // Substitui o texto completo do elemento
                                    mark.textContent = novoTexto;
                                    
                                    console.log('[SUBST_LINK_ANEXOS] ✓ Substituição realizada:', novoTexto);
                                    
                                    // Dispara eventos de mudança
                                    const evento = new Event('input', { bubbles: true });
                                    mark.dispatchEvent(evento);
                                    
                                    // Evento nos editores possíveis
                                    const editores = [
                                        '.ck-editor__editable',
                                        'div.fr-element',
                                        '.area-conteudo'
                                    ];
                                    
                                    for (const seletor of editores) {
                                        const editor = document.querySelector(seletor);
                                        if (editor) {
                                            editor.dispatchEvent(new Event('input', { bubbles: true }));
                                            editor.dispatchEvent(new Event('change', { bubbles: true }));
                                        }
                                    }
                                    
                                    substituido = true;
                                    break;
                                }
                            }
                            
                            resolve({
                                sucesso: substituido,
                                clipboardText: clipboardText,
                                message: substituido ? 'Substituição realizada' : 'Elemento não encontrado'
                            });
                        })
                        .catch(error => {
                            console.error('[SUBST_LINK_ANEXOS] Erro ao ler clipboard:', error);
                            resolve({
                                sucesso: false,
                                error: error.message,
                                message: 'Erro ao acessar clipboard'
                            });
                        });
                } else {
                    resolve({
                        sucesso: false,
                        message: 'Clipboard API não disponível'
                    });
                }
            });
        """)
        
        if debug:
            print(f"[SUBST_LINK_ANEXOS] Resultado da execução: {resultado}")
            
        if resultado and resultado.get('sucesso'):
            if debug:
                print(f"[SUBST_LINK_ANEXOS] ✓ Substituição bem-sucedida!")
                print(f"[SUBST_LINK_ANEXOS] ✓ Texto do clipboard: '{resultado.get('clipboardText')}'")
            return True
        else:
            if debug:
                print(f"[SUBST_LINK_ANEXOS] ✗ Falha na substituição: {resultado.get('message')}")
            return False
            
    except Exception as e:
        if debug:
            print(f"[SUBST_LINK_ANEXOS] ✗ Erro na substituição: {e}")
        return False