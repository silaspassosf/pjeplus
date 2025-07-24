"""
Módulo responsável pelos utilitários de processamento SISBAJUD.

Responsabilidades:
- Extração de resultados SISBAJUD do texto
- Interpretação de regras SISBAJUD
- Análise de texto para identificar padrões

Funções extraídas do m1.py:
- extract_sisbajud_result_from_text()
"""

def extract_sisbajud_result_from_text(text, log=True):
    """
    Extrai resultado SISBAJUD do texto do documento.
    
    Args:
        text (str): Texto completo do documento
        log (bool): Se True, imprime logs de debug
    
    Returns:
        tuple: (resultado, regra_aplicada)
            - resultado: 'positivo' ou 'negativo'
            - regra_aplicada: string descrevendo a regra aplicada
    """
    # Busca a primeira ocorrência de 'determinações normativas e legais' no texto completo
    lines = text.splitlines()
    det_idx = -1
    for idx, line in enumerate(lines):
        if 'determinações normativas e legais' in line.lower():
            det_idx = idx
            break
    if det_idx == -1:
        if log:
            print('[SISBAJUD][DEBUG] determinações normativas e legais marker not found in text.')
        return 'negativo', 'determinações normativas e legais marker not found, default negativo'
    
    # Busca por "Bloqueio de valores" após "determinações normativas e legais"
    bloqueio_idx = -1
    for offset in range(1, 21):
        if det_idx + offset >= len(lines):
            break
        result_line = lines[det_idx + offset].strip().lower()
        if not result_line:
            continue
        if log:
            print(f'[SISBAJUD][DEBUG] Checking line after determinações normativas e legais: {repr(result_line)}')
        
        # Busca pela seção "Bloqueio de valores"
        if 'bloqueio de valores' in result_line:
            bloqueio_idx = det_idx + offset
            if log:
                print(f'[SISBAJUD][DEBUG] Found "Bloqueio de valores" at line {bloqueio_idx}')
            break
    
    # Se não encontrou "Bloqueio de valores", não há SISBAJUD
    if bloqueio_idx == -1:
        if log:
            print('[SISBAJUD][DEBUG] "Bloqueio de valores" not found after determinações normativas e legais')
        return 'negativo', 'Bloqueio de valores não encontrado, sem SISBAJUD'
    
    # Analisa as linhas após "Bloqueio de valores" procurando por SISBAJUD
    for offset in range(1, 15):
        if bloqueio_idx + offset >= len(lines):
            break
        sisbajud_line = lines[bloqueio_idx + offset].strip().lower()
        if not sisbajud_line:
            continue
        if log:
            print(f'[SISBAJUD][DEBUG] Checking line after Bloqueio de valores: {repr(sisbajud_line)}')
        
        # Busca por SISBAJUD e verifica se é seguido por Negativo ou Positivo
        if 'sisbajud' in sisbajud_line:
            if log:
                print(f'[SISBAJUD][DEBUG] Found SISBAJUD marker at line')
            
            # Verifica as próximas linhas após SISBAJUD
            for sib_offset in range(1, 5):
                if bloqueio_idx + offset + sib_offset >= len(lines):
                    break
                resultado_line = lines[bloqueio_idx + offset + sib_offset].strip().lower()
                if not resultado_line:
                    continue
                if log:
                    print(f'[SISBAJUD][DEBUG] Checking SISBAJUD result line: {repr(resultado_line)}')
                
                if 'negativo' in resultado_line:
                    if log:
                        print('[SISBAJUD][DEBUG] Found "Negativo" in SISBAJUD section')
                    return 'negativo', 'SISBAJUD Negativo na seção Bloqueio de valores'
                elif 'positivo' in resultado_line:
                    if log:
                        print('[SISBAJUD][DEBUG] Found "Positivo" in SISBAJUD section')
                    return 'positivo', 'SISBAJUD Positivo na seção Bloqueio de valores'
            
            # Se encontrou SISBAJUD mas não encontrou resultado, assume negativo
            if log:
                print('[SISBAJUD][DEBUG] Found SISBAJUD but no clear result, assuming negativo')
            return 'negativo', 'SISBAJUD encontrado mas resultado inconclusivo'
    
    if log:
        print('[SISBAJUD][DEBUG] No rule matched after determinações normativas e legais marker, default negativo.')
    return 'negativo', 'nenhuma regra anterior satisfeita, default negativo'
