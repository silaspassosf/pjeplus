import logging
logger = logging.getLogger(__name__)

import re
from typing import Optional, List, Dict, Any, Union
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from .core import carregar_progresso_pec, processo_ja_executado_pec
from .regras import determinar_acoes_por_observacao


def _indexar_todos_processos(driver: WebDriver) -> Optional[List[Dict[str, Any]]]:
    """Helper: Indexa todos os processos da lista usando seletor específico para PEC."""
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        if not linhas:
            return None

        todos_processos = []
        padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

        for idx, linha in enumerate(linhas):
            try:
                colunas = linha.find_elements(By.TAG_NAME, 'td')
                if len(colunas) < 6:
                    continue

                # Extrair número do processo da 2ª coluna
                celula_processo = colunas[1]
                numero_processo = None

                elemento_b = celula_processo.find_element(By.TAG_NAME, 'b')
                if elemento_b:
                    texto_b = elemento_b.text.strip()
                    match = padrao_proc.search(texto_b)
                    if match:
                        numero_processo = match.group(0)

                if not numero_processo:
                    continue

                # Extrair observação da 6ª coluna
                celula_observacao = colunas[5]
                observacao = ""

                try:
                    span_observacao = celula_observacao.find_element(By.CSS_SELECTOR, 'span.texto-descricao')
                    observacao = span_observacao.text.lower().strip()
                except:
                    observacao = celula_observacao.text.lower().strip()

                if not observacao:
                    continue

                todos_processos.append({
                    'numero': numero_processo,
                    'observacao': observacao,
                    'linha': linha,
                    'linha_index': idx
                })

            except Exception as e:
                logger.error(f"[INDEXAR]  Erro ao processar linha {idx + 1}: {e}")
                continue

        return todos_processos

    except Exception as e:
        logger.error(f"[INDEXAR]  Erro na indexação: {e}")
        return None


def _filtrar_por_observacao(todos_processos: List[Dict[str, Any]], filtros_observacao: List[str]) -> List[Dict[str, Any]]:
    """Helper: Filtra processos por critérios de observação."""
    logger.info("[INDEXAR] 2. Filtrando por observação...")

    processos_filtrados = []
    for processo in todos_processos:
        observacao = processo['observacao']
        passa_filtro = False

        for filtro in filtros_observacao:
            if filtro.lower() in observacao:
                passa_filtro = True
                break

        if passa_filtro:
            processos_filtrados.append(processo)

    logger.info(f"[INDEXAR]  {len(processos_filtrados)} processos passaram no filtro de observação")

    # Salvar amostra para diagnóstico se nenhum processo passou
    if len(processos_filtrados) == 0:
        _salvar_amostra_debug_rows(todos_processos)

    return processos_filtrados


def _salvar_amostra_debug_rows(processos: List[Dict[str, Any]]) -> None:
    """Helper: Salva amostra de linhas para diagnóstico quando nenhum processo passa no filtro."""
    try:
        dump_path = 'debug_rows_sample.html'
        with open(dump_path, 'w', encoding='utf-8') as f:
            f.write('<html><head><meta charset="utf-8"><title>Debug Rows Sample</title></head><body>')
            f.write(f'<h2>Found {len(processos)} raw rows - sample outerHTML:</h2>')
            for i, p in enumerate(processos[:10]):
                try:
                    linha = p.get('linha')
                    if linha:
                        outer = linha.get_attribute('outerHTML') or linha.get_attribute('innerHTML') or ''
                        f.write(f'<h3>Row {i}</h3>')
                        f.write('<div style="border:1px solid #888;padding:8px;margin:4px;">')
                        f.write(outer)
                        f.write('</div><hr/>')
                except Exception:
                    continue
            f.write('</body></html>')
    except Exception as diag_e:
        return


