# Resumo Rápido - Fix.py

## Funções Principais

### Interação com Elementos
- `safe_click(driver, seletor, timeout=10)` - Clique seguro com espera
- `esperar_elemento(driver, seletor, timeout=10)` - Espera por elemento
- `preencher_campo(driver, seletor, valor)` - Preenche campos de formulário

### Navegação
- `navegar_para_tela(driver, url)` - Navegação com tratamento de erros
- `login_pje_robusto(driver, tentativas=3)` - Login com fallback

### Utilitários
- `limpar_temp_selenium()` - Limpeza de arquivos temporários
- `buscar_seletor_robusto(texto)` - Encontra seletores por texto visível

### Processos
- `processar_lista_processos(driver)` - Fluxo principal de automação
- `extrair_dados_processo(driver)` - Coleta metadados do processo

## Importação Segura
```python
# Exemplo de importação recomendada
from Fix import (
    safe_click,
    esperar_elemento,
    navegar_para_tela
)
