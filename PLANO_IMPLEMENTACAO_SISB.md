# PLANO DE IMPLEMENTAÇÃO - REFATORAÇÃO BACEN.PY

## PROJETO APROVADO ✅

### Estrutura Final
```
d:\PjePlus\
├── sisb.py                     # Orquestrador principal (~100 linhas)
├── bacen.py                    # Arquivo original (backup)
├── sisb_modulos/
│   ├── __init__.py
│   ├── config.py              # Configurações (~150 linhas)
│   ├── drivers.py             # Drivers Selenium (~400 linhas)
│   ├── cookies.py             # Gestão de cookies (~200 linhas)
│   ├── interface_pje.py       # Interface PJe (~300 linhas)
│   ├── dados_processo.py      # Dados do processo (~250 linhas)
│   ├── sisbajud_core.py       # Core SISBAJUD (~350 linhas)
│   ├── kaizen_interface.py    # Interface Kaizen (~400 linhas)
│   ├── preenchimento.py       # Preenchimento (~400 linhas)
│   ├── bloqueios.py           # Processamento (~300 linhas)
│   ├── minutas.py             # Operações minutas (~250 linhas)
│   └── utils.py               # Utilitários (~200 linhas)
```

## DISTRIBUIÇÃO DE FUNÇÕES POR MÓDULO

### 1. `sisb.py` (Orquestrador)
- `main()` - Função principal
- `executar_modo_completo()` - Modo PJe + SISBAJUD
- `executar_modo_sisbajud()` - Modo apenas SISBAJUD
- `executar_modo_teste()` - Modo teste
- `executar_driver_pje()` - Driver PJe
- `executar_driver_sisbajud()` - Driver SISBAJUD
- Funções de compatibilidade

### 2. `config.py` (Configurações)
- `CONFIG` - Dicionário de configurações
- `FIREFOX_CONFIG` - Configurações Firefox
- `COOKIES_CONFIG` - Configurações cookies
- `URLS` - URLs do sistema
- `TIMEOUTS` - Timeouts
- `SELETORES` - Seletores CSS
- `MENSAGENS` - Mensagens do sistema
- Funções de configuração

### 3. `drivers.py` (Drivers)
- `driver_firefox_sisbajud()` - Driver Firefox original
- `criar_driver_firefox_sisb()` - Driver Firefox SISB
- Configurações de perfis
- Gestão de sessões

### 4. `cookies.py` (Cookies)
- `salvar_cookies_sisbajud()` - Salvar cookies
- `carregar_cookies_sisbajud()` - Carregar cookies
- Filtragem de cookies
- Validação de domínios

### 5. `interface_pje.py` (Interface PJe)
- `injetar_botao_sisbajud_pje()` - Injetar botão
- `prompt_js()` - Prompt JavaScript
- `bind_eventos()` - Eventos
- `checar_evento()` - Verificar eventos

### 6. `dados_processo.py` (Dados Processo)
- `salvar_dados_processo_temp()` - Salvar dados
- `carregar_dados_processo_temp()` - Carregar dados
- `integrar_storage_processo()` - Integrar storage
- Persistência de dados

### 7. `sisbajud_core.py` (Core SISBAJUD)
- `abrir_sisbajud_em_firefox_sisbajud()` - Abrir SISBAJUD
- `executar_driver_sisbajud()` - Executar driver
- `aguardar_login_manual_sisbajud()` - Login manual
- `tentar_login_automatico_ahk()` - Login AHK
- `obter_caminho_autohotkey()` - Caminho AHK
- `main_teste_sisbajud()` - Teste SISBAJUD

### 8. `kaizen_interface.py` (Interface Kaizen)
- `injetar_menu_kaizen_sisbajud()` - Injetar menu
- `checar_kaizen_evento()` - Verificar eventos
- `aguardar_tela_minuta_e_injetar_menu()` - Aguardar tela
- `processar_evento_kaizen()` - Processar eventos
- `kaizen_guardar_senha()` - Guardar senha

