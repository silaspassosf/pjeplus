from .loop_base import *


def _extrair_numero_processo_da_linha(linha_elemento: WebElement) -> Optional[str]:
    """Extrai número de processo de um elemento <tr> da tabela de atividades.

    Procura por <a> (links) que contenham o padrão de número de processo:
    NNNNNNN-DD.AAAA.J.TT.OOOO (formato processual brasileiro).

    Args:
        linha_elemento: elemento <tr> da tabela

    Returns:
        String com número do processo (formatado com pontos e hífen) ou None
    """
    try:
        # Buscar padrão processual usando regex
        padrao_processo = re.compile(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})')

        # Estratégia 1: Procurar em links <a> (localização padrão no PJe)
        try:
            links = linha_elemento.find_elements(By.CSS_SELECTOR, 'a')
            for link in links:
                texto = link.text.strip()
                match = padrao_processo.search(texto)
                if match:
                    return match.group(1)
        except:
            pass

        # Estratégia 2: Procurar em toda a linha (fallback)
        try:
            texto_linha = linha_elemento.text.strip()
            match = padrao_processo.search(texto_linha)
            if match:
                return match.group(1)
        except:
            pass

        return None
    except Exception as e:
        logger.error(f'[LOOP_PRAZO][DEBUG] Erro ao extrair número do processo: {e}')
        return None


def selecionar_processos_nao_livres(driver: WebDriver, max_processos: int = 20) -> Tuple[int, bool]:
    """Seleciona processos não livres (com prazo preenchido, comentário ou campo preenchido).
    Retorna (quantidade_selecionada, ha_mais) onde ha_mais indica se há mais processos além do limite.
    """
    try:
        # Executar script JavaScript para seleção
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, max_processos)

        if resultado == -1:
            print('[LOOP_PRAZO][ERRO] Falha no script de seleção de não livres')
            return 0, False

        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']

        ha_mais = total_nao_livres > max_processos

        print(f'[LOOP_PRAZO][NAO_LIVRES] ✅ Selecionados {selecionados} processos não livres (total: {total_nao_livres})')

        if ha_mais:
            print(f'[LOOP_PRAZO][NAO_LIVRES] ⚠️ Há mais processos não livres além do limite ({max_processos})')

        return selecionados, ha_mais

    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro em selecionar_processos_nao_livres: {e}')
        return 0, False