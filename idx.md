# 🧠 Manifesto de Arquitetura e Contexto - PJePlus (IDX)

## 🎯 1. Visão Geral e Objetivos do Projeto
O **PJePlus** é um ecossistema avançado de automação em Python (Selenium) focado no Processo Judicial Eletrônico (PJe). 
* **Navegador Alvo:** Exclusivamente **Mozilla Firefox**.
* **Objetivo de Longo Prazo:** Migrar a execução principal (atualmente baseada no script `x.py` com interface gráfica) para execução 100% automatizada e **Headless** em nuvem (ex: GitHub Actions).
* **Filosofia de Manutenção:** **NÃO FAZER REFATORAÇÕES GIGANTESCAS**. As mudanças devem ser cirúrgicas, focadas em escalabilidade, diminuição de erros (`TimeoutException`, *Race Conditions* do Angular) e aumento de eficiência térmica/rede.

---

## 📂 2. Topologia do Projeto (Onde a Mágica Acontece)

### 🔥 CORE (O Coração da Automação)
Qualquer alteração de alto impacto ocorrerá nestas pastas. Elas contêm as regras de negócio ativas:
* `Fix/`: O motor utilitário. Contém as funções de login, criação do driver, injeções JS, gerenciamento de cache de seletores e manipulação de DOM. **Deve ser à prova de balas para rodar em Headless**.
* `atos/`: Wrappers e orquestradores para movimentações e ações gerais no processo.
* `Mandado/`, `PEC/`, `Prazo/`, `SISB/`: Módulos de negócio específicos.
* `x.py` (e variações): O grande orquestrador final. É o script que deve ser preparado para rodar na nuvem.

### 📚 REFERÊNCIAS FRONT-END (Extensões)
Pastas que contêm extensões de terceiros para o Firefox (`maispje/` e `AVJT/`). **Não são o alvo da automação Python**, mas são nossa biblioteca de "códigos geniais" para manipulação nativa via JS.

### 🏛️ LEGADO FUNCIONAL (O Plano B)
* `ref/` e `ORIGINAIS/`: Códigos antigos. Se uma otimização no CORE quebrar, a IA deve consultar estas pastas para engenharia reversa.

---

## � 2b. Artefatos de Infraestrutura (Novos — reta3)

| Arquivo | Papel |
|---|---|
| `Fix/exceptions.py` | Hierarquia de exceções tipadas: `PJePlusError`, `DriverFatalError`, `ElementoNaoEncontradoError`, `TimeoutFluxoError`, `NavegacaoError`, `LoginError` |
| `Fix/scripts/__init__.py` | Loader JS com cache em memória: `carregar_js(nome, pasta)` / `limpar_cache_js()` |
| `Fix/drivers/lifecycle.py` | `driver_session(tipo, headless)` — context manager que cria e finaliza o driver automaticamente |
| `Fix/sessionpool.py` | `SessionPool` — reutilização de driver/sessão entre módulos |
| `Fix/progress.py` | `ProgressoUnificado` — progresso persistido em `status_execucao.json` |
| `Fix/log.py` | `PJePlusLogger` + `getmodulelogger()` — logger centralizado (sem emoji no texto) |
| `Fix/smartfinder.py` | `SmartFinder` — busca com cache e fallback heurístico; **usar** `buscar(driver, chave, candidatos)` como ponto único de entrada |
| `Fix/headlesshelpers.py` | `click_headless_safe`, `wait_and_click_headless`, `limpar_overlays_headless` |
| `atos/movimentos_fluxo.py` | `movimentar_inteligente(driver, destino)` — único ponto de entrada para movimentação por destino |
| `Mandado/processamento_api.py` | `processar_mandados_devolvidos_api(driver)` — fluxo Mandado iniciado por API |
| `Prazo/fluxo_api.py` | `processar_gigs_sem_prazo_p2b(driver)` — fluxo P2B iniciado por API GIGS |
| `PEC/orquestrador.py` | `executar_fluxo_novo_simplificado(driver)` — fluxo PEC modular iniciado por API |

### Padrões obrigatórios (reta3 — já aplicados)

| Código | Regra |
|---|---|
| P1 | Sem wrappers de uma linha em `Fix/core.py` — apenas re-exportações |
| P2 | Máx 3 níveis de indentação; auxiliares privadas com `_` imediatamente acima |
| P3 | Infraestrutura levanta exceção tipada de `Fix/exceptions.py`; nunca `return False` silencioso |
| P4 | Sem `time.sleep()` — usar `aguardar_renderizacao_nativa` (Fix/utils/observer.py) |
| P5 | JS longo → arquivo `.js` em `scripts/` do módulo; carregado via `carregar_js()` |
| P6 | Retornos complexos → `@dataclass` (modelo: `SISB/standards.py`) |
| P7 | Driver via `driver_session()` context manager em orquestradores novos |
| P8 | Imports sempre no topo do módulo — nunca dentro de função |

---

## �🛠️ 3. Diretrizes de Otimização e Código Limpo (A Bíblia do PJePlus)

A IA que ler este documento deve respeitar as seguintes regras de ouro ao alterar qualquer arquivo do CORE:

### A. O Padrão "Monitor Silencioso" e Cache Dinâmico de Seletores
O código legado possuía funções engessadas tentando múltiplas listas de seletores (`try css1, try css2, try xpath...`), poluindo os logs e a CPU (conforme mapeado no antigo `monitor.py`). Isso está **terminantemente proibido** nas novas refatorações.

