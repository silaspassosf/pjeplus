# Plano Granular — FUT-1, FUT-2, FUT-5, FUT-6 (migração completa, sem shims)

**Data:** 2026-05-04  
**Estratégia:** Migração completa — deletar arquivos intermediários, importar direto da fonte  
**Fora do escopo:** FUT-3 (monolitos congelados), FUT-4 (framework Selenium)

---

## Resumo do Estado Atual

| Item | Estimativa original | Real | Resultado alvo |
|:----:|:-------------------:|:----:|:--------------|
| FUT-6 | 2-4h | 5 arquivos, 10 consumidores | Deletar `Fix/selenium_base/` (5 arquivos) — importar direto de `Fix.core`/`Fix.browser_suporte` |
| FUT-5 | 4-8h | 2 funções em x.py + candidatos | `Fix/tipos.py` + 3 arquivos atualizados |
| FUT-1 | 4-8h | 41 bare excepts acessíveis (32 nos monolitos, deferido) | Zero `except:` nos 11 arquivos não-congelados |
| FUT-2 | 20-40h | ~230 time.sleep fora dos monolitos | Catalogo + substituição DOM-settle por WebDriverWait |

---

## Grafo de Dependências

```
FUT-6 → nenhum bloqueio (iniciar primeiro — limpa namespace)
FUT-5 → nenhum bloqueio (paralelo com FUT-6)
FUT-1 → nenhum bloqueio (paralelo; FUT-6 recomendado antes de editar browser_suporte)
FUT-2 → S2-1 (catalogação) obrigatória antes das demais fases de substituição
```

**Ordem recomendada:** FUT-6 ‖ FUT-5 → FUT-1 → S2-1 → FUT-2 (fases S2-2..S2-7)

---

## FUT-6: Deletar Fix/selenium_base/ — migrar 10 consumidores para importar direto

### Objetivo final

Deletar os 5 arquivos do pacote `Fix/selenium_base/` e migrar todos os 10 consumidores
para importar diretamente de `Fix.core` ou `Fix.browser_suporte`.

**Redução:** 5 arquivos a menos no repositório, zero camadas de indireção.

### Mapa de importações (antes → depois)

| Consumidor | Símbolos | Fonte final |
|-----------|---------|------------|
| `atos/judicial_fluxo.py` L11-14 | `aguardar_e_clicar, safe_click_no_scroll` | `Fix.browser_suporte` |
| `atos/judicial_fluxo.py` L11-14 | `safe_click, esperar_elemento, wait_for_clickable, esperar_url_conter, preencher_multiplos_campos` | `Fix.core` |
| `atos/judicial_navegacao.py` L9-11 | `aguardar_e_clicar, safe_click_no_scroll` | `Fix.browser_suporte` |
| `atos/judicial_navegacao.py` L9-11 | `safe_click, esperar_url_conter` | `Fix.core` |
| `atos/judicial_modelos.py` L10-12 | `aguardar_e_clicar, safe_click_no_scroll` | `Fix.browser_suporte` |
| `atos/judicial_modelos.py` L10-12 | `safe_click, esperar_url_conter` | `Fix.core` |
| `atos/judicial_helpers.py` L1 | `safe_click` | `Fix.core` |
| `atos/judicial_utils.py` L11,L17,L120,L152 | `preencher_multiplos_campos` | `Fix.core` |
| `atos/judicial_utils.py` L11,L17,L120,L152 | `safe_click_no_scroll` | `Fix.browser_suporte` |
| `atos/movimentos_fluxo.py` L6 | `safe_click_no_scroll` | `Fix.browser_suporte` |
| `Mandado/regras.py` L53,L79 | `esperar_elemento, preencher_campo` | `Fix.core` |
| `Mandado/regras.py` L53 | `aguardar_e_clicar` | `Fix.browser_suporte` |
| `Mandado/entrada_api.py` L33 | `safe_click` | `Fix.core` |
| `Mandado/entrada_api.py` L33 | `aguardar_e_clicar` | `Fix.browser_suporte` |
| `Mandado/apoio_fluxos.py` L28 | `aguardar_e_clicar` | `Fix.browser_suporte` |
| `Triagem/dom.py` L38,L571 | `safe_click, esperar_elemento` | `Fix.core` |
| `Triagem/dom.py` L38,L571 | `aguardar_e_clicar` | `Fix.browser_suporte` |

