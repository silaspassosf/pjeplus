# Relatório de sob.py

Este relatório descreve as etapas e funções do script `sob.py` (cópia de p2.py), para facilitar futuras alterações e customizações.

## 1. Objetivo Geral
Automatizar fluxos de análise de processos no PJe, realizando extração de dados, aplicação de regras, criação de GIGS e movimentações, de forma parametrizada e controlada.

---

## 2. Estrutura Geral
O script é composto por funções utilitárias, funções de fluxo principal, funções de callback e uma classe de automação. Abaixo, as principais etapas e funções:

### 2.1. Inicialização e Logging
- **Gera log de execução**: Escreve informações da execução no arquivo `log.py`.
- **Configuração de logging**: Define formato e destino dos logs (arquivo e console).

### 2.2. Funções Utilitárias
- `parse_gigs_param(param)`: Extrai parâmetros de GIGS de uma string.
- `checar_prox(driver, itens, doc_idx, regras, texto_normalizado)`: Busca próximo documento relevante na timeline.
- `esperar_url(driver, url_esperada, timeout)`: Aguarda até a URL ser atingida.
- `esperar_url_conter(driver, trecho_url, timeout)`: Aguarda até a URL conter determinado trecho.

### 2.3. Fluxos Principais
- `fluxo_pz(driver)`: 
    1. Seleciona documento relevante (decisão, despacho, sentença, conclusão).
    2. Extrai texto do documento.
    3. Normaliza texto e aplica regras (regex) para identificar ações.
    4. Executa ações: cria GIGS, movimenta, executa funções auxiliares, etc.
    5. Fecha a aba do processo ao final.
- `fluxo_prazo(driver)`: Itera sobre processos, chamando `fluxo_pz` para cada um.
- `executar_fluxo(driver)`: Executa o fluxo completo: login, navegação, aplicação de filtros, processamento da lista de processos.
- `main()`: Ponto de entrada para execução direta do script.
- `processar_p2(driver_existente=None)`: Permite execução do fluxo com driver externo ou novo.

### 2.4. Funções Auxiliares de Navegação
- `navegar_para_atividades(driver)`: Navega para tela de atividades do GIGS.

### 2.5. Classe de Automação
- `AutomacaoP2`: Classe para encapsular o fluxo de automação, com métodos para iniciar, logar, executar fluxo, reiniciar etapa e finalizar.

---

## 3. Principais Etapas do Fluxo
1. **Login e inicialização do driver**
2. **Navegação até a tela de sobrestamento**
3. **Aplicação de filtros (ex: 100 itens por página, filtro xs)**
4. **Processamento da lista de processos**
5. **Para cada processo:**
    - Seleção do documento relevante (sempre **decisão**, não outras opções)
    - Extração e análise do texto
    - Aplicação de regras (regex)
    - Execução de ações (GIGS, movimentações, pesquisas, etc.)
    - Fechamento da aba
6. **Finalização do driver**

---

## 4. Pontos de Customização
- **Regras de regex**: Editar a lista `regras` em `fluxo_pz` para alterar critérios de ação.
- **Ações customizadas**: Alterar funções passadas como parâmetro nas regras.
- **Filtros e navegação**: Ajustar etapas de filtro em `executar_fluxo`.
- **Classe AutomacaoP2**: Adaptar métodos para integração com outros sistemas.

---

## 5. Observações
- O script depende fortemente de funções utilitárias do módulo `Fix` e de outros módulos do projeto.
- As funções e etapas são altamente parametrizáveis via regras e callbacks.
- O fluxo é robusto para automação de tarefas repetitivas no PJe.

---

*Este relatório pode ser atualizado conforme as alterações forem realizadas em `sob.py`.*
