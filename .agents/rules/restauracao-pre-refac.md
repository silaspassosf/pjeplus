# PJePlus — Protocolo de restauração pré-refatoração (anti-regressão funcional)

> **Regra primária para qualquer agente (Copilot, Antigravity/Gemini, Claude)**
> **Atualizado: 2026-09-24**

## A regra

**Se parou de funcionar, o que funcionava está no branch/tag pré-refatoração.**

- Tag **`pre-refac`** = código que rodava em produção com Selenium ( commits `e26322c`- e
  anteriores). Estado que processava de verdade.
- Branch atual **`refactor/pw-nativo`** = arquitetura Playwright nova.

Quando um fluxo, ato ou seletor para de funcionar após a migração, a hipótese padrão é:
**a lógica/funcionalidade foi perdida na tradução**, não é bug novo. O fluxo de restauração é:

```bash
git show pre-refac:CAMINHO/DO/ARQUIVO.py      # ver o arquivo inteiro como era antes
git show refac-fN:CAMINHO/ARQUIVO.py          # estado após a fase FN
git show pre-refac:CAMINHO/ARQUIVO.py | grep -n "funcao" -A 30   # trecho específico
git log -S "trecho do seletor" -- CAMINHO/ARQUIVO.py             # qual commit trocou
```

## Como restaurar (em ordem de preferência)

1. **Localize a função/lógica no `pre-refac`** (comandos acima).
2. **Restabeleça a lógica** no arquivo atual **preservando a arquitetura Playwright**:
   - mantenha o seletor/driver da nova arquitetura (`Fix/espera.py`, `Play/pjeplay/nativo.py`,
     `espera.ate_*`, `By` de `Play.pjeplay.locators`);
   - traga de volta **o que fazia o fluxo funcionar** — ordem das etapas, condição de espera,
     validação de estado, seletor do PJe real, critério de sucesso;
   - NUNCA reintroduza: `import selenium`, `find_element(s)`, `WebDriverWait`,
     `expected_conditions`, `time.sleep`, tipagem `WebDriver`, `time.sleep` cego.
   - Se o código pré-refac usava `driver.find_element(By.X, v)`, o equivalente direto é
     `espera.elemento(driver, seletor)` / `espera.elementos(...)` — **mesma semântica de
     motor por seletor** (`Fix/espera.py` decide CSS vs XPath pelo 1º caractere).
3. **Nunca "recriar do zero"** o que já existia: primeiro restaurar, depois adaptar.
4. **Registre a origem**: comentário 1 linha `# pre-refac: <funcao> — restaurado em <data>` apenas
   se a mudança não for óbvia pelo git. (Regra de comentário zero do executor não se aplica a
   restaurações funcionais.)

## Falhas que JÁ foram diagnosticadas como perda da tradução (não reinventar)

| Sintoma no log | Causa | Correção validada |
|---|---|---|
| `name 'By' is not defined` | refac removeu `import By` e manteve usos | `from Play.pjeplay.locators import By` |
| `name 'time' is not defined` | idem, `import time` (PEC/carta_execucao.py) | `import time` |
| `botão não encontrado no DOM` (com botão na tela) | seletor **misto CSS+XPath numa string** → `querySelectorAll` estoura | CSS e XPath em chamadas separadas |
| `[PRAZOS] Nenhum campo de prazo na linha selecionada` | traduziu `is_selected()` (propriedade) para atributo XPath | usar CLASSE `mat-checkbox-checked` |
| `[SIGILO_INSERIR] Botao de sigilo nao encontrado` | seletor não é o do PJe real | ver `pre-refac` + monólito |
| `[TIMELINE_API]` vazio / `Nem Certidao...` | import inexistente `obter_sessao_do_driver` | `cliente_para` |

## Referência de seletor correta

O monólito `+pje/PJe-Atual/gigs-plugin.js` roda em PRODUÇÃO contra o DOM real do PJe — é a
referência de seletor mais confiável. Ordem de consulta:

1. `git show pre-refac:...` — o que funcionava no bot
2. `+pje/PJe-Atual/gigs-plugin.js` — como o PJe real expõe o elemento
3. `idx.md` — padrão da arquitetura atual

## Anti-regressão

- `tools/check_pw.py` (ratchet) barra regressão a Selenium nos arquivos migrados — se o patch
  for rejeitado pelo hook pre-commit, é a regra anti-selenium agindo, não um erro seu.
- Arquivo em `tools/pw_baseline.json` (`migrados`) não pode reintroduzir padrões Selenium.
- Restaurar lógica NÃO autoriza regressão: o patch deve passar no ratchet e no smoke
  (`py play/smoke.py --projeto` = 91/91).
