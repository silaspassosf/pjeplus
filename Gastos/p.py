import openpyxl
from openpyxl.cell.cell import MergedCell

# Coloque o nome exato do ficheiro que guardou no seu computador
nome_arquivo = 'Prestacao_de_Contas.xlsx' 
novo_arquivo = 'Prestacao_de_Contas_Final.xlsx'

try:
    print("A abrir a folha de cálculo e a carregar formatações...")
    wb = openpyxl.load_workbook(nome_arquivo)

    # 1. Capturar o "molde" perfeito da aba de Maio 2025
    aba_modelo = wb['Maio 2025']
    rubricas_modelo = {}

    # Lemos as descrições da linha 5 até ao fim da aba modelo
    for linha in range(5, aba_modelo.max_row + 1):
        celula_b_modelo = aba_modelo[f'B{linha}']
        # Guarda o valor apenas se não for uma linha de título/subtotal mesclada
        if not isinstance(celula_b_modelo, MergedCell):
            rubricas_modelo[linha] = celula_b_modelo.value

    # 2. Aplicar o molde a todas as outras abas
    for nome_aba in wb.sheetnames:
        ws = wb[nome_aba]
        print(f"🔄 A padronizar a aba: {nome_aba}")
        
        for linha in range(5, ws.max_row + 1):
            
            # A) Replicar os nomes das despesas
            celula_b = ws[f'B{linha}']
            if not isinstance(celula_b, MergedCell) and linha in rubricas_modelo:
                celula_b.value = rubricas_modelo[linha]
            
            # B) Limpar a coluna E (Comprovantes) apagando a referência "Doc."
            celula_e = ws[f'E{linha}']
            if not isinstance(celula_e, MergedCell):
                valor_comprovante = str(celula_e.value) if celula_e.value else ""
                if "Doc." in valor_comprovante:
                    celula_e.value = None
                    
            # C) Limpar a coluna G (Links antigos e quebrados)
            celula_g = ws[f'G{linha}']
            if not isinstance(celula_g, MergedCell):
                valor_link = str(celula_g.value) if celula_g.value else ""
                if "Abrir no App" in valor_link or "Upload" in valor_link:
                    celula_g.value = None

    wb.save(novo_arquivo)
    print(f"\n✅ SUCESSO! O ficheiro '{novo_arquivo}' foi guardado.")
    print("Todas as abas estão idênticas a Maio/2025 e sem a referência 'Doc.'!")

except FileNotFoundError:
    print(f"❌ Erro: O ficheiro '{nome_arquivo}' não foi encontrado.")
except Exception as e:
    print(f"❌ Ocorreu um erro: {e}")