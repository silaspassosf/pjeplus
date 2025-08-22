import time
from driver_config import criar_driver_PC, login_automatico
from sisb import iniciar_sisbajud, _processar_ordem

# 1. Criar driver e fazer login automático
driver = criar_driver_PC()
login_automatico(driver)

# 2. Navegar para a URL específica do processo
url_processo = "https://pje.trt2.jus.br/pjekz/processo/6203803/detalhe"
print(f"[TESTE] Navegando para: {url_processo}")
driver.get(url_processo)
time.sleep(3)  # Aguarda carregamento

# 3. Executar iniciar_sisbajud
print("[TESTE] Executando iniciar_sisbajud...")
try:
    driver_sisbajud = iniciar_sisbajud(driver)
    print("[TESTE] ✅ SISBAJUD inicializado")
except Exception as e:
    print(f"[TESTE] ❌ Erro ao inicializar SISBAJUD: {e}")

# 4. Executar _processar_ordem
print("[TESTE] Executando _processar_ordem...")
try:
    # Exemplo de ordem e tipo_fluxo para teste
    ordem = {'sequencial': 1, 'linha_el': None}  # Substitua por uma ordem real se necessário
    tipo_fluxo = 'POSITIVO'  # Ou 'DESBLOQUEIO'
    _processar_ordem(driver_sisbajud, ordem, tipo_fluxo, log=True)
    print("[TESTE] ✅ _processar_ordem executada")
except Exception as e:
    print(f"[TESTE] ❌ Erro durante execução de _processar_ordem: {e}")

# Manter driver aberto por alguns segundos para verificação
time.sleep(5)

# Fechar driver
driver.quit()
print("[TESTE] Script finalizado")