### 9. `preenchimento.py` (Preenchimento)
- `kaizen_preencher_campos()` - Preencher campos
- `_preencher_juiz_solicitante()` - Juiz solicitante
- `_preencher_vara_juizo()` - Vara juízo
- `_preencher_numero_processo()` - Número processo
- `_preencher_tipo_acao()` - Tipo ação
- `_preencher_cpf_autor()` - CPF autor
- `_preencher_nome_autor()` - Nome autor
- `_preencher_teimosinha()` - Teimosinha
- `_preencher_endereco_opcoes()` - Endereço opções
- `_verificar_requisicao_endereco()` - Verificar endereço
- `escolher_opcao_sisbajud()` - Escolher opção
- `escolher_opcao_sisbajud_avancado()` - Escolher opção avançada

### 10. `bloqueios.py` (Bloqueios)
- `processar_bloqueios()` - Processar bloqueios
- `_aplicar_cores_status_bloqueio()` - Aplicar cores
- `_buscar_linhas_jun_2025()` - Buscar linhas JUN 2025

### 11. `minutas.py` (Minutas)
- `minuta_bloqueio()` - Minuta bloqueio
- `minuta_endereco()` - Minuta endereço
- `kaizen_nova_minuta()` - Nova minuta
- `kaizen_consultar_minuta()` - Consultar minuta
- `kaizen_consultar_teimosinha()` - Consultar teimosinha
- `kaizen_consulta_rapida()` - Consulta rápida

### 12. `utils.py` (Utilitários)
- `dados_login()` - Dados login
- `monitor_janela_sisbajud()` - Monitor janela
- `monitorar_driver_sisbajud()` - Monitorar driver
- `monitorar_drivers_completo()` - Monitorar completo
- Funções auxiliares

## COMPATIBILIDADE GARANTIDA

### Importações Mantidas
- ✅ `from Fix import extrair_dados_processo`
- ✅ `from driver_config import criar_driver, login_func`
- ✅ Todas as importações Selenium
- ✅ Todas as importações padrão Python

### Variáveis Globais
- ✅ `processo_dados_extraidos`
- ✅ `login_ahk_executado`
- ✅ `CONFIG`

### Funcionalidades
- ✅ Todas as 47 funções originais
- ✅ Fluxos de execução idênticos
- ✅ Comportamento preservado
- ✅ Parâmetros mantidos

## VANTAGENS DA REFATORAÇÃO

### 1. **Organização**
- Código dividido em módulos lógicos
- Fácil localização de funcionalidades
- Estrutura clara e intuitiva

### 2. **Manutenibilidade**
- Módulos ≤ 400 linhas
- Responsabilidades bem definidas
- Debug mais eficiente

### 3. **Escalabilidade**
- Fácil adição de novos recursos
- Modificações isoladas
- Testes unitários possíveis

### 4. **Reutilização**
- Módulos importáveis individualmente
- Funcionalidades compartilhadas
- Integração com outros scripts

## EXECUÇÃO APÓS REFATORAÇÃO

### Comandos Mantidos
```bash
# Execução completa (igual ao bacen.py original)
python sisb.py

# Modo apenas SISBAJUD
python sisb.py  # Opção 2 no menu

# Modo teste
python sisb.py  # Opção 3 no menu
```

### Importações Permitidas
```python
# Importar módulos específicos
from sisb_modulos import minutas
from sisb_modulos import bloqueios

# Importar funções específicas
from sisb_modulos.preenchimento import kaizen_preencher_campos
from sisb_modulos.cookies import salvar_cookies_sisbajud

# Compatibilidade total
import sisb  # Funciona como bacen.py
```

## PRÓXIMOS PASSOS

### ✅ Concluído
- [x] Análise do código original
- [x] Definição da estrutura modular
- [x] Mapeamento de funções
- [x] Projeto de refatoração
- [x] Exemplos de código

### 🔄 Em Andamento
- [ ] Aprovação do projeto
- [ ] Criação da estrutura de pastas
- [ ] Implementação dos módulos

### 📋 Pendente
- [ ] Criação do `sisb_modulos/`
- [ ] Extração das funções para módulos
- [ ] Criação do orquestrador `sisb.py`
- [ ] Testes de integração
- [ ] Documentação detalhada
- [ ] Validação completa

---

**Status**: Projeto definido e pronto para implementação
**Próxima ação**: Aguardar aprovação e iniciar criação da estrutura modular
