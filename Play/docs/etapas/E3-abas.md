# E3 — `Fix/browser_suporte.py`: esperas e abas

**Leia antes:** `00-contexto.md`, `02-esperas.md`, `01-traducao.md` §1 e §5.

## Arquivo exclusivo

```
Fix/browser_suporte.py
```

Só este. Os ~383 sítios que manipulam abas vivem em `atos/`, `PEC/`, `Mandado/`,
`Prazo/`, `SISB/` — pertencem às etapas donas daqueles diretórios. Aqui você
melhora **os helpers**; a adoção nos chamadores é de quem os possui.

## Volume

7 `WebDriverWait`, 3 `EC.`, 1 `time.sleep`.

## Parte 1 — Converter as esperas

Tabela em `01-traducao.md` §1. Cuidado: `click_headless_safe`,
`scroll_to_element_safe` e `is_headless_mode` são primitivas embrulhadas pelo
`pjeplay/nativo.py`. Pode converter esperas **dentro** delas, mas não altere
assinatura nem contrato de retorno.

## Parte 2 — Abas

`Fix/browser_suporte.py` concentra `trocar_para_nova_aba`, `aguardar_nova_aba` e
`forcar_fechamento_abas_extras`. Hoje funcionam lendo `window_handles` antes e
depois da ação — padrão que tem uma corrida real: se a aba abre e fecha entre as
duas leituras, o handle nunca é visto.

O Playwright resolve isso armando a escuta **antes** da ação
(`context.expect_page`). Já está implementado em `play/pjeplay/pje.py`:

```python
pje.abrir_em_nova_aba(page, acao)   # devolve a Page nova
pje.fechar_abas_extras(page, manter=...)
```

O problema: as assinaturas atuais recebem `aba_lista_original` e devolvem
*handle*, e os chamadores esperam isso. **Não quebre esse contrato** — outras
etapas dependem dele.

Faça assim:

1. Mantenha `trocar_para_nova_aba`, `aguardar_nova_aba` e
   `forcar_fechamento_abas_extras` com assinatura e retorno idênticos.
2. Acrescente ao lado uma função nova, que os chamadores possam adotar depois:

   ```python
   def abrir_em_nova_aba(driver, acao, timeout=15):
       """Executa `acao` e devolve o handle da aba que ela abriu.
       Sem corrida: no backend Playwright a escuta é armada antes da ação."""
   ```

   No Selenium: leia handles, execute `acao()`, espere surgir handle novo
   (`espera.ate_abas`), troque. No backend Playwright: delegue para
   `pje.abrir_em_nova_aba` e devolva o handle correspondente do `PWDriver`.
3. Se conseguir reimplementar os três originais **por dentro** usando a mesma
   escuta prévia sem mudar assinatura, melhor ainda — mas só se o retorno
   continuar sendo exatamente o mesmo tipo.

Para a versão Playwright, acrescente o override em `play/pjeplay/nativo.py`…
**não**: esse arquivo é de E1. Se precisar de override nativo, **reporte** como
pendência para E1 em vez de editar.

## Parte 3 — Headless (ver `04-headless.md`)

Este arquivo concentra a camada de compensação para headless do Selenium:
`click_headless_safe` (3 estratégias progressivas), `limpar_overlays_headless`,
`scroll_to_element_safe`, `is_headless_mode`. Ela existe porque o Firefox
headless do geckodriver renderiza por caminho diferente do headed.

No Playwright o problema não existe: headless e headed usam o mesmo caminho, e
`locator.click()` faz a mesma checagem de actionability nos dois.

**Ação:** documente por docstring que essas quatro funções são compensação
específica do caminho Selenium, e que sob o backend Playwright viram no-op
efetivo (`pjeplay/nativo.py` já substitui `click_headless_safe`,
`scroll_to_element_safe` e `is_headless_mode`).

⚠️ **Não delete nada.** O caminho Selenium continua sendo produção e ainda
precisa delas. Marcar como legado ≠ remover.

## Regras

- `teto` = exatamente o valor que já estava.
- Não mude assinatura nem tipo de retorno das funções existentes.
- Não edite `play/pjeplay/nativo.py` (é de E1) nem os chamadores (são de E4–E8).
- Na dúvida, deixe como está.

## Validação

```bash
python -m py_compile Fix/browser_suporte.py
```

```bash
python -c "import Fix.browser_suporte, atos.judicial_fluxo, Mandado.entrada_api; print('OK')"
```

```bash
py play/smoke.py --projeto
```

O `smoke` cobre `window_handles`, `switch_to`, `close` e
`pje.abrir_em_nova_aba`. Precisa seguir 91/91.

## Relatório

```
esperas convertidas: N/7 waits, N/3 EC, N/1 sleep
abas: função nova adicionada? contratos antigos preservados? (sim/não)
pendências para E1: <overrides nativos necessários>
adoção pelos chamadores: NÃO FEITA (é de E4–E8) — liste onde vale a pena
VALIDAÇÃO smoke: __/91 | py_compile: ok | imports: ok
```
