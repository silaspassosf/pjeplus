import json
import os
from Fix.log import logger

_CACHE_PATH = os.path.join(os.path.dirname(__file__), '..', 'cache', 'assinatura_cookies.json')
_COOKIES_ALVO = ('ASSINADOR_PJE', 'MO')


def _ler_cache():
    try:
        if os.path.exists(_CACHE_PATH):
            with open(_CACHE_PATH, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            logger.info(f"ASSINATURA_COOKIES | Cache lido: {list(dados.keys()) if dados else '(vazio)'}")
            return dados
    except Exception as e:
        logger.info(f"ASSINATURA_COOKIES | Falha ao ler cache: {e}")
    return {}


def _salvar_cache(dados):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(_CACHE_PATH)), exist_ok=True)
        with open(_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        logger.info(f"ASSINATURA_COOKIES | Cache gravado em: {os.path.abspath(_CACHE_PATH)}")
    except Exception as e:
        logger.info(f"ASSINATURA_COOKIES | Falha ao salvar cache: {e}")


def cache_tem_cookies():
    """Retorna True se o cache possui cookies de assinatura registrados."""
    cache = {}
    try:
        if os.path.exists(_CACHE_PATH):
            with open(_CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
    except Exception:
        pass
    resultado = bool(cache)
    logger.info(f"ASSINATURA_COOKIES | cache_tem_cookies={resultado} chaves={list(cache.keys())}")
    return resultado


def capturar_apos_assinatura(driver):
    """Lê ASSINADOR_PJE e MO do driver e persiste em cache. Chamar após snackbar de sucesso."""
    try:
        todos = {c['name']: c for c in driver.get_cookies()}
        logger.info(f"ASSINATURA_COOKIES | Todos os cookies presentes no driver: {sorted(todos.keys())}")
        encontrados = {k: todos[k] for k in _COOKIES_ALVO if k in todos}
        if not encontrados:
            logger.info(f"ASSINATURA_COOKIES | Cookies de metodo nao encontrados apos assinatura. Alvo={_COOKIES_ALVO}")
            return
        cache = {k: {'value': v['value'], 'domain': v.get('domain', ''), 'path': v.get('path', '/')}
                 for k, v in encontrados.items()}
        logger.info(f"ASSINATURA_COOKIES | Capturando cookies para persistencia: {list(cache.keys())}")
        for nome, dados in cache.items():
            logger.info(f"ASSINATURA_COOKIES |   {nome}: domain={dados['domain']} path={dados['path']} value_len={len(dados['value'])}")
        _salvar_cache(cache)
        logger.info(f"ASSINATURA_COOKIES | Capturados e salvos com sucesso: {list(cache.keys())}")
    except Exception as e:
        logger.info(f"ASSINATURA_COOKIES | Erro ao capturar: {e}")


def reinjetar_antes_assinatura(driver):
    """Lê cache e reinjecta ASSINADOR_PJE e MO no driver se ausentes. Chamar antes do clique em Assinar."""
    logger.info("ASSINATURA_COOKIES | reinjetar_antes_assinatura chamado")
    cache = _ler_cache()
    if not cache:
        logger.info("ASSINATURA_COOKIES | Cache vazio — nenhum cookie para reinjetar (1a assinatura esperada)")
        return
    try:
        presentes = {c['name'] for c in driver.get_cookies()}
        logger.info(f"ASSINATURA_COOKIES | Cookies presentes no driver agora: {sorted(presentes)}")
        ja_presentes = [n for n in cache if n in presentes]
        ausentes = [n for n in cache if n not in presentes]
        if ja_presentes:
            logger.info(f"ASSINATURA_COOKIES | Ja presentes (nao reinjetar): {ja_presentes}")
        logger.info(f"ASSINATURA_COOKIES | Ausentes a reinjetar: {ausentes}")
        reinjetados = []
        for nome, dados in cache.items():
            if nome not in presentes:
                dominio = dados.get('domain') or driver.execute_script("return document.domain")
                driver.add_cookie({
                    'name': nome,
                    'value': dados['value'],
                    'domain': dominio,
                    'path': dados.get('path', '/'),
                })
                reinjetados.append(nome)
                logger.info(f"ASSINATURA_COOKIES |   Reinjetado {nome}: domain={dominio} value_len={len(dados['value'])}")
        if reinjetados:
            logger.info(f"ASSINATURA_COOKIES | Reinjercao concluida: {reinjetados}")
        else:
            logger.info("ASSINATURA_COOKIES | Todos os cookies ja estavam presentes — sem necessidade de reinjercao")
    except Exception as e:
        logger.info(f"ASSINATURA_COOKIES | Erro ao reinjetar: {e}")
