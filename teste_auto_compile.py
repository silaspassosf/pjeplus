# Arquivo de teste para demonstrar Auto-Compile & Fix
# Este arquivo contém erros intencionais para testar a extensão

def teste_com_erro():
    """Função com erro intencional para testar detecção automática"""
    print("Iniciando teste...")
    
    # Erro 1: Variável não definida
    resultado = variavel_inexistente + 10
    
    # Erro 2: Indentação incorreta
   print("Resultado:", resultado)
    
    return resultado

def teste_sintaxe_incorreta():
    """Função com erro de sintaxe"""
    if True
        print("Faltou dois pontos no if")
    
    # Erro 3: Parênteses não fechados
    lista = [1, 2, 3
    return lista

def teste_import_inexistente():
    """Função com import que não existe"""
    import modulo_que_nao_existe
    return modulo_que_nao_existe.funcao()

# Como testar:
# 1. Abra este arquivo no VS Code
# 2. Clique com botão direito → "🔧 Compile & Validate Current File"
# 3. A extensão detectará os erros e focará no primeiro
# 4. Use @restricted no chat para análise e correção

if __name__ == "__main__":
    teste_com_erro()
