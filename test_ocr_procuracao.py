#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para diagnóstico de OCR em procurações.
Testa extração de texto e busca de nomes.
"""

import io
import sys
from pathlib import Path

# Adicionar o projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

def test_ocr_procuracao():
    """Testa OCR e busca de nome em procuração."""
    print("=" * 80)
    print("TESTE DE OCR EM PROCURAÇÃO")
    print("=" * 80)
    
    # Teste 1: Tentar com pdfplumber (extração de texto nativo)
    try:
        import pdfplumber
        print("\n✓ pdfplumber disponível")
    except ImportError:
        print("\n✗ pdfplumber NÃO disponível")
        pdfplumber = None
    
    # Teste 2: Tentar com pytesseract/tesseract
    try:
        import pytesseract
        print("✓ pytesseract disponível")
        
        # Verificar se tesseract.exe está instalado
        import pathlib
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"D:\Tesseract-OCR\tesseract.exe",
        ]
        found_tess = None
        for c in candidates:
            if pathlib.Path(c).exists():
                found_tess = c
                break
        if found_tess:
            print(f"✓ tesseract.exe encontrado em: {found_tess}")
        else:
            print(f"✗ tesseract.exe NÃO encontrado. Candidatos testados: {candidates}")
    except ImportError:
        print("✗ pytesseract NÃO disponível")
        pytesseract = None
    
    # Teste 3: Tentar com fitz
    try:
        import fitz
        print("✓ fitz (PyMuPDF) disponível")
    except ImportError:
        print("✗ fitz (PyMuPDF) NÃO disponível")
        fitz = None
    
    # Teste 4: Procuração anexada no envelope
    print("\n" + "=" * 80)
    print("PROCURAÇÃO ANEXADA NO ENVELOPE PDF:")
    print("=" * 80)
    
    procuracao_texto = """
    P R O C U R A Ç Ã O
    
    OUTORGANTE: MYCHELLY DA SILVA FRANCA, brasileira, casada, nascida
    em 02 de outubro de 1981 (oitenta e hum), filha de Maria do Socorro da Silva Franca,
    inscrita no sob o nº CPF/MF 217.769.458-24 e cédula de identidade R.G. nº 33.719.061
    SSP/SP, portadora da CTPS nº 21776945, série 824-SP, PIS/PASEP 131.03155.93-9,
    residente e domiciliado em Mauá, SP, na Rua Santos Dumont n. 374, Vila Bocaina,
    CEP: 09310-130.nomeia e constituiu seu bastante procuradores;
    """
    
    print(procuracao_texto)
    
    # Teste 5: Busca de nome
    print("\n" + "=" * 80)
    print("TESTE DE BUSCA DE NOME:")
    print("=" * 80)
    
    from bianca.triagem.utils import _norm
    
    nome_reclamante = "MICHELLY DA SILVA FRANCA PEREIRA"
    nome_norm = _norm(nome_reclamante)
    procuracao_norm = _norm(procuracao_texto)
    
    print(f"Nome reclamante original: {nome_reclamante}")
    print(f"Nome reclamante normalizado: {nome_norm}")
    print()
    print(f"Procuração original (primeiros 200 chars):\n{procuracao_texto[:200]}")
    print()
    print(f"Procuração normalizada (primeiros 200 chars):\n{procuracao_norm[:200]}")
    print()
    
    # Estratégias de busca
    partes_nome = nome_norm.split()
    print(f"Partes do nome normalizado: {partes_nome}")
    
    estrategias = {
        "Nome completo": ' '.join(partes_nome),
        "Primeiro nome": partes_nome[0] if partes_nome else '',
        "Sobrenome": partes_nome[-1] if partes_nome else '',
    }
    
    print("\nTestes de busca:")
    for estrategia, busca_str in estrategias.items():
        if not busca_str or len(busca_str) <= 3:
            print(f"  ✗ {estrategia}: '{busca_str}' (muito curto)")
            continue
        
        # Estratégia 1: Substring simples
        encontrado_simples = busca_str in procuracao_norm
        
        # Estratégia 2: Com limites de palavra
        encontrado_palavra = ' ' + busca_str + ' ' in ' ' + procuracao_norm + ' '
        
        print(f"  {estrategia}: '{busca_str}'")
        print(f"    - Substring simples: {'✓' if encontrado_simples else '✗'}")
        print(f"    - Com limites de palavra: {'✓' if encontrado_palavra else '✗'}")
    
    print("\n" + "=" * 80)
    print("RECOMENDAÇÕES:")
    print("=" * 80)
    print("""
    1. Se pytesseract/tesseract NÃO estão disponíveis:
       - Instale Tesseract-OCR: https://github.com/UB-Mannheim/tesseract/wiki
       - Recomendado: C:\Program Files\Tesseract-OCR\

    2. Se pdfplumber NÃO está disponível:
       - pip install pdfplumber
    
    3. Para melhorar OCR de procurações:
       - Aumentar DPI de renderização (atual: 300)
       - Tentar usar a página inteira, não apenas fração
       - Adicionar preprocessamento de imagem (contraste, binarização)
    
    4. Para melhorar busca de nomes:
       - Usar regex com alternância (nomes, preposições)
       - Considerar variações ortográficas (MICHELLY vs MYCHELLY)
       - Buscar contexto "OUTORGANTE:" para localizar nome com certeza
    """)

if __name__ == '__main__':
    test_ocr_procuracao()