### Tarefa F6-1: Migrar atos/ (6 arquivos)

Usando o mapa acima, substituir cada linha de import `Fix.selenium_base.*` pelo par direto `Fix.browser_suporte` / `Fix.core`. Atenção: `judicial_utils.py` tem 2 lazy imports adicionais em L120 e L152 dentro de funções — substituir também.

**Resumo por arquivo:**

```
judicial_fluxo.py  L11-14 → from Fix.browser_suporte import aguardar_e_clicar, safe_click_no_scroll
                            from Fix.core import safe_click, esperar_elemento, wait_for_clickable, esperar_url_conter, preencher_multiplos_campos
judicial_navegacao L9-11  → from Fix.browser_suporte import aguardar_e_clicar, safe_click_no_scroll
                            from Fix.core import safe_click, esperar_url_conter
judicial_modelos   L10-12 → from Fix.browser_suporte import aguardar_e_clicar, safe_click_no_scroll
                            from Fix.core import safe_click, esperar_url_conter
judicial_helpers   L1     → from Fix.core import safe_click
judicial_utils     L11,17,120,152 → from Fix.core import preencher_multiplos_campos
                                    from Fix.browser_suporte import safe_click_no_scroll
movimentos_fluxo   L6     → from Fix.browser_suporte import safe_click_no_scroll
```

**Gate:** `py -m py_compile atos/judicial_fluxo.py atos/judicial_navegacao.py atos/judicial_modelos.py atos/judicial_helpers.py atos/judicial_utils.py atos/movimentos_fluxo.py`

---

### Tarefa F6-2: Migrar Mandado/ e Triagem/ (4 arquivos)

```
Mandado/entrada_api.py L33   → from Fix.browser_suporte import aguardar_e_clicar
                               from Fix.core import safe_click
Mandado/apoio_fluxos.py L28  → from Fix.browser_suporte import aguardar_e_clicar
Mandado/regras.py L53,L79    → from Fix.core import esperar_elemento, preencher_campo
                               from Fix.browser_suporte import aguardar_e_clicar
Triagem/dom.py L38           → from Fix.browser_suporte import aguardar_e_clicar
Triagem/dom.py L571 (lazy)   → from Fix.core import safe_click, esperar_elemento
                               from Fix.browser_suporte import aguardar_e_clicar
```

**Gate:** `py -m py_compile Mandado/entrada_api.py Mandado/apoio_fluxos.py Mandado/regras.py Triagem/dom.py`

---

### Tarefa F6-3: Deletar Fix/selenium_base/ (5 arquivos)

```powershell
Remove-Item -Recurse -Force D:\PjePlus\Fix\selenium_base
```

**Arquivos deletados:** `__init__.py`, `click_operations.py`, `element_interaction.py`, `wait_operations.py`, `retry_logic.py`

**Gate final:** `py test_imports.py` verde (0 failed) + `py -c "from Fix.browser_suporte import aguardar_e_clicar, safe_click_no_scroll; from Fix.core import safe_click, esperar_elemento, com_retry; print('F6 OK')"`

**Depends on:** F6-1, F6-2 completos

---

## FUT-5: TypedDict — ResultadoFluxo

### Tarefa T5-1: Criar Fix/tipos.py

```python
# Fix/tipos.py (novo arquivo)
from typing import TypedDict, Optional, Any

class ResultadoFluxo(TypedDict, total=False):
    sucesso: bool      # obrigatorio na pratica
    status: str        # "OK" | "ERRO" | "AVISO"
    erro: str          # presente quando sucesso=False
    dados: Any         # payload opcional do fluxo
```

**Gate:** `py -c "from Fix.tipos import ResultadoFluxo; print('OK')"`

---

### Tarefa T5-2: Aplicar em x.py