**Como implementar a busca de elementos agora:**
1. **Limpeza do Código de Negócio:** Módulos nas pastas `atos/`, `PEC/`, etc., não devem mais conter listas de `try...except` para achar um botão. O código deve ser declarativo.
2. **Uso do Cache (`Fix.utils_selectors`):** Toda busca de elementos mutáveis deve ser roteada por uma classe utilitária (ex: `SmartFinder` ou `Monitor`).
3. **Execução Paralela e Silenciosa:** O `SmartFinder` deve consultar um arquivo `cache_seletores.json`. Se o seletor em cache funcionar, ele retorna o elemento. Se falhar, o utilitário fará a varredura na lista de fallback em silêncio, atualizará o `.json` em background com o novo seletor vencedor e retornará o elemento.
4. **Logs Isolados:** Falhas de seletores e reajustes de cache **não devem aparecer no log principal** da automação. Eles devem ser direcionados para um arquivo de debug isolado (ex: `monitor_aprendizado.log`).

### B. Injeção JS Nativa vs Waits do Selenium (Fim do Polling)
O PJe é um SPA pesado em Angular. O uso de `time.sleep()` ou `WebDriverWait` em loops gera lentidão extrema e sobrecarrega a porta de rede do WebDriver.
* Sempre que precisar aguardar uma tabela renderizar, um spinner `.loading-spinner` sumir ou uma animação acabar, utilize a função utilitária `aguardar_renderizacao_nativa` localizada no módulo `Fix` (que injeta um `MutationObserver` nativo no navegador).

### C. Sanitização de Logs para Nuvem
* Remova logs de "tentativa 1", "buscando...", "scroll realizado".
* Mantenha no fluxo principal apenas: **Mudança de Estado do Processo** (ex: "Minuta Salva"), **Sucessos** e **Falhas Críticas que abortaram a execução**. O terminal da nuvem precisa ser analítico, não verboso.

### D. Instrumentação de Tempo (Tempo de Execução)

- **Local:** `Fix/core.py` — adicionados `tempo_execucao` (context manager) e `medir_tempo` (decorator).
- **Ativação:** defina a variável de ambiente `PJEPLUS_TIME=1` (ou `true`) para habilitar logs de medição.
- **Uso rápido:**
	- Context manager:

		```
		from Fix.core import tempo_execucao
		with tempo_execucao('minha_etapa'):
				fazer_algo()
		```

	- Decorator:

		```
		from Fix.core import medir_tempo

		@medir_tempo('fluxo_cls')
		def fluxo_cls(...):
				...
		```

- **Exemplos já instrumentados:** `atos/judicial_fluxo.py` (`fluxo_cls`) e `Prazo/p2b_fluxo_regras.py` (`_processar_regras_gerais`).
- **Objetivo:** permitir medição rápida de latências e identificação de bursts de requisições sem modificar a lógica de negócio — útil para debugging e tuning em ambiente Headless.

## ☁️ 4. Diretrizes para Cloud / Headless (Próximos Passos)

Para garantir a futura conteinerização do `x.py` no GitHub Actions:
1. **O Firefox será invisível (`-headless`):** Lógicas que dependem de ActionChains complexos, coordenadas absolutas de tela ou manipulação de janelas nativas do SO (Windows/Linux) **vão falhar**.
2. **Downloads Silenciosos:** O profile do Firefox deve forçar downloads diretos via MIME types, ignorando caixas de diálogo nativas (`browser.helperApps.neverAsk.saveToDisk`).
3. **Scroll Virtual:** Como a viewport virtual headless não possui rolagem física de usuário, antes de qualquer `.click()`, faça o elemento entrar em foco injetando: `driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)`.

***
**INSTRUÇÃO FINAL PARA A IA:** Ao iniciar a sessão, confirme a leitura do `IDX.md`, compreenda a topologia e aguarde a indicação do usuário sobre qual módulo (ou implantação do `SmartFinder` / Cache) será trabalhado hoje.

---

## 🧠 5. Lições Operacionais (Bugs Críticos — Registro Incremental)

Registro de bugs críticos encontrados em produção com causa raiz e fix. Acrescentar cada novo bug aqui.

| Data | ID | Módulo | Sintoma | Causa Raiz | Fix |
|---|---|---|---|---|---|
| 31/03/2026 | #001 | `Fix/navigation/filters.py` | `aplicar_filtro_100` retorna False silenciosamente; não loga nada | `com_retry` chamado com `log=True` mas implementação usa `log_enabled` → TypeError silencioso a cada tentativa | Trocar `log=True` → `log_enabled=True` na linha 244 |

### Regra derivada do Bug #001

**`com_retry` — dois contextos de import:**

```python
# VIA Fix.core (wrapper público — usar log=True):
from Fix.core import com_retry
com_retry(func, max_tentativas=3, log=True)  # ✅ OK

# VIA Fix.selenium_base.retry_logic (implementação direta — usar log_enabled=True):
from Fix.selenium_base.retry_logic import com_retry
com_retry(func, max_tentativas=3, log_enabled=True)  # ✅ OK
com_retry(func, max_tentativas=3, log=True)  # ❌ ERRO SILENCIOSO — não usar
```

Preferir sempre o import via `Fix.core` para evitar incompatibilidades de parâmetro.

