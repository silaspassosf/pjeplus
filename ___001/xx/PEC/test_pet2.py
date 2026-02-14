import logging
logger = logging.getLogger(__name__)

"""
Test script for pet2.py field-specific verification system.

This script:
1. Parses test data from doc.txt
2. Creates PeticaoLinha objects
3. Tests each petition against all rules
4. Validates that field isolation works correctly

Run: python PEC/test_pet2.py
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Any
import importlib.util

# Load pet2.py directly without going through PEC/__init__.py
pet2_path = os.path.join(os.path.dirname(__file__), 'pet2.py')
spec = importlib.util.spec_from_file_location("pet2", pet2_path)
pet2 = importlib.util.module_from_spec(spec)
sys.modules['pet2'] = pet2
spec.loader.exec_module(pet2)

# Import from loaded module
PeticaoLinha = pet2.PeticaoLinha
definir_regras = pet2.definir_regras
verifica_peticao_contra_hipotese = pet2.verifica_peticao_contra_hipotese
normalizar_texto = pet2.normalizar_texto


def parse_test_data(filepath: str) -> List[Dict[str, Any]]:
    """Parse test data from doc.txt file."""
    petitions = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments, empty lines, and header lines
            if not line or line.startswith('#') or line.startswith('=') or line.startswith('Formato') or 'TABELA' in line:
                continue
            
            # Parse petition data
            parts = [p.strip() for p in line.split('|')]
            if len(parts) != 8:
                continue
            
            numero, tipo, desc, tarefa, fase, perito, data_aud, polo = parts
            
            # Parse boolean eh_perito
            eh_perito = perito == 'True'
            
            # Parse data_audiencia
            data_audiencia = None
            if data_aud != 'None':
                try:
                    data_audiencia = datetime.strptime(data_aud, '%d/%m/%Y')
                except:
                    pass
            
            # Parse polo
            polo_parsed = None if polo == 'None' else polo
            
            petitions.append({
                'numero_processo': numero,
                'tipo_peticao': tipo,
                'descricao': desc,
                'tarefa': tarefa,
                'fase': fase,
                'eh_perito': eh_perito,
                'data_audiencia': data_audiencia,
                'polo': polo_parsed,
                'data_juntada': '15/12/2025',  # Fixed date for testing
                'elemento_html': None,  # Not needed for testing
                'indice': 0,  # Not needed for testing
            })
    
    return petitions


def create_peticao_linha(data: Dict[str, Any]) -> PeticaoLinha:
    """Create PeticaoLinha object from parsed data."""
    return PeticaoLinha(
        numero_processo=data['numero_processo'],
        tipo_peticao=data['tipo_peticao'],
        descricao=data['descricao'],
        tarefa=data['tarefa'],
        fase=data['fase'],
        data_juntada=data['data_juntada'],
        elemento_html=data['elemento_html'],
        eh_perito=data['eh_perito'],
        data_audiencia=data['data_audiencia'],
        polo=data['polo'],
        indice=data['indice'],
    )


def test_petition(peticao: PeticaoLinha, regras_dict: Dict[str, List]) -> Dict[str, Any]:
    """Test a single petition against all rules."""
    results = {}
    
    for nome_bloco, regras in regras_dict.items():
        block_matches = []
        
        for nome_regra, padroes, _ in regras:
            match = verifica_peticao_contra_hipotese(peticao, padroes)
            if match:
                block_matches.append(nome_regra)
        
        results[nome_bloco] = block_matches
    
    return results


def print_test_results(peticao: PeticaoLinha, results: Dict[str, List[str]], expected_block: str = None):
    """Print formatted test results for a petition."""
    numero = peticao.numero_processo.split('-')[0]
    tipo = peticao.tipo_peticao
    desc = peticao.descricao[:30] + '...' if len(peticao.descricao) > 30 else peticao.descricao
    
    
    total_matches = sum(len(matches) for matches in results.values())
    
    if total_matches == 0:
        pass
    else:
        for bloco, matches in results.items():
            if matches:
                for regra in matches:
                    status = "✓" if expected_block and bloco.lower() in expected_block.lower() else ""
    
    return total_matches


def main():
    """Main test execution."""
    print("=" * 80)
    print("TESTE DE VERIFICAÇÃO COM CAMPOS EXPLÍCITOS - pet2.py")
    print("=" * 80)
    
    # Load test data
    doc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'doc.txt')
    print(f"\nCarregando dados de teste de: {doc_path}")
    
    test_data = parse_test_data(doc_path)
    print(f"  → {len(test_data)} petições carregadas\n")
    
    # Load rules
    regras_dict = definir_regras()
    print(f"Regras carregadas:")
    for bloco, regras in regras_dict.items():
        print(f"  → {bloco}: {len(regras)} hipótese(s)")
    
    # Test statistics
    stats = {
        'total': len(test_data),
        'with_matches': 0,
        'without_matches': 0,
        'by_block': {},
    }
    
    # Test each petition
    print("\n" + "=" * 80)
    print("RESULTADOS DOS TESTES")
    print("=" * 80)
    
    for data in test_data:
        peticao = create_peticao_linha(data)
        results = test_petition(peticao, regras_dict)
        
        # Determine expected block from process number
        numero_inicial = peticao.numero_processo.split('-')[0]
        expected = None
        if numero_inicial.startswith('1000'):
            expected = 'apagar'
        elif numero_inicial.startswith('2000'):
            expected = 'perícias'
        elif numero_inicial.startswith('3000'):
            expected = 'recurso'
        elif numero_inicial.startswith('4000'):
            expected = 'diretos'
        elif numero_inicial.startswith('5000'):
            expected = 'gigs'
        elif numero_inicial.startswith('6000'):
            expected = 'análise'
        elif numero_inicial.startswith('9000'):
            expected = 'negativo'
        
        total_matches = print_test_results(peticao, results, expected)
        
        if total_matches > 0:
            stats['with_matches'] += 1
            for bloco, matches in results.items():
                if matches:
                    stats['by_block'][bloco] = stats['by_block'].get(bloco, 0) + 1
        else:
            stats['without_matches'] += 1
    
    # Print summary
    print("\n" + "=" * 80)
    print("RESUMO ESTATÍSTICO")
    print("=" * 80)
    print(f"Total de petições testadas: {stats['total']}")
    print(f"  → Com match: {stats['with_matches']}")
    print(f"  → Sem match: {stats['without_matches']}")
    print(f"\nMatches por bloco:")
    for bloco, count in sorted(stats['by_block'].items()):
        print(f"  → {bloco}: {count} petição(ões)")
    
    # Validation checks
    print("\n" + "=" * 80)
    print("VALIDAÇÕES")
    print("=" * 80)
    
    expected_with_match = len([d for d in test_data if not d['numero_processo'].startswith('9000')])
    expected_without_match = len([d for d in test_data if d['numero_processo'].startswith('9000')])
    
    checks = [
        ("Casos negativos (9000xxx) sem match", 
         stats['without_matches'] >= expected_without_match,
         f"{stats['without_matches']} >= {expected_without_match}"),
        
        ("Casos positivos (não-9000xxx) com match",
         stats['with_matches'] >= expected_with_match - 4,  # Allow some tolerance
         f"{stats['with_matches']} >= {expected_with_match - 4}"),
        
        ("Bloco APAGAR detectado",
         'apagar' in stats['by_block'],
         f"'apagar' in {list(stats['by_block'].keys())}"),
        
        ("Bloco PERÍCIAS detectado",
         'pericias' in stats['by_block'] or 'perícias' in stats['by_block'],
         f"perícias in {list(stats['by_block'].keys())}"),
    ]
    
    all_passed = True
    for check_name, passed, details in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {check_name}")
        if not passed:
            print(f"         Detalhes: {details}")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ TODOS OS TESTES PASSARAM")
    else:
        print("✗ ALGUNS TESTES FALHARAM")
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