```python
# ANTES (x.py L141):
def normalizar_resultado(resultado: Any) -> Dict[str, Any]:
# DEPOIS:
def normalizar_resultado(resultado: Any) -> ResultadoFluxo:

# ANTES (x.py L153):
                    normalizar: bool = True, on_none_error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
# DEPOIS:
                    normalizar: bool = True, on_none_error: Optional[ResultadoFluxo] = None) -> ResultadoFluxo:

# Adicionar ao bloco de imports de x.py:
from Fix.tipos import ResultadoFluxo
```

**Gate:** `py -m py_compile x.py`

---

### Tarefa T5-3: Aplicar em Mandado/core.py e Mandado/entrada_api.py

```python
# Mandado/core.py L253:
# ANTES:
def iniciar_fluxo_robusto(driver: WebDriver) -> Dict[str, Any]:
# DEPOIS:
def iniciar_fluxo_robusto(driver: WebDriver) -> ResultadoFluxo:
# (+ adicionar import: from Fix.tipos import ResultadoFluxo)

# Mandado/entrada_api.py L90 (a funcao que retorna dict puro):
# ANTES:
) -> dict:
# DEPOIS:
) -> ResultadoFluxo:
# (+ adicionar import: from Fix.tipos import ResultadoFluxo)
```

**Gate:** `py -m py_compile Mandado/core.py Mandado/entrada_api.py` + `py test_imports.py`

---

## FUT-1: Bare `except:` — substituição exata por arquivo

### Regras de substituição

| Contexto do bloco | Substituição |
|-------------------|-------------|
| `except: pass` — supressão silenciosa | `except Exception: pass  # supressão intencional` |
| `except: continue` — loop, item individual | `except Exception: continue` |
| `except:` com log/retorno | `except Exception as e:` + manter corpo |
| `except:` capturando `KeyboardInterrupt` / `SystemExit` implicitamente | `except Exception as e:` (quebra intencional — não capturar sinais) |

---

### Tarefa E1-1: Fix/browser_suporte.py (6 bare excepts)

| Linha | Contexto | Substituição |
|:-----:|---------|-------------|
| 187 | `except:` após `logger.debug(...)` com formatação de URL | `except Exception: logger.debug("%s abas detectadas", len(abas))` |
| 212 | `except:` após tentativa de ler URL da nova aba | `except Exception: logger.debug('Nova aba aberta')` |
| 315 | `except:` após `url_aba = driver.current_url[:60]` | `except Exception: url_aba = "URL nao disponivel"` |
| 469 | `except:` após `scroll strategy 1` — fallback chain | `except (Exception, AttributeError):` |
| 478 | `except:` após `scroll strategy 2` — fallback chain | `except (Exception, AttributeError): return False` |
| 546 | `except:` em `is_headless_mode` final | `except Exception: return False` |

**Gate:** `py -m py_compile Fix/browser_suporte.py`

---

### Tarefa E1-2: Fix/diagnostico_runtime.py (2 bare excepts)

| Linha | Contexto | Substituição |
|:-----:|---------|-------------|
| 220 | `except: pass` após `contexto['url'] = driver.current_url` | `except Exception: pass  # URL nao disponivel` |
| 273 | `except: pass` após `overlays = driver.execute_script(...)` | `except Exception: pass  # overlays nao disponivel` |

**Gate:** `py -m py_compile Fix/diagnostico_runtime.py`

---

### Tarefa E1-3: Módulos de negócio (7 bare excepts)

| Arquivo | Linha | Contexto | Substituição |
|---------|:-----:|---------|-------------|
| `atos/judicial_helpers.py` | 130 | `except:` após WebDriverWait para `div.post-it-set` | `except Exception: return False` |
| `Mandado/apoio_fluxos.py` | 236 | `except: continue` dentro de loop de documentos | `except Exception: continue` |
| `Mandado/core.py` | 214 | `except: continue` dentro de loop de chips | `except Exception: continue` |
| `Mandado/entrada_api.py` | 631 | `except: pass` após `body.send_keys(Keys.ESCAPE)` | `except Exception: pass` |
| `PEC/anexos/anexos_juntador_metodos.py` | 379 | `except:` após `salvar_btn.is_enabled()` | `except Exception: logger.info('[JUNTADA] Botao Salvar nao disponivel - documento ja salvo')` |
| `Peticao/core/extracao/extracao.py` | 346 | `except: pass` após regex aria-label | `except Exception: pass` |
| `Peticao/core/extracao/extracao.py` | 437 | `except:` após `datetime.fromisoformat` | `except Exception: processo_memoria["dtAutuacao"] = dt` |
| `Triagem/dom.py` | 1028 | `except: continue` em loop de parsing | `except Exception: continue` |

