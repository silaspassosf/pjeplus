"""
run_debug_auto.py
Script para execução automática iterativa com debug e correções
"""
import os
import sys
import json
import subprocess
import time
from datetime import datetime


def limpar_progresso():
    """Limpa arquivos de progresso para recomeçar do zero"""
    arquivos = [
        'progresso.json',
    ]
    
    for arq in arquivos:
        if os.path.exists(arq):
            try:
                os.remove(arq)
                print(f"[LIMPAR] Removido: {arq}")
            except Exception as e:
                print(f"[AVISO] Erro ao remover {arq}: {e}")


def executar_x_py_auto():
    """
    Executa x.py em modo automático com inputs pré-definidos
    DD = VT Headless + Debug
    A = Bloco Completo
    """
    print("\n" + "=" * 80)
    print("[AUTO] EXECUTANDO X.PY EM MODO DEBUG AUTOMATICO")
    print("=" * 80)
    print("Configuracao:")
    print("  - Ambiente: VT Headless + Debug (DD)")
    print("  - Fluxo: Bloco Completo (A)")
    print("  - Modo: Automatico (fixes aplicados sem input)")
    print("=" * 80 + "\n")
    
    # Preparar inputs
    inputs = "DD\nA\nn\n"  # DD (VT Headless Debug), A (Bloco Completo), n (não continuar)
    
    try:
        # Executar com timeout de 30 minutos
        processo = subprocess.Popen(
            ['py', '-3', 'x.py'],  # Usar launcher py do Windows
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Enviar inputs
        stdout, _ = processo.communicate(input=inputs, timeout=1800)
        
        # Mostrar output
        print(stdout)
        
        return processo.returncode, stdout
        
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] Execucao excedeu 30 minutos")
        processo.kill()
        return -1, ""
    except Exception as e:
        print(f"[ERRO] Erro na execucao: {e}")
        return -1, str(e)


def analisar_logs_debug():
    """Analisa logs de debug gerados"""
    debug_dir = 'debug_interativo'
    
    if not os.path.exists(debug_dir):
        print("[INFO] Nenhum erro de debug registrado")
        return []
    
    erros = []
    
    # Listar relatórios JSON
    for arquivo in os.listdir(debug_dir):
        if arquivo.endswith('_relatorio.json'):
            caminho = os.path.join(debug_dir, arquivo)
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    erro = json.load(f)
                    erros.append(erro)
            except:
                pass
    
    if erros:
        print("\n" + "=" * 80)
        print("[ANALISE] ERROS DETECTADOS")
        print("=" * 80)
        print(f"Total de erros: {len(erros)}")
        
        for idx, erro in enumerate(erros, 1):
            print(f"\n[{idx}] {erro.get('mensagem', '')[:100]}...")
            print(f"    Contexto: {erro.get('contexto', {})}")
            print(f"    Screenshot: {erro.get('screenshot', 'N/A')}")
            print(f"    Overlays: {erro.get('overlays_count', 0)}")
    
    return erros


def main():
    """Execução principal iterativa"""
    max_iteracoes = 5
    iteracao = 1
    
    print("[INICIO] CICLO DE DEBUG AUTOMATICO ITERATIVO")
    print(f"Maximo de iteracoes: {max_iteracoes}\n")
    
    while iteracao <= max_iteracoes:
        print("\n" + "=" * 80)
        print(f"[ITERACAO {iteracao}/{max_iteracoes}]")
        print("=" * 80)
        
        # 1. Limpar progresso
        print("\n[1/3] Limpando arquivos de progresso...")
        limpar_progresso()
        time.sleep(1)
        
        # 2. Executar x.py
        print("\n[2/3] Executando x.py...")
        returncode, output = executar_x_py_auto()
        
        # 3. Analisar resultados
        print("\n[3/3] Analisando resultados...")
        erros = analisar_logs_debug()
        
        # Verificar se houve erros críticos
        if not erros:
            print("\n[SUCESSO] Nenhum erro critico detectado.")
            print("Execucao completada sem problemas.")
            break
        
        # Se ainda há erros, continuar iterando
        print(f"\n[AVISO] Encontrados {len(erros)} erro(s)")
        print(f"Fixes automaticos foram aplicados.")
        print(f"Reexecutando na proxima iteracao...\n")
        
        iteracao += 1
        time.sleep(2)
    
    if iteracao > max_iteracoes:
        print("\n[AVISO] Limite de iteracoes atingido")
        print("Verifique erros persistentes em: debug_interativo/")
    
    print("\n" + "=" * 80)
    print("[FIM] CICLO DE DEBUG CONCLUIDO")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERROMPIDO] Usuario cancelou execucao")
        sys.exit(1)
