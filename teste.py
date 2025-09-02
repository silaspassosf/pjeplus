import time
from driver_config import criar_driver_sisb, exibir_configuracao_ativa

# Importações diretas de sisb.py (sem usar as funções de alto nível)
from sisb import driver_sisbajud, login_automatico_sisbajud, processar_ordem_sisbajud

# 1. Mostrar configuração ativa
exibir_configuracao_ativa()

# 2. Criar driver SISBAJUD diretamente
print("[TESTE] Criando driver SISBAJUD...")
driver_sisbajud = driver_sisbajud()
if not driver_sisbajud:
    print('[TESTE] ❌ Falha ao criar driver SISBAJUD')
    raise SystemExit(1)

# 3. Fazer login automático no SISBAJUD
print("[TESTE] Fazendo login automático no SISBAJUD...")
if not login_automatico_sisbajud(driver_sisbajud):
    print('[TESTE] ❌ Falha no login SISBAJUD')
    try:
        driver_sisbajud.quit()
    except Exception:
        pass
    raise SystemExit(1)

print("[TESTE] ✅ Login SISBAJUD realizado com sucesso")

# 4. Preparar dados do processo correto para SISBAJUD
dados_processo = {
    'numero': '1000996-92.2021.5.02.0703',
    'numero_processo': '1000996-92.2021.5.02.0703'
}

# 5. Executar processar_ordem_sisbajud diretamente
print("[TESTE] Executando processar_ordem_sisbajud com processo 1000996-92.2021.5.02.0703...")
try:
    resultado = processar_ordem_sisbajud(driver_sisbajud, dados_processo, log=True)
    print(f"[TESTE] Resultado: {resultado}")
    print("[TESTE] ✅ processar_ordem_sisbajud executada com sucesso")
except Exception as e:
    print(f"[TESTE] ❌ Erro durante execução de processar_ordem_sisbajud: {e}")

# Manter driver aberto por alguns segundos para verificação
time.sleep(5)

# Nota: processar_ordem_sisbajud irá fechar o driver SISBAJUD ao final do processamento
print("[TESTE] Script finalizado")