#!/usr/bin/env python3
"""
Script para configurar os caminhos do sistema nas credenciais do Windows.

Este script permite definir os caminhos dos drivers e perfis do Firefox
usando o keyring do Windows, permitindo configurações específicas por máquina
sem alterar o código-fonte.
"""

import keyring
import os
import sys
from Fix.utils_paths import (
    configurar_caminho_credencial,
    exibir_configuracao_atual
)

def configurar_caminhos_interativo():
    """Configura os caminhos de forma interativa"""
    print("Configuração de caminhos do sistema para PJePlus")
    print("=" * 50)

    # Caminho do perfil do Firefox
    print("\n1. Caminho do perfil do Firefox:")
    print("   Exemplo: C:\\Users\\SeuUsuario\\AppData\\Roaming\\Mozilla\\Dev\\Selenium")
    perfil_atual = keyring.get_password('pjeplus_paths', 'FIREFOX_PROFILE_PATH')
    if perfil_atual:
        print(f"   Configurado atualmente: {perfil_atual}")

    novo_perfil = input("   Digite o novo caminho (ou Enter para manter): ").strip()
    if novo_perfil and os.path.exists(novo_perfil):
        configurar_caminho_credencial('FIREFOX_PROFILE_PATH', novo_perfil)
        print("   ✓ Caminho do perfil do Firefox configurado com sucesso!")
    elif novo_perfil:
        print("   ✗ Caminho inválido, mantendo configuração atual")

    # Caminho do executável do Firefox
    print("\n2. Caminho do executável do Firefox:")
    print("   Exemplo: C:\\Program Files\\Firefox Developer Edition\\firefox.exe")
    exe_atual = keyring.get_password('pjeplus_paths', 'FIREFOX_BINARY')
    if exe_atual:
        print(f"   Configurado atualmente: {exe_atual}")

    novo_exe = input("   Digite o novo caminho (ou Enter para manter): ").strip()
    if novo_exe and os.path.exists(novo_exe):
        configurar_caminho_credencial('FIREFOX_BINARY', novo_exe)
        print("   ✓ Caminho do executável do Firefox configurado com sucesso!")
    elif novo_exe:
        print("   ✗ Caminho inválido, mantendo configuração atual")

    # Caminho do geckodriver
    print("\n3. Caminho do geckodriver:")
    print("   Exemplo: D:\\PjePlus\\Fix\\geckodriver.exe")
    gecko_atual = keyring.get_password('pjeplus_paths', 'GECKODRIVER_PATH')
    if gecko_atual:
        print(f"   Configurado atualmente: {gecko_atual}")

    novo_gecko = input("   Digite o novo caminho (ou Enter para manter): ").strip()
    if novo_gecko and os.path.exists(novo_gecko):
        configurar_caminho_credencial('GECKODRIVER_PATH', novo_gecko)
        print("   ✓ Caminho do geckodriver configurado com sucesso!")
    elif novo_gecko:
        print("   ✗ Caminho inválido, mantendo configuração atual")

    # Caminho do perfil VT PJE
    print("\n4. Caminho do perfil VT PJE:")
    print("   Exemplo: C:\\Users\\SeuUsuario\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\seu.perfil")
    vt_atual = keyring.get_password('pjeplus_paths', 'VT_PROFILE_PJE')
    if vt_atual:
        print(f"   Configurado atualmente: {vt_atual}")

    novo_vt = input("   Digite o novo caminho (ou Enter para manter): ").strip()
    if novo_vt and os.path.exists(novo_vt):
        configurar_caminho_credencial('VT_PROFILE_PJE', novo_vt)
        print("   ✓ Caminho do perfil VT PJE configurado com sucesso!")
    elif novo_vt:
        print("   ✗ Caminho inválido, mantendo configuração atual")

    # Caminho do perfil VT PJE alternativo
    print("\n5. Caminho do perfil VT PJE alternativo:")
    print("   Exemplo: C:\\Users\\SeuUsuario\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\outro.perfil")
    vt_alt_atual = keyring.get_password('pjeplus_paths', 'VT_PROFILE_PJE_ALT')
    if vt_alt_atual:
        print(f"   Configurado atualmente: {vt_alt_atual}")

    novo_vt_alt = input("   Digite o novo caminho (ou Enter para manter): ").strip()
    if novo_vt_alt and os.path.exists(novo_vt_alt):
        configurar_caminho_credencial('VT_PROFILE_PJE_ALT', novo_vt_alt)
        print("   ✓ Caminho do perfil VT PJE alternativo configurado com sucesso!")
    elif novo_vt_alt:
        print("   ✗ Caminho inválido, mantendo configuração atual")

    # Caminho do Firefox alternativo
    print("\n6. Caminho do executável do Firefox alternativo:")
    print("   Exemplo: C:\\Users\\SeuUsuario\\AppData\\Local\\Firefox Developer Edition\\firefox.exe")
    exe_alt_atual = keyring.get_password('pjeplus_paths', 'FIREFOX_BINARY_ALT')
    if exe_alt_atual:
        print(f"   Configurado atualmente: {exe_alt_atual}")

    novo_exe_alt = input("   Digite o novo caminho (ou Enter para manter): ").strip()
    if novo_exe_alt and os.path.exists(novo_exe_alt):
        configurar_caminho_credencial('FIREFOX_BINARY_ALT', novo_exe_alt)
        print("   ✓ Caminho do executável do Firefox alternativo configurado com sucesso!")
    elif novo_exe_alt:
        print("   ✗ Caminho inválido, mantendo configuração atual")

    print("\n" + "=" * 50)
    print("Configuração concluída!")
    print("\nConfiguração atual:")
    exibir_configuracao_atual()

def exibir_configuracao():
    """Exibe a configuração atual"""
    print("Configuração atual de caminhos")
    print("=" * 50)
    exibir_configuracao_atual()

def mostrar_opcoes():
    """Mostra as opções disponíveis"""
    print("Opções:")
    print("  1. Configurar caminhos (interativo)")
    print("  2. Exibir configuração atual")
    print("  3. Sair")

if __name__ == "__main__":
    print("PJePlus - Configuração de Caminhos")
    print("=" * 50)

    while True:
        mostrar_opcoes()
        escolha = input("\nEscolha uma opção (1-3): ").strip()

        if escolha == "1":
            configurar_caminhos_interativo()
            break
        elif escolha == "2":
            exibir_configuracao()
            input("\nPressione Enter para continuar...")
        elif escolha == "3":
            print("Saindo...")
            break
        else:
            print("Opção inválida. Por favor, escolha 1, 2 ou 3.")