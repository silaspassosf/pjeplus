# Guia de Configuração de Caminhos - PJePlus

Este guia explica como configurar os caminhos do sistema usando credenciais do Windows, eliminando a necessidade de alterar o código-fonte para diferentes ambientes.

## Visão Geral

O sistema agora permite armazenar os caminhos dos drivers e perfis do Firefox usando o `keyring` do Windows, permitindo configurações específicas por máquina sem alterar o código-fonte.

## Configuração Inicial

### Método 1: Script Interativo

Execute o script de configuração:

```bash
python configurar_caminhos.py
```

Este script irá:
1. Solicitar os caminhos para os principais componentes
2. Validar se os caminhos existem
3. Armazenar as informações nas credenciais do Windows
4. Exibir a configuração atual

### Método 2: Configuração Manual via Python

Você também pode configurar manualmente usando o seguinte código:

```python
from Fix.utils_paths import configurar_caminho_credencial

# Configurar caminho do perfil do Firefox
configurar_caminho_credencial('FIREFOX_PROFILE_PATH', r'C:\Users\SeuUsuario\AppData\Roaming\Mozilla\Dev\Selenium')

# Configurar caminho do executável do Firefox
configurar_caminho_credencial('FIREFOX_BINARY', r'C:\Program Files\Mozilla Firefox\firefox.exe')

# Configurar caminho do geckodriver
configurar_caminho_credencial('GECKODRIVER_PATH', r'C:\caminho\para\geckodriver.exe')

# Configurar caminho do perfil VT PJE
configurar_caminho_credencial('VT_PROFILE_PJE', r'C:\Users\SeuUsuario\AppData\Roaming\Mozilla\Firefox\Profiles\seu.perfil')

# Configurar caminho do perfil VT PJE alternativo
configurar_caminho_credencial('VT_PROFILE_PJE_ALT', r'C:\Users\SeuUsuario\AppData\Roaming\Mozilla\Firefox\Profiles\outro.perfil')

# Configurar caminho do Firefox alternativo
configurar_caminho_credencial('FIREFOX_BINARY_ALT', r'C:\Users\SeuUsuario\AppData\Local\Mozilla Firefox\firefox.exe')

# Configurar caminho do perfil SISBAJUD
configurar_caminho_credencial('SISB_PROFILE_PATH', r'C:\Users\SeuUsuario\AppData\Local\Mozilla\Firefox\Profiles\sisb.perfil')

# Configurar caminho do AutoHotkey
configurar_caminho_credencial('AUTOHOTKEY_EXE', r'C:\Program Files\AutoHotkey\AutoHotkey.exe')
```

## Credenciais Disponíveis

As seguintes credenciais podem ser configuradas no namespace `pjeplus_paths`:

- `FIREFOX_PROFILE_PATH`: Caminho do perfil do Firefox
- `FIREFOX_BINARY`: Caminho do executável do Firefox principal
- `FIREFOX_BINARY_ALT`: Caminho do executável do Firefox alternativo
- `GECKODRIVER_PATH`: Caminho do geckodriver
- `VT_PROFILE_PJE`: Caminho do perfil VT PJE
- `VT_PROFILE_PJE_ALT`: Caminho do perfil VT PJE alternativo
- `SISB_PROFILE_PATH`: Caminho do perfil SISBAJUD
- `AUTOHOTKEY_EXE`: Caminho do executável do AutoHotkey

## Como Funciona

1. Quando uma função precisa de um caminho, ela primeiro tenta obter o valor das credenciais do Windows
2. Se o valor não estiver configurado ou o caminho não existir, é utilizado um valor padrão
3. Isso permite que diferentes máquinas tenham configurações específicas sem alterar o código

## Exibindo Configuração Atual

Para verificar a configuração atual:

```python
from Fix.utils_paths import exibir_configuracao_atual
exibir_configuracao_atual()
```

Ou execute:

```bash
python -c "from Fix.utils_paths import exibir_configuracao_atual; exibir_configuracao_atual()"
```

## Benefícios

- **Portabilidade**: Mesmo código funciona em diferentes máquinas
- **Segurança**: Caminhos sensíveis não ficam hardcoded no código
- **Flexibilidade**: Fácil ajuste por máquina sem alterar o código-fonte
- **Manutenção**: Centralização das configurações em um único lugar

## Compatibilidade

O sistema mantém compatibilidade com versões anteriores, usando valores padrão quando as credenciais não estão configuradas.