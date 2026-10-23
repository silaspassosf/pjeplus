# EDITAR AQUI — Ponto de entrada da Camada Headless

> **Para o LLM executor.** Este é o único arquivo que você precisa ler para implementar. Os demais docs (`00`–`04`) são contexto/justificativa.
> Branch: `main` (confirme com `git branch --show-current`). Proibido Selenium, `time.sleep`, `input()` novo.

## Regra de ouro (inegociável)

**O modo visível não pode mudar.** Toda a camada é código novo que só executa quando `headless=True`.
- Nenhum arquivo de negócio é editado (`Mandado/`, `Prazo/`, `PEC/`, `atos/`, `Fix/`, `x.py`, `pw.py`, `SISB/`).
- Único arquivo existente tocado: `Play/pjeplay/launcher.py` (+3 linhas, dentro de `if headless:`).
- Se `driver.headless` for `False`, o módulo novo **nem é importado**.

## Escopo (apenas o que foi comprovado no código)

| # | Item | Por quê |
|---|---|---|
| 1 | Clipboard virtual (`pyperclip.paste` em headless) | Sonda: headless não atualiza clipboard do SO. Há só 2 leitores: `PEC/anexos/anexos_extracao.py:44` e `Fix/extracao.py:213` |
| 2 | Recovery de driver mantém headless | `Fix/utils.py:1594` recria com `headless=False` (abre janela). Corrigido por patch em runtime, sem editar `Fix/utils.py` |

Fora de escopo (já resolvido ou sem evidência — **não implementar**): overlay buster (existe em `Fix/browser_suporte.py`), CKEditor (já usa `setData`), `input()` do SISB (não existe), checkbox/datepicker/abas (hipóteses; só agir se teste real falhar — ver `04_VALIDACAO_E_AJUSTES.md`).

## Tarefa A — Criar `Play/pjeplay/headless.py` (arquivo novo)

API pública (idempotente, tudo envolvido em `try/except` com `logger.warning`; jamais levantar exceção para o fluxo):

```python
def ativar_para_driver(driver) -> None
    """Chamado só se driver.headless. Faz 1) e 2) abaixo."""
```

### A1. Clipboard virtual
1. `driver._context.add_init_script(JS_CLIPBOARD)` — verifique o nome do atributo do context em `Play/pjeplay/driver.py` (`PWDriver.__init__`, ~L119-135) antes de usar.
   `JS_CLIPBOARD` deve, em todas as páginas/frames:
   - ouvir `document.addEventListener('copy', ..., true)` e gravar em `window.__pjeplay_clipboard` o texto copiado, obtido por: se `document.activeElement` é `input`/`textarea` → `value.substring(selectionStart, selectionEnd)`; senão `window.getSelection().toString()`. (Firefox devolve seleção vazia dentro de textarea — por isso o tratamento do activeElement; ngx-clipboard cria textarea temporário.)
   - envolver `navigator.clipboard.writeText` (se existir) gravando o texto na mesma variável antes de chamar o original (com `.catch` silencioso).
   - envolver `document.execCommand`: após `execCommand('copy')` retornar, capturar do mesmo jeito se o listener não tiver disparado.
2. Em Python, no primeiro `ativar_para_driver`, substituir `pyperclip.paste` (guard `_instalado`; guardar original em `_paste_original`):
   ```python
   def _paste_headless():
       drv = <driver ativo>          # Play/pjeplay/api_resiliencia._driver_ativo (já registrado por launcher.registrar_driver)
       if drv is not None and getattr(drv, "headless", False):
           txt = ler_clipboard_virtual(drv)   # lê da página ativa; se vazio, tenta demais abas do context
           # consome: limpar window.__pjeplay_clipboard = '' após ler
           return txt or ""          # '' (não o lixo do SO) -> os 2 chamadores já tratam vazio com fallback
       return _paste_original()
   ```
   - `ler_clipboard_virtual` usa `drv.execute_script("return window.__pjeplay_clipboard || ''")` (interface existente do PWDriver) com `try/except` → `""`.
   - Não substituir `pyperclip.copy` (só um fallback de ImportError em `Fix/utils.py:984`, sem impacto).
   - Os chamadores usam `import pyperclip` + `pyperclip.paste()` (atributo no módulo, resolvido em runtime), então o patch funciona. Não é preciso editar `anexos_extracao.py` nem `Fix/extracao.py`.

