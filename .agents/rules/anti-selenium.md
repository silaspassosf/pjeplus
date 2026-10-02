## Regra de arquitetura: Playwright é a única via; branch de trabalho `main`

O agente deve operar e editar EXCLUSIVAMENTE na branch `main`,
confirmando-a com `git branch --show-current`, e respeitar rigorosamente o `idx.md`.
Não troque de branch automaticamente.

Todo código que roda em `py pw.py` fala o vocabulário nativo do projeto
(`Fix/espera.py`, `Play/pjeplay/nativo.py`) ou `Page`/`Locator`.

É proibido introduzir em arquivos do projeto:
`import selenium`, `driver.find_element`, `driver.find_elements`,
`driver.execute_script`, `driver.send_keys`, `driver.window_handles`,
`WebDriverWait`, `expected_conditions`, tipagem `WebDriver`, `time.sleep`.

Espera é sempre condição observável (`espera.ate_*`), nunca pausa cega.
JS só existe dentro de helper nomeado — nunca solto no fluxo de negócio.
A camada `Play/pjeplay/compat.py` existe apenas para módulos legados ainda não
migrados; ela não é justificativa para código novo no estilo Selenium.
Arquivo listado como migrado em `tools/pw_baseline.json` não pode regredir.
