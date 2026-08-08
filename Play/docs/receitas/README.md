# Receitas — tarefas mecânicas para modelos de contexto pequeno

Formato pensado para **DeepSeek Flash, Gemini Flash, Raptor Mini** e similares
no GitHub Copilot. Cada receita é **autossuficiente**: não manda ler outro
documento, repete as regras críticas inline e cabe inteira no contexto.

---

## O que dá e o que não dá

Sejamos diretos sobre o limite. A segunda camada da migração tem duas metades:

### ✅ Dá — reconhecimento de forma

Padrões com **antes e depois literais**, encontráveis por `grep`, sem decisão de
projeto. É o que está nestas receitas.

| Receita | Padrão | Sítios |
|---|---|---|
| [R01](R01-abas.md) | abas por `window_handles` → `abrir_em_nova_aba` | 11 |
| [R02](R02-clique-js.md) | `execute_script("arguments[0].click()")` → clique real com fallback | 113 |
| [R03](R03-cliente-api.md) | `session_from_driver` → `cliente_para` | 11 |

### ❌ Não dá — exige julgamento

Não tente com modelo pequeno. Vai produzir código plausível e errado:

- **Reescrever fluxo em `Locator` nativo** (P2B, PEC, Mandado sem a fachada) —
  exige entender o fluxo inteiro, não um trecho.
- **`api.esperar_resposta`** — exige saber *qual* requisição a ação dispara.
  Errar o padrão de URL faz a espera cair no timeout silenciosamente.
- **`get_by_role` / `:has-text`** no lugar de seletores CSS — exige julgar se o
  papel acessível é estável naquela tela do PJe.
- **Converter `WebDriverWait`** — precisa decidir a condição pelo contexto. É
  trabalho das etapas E1–E9, com modelo de contexto grande.

Se um modelo pequeno "resolver" um item da lista de baixo, **descarte**: ele
adivinhou.

---

## Prompt para a janela

Cole isto, trocando `<RECEITA>`:

```
Projeto PJePlus em D:\PjePlus. Tarefa mecânica de refatoração.

Leia o arquivo play/docs/receitas/<RECEITA>.md e execute exatamente o que ele
manda. Ele é autossuficiente: não leia mais nada.

Regras que valem acima de qualquer coisa:

1. Aplique a troca SOMENTE onde o código bater EXATAMENTE com o bloco "ANTES"
   da receita. Se estiver parecido mas não igual, PULE e anote.
2. Não altere nenhuma outra linha. Não reformate. Não renomeie.
3. Não invente seletor, nome de variável nem parâmetro.
4. Nunca toque em nada dentro de SISB/Core/.
5. Se não tiver certeza, PULE. Pular é resultado correto.

Ao terminar rode e cole a saída dos comandos de validação que a receita indica.
Depois liste o que mudou, uma linha por mudança, no formato que ela define.

Não commite.
```

---

## Ordem

R01 e R03 dependem de etapas anteriores:

| Receita | Precisa que já exista | De onde vem |
|---|---|---|
| R01 | `abrir_em_nova_aba` em `Fix/browser_suporte.py` | etapa E3 |
| R02 | nada | pode rodar já |
| R03 | `cliente_para` em `Fix/variaveis.py` | etapa E9 |

**R02 pode começar agora.** É a maior (113 sítios) e não depende de nada.

Se a função exigida não existir, a receita manda parar — e parar está certo.

---

## Conflito entre janelas

Cada receita percorre **todo o escopo**, então duas receitas rodando ao mesmo
tempo podem tocar o mesmo arquivo. **Rode uma receita por vez**, ou divida por
diretório entre janelas (uma faz `atos/`, outra `PEC/`, outra `Fix/`) — nunca
duas receitas diferentes no mesmo diretório ao mesmo tempo.