### A2. Recovery mantém headless (sem editar `Fix/utils.py`)
`Fix.utils.driver_pc(headless=False)` → `obter_driver_padronizado(headless=headless)` → `criar_driver_PC`. O recovery (`Fix/utils.py:1594`) chama a factory com `headless=False`.
- Em `ativar_para_driver`, `import Fix.utils as u` e substituir `u.obter_driver_padronizado` por wrapper que força `headless=True` (guardar original; guard `_instalado_recovery`). `driver_pc` e `obter_driver_padronizado` resolvem o nome global em runtime, então o patch vale.
- Só os fluxos Triagem/Peticao/Andrei registram recovery; **Mandado/P2B/PEC não usam** → baixa prioridade, mas barato. Se `import Fix.utils` falhar, ignorar com `logger.debug`.

## Tarefa B — Gancho em `Play/pjeplay/launcher.py` (único edit em arquivo existente)

Dentro de `criar_driver`, logo **após** o bloco `context.add_init_script("Object.defineProperty(navigator, 'webdriver' ...)")` (hoje ~L172-174) e antes de `return driver`:

```python
    if headless:
        try:
            from . import headless as _headless_layer
            _headless_layer.ativar_para_driver(driver)
        except Exception as e:
            logger.warning("camada headless nao ativada: %s", e)
```

Atenção: o nome do parâmetro `headless` em `criar_driver(headless=False, ...)` sombreia o módulo; por isso o alias `_headless_layer`. Nada mais muda no launcher.

## Tarefa C — Teste de aceitação (arquivo novo `tools/check_headless_layer.py`, estilo de `tools/check_pw.py`)

Verificar, usando a sonda de ontem como base (`C:\Users\Silas\.gemini\antigravity-ide\brain\8ef569ec-4abd-4774-9d65-8e669f4bedf2\scratch\sonda_headless.py` — copiar a lógica, não depender do caminho):
1. **Headless**: página `data:` com botão que faz textarea + `execCommand('copy')` → `pyperclip.paste()` devolve o texto copiado (e `''` se nada foi copiado, mesmo com sentinela no clipboard do SO).
2. **Visível**: `pyperclip.paste` continua sendo o original (`pyperclip.paste is _paste_original` / módulo `headless` nem importado: `'Play.pjeplay.headless' not in sys.modules`).
3. Recovery: `Fix.utils.obter_driver_padronizado(headless=False)` em sessão headless devolve driver com `.headless is True`.

## Tarefa D — Documentação

- Em `idx.md` (seção de Play/pjeplay) acrescentar: `Play/pjeplay/headless.py` — camada headless (clipboard virtual, recovery headless); ativada só via `launcher.criar_driver` quando `headless=True`.
- Não editar mais nenhum doc.

## Como rodar em headless (referência)

`PJEPLUS_DRIVER=PC_HEADLESS PJEPLUS_FLUXO=A py pw.py` (A=Mandado, B=Prazo/P2B, D=PEC; ver `x.py` ~L848). As variáveis evitam os menus com `input()` de `x.py:793,832`. `DEBUG_PAUSAS_LOOP` já é `False`. Login: `x.py:137` (`_criar_driver_headless_com_login_visivel`) usa cookies; se expirados, abre janela visível uma vez.

## Critérios de pronto

- [ ] `git diff` mostra só: `Play/pjeplay/headless.py` (novo), `Play/pjeplay/launcher.py` (+≤8 linhas dentro de `if headless:`), `tools/check_headless_layer.py` (novo), `idx.md`.
- [ ] Nenhuma ocorrência nova de `selenium`, `time.sleep`, `input(`.
- [ ] `py tools/check_headless_layer.py` passa nos 3 testes.
- [ ] `py tools/check_pw.py` (baseline) continua passando.
- [ ] Execução visível de qualquer fluxo inalterada (nenhum import do módulo novo).
