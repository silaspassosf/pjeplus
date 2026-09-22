#!/usr/bin/env python3
"""
Script de limpeza SEGURA de temporários Python.
Remove apenas __pycache__ e .pyc do workspace.
NÃO toca em configurações do VS Code para evitar problemas.
"""

import os
import shutil
import sys
from pathlib import Path

def limpar_pycache(raiz: str) -> int:
    """Remove todos os diretórios __pycache__."""
    removidos = 0
    for root, dirs, files in os.walk(raiz):
        if '__pycache__' in dirs:
            caminho = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(caminho)
                print(f"✅ Removido: {caminho}")
                removidos += 1
            except Exception as e:
                print(f"❌ Erro ao remover {caminho}: {e}")
    return removidos

def limpar_pyc(raiz: str) -> int:
    """Remove todos os arquivos .pyc."""
    removidos = 0
    for root, dirs, files in os.walk(raiz):
        for arquivo in files:
            if arquivo.endswith('.pyc'):
                caminho = os.path.join(root, arquivo)
                try:
                    os.remove(caminho)
                    print(f"✅ Removido: {caminho}")
                    removidos += 1
                except Exception as e:
                    print(f"❌ Erro ao remover {caminho}: {e}")
    return removidos

def limpar_pyo(raiz: str) -> int:
    """Remove todos os arquivos .pyo."""
    removidos = 0
    for root, dirs, files in os.walk(raiz):
        for arquivo in files:
            if arquivo.endswith('.pyo'):
                caminho = os.path.join(root, arquivo)
                try:
                    os.remove(caminho)
                    print(f"✅ Removido: {caminho}")
                    removidos += 1
                except Exception as e:
                    print(f"❌ Erro ao remover {caminho}: {e}")
    return removidos

def limpar_pytest_cache(raiz: str) -> int:
    """Remove diretórios .pytest_cache."""
    removidos = 0
    for root, dirs, files in os.walk(raiz):
        if '.pytest_cache' in dirs:
            caminho = os.path.join(root, '.pytest_cache')
            try:
                shutil.rmtree(caminho)
                print(f"✅ Removido: {caminho}")
                removidos += 1
            except Exception as e:
                print(f"❌ Erro ao remover {caminho}: {e}")
    return removidos

def limpar_python_logs_vscode() -> int:
    """Remove logs de execução Python do VS Code (SEGURO)."""
    removidos = 0
    caminhos_logs = [
        os.path.expanduser(r"~\AppData\Roaming\Code\logs\*\exthost\ms-python.python"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python*\Lib\site-packages\__pycache__"),
    ]
    
    for pattern in caminhos_logs:
        from glob import glob
        for caminho in glob(pattern, recursive=True):
            if os.path.exists(caminho):
                try:
                    if os.path.isdir(caminho):
                        shutil.rmtree(caminho)
                    else:
                        os.remove(caminho)
                    print(f"✅ Removido: {caminho}")
                    removidos += 1
                except Exception as e:
                    print(f"⚠️  Erro ao remover {caminho}: {e}")
    
    return removidos

def limpar_pylance_cache_seguro() -> int:
    """Remove APENAS cache de análise do Pylance (regenerável, SEGURO)."""
    removidos = 0
    # Apenas cache de análise, não configurações
    pylance_cache = os.path.expanduser(r"~\AppData\Local\Temp\pylance")
    
    if os.path.exists(pylance_cache):
        try:
            shutil.rmtree(pylance_cache)
            print(f"✅ Removido: {pylance_cache}")
            removidos += 1
        except Exception as e:
            print(f"⚠️  Erro ao remover {pylance_cache}: {e}")
    
    return removidos

def limpar_vscode_workspace_storage(raiz: str) -> int:
    """Remove storage local do workspace (histórico, estados temporários)."""
    removidos = 0
    workspace_storage = os.path.join(raiz, '.vscode', 'workspaceStorage')
    
    if os.path.exists(workspace_storage):
        try:
            shutil.rmtree(workspace_storage)
            print(f"✅ Removido: {workspace_storage}")
            removidos += 1
        except Exception as e:
            print(f"⚠️  Erro ao remover {workspace_storage}: {e}")
    
    return removidos

def main():
    """Executa limpeza SEGURA apenas do workspace Python."""
    raiz = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print("🧹 LIMPEZA SEGURA DE TEMPORÁRIOS PYTHON + VS CODE")
    print("=" * 70)
    print(f"📂 Workspace: {raiz}")
    print("\n⚠️  NOTA: Remove apenas temporários seguros que podem ser regenerados.")
    print("⚠️  NÃO remove configurações ou cache crítico do VS Code.\n")
    
    total = 0
    
    print("📦 Limpando __pycache__...")
    total += limpar_pycache(raiz)
    
    print("\n📦 Limpando arquivos .pyc...")
    total += limpar_pyc(raiz)
    
    print("\n📦 Limpando arquivos .pyo...")
    total += limpar_pyo(raiz)
    
    print("\n📦 Limpando .pytest_cache...")
    total += limpar_pytest_cache(raiz)
    
    print("\n📦 Limpando logs Python do VS Code...")
    total += limpar_python_logs_vscode()
    
    print("\n📦 Limpando cache de análise Pylance...")
    total += limpar_pylance_cache_seguro()
    
    print("\n📦 Limpando workspace storage local...")
    total += limpar_vscode_workspace_storage(raiz)
    
    print("\n" + "=" * 70)
    print(f"✅ LIMPEZA CONCLUÍDA - {total} items removidos")
    print("=" * 70)
    print("\n💡 DICA: Recarregue o VS Code se necessário:")
    print("   Ctrl+Shift+P > 'Developer: Reload Window'")
    print("\n🔒 SEGURO: Cache de análise do Pylance será regenerado automaticamente.")

if __name__ == '__main__':
    main()
