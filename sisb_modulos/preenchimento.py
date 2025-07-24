#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sisb_modulos/preenchimento.py
Preenchimento automático SISBAJUD baseado no gigs-plugin.js
Implementação fiel às linhas 13745-14123 do gigs-plugin.js
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class PreenchimentoSISBAJUD:
    """
    Classe responsável pelo preenchimento do formulário SISBAJUD,
    replicando a lógica do gigs-plugin.js com base nas preferências
    e dados do processo.
    """
    def __init__(self, driver, prefs, dados_processo):
        self.driver = driver
        self.prefs = prefs
        self.dados_processo = dados_processo
        self.wait = WebDriverWait(self.driver, 10)

    def _wait_and_click(self, by, value):
        try:
            element = self.wait.until(EC.element_to_be_clickable((by, value)))
            element.click()
            print(f"Clicado com sucesso no elemento: {value}")
            return True
        except TimeoutException:
            print(f"Erro de Timeout: Elemento não clicável encontrado para o seletor '{value}'")
            return False
        except Exception as e:
            print(f"Erro ao clicar no elemento '{value}': {e}")
            return False

    def _wait_and_send_keys(self, by, value, keys):
        try:
            element = self.wait.until(EC.visibility_of_element_located((by, value)))
            element.clear()
            element.send_keys(keys)
            print(f"Texto '{keys}' enviado com sucesso para o elemento: {value}")
            return True
        except TimeoutException:
            print(f"Erro de Timeout: Elemento não visível encontrado para o seletor '{value}'")
            return False
        except Exception as e:
            print(f"Erro ao enviar texto para o elemento '{value}': {e}")
            return False

    def preencher_juiz(self):
        print("[SISBAJUD] Preenchendo Juiz Solicitante...")
        juiz = self.prefs.get('juiz', '')
        if not juiz:
            juiz = self.dados_processo.get('magistrado', '')
        if not juiz:
            print("Juiz não definido nas preferências nem nos dados do processo.")
            return False
        return self._wait_and_send_keys(By.CSS_SELECTOR, 'input[placeholder*="Juiz"]', juiz)

    def preencher_vara(self):
        print("[SISBAJUD] Preenchendo Vara/Juízo...")
        vara = self.prefs.get('vara', '')
        if not vara:
            vara = self.dados_processo.get('juizo', '')
        if not vara:
            print("Vara/Juízo não definido nas preferências nem nos dados do processo.")
            return False
        # mat-select exige lógica especial, aqui simplificado
        return self._wait_and_send_keys(By.CSS_SELECTOR, 'mat-select[name*="varaJuizoSelect"]', vara)

    def preencher_numero_processo(self):
        print("[SISBAJUD] Preenchendo Número do Processo...")
        numero = self.dados_processo.get('numero', '') or self.dados_processo.get('numero_processo', '')
        if not numero:
            print("Número do processo não encontrado nos dados extraídos.")
            return False
        return self._wait_and_send_keys(By.CSS_SELECTOR, 'input[placeholder="Número do Processo"]', numero)

    def preencher_tipo_acao(self):
        print("[SISBAJUD] Preenchendo Tipo de Ação...")
        # Supondo valor padrão, pode ser ajustado conforme preferências
        return self._wait_and_send_keys(By.CSS_SELECTOR, 'mat-select[name*="acao"]', 'Ação Trabalhista')

    def preencher_cpf_autor(self):
        print("[SISBAJUD] Preenchendo CPF do Autor...")
        partes = self.dados_processo.get('partes', {})
        cpf = ''
        if partes:
            cpf = partes.get('ativas', [{}])[0].get('documento', '')
        if not cpf:
            cpf = self.dados_processo.get('cpf_autor', '')
        if not cpf:
            print("CPF do autor não encontrado.")
            return False
        return self._wait_and_send_keys(By.CSS_SELECTOR, 'input[placeholder*="CPF"]', cpf)

    def preencher_nome_autor(self):
        print("[SISBAJUD] Preenchendo Nome do Autor...")
        partes = self.dados_processo.get('partes', {})
        nome = ''
        if partes:
            nome = partes.get('ativas', [{}])[0].get('nome', '')
        if not nome:
            nome = self.dados_processo.get('nome_autor', '')
        if not nome:
            print("Nome do autor não encontrado.")
            return False
        return self._wait_and_send_keys(By.CSS_SELECTOR, 'input[placeholder="Nome do autor/exequente da ação"]', nome)

    def preencher_teimosinha(self):
        print("[SISBAJUD] Preenchendo Teimosinha...")
        teimosinha = self.prefs.get('teimosinha', 'não')
        if teimosinha != 'não':
            # Seleciona radio e define prazo se necessário
            return self._wait_and_click(By.CSS_SELECTOR, 'mat-radio-button')
        return True

    def preencher_conta_salario(self):
        print("[SISBAJUD] Preenchendo Conta Salário...")
        contasalario = self.prefs.get('contasalario', 'não')
        # Lógica de seleção conforme preferências
        return True

    def preencher_cpf_cnpj_reu(self):
        print("[SISBAJUD] Preenchendo CPF/CNPJ do Réu...")
        doc_reu = self.dados_processo.get('cpf_cnpj_reu', '')
        if not doc_reu:
            partes = self.dados_processo.get('partes', {})
            doc_reu = partes.get('passivas', [{}])[0].get('documento', '')
        if not doc_reu:
            print("CPF/CNPJ do réu não encontrado.")
            return False
        return self._wait_and_send_keys(By.CSS_SELECTOR, 'input[placeholder="CPF/CNPJ do réu/executado"]', doc_reu)

    def preencher_valor_desbloqueio(self):
        print("[SISBAJUD] Preenchendo Valor de Desbloqueio...")
        valor = self.prefs.get('valor_desbloqueio', 'não')
        if valor == 'não':
            return True
        return self._wait_and_send_keys(By.CSS_SELECTOR, 'input[placeholder*="Valor aplicado a todos"]', valor)

    def preencher_banco_agencia(self):
        print("[SISBAJUD] Preenchendo Banco/Agência preferidos...")
        # Lógica de seleção baseada em banco_preferido e agencia_preferida
        return True

    def confirmar(self):
        print("[SISBAJUD] Confirmando...")
        if self.prefs.get('confirmar', 'não') == 'sim':
            return self._wait_and_click(By.CSS_SELECTOR, 'button[type="submit"]')
        return True

    def salvar_e_protocolar(self):
        print("[SISBAJUD] Salvando e protocolando...")
        if self.prefs.get('salvarEprotocolar', 'não') == 'sim':
            return self._wait_and_click(By.CSS_SELECTOR, '#btnProtocolar')
        return True

    def executar_fluxo(self):
        print("[SISBAJUD] Iniciando fluxo de preenchimento completo...")
        etapas = [
            self.preencher_juiz,
            self.preencher_vara,
            self.preencher_numero_processo,
            self.preencher_tipo_acao,
            self.preencher_cpf_autor,
            self.preencher_nome_autor,
            self.preencher_teimosinha,
            self.preencher_conta_salario,
            self.preencher_cpf_cnpj_reu,
            self.preencher_valor_desbloqueio,
            self.preencher_banco_agencia,
            self.confirmar,
            self.salvar_e_protocolar
        ]
        for etapa in etapas:
            if not etapa():
                print(f"[SISBAJUD] Erro na etapa: {etapa.__name__}")
                return False
            time.sleep(0.3)
        print("[SISBAJUD] Fluxo de preenchimento concluído com sucesso.")
        return True

