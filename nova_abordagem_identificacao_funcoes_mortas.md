# Nova Abordagem para Identificação de Funções Mortas

## 1. Introdução

Este documento descreve uma nova abordagem para identificar funções mortas no projeto PJE Plus com maior precisão, levando em consideração os erros identificados nas tentativas anteriores.

## 2. Limitações das Abordagens Anteriores

1. Verificação incompleta de chamadas indiretas
2. Não consideração adequada de imports dinâmicos
3. Falha em identificar funções chamadas através de referências em strings

## 3. Nova Abordagem

### 3.1. Análise Estática com pyan

1. Utilizar a ferramenta `pyan` para gerar um grafo de chamadas:
   ```
   pyan d:\PjePlus\*.py --uses --no-defines --colored --grouped --annotated --dot > call_graph.dot
   ```

2. Analisar o grafo gerado para identificar funções isoladas que não são chamadas por nenhuma outra função.

### 3.2. Verificação Manual de Funções Suspeitas

Para funções identificadas como potencialmente mortas:
1. Verificar chamadas diretas com `grep`
2. Verificar referências em strings (para chamadas dinâmicas)
3. Verificar se são atributos de classes ou funções utilizadas

### 3.3. Análise de Fluxos de Execução

1. Identificar os principais fluxos de execução (x.py, Mandado, Prazo, PEC)
2. Mapear todas as funções chamadas nesses fluxos
3. Verificar se funções identificadas como mortas aparecem nesses fluxos

### 3.4. Verificação de Imports

1. Identificar todos os imports diretos e indiretos
2. Verificar se funções identificadas como mortas são importadas em algum lugar
3. Analisar se os módulos que contêm essas funções são acessíveis pelos fluxos principais

## 4. Critérios para Classificação

1. Uma função é considerada viva se:
   - É chamada diretamente em algum fluxo principal
   - É referenciada em uma string que é usada para chamadas dinâmicas
   - É um atributo de classe ou função que é utilizado
   - Está em um módulo que é importado e acessível pelos fluxos principais

2. Uma função é considerada morta se:
   - Não atende a nenhum dos critérios acima
   - Está em um módulo que não é acessível pelos fluxos principais

## 5. Processo de Validação

1. Revisar manualmente todas as funções identificadas como mortas
2. Confirmar com múltiplas técnicas que não são utilizadas
3. Documentar claramente as razões para a classificação

## 6. Ferramentas Necessárias

1. `pyan` para análise estática
2. `grep` para buscas textuais
3. Visualizador de grafos (como Graphviz) para analisar o grafo de chamadas

Esta abordagem visa proporcionar uma identificação muito mais precisa e confiável de funções mortas.