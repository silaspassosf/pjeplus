"""apiaud.py - lista de processos da Triagem Inicial via execute_async_script.

Padrao baseado em Peticao/api_client.py: fetch JS dentro do browser.
O browser gerencia cookies de sessao e XSRF-TOKEN automaticamente.
Nao usar requests.Session para endpoints POST protegidos por XSRF.
Execucao: py apiaud.py
"""

import json
import time
import traceback
from typing import Any, Dict, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver

URL_LISTA_TRIAGEM = 'https://pje.trt2.jus.br/pjekz/painel/global/10/lista-processos'


def _normalizar_lista(dados) -> list:
    if isinstance(dados, list):
        return dados
    if isinstance(dados, dict):
        for chave in ('resultado', 'content', 'data', 'conteudo', 'items'):
            if isinstance(dados.get(chave), list):
                return dados[chave]
    return []


def criar_driver_e_logar(driver: Optional[WebDriver] = None) -> Optional[WebDriver]:
    if driver is not None:
        return driver
    try:
        from Fix.utils import driver_pc, login_cpf
        print('[APIAUD] Criando driver e executando login')
        drv = driver_pc()
        if not drv:
            print('[APIAUD] Falha ao criar driver')
            return None
        if not login_cpf(drv):
            try:
                drv.quit()
            except Exception:
                pass
            print('[APIAUD] Login falhou')
            return None
        return drv
    except Exception as e:
        print(f'[APIAUD] Excecao ao criar/logar driver: {e}')
        traceback.print_exc()
        return None


_JS_BUSCAR_TRIAGEM = """
const tamPag   = arguments[0] || 100;
const callback = arguments[1];

var xsrfCookie = document.cookie.split(';')
    .map(function(c) { return c.trim(); })
    .find(function(c) { return c.toLowerCase().indexOf('xsrf-token=') === 0; });
var xsrf = xsrfCookie ? xsrfCookie.split('=').slice(1).join('=') : '';

function normalizar(d) {
    if (!d) return [];
    if (Array.isArray(d)) return d;
    var chaves = ['resultado', 'content', 'data', 'conteudo', 'items', 'processos'];
    for (var i = 0; i < chaves.length; i++) {
        if (Array.isArray(d[chaves[i]])) return d[chaves[i]];
    }
    return [];
}

(async function() {
    var base = location.origin;
    var url  = base + '/pje-comum-api/api/agrupamentotarefas/10/processos';
    var todos = [];
    var pg = 1;
    var LIMITE = 50;
    while (pg <= LIMITE) {
        try {
            var r = await window.fetch(url, {
                method: 'PATCH',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-XSRF-TOKEN': xsrf
                },
                body: JSON.stringify({
                    pagina: pg, tamanhoPagina: tamPag,
                    subCaixa: null, tipoAtividade: null, processos: null,
                    nomeConclusoMagistrado: null, usuarioResponsavel: null,
                    faseProcessualString: null, numeroProcesso: null,
                    juizoDigital: null
                })
            });
            if (!r.ok) {
                callback({ erro: 'HTTP_' + r.status, resultado: todos, pagina: pg });
                return;
            }
            var data = await r.json();
            var lista = normalizar(data);
            if (!lista.length) {
                callback({ resultado: todos });
                return;
            }
            todos = todos.concat(lista);
            var totalPags = data.qtdPaginas || data.totalPaginas || 1;
            if (pg >= totalPags || lista.length < tamPag) {
                callback({ resultado: todos, total: data.totalRegistros || todos.length });
                return;
            }
            pg++;
        } catch(e) {
            callback({ erro: 'ASYNC_ERR: ' + e.message, resultado: todos });
            return;
        }
    }
    callback({ resultado: todos, aviso: 'limite_paginas' });
})();
"""


def buscar_lista_triagem(driver: WebDriver) -> List[Dict[str, Any]]:
    """Busca todos os itens da fila via execute_async_script (padrao Peticao/api_client.py).

    O fetch corre dentro do contexto do browser: cookies de sessao e XSRF-TOKEN
    sao tratados automaticamente — sem depender de requests.Session.
    """
    try:
        driver.set_script_timeout(120)
        res = driver.execute_async_script(_JS_BUSCAR_TRIAGEM, 100)
    finally:
        try:
            driver.set_script_timeout(30)
        except Exception:
            pass

    if not res:
        print('[APIAUD] execute_async_script retornou None')
        return []

    if res.get('erro'):
        print(f'[APIAUD] Erro do fetch JS: {res["erro"]}')
        return []

    if res.get('aviso'):
        print(f'[APIAUD] Aviso: {res["aviso"]}')

    lista = res.get('resultado', [])
    print(f'[APIAUD] Total bruto: {len(lista)} itens')
    return lista


