**BRANCH DE TRABALHO EXCLUSIVA: `main`**
- O agente deve SEMPRE verificar `git branch --show-current`. Toda edição, refatoração e manutenção do PJePlus deve ocorrer OBRIGATORIAMENTE no branch `main` e respeitar o `idx.md`.
- Não consulte branches anteriores nem troque de branch automaticamente.

**REGRA DE ARQUITETURA INEGOCIÁVEL: APENAS PLAYWRIGHT, NUNCA SELENIUM**
- É TERMINANTEMENTE PROIBIDO reintroduzir ou usar Selenium (`import selenium`, `driver.find_element`, `driver.find_elements`, `WebDriverWait`, `expected_conditions`, tipagem `WebDriver`, `time.sleep`).
- Toda automação deve falar o vocabulário nativo Playwright do projeto (`Fix/espera.py`, `Play/pjeplay/nativo.py`, `_executar_js`, `espera.ate_*`, locators/handles seguros).

Leia e siga todas as instruções em ./idx.md para contexto arquitetural completo do projeto pjeplus no branch `main`.

Regras always-on deste workspace estão em .agents/rules/ e são carregadas automaticamente — não precisam ser relidas manualmente.

Agentes especializados disponíveis em .agents/rules/agents/ (invocar pelo nome quando a tarefa se encaixar no escopo dele):
- pjeplus-analyst — análise e implementação direta no branch main com Playwright (bugs, features, refatoração cirúrgica); excepcionalmente gera bloco pjeplus:apply quando o usuário pedir explicitamente
- pjeplus-debug — diagnóstico cross-module leve + correção pontual aplicada e validada; excepcionalmente gera dump 00act.md quando o usuário pedir explicitamente
- pjeplus-surgical — aplicação de patch mínimo a partir de bloco pjeplus:apply ou instrução direta (modo único: sempre edita)
- pjeplus-script — especialista exclusivo na pasta Script/ (Tampermonkey, console, bookmarklets)

Antes de qualquer busca exploratória (grep/glob) fora do escopo já mapeado, consulte .agents/rules/idx-core.md (Quick Reference + Árvore de Decisão). Se a tarefa não estiver coberta lá, leia ./idx.md para o índice completo (palavras-chave, cadeias de chamada, catálogo de atos/, API obrigatória).

**REGRAS always-on: leia também .agents/rules/anti-selenium.md e .agents/rules/comparacao-historica.md — são inegociáveis.**

Resumo temporal (detalhes no arquivo): em caso de dúvida, falha ou regressão, compare o código atual com o estado imediatamente anterior ao commit `968047a` (`git show 968047a^:CAMINHO/ARQUIVO.py`). A comparação é somente histórica; não restaure nem copie código automaticamente. Não consulte branches anteriores. `gigs-plugin.js`, `LEGADO.md`, `legado.md` e outras fontes legadas só podem ser consultadas se o prompt as mencionar expressamente.
