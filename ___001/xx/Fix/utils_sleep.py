import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_sleep - Módulo de funções de espera e sleep para PJe automação.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

import random
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def sleep_random(min_seg=0.5, max_seg=2.0):
    """Sleep aleatório entre min_seg e max_seg segundos"""
    tempo = random.uniform(min_seg, max_seg)
    time.sleep(tempo)
    return tempo

def sleep_fixed(segundos):
    """Sleep fixo por N segundos"""
    time.sleep(segundos)
    return segundos

def sleep_progressivo(inicio=0.5, fim=3.0, passos=5):
    """Sleep progressivo aumentando gradualmente"""
    intervalo = (fim - inicio) / (passos - 1) if passos > 1 else 0

    for i in range(passos):
        tempo = inicio + (intervalo * i)
        time.sleep(tempo)
        yield tempo

def aguardar_url_mudar(driver, url_atual, timeout=30):
    """Aguarda até que a URL mude da atual"""
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            if driver.current_url != url_atual:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def aguardar_elemento_sumir(driver, seletor, timeout=10):
    """Aguarda até que um elemento suma da página"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, seletor))
        )
        return True
    except Exception:
        return False

def aguardar_texto_mudar(driver, seletor, texto_atual, timeout=10):
    """Aguarda até que o texto de um elemento mude"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.find_element(By.CSS_SELECTOR, seletor).text != texto_atual
        )
        return True
    except Exception:
        return False

def aguardar_loading_sumir(driver, seletor_loading='.loading, .spinner, #loading', timeout=30):
    """Aguarda até que indicadores de loading sumam"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, seletor_loading))
        )
        return True
    except Exception:
        return False

def sleep_condicional(condicao_func, timeout=30, intervalo=0.5):
    """Sleep condicional até que uma condição seja atendida"""
    inicio = time.time()
    while time.time() - inicio < timeout:
        if condicao_func():
            return True
        time.sleep(intervalo)
    return False

def aguardar_pagina_carregar(driver, timeout=30):
    """Aguarda até que a página esteja totalmente carregada"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        return True
    except Exception:
        return False

def sleep_com_logging(segundos, mensagem="Aguardando"):
    """Sleep com logging do progresso"""
    logger.info(f"{mensagem}: {segundos}s")
    tempo_inicio = time.time()

    while time.time() - tempo_inicio < segundos:
        restante = segundos - (time.time() - tempo_inicio)
        if restante > 1:
            time.sleep(1)
        else:
            time.sleep(restante)

    logger.info(f"{mensagem}: concluído")

def aguardar_multiplas_condicoes(driver, condicoes, timeout=30, modo='any'):
    """
    Aguarda múltiplas condições
    modo: 'any' = qualquer uma, 'all' = todas
    """
    inicio = time.time()

    while time.time() - inicio < timeout:
        resultados = []
        for condicao in condicoes:
            try:
                if callable(condicao):
                    resultados.append(condicao())
                else:
                    # Assumir que é um seletor CSS
                    elementos = driver.find_elements(By.CSS_SELECTOR, condicao)
                    resultados.append(len(elementos) > 0)
            except Exception:
                resultados.append(False)

        if modo == 'any' and any(resultados):
            return True
        elif modo == 'all' and all(resultados):
            return True

        time.sleep(0.5)

    return False

def sleep_adaptativo(driver, seletor_verificacao=None, max_tempo=10):
    """Sleep adaptativo baseado na velocidade de resposta da página"""
    tempos = []

    for i in range(3):
        inicio = time.time()

        if seletor_verificacao:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor_verificacao)
                _ = len(elementos)  # Forçar avaliação
            except Exception:
                pass

        fim = time.time()
        tempos.append(fim - inicio)

    tempo_medio = sum(tempos) / len(tempos)
    tempo_adaptado = min(max_tempo, tempo_medio * 2)

    time.sleep(tempo_adaptado)
    return tempo_adaptado

def sleep(ms):
    """Compatibilidade: converte milissegundos para segundos"""
    time.sleep(ms / 1000.0)

def smart_sleep(t='default', multiplier=1.0):
    """Sleep inteligente baseado na configuração global"""
    from .utils_cookies import config
    time.sleep(config.get_delay(t) * multiplier)