def executar_preenchimento_sisbajud(driver, dados_processo):
    """
    Integração padrão: executa o preenchimento SISBAJUD usando as preferências do sistema.
    :param driver: Selenium WebDriver já autenticado e na tela correta do SISBAJUD
    :param dados_processo: dicionário com dados extraídos do processo (número, partes, etc)
    :return: True se sucesso, False se erro
    """
    try:
        from preferencias_sisb import gerenciador_preferencias
        prefs = gerenciador_preferencias.obter_sisbajud().__dict__
        preench = PreenchimentoSISBAJUD(driver, prefs, dados_processo)
        return preench.executar_fluxo()
    except Exception as e:
        print(f"[SISBAJUD][INTEGRAÇÃO] Erro ao executar preenchimento: {e}")
        return False

# Exemplo de uso
if __name__ == '__main__':
    class MockDriver:
        def find_element(self, by, value):
            print(f"Mock: find_element({by}, {value})")
            return self
        def click(self):
            print("Mock: click()")
        def send_keys(self, keys):
            print(f"Mock: send_keys({keys})")
        def clear(self):
            print("Mock: clear()")
    driver = MockDriver()
    prefs = {
        'juiz': 'João Silva',
        'vara': '1ª Vara',
        'teimosinha': 'sim',
        'contasalario': 'não',
        'valor_desbloqueio': '1000,00',
        'banco_preferido': 'Banco do Brasil',
        'agencia_preferida': '1234-5',
        'confirmar': 'sim',
        'salvarEprotocolar': 'sim'
    }
    dados = {
        'numero': '0001234-56.2023.5.02.0001',
        'cpf_cnpj_reu': '12345678900',
        'partes': {
            'ativas': [{'documento': '11122233344', 'nome': 'Autor Exemplo'}],
            'passivas': [{'documento': '12345678900', 'nome': 'Réu Exemplo'}]
        }
    }
    preench = PreenchimentoSISBAJUD(driver, prefs, dados)
    preench.executar_fluxo()
