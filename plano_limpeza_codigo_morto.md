# Plano de Limpeza de Código Morto

Este documento descreve o plano sistemático para identificar, classificar e remover código morto do projeto PJE Plus, garantindo a manutenibilidade e clareza do código fonte.

## 1. Classificação por Prioridade de Ação

### 🔴 ALTA PRIORIDADE - Remover Imediatamente

#### Arquivos de backup
- `PEC\processamento_backup.py` → `testar_coluna_observacao`, `testar_coluna_observacao_novo`
- Justificativa: Código duplicado que pode causar confusão

#### Arquivos de teste/exemplo
- `PEC\test_pet2.py` e `PEC\test_pet2_real.py` (todas as funções)
- Justificativa: Se não são parte do pipeline de testes automatizados

### 🟡 MÉDIA PRIORIDADE - Investigar e Decidir

#### Getters/Setters órfãos
- `PEC\matcher.py` → `get_cached_rules`, `get_action_rules`
- `PEC\sisbajud_driver.py` → `get_or_create_driver_sisbajud`

#### Funções de sobrestamento específicas
- `PEC\sobrestamento.py` → Todas as funções
- Verificar se o fluxo de sobrestamento está usando estas ou outras variantes

### 🟢 BAIXA PRIORIDADE - Documentar e Monitorar

#### Funções com nomes sugestivos
- Marcar com decorator `@deprecated` ou comentário especial
- Ex: `atos\core.py` → `aguardar_e_verificar_detalhe`

## 2. Abordagem Sistemática de Remoção

### Etapa 1: Criar Branch Específica
```bash
git checkout -b limpeza-funcoes-mortas
```

### Etapa 2: Remover Arquivos de Backup e Testes
```python
# Verificar se há dependências antes de remover
# Buscar por referências nos arquivos:
grep -r "testar_coluna_observacao" . --include="*.py"
```

### Etapa 3: Refatorar Funções Duplicadas
Muitas funções parecem ter duplicatas. Por exemplo:
- Em `Prazo/` existem dois sistemas de fluxo: `prov.py` e `prov_fluxo.py`
- Verificar qual é o ativo e remover o obsoleto

## 3. Melhorias no Código Fonte

### Adicionar Decorators para Funções Obsoletas
```python
import warnings
from functools import wraps

def deprecated(reason):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {reason}",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Uso:
@deprecated("Usar nova_api_de_envio no lugar")
def enviar_url_infojud():
    pass
```

### Criar Sistema de Monitoramento de Uso
```python
def track_usage(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Registrar uso em log
        logging.info(f"Função {func.__name__} chamada em {datetime.now()}")
        return func(*args, **kwargs)
    return wrapper

# Aplicar em funções duvidosas
@track_usage
def funcao_suspeita():
    pass
```

## 4. Verificações Antes da Remoção

### 1. Buscar Referências Indiretas
```bash
# Verificar chamadas dinâmicas
grep -r "funcao_nome" . --include="*.py"

# Verificar uso em strings (eval, getattr, etc.)
grep -r "getattr.*funcao_nome" . --include="*.py"
```

### 2. Verificar Dependências em JSON/Configurações
- Buscar nomes de funções em arquivos de configuração
- Verificar se são pontos de entrada em scripts externos

### 3. Validar em Ambiente de Teste
- Executar fluxos principais após remoção
- Verificar logs por erros de NameError

## 5. Plano de Ação Recomendado

### Semana 1: Limpeza Imediata
1. Remover arquivos de backup confirmados
2. Remover funções de teste não utilizadas
3. Corrigir problemas de encoding relatados

### Semana 2: Análise Profunda
1. Investigar funções marcadas como "Motivo desconhecido"
2. Decidir sobre wrappers e getters/setters órfãos
3. Consolidar funções duplicadas

### Semana 3: Documentação e Monitoramento
1. Adicionar decorators para funções obsoletas
2. Criar sistema de tracking para funções duvidosas
3. Atualizar documentação do projeto

### Semana 4: Validação Final
1. Executar testes completos
2. Validar em ambiente de staging
3. Preparar merge para branch principal

## 6. Ferramentas Úteis para Continuar a Análise

### Script para Verificar Referências
```python
# check_references.py
import ast
import os

def find_function_references(func_name, search_path="."):
    references = []
    for root, dirs, files in os.walk(search_path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if func_name in content:
                            references.append(filepath)
                except:
                    pass
    return references
```

## 7. Critérios de Aceitação

- [x] Todos os arquivos de backup foram removidos
- [x] Funções de teste não utilizadas foram excluídas
- [ ] Funções duplicadas foram consolidadas
- [ ] Funções obsoletas foram marcadas com `@deprecated`
- [ ] Sistema de monitoramento foi implementado para funções duvidosas
- [ ] Todos os testes estão passando após as mudanças
- [ ] Validação em ambiente de staging concluída com sucesso

Este plano será revisado e atualizado conforme necessário durante o processo de limpeza.