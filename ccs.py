"""
ccs.py - Automação para preenchimento de formulários no sistema CCS

Replica a funcionalidade da extensão PJePlus para automação no CCS
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Fix import extrair_dados_processo  # Função existente no Fix.py
import time
from datetime import datetime, timedelta

class CCSAutomation:
    def __init__(self, driver):
        self.driver = driver
        self.ccs_url = "https://www3.bcb.gov.br/ccs/dologin"
    
    async def preencher_campos_ccs(self):
        """Replica exatamente a função preenchercamposCCS() usando dados do fix.py"""
        if not self.driver.current_url.startswith(self.ccs_url):
            return
            
        # Verificar se está na página correta
        if not self._elemento_existe('input[name="numeroProcesso"]'):
            self.driver.get(f"{self.ccs_url}/requisitarConsultaCpfCnpj.do?method=iniciar&maisPje=preencherCampos")
            return
        
        print("   |___PREENCHER CAMPOS")
        
        # Obter dados do processo do fix.py
        dados_processo = extrair_dados_processo(self.driver)
        
        # 1. Número do Processo
        print("      |___NUMERO DO PROCESSO")
        el = self.driver.find_element(By.CSS_SELECTOR, 'input[name="numeroProcesso"]')
        el.clear()
        el.send_keys(dados_processo.get('Número do Processo', ''))
        self._trigger_input_event(el)
        
        # 2. Motivo da Consulta
        print("      |___MOTIVO DA CONSULTA")
        el = self.driver.find_element(By.CSS_SELECTOR, 'textarea[name="motivoConsulta"]')
        el.clear()
        el.send_keys('Execução trabalhista')
        self._trigger_input_event(el)
        
        # 3. Data de Início (1 ano atrás)
        print("      |___DATA DE INÍCIO")
        data_inicio = (datetime.now() - timedelta(days=365)).strftime('%d/%m/%Y')
        el = self.driver.find_element(By.CSS_SELECTOR, 'input[name="dataInicio"]')
        el.clear()
        el.send_keys(data_inicio)
        self._trigger_input_event(el)
        
        # 4. Data de Fim (hoje)
        print("      |___DATA DE FIM")
        data_fim = datetime.now().strftime('%d/%m/%Y')
        el = self.driver.find_element(By.CSS_SELECTOR, 'input[name="dataFim"]')
        el.clear()
        el.send_keys(data_fim)
        self._trigger_input_event(el)
        
        # 5. Inserção dos Réus (assume que a função retorna partes em formato específico)
        print("      |___INSERÇÃO DOS RÉUS")
        cpfs_cnpjs = "\n".join([
            parte.split('CPF/CNPJ:')[1].strip() 
            for parte in dados_processo.get('Partes', []) 
            if 'CPF/CNPJ:' in parte
        ])
        el = self.driver.find_element(By.CSS_SELECTOR, 'textarea[name="cpfCnpj"]')
        el.clear()
        el.send_keys(cpfs_cnpjs)
        self._trigger_input_event(el)
        
        print("      |___FIM")
        
        # Clicar no botão Continuar
        bt_continuar = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[value="Continuar"]'))
        )
        bt_continuar.click()
    
    def _elemento_existe(self, seletor):
        """Verifica se elemento existe"""
        try:
            self.driver.find_element(By.CSS_SELECTOR, seletor)
            return True
        except:
            return False
    
    def _trigger_input_event(self, element):
        """Dispara evento input como no JavaScript original"""
        self.driver.execute_script("""
            var event = new Event('input', { bubbles: true });
            arguments[0].dispatchEvent(event);
        """, element)

    def inject_button(self):
        """Injeta um botão de automação na página do CCS"""
        script = """
        var btn = document.createElement('button');
        btn.id = 'autoCCS';
        btn.style = 'position:fixed;bottom:20px;right:20px;z-index:9999;padding:10px;background:#4CAF50;color:white;border:none;border-radius:4px;';
        btn.textContent = 'Preencher Automaticamente';
        btn.onclick = function() {
            // Lógica de preenchimento será adicionada aqui
            alert('Funcionalidade de preenchimento será executada!');
        };
        document.body.appendChild(btn);
        """
        self.driver.execute_script(script)
    
    def executar_fluxo(self):
        """Executa o fluxo completo de automação"""
        if self.driver.current_url.startswith(self.ccs_url):
            self.inject_button()
            # Implementar lógica completa baseada na função preenchercamposCCS()
            # da extensão original

if __name__ == "__main__":
    # Configuração inicial do driver
    driver = webdriver.Firefox()  # Usando Firefox como na memória do projeto
    driver.get("https://www3.bcb.gov.br/ccs/dologin")
    
    # Instanciar e executar automação
    ccs = CCSAutomation(driver)
    ccs.executar_fluxo()
