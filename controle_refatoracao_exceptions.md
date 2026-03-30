# Controle de Refatoração: Uso de Exceções Tipadas (Fix/exceptions.py)

## 1. Critérios de Identificação
- Alvo: Locais que usam `return False`, `except Exception`, ou tratam erros Selenium/DOM de forma genérica.
- Objetivo: Substituir por exceções tipadas, centralizando o tratamento e tornando o fluxo mais previsível.

---

## 2. Locais Prioritários para Refatoração

### 2.1 Fix/ (motor utilitário)
- **Fix/abas.py**
  - Gerenciamento de abas, navegação entre janelas.
  - Ação: Substituir por `NavegacaoError` e `DriverFatalError`.
- **Fix/core.py**
  - Funções de click, wait, preenchimento, criação de driver.
  - Ação: Usar `ElementoNaoEncontradoError`, `TimeoutFluxoError`, `DriverFatalError`.
- **Fix/smartfinder.py**
  - Busca de elementos com cache/fallback.
  - Ação: Mapear para `ElementoNaoEncontradoError`.
- **Fix/utils/observer.py**
  - Espera por renderização Angular.
  - Ação: Usar `TimeoutFluxoError`.

### 2.2 atos/ (wrappers e orquestradores)
- **atos/wrappers_mov.py**
  - Wrappers de movimentação processual.
  - Ação: Substituir por exceções tipadas, removendo retornos silenciosos.
- **atos/wrappers_utils.py**
  - Utilitários de atos, manipulação de visibilidade.
  - Ação: Usar exceções tipadas para falhas de manipulação.
- **atos/comunicacao.py**
  - Comunicação judicial, envio de atos.
  - Ação: Mapear falhas para exceções específicas.

### 2.3 Mandado/, PEC/, Prazo/, SISB/
- Orquestradores e fluxos principais.
- Ação: Capturar apenas `PJePlusError` no topo, nunca tratar exceções Selenium diretamente.

---

## 3. Pontos de Unificação e Centralização
- Centralizar lançamento de exceções tipadas em funções utilitárias (Fix/).
- Wrappers de negócio deixam exceções subirem até o orquestrador.
- Orquestradores finais capturam apenas `PJePlusError` e subclasses.

---

## 4. Exemplos de Pontos de Entrada/Funções
- **Fix/core.py**: `aguardar_e_clicar`, `preencher_campo`, `wait_for_visible`, `criar_driver_PC`
- **Fix/abas.py**: `trocar_aba`, `fechar_aba`, `abrir_nova_aba`
- **atos/wrappers_mov.py**: `mov`, `mov_simples`, `mov_arquivar`
- **Mandado/processamento.py**, **PEC/processamento.py**: funções de fluxo principal

---

## 5. Fluxo Visual de Exceções

```mermaid
flowchart TD
    subgraph Infraestrutura (Fix/)
        A[Funções utilitárias] -- lança --> B[Exceções tipadas]
    end
    subgraph Negócio (atos/, Mandado/, etc.)
        C[Wrappers/Helpers] -- deixa subir --> B
    end
    D[Orquestrador final] -- captura --> B
    B -- loga/aborta --> D
```

---

## 6. Roteiro Incremental de Refatoração

### 6.1 Etapa 1: Fix/abas.py
- Substituir todos os `try/except Exception` e retornos silenciosos por exceções tipadas. **(CONCLUÍDO)**
- Validar dependências e impacto.

### 6.2 Etapa 2: Fix/core.py
- Refatorar funções de click, wait, preenchimento para lançar exceções tipadas. **(CONCLUÍDO)**

### 6.3 Etapa 3: Fix/smartfinder.py
- Mapear falhas de busca para `ElementoNaoEncontradoError`. **(NÃO FOI NECESSÁRIO — já está seguro)**

### 6.4 Etapa 4: atos/wrappers_mov.py
- Remover retornos silenciosos, lançar exceções específicas. **(CONCLUÍDO)**

### 6.5 Etapa 5: Ajuste dos orquestradores
- Garantir que capturam apenas `PJePlusError`. **(NÃO FOI NECESSÁRIO — já está seguro)**

---

**Atualize este arquivo a cada etapa concluída para controle incremental.**
