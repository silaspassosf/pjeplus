# Changelog — 22/04/2026

## Triagem/acoes.py

### Observação "//processo estava sem aud" pós-relatório de triagem
Nos fluxos que marcam audiência, a primeira ação após `criar_gigs("xs triagem")` agora cria
um GIGS adicional de observação `"//processo estava sem aud"` (sem prazo, sem responsável).

Funções afetadas:
- `acao_bucket_a` — ramo `not tem_100` (processo sem 100% digital)
- `acao_bucket_a` — ramo `tem_100` (processo com 100% que é desmarcado e marcado novamente)
- `acao_bucket_b` — início do fluxo
- `acao_bucket_d` — início do fluxo

---

## atos/movimentos_navegacao.py

### Fix 1 — `_normalizar_tarefa`: remoção real de acentos + strip prefixo DOM

**Problema:** `_normalizar_tarefa` apenas fazia `.lower()`, sem remover acentos de fato.
O DOM do PJe retorna o nome da tarefa como `"Tarefa:\nArquivo"`, que após `.lower()` ficava
`'tarefa:\narquivo'` — chave inexistente no dict `movimentos` — fazendo o fluxo cair no
fallback `_movimento_padrao_para_analise`, que então tentava `button[aria-label='Análise']`
(inexistente na tarefa Arquivo) e falhava.

**Fix:** normalização via `unicodedata.normalize('NFD')` + regex `^tarefa:\s*` removido,
alinhando com o `removeAcento` do gigs-plugin.js.

### Fix 2 — `_movimento_arquivo`: implementação real (era stub `return False`)

**Problema:** `_movimento_arquivo` retornava `False` incondicionalmente — processo em "Arquivo"
nunca conseguia voltar para análise.

**Fix:** espelha o gigs-plugin (`clicarBotao('button', 'desarquivar', true)`) — clica no botão
"Desarquivar", aguarda transição e retorna `True`.
