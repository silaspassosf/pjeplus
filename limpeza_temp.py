#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
limpeza_temp.py - Script para limpeza de arquivos temporários e execuções anteriores

Funcionalidades:
1. Remove arquivos temporários de ontem para trás
2. Limpa logs de execuções antigas
3. Remove cookies expirados
4. Limpa arquivos de progresso antigos
5. Remove relatórios temporários
"""

import os
import glob
import shutil
from datetime import datetime, timedelta
import json

def limpar_arquivos_por_data(pasta, extensoes, dias_atras=1, log=True):
    """Remove arquivos com mais de X dias"""
    try:
        data_limite = datetime.now() - timedelta(days=dias_atras)
        arquivos_removidos = 0
        
        for extensao in extensoes:
            pattern = os.path.join(pasta, f"*.{extensao}")
            for arquivo in glob.glob(pattern):
                try:
                    data_modificacao = datetime.fromtimestamp(os.path.getmtime(arquivo))
                    if data_modificacao < data_limite:
                        os.remove(arquivo)
                        arquivos_removidos += 1
                        if log:
                            print(f"[LIMPEZA] Removido: {os.path.basename(arquivo)}")
                except Exception as e:
                    if log:
                        print(f"[LIMPEZA] Erro ao remover {arquivo}: {e}")
        
        if log:
            print(f"[LIMPEZA] {arquivos_removidos} arquivos {extensoes} removidos de {pasta}")
        return arquivos_removidos
    except Exception as e:
        if log:
            print(f"[LIMPEZA] Erro na pasta {pasta}: {e}")
        return 0

def limpar_cookies_antigos(log=True):
    """Remove cookies com mais de 3 horas"""
    try:
        pasta_cookies = "cookies_sessoes"
        if not os.path.exists(pasta_cookies):
            return 0
        
        data_limite = datetime.now() - timedelta(hours=3)
        arquivos_removidos = 0
        
        for arquivo in os.listdir(pasta_cookies):
            if arquivo.endswith('.json'):
                caminho_completo = os.path.join(pasta_cookies, arquivo)
                try:
                    data_modificacao = datetime.fromtimestamp(os.path.getmtime(caminho_completo))
                    if data_modificacao < data_limite:
                        os.remove(caminho_completo)
                        arquivos_removidos += 1
                        if log:
                            print(f"[LIMPEZA] Cookie removido: {arquivo}")
                except Exception as e:
                    if log:
                        print(f"[LIMPEZA] Erro ao remover cookie {arquivo}: {e}")
        
        if log:
            print(f"[LIMPEZA] {arquivos_removidos} cookies antigos removidos")
        return arquivos_removidos
    except Exception as e:
        if log:
            print(f"[LIMPEZA] Erro ao limpar cookies: {e}")
        return 0

def limpar_logs_antigos(log=True):
    """Remove logs com mais de 3 dias"""
    try:
        extensoes_log = ['log', 'txt']
        patterns_log = ['*debug*', '*test*', '*temp*', '*tmp*', 'pje_automacao*']
        
        arquivos_removidos = 0
        data_limite = datetime.now() - timedelta(days=3)
        
        # Logs por padrão
        for pattern in patterns_log:
            for arquivo in glob.glob(pattern):
                if any(arquivo.endswith(f'.{ext}') for ext in extensoes_log):
                    try:
                        data_modificacao = datetime.fromtimestamp(os.path.getmtime(arquivo))
                        if data_modificacao < data_limite:
                            os.remove(arquivo)
                            arquivos_removidos += 1
                            if log:
                                print(f"[LIMPEZA] Log removido: {arquivo}")
                    except Exception as e:
                        if log:
                            print(f"[LIMPEZA] Erro ao remover log {arquivo}: {e}")
        
        if log:
            print(f"[LIMPEZA] {arquivos_removidos} logs antigos removidos")
        return arquivos_removidos
    except Exception as e:
        if log:
            print(f"[LIMPEZA] Erro ao limpar logs: {e}")
        return 0

def limpar_relatorios_temporarios(log=True):
    """Remove relatórios HTML temporários antigos"""
    try:
        patterns = ['relatorio_*.html', 'relatorio_*.txt', 'ecarta_*.html']
        arquivos_removidos = 0
        data_limite = datetime.now() - timedelta(days=2)
        
        for pattern in patterns:
            for arquivo in glob.glob(pattern):
                try:
                    data_modificacao = datetime.fromtimestamp(os.path.getmtime(arquivo))
                    if data_modificacao < data_limite:
                        os.remove(arquivo)
                        arquivos_removidos += 1
                        if log:
                            print(f"[LIMPEZA] Relatório removido: {arquivo}")
                except Exception as e:
                    if log:
                        print(f"[LIMPEZA] Erro ao remover relatório {arquivo}: {e}")
        
        if log:
            print(f"[LIMPEZA] {arquivos_removidos} relatórios temporários removidos")
        return arquivos_removidos
    except Exception as e:
        if log:
            print(f"[LIMPEZA] Erro ao limpar relatórios: {e}")
        return 0

def limpar_arquivos_progresso(log=True):
    """Remove arquivos de progresso antigos"""
    try:
        patterns = ['progresso_*.json', '*_progress.json', 'dados_temp_*.json']
        arquivos_removidos = 0
        data_limite = datetime.now() - timedelta(days=1)
        
        for pattern in patterns:
            for arquivo in glob.glob(pattern):
                try:
                    data_modificacao = datetime.fromtimestamp(os.path.getmtime(arquivo))
                    if data_modificacao < data_limite:
                        os.remove(arquivo)
                        arquivos_removidos += 1
                        if log:
                            print(f"[LIMPEZA] Progresso removido: {arquivo}")
                except Exception as e:
                    if log:
                        print(f"[LIMPEZA] Erro ao remover progresso {arquivo}: {e}")
        
        if log:
            print(f"[LIMPEZA] {arquivos_removidos} arquivos de progresso removidos")
        return arquivos_removidos
    except Exception as e:
        if log:
            print(f"[LIMPEZA] Erro ao limpar arquivos de progresso: {e}")
        return 0

def limpar_cache_python(log=True):
    """Remove cache do Python (__pycache__)"""
    try:
        arquivos_removidos = 0
        
        # Buscar todas as pastas __pycache__
        for root, dirs, files in os.walk('.'):
            if '__pycache__' in dirs:
                pasta_cache = os.path.join(root, '__pycache__')
                try:
                    shutil.rmtree(pasta_cache)
                    arquivos_removidos += 1
                    if log:
                        print(f"[LIMPEZA] Cache removido: {pasta_cache}")
                except Exception as e:
                    if log:
                        print(f"[LIMPEZA] Erro ao remover cache {pasta_cache}: {e}")
        
        # Remover arquivos .pyc individuais
        for arquivo in glob.glob('*.pyc'):
            try:
                os.remove(arquivo)
                arquivos_removidos += 1
                if log:
                    print(f"[LIMPEZA] .pyc removido: {arquivo}")
            except Exception as e:
                if log:
                    print(f"[LIMPEZA] Erro ao remover .pyc {arquivo}: {e}")
        
        if log:
            print(f"[LIMPEZA] {arquivos_removidos} itens de cache Python removidos")
        return arquivos_removidos
    except Exception as e:
        if log:
            print(f"[LIMPEZA] Erro ao limpar cache Python: {e}")
        return 0

def limpar_arquivos_teste(log=True):
    """Remove arquivos de teste temporários"""
    try:
        patterns = ['teste_*.py', 'test_*.py', 'debug_*.py', '*_test.py', '*_debug.py']
        arquivos_removidos = 0
        data_limite = datetime.now() - timedelta(days=2)
        
        # Exceções - arquivos que não devem ser removidos
        excecoes = ['test_html_insert.py', 'debug_visual_config.py']
        
        for pattern in patterns:
            for arquivo in glob.glob(pattern):
                if os.path.basename(arquivo) in excecoes:
                    continue
                    
                try:
                    data_modificacao = datetime.fromtimestamp(os.path.getmtime(arquivo))
                    if data_modificacao < data_limite:
                        os.remove(arquivo)
                        arquivos_removidos += 1
                        if log:
                            print(f"[LIMPEZA] Teste removido: {arquivo}")
                except Exception as e:
                    if log:
                        print(f"[LIMPEZA] Erro ao remover teste {arquivo}: {e}")
        
        if log:
            print(f"[LIMPEZA] {arquivos_removidos} arquivos de teste removidos")
        return arquivos_removidos
    except Exception as e:
        if log:
            print(f"[LIMPEZA] Erro ao limpar arquivos de teste: {e}")
        return 0

def obter_tamanho_pasta(pasta):
    """Calcula tamanho total de uma pasta em MB"""
    try:
        tamanho_total = 0
        for dirpath, dirnames, filenames in os.walk(pasta):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    tamanho_total += os.path.getsize(filepath)
                except:
                    pass
        return tamanho_total / (1024 * 1024)  # Converter para MB
    except:
        return 0

def main():
    """Função principal de limpeza"""
    print("========================================")
    print("LIMPEZA DE ARQUIVOS TEMPORÁRIOS")
    print("========================================")
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Calcular tamanho inicial
    tamanho_inicial = obter_tamanho_pasta('.')
    print(f"[LIMPEZA] Tamanho inicial do projeto: {tamanho_inicial:.2f} MB")
    print()
    
    total_removidos = 0
    
    # 1. Cookies antigos (7+ dias)
    print("[LIMPEZA] 1. Limpando cookies antigos...")
    total_removidos += limpar_cookies_antigos()
    print()
    
    # 2. Logs antigos (3+ dias)
    print("[LIMPEZA] 2. Limpando logs antigos...")
    total_removidos += limpar_logs_antigos()
    print()
    
    # 3. Relatórios temporários (2+ dias)
    print("[LIMPEZA] 3. Limpando relatórios temporários...")
    total_removidos += limpar_relatorios_temporarios()
    print()
    
    # 4. Arquivos de progresso (1+ dia)
    print("[LIMPEZA] 4. Limpando arquivos de progresso...")
    total_removidos += limpar_arquivos_progresso()
    print()
    
    # 5. Cache Python
    print("[LIMPEZA] 5. Limpando cache Python...")
    total_removidos += limpar_cache_python()
    print()
    
    # 6. Arquivos de teste (2+ dias)
    print("[LIMPEZA] 6. Limpando arquivos de teste...")
    total_removidos += limpar_arquivos_teste()
    print()
    
    # Calcular tamanho final
    tamanho_final = obter_tamanho_pasta('.')
    espaco_liberado = tamanho_inicial - tamanho_final
    
    print("========================================")
    print("RESUMO DA LIMPEZA")
    print("========================================")
    print(f"Total de arquivos removidos: {total_removidos}")
    print(f"Tamanho inicial: {tamanho_inicial:.2f} MB")
    print(f"Tamanho final: {tamanho_final:.2f} MB")
    print(f"Espaço liberado: {espaco_liberado:.2f} MB")
    print()
    
    if total_removidos > 0:
        print("✅ Limpeza concluída com sucesso!")
    else:
        print("ℹ️ Nenhum arquivo temporário encontrado para remoção")
    
    print("========================================")

if __name__ == "__main__":
    main()