**Gate:** `py -m py_compile atos/judicial_helpers.py Mandado/apoio_fluxos.py Mandado/core.py Mandado/entrada_api.py PEC/anexos/anexos_juntador_metodos.py Peticao/core/extracao/extracao.py Triagem/dom.py`

---

### Tarefa E1-4: SISB/ (23 bare excepts)

**Padrão:** Alta concentração em `SISB/batch.py` (17) dentro de loops de processamento de ordens — todos os `except: pass` em loops individuais viram `except Exception: continue` ou `except Exception: pass` conforme o bloco.

| Arquivo | Linhas | Padrão |
|---------|--------|--------|
| `SISB/batch.py` | 144, 201, 212 | `except: pass` em cleanup de driver → `except Exception: pass` |
| `SISB/batch.py` | 227, 264, 268, 292, 297, 318, 322 | `except: continue` em loop de processos → `except Exception: continue` |
| `SISB/batch.py` | 360, 363, 376, 425, 435, 454, 472 | `except: pass` ou `continue` em loop de ordem → classificar lendo contexto |
| `SISB/ordens_dados_navegacao.py` | 185, 213 | `except:` após `safe_click` no dropdown — fallback | `except Exception:` |
| `SISB/ordens_dados_navegacao.py` | 273 | `except:` após `send_keys(Keys.ESCAPE)` | `except Exception: continue` |
| `SISB/ordens_dados_navegacao.py` | 284 | `except:` após `send_keys(Keys.ESCAPE)` | `except Exception: continue` |
| `SISB/ordens_execucao.py` | 152, 176 | `except:` em validação de elemento | `except Exception:` |

**Gate:** `py -m py_compile SISB/batch.py SISB/ordens_dados_navegacao.py SISB/ordens_execucao.py` + `py test_imports.py`

---

### Tarefa E1-5: tools/probe.py (2 bare excepts)

Linhas 232 e 332 — ferramenta de diagnóstico, não está no caminho de produção.

**Gate:** `py -m py_compile tools/probe.py`

---

### Checkpoint FUT-1

```powershell
# Verificar zero bare excepts nos arquivos acessíveis:
Get-ChildItem Fix/browser_suporte.py, Fix/diagnostico_runtime.py, SISB/batch.py,
  SISB/ordens_dados_navegacao.py, SISB/ordens_execucao.py,
  atos/judicial_helpers.py, Mandado/apoio_fluxos.py, Mandado/core.py,
  Mandado/entrada_api.py, PEC/anexos/anexos_juntador_metodos.py,
  Peticao/core/extracao/extracao.py, Triagem/dom.py, tools/probe.py |
  Select-String "^\s*except:\s*$"
# Resultado esperado: 0 matches
```

Monolitos congelados (Fix/core.py 13, Fix/extracao.py 14, Fix/utils.py 5) — deferido para FUT-3.

---

## FUT-2: Substituir time.sleep por WebDriverWait

### Categorias de classificação

| Categoria | Ação |
|-----------|------|
| **DOM-settle** — aguarda DOM estabilizar após clique/submit | Substituir por `esperar_elemento()` ou `WebDriverWait(...).until(EC.presence_of_element_located(...))` |
| **UI-transition** — aguarda mudança de estado visível | Substituir por `WebDriverWait(...).until(EC.visibility_of_element_located(...))` ou `EC.element_to_be_clickable(...)` |
| **genuine-delay** — rate-limit ou regra de negócio | Manter com comentário `# rate-limit` ou `# estabilizacao PJe` |

**Regra de ouro:** Nunca remover `time.sleep` sem substituir por condição verificável.

---

### Tarefa S2-1: Catálogo de classificação (revisão humana obrigatória)

Tabela pré-preenchida para os 5 arquivos com maior concentração:

**Fix/browser_suporte.py (12):**

