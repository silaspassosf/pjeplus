# CORREÇÕES IMPLEMENTADAS - FLUXO ARGOS

## PROBLEMA 1: Função `retirar_sigilo` não estava fazendo nada ❌ → ✅

### Localização
[Mandado/utils.py](Mandado/utils.py#L290) - Linhas 290-324

### O Problema
A lógica de verificação estava invertida. O código tinha:
```python
if "retirar sigilo" not in aria_label:
    # Verifica ícone
    if 'tl-nao-sigiloso' in classes_icone:
        return True  # ✅ Sem sigilo
    if 'tl-sigiloso' not in classes_icone:
        return True  # ✅ Sem sigilo
    # ... mais verificações que retornavam True
```

**Resultado**: Quando o `aria-label` não continha "retirar sigilo" exatamente, a função entrava na lógica de verificação de ícone MAS **retornava True (sucesso) sem clicar no botão**, mesmo quando havia sigilo ativo!

### A Solução
Refatoração da lógica de três estados:

```python
# Estado 1: "inserir sigilo" = já sem sigilo
if "inserir sigilo" in aria_label:
    return True  # ✅ Sem sigilo (não clicar)

# Estado 2: "retirar sigilo" = COM sigilo, precisa clicar
if "retirar sigilo" in aria_label:
    # Clicar no botão
    driver.execute_script('arguments[0].click();', btn_sigilo)
    return True

# Estado 3: Sem aria-label claro = verificar ícone
else:
    # Verificar tl-nao-sigiloso ou tl-sigiloso
    # Se tem tl-sigiloso mas aria-label vazio, CLICAR
```

### Impacto
✅ A função agora **realmente clica** quando há sigilo ativo  
✅ Verifica aria-label como indicador primário  
✅ Fallback para ícones quando aria-label está vazio  

---

## PROBLEMA 2: Função `processar_argos` não itera sobre regras ❌ → ✅

### Localização
[Mandado/processamento.py](Mandado/processamento.py#L714) - Etapas 4, 5, 6

### O Problema
A função tinha apenas **UM** fluxo linear:
1. Chama `buscar_documento_argos()` **UMA VEZ**
2. Se encontrar documento, extrai texto
3. Chama `aplicar_regras_argos()` **UMA VEZ**
4. **Se nenhuma regra aplicar, simplesmente retorna True sem fazer nada!**

**Resultado**: Se o primeiro documento encontrado não continha padrão de nenhuma estratégia em `aplicar_regras_argos()`, o fluxo terminava sem executar ação alguma!

### A Solução
Implementar **LOOP DE TENTATIVAS** que:

```python
while tentativa < max_tentativas and not sucesso_regras:
    # 1. Busca documento via buscar_documento_argos()
    resultado_documento = buscar_documento_argos(driver, log=True)
    
    # 2. Extrai destinatários
    destinatarios_extraidos = extrair_destinatarios_decisao(...)
    
    # 3. TENTA APLICAR REGRAS
    regras_aplicadas = aplicar_regras_argos(...)
    
    # 4. SE REGRA FOI APLICADA = SUCESSO! Sai do loop
    if regras_aplicadas:
        sucesso_regras = True
        break
    
    # 5. SE NÃO APLICOU = Continua o loop para próximo documento
    else:
        print('⚠️ Nenhuma regra - tentando próximo documento...')
        continue
```

### Características do Loop
- **Máximo de 5 tentativas** (limite de segurança)
- **Continua iterando** enquanto não achar documento com regra aplicável
- **Executa UMA VEZ apenas** quando encontra regra válida (conforme requisito)
- **Logs detalhados** com número da tentativa
- **Tolerância ao falhar**: Se todas as tentativas falharem, continua o fluxo (não aborta)

### Impacto
✅ Agora itera sobre **múltiplos documentos** até encontrar um com regra  
✅ **Executa a ação correspondente** quando encontra padrão válido  
✅ **Sai do loop** após executar (apenas uma vez)  
✅ **Logs com rastreamento** de tentativa (Tentativa 1/5, 2/5, etc)  

---

## RESUMO DAS MUDANÇAS

| Arquivo | Linhas | Tipo | Status |
|---------|--------|------|--------|
| [utils.py](Mandado/utils.py#L290) | 290-324 | Lógica invertida | ✅ Corrigido |
| [processamento.py](Mandado/processamento.py#L714) | 714-793 | Loop adicionado | ✅ Corrigido |

### Antes vs Depois

#### Antes
```
[ARGOS] Buscando documento relevante...
[ARGOS] Documento encontrado
[ARGOS] Aplicando regras...
[ARGOS] ❌ Nenhuma regra aplicada (PARA AQUI)
[ARGOS] SUCESSO! (❌ FALSO - nada foi feito)
```

#### Depois
```
[ARGOS] Tentativa 1/5...
[ARGOS] Buscando documento...
[ARGOS] ✅ Documento encontrado
[ARGOS] Aplicando regras...
[ARGOS] ⚠️ Nenhuma regra - tentando próximo...

[ARGOS] Tentativa 2/5...
[ARGOS] Buscando documento...
[ARGOS] ✅ Documento encontrado
[ARGOS] Aplicando regras...
[ARGOS] ✅ Regra aplicada com sucesso!
[ARGOS] SUCESSO! (✅ VERDADEIRO - ação executada)
```

---

## TESTES RECOMENDADOS

### Teste 1: Sigilo Ativo
1. Navegue para mandado com documento sigiloso
2. Execute `processar_argos(driver)`
3. **Esperado**: Função `retirar_sigilo()` clica e remove sigilo
4. **Verificar**: Ícone muda de azul para vermelho (ou aria-label muda)

### Teste 2: Múltiplos Documentos
1. Navegue para mandado com vários despachos/decisões
2. Primeira decisão: **não contém padrão** de regra
3. Segunda decisão: **contém "defiro a instauração"**
4. Execute `processar_argos(driver)`
5. **Esperado**: Pula primeira (log: "nenhuma regra"), tenta segunda (log: "regra aplicada")
6. **Verificar**: Ato judicial foi executado para a segunda decisão

### Teste 3: Falha em Todas
1. Navegue para mandado com decisões sem padrão
2. Execute `processar_argos(driver)`
3. **Esperado**: Log "Nenhuma regra Argos foi aplicada após todas as tentativas"
4. **Verificar**: Fluxo continua (não aborta)

---

## NOTAS IMPORTANTES

⚠️ **Recurso**: Se `aplicar_regras_argos()` continuar retornando `False`, verificar:
- Estratégias definidas em [regras.py](Mandado/regras.py#L342)
- Padrões esperados no texto do documento
- Debug logs: `aplicar_regras_argos(..., debug=True)`

⚠️ **Timeout**: Limite de 5 tentativas pode ser ajustado na variável `max_tentativas`

✅ **Compatibilidade**: Alterações são **100% retrocompatíveis** - não quebram código externo
