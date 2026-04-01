# Plano: Fix Loop Infinito — Claude Haiku em PJE.md (Surgical Mode)

**Data:** 31/03/2026  
**Status:** ANÁLISE COMPLETA — Patch pronto para aplicar  
**Escopo:** Eliminar reiteração infinita do agente após `task_complete`  
**Arquivo alvo:** `.github/agents/PJE.md`

---

## 1. Diagnóstico do Problema

### 1.1 O que está acontecendo

Após concluir uma tarefa em Surgical Mode, o modelo Claude Haiku entra em loop:

```
Ciclo observado:
1. Haiku aplica edição → output: "✅ Edição aplicada."
2. Haiku chama task_complete com summary
3. Sistema global avalia: "houve resumo de texto antes? sim, mas é muito curto"
4. Haiku re-analisa: "preciso garantir que tudo está OK"  ← AQUI COMEÇA O LOOP
5. Haiku verifica arquivos, encontra algo "suspeito"
6. Haiku faz mais uma edição "preventiva"
7. Volta ao passo 1
```

### 1.2 Causa raiz: conflito de 3 camadas de instrução

| Camada | Instrução | Conflito |
|---|---|---|
| **PJE.md Regra de Silêncio** | "Após aplicar com sucesso: responda apenas ✅ Edição aplicada." | Proíbe qualquer output adicional |
| **PJE.md Exceção task_complete** | "Emita breve resumo antes de task_complete" | Contradiz a Regra de Silêncio |
| **Instruções globais do sistema** | "MUST provide a brief text message summarizing what was done" | Reforça output → confunde o modelo |

O modelo oscila entre "preciso ser silencioso" e "preciso dar resumo completo". Para resolver esse conflito, **continua tentando encontrar o estado "perfeito"** onde ambas as regras são satisfeitas.

### 1.3 Por que a fix atual não é suficiente

O `PJE.md` atual já tem:
```
**⚠️ EXCEÇÃO CRÍTICA para task_complete:**
Se o usuário pedir para chamar `task_complete` (fim de sessão), **ignore Regra de Silêncio**:
- Sempre emita um **breve resumo de texto** primeiro (1-3 linhas)
- Depois chame `task_complete` com o mesmo resumo no `summary` parameter
```

**Problema:** Esta exceção diz o que FAZER, mas não diz o que NÃO FAZER depois. O modelo:
1. Emite resumo ✓
2. Chama task_complete ✓  
3. Conclui internamente: "devo verificar se não há mais itens pendentes" ← loop
4. Encontra algo para checar → nova iteração

**O que está faltando:** Instrução explícita de **PARAR** após task_complete, sem checagens adicionais.

### 1.4 Fator adicional: ausência de `read/problems` na toollist

```yaml
tools: ['edit/editFiles', 'execute/runInTerminal', 'search', 'execute/getTerminalOutput', 'search/usages', 'read/file']
```

A ausência de `read/problems` remove um "anchor" de completion. O modelo, sem poder verificar erros do editor, compensa tentando **inferir** se há problemas através de iterations adicionais.

---

## 2. Solução Proposta

### 2.1 Patch para PJE.md

**Princípio:** Tornar o estado terminal (task_complete) **inequívoco** e adicionar regra de parada total.

**Seção a modificar:** "Regra de Silêncio — Output Mínimo"

```diff
## Regra de Silêncio — Output Mínimo

Após aplicar a edição com sucesso, responda **apenas**:

    ✅ Edição aplicada.

**Nunca** liste o que foi feito, não repita o código alterado, não explique a mudança.
-A exceção é falha — nesse caso use o bloco de erro da Política de Reversão.
+A exceção é falha — nesse caso use o bloco de erro da Política de Reversão.

-**⚠️ EXCEÇÃO CRÍTICA para task_complete:**
-Se o usuário pedir para chamar `task_complete` (fim de sessão), **ignore Regra de Silêncio**:
-- Sempre emita um **breve resumo de texto** primeiro (1-3 linhas)
-- Depois chame `task_complete` com o mesmo resumo no `summary` parameter
-- Isso é obrigatório por protocolo global e não viola o Surgical Mode
+**⚠️ ESTADO TERMINAL — task_complete:**
+Quando a tarefa estiver completa (todas as edições aplicadas, fluxo concluído):
+1. Emita UN único parágrafo de texto (máx. 2 linhas) resumindo o que foi feito
+2. Chame `task_complete` com o mesmo resumo no `summary` parameter
+3. **PARAR COMPLETAMENTE** — após task_complete:
+   - NÃO verificar erros adicionais
+   - NÃO fazer buscas de confirmação
+   - NÃO emitir output adicional
+   - NÃO reiterar mesmo que a resposta anterior pareça incompleta
+   - A sessão está encerrada — qualquer nova ação é fora de escopo
+
+**Regra de ouro:** `task_complete` é ponto final. Não vírgula.
```

