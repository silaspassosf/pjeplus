from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

class JuntadaAutomatica:
    """
    Classe responsável por gerenciar a juntada automática de anexos, com fluxo robusto inspirado em ato_judicial.
    """
    def __init__(self, driver):
        self.driver = driver

    def executar_juntada(self, configuracao):
        """
        Executa a juntada automática de anexos com base na configuração fornecida.
        Se modelo for 'PDF', chama fluxo de juntada direta de PDF, senão segue fluxo normal.
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
        # Troca o sufixo da URL por /documento/anexar (robusto)
        url_anexar = re.sub(r'/[^/]*$', '/documento/anexar', url_atual)
        print(f'[JUNTADA][DEBUG] Abrindo nova aba para anexar: {url_anexar}')
        abas_antes = set(driver.window_handles)
        driver.execute_script(f"window.open('{url_anexar}', '_blank');")
        # Aguarda a nova aba aparecer (timeout de 10s)
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.5)
        if not nova_aba:
            print('[JUNTADA][ERRO] Nova aba de anexar não foi aberta.')
            return False
        try:
            driver.switch_to.window(nova_aba)
        except Exception as e:
            print(f'[JUNTADA][ERRO] Não foi possível trocar para nova aba de anexar: {e}')
            return False
        time.sleep(2)
        if not re.search(r'/anexar$', driver.current_url):
            print(f'[JUNTADA][ERRO] URL inesperada após abrir aba de anexar: {driver.current_url}')
            return False
        print(f'[JUNTADA][DEBUG] Nova aba de anexar aberta e foco trocado com sucesso.')

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

            # 4. Selecionar Modelo (se houver)
            modelo = configuracao.get('modelo', '')
            if modelo:
                if not self.selecionar_modelo_robusto(modelo):
                    print('[JUNTADA][ERRO] Não foi possível selecionar o modelo.')
                    return False

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
                    campo.clear()
                    campo.send_keys(valor)
                    print(f'[JUNTADA][DEBUG] Campo {nome_campo} preenchido via seletor: {seletor}')
                    return True
            except Exception as e:
                print(f'[JUNTADA][WARN] Falha ao tentar preencher {nome_campo} com seletor {seletor}: {e}')
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

    def selecionar_modelo_robusto(self, modelo):
        print(f"[JUNTADA][DEBUG] Selecionando modelo: {modelo}")
        try:
            campo_filtro = self.driver.find_element(By.CSS_SELECTOR, 'input[aria-label*="Modelo"]')
            campo_filtro.clear()
            campo_filtro.send_keys(modelo)
            from selenium.webdriver.common.keys import Keys
            campo_filtro.send_keys(Keys.ENTER)
            print(f'[JUNTADA][DEBUG] Filtro de modelo preenchido: {modelo}')
            # Seleciona o modelo filtrado (ajustar seletor conforme DOM real)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            modelo_item = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{modelo}') or contains(., '{modelo}')]"))
            )
            self.driver.execute_script("arguments[0].click();", modelo_item)
            print(f'[JUNTADA][OK] Modelo selecionado: {modelo}')
            return True
        except Exception as e:
            print(f'[JUNTADA][WARN] Falha ao selecionar modelo: {e}')
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

# Exemplo de template para configuração de juntada automática
def criar_template_juntada():
    """
    Cria um template de configuração para juntada automática de anexos.

    Returns:
        dict: Template de configuração.
    """
    return {
        "nm_botao": "Nome do Botão",
        "tipo": "Certidão",
        "descricao": "Descrição do Documento",
        "sigilo": "nao",
        "modelo": "",
        "assinar": "nao",
        "vinculo": "Nenhum",
        "visibilidade": "sim"
    }

# Função auxiliar para aplicar visibilidade extra após juntada, se sigilo for 'sim'
def aplicar_visibilidade_se_necessario(driver, sigilo, log=True):
    if str(sigilo).lower() in ("sim", "true", "1"):  # aceita várias formas de positivo
        try:
            from Fix import visibilidade_sigilosos
            visibilidade_sigilosos(driver, log=log)
            if log:
                print("[JUNTADA] Visibilidade extra aplicada por sigilo positivo.")
        except Exception as e:
            if log:
                print(f"[JUNTADA][ERRO] Falha ao aplicar visibilidade extra: {e}")

def def_carta(driver, ecarta_data, log=True):
    """
    Creates and attaches an eCarta certificate with the provided data.
    
    Args:
        driver: Selenium WebDriver instance
        ecarta_data: List of strings containing eCarta consultation results
        log: Whether to print log messages
    """
    try:
        # Create configuration for automatic attachment
        config = {
            "nm_botao": "Certidão",
            "tipo": "Certidão",
            "descricao": "Certidão eCarta",
            "sigilo": "nao",
            "modelo": "Certidão",
            "assinar": "sim",
            "vinculo": "Nenhum",
            "visibilidade": "sim"
        }
        
        # Initialize automatic attachment handler
        juntador = JuntadaAutomatica(driver)
        
        # Start attachment process
        juntador.executar_juntada(config)
        
        # After certidão is created, paste eCarta data into the document
        try:
            # Wait for editor
            editor = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.fr-element"))
            )
            
            # Format eCarta data
            formatted_data = "CERTIDÃO\n\n"
            formatted_data += "Certifico que, conforme consulta ao sistema eCarta em anexo, foram localizados os seguintes registros:\n\n"
            
            for idx, data in enumerate(ecarta_data, 1):
                formatted_data += f"{idx}. {data}\n"
                
            # Insert into editor
            editor.send_keys(formatted_data)
            
            if log:
                print("[CARTA] eCarta data inserted successfully")
            return True
            
        except Exception as e:
            if log:
                print(f"[CARTA] Error inserting eCarta data: {str(e)}")
            return False
            
    except Exception as e:
        if log:
            print(f"[CARTA] Error in def_carta: {str(e)}")
        return False

def make_anexo_wrapper():
    """
    Placeholder para wrapper padronizado de anexos. Ajuste conforme necessidade futura.
    """
    def wrapper(driver, tipo, descricao, sigilo, modelo, assinar, caminho_pdf=None, **kwargs):
        config = {
            'tipo': tipo,
            'descricao': descricao,
            'sigilo': sigilo,
            'modelo': modelo,
            'assinar': assinar,
            'caminho_pdf': caminho_pdf,
            **kwargs
        }
        juntador = JuntadaAutomatica(driver)
        return juntador.executar_juntada(config)
    return wrapper