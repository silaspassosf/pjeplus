# EXEMPLO DE REFATORAÇÃO DO def_sob BASEADO NA ESTRUTURA CLARA DO p2.py
# Este arquivo mostra como o def_sob poderia ser refatorado para ser mais claro e direto

def def_sob_refatorado(driver, numero_processo, observacao, debug=False, timeout=10):
    """
    Versão refatorada do def_sob usando estrutura mais clara baseada no p2.py
    
    VANTAGENS:
    1. Estrutura mais limpa e organizada
    2. Cada regra é uma função separada (melhor organização)
    3. Loop único para aplicar regras (DRY principle)
    4. Mais fácil de adicionar/remover regras
    5. Menos código repetitivo
    6. Mais fácil de debugar e manter
    """
    
    # ===== FUNÇÕES DE AÇÃO PARA CADA REGRA =====
    def executar_mov_sob_precatorio():
        """Executa mov_sob com 1 mês para precatório/RPV/pequeno valor"""
        log_msg("✅ Regra: 'precatório/RPV/pequeno valor' - executando mov_sob com 1 mês")
        try:
            from atos import mov_sob
            resultado = mov_sob(driver, numero_processo, "sob 1", debug=True, timeout=timeout)
            return resultado
        except Exception as e:
            log_msg(f"❌ Erro ao executar mov_sob: {e}")
            return False
    
    def executar_juizo_universal():
        """Executa sequência mov_fimsob + ato_fal para juízo universal"""
        log_msg("✅ Regra: 'juízo universal' - executando mov_fimsob + ato_fal")
        try:
            # Capturar informações das abas
            abas_antes = driver.window_handles
            aba_atual = driver.current_window_handle
            
            # Executar mov_fimsob
            from atos import mov_fimsob
            resultado_fimsob = mov_fimsob(driver, debug=debug)
            if not resultado_fimsob:
                return False
            
            # Garantir aba correta e executar ato_fal
            if aba_atual in driver.window_handles:
                driver.switch_to.window(aba_atual)
            
            from atos import ato_fal
            resultado_fal = ato_fal(driver, debug=debug)
            return resultado_fal
            
        except Exception as e:
            log_msg(f"❌ Erro durante sequência juízo universal: {e}")
            return False
    
    def executar_def_presc():
        """Executa def_presc para prazo prescricional"""
        log_msg("✅ Regra: 'prazo prescricional' - executando def_presc")
        try:
            resultado = def_presc(driver, numero_processo, texto, debug=debug)
            return resultado
        except Exception as e:
            log_msg(f"❌ Erro ao executar def_presc: {e}")
            return False
    
    def executar_ato_prov():
        """Executa ato_prov para atos principais"""
        log_msg("✅ Regra: 'atos principais' - executando ato_prov")
        try:
            from atos import ato_prov
            resultado = ato_prov(driver, debug=debug)
            return resultado
        except Exception as e:
            log_msg(f"❌ Erro ao executar ato_prov: {e}")
            return False
    
    def executar_ato_x90():
        """Executa ato_x90 para andamento da penhora no rosto"""
        log_msg("✅ Regra: 'andamento da penhora no rosto' - executando ato_x90")
        try:
            from atos import ato_x90
            resultado = ato_x90(driver, debug=debug)
            return resultado
        except Exception as e:
            log_msg(f"❌ Erro ao executar ato_x90: {e}")
            return False

    # ===== ESTRUTURA DE REGRAS BASEADA NO p2.py =====
    regras_def_sob = [
        # [lista_de_termos, função_de_ação, descrição]
        (['precatório', 'RPV', 'pequeno valor'], executar_mov_sob_precatorio, 'Precatório/RPV/Pequeno valor'),
        (['juízo universal'], executar_juizo_universal, 'Juízo universal'),
        (['prazo prescricional'], executar_def_presc, 'Prazo prescricional'),
        (['atos principais'], executar_ato_prov, 'Atos principais'),
        (['andamento da penhora no rosto'], executar_ato_x90, 'Andamento da penhora no rosto'),
    ]
    
    # ===== APLICAÇÃO DAS REGRAS (LOOP ÚNICO - MAIS LIMPO) =====
    log_msg("Analisando conteúdo e aplicando regras...")
    
    # Normalizar texto uma única vez
    texto_normalizado = normalizar_texto(texto)
    
    # Aplicar regras de forma limpa
    for termos, acao_func, descricao in regras_def_sob:
        # Verificar se algum termo da regra está presente
        for termo in termos:
            regex = gerar_regex_geral(termo)
            if regex.search(texto_normalizado):
                log_msg(f"Regra encontrada: {descricao} (termo: '{termo}')")
                resultado = acao_func()
                if resultado:
                    log_msg(f"✅ Regra '{descricao}' executada com sucesso")
                    return True
                else:
                    log_msg(f"❌ Falha na execução da regra '{descricao}'")
                    return False
    
    # Se nenhuma regra foi aplicada
    regras_nomes = [descricao for _, _, descricao in regras_def_sob]
    log_msg("⚠️ Nenhuma regra aplicável encontrada no conteúdo")
    log_msg(f"Regras verificadas: {', '.join(regras_nomes)}")
    return False

# ===== COMPARAÇÃO ESTRUTURAL =====

"""
ESTRUTURA ATUAL (pec.py):
- 150+ linhas para def_sob
- Cada regra tem 15-20 linhas de código repetitivo
- if/elif/else grande e difícil de manter
- Adição de nova regra requer modificar múltiplos pontos

ESTRUTURA PROPOSTA (baseada em p2.py):
- ~100 linhas para def_sob
- Cada regra é uma função separada e concisa
- Loop único para aplicar todas as regras
- Adição de nova regra requer apenas adicionar item na lista
- Mais fácil de debugar e manter
- Melhor organização do código

VANTAGENS DA REFATORAÇÃO:
1. Código mais limpo e legível
2. Princípio DRY (Don't Repeat Yourself) aplicado
3. Easier to add new rules
4. Better error handling
5. More maintainable
6. Consistent with p2.py structure
"""
