import time
from driver_config import criar_driver, login_automatico, exibir_configuracao_ativa
from sisb import iniciar_sisbajud, processar_ordem_sisbajud

# 1. Mostrar configuração ativa e criar driver usando a opção ativa em driver_config
exibir_configuracao_ativa()
driver = criar_driver()
# Verifica se o login automático foi bem-sucedido antes de prosseguir
if not login_automatico(driver):
    print('[TESTE] ❌ Falha no login automático — abortando execução para evitar criação prematura do SISBAJUD')
    try:
        driver.quit()
    except Exception:
        pass
    raise SystemExit(1)

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
print("[TESTE] Executando fluxo orquestrado processar_ordem_sisbajud (autônomo)...")
try:
    # Não passar dados: a função usará o global `processo_dados_extraidos` ou carregará de arquivo
    resultado = processar_ordem_sisbajud(driver_sisbajud, None, log=True)
    print(f"[TESTE] Resultado: {resultado}")
    print("[TESTE] ✅ processar_ordem_sisbajud executada")
except Exception as e:
    print(f"[TESTE] ❌ Erro durante execução de processar_ordem_sisbajud: {e}")

# Manter driver aberto por alguns segundos para verificação
time.sleep(5)

# Nota: processar_ordem_sisbajud irá fechar o driver SISBAJUD ao final do processamento.
print("[TESTE] Script finalizado")