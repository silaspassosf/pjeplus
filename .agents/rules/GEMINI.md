**BRANCH DE TRABALHO EXCLUSIVA: `refat` (`refactor/pw-nativo`)**
- O agente deve SEMPRE verificar `git branch --show-current`. Toda edição, refatoração e manutenção do PJePlus deve ocorrer OBRIGATORIAMENTE no branch `refat` (`refactor/pw-nativo`) e respeitar o `idx.md` deste branch.
- A branch `main` serve exclusivamente como consulta histórica de comportamento funcional validado (`git show main:CAMINHO/ARQUIVO.py`) — NUNCA edite em `main` código de automação, nem faça checkout/merge/fetch automáticos (a única exceção é `Script/`, que tem ciclo próprio de publicação).

**REGRA DE ARQUITETURA INEGOCIÁVEL: APENAS PLAYWRIGHT, NUNCA SELENIUM**
- É TERMINANTEMENTE PROIBIDO reintroduzir ou usar Selenium (`import selenium`, `driver.find_element`, `driver.find_elements`, `WebDriverWait`, `expected_conditions`, tipagem `WebDriver`, `time.sleep`).
- Toda automação deve falar o vocabulário nativo Playwright do projeto (`Fix/espera.py`, `Play/pjeplay/nativo.py`, `_executar_js`, `espera.ate_*`, locators/handles seguros).

Leia e siga todas as instruções em ./idx.md para contexto arquitetural completo do projeto pjeplus no branch `refat`.

Regras always-on deste workspace estão em .agents/rules/ e são carregadas automaticamente — não precisam ser relidas manualmente.

Agentes especializados disponíveis em .agents/rules/agents/ (invocar pelo nome quando a tarefa se encaixar no escopo dele):
- pjeplus-analyst — análise e geração de patches no branch refat com Playwright (bugs, features, refatoração cirúrgica)
- pjeplus-debug — diagnóstico cross-module leve, produz diagnóstico + correção pontual sem editar
- pjeplus-surgical — aplicação de patch mínimo a partir de bloco pjeplus:apply já pronto
- pjeplus-script — especialista exclusivo na pasta Script/ (Tampermonkey, console, bookmarklets)

Antes de qualquer busca exploratória (grep/glob) fora do escopo já mapeado, consulte .agents/rules/idx-core.md (Quick Reference + Árvore de Decisão). Se a tarefa não estiver coberta lá, leia ./idx.md para o índice completo (palavras-chave, cadeias de chamada, catálogo de atos/, API obrigatória).

**REGRAS always-on: leia também .agents/rules/anti-selenium.md e .agents/rules/restauracao-pre-refac.md — são inegociáveis.**

Resumo da regra de restauração (detalhes no arquivo): se um fluxo/ato/seletor parou de funcionar, a lógica que funcionava está na tag `pre-refac` (`git show pre-refac:CAMINHO/ARQUIVO.py`) ou em `main`. Restaure a LÓGICA preservando a arquitetura Playwright atual (espera.ate_*, Fix/espera.py, locators) — nunca reintroduza Selenium. Não recrie do zero o que já existia; restaure, adapte para Playwright, e valide com `py -m py_compile`.
