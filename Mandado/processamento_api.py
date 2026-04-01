import json
from pathlib import Path

from selenium.webdriver.common.by import By

from Fix.core import wait_for_page_load, safe_click_no_scroll, esperar_elemento
from Fix.log import logger
from Fix.progress import ProgressoUnificado
from Fix.utils.observer import aguardar_renderizacao_nativa

from Mandado.processamento_argos import processar_argos
from Mandado.processamento_outros import fluxo_mandados_outros


def _fechar_abas_extras(driver, handle_principal):
    """Fecha todas as abas abertas durante o processamento e retorna ao handle principal."""
    try:
        for h in list(driver.window_handles):
            if h != handle_principal:
                try:
                    driver.switch_to.window(h)
                    driver.close()
                except Exception:
                    pass
        driver.switch_to.window(handle_principal)
    except Exception:
        pass


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


def _selecionar_doc_via_timeline(driver, log=True):
    """
    Localiza e clica na primeira ocorrência relevante da timeline (mais recente).
    Usa safe_click_no_scroll (dispatchEvent) — independente de scroll.
    Retorna 'argos', 'outros' ou None se nenhum doc relevante encontrado.
    Regras espelham classificarItem() de lista.timeline.js.
    """
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    for item in itens:
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
        except Exception:
            continue

        low = (link.text or '').lower()

        if 'devolução de ordem' in low or 'devolucao de ordem' in low:
            tipo = 'argos'
        elif ('certidão de oficial' in low or 'certidao de oficial' in low
              or 'oficial de justiça' in low or 'oficial de justica' in low):
            tipo = 'outros'
        else:
            continue

        if log:
            logger.info(f"[MANDADOS_API] Timeline: primeiro doc relevante tipo={tipo} — '{(link.text or '')[:60]}'")

        if not safe_click_no_scroll(driver, link, log=log):
            logger.warning(f"[MANDADOS_API] Falha ao clicar doc timeline: '{(link.text or '')[:40]}'")
            return None

        aguardar_renderizacao_nativa(driver)
        return tipo

    return None


def processar_mandado_detalhe(driver, numero_processo=None, id_processo=None):
    """Navega para /processo/{id}/detalhe/ na aba atual, processa mandado e fecha abas extras."""
    if id_processo:
        detalhe_url = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/detalhe/"
    elif numero_processo:
        detalhe_url = f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe/"
    else:
        raise ValueError("id_processo ou numero_processo deve ser fornecido")

    handle_principal = driver.current_window_handle

    try:
        driver.get(detalhe_url)
        wait_for_page_load(driver, timeout=15)
        timeline_ok = esperar_elemento(driver, 'li.tl-item-container', timeout=15)
        if not timeline_ok:
            logger.error(f"[MANDADOS_API] Timeline nao encontrada para {id_processo or numero_processo}")
            return False

        tipo = _selecionar_doc_via_timeline(driver, log=True)

        if tipo == 'argos':
            logger.info(f"[MANDADOS_API] {id_processo or numero_processo} -> Argos (via timeline)")
            return processar_argos(driver, log=True)

        if tipo == 'outros':
            logger.info(f"[MANDADOS_API] {id_processo or numero_processo} -> Outros (via timeline)")
            fluxo_mandados_outros(driver, log=False)
            return True

        logger.info(f"[MANDADOS_API] Tipo nao mapeado para {id_processo or numero_processo} (nenhum doc relevante na timeline) — pulando")
        return 'PULAR'
    except Exception as e:
        logger.error(f"[MANDADOS_API] Erro ao processar {id_processo or numero_processo}: {e}")
        return False
    finally:
        _fechar_abas_extras(driver, handle_principal)


def processar_mandados_devolvidos_api(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Fluxo completo: consulta API + lista fila + processa individualmente com progresso."""
    mandados = obter_mandados_devolvidos(driver, pagina=pagina, tamanho_pagina=tamanho_pagina, ordenacao_crescente=ordenacao_crescente)

    if not mandados:
        logger.info('[MANDADOS_API] Nenhum mandado devolvido encontrado')
        return False

    # ── Extrair itens normalizados
    itens = []
    for item in mandados:
        processo_obj = item.get('processo') or {}
        id_p = processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id')
        num = processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero')
        if id_p or num:
            itens.append({'id': id_p, 'numero': num})

    if not itens:
        logger.info('[MANDADOS_API] Nenhum item na fila')
        return False

    # ── Listar fila completa antes de começar
    logger.info(f'[MANDADOS_API] {len(itens)} processo(s) na fila:')
    for i, it in enumerate(itens, 1):
        logger.info(f'[MANDADOS_API]   #{i}: id={it["id"]}  numero={it["numero"]}')

    # ── Sistema de progresso
    progresso = ProgressoUnificado(arquivo_progresso=Path('progresso.json'))
    progresso.registrar_modulo('MANDADO', len(itens))

    sucesso_algum = False
    falhas = []
    pulados = []

    for idx, it in enumerate(itens, 1):
        id_p = it['id']
        num = it['numero']
        label = str(num or id_p)

        logger.info(f"[MANDADOS_API] [{idx}/{len(itens)}] id={id_p} numero={num}")

        resultado = processar_mandado_detalhe(driver, numero_processo=num, id_processo=id_p)

        if resultado == 'PULAR':
            pulados.append(label)
            logger.info(f"[MANDADOS_API] #{idx} pulado (tipo nao mapeado)")
            progresso.atualizar('MANDADO', item_atual=label)
        elif resultado:
            sucesso_algum = True
            logger.info(f"[MANDADOS_API] #{idx} concluido")
            progresso.atualizar('MANDADO', item_atual=label)
        else:
            falhas.append(label)
            logger.error(f"[MANDADOS_API] #{idx} falhou: {label}")
            progresso.atualizar('MANDADO', item_atual=label, erro=True)

    progresso.completar('MANDADO', sucesso=(len(falhas) == 0))

    logger.info(f'[MANDADOS_API] Concluido — processados={len(itens)} sucesso={len(itens)-len(falhas)-len(pulados)} pulados={len(pulados)} falhas={len(falhas)}')
    if falhas:
        logger.warning(f'[MANDADOS_API] Falhas: {falhas}')

    # Falha real somente se TODOS os itens falharam (pulados não contam como falha)
    return sucesso_algum or (len(pulados) == len(itens))


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
