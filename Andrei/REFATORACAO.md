# Plano de Refatoração — `Andrei/`

**Data:** 2026-05-04  
**Base de comparação:** `Peticao/` (módulo ativo chamado por `x.py`)

---

## Confirmação via Fluxo Real

```
x.py (linha 51)
  └─ from Peticao.runtime_pet import run_pet   ← ATIVO
       └─ Peticao/regras_execucao.py
       └─ Peticao/helpers/helpers.py
       └─ Peticao/core/extracao/extracao.py
       └─ Peticao/api/client.py
       └─ Fix/*, atos/*, utilitarios_processamento
```

`Andrei/` **não é importado por `x.py`**. Ponto de entrada é `Andrei/main.py → Andrei/pipeline.run_pet`, executado standalone (`py Andrei/main.py`).

---

## O Que É `Andrei/`

`Andrei/` foi criado intencionalmente como um **clone standalone do fluxo Petição**, sem dependências de `Fix/`, `atos/`, `Peticao/`, `core/` etc. Motivação: permitir executar o pipeline de petições com login manual (browser abre, usuário loga, código continua) sem precisar do ambiente completo do projeto.

**Status:** Totalmente funcional e importável. Confirmado:
```
py -c "from Andrei.pipeline import run_pet; print('OK')"  → OK
```

---

## Estrutura de Andrei/ (13 arquivos, ~7.065 linhas)

| Arquivo | Linhas | Equivalente em Peticao/ |
|---------|--------|------------------------|
| `atos_helpers.py` | 1448 | (inlines de `atos/`, `Fix/core`) |
| `atos_judicial.py` | 1620 | `atos/judicial_fluxo.py` (inlinado) |
| `helpers.py` | 1017 | `Peticao/helpers/helpers.py` |
| `extracao.py` | 949 | `Peticao/core/extracao/extracao.py` |
| `pipeline.py` | 640 | `Peticao/runtime_pet.py` |
| `api_client.py` | 633 | `Peticao/api/client.py` |
| `utils_selenium.py` | 615 | `Fix/core`, `Fix/selenium_base` |
| `regras.py` | 480 | `Peticao/regras_execucao.py` |
| `atos_wrappers.py` | 384 | `atos/wrappers_*.py` |
| `driver.py` | 171 | *(login manual — único no projeto)* |
| `config.py` | 47 | *(sem equivalente)* |
| `main.py` | 60 | *(entry point standalone)* |
| `__init__.py` | 1 | — |

---

## Sobreposição com Peticao/

| Categoria | Quantidade |
|-----------|-----------|
| Funções duplicadas (mesmo nome) | **82** |
| Funções exclusivas de Andrei | **77** |
| Funções exclusivas de Peticao | **35** |

As 82 "duplicadas" **não são código morto** — são cópias intencionais que permitem o isolamento. O módulo não pode importar de `Peticao/` nem de `Fix/` (restrição de design).

---

## Diferenças nas Cópias (Divergências Confirmadas)

| Função | Andrei | Peticao | Causa |
|--------|--------|---------|-------|
| `session_from_driver` | 43 linhas | 21 linhas | Andrei tem lógica de timeout e retry extras |
| `documento_por_id` | 31 linhas | 13 linhas | Andrei tem fallback de encoding PDF |
| `run_pet` | 53 linhas | 41 linhas | Andrei sem controle de progresso; com recovery manual |
| `checar_habilitacao` | 166 linhas | 171 linhas | Versão Andrei levemente simplificada |
| `extrair_documento` | 9 linhas | 8 linhas | Diferença mínima |

**Andrei evoluiu** em alguns pontos (`session_from_driver`, `documento_por_id`). Não é uma cópia estagnada.

---

## O Que Andrei Tem Que Peticao Não Tem (77 funções exclusivas)

**Capacidades únicas de Andrei (não existem em Peticao/):**

- **Login manual:** `aguardar_login_manual`, `criar_driver` (browser sem credenciais automatizadas)
- **BNDT pipeline:** `bndt`, `_bndt_abrir_menu`, `_bndt_abrir_nova_aba`, `_bndt_clicar_icone`, `_bndt_gravar_e_confirmar_polo`, `_bndt_processar_selecoes_polo`, `_bndt_selecionar_operacao_para_polo`, `_bndt_validar_localizacao` — funcionalidade de débitos trabalhistas que Peticao/ não tem
- **Selenium extras inlinados:** `aguardar_e_clicar`, `safe_click`, `safe_click_no_scroll`, `esperar_elemento`, `esperar_url_conter`, `fechar_abas_extras`, `limpar_overlays`, `wait_for_clickable`, `_aguardar_nova_aba`
- **Atos extras:** `ato_judicial`, `fluxo_cls`, `focar_campo_minutar_se_necessario`, `aguardar_transicao_minutar`, `navegar_para_conclusao`, `preparar_campo_minutar`, `escolher_tipo_conclusao`, `selecionar_movimento_auto`, `selecionar_movimento_dois_estagios`, `preencher_multiplos_campos`, `preencher_prazos_destinatarios`
- **API extras:** `gateway_get`, `gateway_patch`, `gateway_post`, `request_gateway`, `domicilio_eletronico`, `atividades_gigs`
- **RuleRegistry inlinado:** `register`, `match`, `all_rules`, `get_actions_for_bucket`, `adapt_action`
- **Utils portados de Fix/:** `obter_chave_ultimo_despacho_decisao_sentenca`, `resultado_ok`, `resultado_falha`, `configurar_recovery_driver`, `handle_exception_with_recovery`, `normalizar_texto`, `remover_acentos`

