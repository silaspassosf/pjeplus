# extrair.py - Função única para extrair dados do processo via Selenium (PJe TRT2)
# Uso: importar e chamar extrair_dados_processo(driver, caminho_json)
from selenium.webdriver.common.by import By
import json
import re
import time
import requests
from urllib.parse import urlparse

def extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False):
    """
    Extrai dados do processo via API do PJe (TRT2), seguindo a mesma lógica da extensão MaisPje.
    Função completa auto-contida.
    """
    # Funções auxiliares internas
    def get_cookies_dict(driver):
        cookies = driver.get_cookies()
        return {c['name']: c['value'] for c in cookies}

    def extrair_numero_processo_url(driver):
        """Extrai número do processo da URL ou do elemento clipboard"""
        url = driver.current_url
        # Primeiro tenta extrair da URL
        m = re.search(r'processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', url)
        if m:
            return m.group(1)
        
        # Se não encontrar na URL, tenta extrair do elemento clipboard do PJE
        try:
            xpath_clipboard = "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o número do processo')]"
            elemento_clipboard = driver.find_element(By.XPATH, xpath_clipboard)
            aria_label = elemento_clipboard.get_attribute("aria-label")
            if aria_label:
                match_clipboard = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                if match_clipboard:
                    return match_clipboard.group(1)
        except:
            pass
        
        return None

    def extrair_trt_host(driver):
        url = driver.current_url
        parsed = urlparse(url)
        return parsed.netloc

    def obter_id_processo_via_api(numero_processo, sess, trt_host):
        """Replica a função obterIdProcessoViaApi do gigs-plugin.js"""
        url = f'https://{trt_host}/pje-comum-api/api/agrupamentotarefas/processos?numero={numero_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('idProcesso')
        except Exception as e:
            if debug:
                print(f'[extrair.py] Erro ao obter ID via API: {e}')
        return None

    def obter_dados_processo_via_api(id_processo, sess, trt_host):
        """Replica a função obterDadosProcessoViaApi do gigs-plugin.js"""
        url = f'https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                return resp.json()
        except Exception as e:
            if debug:
                print(f'[extrair.py] Erro ao obter dados via API: {e}')
        return None
    
    cookies = get_cookies_dict(driver)
    numero_processo = extrair_numero_processo_url(driver)
    trt_host = extrair_trt_host(driver)
    
    sess = requests.Session()
    for k, v in cookies.items():
        sess.cookies.set(k, v)
    sess.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Grau-Instancia": "1"  # Adiciona header usado pela extensão
    })
    
    if not numero_processo:
        if debug:
            print('[extrair.py] Não foi possível extrair o número do processo.')
        return {}

    # 1. Obter ID do processo usando o número (como na extensão MaisPje)
    id_processo = obter_id_processo_via_api(numero_processo, sess, trt_host)
    if not id_processo:
        if debug:
            print('[extrair.py] Não foi possível obter o ID do processo via API.')
        return {}

    # 2. Obter dados completos do processo usando o ID
    dados_processo = obter_dados_processo_via_api(id_processo, sess, trt_host)
    if not dados_processo:
        if debug:
            print('[extrair.py] Não foi possível obter dados do processo via API.')
        return {}
    
    processo_memoria = {
        "numero": [dados_processo.get("numero", numero_processo)], 
        "id": id_processo, 
        "autor": [], 
        "reu": [], 
        "terceiro": [],
        "divida": {}, 
        "justicaGratuita": [], 
        "transito": "", 
        "custas": "", 
        "dtAutuacao": "",
        "classeJudicial": dados_processo.get("classeJudicial", {}),
        "labelFaseProcessual": dados_processo.get("labelFaseProcessual", ""),
        "orgaoJuizo": dados_processo.get("orgaoJuizo", {}),
        "dataUltimo": dados_processo.get("dataUltimo", "")
    }

    # Extrai data de autuação dos dados principais
    dt = dados_processo.get("autuadoEm")
    if dt:
        from datetime import datetime
        try:
            dtobj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
        except:
            processo_memoria["dtAutuacao"] = dt
    
    # 2. Partes (formato limpo)
    def criar_pessoa_limpa(parte):
        nome = parte.get("nome", "").strip()
        doc = re.sub(r'[^\d]', '', parte.get("documento", ""))
        
        pessoa = {"nome": nome, "cpfcnpj": doc}
        
        reps = parte.get("representantes", [])
        if reps:
            adv = reps[0]
            pessoa["advogado"] = {
                "nome": adv.get("nome", "").strip(),
                "cpf": re.sub(r'[^\d]', '', adv.get("documento", "")),
                "oab": adv.get("numeroOab", "")
            }
        return pessoa
          # 2. Partes usando API separada (como na extensão)
    try:
        url_partes = f"https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}/partes"
        resp = sess.get(url_partes, timeout=10)
        if resp.ok:
            j = resp.json()
            for parte in j.get("ATIVO", []):
                processo_memoria["autor"].append(criar_pessoa_limpa(parte))
            for parte in j.get("PASSIVO", []):
                processo_memoria["reu"].append(criar_pessoa_limpa(parte))
            for parte in j.get("TERCEIROS", []):
                processo_memoria["terceiro"].append({"nome": parte.get("nome", "").strip()})
    except Exception as e:
        if debug:
            print('[extrair.py] Erro ao buscar partes:', e)
    
    # 3. Divida
    try:
        url_divida = f"https://{trt_host}/pje-comum-api/api/calculos/processo?pagina=1&tamanhoPagina=10&ordenacaoCrescente=true&idProcesso={id_processo}&mostrarCalculosHomologados=true&incluirCalculosHomologados=true"
        resp = sess.get(url_divida, timeout=10)
        if resp.ok:
            j = resp.json()
            if j and j.get("resultado"):
                ultimo = j["resultado"][-1]
                processo_memoria["divida"] = {
                    "valor": ultimo.get("total", 0),
                    "data": ultimo.get("dataLiquidacao", "")
                }
    except Exception as e:
        if debug:
            print('[extrair.py] Erro ao buscar divida:', e)
      # Salva JSON
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(processo_memoria, f, ensure_ascii=False, indent=2)
    return processo_memoria
