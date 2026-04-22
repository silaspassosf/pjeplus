from .loop_base import *


def _selecionar_processos_por_gigs_aj_jt(driver: WebDriver, client: 'PjeApiClient') -> int:
    """Seleciona processos com atividade GIGS AJ-JT apenas em fase LIQUIDAÇÃO."""
    try:
        if not pausar_confirmacao('CICLO2/GIGS_AJ_JT', 'Iniciar varredura e seleção de processos com AJ-JT'):
            return 0
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        processos_com_gigs = []

        for linha in linhas:
            try:
                numero_processo = _extrair_numero_processo_da_linha(linha)
                if not numero_processo:
                    continue

                dados_gigs_fase = obter_gigs_com_fase(client, numero_processo)
                if not dados_gigs_fase:
                    continue

                # Apenas Liquidação
                if dados_gigs_fase.get('fase') != 'Liquidação':
                    continue

                # Procurar por AJ-JT
                atividades_gigs = dados_gigs_fase.get('atividades_gigs', [])
                for atividade in atividades_gigs:
                    if 'AJ-JT' in atividade.get('observacao', ''):
                        processos_com_gigs.append(numero_processo)
                        break

            except Exception:
                continue

        if processos_com_gigs:
            if not pausar_confirmacao('CICLO2/GIGS_AJ_JT_SCRIPT', f'Selecionar {len(processos_com_gigs)} processo(s) via script JS'):
                return 0
            selecionados = driver.execute_script(
                SCRIPT_SELECAO_GIGS_AJ_JT,
                processos_com_gigs
            )
            logger.info(f'[CICLO2][GIGS-AJ-JT] ✅ {selecionados} processo(s) com AJ-JT selecionado(s)')
            try:
                from Fix.core import aguardar_renderizacao_nativa
                aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1.5)
            except Exception:
                time.sleep(1.5)
            return selecionados

        logger.info('[CICLO2][GIGS-AJ-JT] ℹ️ Nenhum processo com atividade AJ-JT encontrado')
        return 0

    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro em _selecionar_processos_por_gigs_aj_jt: {e}')
        return 0


def _verificar_processo_tem_xs(client: 'PjeApiClient', numero_processo: str) -> bool:
    """Verifica se o processo já tem atividade GIGS xs (sem prazo).

    Args:
        client: Cliente PJe API
        numero_processo: Número do processo formatado (NNNNNNN-DD.AAAA.J.TT.OOOO)

    Returns:
        True se processo já tem atividade xs (sem prazo), False caso contrário
    """
    try:
        # Buscar atividades GIGS do processo
        atividades = client.atividades_gigs(numero_processo)

        if not atividades:
            return False

        # Verificar se existe alguma atividade sem prazo (dataPrazo vazio/null)
        for atividade in atividades:
            data_prazo = atividade.get('dataPrazo')
            # Se dataPrazo é None, vazio ou string vazia, é atividade xs
            if not data_prazo or (isinstance(data_prazo, str) and not data_prazo.strip()):
                print(f'[LOOP_PRAZO][XS] ⚠️ Processo {numero_processo} já tem atividade xs no GIGS')
                return True

        return False
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro ao verificar xs para {numero_processo}: {e}')
        # Em caso de erro, retornar False para não bloquear o processo
        return False


def _verificar_processos_xs_paralelo(client: 'PjeApiClient', numeros_processos: List[str], max_workers: int = 10) -> Dict[str, bool]:
    """Verifica múltiplos processos em paralelo para ver se têm atividade xs.

    Args:
        client: Cliente PJe API
        numeros_processos: Lista de números de processos
        max_workers: Número máximo de threads paralelas (padrão: 10)

    Returns:
        Dicionário {numero_processo: tem_xs}
    """
    resultados = {}
    total = len(numeros_processos)
    print(f'[LOOP_PRAZO][XS] 🚀 Verificando {total} processos em paralelo (workers={max_workers})...')

    inicio = time.time()

    # Função wrapper para executar em thread
    def verificar_um(numero: str) -> Tuple[str, bool]:
        tem_xs = _verificar_processo_tem_xs(client, numero)
        return (numero, tem_xs)

    # Executar em paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas as tarefas
        futures = {executor.submit(verificar_um, num): num for num in numeros_processos}

        # Processar resultados conforme completam
        processados = 0
        for future in as_completed(futures):
            try:
                numero, tem_xs = future.result()
                resultados[numero] = tem_xs
                processados += 1

                # Atualizar progresso a cada 10 processos
                if processados % 10 == 0 or processados == total:
                    print(f'[LOOP_PRAZO][XS] 📊 Progresso: {processados}/{total} ({processados*100//total}%)')

            except Exception as e:
                numero = futures[future]
                print(f'[LOOP_PRAZO][ERRO] Erro ao verificar {numero}: {e}')
                resultados[numero] = False

    duracao = time.time() - inicio
    print(f'[LOOP_PRAZO][XS] ✅ Verificação concluída em {duracao:.1f}s ({total/duracao:.1f} processos/s)')

    return resultados


def _obter_processos_com_gigs_api(client: 'PjeApiClient', numeros_processos: List[str], max_workers: int = 20) -> List[str]:
    """Retorna lista de números de processos que têm QUALQUER atividade GIGS (com ou sem prazo)."""
    com_gigs: List[str] = []

    def verificar_um(numero: str) -> Tuple[str, bool]:
        try:
            atividades = client.atividades_gigs(numero)
            return (numero, bool(atividades))
        except Exception:
            return (numero, False)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(verificar_um, num): num for num in numeros_processos}
        for future in as_completed(futures):
            try:
                numero, tem = future.result()
                if tem:
                    com_gigs.append(numero)
            except Exception:
                pass

    logger.info(f'[LOOP_PRAZO][GIGS_API] {len(com_gigs)}/{len(numeros_processos)} processos com gigs (API)')
    return com_gigs