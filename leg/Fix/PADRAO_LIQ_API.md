# Função `padrao_liq()` - Extração Simples via API

## 📋 Visão Geral

A função `padrao_liq()` foi adicionada ao módulo `Fix/variaveis.py` e realiza uma **extração simples e direta** de dois dados essenciais:

1. **Existe perito com nome especificado?** (padrão: ROGERIO)
2. **Existe alguma reclamada sem advogado?**

---

## 🔧 Assinatura da Função

```python
def padrao_liq(client: PjeApiClient, id_processo: str, nome_perito: str = 'ROGERIO') -> Dict[str, bool]:
    """
    Extrai dados simples de liquidação via API PJe.
    
    Args:
        client: PjeApiClient configurado (com sessão autenticada)
        id_processo: ID do processo (formato CNJ ou ID interno)
        nome_perito: Nome do perito a procurar (padrão: 'ROGERIO', case-insensitive)
    
    Returns:
        {
            'tem_perito': bool,
            'existe_reclamada_sem_advogado': bool,
            'erro': str (opcional, se houver exceção)
        }
    """
```

---

## 📊 Estrutura de Retorno

```python
{
    'tem_perito': True,  # Existe perito com nome procurado?
    'existe_reclamada_sem_advogado': False  # Existe alguma reclamada sem advogado?
}
```

Ou em caso de erro:

```python
{
    'tem_perito': False,
    'existe_reclamada_sem_advogado': False,
    'erro': 'Descrição do erro'
}
```

---

## 🚀 Exemplo de Uso

```python
from Fix.variaveis import session_from_driver, PjeApiClient, padrao_liq

# 1. Criar sessão e cliente a partir do driver Selenium
sess, trt_host = session_from_driver(driver)
client = PjeApiClient(sess, trt_host)

# 2. Chamar função com nome padrão (ROGERIO)
resultado = padrao_liq(client, '1002187-36.2025.5.02.0703')

# 3. Acessar dados
if resultado.get('tem_perito'):
    print("✅ Existe perito ROGERIO")
else:
    print("❌ Não existe perito ROGERIO")

if resultado.get('existe_reclamada_sem_advogado'):
    print("⚠️ Existe reclamada SEM advogado")
else:
    print("✅ Todas as reclamadas têm advogado")

# 4. Usar parâmetro customizado
resultado = padrao_liq(client, '1002187-36.2025.5.02.0703', nome_perito='JOAO')
if resultado.get('tem_perito'):
    print("✅ Existe perito JOAO")
```

---

## 📡 APIs Utilizadas

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/pje-comum-api/api/processos/id/{id}/pericias` | GET | Lista perícias com nome do perito |
| `/pje-comum-api/api/processos/id/{id}/partes` | GET | Lista partes com info de advogados |

Chamadas diretas via:
- `client.pericias(id_processo)`
- `client.partes(id_processo)`

---

## 🔍 Lógica Detalhada

### 1️⃣ Verificação de Perito

```python
for pericia in pericias_list:
    nome_perito_api = pericia.get('nomePerito') or pericia.get('perito')
    
    if 'ROGERIO' in nome_perito_api.upper():
        tem_perito = True
        break
```

**Busca:**
- Case-insensitive (ROGERIO, rogerio, Rogerio = igual)
- Por substring (funciona para "ROGERIO SANTOS", "JOÃO ROGERIO")
- Customizável via parâmetro `nome_perito`

**Campos verificados:**
- `nomePerito`
- `perito`
- `responsavel`

---

### 2️⃣ Verificação de Reclamada sem Advogado

```python
for parte in partes:
    polo = parte.get('tipoPolo', '').upper()
    
    # É reclamada?
    eh_reclamada = 'PASSIVO' in polo or 'RECLAMADO' in polo or 'REU' in polo
    
    if eh_reclamada:
        # Tem advogado?
        tem_advogado = bool(
            parte.get('representante') or
            parte.get('procuradores') or
            parte.get('advogado')
        )
        
        if not tem_advogado:
            existe_reclamada_sem_advogado = True
            break
```

**Critérios:**
- Conta como **reclamada**: polo contém 'PASSIVO', 'RECLAMADO', 'REU', 'EXECUTADO'
- Conta como **com advogado**: se tem `representante`, `procuradores`, ou `advogado`
- **Resultado:** True se ALGUMA reclamada não tem advogado

---

## ⚠️ Tratamento de Erros

```python
resultado = padrao_liq(client, '1002187-36.2025.5.02.0703')

if 'erro' in resultado:
    print(f"Erro: {resultado['erro']}")
else:
    # Usar dados com segurança
    if resultado['tem_perito']:
        # fazer algo
```

---

## 💡 Casos de Uso

### Caso 1: Liquidação Simples
```python
# Verificar se processo pode ser automatizado
resultado = padrao_liq(client, proc_id)

if not resultado.get('existe_reclamada_sem_advogado'):
    # Pode automatizar - todas têm advogado
    executar_ato_ceju(driver)
```

### Caso 2: Perícias
```python
# Verificar se tem perito específico
resultado = padrao_liq(client, proc_id, nome_perito='ROGERIO')

if resultado.get('tem_perito'):
    # Aguardar laudo
    criar_gigs(driver, "5", "Aguardando laudo perito")
```

### Caso 3: Religa
```python
# Combinação com outras verificações
resultado = padrao_liq(client, proc_id)

if resultado.get('existe_reclamada_sem_advogado'):
    # Pode ser RELIGA - processar com cuidado
    print("Verificar manualmente - reclamada sem advogado")
```

---

## 🧪 Testes Recomendados

```python
# Teste 1: Perito existe
resultado = padrao_liq(client, '1002187-36.2025.5.02.0703')
assert resultado['tem_perito'] == True

# Teste 2: Perito não existe
resultado = padrao_liq(client, '1002187-36.2025.5.02.0703', nome_perito='INEXISTENTE')
assert resultado['tem_perito'] == False

# Teste 3: Reclamada sem advogado
resultado = padrao_liq(client, '1000000-00.0000.0.00.0000')
assert resultado['existe_reclamada_sem_advogado'] == True

# Teste 4: Parâmetro customizado
resultado = padrao_liq(client, '1002187-36.2025.5.02.0703', nome_perito='JOAO')
# resultado['tem_perito'] depende da presença de JOAO
```

---

## 📝 Notas

1. **Simples:** Apenas 2 informações essenciais, sem excesso de dados
2. **Rápido:** 2 chamadas API mínimas
3. **Flexível:** Parametrizado para buscar qualquer perito
4. **Robusto:** Trata múltiplos formatos de resposta da API
5. **Seguro:** Retorna sempre um dict válido, mesmo com erro
