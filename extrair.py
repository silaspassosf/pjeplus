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
    Extrai dados do processo via API do PJe (TRT2), formato limpo conforme especificação.
    Função completa auto-contida.
    """
    # Funções auxiliares internas
    def get_cookies_dict(driver):
        cookies = driver.get_cookies()
        return {c['name']: c['value'] for c in cookies}

    def extrair_id_processo_url(driver):
        url = driver.current_url
        m = re.search(r'/processo/(\d+)', url)
        return m.group(1) if m else None

    def extrair_trt_host(driver):
        url = driver.current_url
        parsed = urlparse(url)
        return parsed.netloc
    
    cookies = get_cookies_dict(driver)
    id_processo = extrair_id_processo_url(driver)
    trt_host = extrair_trt_host(driver)
    sess = requests.Session()
    for k, v in cookies.items():
        sess.cookies.set(k, v)
    sess.headers.update({"Accept": "application/json, text/plain, */*"})
    
    if not id_processo:
        if debug:
            print('[extrair.py] Não foi possível extrair o id do processo da URL.')
        return {}
    
    url_base = f"https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}"
    url_partes = f"https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}/partes"
    
    processo_memoria = {
        "numero": [], "id": id_processo, "autor": [], "reu": [], "terceiro": [],
        "divida": {}, "justicaGratuita": [], "transito": "", "custas": "", "dtAutuacao": ""
    }
    
    # 1. Dados principais
    try:
        resp = sess.get(url_base, timeout=10)
        if resp.ok:
            j = resp.json()
            numero = j.get("numero", "") or j.get("numeroProcesso", "")
            if numero:
                processo_memoria["numero"] = [numero]
            dt = j.get("autuadoEm")
            if dt:
                from datetime import datetime
                try:
                    dtobj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                    processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
                except:
                    processo_memoria["dtAutuacao"] = dt
    except Exception as e:
        if debug:
            print('[extrair.py] Erro ao buscar dados principais:', e)
    
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
        
    try:
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