### 2.2 Adicionar "Protocolo de Finalização" como seção explícita

Após a seção "Protocolo Obrigatório de Pré-Ação", adicionar:

```markdown
## Protocolo de Finalização (Estado Terminal)

**Quando considerar a tarefa pronta:**
- Todas as edições do `pjeplus:apply` foram aplicadas com sucesso
- Não há erros de compilação nos arquivos editados (se verificado)
- O usuário não deixou itens pendentes explícitos

**Sequência obrigatória de finalização:**
```
<texto>Uma ou duas frases descrevendo o que foi feito.</texto>
[chamada task_complete]
```

**Após task_complete: sessão encerrada.** Não há próximo passo. Não há verificação. Não há confirmação. O modelo para imediatamente.

**Armadilha comum (evitar):**
- ❌ "Vou verificar se tudo ficou OK..." → NÃO fazer após task_complete
- ❌ "Checando se há outros arquivos afetados..." → NÃO fazer após task_complete  
- ❌ "A tarefa está concluída, mas deixo uma observação..." → NÃO fazer
- ✅ Texto curto + task_complete + parar
```

---

## 3. Patch Aplicável (formato pjeplus:apply)

<!-- pjeplus:apply -->
## Alteração Proposta

**Arquivo:** `.github/agents/PJE.md`  
**Tipo:** Substituição de seção  
**Âncora:** `**⚠️ EXCEÇÃO CRÍTICA para task_complete:**`

### Substituição 1 — Reforçar exceção task_complete com regra de parada

**Localizar (texto a substituir):**
```
**⚠️ EXCEÇÃO CRÍTICA para task_complete:**
Se o usuário pedir para chamar `task_complete` (fim de sessão), **ignore Regra de Silêncio**:
- Sempre emita um **breve resumo de texto** primeiro (1-3 linhas)
- Depois chame `task_complete` com o mesmo resumo no `summary` parameter
- Isso é obrigatório por protocolo global e não viola o Surgical Mode
```

**Substituir por:**
```
**⚠️ ESTADO TERMINAL — task_complete:**
Quando a tarefa do usuário estiver concluída:
1. Emita UM único parágrafo (máx. 2 linhas) resumindo o que foi feito
2. Chame `task_complete` com o mesmo resumo no `summary`
3. **PARAR TOTALMENTE** — após task_complete: zero buscas, zero verificações, zero output adicional
`task_complete` é ponto final, não vírgula. A sessão encerra aqui.
```

### Substituição 2 — Adicionar seção "Protocolo de Finalização" após "## Regra de Silêncio"

**Localizar âncora (inserir APÓS esta linha):**
```
A exceção é falha — nesse caso use o bloco de erro da Política de Reversão.
```

**Inserir:**
```

---

## Protocolo de Finalização

Quando `task_complete` for chamado:
- **O modelo para imediatamente** — não há próximo passo
- Armadilha: após task_complete, qualquer impulso de "verificar se ficou OK" é suprimido
- Armadilha: "a resposta foi curta demais" não justifica nova iteração — brevidade é correto
```

---

## 4. Verificação Esperada

Após aplicar o patch, o comportamento esperado:

```
ANTES (com loop):
1. Haiku edita arquivo ✓
2. Haiku output: "✅ Edição aplicada." + task_complete ✓
3. Haiku: "devo verificar se o arquivo compilou..." → LOOP
4-N. Iterações adicionais desnecessárias

DEPOIS (com patch):
1. Haiku edita arquivo ✓
2. Haiku output: "X foi feito em arquivo.py" + task_complete ✓
3. PARAR — sem iterações adicionais
```

---

## 5. Notas de Implementação

### Por que não depender apenas de `read/problems`
Mesmo com `read/problems` na toollist, o loop ocorreria pois a causa raiz é a **ambiguidade de estado terminal**, não a falta de verificação de erros. A fix correta é tornar o estado terminal inequívoco via instrução explícita.

### Compatibilidade com outros modelos
Esta mudança beneficia todos os modelos (GPT-4.1, Qwen, DeepSeek, Claude) pois:
- Regras de parada explícitas são mais eficazes que regras implícitas em todos os LLMs
- O formato "1-2-3 + regra de ouro" é compreendido uniformemente

### Limitação conhecida
Se o modelo for instruído externamente (fora do PJE.md) a "sempre verificar erros após edição", o loop pode persistir. Nesse caso, a solução é mover a instrução de task_complete para o nível de system prompt do projeto, não apenas para o agente mode.
