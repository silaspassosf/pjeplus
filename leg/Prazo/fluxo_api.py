"""Fluxos API de Prazo (GIGS xs1 via API)."""

from typing import List


def gerar_script_gigs_xs1(tamanho_pagina: int = 100) -> str:
    """Retorna script JS para listar GIGS com observação xs1 via API REST."""
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
const params = 'filtrarAtividadesSemPrazo=false'
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

        const xs1 = all.filter(item => {{
            const tipo = (item.tipoAtividade && (item.tipoAtividade.descricao || item.tipoAtividade.nome)) || '';
            const observacao = (item.observacao || '').toString();
            const texto = `${{tipo}} ${{observacao}}`.toLowerCase();
            return texto.includes('xs1');
        }});

        callback({{ totalRegistros: p1.totalRegistros, qtdPaginas: totalPages, resultado: xs1 }});
    }} catch (error) {{
        callback({{ erro: error.message || String(error), resultado: [] }});
    }}
}})();
"""


def testar_gigs_xs1(driver, tamanho_pagina: int = 100) -> List[dict]:
    """Executa o script JS no driver e retorna as atividades XS1 via API."""
    script = gerar_script_gigs_xs1(tamanho_pagina=tamanho_pagina)

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
        raise RuntimeError(f"Fluxo API XS1 falhou: {erro}")

    return response.get('resultado', [])


def gerar_script_gigs_sem_prazo(tamanho_pagina: int = 100) -> str:
    """Compatibilidade: wrapper para gerar_script_gigs_xs1."""
    return gerar_script_gigs_xs1(tamanho_pagina=tamanho_pagina)


def testar_gigs_sem_prazo(driver, tamanho_pagina: int = 100) -> List[dict]:
    """Compatibilidade: wrapper para testar_gigs_xs1."""
    return testar_gigs_xs1(driver, tamanho_pagina=tamanho_pagina)


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
    atividades = testar_gigs_xs1(driver, tamanho_pagina=tamanho_pagina)
    total_encontrado = len(atividades)
    if total_encontrado == 0:
        logger.info('[PRAZO_API] Nenhuma atividade XS1 encontrada')
        return {'sucesso': True, 'total': 0, 'processados': 0}

    logger.info(f'[PRAZO_API] GIGS XS1 encontrados: {total_encontrado}')

    # Registrar os processos que serão executados
    processos_para_executar = []
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

        processos_para_executar.append((id_processo, numero, chave_progresso))

    # Registrar quais processos serão executados
    logger.info(f'[PRAZO_API] Processos a serem executados: {[p[1] for p in processos_para_executar]}')

    processados = 0
    falhas = []

    # Processar cada processo individualmente na mesma aba
    for idx, (id_processo, numero, chave_progresso) in enumerate(processos_para_executar, start=1):
        try:
            # Garantir que estamos apenas na aba principal antes de começar
            abas = driver.window_handles
            if len(abas) > 1:
                # Fechar todas as abas extras, mantendo apenas a primeira
                aba_principal = abas[0]
                for aba in abas[1:]:
                    try:
                        driver.switch_to.window(aba)
                        driver.close()
                    except Exception:
                        pass
                driver.switch_to.window(aba_principal)

            detalhe_url = f'https://pje.trt2.jus.br/pjekz/processo/{id_processo}/detalhe/'
            logger.info(f'[PRAZO_API] [{idx}/{len(processos_para_executar)}] Abrindo processo id={id_processo} numero={numero}')

            # Navegar para o processo na mesma aba
            driver.get(detalhe_url)

            try:
                # Chamar o orquestrador `fluxo_pz` para extrair + aplicar regras + executar ações
                from .p2b_fluxo import fluxo_pz

                # esperar carregamento mínimo da página
                try:
                    wait_for_page_load(driver, timeout=20)
                except Exception:
                    pass

                try:
                    ok = fluxo_pz(driver)
                except Exception as e:
                    logger.error(f'[PRAZO_API] Erro ao executar fluxo_pz para processo {numero}: {e}')
                    falhas.append({'numero': numero, 'erro': str(e)})
                    ok = False

                if ok:
                    processados += 1
                    if chave_progresso:
                        marcar_processo_executado_p2b(chave_progresso, progresso)
                    logger.info(f'[PRAZO_API] Processo {numero} processado com sucesso (fluxo_pz)')
                else:
                    logger.error(f'[PRAZO_API] Processo {numero} não processado pelo fluxo_pz')
                    falhas.append({'numero': numero, 'erro': 'fluxo_pz_nao_executou'})

            except Exception as e:
                logger.error(f'[PRAZO_API] Erro ao processar processo {numero}: {e}')
                falhas.append({'numero': numero, 'erro': str(e)})
                
        except Exception as e:
            logger.error(f'[PRAZO_API] Erro geral ao processar processo {numero}: {e}')
            falhas.append({'numero': numero, 'erro': str(e)})

    return {
        'sucesso': len(falhas) == 0,
        'total': total_encontrado,
        'processados': processados,
        'falhas': falhas,
    }