| Linha | Valor | Categoria | Substituto proposto |
|:-----:|-------|:---------:|---------------------|
| 239 | 0.2s | DOM-settle | `WebDriverWait(driver, 5).until(EC.staleness_of(element))` ou omitir |
| 310 | 0.1s | DOM-settle | omitir — switch já garante estado |
| 324 | 0.2s | DOM-settle | omitir — retry já volta |
| 330 | 0.1s | DOM-settle | omitir |
| 334 | 0.3s | DOM-settle | omitir |
| 343 | 0.1s | DOM-settle | omitir |
| 346 | 0.1s | DOM-settle | omitir |
| 443 | 0.2s | DOM-settle | `esperar_elemento(driver, seletor, timeout=3)` |
| 467 | 0.3s | DOM-settle | dentro de `scroll_to_element_safe` — omitir com JS |
| 476 | 0.3s | DOM-settle | idem |
| 517 | 0.4s | UI-transition | `WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))` |
| 527 | 0.2s | DOM-settle | omitir — JS click já executado |

**atos/judicial_fluxo.py (10):**

| Linha | Valor | Categoria | Substituto proposto |
|:-----:|-------|:---------:|---------------------|
| Ler antes de classificar | — | — | Leitura obrigatória das linhas |

**Prazo/loop_lote.py (21) — maior arquivo:**

| Linha | Valor | Categoria | Nota |
|:-----:|-------|:---------:|------|
| Ler antes de classificar | — | — | Leitura obrigatória |

**Regra de aprovação:** Cada `time.sleep` marcado como `DOM-settle` ou `UI-transition` requer
revisão de contexto (o que a linha anterior faz?) antes de substituir. Não substituir por inferência.

---

### Tarefa S2-2: Fix/browser_suporte.py (12 time.sleep)

**Dependências:** S2-1 (catálogo), FUT-6 (arquivo já editado)

Para cada sleep classificado como `DOM-settle` com valor ≤ 0.3s após `execute_script` ou `switch_to.window`:

```python
# Padrão DOM-settle após execute_script (scrollIntoView) — linhas 467, 476:
# ANTES:
driver.execute_script("arguments[0].scrollIntoView(...);", element)
time.sleep(0.3)
# DEPOIS:
driver.execute_script("arguments[0].scrollIntoView(...);", element)
# (remover sleep — JS é síncrono, scrollIntoView não precisa de wait)

# Padrão UI-transition antes de click — linha 517:
# ANTES:
time.sleep(0.4)
element.click()
# DEPOIS:
WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))
element.click()
```

**Gate:** `py -m py_compile Fix/browser_suporte.py` + `py test_imports.py`

---

### Tarefa S2-3: atos/ (~51 time.sleep — 10 arquivos)

**Para cada arquivo:** ler contexto das linhas com `time.sleep`, classificar, substituir os `DOM-settle`.

Padrão mais comum em `atos/`:

```python
# DOM-settle após aguardar_e_clicar — substituir por esperar_elemento:
# ANTES:
aguardar_e_clicar(driver, '#seletor', timeout=10)
time.sleep(0.3)
# DEPOIS:
aguardar_e_clicar(driver, '#seletor', timeout=10)
esperar_elemento(driver, '#resultado-esperado', timeout=5)

# genuine-delay entre etapas de formulário (>0.5s) — manter:
time.sleep(1)  # estabilizacao PJe apos submit
```

**Gate por arquivo:** `py -m py_compile atos/judicial_fluxo.py atos/judicial_navegacao.py atos/movimentos_fimsob.py atos/movimentos_despacho.py atos/movimentos_fluxo.py`

---

### Tarefa S2-4: SISB/ fora de monolitos (~47 time.sleep)

Arquivos: `SISB/ordens_dados_navegacao.py` (14), `SISB/core.py` (13), `SISB/Core/login.py` (11), `SISB/Core/utils_web.py` (5), `SISB/batch.py` (3).

**Padrão identificado em `SISB/ordens_dados_navegacao.py`:**

