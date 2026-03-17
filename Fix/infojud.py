"""
Fix.infojud

Módulo para funcionalidades relacionadas ao InfoJud no contexto PJe Python.
"""

import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import socket
import json
import os

PORT = int(os.environ.get('INFOJUD_PORT', 18765))

def enviar_url_infojud(url):
    """Envia URL para o Firefox via native messaging para abrir no perfil logado."""
    try:
        s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
        s.sendall((json.dumps({"action": "open_url", "url": url}) + "\n").encode("utf-8"))
        resp = s.recv(4096).decode("utf-8").strip()
        s.close()
        response = json.loads(resp)
        if response.get("ok"):
            print(f"URL enviada com sucesso: {url}")
            return True
        else:
            print(f"Erro ao enviar URL: {response.get('error', 'desconhecido')}")
            return False
    except Exception as e:
        print(f"Erro na comunicação com native host: {e}")
        return False

def consultar_cnpjs_infojud(driver_pje):
    """
    Lê o card de destinatários na página de comunicação PEC,
    extrai CNPJs únicos, normaliza-os e abre URLs no InfoJud via native messaging.

    Args:
        driver_pje: Instância do Selenium WebDriver na página de comunicação.

    Returns:
        None
    """
    try:
        # Localizar o fieldset da tabela de destinatários usando XPath mais robusto
        fieldset = driver_pje.find_element(By.XPATH, "//fieldset[legend[contains(text(), 'Expedientes e comunicações')]]")
        html = fieldset.get_attribute('outerHTML')
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Encontrar todos os spans que contêm "CNPJ: "
        cnpjs = []
        for span in soup.find_all('span', class_='pec-formatacao-padrao-dados-parte'):
            texto = span.get_text()
            # Procurar por CNPJ: seguido de números
            match = re.search(r'CNPJ:\s*([\d./-]+)', texto)
            if match:
                cnpj = match.group(1)
                # Normalizar: remover pontuações
                cnpj_normalizado = re.sub(r'[./-]', '', cnpj)
                cnpjs.append(cnpj_normalizado)
        
        # CNPJs únicos
        cnpjs_unicos = list(set(cnpjs))
        
        print(f"Quantidade de ocorrências diferentes de CNPJ: {len(cnpjs_unicos)}")
        print(f"CNPJs únicos encontrados: {cnpjs_unicos}")
        
        if not cnpjs_unicos:
            print("Nenhum CNPJ encontrado.")
            return
        
        # Enviar URLs via native messaging
        for cnpj in cnpjs_unicos:
            url = f"https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI={cnpj}"
            print(f"Enviando URL InfoJud: {url}")
            sucesso = enviar_url_infojud(url)
            if not sucesso:
                print(f"Falha ao enviar URL para CNPJ: {cnpj}")
    
    except Exception as e:
        print(f"Erro ao consultar CNPJs no InfoJud: {e}")
        input("Pressione Enter para continuar...")