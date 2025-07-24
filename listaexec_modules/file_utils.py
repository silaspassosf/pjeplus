"""
Módulo para funções de manipulação de arquivos.
Extraído de listaexec2.py para modularização.
"""


def salvar_alvaras_processados_no_arquivo(alvaras_processados, log=True):
    """
    Salva alvarás processados no arquivo alvaras.js para uso pela função pagamento.
    
    Args:
        alvaras_processados: Lista de alvarás processados com dados completos
        log: Se deve exibir logs
    """
    try:
        if not alvaras_processados:
            return
            
        # Converter alvarás processados para o formato do arquivo
        alvaras_para_arquivo = []
        
        for alvara in alvaras_processados:
            # Extrair dados essenciais do alvará processado
            alvara_data = {
                'data_expedicao': alvara.get('data_expedicao', ''),
                'valor': alvara.get('valor', ''),
                'beneficiario': alvara.get('beneficiario', ''),
                'tipo': alvara.get('tipo', 'Alvará'),
                'status': 'PENDENTE'  # Status inicial
            }
            alvaras_para_arquivo.append(alvara_data)
        
        # Salvar no arquivo alvaras.js
        try:
            with open('alvaras.js', 'w', encoding='utf-8') as f:
                f.write('var alvaras = ')
                f.write(str(alvaras_para_arquivo).replace("'", '"'))
                f.write(';')
                
            if log:
                print(f'[ARQUIVO] ✅ Salvos {len(alvaras_para_arquivo)} alvarás processados no arquivo alvaras.js')
                
        except Exception as e_arquivo:
            if log:
                print(f'[ARQUIVO][ERRO] Erro ao salvar arquivo alvaras.js: {e_arquivo}')
            
    except Exception as e:
        if log:
            print(f'[SALVAR-ALVARAS][ERRO] Erro geral: {e}')
