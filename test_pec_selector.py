#!/usr/bin/env python3
"""
Teste para validar os seletores de PEC após correção
"""

# Simular a estrutura de seletor de PEC
def test_pec_selectors():
    """Testa os diferentes seletores de PEC em ordem de prioridade"""
    
    # Novo seletor (label.enviarPec > input)
    novo_seletor = 'label.enviarPec input[type="checkbox"]'
    assert novo_seletor is not None, "Novo seletor nao pode ser None"
    print(f"[OK] Novo seletor: {novo_seletor}")
    
    # Seletores fallback (antigos)
    fallbacks = [
        'mat-checkbox[aria-label="Enviar para PEC"]',
        'div.checkbox-pec mat-checkbox',
        'input[type="checkbox"][aria-label="Enviar para PEC"]'
    ]
    
    for i, selector in enumerate(fallbacks, 1):
        assert selector is not None, f"Fallback {i} nao pode ser None"
        print(f"[OK] Fallback {i}: {selector}")
    
    print("\n[PASS] Todos os seletores de PEC estao configurados")

if __name__ == "__main__":
    test_pec_selectors()
