"""Fluxos API de Prazo (GIGS sem prazo / XS)"""

from typing import List


def gerar_script_gigs_sem_prazo(tamanho_pagina: int = 100) -> str:
    """Retorna script JS para listar GIGS sem prazo (sem prazo + xs) via API REST."""
    return f"""
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
const params = 'filtrarAtividadesSemPrazo=true'
             + '&filtrarAtividadesSemPrazoConcluidas=false'
             + '&ordenacaoCrescente=true'
             + '&filtrarPorDestinatario=false'
             + '&filtrarPorLocalizacao=false';
const headers = {{
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-XSRF-TOKEN': xsrf
}};

(async () => {{
    const fetchPage = async (pagina) => {{
        const url = `${{base}}/pje-gigs-api/api/relatorioatividades/?${{params}}&pagina=${{pagina}}&tamanhoPagina={tamanho_pagina}`;
        const r = await fetch(url, {{ credentials: 'include', headers }});
        if (!r.ok) return {{ erro: r.status, url, resultado: [] }};
        return r.json();
    }};

    try {{
        const p1 = await fetchPage(1);
        if (p1.erro) {{
            callback({{ erro: p1.erro, url: p1.url, xsrfLen: xsrf.length, resultado: [] }});
            return;
        }}

        let all = [...(p1.resultado || [])];
        const totalPages = p1.qtdPaginas || 1;

        if (totalPages > 1) {{
            const rest = await Promise.all(
                Array.from({{ length: totalPages - 1 }}, (_, i) => fetchPage(i + 2))
            );
            rest.forEach(p => (all = all.concat(p.resultado || [])));
        }}

        const xs = all.filter(item => {{
            const tipo = (item.tipoAtividade && (item.tipoAtividade.descricao || item.tipoAtividade.nome)) || '';
            const observacao = (item.observacao || '').toString();
            const texto = `${{tipo}} ${{observacao}}`.toLowerCase();
            return texto.includes('xs');
        }});

        callback({{ totalRegistros: p1.totalRegistros, qtdPaginas: totalPages, resultado: xs }});
    }} catch (error) {{
        callback({{ erro: error.message || String(error), resultado: [] }});
    }}
}})();
"""


def testar_gigs_sem_prazo(driver, tamanho_pagina: int = 100) -> List[dict]:
    """Executa o script JS no driver e retorna as atividades XS (sem prazo)."""
    script = gerar_script_gigs_sem_prazo(tamanho_pagina=tamanho_pagina)

    driver.set_script_timeout(60)
    try:
        response = driver.execute_async_script(script)
    finally:
        try:
            driver.set_script_timeout(30)
        except Exception:
            pass

    if not response or response.get('erro'):
        erro = (response or {}).get('erro', 'sem_resposta')
        raise RuntimeError(f"Fluxo API XS sem prazo falhou: {erro}")

    return response.get('resultado', [])


def processar_gigs_sem_prazo_p2b(driver, tamanho_pagina: int = 100, max_processos: int = 0):
    """Executa o fluxo P2B usando API GIGS sem prazo + 'XS'.

    Substitui apenas a etapa de navegação/listagem onde D em x.py chamava fluxo_prazo.
    Ações por processo continuam sendo executadas via fluxo_pz (mesma lógica de processos).
    """
    from .p2b_fluxo import fluxo_pz
    from Prazo.p2b_core import carregar_progresso_p2b, marcar_processo_executado_p2b, processo_ja_executado_p2b
    from Fix.core import wait_for_page_load
    import logging

    logger = logging.getLogger(__name__)

    progresso = carregar_progresso_p2b()
    atividades = testar_gigs_sem_prazo(driver, tamanho_pagina=tamanho_pagina)
    total_encontrado = len(atividades)
    if total_encontrado == 0:
        logger.info('[PRAZO_API] Nenhuma atividade XS sem prazo encontrada')
        return {'sucesso': True, 'total': 0, 'processados': 0}

    logger.info(f'[PRAZO_API] GIGS sem prazo XS encontrados: {total_encontrado}')

    main_handle = driver.current_window_handle
    processados = 0
    falhas = []

    for idx, item in enumerate(atividades, start=1):
        if max_processos and idx > max_processos:
            break

        processo_obj = item.get('processo') or {}
        id_processo = (processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id'))
        numero = (processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero'))

        # 1) Priorizar progressão por número do processo (CNJ) e fallback para id interno
        chave_progresso = numero or str(id_processo)

        if chave_progresso and processo_ja_executado_p2b(chave_progresso, progresso):
            logger.info(f'[PRAZO_API] Processo {chave_progresso} já executado, pulando ({idx}/{total_encontrado})')
            continue

        if not id_processo:
            logger.warning(f'[PRAZO_API] Item {idx} sem id_processo, pulando (numero_recuperado={numero})')
            continue

        detalhe_url = f'https://pje.trt2.jus.br/pjekz/processo/{id_processo}/detalhe/'
        logger.info(f'[PRAZO_API] [{idx}/{total_encontrado}] Abrindo processo id={id_processo} numero={numero}')

        before_handles = set(driver.window_handles)
        driver.execute_script("window.open(arguments[0], '_blank');", detalhe_url)
        new_handles = [h for h in driver.window_handles if h not in before_handles]
        if not new_handles:
            logger.error(f'[PRAZO_API] Falha ao abrir nova aba para {target}')
            falhas.append({'id': id_processo, 'numero': numero, 'erro': 'aba_nao_aberta'})
            continue

        driver.switch_to.window(new_handles[-1])

        try:
            wait_for_page_load(driver, timeout=20)
            fluxo_pz(driver)
            processados += 1

            # 2) Marcar progresso P2B somente se executado com sucesso
            if chave_progresso:
                marcar_processo_executado_p2b(chave_progresso, progresso)

            logger.info(f'[PRAZO_API] Processo {numero} processado com sucesso')
        except Exception as e:
            logger.error(f'[PRAZO_API] Erro ao processar processo {numero}: {e}')
            falhas.append({'numero': numero, 'erro': str(e)})
        finally:
            try:
                driver.close()
            except Exception:
                pass
            driver.switch_to.window(main_handle)

    return {
        'sucesso': len(falhas) == 0,
        'total': total_encontrado,
        'processados': processados,
        'falhas': falhas,
    }