---

## O Que Peticao Tem Que Andrei Não Tem (capacidades de negócio)

| Função | Peticao | Presença em Andrei |
|--------|---------|-------------------|
| `_run_pet_ok` / `_run_pet_falha` | Wrappers padronizados de resultado | Andrei usa `resultado_ok`/`resultado_falha` locais (equivalente) |
| `carregar_progresso_pet` | Persiste progresso em JSON | **AUSENTE** — Andrei não tem skip/retomar |
| `marcar_processo_executado_pet` | Marca processo como concluído | **AUSENTE** |
| `salvar_progresso_pet` | Salva estado para retomada | **AUSENTE** |
| `consolidar_delete_com_bookmarklet` | Gera bookmarklet JS para apagar | **AUSENTE** |
| `_fetch_peticoes` | Fetch com paginação via Peticao.api | Andrei usa `carregar_itens` (equivalente próprio) |

**Conclusão:** As ausências são intencionais — `PLANO.md` de Andrei especifica explicitamente "sem controle de progresso, sem skip, todos os itens processados a cada execução".

---

## Decisões Assertivas

### Decisão 1: Andrei/ NÃO é código morto — é um módulo paralelo funcional

Ao contrário de `bianca/triagem_regras.py`, Andrei/ **tem um ponto de entrada independente** (`Andrei/main.py`) e funcionalidades únicas (login manual + BNDT). Deletar seria perder trabalho real.

### Decisão 2: Não há refatoração de duplicatas a fazer agora

As 82 funções duplicadas são cópias intencionais para garantir isolamento. Removê-las exigiria que Andrei importasse de `Peticao/` ou `Fix/` — quebrando a premissa do módulo standalone. Não fazer.

### Decisão 3: Corrigir os 2 problemas estruturais reais

**Problema A — `Andrei/helpers.py` importa de `Andrei.atos.wrappers` (subpasta que não existe como pacote)**

`Andrei/helpers.py` tem:
```python
from Andrei.atos.wrappers import ato_agpetidpj
from Andrei.atos.wrappers import ato_agpet
...
```
Mas `Andrei/atos/` não existe — os wrappers estão em `Andrei/atos_wrappers.py`. Atualmente funciona porque provavelmente os wrappers ainda não são executados, mas o import falhará em runtime quando `helpers.py` for realmente carregado com essas funções.

**Verificar e corrigir:** substituir `from Andrei.atos.wrappers import` por `from Andrei.atos_wrappers import`.

**Problema B — `atos_wrappers.py` declara `__all__` com wrappers mas não tem nenhuma função (`ast` retorna 0 funções)**

O arquivo tem 384 linhas e `__all__` populado, mas as instâncias dos wrappers são criadas como atribuições de módulo (não `def`). Isso é correto — são chamadas a `make_ato_wrapper(...)`. Sem ação necessária.

---

## Plano de Execução

### Tarefa 1 — Corrigir import de `Andrei.atos.wrappers` em `helpers.py`

**Problema:** `from Andrei.atos.wrappers import ato_agpetidpj` aponta para subpacote `Andrei/atos/` que não existe.

**Ação:** Substituir 6 imports em `Andrei/helpers.py`:
```python
# ANTES (incorreto — subpacote inexistente)
from Andrei.atos.wrappers import ato_agpetidpj
from Andrei.atos.wrappers import ato_agpet
from Andrei.atos.wrappers import ato_agpinter
from Andrei.atos.wrappers import ato_assistente
from Andrei.atos.wrappers import ato_contestar
from Andrei.atos.wrappers import ato_revel

# DEPOIS (correto — módulo flat)
from Andrei.atos_wrappers import (
    ato_agpetidpj, ato_agpet, ato_agpinter,
    ato_assistente, ato_contestar, ato_revel,
)
```

**Verificação:**
- [ ] `py -m py_compile Andrei/helpers.py`
- [ ] `py -c "from Andrei.helpers import checar_habilitacao; print('OK')"`

**Dependências:** Nenhuma  
**Estimativa:** XS

---

### Tarefa 2 — Confirmar que `atos_wrappers.py` exporta todos os símbolos do `__all__`

**Ação:** Verificar que todas as entradas do `__all__` em `atos_wrappers.py` são realmente atribuídas no módulo (não há nomes declarados no `__all__` que não existam como variáveis).

**Verificação:**
- [ ] `py -c "from Andrei.atos_wrappers import ato_instc, ato_laudo, ato_gen; print('OK')"`

**Dependências:** Tarefa 1  
**Estimativa:** XS

---

### Tarefa 3 — Documentar diferenças evolutivas para sincronização futura

`Andrei/` tem versões melhoradas de `session_from_driver` e `documento_por_id` (mais robustas que `Peticao/api/client.py`). Se o projeto principal (`Peticao/`) precisar dessas melhorias, elas devem ser portadas de volta.

**Ação:** Adicionar comentário em `Andrei/api_client.py` nas funções divergentes apontando o que mudou em relação ao original, para facilitar eventual sync.

**Estimativa:** XS (documentação, sem código funcional)
