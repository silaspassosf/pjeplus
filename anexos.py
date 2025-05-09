from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class JuntadaAutomatica:
    """
    Classe responsável por gerenciar a juntada automática de anexos.
    """

    def __init__(self, driver):
        self.driver = driver

    def executar_juntada(self, configuracao):
        """
        Executa a juntada automática de anexos com base na configuração fornecida.

        Args:
            configuracao (dict): Configuração contendo os parâmetros da juntada.
        """
        print(f"[JUNTADA] Iniciando juntada automática: {configuracao['nm_botao']}")

        # Escolhe o tipo de documento
        tipo = configuracao.get('tipo', 'Certidão')
        self.preencher_campo('input[aria-label="Tipo de Documento"]', tipo)

        # Preenche a descrição
        descricao = configuracao.get('descricao', '')
        if descricao:
            self.preencher_campo('input[aria-label="Descrição"]', descricao)

        # Configura sigilo
        sigilo = configuracao.get('sigilo', 'nao').lower()
        if 'sim' in sigilo:
            self.clicar_elemento('input[name="sigiloso"]')
            print("[JUNTADA] Sigilo aplicado.")

        # Escolhe o modelo
        modelo = configuracao.get('modelo', '')
        if modelo:
            self.selecionar_modelo(modelo)

        # Realiza a juntada
        self.clicar_elemento('button[aria-label="Salvar"]')
        print("[JUNTADA] Documento salvo com sucesso.")

        # Assina o documento, se necessário
        if configuracao.get('assinar', 'nao').lower() == 'sim':
            self.clicar_elemento('button[aria-label="Assinar documento e juntar ao processo"]')
            print("[JUNTADA] Documento assinado com sucesso.")
        # Após finalizar e voltar à aba de detalhes, aplica visibilidade se sigilo for positivo
        aplicar_visibilidade_se_necessario(self.driver, configuracao.get('sigilo', 'nao'))

    def preencher_campo(self, seletor, valor):
        """
        Preenche um campo de entrada com o valor fornecido.

        Args:
            seletor (str): Seletor CSS do campo.
            valor (str): Valor a ser preenchido.
        """
        campo = self.driver.find_element(By.CSS_SELECTOR, seletor)
        campo.clear()
        campo.send_keys(valor)

    def clicar_elemento(self, seletor):
        """
        Clica em um elemento identificado pelo seletor CSS.

        Args:
            seletor (str): Seletor CSS do elemento.
        """
        elemento = self.driver.find_element(By.CSS_SELECTOR, seletor)
        elemento.click()

    def selecionar_modelo(self, modelo):
        """
        Seleciona um modelo de documento.

        Args:
            modelo (str): Nome do modelo a ser selecionado.
        """
        print(f"[JUNTADA] Selecionando modelo: {modelo}")
        # Implementar lógica para selecionar o modelo

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