def _filtrar_por_progresso(processos_filtrados: List[Dict[str, Any]], progresso: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Helper: Filtra processos que já foram executados."""
    logger.info("[INDEXAR] 3. Filtrando processos já executados...")

    processos_pendentes = []
    processos_pulados = 0

    for processo in processos_filtrados:
        numero_processo = processo['numero']

        if processo_ja_executado_pec(numero_processo, progresso):
            logger.info(f"[INDEXAR] ⏭ Processo {numero_processo} já executado, pulando...")
            processos_pulados += 1
        else:
            processos_pendentes.append(processo)
            logger.info(f"[INDEXAR]  Processo {numero_processo} será processado")

    logger.info(f"[INDEXAR] {processos_pulados} processos pulados (já executados)")
    logger.info(f"[INDEXAR] {len(processos_pendentes)} processos serão processados")

    return processos_pendentes


def _filtrar_por_acoes_validas(processos_pendentes: List[Dict[str, Any]], progresso: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Helper: Filtra processos por ações válidas antes de abrir."""
    processos_para_abrir = []
    processos_pulados_sem_regra = 0

    for processo in processos_pendentes:
        numero_processo = processo['numero']
        observacao = processo['observacao']

        acoes_result = determinar_acoes_por_observacao(observacao)

        if not acoes_result:
            processos_pulados_sem_regra += 1
        else:
            acoes = acoes_result  # Lista de funções

            # Extrair nome das ações para logging
            nomes_acoes = [a.__name__ if callable(a) else str(a) for a in acoes]

            processo['acoes'] = acoes  # Armazenar LISTA de ações
            processos_para_abrir.append(processo)

    return processos_para_abrir


def _agrupar_em_buckets(processos_para_abrir: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Helper: Agrupa processos em buckets baseado na PRIMEIRA AÇÃO.
    A primeira ação já foi determinada por determinar_acoes_por_observacao."""
    buckets = {
        'sob': [],
        'carta': [],
        'comunicacoes': [],  # xs sigilo, pec cp, exclusão, citação, intimação
        'outros': [],
        'sobrestamento': [],
        'sisbajud': []
    }

    sisbajud_names = {'minuta_bloqueio', 'minuta_bloqueio_60', 'processar_ordem_sisbajud', 'processar_ordem_sisbajud_wrapper'}
    carta_names = {'carta', 'analisar_documentos_pos_carta'}
    sob_names = {'mov_aud'}  # Removido def_chip e mov_sob
    sobrestamento_names = {'def_sob', 'def_chip', 'mov_sob'}
    # Comunicações explícitas: xs sigilo, pec cp, exclusão, citação, intimação, etc.
    # 'wrapper' incluído para funções criadas via make_comunicacao_wrapper
    comunicacoes_names = {
        'pec_sigilo', 'pec_cpgeral', 'pec_excluiargos',
        'pec_bloqueio', 'pec_decisao', 'pec_editaldec', 'pec_editalidpj',
        'pec_ord', 'pec_sum', 'pec_editalaud',
        'ato_citacao', 'ato_intimacao',
        'wrapper'  # Funções criadas via make_comunicacao_wrapper
    }

    for p in processos_para_abrir:
        acoes = p.get('acoes', [])
        if not acoes:
            buckets['outros'].append(p)
            continue

        # Usar PRIMEIRA ação para classificar bucket
        primeira_acao = acoes[0]
        
        # Se primeira_acao é uma lista (múltiplas ações), verificar todas
        if isinstance(primeira_acao, list):
            nomes_acoes = [a.__name__ if callable(a) else str(a) for a in primeira_acao]
            acao_nome = nomes_acoes[0] if nomes_acoes else ''
        else:
            acao_nome = primeira_acao.__name__ if callable(primeira_acao) else str(primeira_acao)

        if acao_nome in sisbajud_names:
            buckets['sisbajud'].append(p)
        elif acao_nome in carta_names:
            buckets['carta'].append(p)
        elif acao_nome in sob_names:
            buckets['sob'].append(p)
        elif acao_nome in sobrestamento_names:
            buckets['sobrestamento'].append(p)
        elif acao_nome in comunicacoes_names:
            # Comunicações explícitas
            buckets['comunicacoes'].append(p)
        elif acao_nome.startswith('pec_'):
            # Fallback: qualquer ação pec_* não mapeada explicitamente
            buckets['comunicacoes'].append(p)
        else:
            buckets['outros'].append(p)

    # Log resumido dos buckets
    return buckets


def _executar_dry_run(buckets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """Helper: Executa dry run mostrando buckets sem processar."""
    logger.info('[INDEXAR][DRY_RUN] Dry run enabled - not opening processes. Showing bucket summary:')
    for name in ['sobrestamento', 'carta', 'comunicacoes', 'outros', 'sisbajud']:
        bucket = buckets.get(name, [])
        logger.info(f"  - {name}: {len(bucket)} processes")
        if bucket:
            sample = [p.get('numero') for p in bucket[:10]]
            logger.info(f"     sample: {sample}")
    return buckets


def indexar_e_criar_buckets_unico(driver: Union[WebDriver, str], filtros_observacao: Optional[List[str]] = None, dry_run: bool = False) -> Union[bool, Dict[str, List[Dict[str, Any]]]]:
    """Lê tabela, agrupa processos em buckets pela observação, executa."""
    if filtros_observacao is None:
        filtros_observacao = ['xs', 'silas', 'sobrestamento', 'sob ']

    progresso = carregar_progresso_pec()
    logger.info(f"[INDEXAR] Progresso: {len(progresso.get('processos_executados', []))} executados")

    # Extrair linhas da tabela
    if isinstance(driver, str):
        from bs4 import BeautifulSoup
        linhas = BeautifulSoup(driver, 'html.parser').find_all('tr')
    else:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        if not linhas:
            logger.info("[INDEXAR]  Nenhuma linha encontrada na tabela")
            return False
    
    logger.info(f"[INDEXAR] Total de linhas encontradas: {len(linhas)}")

    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

    processos_para_abrir: List[Dict[str, Any]] = []
    processos_filtrados_obs = 0
    processos_ja_executados = 0
    processos_sem_acoes = 0

    # Iterar linhas e construir lista de processos com 'acoes' já determinadas (UMA chamada por observação)
    for idx, linha in enumerate(linhas):
        try:
            if isinstance(driver, str):
                colunas = linha.find_all('td')
                if len(colunas) < 6:
                    continue
                texto_b = colunas[1].find('b')
                numero_processo = padrao_proc.search(texto_b.get_text()).group(0) if texto_b else None
                span_obs = colunas[5].find('span', class_='texto-descricao')
                observacao = (span_obs.get_text() if span_obs else colunas[5].get_text()).lower().strip()
            else:
                colunas = linha.find_elements(By.TAG_NAME, 'td')
                if len(colunas) < 6:
                    continue
                try:
                    texto_b = colunas[1].find_element(By.TAG_NAME, 'b').text
                    numero_processo = padrao_proc.search(texto_b).group(0) if texto_b else None
                except:
                    numero_processo = None
                try:
                    observacao = colunas[5].find_element(By.CSS_SELECTOR, 'span.texto-descricao').text.lower().strip()
                except:
                    observacao = colunas[5].text.lower().strip()

            if not numero_processo or not observacao:
                continue

            # Filtro de observação
            if not any(f.lower() in observacao for f in filtros_observacao):
                processos_filtrados_obs += 1
                continue

            # Determinar ações UMA única vez e armazenar
            acoes_result = determinar_acoes_por_observacao(observacao)
            if not acoes_result:
                processos_sem_acoes += 1
                continue

            # Pular se já executado com SUCESSO (processos com erro serão reexecutados)
            if processo_ja_executado_pec(numero_processo, progresso):
                processos_ja_executados += 1
                continue

            processos_para_abrir.append({
                'numero': numero_processo,
                'observacao': observacao,
                'acoes': acoes_result,
                'linha': linha,
                'linha_index': idx
            })

        except Exception as e:
            logger.error(f"[INDEXAR]  Erro ao processar linha {idx}: {e}")
            continue
    
    # Log de diagnóstico
    logger.info(f"[INDEXAR] Resumo da filtragem:")
    logger.info(f"[INDEXAR]   Total linhas: {len(linhas)}")
    logger.info(f"[INDEXAR]   Filtrados por observação: {processos_filtrados_obs}")
    logger.info(f"[INDEXAR]   Sem ações válidas: {processos_sem_acoes}")
    logger.info(f"[INDEXAR]   Já executados (com sucesso): {processos_ja_executados}")
    logger.info(f"[INDEXAR]   Processos a processar: {len(processos_para_abrir)}")

    # Agrupar por buckets usando a primeira ação já determinada
    buckets = _agrupar_em_buckets(processos_para_abrir)

    if dry_run:
        return buckets

    from .processamento_buckets import _processar_buckets
    return _processar_buckets(driver, buckets, progresso)
