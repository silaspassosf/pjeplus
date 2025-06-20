#!/usr/bin/env python3
# ajustar_coordenadas.py
"""
Script para ajustar coordenadas do AutoHotkey no SISBAJUD
"""

def main():
    print("🎯 AJUSTE DE COORDENADAS - SISBAJUD")
    print("=" * 50)
    print()
    
    print("📋 COORDENADAS ATUAIS NO SCRIPT:")
    print("   Campo CPF: X=1050, Y=181")
    print("   Campo Senha: X=1050, Y=254") 
    print("   Botão Entrar: X=1177, Y=305")
    print()
    
    print("🔧 COMO AJUSTAR AS COORDENADAS:")
    print("1. Execute o script loginsisb.ahk")
    print("2. Pressione F5 para mostrar posição do mouse")
    print("3. Mova o mouse sobre cada campo e anote as coordenadas")
    print("4. Ajuste as coordenadas no script se necessário")
    print()
    
    print("🧪 TESTES DISPONÍVEIS:")
    print("   F1: Login completo")
    print("   F2: Apenas CPF")
    print("   F3: Apenas senha")
    print("   F4: Apenas botão Entrar")
    print("   F5: Mostrar coordenadas do mouse")
    print("   F6: Teste de digitação")
    print()
    
    print("💡 DICAS:")
    print("• Mantenha o SISBAJUD na mesma posição/tamanho")
    print("• Use resolução de tela consistente") 
    print("• Teste cada função individualmente")
    print("• Se não funcionar, ajuste as coordenadas")
    print()
    
    print("🎯 BASEADO NA IMAGEM FORNECIDA:")
    print("• Campo CPF está no canto superior direito")
    print("• Campo senha está logo abaixo do CPF")
    print("• Botão Entrar é azul e está à direita")
    print()
    
    input("Pressione Enter para continuar...")

if __name__ == "__main__":
    main()