```python
# ANTES (loop de dropdown — L188, L203, L215):
safe_click(driver, select_element, 'click')
time.sleep(0.8)
opcoes = WebDriverWait(driver, 3.0).until(EC.presence_of_all_elements_located(...))
# DEPOIS:
safe_click(driver, select_element, 'click')
opcoes = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located(
    (By.CSS_SELECTOR, "mat-option[role='option']")
))

# ANTES (após ESC — L275, L285):
driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
time.sleep(0.3)
# DEPOIS:
driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
# (remover sleep — ESC é síncrono; next iteration não precisa de wait)
```

**Gate:** `py -m py_compile SISB/ordens_dados_navegacao.py SISB/core.py SISB/batch.py` + `py test_imports.py`

---

### Tarefa S2-5: Prazo/ (~28 time.sleep)

Arquivos: `Prazo/loop_lote.py` (21), `Prazo/loop_execucao_final.py` (3), `Prazo/loop_orquestrador.py` (3), `Prazo/p2b_documentos.py` (1).

`loop_lote.py` tem 21 sleeps — maior concentração fora dos monolitos. Ler cada um antes de classificar.

**Gate:** `py -m py_compile Prazo/loop_lote.py Prazo/loop_execucao_final.py` + `py test_imports.py`

---

### Tarefa S2-6: Mandado/ e PEC/ (~37 time.sleep)

Arquivos: `Mandado/fluxo_argos.py` (13), `Mandado/entrada_api.py` (9), `Mandado/core.py` (6), `PEC/carta_execucao.py` (12), `PEC/anexos/anexos_juntador_metodos.py` (10), `PEC/core_navegacao.py` (4).

**Gate:** `py -m py_compile Mandado/fluxo_argos.py PEC/carta_execucao.py PEC/anexos/anexos_juntador_metodos.py` + `py test_imports.py`

---

### Tarefa S2-7: Triagem/dom.py (22 time.sleep)

Ler cada `time.sleep` no contexto. A maioria está em código comentado (blocos `# FLUXO ANTIGO`) — verificar se são comentados antes de editar. Código ativo: `time.sleep(2)` após `criar_lembrete_posit` (linha ~823) é um genuine-delay — manter com comentário.

**Gate:** `py -m py_compile Triagem/dom.py` + `py test_imports.py`

---

### Checkpoint FUT-2

- [ ] `py test_imports.py` verde
- [ ] Cada `time.sleep` substituído tem comentário `# substituído por WebDriverWait` ou `# rate-limit: manter`
- [ ] Monolitos congelados (Fix/extracao.py 52, Fix/core.py 33, Fix/utils.py 25) — registrado como pendente FUT-3

---

## Ordem de Execução e Riscos

```
Sprint 1 (~2h):  FUT-6 (F6-1 → F6-2 → F6-3) ‖ FUT-5 (T5-1 → T5-2 → T5-3)
Sprint 2 (~4h):  FUT-1 (E1-1 → E1-2 → E1-3 → E1-4 → E1-5)
Sprint 3 (~2h):  S2-1 (catalogação — revisão humana obrigatória)
Sprint 4-7 (~16h): S2-2 → S2-3 → S2-4 → S2-5 → S2-6 → S2-7
```

| Risco | Impacto | Mitigação |
|-------|:-------:|-----------|
| Import circular ao importar `Fix.core` em arquivo que já importa indiretamente | Médio | Verificar com `py -m py_compile` após cada F6-x |
| `time.sleep` em `Triagem/dom.py` está em código comentado — não substituir | Baixo | Verificar se linha está ativa (não comentada) antes de editar |
| `SISB/batch.py` tem padrão de `except:` em loop — mudar para `Exception` pode alterar fluxo se `StopIteration` for capturada | Médio | Ler bloco completo antes de substituir |
| `Prazo/loop_lote.py` (21 sleeps) — alguns podem ser genuine-delay entre chamadas ao PJe | Alto | Nunca remover sem classificar em S2-1 primeiro |
| Deletar `Fix/selenium_base/` antes de migrar todos os consumidores | Alto | F6-3 é a última tarefa, depois de F6-1 e F6-2 |

**Fora do escopo deste plano:** FUT-3 (monolitos), FUT-4 (testes Selenium), 32 bare excepts nos monolitos, 110 time.sleep nos monolitos.

