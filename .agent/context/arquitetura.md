# Contexto: Arquitetura do Projeto

## Camadas

### 1. Core (Fix/)
**Responsabilidade:** Funcionalidades base reutilizáveis
- `log.py` - Logging centralizado
- `core.py` - Funções Selenium (aguardar_elemento, safe_click)
- `utils.py` - Helpers gerais

### 2. Módulos de Negócio
**PEC/** - Petições Eletrônicas
**SISB/** - SISBAJUD (bloqueios bancários)
**atos/** - Atos processuais (citações, intimações)
**Mandado/** - Gestão de mandados
**Prazo/** - Controle de prazos

### 3. Legacy (ref/)
**NÃO MODIFICAR** - Código funcional original
Usar apenas como referência para restaurar lógica

## Fluxo de Dados
```
Usuario → Módulo → Fix/core → Selenium → PJe
                ↓
              Fix/log → Arquivo de log
```

## Dependências Críticas
- Selenium WebDriver
- Chrome/ChromeDriver
- Python 3.8+
