import time
from driver_config import criar_driver_PC, login_automatico
from sisb import minuta_bloqueio

# Criar driver e fazer login automático
driver = criar_driver_PC()
login_automatico(driver)

# Navegar para a URL específica do processo
url_processo = "https://pje.trt2.jus.br/pjekz/processo/3583425/detalhe"
print(f"[TESTE] Navegando para: {url_processo}")
driver.get(url_processo)
time.sleep(3)  # Aguarda carregamento

# Executar função de minuta de bloqueio do sisb.py diretamente
print("[TESTE] Executando minuta de bloqueio SISBAJUD...")
try:
    resultado = minuta_bloqueio(driver_pje=driver, dados_processo=None)
    if resultado:
        print("[TESTE] ✅ Minuta de bloqueio criada com sucesso")
    else:
        print("[TESTE] ❌ Falha na criação da minuta de bloqueio")
except Exception as e:
    print(f"[TESTE] ❌ Erro durante execução: {e}")

# Manter driver aberto por alguns segundos para verificação
time.sleep(5)

# Fechar driver
driver.quit()
print("[TESTE] Script finalizado")