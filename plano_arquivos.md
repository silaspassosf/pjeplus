# Plano 3 — Tamanho de Arquivos e Organização de Módulos

**Status:** Diagnóstico concluído — reorganização incremental por módulo  
**Risco:** Alto se feito de forma ampla / Baixo se feito arquivo por arquivo  
**Modelo alvo:** GPT-4.1 via PJE.md (Surgical Mode)

---

## Diagnóstico

### Arquivos acima do limiar (>500 linhas, exceto legado)

| Arquivo | Linhas | Situação | Ação |
|---|---|---|---|
| `Peticao/pet2.py` | 1687 | **Duplicata** de `pet_novo.py` — ambos com docstring "PEC/pet" | Candidato a remoção após validar de qual x.py importa |
| `Peticao/pet_novo.py` | 1560 | Versão mais recente — manter como canônica | Dividir em `pet_regras.py` + `pet_fluxo.py` |
| `carta/anexos.py` | 1284 | Processamento de anexos + navegação misturados | Dividir: `anexos_nav.py` + `anexos_proc.py` |
| `aud.py` (raiz) | 1195 | Duplicata de `bianca/aud.py` (mesmo tamanho 1086) | Verificar qual é canônico |
| `SISB/minutas/processor.py` | 1162 | Processamento + extração + formatação misturados | Dividir: `minutas_extrator.py` + `minutas_formatador.py` |
| `SISB/core.py` | 1078 | Core com responsabilidades mistas | Dividir: separar helpers em `SISB/helpers_utils.py` |
| `atos/judicial_fluxo.py` | 1011 | Fluxo + regras + callbacks misturados | Dividir: `judicial_regras.py` + `judicial_callbacks.py` |

### Fix/selenium_base/ — pasta com estrutura já boa
Os 8 arquivos de `Fix/selenium_base/` estão todos abaixo de 630 linhas e com
responsabilidades bem separadas. **Não alterar.**

### Módulos com responsabilidade única excessiva
`Fix/selenium_base/element_interaction.py` (626 linhas) — concentra 3 estratégias de
click + scroll + estado. Aceitável dado que **já é o módulo atômico correto**.

---

## Estratégia

**Não renomear arquivos com `mv`/`rename` — LLMs perdem rastreamento.**  
Padrão seguro: criar novo arquivo com funções extraídas → atualizar `__init__.py` →
manter arquivo original como re-exportador por 1 sprint → remover após validação.

---

## Etapas Incrementais

### Etapa 3.1 — Consolidar Peticao/

**Problema:** `pet.py` (739L), `pet2.py` (1687L), `pet_novo.py` (1560L) — 3 versões ativas.  
**Ação antes de qualquer divisão:** confirmar qual é importada em `x.py`.

<!-- pjeplus:apply -->
## Análise de Uso (executar antes do patch)

```bash
# Checar qual pet* é importado
py -c "import ast, pathlib; [print(f.name, [n.module for n in ast.walk(ast.parse(f.read_text(encoding='utf-8'))) if isinstance(n, ast.ImportFrom) and 'Peticao' in (n.module or '')]) for f in [pathlib.Path('x.py')]]"
```

**Se `pet_novo` for o canônico:**
1. Marcar `pet2.py` como `# DEPRECATED — usar pet_novo.py` no topo
2. Criar `Peticao/pet_fluxo.py` com as funções de orquestração (~30% do arquivo)
3. Criar `Peticao/pet_regras.py` com as regras de negócio (~50% do arquivo)
4. `pet_novo.py` vira fachada (~20%): importa de `pet_fluxo` e `pet_regras`

---

### Etapa 3.2 — Dividir atos/judicial_fluxo.py (1011 linhas)

**Arquivo:** `atos/judicial_fluxo.py`  
**Diagnóstico:** Contém fluxo principal + regras de negócio + callbacks de conclusão.

**Divisão proposta:**
```
atos/judicial_fluxo.py          (~400L) — orquestração principal — MANTIDO
atos/judicial_regras_negocio.py (~350L) — regras e validações — NOVO
atos/judicial_callbacks.py      (~200L) — callbacks e pós-processamento — NOVO
```

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: atos/__init__.py
operacao: verificar_e_adicionar
ancora: final do arquivo
```

```python
# Novos sub-módulos de judicial (após divisão)
# from atos.judicial_regras_negocio import *  # descomentar após criação
# from atos.judicial_callbacks import *        # descomentar após criação
```

> **Nota para Surgical Mode:** NÃO executar a divisão ainda — apenas preparar o
> `__init__.py` como receptor. A divisão real exige leitura completa de
> `judicial_fluxo.py` e é uma operação multi-arquivo.

---

### Etapa 3.3 — Eliminar duplicata aud.py raiz vs bianca/aud.py

**Situação:** `aud.py` (raiz, 1195L) e `bianca/aud.py` (1086L) — provavelmente
a versão da raiz é mais recente.

<!-- pjeplus:apply -->
## Análise (executar)

```bash
# Comparar primeiras 20 linhas
py -c "
a = open('aud.py', encoding='utf-8').readlines()[:20]
b = open('bianca/aud.py', encoding='utf-8').readlines()[:20]
print('raiz:', a[:3])
print('bianca:', b[:3])
"
```

**Decisão após análise:**
- Se raiz é superset de bianca: deprecar `bianca/aud.py`
- Se são independentes: renomear `aud.py` → `aud_raiz.py` com comentário de distinção

---

### Etapa 3.4 — SISB/minutas/processor.py (1162 linhas)

**Divisão proposta (low risk — módulo bem isolado):**
```
SISB/minutas/extrator.py    (~400L) — extração de dados das minutas
SISB/minutas/formatador.py  (~350L) — formatação e apresentação
SISB/minutas/processor.py   (~400L) — orquestração — MANTIDO como fachada
```

**Pré-condição:** Ler `SISB/standards.py` para garantir dataclasses compatíveis.

---

## Regra Geral Para Divisão Segura

```
1. Novo arquivo criado (nunca mover — copiar + adaptar)
2. Original mantido como re-exportador: from novo_arquivo import *
3. Validar: py -m py_compile arquivo_original.py
4. Testes manuais de 1 fluxo completo
5. Apenas após validação: remover funções do original
```

---

## Verificação por Etapa

```bash
# Etapa 3.1
py -m py_compile Peticao/pet_novo.py ; py -m py_compile Peticao/pet2.py

# Etapa 3.2  
py -m py_compile atos/judicial_fluxo.py ; py -m py_compile atos/__init__.py

# Etapa 3.4
py -m py_compile SISB/minutas/processor.py
```