def _is_triagem_inicial(item: Dict) -> bool:
    """Verifica se o item esta na tarefa Triagem Inicial pelo campo tarefa do item bruto."""
    tarefa = item.get('tarefa') or ''
    if isinstance(tarefa, dict):
        tarefa = str(tarefa.get('nome') or tarefa.get('descricao') or tarefa.get('nome') or '')
    return 'triagem inicial' in str(tarefa).lower()


def _numero_cnj(item: Dict) -> str:
    """Retorna o numero CNJ completo (ex: 1000632-12.2025.5.02.0999)."""
    return str(item.get('numeroProcesso') or item.get('numero') or item.get('id') or '')


def enriquecer_processo(item: Dict) -> Optional[Dict]:
    """Classifica processo em bucket usando apenas os campos do item bruto da fila."""
    id_proc = item.get('id') or item.get('idProcesso')
    numero = _numero_cnj(item)
    if not id_proc:
        return None

    tipo = str(item.get('classeJudicial') or '').upper()
    digital = item.get('juizoDigital') is True or item.get('juizoDigital') == 'true'
    tem_aud = bool(item.get('dataProximaAudiencia'))

    bucket = 'D' if 'HTE' in tipo else ('A' if not tem_aud else ('B' if digital else 'C'))
    return {
        'numero': numero,
        'id_processo': id_proc,
        'tipo': tipo,
        'digital': digital,
        'tem_audiencia': tem_aud,
        'bucket': bucket,
    }


def executar_teste_lista_triagem(driver: Optional[WebDriver] = None):
    drv = criar_driver_e_logar(driver)
    if not drv:
        return {'sucesso': False, 'total': 0, 'processos': []}

    try:
        print(f'[APIAUD] Navegando para {URL_LISTA_TRIAGEM}')
        drv.get(URL_LISTA_TRIAGEM)
        time.sleep(2)

        itens_brutos = buscar_lista_triagem(drv)
        if not itens_brutos:
            print('[APIAUD] Lista vazia — verificar endpoint ou sessao')
            return {'sucesso': False, 'total': 0, 'processos': []}

        print(f'[APIAUD] Enriquecendo {len(itens_brutos)} itens...')
        triagem = [i for i in itens_brutos if _is_triagem_inicial(i)]
        ignorados = len(itens_brutos) - len(triagem)
        if ignorados:
            print(f'[APIAUD] {ignorados} item(ns) ignorado(s) — nao estao em Triagem Inicial')
        if not triagem:
            # se campo tarefa nao discrimina, usa todos
            print('[APIAUD] Campo tarefa nao identificou Triagem Inicial — usando todos os itens')
            triagem = itens_brutos

        processos = []
        for item in triagem:
            enriquecido = enriquecer_processo(item)
            if enriquecido:
                processos.append(enriquecido)

        buckets: Dict[str, List[str]] = {'A': [], 'B': [], 'C': [], 'D': []}
        for p in processos:
            buckets[p['bucket']].append(p['numero'])

        labels = {'B': '100% Digital com aud', 'C': 'Nao-Digital com aud', 'A': 'Sem audiencia', 'D': 'HTE'}
        for k in ('B', 'C', 'A', 'D'):
            if buckets[k]:
                print(f"{labels[k]}: {' '.join(str(n) for n in buckets[k])}")

        return {'sucesso': True, 'total': len(processos), 'processos': processos}

    except Exception as e:
        print(f'[APIAUD] Erro geral: {e}')
        traceback.print_exc()
        return None
    finally:
        if driver is None and drv:
            try:
                drv.quit()
            except Exception:
                pass


def run_apiaud(driver: Optional[WebDriver] = None):
    return executar_teste_lista_triagem(driver)


if __name__ == '__main__':
    print('[APIAUD] executando teste da lista de triagem')
    run_apiaud(None)
