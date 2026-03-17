import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_selectors - Módulo de seletores CSS e funções relacionadas para PJe automação.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

from selenium.webdriver.common.by import By

# Seletores comuns do PJe
SELECTORS_PJE = {
    'login': {
        'btn_sso_pdpj': '#btnSsoPdpj',
        'btn_certificado': '.botao-certificado-titulo',
        'campo_username': '#username',
        'campo_password': '#password',
        'btn_login': '#kc-login',
        'painel_url': 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'
    },
    'processo': {
        'numero_processo': '[id*="numeroProcesso"], [name*="numeroProcesso"]',
        'campo_busca': '#fPP\\:numeroProcesso\\:numeroSequencial',
        'btn_pesquisar': '#fPP\\:j_id',
        'tabela_resultados': '.rich-table',
        'link_processo': '.rich-table a',
        'aba_dados_basicos': '#tabDadosBasicos',
        'aba_partes': '#tabPartes',
        'aba_movimentos': '#tabMovimentos'
    },
    'atos': {
        'btn_novo_ato': '#btnNovoAto',
        'select_tipo_ato': '#tipoAto',
        'campo_texto_ato': '#textoAto',
        'btn_salvar_ato': '#btnSalvarAto',
        'btn_assinar_ato': '#btnAssinarAto'
    },
    'movimentos': {
        'btn_novo_movimento': '#btnNovoMovimento',
        'select_tipo_movimento': '#tipoMovimento',
        'campo_descricao': '#descricaoMovimento',
        'btn_salvar_movimento': '#btnSalvarMovimento'
    },
    'comunicacao': {
        'btn_nova_comunicacao': '#btnNovaComunicacao',
        'select_tipo_comunicacao': '#tipoComunicacao',
        'campo_destinatario': '#destinatario',
        'btn_enviar': '#btnEnviar'
    },
    'loading': '.loading, .spinner, #loading, .ui-blockui, .blockUI',
    'erros': '.error, .erro, .alert-danger, .ui-messages-error',
    'sucesso': '.success, .sucesso, .alert-success, .ui-messages-info'
}

def obter_seletor_pje(categoria, chave):
    """Obtém seletor PJe por categoria e chave"""
    try:
        return SELECTORS_PJE[categoria][chave]
    except KeyError:
        logger.warning(f"Seletor não encontrado: {categoria}.{chave}")
        return ""

def buscar_seletor_robusto(driver, seletores, timeout=10):
    """Busca o primeiro seletor disponível de uma lista"""
    from .extracao import esperar_elemento

    for seletor in seletores:
        try:
            elemento = esperar_elemento(driver, seletor, timeout=2)
            if elemento:
                return elemento, seletor
        except Exception:
            continue

    return None, None

def gerar_seletor_dinamico(tipo_elemento, atributos=None):
    """Gera seletor CSS dinâmico baseado em atributos"""
    if not atributos:
        return tipo_elemento

    seletores = [tipo_elemento]

    for attr, valor in atributos.items():
        if attr == 'id':
            seletores.append(f"#{valor}")
        elif attr == 'class':
            # Para múltiplas classes
            if isinstance(valor, list):
                seletores.append(f".{'.'.join(valor)}")
            else:
                seletores.append(f".{valor}")
        elif attr == 'name':
            seletores.append(f"[name='{valor}']")
        elif attr == 'type':
            seletores.append(f"[type='{valor}']")
        elif attr == 'placeholder':
            seletores.append(f"[placeholder*='{valor}']")
        elif attr == 'title':
            seletores.append(f"[title*='{valor}']")
        elif attr == 'text':
            # Para texto, usaremos XPath
            seletores.append(f"//*[contains(text(), '{valor}')]")

    return ', '.join(seletores)

def detectar_seletor_elemento(driver, elemento):
    """Detecta possíveis seletores para um elemento"""
    try:
        seletores = []

        # ID
        elem_id = elemento.get_attribute('id')
        if elem_id:
            seletores.append(f"#{elem_id}")

        # Name
        elem_name = elemento.get_attribute('name')
        if elem_name:
            seletores.append(f"[name='{elem_name}']")

        # Classes
        elem_class = elemento.get_attribute('class')
        if elem_class:
            classes = elem_class.split()
            if classes:
                seletores.append(f".{classes[0]}")
                if len(classes) > 1:
                    seletores.append(f".{'.'.join(classes)}")

        # Tipo
        elem_type = elemento.get_attribute('type')
        if elem_type:
            seletores.append(f"[type='{elem_type}']")

        # Placeholder
        placeholder = elemento.get_attribute('placeholder')
        if placeholder:
            seletores.append(f"[placeholder*='{placeholder[:20]}']")

        # Tag + texto parcial
        texto = elemento.text.strip()
        if texto and len(texto) > 3:
            tag = elemento.tag_name
            seletores.append(f"{tag}[contains(text(), '{texto[:20]}')]")

        return seletores

    except Exception as e:
        logger.error(f"Erro ao detectar seletor do elemento: {e}")
        return []

def validar_seletor(driver, seletor, esperado_multiplos=False):
    """Valida se um seletor encontra elementos na página"""
    try:
        elementos = driver.find_elements(By.CSS_SELECTOR, seletor)

        if esperado_multiplos:
            return len(elementos) > 0, len(elementos)
        else:
            return len(elementos) == 1, len(elementos)

    except Exception as e:
        logger.error(f"Erro ao validar seletor {seletor}: {e}")
        return False, 0

def encontrar_seletor_estavel(driver, seletores_lista, timeout=10):
    """Encontra o seletor mais estável de uma lista"""
    resultados = {}

    for seletor in seletores_lista:
        try:
            inicio = time.time()
            elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
            tempo = time.time() - inicio

            if elementos:
                resultados[seletor] = {
                    'count': len(elementos),
                    'time': tempo,
                    'stable': len(elementos) == 1  # Considera estável se encontra exatamente 1
                }
        except Exception:
            continue

    # Retorna o seletor mais rápido que encontrou exatamente 1 elemento
    candidatos = [s for s, r in resultados.items() if r['stable']]
    if candidatos:
        return min(candidatos, key=lambda s: resultados[s]['time'])

    # Fallback: retorna o que encontrou mais elementos
    if resultados:
        return max(resultados.keys(), key=lambda s: resultados[s]['count'])

    return None

def criar_seletor_fallback(seletor_principal, seletores_backup):
    """Cria estratégia de fallback para seletores"""
    return {
        'principal': seletor_principal,
        'backup': seletores_backup,
        'usar_primeiro_disponivel': True
    }

def aplicar_estrategia_seletor(driver, estrategia, timeout=10):
    """Aplica estratégia de seletor com fallbacks"""
    try:
        # Tentar seletor principal
        elemento, seletor_usado = buscar_seletor_robusto(
            driver, [estrategia['principal']], timeout=timeout
        )

        if elemento:
            return elemento, seletor_usado

        # Tentar backups se configurado
        if estrategia.get('usar_primeiro_disponivel', False) and estrategia.get('backup'):
            elemento, seletor_usado = buscar_seletor_robusto(
                driver, estrategia['backup'], timeout=timeout
            )
            if elemento:
                logger.info(f"Usando seletor backup: {seletor_usado}")
                return elemento, seletor_usado

        return None, None

    except Exception as e:
        logger.error(f"Erro ao aplicar estratégia de seletor: {e}")
        return None, None