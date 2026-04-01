import json
import time

from Fix.core import wait_for_page_load, esperar_elemento
from Fix.log import logger

from Mandado.processamento_argos import processar_argos
from Mandado.processamento_outros import fluxo_mandados_outros


def obter_mandados_devolvidos(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Retorna a lista de mandados devolvidos via endpoint interno."""
    url = (
        'https://pje.trt2.jus.br/pje-comum-api/api/escaninhos/documentosinternos'
        f'?mandadosDevolvidos=true&pagina={pagina}&tamanhoPagina={tamanho_pagina}'
        f'&ordenacaoCrescente={str(ordenacao_crescente).lower()}'
    )

    script = f"""
        return (async function() {{
            const url = '{url}';
            const xsrfCookie = document.cookie.split(';').map(c => c.trim())
                .find(c => c.toLowerCase().startsWith('xsrf-token='));
            if (!xsrfCookie) {{ return {{ status: 0, error: 'XSRF_NOT_FOUND' }}; }}
            const xsrf = xsrfCookie.split('=')[1];

            const response = await fetch(url, {{
                method: 'GET',
                credentials: 'include',
                headers: {{
                    'Accept': 'application/json',
                    'X-XSRF-TOKEN': xsrf
                }}
            }});

            const text = await response.text();
            return {{ status: response.status, body: text }};
        }})();
    """

    resultado = driver.execute_script(script)
    status = resultado.get('status')

    if status != 200:
        raise RuntimeError(f"[MANDADOS_API] Erro HTTP: {status}, payload: {resultado.get('body')}")

    try:
        data = json.loads(resultado.get('body', '{}'))
    except Exception as e:
        raise RuntimeError(f"[MANDADOS_API] Falha parse JSON: {e}")

    if isinstance(data, dict):
        processos = data.get('resultado') or data.get('dados') or []
    elif isinstance(data, list):
        processos = data
    else:
        processos = []

    return processos


def processar_mandado_detalhe(driver, numero_processo=None, id_processo=None):
    """Abre /processo/{id}/detalhe/, processa mandado e fecha aba."""
    if id_processo:
        detalhe_url = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/detalhe/"
    elif numero_processo:
        detalhe_url = f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe/"
    else:
        raise ValueError("id_processo ou numero_processo deve ser fornecido")

    main_handle = driver.current_window_handle
    driver.execute_script("window.open(arguments[0], '_blank');", detalhe_url)
    time.sleep(0.5)

    new_handles = [h for h in driver.window_handles if h != main_handle]
    if not new_handles:
        logger.error(f"[MANDADOS_API] Não abriu a aba de detalhe para {id_processo or numero_processo}")
        return False

    driver.switch_to.window(new_handles[0])

    try:
        wait_for_page_load(driver, timeout=15)
        cabecalho = esperar_elemento(driver, '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title', timeout=15)
        if not cabecalho:
            logger.error(f"[MANDADOS_API] Cabeçalho não encontrado para {id_processo or numero_processo}")
            return False

        texto_doc = cabecalho.text or ''
        texto_lower = texto_doc.lower()

        if any(term in texto_lower for term in ['pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa', 'certidao de devolucao', 'certidão de devolução']):
            logger.info(f"[MANDADOS_API] {id_processo or numero_processo} -> Argos")
            return processar_argos(driver, log=True)

        if any(term in texto_lower for term in ['oficial de justica', 'certidao de oficial', 'certidão de oficial', 'oficial de justiça']):
            logger.info(f"[MANDADOS_API] {id_processo or numero_processo} -> Outros")
            fluxo_mandados_outros(driver, log=False)
            return True

        logger.warning(f"[MANDADOS_API] Tipo não identificado para {id_processo or numero_processo}: {texto_doc[:60]}")
        return False
    except Exception as e:
        logger.error(f"[MANDADOS_API] Erro ao processar {id_processo or numero_processo}: {e}")
        return False
    finally:
        try:
            driver.close()
        except Exception:
            pass
        driver.switch_to.window(main_handle)


def processar_mandados_devolvidos_api(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Fluxo completo: consulta API + itera mandados + abre/processa/fecha cada detalhe."""
    mandados = obter_mandados_devolvidos(driver, pagina=pagina, tamanho_pagina=tamanho_pagina, ordenacao_crescente=ordenacao_crescente)

    if not mandados:
        logger.info('[MANDADOS_API] Nenhum mandado devolvido encontrado')
        return False

    sucesso_total = True

    for idx, item in enumerate(mandados, start=1):
        processo_obj = item.get('processo') or {}
        id_processo = processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id')
        numero = processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero')

        if not id_processo and not numero:
            logger.warning(f"[MANDADOS_API] Item {idx} sem ids, pulando")
            sucesso_total = False
            continue

        logger.info(f"[MANDADOS_API] Item {idx}: idProcesso={id_processo} numeroProcesso={numero}")

        if not processar_mandado_detalhe(driver, numero_processo=numero, id_processo=id_processo):
            logger.error(f"[MANDADOS_API] Falha no processamento do item {idx}: {id_processo or numero}")
            sucesso_total = False

    return sucesso_total


def _gigs_sem_prazo_via_js(driver, tamanho_pagina: int = 100) -> list:
    """Busca GIGS sem prazo (XS) via execute_async_script (API REST)."""
    JS = f'''
const callback = arguments[0];

const rawCookie = document.cookie.split(';')
    .map(c => c.trim())
    .find(c => c.toLowerCase().startsWith('xsrf-token='));
const xsrf = rawCookie ? rawCookie.split('=').slice(1).join('=') : null;

if (!xsrf) {{
    callback({{ erro: 'XSRF_NOT_FOUND', href: location.href, cookieCount: document.cookie.split(';').filter(c => c.trim()).length, resultado: [] }});
    return;
}}

const base = location.origin;
const params = 'filtrarAtividadesSemPrazo=true&filtrarAtividadesSemPrazoConcluidas=false&ordenacaoCrescente=true'
             + '&filtrarPorDestinatario=false&filtrarPorLocalizacao=false';
const hdrs = {{
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-XSRF-TOKEN': xsrf
}};

(async () => {{
    const getPage = async (pagina) => {{
        const url = `${{base}}/pje-gigs-api/api/relatorioatividades/?${{params}}&pagina=${{pagina}}&tamanhoPagina={tamanho_pagina}`;
        const r = await fetch(url, {{ credentials: 'include', headers: hdrs }});
        if (!r.ok) return {{ erro: r.status, url: url, resultado: [] }};
        return r.json();
    }};
    try {{
        const p1 = await getPage(1);
        if (p1.erro) {{
            callback({{ erro: p1.erro, url: p1.url, xsrfLen: xsrf.length, resultado: [] }});
            return;
        }}
        let todos = [...(p1.resultado || [])];
        const total = p1.qtdPaginas || 1;
        if (total > 1) {{
            const rest = await Promise.all(
                Array.from({{ length: total - 1 }}, (_, i) => getPage(i + 2))
            );
            rest.forEach(p => todos.push(...(p.resultado || [])));
        }}
        callback({{ qtdPaginas: total, totalRegistros: p1.totalRegistros, resultado: todos }});
    }} catch (e) {{
        callback({{ erro: e.message, resultado: [] }});
    }}
}})();
'''

    try:
        driver.set_script_timeout(60)
        resultado = driver.execute_async_script(JS)
    finally:
        try:
            driver.set_script_timeout(30)
        except Exception:
            pass

    if not resultado or resultado.get('erro'):
        erro = (resultado or {}).get('erro', 'sem_resposta')
        logger.error(f"[MANDADOS_API] falha GIGS sem prazo: {erro}")
        return []

    dados = resultado.get('resultado', [])

    # Filtrar somente GIGS com descricao xs (se aplica)
    filtrados = []
    for item in dados:
        tipo = (item.get('tipoAtividade') or {}).get('descricao', '') or (item.get('tipoAtividade') or {}).get('nome', '')
        if isinstance(tipo, str) and 'xs' in tipo.lower():
            filtrados.append(item)

    logger.info(f"[MANDADOS_API] GIGS sem prazo bruto {len(dados)}, filtrado xs {len(filtrados)}")
    return filtrados


def testar_api_gigs_sem_prazo(driver, tamanho_pagina: int = 100) -> list:
    """Teste local rápido do endpoint de GIGS sem prazo (XS)."""
    resultado = _gigs_sem_prazo_via_js(driver, tamanho_pagina=tamanho_pagina)
    logger.info(f"[MANDADOS_API] total capturado: {len(resultado)}")
    if resultado:
        logger.info(f"[MANDADOS_API] exemplo: {resultado[0]}")
    return resultado
