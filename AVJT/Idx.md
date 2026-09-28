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

## 🛠️ 3. Diretrizes de Otimização e Código Limpo (A Bíblia do PJePlus)

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

---

## ☁️ 4. Diretrizes para Cloud / Headless (Próximos Passos)

Para garantir a futura conteinerização do `x.py` no GitHub Actions:
1. **O Firefox será invisível (`-headless`):** Lógicas que dependem de ActionChains complexos, coordenadas absolutas de tela ou manipulação de janelas nativas do SO (Windows/Linux) **vão falhar**.
2. **Downloads Silenciosos:** O profile do Firefox deve forçar downloads diretos via MIME types, ignorando caixas de diálogo nativas (`browser.helperApps.neverAsk.saveToDisk`).
3. **Scroll Virtual:** Como a viewport virtual headless não possui rolagem física de usuário, antes de qualquer `.click()`, faça o elemento entrar em foco injetando: `driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)`.

***
**INSTRUÇÃO FINAL PARA A IA:** Ao iniciar a sessão, confirme a leitura do `IDX.md`, compreenda a topologia e aguarde a indicação do usuário sobre qual módulo (ou implantação do `SmartFinder` / Cache) será trabalhado hoje.