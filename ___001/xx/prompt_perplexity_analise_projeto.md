# Prompt Completo para Análise do Projeto no Perplexity Pro

## 📋 Como Usar
Copie o texto abaixo e cole no Perplexity Pro. Para melhores resultados, **anexe** os arquivos principais do seu projeto ou, se possível, faça o upload de um `.zip` contendo o código fonte (especialmente `ARQUITETURA_REFATORADA.md` e pastas relevantes como `Fix`, `PEC`, `SISB`).

---

**[INÍCIO DO PROMPT]**

Atue como um **Senior Software Architect** especializado em Python, Automação de Processos (RPA/Selenium) e Engenharia de Software Moderna.

Estou trabalhando no projeto **PJePlus**, uma suíte de automação para sistemas jurídicos (PJe, SISBAJUD, etc.) escrita em Python. O projeto está passando por uma refatoração significativa de uma estrutura monolítica para uma arquitetura modular.

**Contexto do Projeto:**
- **Status:** Fase 1 da refatoração concluída (Módulos `Fix`, `PEC`, `SISB` modularizados).
- **Legado:** Módulos `atos`, `Mandado`, `Prazo`, `Peticao` ainda contêm código antigo/misturado.
- **Tecnologias:** Python, Selenium (Webdriver).
- **Estrutura Atual:**
    - `Fix`: Core/Foundation (Drivers, Logging, Helpers).
    - `PEC`: Petições Eletrônicas (Lógica de negócio específica).
    - `SISB`: Integração Bancária (SISBAJUD).
- **Problemas Identificados:** Código duplicado entre módulos, acoplamento forte, dificuldade de manutenção por IA (código imperativo longo), performance de execução Selenium não otimizada.

**Objetivos da Análise:**
Por favor, analise a estrutura e o código fornecido com foco em 4 pilares:

1.  **Eliminação de Duplicidade (DRY):**
    - Identifique padrões repetidos entre os módulos (ex: tratamento de exceções, espera de elementos, manipulação de strings/datas).
    - Sugira abstrações para o módulo `Fix` ou um novo `Core` compartilhado.

2.  **Redução de Dependências:**
    - Como desacoplar melhor os módulos para evitar imports circulares e facilitar testes unitários?
    - Sugira padrões (ex: Injeção de Dependência, Event Bus) para comunicação entre módulos.

3.  **Manutenibilidade para IA:**
    - Como estruturar o código (Type Hints, Docstrings, Classes vs Funções Puras) para que agentes de IA possam entender e manter o projeto com mais facilidade?
    - Quais bibliotecas (ex: Pydantic, Loguru) facilitariam a legibilidade para LLMs?

4.  **Eficiência de Execução:**
    - Estratégias para otimizar o uso do Selenium (ex: evitar `time.sleep`, usar `WebDriverWait` wrapper global, paralelismo seguro).
    - Como melhorar a performance em scripts de longa duração (gerenciamento de memória, sessões)?

**Saída Esperada:**
Uma análise técnica detalhada contendo:
- **Diagnóstico de Arquitetura:** Avaliação da estrutura atual e identificação de Anti-Patterns.
- **Oportunidades de Refatoração Imediata:** Lista de 3 funcionalidades para promover ao `Fix` (Core).
- **Guia de Estilo "AI-First":** Padrões de codificação e documentação recomendados.
- **Roadmap Sugerido:** Ordem lógica para refatorar os módulos restantes (`atos`, `Mandado`, `Prazo`).

**[FIM DO PROMPT]**
