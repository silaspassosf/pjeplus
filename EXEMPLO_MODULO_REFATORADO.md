# 📋 EXEMPLO DE MÓDULO REFATORADO - setup_driver.py

## 🎯 **OBJETIVO**
Demonstrar como será a estrutura de um módulo refatorado, mantendo total compatibilidade com o código original.

## 📄 **CONTEÚDO DO MÓDULO**

```python
# mdd_modulos/setup_driver.py
"""
Módulo responsável pelo setup e configuração inicial do driver Selenium.

Responsabilidades:
- Configuração inicial do driver
- Limpeza de arquivos temporários
- Preparação do ambiente de automação

Funções extraídas do m1.py:
- setup_driver()
"""

import time
import os
from Fix import limpar_temp_selenium
from driver_config import criar_driver

def setup_driver():
    """
    Setup inicial do driver e limpeza.
    
    Returns:
        webdriver: Instância do driver configurado ou None em caso de erro
    """
    limpar_temp_selenium()
    driver = criar_driver(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return None
    return driver
```

## 🔄 **EXEMPLO DE MÓDULO COMPLEXO - argos_regras.py**

```python
# mdd_modulos/argos_regras.py
"""
Módulo responsável pelas regras de negócio específicas do fluxo Argos.

Responsabilidades:
- Aplicação de regras baseadas em SISBAJUD
- Lógica de prioridades e precedência
- Criação de lembretes
- Execução de atos judiciais

Funções extraídas do m1.py:
- aplicar_regras_argos()
- lembrete_bloq()
"""

import re
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from Fix import safe_click, wait_for_visible, sleep
from atos import ato_bloq, ato_meios, ato_termoS, pec_idpj, ato_meiosub
from p2 import checar_prox

def lembrete_bloq(driver, debug=False):
    """
    Cria lembrete de bloqueio com título "Bloqueio pendente" e conteúdo "processar após IDPJ".
    
    Args:
        driver: Instância do WebDriver
        debug (bool): Se True, imprime logs de debug
    """
    try:
        if debug:
            print('[ARGOS][LEMBRETE] Criando lembrete de bloqueio...')
            
        # 1. Clique no menu (fa-bars)
        menu_clicked = safe_click(driver, '.fa-bars', log=debug)
        if not menu_clicked and debug:
            print('[ARGOS][LEMBRETE] Falha ao clicar no menu')
        sleep(1000)
        
        # 2. Clique no ícone de lembrete
        lembrete_selector = '.lista-itens-menu > li:nth-child(16) > pje-icone-post-it:nth-child(1) > li:nth-child(1) > button:nth-child(1)'
        lembrete_clicked = safe_click(driver, lembrete_selector, log=debug)
        if not lembrete_clicked and debug:
            print('[ARGOS][LEMBRETE] Falha ao clicar no ícone de lembrete')
        sleep(1000)
        
        # 3. Preenche formulário
        dialog_clicked = safe_click(driver, '.mat-dialog-content', log=debug)
        sleep(1000)
        
        # 4. Preenche título
        titulo = wait_for_visible(driver, '#tituloPostit', timeout=5)
        if titulo:
            titulo.clear()
            titulo.send_keys('Bloqueio pendente')
        
        # 5. Preenche conteúdo
        conteudo = wait_for_visible(driver, '#conteudoPostit', timeout=5)
        if conteudo:
            conteudo.clear()
            conteudo.send_keys('processar após IDPJ')
        
        # 6. Salva
        salvar_clicked = safe_click(driver, 'button.mat-raised-button:nth-child(1)', log=debug)
        sleep(1000)
        
        if debug:
            print('[ARGOS][LEMBRETE] Lembrete criado com sucesso.')
            
    except Exception as e:
        if debug:
            print(f'[ARGOS][LEMBRETE][ERRO] Falha ao criar lembrete: {e}')
        raise

def aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """
    Aplica as regras específicas do Argos com base no resultado do SISBAJUD, sigilo dos anexos e tipo de documento.
    
    Args:
        driver: Instância do WebDriver
        resultado_sisbajud (str): Resultado do SISBAJUD ('positivo' ou 'negativo')
        sigilo_anexos (dict): Dicionário com status de sigilo dos anexos
        tipo_documento (str): Tipo do documento ('despacho' ou 'decisao')
        texto_documento (str): Texto completo do documento
        debug (bool): Se True, imprime logs de debug
    """
    try:
        regra_aplicada = None
        trecho_relevante = texto_documento if texto_documento else ''
        
        if debug:
            print(f'[ARGOS][REGRAS] Analisando regras para tipo: {tipo_documento}')
            print(f'[ARGOS][REGRAS] Resultado SISBAJUD: {resultado_sisbajud}')
            print(f'[ARGOS][REGRAS] Sigilo anexos: {sigilo_anexos}')
        
        # PRIORIDADE MÁXIMA: Despacho com palavra "ARGOS"
        if tipo_documento == 'despacho' and texto_documento and 'argos' in texto_documento.lower():
            regra_aplicada = '[PRIORIDADE MÁXIMA] despacho+argos'
            if debug:
                print('[ARGOS][REGRAS] NOVA REGRA: Despacho com ARGOS detectado')
            
            if resultado_sisbajud == 'positivo':
                regra_aplicada += ' | sisbajud positivo => ato_bloq'
                if debug:
                    print('[ARGOS][REGRAS] ARGOS: SISBAJUD positivo, executando ato_bloq')
                ato_bloq(driver, debug=debug)
            elif resultado_sisbajud == 'negativo':
                tem_sigiloso = any(v == 'sim' for v in sigilo_anexos.values()) if sigilo_anexos else False
                if tem_sigiloso:
                    regra_aplicada += ' | sisbajud negativo, com sigiloso => ato_termoS'
                    if debug:
                        print('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo com anexo sigiloso, executando ato_termoS')
                    ato_termoS(driver, debug=debug)
                else:
                    regra_aplicada += ' | sisbajud negativo, sem sigiloso => ato_meios'
                    if debug:
                        print('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo sem anexo sigiloso, executando ato_meios')
                    ato_meios(driver, debug=debug)
            
            print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\\nTrecho considerado: {trecho_relevante}')
            return
        
        # PRIORIDADE ABSOLUTA: "defiro a instauração" com SISBAJUD positivo
        if 'defiro a instauração' in texto_documento.lower() and resultado_sisbajud == 'positivo':
            regra_aplicada = '[PRIORIDADE] decisao+defiro a instauracao+sisbajud positivo'
            if debug:
                print('[ARGOS][REGRAS][PRIORIDADE] ✅ REGRA DE PRECEDÊNCIA: defiro a instauração + SISBAJUD positivo')
            
            regra_aplicada += ' | lembrete_bloq + pec_idpj [PRECEDENCIA ABSOLUTA]'
            lembrete_bloq(driver, debug=debug)
            pec_idpj(driver, debug=debug)
            
            print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\\nTrecho considerado: {trecho_relevante}')
            return
        
        # [... outras regras seguem o mesmo padrão ...]
        
        # Log da regra aplicada
        print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\\nTrecho considerado: {trecho_relevante}')
        
    except Exception as e:
        if debug:
            print(f'[ARGOS][REGRAS][ERRO] Falha ao aplicar regras: {e}')
        raise
```

