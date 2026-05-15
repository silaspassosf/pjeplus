# Plano: Troca de Modelo vs Alteração de Meio de Expedição

## Contexto

Há **dois fluxos diferentes** que estão sendo confundidos em `pec_ord`:

### Fluxo 1: Alterar Meio de Expedição → Troca de Modelo
**Aplicável a: `pec_decisao`, `pec_idpj` e similares**

```
Seleção de Destinatários
    ↓
Verifica tipos de expediente
    ↓
Se "Correios" está nos tipos de expediente:
    ↓
    Altera Domicílio Eletrônico → Correios
    ↓
    Troca modelo (zordc ou zsumc) para linhas com Correios
    ↓
Salva minuta
```

**Funções envolvidas:**
- `alterar_meio_expedicao()` - muda Domicílio para Correios
  - Dentro dela: chama `trocar_modelo_minuta()` se `alterados > 0`
- `trocar_modelo_minuta()` - procura linhas com Correios e troca modelo

**Configuração no wrapper:**
```python
endereco_tipo='correios'    # Dispara alterar_meio_expedicao()
trocar_modelo=False/ausente  # Não usado neste caso
```

---

### Fluxo 2: Apenas Troca de Modelo (Sem Alterar Meio de Expedição)
**Aplicável a: `pec_ord`, `pec_sum` (notificações)**

```
Seleção de Destinatários
    ↓
Verifica tipos de expediente
    ↓
Se "Correios" está nos tipos de expediente:
    ↓
    Troca modelo (zordc) diretamente
    ↓
Salva minuta
```

**Diferença crítica:** 
- NÃO altera meio de expedição (permanece Domicílio Eletrônico ou outro)
- Apenas troca o modelo do ato para versão apropriada

**Configuração no wrapper (CORRIGIDA):**
```python
endereco_tipo=None          # NÃO dispara alterar_meio_expedicao()
trocar_modelo=True          # Indica que precisa trocar modelo
```

---

## Problema Atual

**Em `pec_ord` e `pec_sum`:**
```python
endereco_tipo='correios'    # ❌ ERRADO
trocar_modelo=True          # ✅ CORRETO
```

### O que acontece com `endereco_tipo='correios'`:

1. Entra em `alterar_meio_expedicao()`
2. Procura por "Domicílio Eletrônico" e tenta alterar para Correios
3. Se encontrar, chama `trocar_modelo_minuta()`

### O problema:

- Se `pec_ord` começa com Domicílio Eletrônico e **não há "Correios"** nos tipos de expediente
  - `alterar_meio_expedicao()` retorna `False` (nenhuma linha encontrada)
  - `trocar_modelo_minuta()` **nunca é chamada**

- Se há "Correios" nos tipos de expediente mas ele está em **outra linha** (não Domicílio)
  - Há confusão entre qual linha mudar e qual modelo trocar

---

## Solução

### 1. **Remover `endereco_tipo='correios'` de `pec_ord` e `pec_sum`**

```python
pec_ord = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zordd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    # endereco_tipo=None,  # ← REMOVER essa linha
    trocar_modelo=True,  # ← MANTER só isso
    wrapper_name='pec_ord'
)
```

### 2. **Adicionar lógica de troca de modelo direta em `comunicacao.py`**

Após `selecionar_destinatarios()`, adicionar:

```python
# Se trocar_modelo=True, executar troca de modelo diretamente
# (independente de alterar_meio_expedicao)
if call_kwargs.get('trocar_modelo') and not endereco_tipo:
    log_fn("[COMUNICACAO][ORQUESTRA] Executando troca de modelo (sem alterar meio)")
    trocar_modelo_minuta(driver, debug=debug, log=log_fn)
```

---

## Responsabilidades de Cada Função

### `alterar_meio_expedicao()`
- **Responsabilidade:** Alterar Domicílio Eletrônico → Correios
- **Quando chamada:** Se `endereco_tipo == 'correios'`
- **Efeito colateral:** Chama `trocar_modelo_minuta()` se houve alterações

### `trocar_modelo_minuta()`
- **Responsabilidade:** Trocar modelo em linhas com Correios
- **Quando chamada:** 
  - Dentro de `alterar_meio_expedicao()` se houve alterações (fluxo 1)
  - Diretamente em `make_comunicacao_wrapper` se `trocar_modelo=True` (fluxo 2)
- **Precisa:** Linhas com "Correios" já presentes na tabela

---

## Checklist de Implementação

- [ ] Remover `endereco_tipo='correios'` de `pec_ord`
- [ ] Remover `endereco_tipo='correios'` de `pec_sum`
- [ ] Adicionar lógica de trocar_modelo direta em `comunicacao.py`
- [ ] Testar `pec_ord` com processo que tem Correios nos tipos de expediente
- [ ] Testar `pec_decisao` (deve continuar funcionando com alteração de meio + troca)

---

## Resumo das Diferenças

| Aspecto | `pec_decisao` (Fluxo 1) | `pec_ord` (Fluxo 2) |
|--------|------------------------|---------------------|
| `endereco_tipo` | `'correios'` | `None` |
| `trocar_modelo` | `False/ausente` | `True` |
| Altera meio? | ✅ Sim (Domicílio → Correios) | ❌ Não |
| Troca modelo? | ✅ Sim | ✅ Sim |
| Onde chamadas | `alterar_meio_expedicao()` | `make_comunicacao_wrapper()` direto |
| Modelo de entrada | 'xs dec reg' | 'zordd' |
| Modelo saída | Mesmo + linhas Correios | 'zordc' se Correios presente |

