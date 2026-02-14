#!/usr/bin/env python3
"""
ARQUITETURA DE LOGGING LIMPA - FIX PROJECT
=============================================

Princípios:
  1. Logs CRÍTICOS apenas (erro, sucesso, mudanças de estado)
  2. Sem emojis, sem print(), standardizado em logger
  3. Níveis: ERROR, WARNING, INFO (sem DEBUG em produção)
  4. Sem logs de ações triviais (cada scroll, clique individual, etc)

# Exemplo de arquivo limpo:

    import logging
    logger = logging.getLogger(__name__)

    def aguardar_e_clicar_v3(driver, seletor, timeout=10):
        '''Clique inteligente com auto-detecção.'''
        try:
            elemento = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
            elemento.click()
            return True
        except TimeoutException:
            logger.error(f"Clique falhou: {seletor} (timeout {timeout}s)")
            return False
        except Exception as e:
            logger.error(f"Clique falhou: {seletor} - {e}")
            return False

    def diagnosticar_falha(driver, seletor):
        '''Log COMPLETO apenas quando necessário debugar.'''
        elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
        logger.warning(f"Diagnóstico: {seletor} - {len(elementos)} encontrados, visível={elementos[0].is_displayed() if elementos else False}")

=============================================================================
MAPA DE LOGGING POR CENÁRIO
=============================================================================

CENÁRIO 1: Sucesso
  FAZER: logger.info("Clique bem-sucedido: #botao")
  NÃO: print cada micro-ação

CENÁRIO 2: Falha crítica
  FAZER: logger.error("Clique falhou: seletor não encontrado")
  NÃO: logger.debug de cada tentativa falhada

CENÁRIO 3: Fallback para alternativa
  FAZER: logger.warning("JS click falhou, tentando scroll+click")
  NÃO: print("tentativa 1...", "tentativa 2...", etc)

CENÁRIO 4: Debug específico (temporário)
  FAZER: logger.info(diagnosticar_falha(driver, seletor))
  NÃO: logger.debug em cada linha da função

=============================================================================
PADRÃO DE BLOCO DE TENTATIVAS (SEM LOGS TRIVIAIS)
=============================================================================

# ❌ ANTES (verboso - 15 linhas de log):
def clicar_com_fallbacks(driver, seletor):
    logger.debug(f"Tentativa 1: JS click")
    try:
        js_click(driver, seletor)
        logger.debug(f"✓ Sucesso: JS click")
        return True
    except Exception as e:
        logger.debug(f"✗ Falhou: JS click - {e}")
    
    logger.debug(f"Tentativa 2: Scroll + click")
    try:
        scroll_e_click(driver, seletor)
        logger.debug(f"✓ Sucesso: scroll+click")
        return True
    except Exception as e:
        logger.debug(f"✗ Falhou: scroll+click - {e}")
    
    logger.debug(f"Tentativa 3: Selenium click")
    try:
        selenium_click(driver, seletor)
        logger.debug(f"✓ Sucesso: selenium click")
        return True
    except Exception as e:
        logger.debug(f"✗ Falhou: selenium click - {e}")
    
    logger.error(f"Clique falhou em todas tentativas")
    return False


# ✅ DEPOIS (limpo - 1 log crítico):
def clicar_com_fallbacks(driver, seletor):
    estrategias = [
        ("js_click", lambda: js_click(driver, seletor)),
        ("scroll_e_click", lambda: scroll_e_click(driver, seletor)),
        ("selenium_click", lambda: selenium_click(driver, seletor)),
    ]
    
    for nome, funcao in estrategias:
        try:
            if funcao():
                return True
        except Exception:
            pass
    
    logger.error(f"Clique falhou em todas {len(estrategias)} estratégias: {seletor}")
    return False

=============================================================================
PADRÃO PARA PROCESSAMENTO EM LOOP (SEM RUÍDO)
=============================================================================

# ❌ ANTES (log a cada iteração):
def processar_links(driver, links):
    for i, link in enumerate(links):
        logger.debug(f"Iteração {i}/{len(links)}: {link}")
        print(f"Acessando link {i}...")
        try:
            acessar_link(driver, link)
            print(f"✓ Link acessado")
            logger.debug(f"Sucesso no link")
        except Exception as e:
            print(f"✗ Erro: {e}")
            logger.debug(f"Erro ao acessar link")
    logger.info(f"Processamento finalizado")


# ✅ DEPOIS (log apenas checkpoints):
def processar_links(driver, links):
    sucesso = 0
    falhas = []
    
    for link in links:
        try:
            acessar_link(driver, link)
            sucesso += 1
        except Exception as e:
            falhas.append((link, str(e)))
    
    logger.info(f"Processamento: {sucesso}/{len(links)} sucesso, {len(falhas)} falhas")
    if falhas:
        logger.warning(f"Falhas: {', '.join(f[0] for f in falhas[:3])}")

=============================================================================
SETUP DE LOGGING NO __INIT__ DO PROJETO
=============================================================================

# Fix/__init__.py

import logging
import logging.handlers
from pathlib import Path

# Criar pasta de logs se não existir
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configurar logger principal
logger = logging.getLogger("Fix")
logger.setLevel(logging.INFO)  # INFO em produção, DEBUG em desenvolvimento

# Handler para arquivo (sem emojis, formatado)
file_handler = logging.FileHandler(LOG_DIR / "fix.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)

# Handler para console (minimalista)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)  # Apenas aviso/erro no console
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)

# Adicionar handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Silenciar bibliotecas verbosas
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

__all__ = ["logger"]

=============================================================================
CHECKLIST DE LIMPEZA PARA CADA FUNÇÃO
=============================================================================

ANTES de refatorar uma função:

  [ ] Remover todos print() - converter para logger.info/error
  [ ] Remover todos logger.debug() - manter apenas info/error
  [ ] Remover emojis (✓❌⚠️🔄)
  [ ] Remover linhas decorativas (print("=" * 60))
  [ ] Logs de entrada (logger.info("Iniciando função...")) → REMOVER
  [ ] Logs de saída (logger.info("Finalizando função...")) → REMOVER
  [ ] Logs de cada iteração em loops → Juntar em summary
  [ ] Logs de tentativas individuais → Juntar em resultado final
  [ ] Verificar função é legível após limpeza
  [ ] Testar que não quebraram funcionalidades críticas

=============================================================================
# EXEMPLOS DE CONVERSÃO REAIS
=============================================================================

# EXEMPLO 1: Função com loops verbosos
# ---

# ANTES:
def processar_dados(items):
    logger.debug("Iniciando processamento")
    print("=" * 50)
    print("PROCESSAMENTO INICIADO")
    print("=" * 50)
    
    for i, item in enumerate(items):
        print(f"Processando {i}/{len(items)}: {item}")
        logger.debug(f"Item {i}: iniciando")
        try:
            resultado = processar_item(item)
            logger.debug(f"Item {i}: sucesso")
            print(f"✓ Item {i} processado")
        except Exception as e:
            logger.debug(f"Item {i}: falha")
            print(f"✗ Item {i}: {e}")
    
    logger.debug("Processamento finalizado")
    print("=" * 50)
    print("PROCESSAMENTO FINALIZADO")
    print("=" * 50)

# DEPOIS:
def processar_dados(items):
    processados = 0
    erros = []
    
    for item in items:
        try:
            processar_item(item)
            processados += 1
        except Exception as e:
            erros.append((item, str(e)))
    
    logger.info(f"Processamento concluído: {processados}/{len(items)} sucesso")
    if erros:
        logger.warning(f"Erros em {len(erros)} items")

# ---

# EXEMPLO 2: Função com tentativas de clique
# ---

# ANTES:
def clicar(driver, seletor):
    logger.debug(f"Tentativa de clique: {seletor}")
    print(f"Clicando em {seletor}")
    
    # Estratégia 1
    try:
        logger.debug("Tentativa 1: JS click")
        elemento = driver.find_element(By.CSS_SELECTOR, seletor)
        driver.execute_script("arguments[0].click();", elemento)
        logger.debug("✓ Sucesso")
        print("✓ JS click funcionou")
        return True
    except Exception as e:
        logger.debug(f"✗ Falhou: {e}")
        print(f"✗ JS click falhou: {e}")
    
    # Estratégia 2
    try:
        logger.debug("Tentativa 2: Selenium click")
        elemento = driver.find_element(By.CSS_SELECTOR, seletor)
        elemento.click()
        logger.debug("✓ Sucesso")
        print("✓ Selenium click funcionou")
        return True
    except Exception as e:
        logger.debug(f"✗ Falhou: {e}")
        print(f"✗ Selenium click falhou: {e}")
    
    logger.error(f"Clique falhou: {seletor}")
    print(f"✗ Clique falhou")
    return False

# DEPOIS:
def clicar(driver, seletor):
    estrategias = [
        lambda: driver.execute_script(f"document.querySelector('{seletor}').click();"),
        lambda: driver.find_element(By.CSS_SELECTOR, seletor).click(),
    ]
    
    for estrategia in estrategias:
        try:
            estrategia()
            return True
        except Exception:
            pass
    
    logger.error(f"Clique falhou: {seletor}")
    return False

# ---

# EXEMPLO 3: Diagnóstico detalhado (mantém log completo)
# ---

# Usar quando necessário debugar, colocar em função separate:
def diagnosticar_elemento(driver, seletor):
    '''Retorna diagnóstico COMPLETO - chamar apenas se debug necessário.'''
    try:
        elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
        if elementos:
            elem = elementos[0]
            return {
                "encontrado": True,
                "quantidade": len(elementos),
                "visivel": elem.is_displayed(),
                "habilitado": elem.is_enabled(),
                "tag": elem.tag_name,
                "texto": elem.text[:50],
            }
        else:
            return {"encontrado": False, "quantidade": 0}
    except Exception as e:
        return {"erro": str(e)}

# Usar em função de processamento:
def processar_com_debug(driver, seletor):
    sucesso = clicar(driver, seletor)
    if not sucesso:
        diagnostico = diagnosticar_elemento(driver, seletor)
        logger.warning(f"Clique falhou - Diagnóstico: {diagnostico}")
    return sucesso

=============================================================================
MIGRAÇÃO PASSO A PASSO
=============================================================================

PASSO 1: Backup
  $ git commit -m "Backup antes de limpeza de logs"
  $ python clean_logs.py Fix/core.py

PASSO 2: Validar
  $ python validate_refactoring.py Fix/

PASSO 3: Testar
  $ python -m pytest tests/ -v
  $ python test_fix_manual.py

PASSO 4: Se erro → restaurar
  $ git checkout Fix/core.py  # OU
  $ cp Fix/core.py.backup Fix/core.py

PASSO 5: Se OK → limpar backups
  $ rm Fix/core.py.backup
  $ git add -A && git commit -m "Limpeza de logs completa"

=============================================================================
PERGUNTAS FREQUENTES
=============================================================================

P: Como saber se log é "crítico" o suficiente?
R: Se você deletasse a linha de log, a função ainda funcionaria exatamente igual?
   Se SIM → provavelmente pode deletar (não é crítico)
   Se NÃO → manter (é informação importante)

P: E se eu precisar debugar um problema futuro?
R: Manter função diagnosticar_xxx() separada que você CHAMA quando preciso
   Não deixar logs de debug sempre ligados

P: Posso usar logger.debug em desenvolvimento?
R: Sim! Configure:
   logger.setLevel(logging.DEBUG)  # em dev
   logger.setLevel(logging.INFO)   # em produção
   
   Assim logs de debug aparecem quando você quer

P: Quantas linhas de log esperado pós-limpeza?
R: Regra de ouro:
   - Arquivo <300 linhas: max 10-15 linhas de logger (5%)
   - Função de loop: 1-2 logs de summary, não por iteração
   - Função simples: 0 logs normais, 1 erro/falha

P: E se quebrar algo?
R: Restaurar de backup:
   $ cp Fix/core.py.backup Fix/core.py
   $ python validate_refactoring.py
   $ git checkout .  # reset git

=============================================================================
"""

print(__doc__)