## 📄 **ORQUESTRADOR mdd.py**

```python
# mdd.py - Arquivo principal
"""
Orquestrador principal do sistema MDD (Mandados).

Este arquivo substitui o m1.py original, mantendo total compatibilidade
mas com código organizado em módulos menores.
"""

import sys
import os
from datetime import datetime

# Importações dos módulos internos
from mdd_modulos import (
    setup_driver,
    navegacao,
    argos_core,
    outros_core
)

# Importações externas preservadas (idênticas ao m1.py original)
from Fix import (
    navegar_para_tela,
    extrair_pdf,
    analise_outros,
    extrair_documento,
    criar_gigs,
    esperar_elemento,
    safe_click,
    wait,
    wait_for_visible,
    wait_for_clickable,
    sleep,
    buscar_seletor_robusto,
    limpar_temp_selenium,
    driver_pc,
    indexar_e_processar_lista,
    extrair_dados_processo,
    buscar_documento_argos,
    buscar_mandado_autor,
    buscar_ultimo_mandado,
    validar_conexao_driver,
)

from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj,
    mov_arquivar,
    ato_meiosub
)

from p2 import checar_prox
from driver_config import criar_driver, login_func

# Log inicial (preservado do original)
with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\\n")

def fluxo_mandado(driver):
    """
    Percorre a lista de processos e executa o fluxo adequado (Argos ou Outros) para cada mandado.
    Função delegada para o módulo de navegação.
    """
    return navegacao.fluxo_mandado(driver)

def main():
    """
    Função principal que coordena todo o fluxo do programa.
    1. Setup inicial (driver e limpeza)
    2. Login humanizado
    3. Navegação para a lista de documentos internos
    4. Execução do fluxo automatizado sobre a lista
    """
    # Setup inicial
    driver = setup_driver.setup_driver()
    if not driver:
        return

    # Login process
    if not login_func(driver):
        driver.quit()
        return

    # Navegação para a lista de documentos internos
    if not navegacao.navegacao(driver):
        driver.quit()
        return

    # Processa a lista de documentos internos
    fluxo_mandado(driver)

    print("[INFO] Processamento concluído. Pressione ENTER para encerrar...")
    input()
    driver.quit()

if __name__ == "__main__":
    main()
```

## 🔧 **VANTAGENS DA ESTRUTURA MODULAR**

### **1. Manutenibilidade**
- ✅ Cada módulo tem responsabilidade única
- ✅ Código mais legível e organizado
- ✅ Facilita localização de bugs
- ✅ Reduz complexidade cognitiva

### **2. Testabilidade**
- ✅ Módulos podem ser testados isoladamente
- ✅ Mocking de dependências facilitado
- ✅ Cobertura de testes mais granular
- ✅ Debugging mais eficiente

### **3. Reutilização**
- ✅ Funções podem ser reutilizadas em outros projetos
- ✅ Módulos independentes
- ✅ API interna bem definida
- ✅ Facilita extensões futuras

### **4. Desenvolvimento em Equipe**
- ✅ Equipe pode trabalhar em módulos separados
- ✅ Conflitos de merge reduzidos
- ✅ Revisão de código mais focada
- ✅ Onboarding de novos desenvolvedores facilitado

---

**Este exemplo demonstra como será a estrutura final após a refatoração, mantendo 100% de compatibilidade com o código original.**
