# Metodologia para Identificação de Funções Mortas

## 1. Introdução

Este documento descreve uma abordagem mais robusta para identificar funções mortas no projeto PJE Plus, visando minimizar erros e aumentar a precisão dos resultados.

## 2. Limitações da Abordagem Anterior

A abordagem anterior teve os seguintes problemas:
1. Não verificou adequadamente as chamadas indiretas às funções
2. Não considerou funções chamadas através de imports dinâmicos
3. Não analisou completamente os fluxos de execução principais

## 3. Nova Abordagem Robusta

### 3.1. Análise de Fluxos de Execução Principais

1. Identificar os pontos de entrada principais:
   - `x.py` como orquestrador central
   - Módulos específicos para cada fluxo (Mandado, Prazo, PEC)

2. Mapear as chamadas de função a partir desses pontos de entrada:
   - Utilizar ferramentas de análise estática para rastrear chamadas
   - Identificar chamadas diretas e indiretas

### 3.2. Análise de Imports

1. Verificar imports diretos e indiretos:
   - Identificar funções importadas em cada módulo
   - Verificar imports condicionais e dinâmicos

2. Mapear dependências entre módulos:
   - Criar um grafo de dependências
   - Identificar módulos que não são alcançáveis a partir dos fluxos principais

### 3.3. Verificação Cruzada

1. Para cada função suspeita de estar morta:
   - Verificar em todo o código se ela é chamada diretamente
   - Verificar se ela é referenciada em strings (para chamadas dinâmicas)
   - Verificar se ela é um atributo de classe ou função que é utilizado

2. Confirmar que funções identificadas como utilizadas:
   - Aparecem em pelo menos um dos fluxos principais
   - Têm chamadas diretas ou indiretas verificáveis

## 4. Ferramentas e Técnicas

1. Utilizar `grep` e variantes para buscas abrangentes:
   - Buscar definições de funções
   - Buscar chamadas diretas
   - Buscar referências em strings

2. Utilizar análise estática com ferramentas como `pyan`:
   - Gerar grafos de chamadas
   - Identificar funções isoladas

3. Criar scripts personalizados para:
   - Mapear fluxos de execução
   - Verificar dependências de imports
   - Identificar funções potencialmente mortas

## 5. Critérios para Classificação

1. Uma função é considerada viva se:
   - É chamada diretamente em algum fluxo principal
   - É referenciada em uma string que é usada para chamadas dinâmicas
   - É um atributo de classe ou função que é utilizado

2. Uma função é considerada morta se:
   - Não atende a nenhum dos critérios acima
   - Está em um módulo que não é importado por nenhum fluxo principal

## 6. Processo de Validação

1. Revisar manualmente funções identificadas como mortas:
   - Confirmar que não são chamadas em nenhum lugar
   - Verificar se têm utilidade potencial futura

2. Revisar amostra de funções identificadas como vivas:
   - Confirmar que realmente são chamadas nos fluxos
   - Verificar se há chamadas indiretas não identificadas

## 7. Documentação e Relatório

1. Manter registro detalhado do processo:
   - Listar funções verificadas
   - Documentar chamadas encontradas
   - Justificar classificações

2. Criar relatório claro e verificável:
   - Separar funções vivas e mortas
   - Fornecer evidências para classificações
   - Facilitar revisão por outros desenvolvedores

Esta metodologia visa proporcionar uma identificação mais precisa e confiável de funções mortas, reduzindo significativamente a chance de erros.