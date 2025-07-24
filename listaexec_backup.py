# Divisão simples do código original - mesma execução
import re
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from Fix import extrair_documento, criar_gigs
import time

# Importar as funções divididas
from listaexec.buscar_medidas import buscar_medidas_executorias
from listaexec.alvara_functions import alvara
from listaexec.file_functions import salvar_alvaras_processados_no_arquivo

def listaexec(driver, log=True):
    """
    Lista medidas executórias realizadas nos autos do PJe.
    Ao encontrar alvarás, extrai dados detalhados e salva em alvaras.js
    
    Args:
        driver: WebDriver do Selenium
        log: Se deve exibir logs (default: True)
    
    Returns:
        list: Lista de medidas executórias encontradas
    """
    
    # CÓDIGO ORIGINAL SEM MODIFICAÇÕES - apenas movido de lugar
    try:
        if log:
            print('[LISTAEXEC] Iniciando análise de medidas executórias...')
        
        # Usar função buscar_medidas_executorias dividida
        medidas = buscar_medidas_executorias(driver, log)
        
        # Encontrar alvarás para processar
        alvaras_encontrados = []
        for medida in medidas:
            # Buscar por alvarás ou qualquer documento que precise ser processado
            texto = medida.get('texto', '').lower()
            if any(termo in texto for termo in ['alvara', 'alvarà', 'autoriza', 'pagamento', 'liberacao', 'liberação']):
                alvaras_encontrados.append(medida)
        
        if log and alvaras_encontrados:
            print(f'[LISTAEXEC] Encontrados {len(alvaras_encontrados)} alvarás para processar')
        
        # Processar alvarás encontrados usando função dividida
        alvaras_processados = []
        for medida in alvaras_encontrados:
            try:
                elemento = medida.get('elemento')
                # Buscar link dentro do elemento
                links = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                link = links[0] if links else None
                data = medida.get('data', 'Data não encontrada')
                
                if link:
                    # Usar função alvara dividida
                    alvara_dados = alvara(driver, elemento, link, data, log)
                    if alvara_dados:
                        alvaras_processados.append(alvara_dados)
                        
            except Exception as e:
                if log:
                    print(f'[LISTAEXEC][ERRO] Erro ao processar alvará: {e}')
                continue
        
        # Salvar alvarás processados usando função dividida
        if alvaras_processados:
            salvar_alvaras_processados_no_arquivo(alvaras_processados, log)
        
        if log:
            print(f'[LISTAEXEC] ✅ Concluído: {len(medidas)} medidas, {len(alvaras_processados)} alvarás processados')
        
        return medidas
        
    except Exception as e:
        if log:
            print(f'[LISTAEXEC][ERRO] Erro na função principal: {e}')
        return []
