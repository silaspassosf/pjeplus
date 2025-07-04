import re

# Dados esperados para o processo 2
dados_esperados = {
    'total': '23.052,24',
    'data_liquidacao': '03/08/2023',
    'id_planilha': 'P5502',
    'custas': '299,89',
    'assinatura': 'P5502',
    'inss': '1.035,16',
    'honorarios': '2.305,22'
}

# Padrões de extração do CALC.user.js
padroes = {
    'totalBruto': r'(?:Total\s+(?:Bruto|Geral|dos\s+Créditos?)[\s\S]*?|TOTAL[\s\S]*?|Valor\s+Total[\s\S]*?)(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})',
    'dataLiquidacao': r'(?:Data\s+(?:de\s+)?Liquidação|Atualização|Cálculo)[\s\S]*?(\d{1,2}\/\d{1,2}\/\d{4})',
    'assinaturaId': r'(?:Planilha|ID|Identificação|Assinatura)[\s\S]*?([A-Z]\d{4,})',
    'custas': r'(?:Custas?|Taxa)[\s\S]*?(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})',
    'honorarios': r'(?:Honorários?\s+(?:Advocatícios?|Sucumbenciais?|de\s+Sucumbência)|Hon\.?\s+Adv)[\s\S]*?(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})',
    'inss': r'(?:INSS|Instituto\s+Nacional)[\s\S]*?(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})'
}

# Texto simulado do processo 2
texto_processo2 = """
CÁLCULO DE LIQUIDAÇÃO DE SENTENÇA

Planilha de Cálculo ID: P5502
Data de Liquidação: 03/08/2023

Discriminação dos Valores:

Valor Principal: R$ 19.412,76
Correção Monetária: R$ 1.299,21

Deduções:
INSS: R$ 1.035,16
Custas Processuais: R$ 299,89

Honorários Advocatícios: R$ 2.305,22

TOTAL GERAL DOS CRÉDITOS: R$ 23.052,24

Assinatura Digital: P5502
"""

def testar_padrao(nome, padrao, texto_teste, valor_esperado):
    print(f"\n=== Testando {nome} ===")
    print(f"Padrão: {padrao}")
    print(f"Esperado: {valor_esperado}")
    
    match = re.search(padrao, texto_teste, re.IGNORECASE)
    
    if match:
        valor_extraido = match.group(1)
        print(f"Extraído: {valor_extraido}")
        
        if valor_extraido == valor_esperado:
            print("✅ SUCESSO!")
            return True
        else:
            print("❌ FALHOU!")
            print(f"Match completo: {match.groups()}")
            return False
    else:
        print("❌ NENHUM MATCH ENCONTRADO!")
        return False

def executar_todos_testes():
    print("🧪 TESTE MANUAL - PROCESSO 2")
    print("=" * 50)
    
    testes = [
        ('Total Bruto', padroes['totalBruto'], dados_esperados['total']),
        ('Data de Liquidação', padroes['dataLiquidacao'], dados_esperados['data_liquidacao']),
        ('ID/Assinatura', padroes['assinaturaId'], dados_esperados['assinatura']),
        ('Custas', padroes['custas'], dados_esperados['custas']),
        ('Honorários', padroes['honorarios'], dados_esperados['honorarios']),
        ('INSS', padroes['inss'], dados_esperados['inss'])
    ]
    
    sucessos = 0
    total = len(testes)
    
    for nome, padrao, esperado in testes:
        if testar_padrao(nome, padrao, texto_processo2, esperado):
            sucessos += 1
    
    print(f"\n{'='*50}")
    print(f"📊 RESUMO FINAL")
    print(f"Sucessos: {sucessos}/{total}")
    print(f"Taxa de acerto: {(sucessos/total*100):.1f}%")
    
    if sucessos == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM!")
    
    return sucessos == total

if __name__ == "__main__":
    executar_todos_testes()
