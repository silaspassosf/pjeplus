"""
install_ocr_deps.py — Instala dependências opcionais para OCR.

OCR é necessário para extrair texto de documentos DIGITALIZADOS (RG, CNH, etc).
Se não estiver instalado, a extração retorna vazio para esses anexos.

Uso: python install_ocr_deps.py
"""

import subprocess
import sys

# Dependências para OCR (opcionais mas recomendadas)
DEPS_OCR = [
    'pytesseract',   # Interface Python para Tesseract
    'pdf2image',     # Converte PDF para imagem
]

print("[OCR] Instalando dependências opcionais para OCR...")
print(f"[OCR] Dependências: {DEPS_OCR}")

for dep in DEPS_OCR:
    print(f"\n[OCR] Instalando {dep}...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', dep])
        print(f"[OCR] ✓ {dep} instalado com sucesso")
    except subprocess.CalledProcessError as e:
        print(f"[OCR] ✗ ERRO ao instalar {dep}: {e}")
        print(f"[OCR] Tente manualmente: pip install {dep}")

print("\n[OCR] ℹ️  IMPORTANTES: Dois executáveis adicionais são necessários.")
print("[OCR]")
print("[OCR] 1) Tesseract-OCR:")
print("[OCR]   • Windows: https://github.com/UB-Mannheim/tesseract/wiki (baixe .exe)")
print("[OCR]   • Linux: sudo apt-get install tesseract-ocr")
print("[OCR]   • macOS: brew install tesseract")
print("[OCR]")
print("[OCR] 2) Poppler (necessário para pdf2image converter PDF em imagens):")
print("[OCR]   • Windows: https://github.com/oschwartz10612/poppler-windows/releases")
print("[OCR]             → Extraia em C:\\poppler  (espera-se C:\\poppler\\bin\\pdftoppm.exe)")
print("[OCR]             → Adicione C:\\poppler\\bin ao PATH do sistema")
print("[OCR]   • Linux: sudo apt-get install poppler-utils")
print("[OCR]   • macOS: brew install poppler")
print("\n[OCR] Done!")
