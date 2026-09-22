# E8 — `SISB/` (exceto `SISB/Core/`)

**Leia antes:** `00-contexto.md` — em especial a seção de proibições —,
`02-esperas.md`, `01-traducao.md` §1.

> ⚠️ **Esta é a etapa de maior risco do projeto.** O SISBAJUD é um sistema do
> CNJ com detecção de automação. Leia a seção seguinte inteira antes de abrir
> qualquer arquivo.

---

## ⛔ `SISB/Core/` é proibido

Não abra, não edite, não converta. É onde mora a evasão de detecção:

- `simulate_human_movement` — os `sleep` existem **para** gastar tempo; sem
  eles a função vira no-op e o comportamento passa a parecer robô;
- `aplicar_rate_limiting`, `smart_wait`, `anti_detection_measures`;
- `time.sleep(30)` aguardando intervenção manual em CAPTCHA.

Encurtar qualquer uma dessas esperas pode causar **bloqueio da conta**.

Confirme ao final, obrigatoriamente:

```bash
git diff --name-only SISB/Core/     # PRECISA sair vazio
```

## ⛔ E fora do `Core/` também

Qualquer espera cujo contexto sugira **throttle, ritmo, intervalo entre
requisições, simulação de comportamento humano, backoff ou jitter aleatório**:
deixe como está, mesmo fora de `SISB/Core/`.

Sinal claro: `time.sleep(random.uniform(...))` é sempre jitter. Nunca converta.

Ponto de atenção específico: `SISB/processamento/ordens_acao.py` é chamado de
dentro de `_processar_series`, adjacente a `aplicar_rate_limiting` (`idx.md`
L237). Trate esse arquivo com cautela extra.

---

## Arquivos exclusivos

```
SISB/**    exceto SISB/Core/**
```

## Volume

35 `WebDriverWait`, 43 `EC.`, 21 `time.sleep`, 6 `espera.assentar`.

**Espere poucas conversões.** O risco de errar aqui é maior que o ganho. Uma
etapa que converta 10 dos 78 waits, com as 68 restantes justificadas, é um bom
resultado.

## Onde converter com segurança

Só onde for claramente **navegação ou carregamento de tela**, nunca ritmo:

```
table.mat-table tbody                         tabela de ordens
div.cdk-overlay-backdrop...-showing           overlay/backdrop
#maisPJe_valor_execucao                       campo injetado por script
!location.href.includes('/desdobrar')         navegação iniciou
button mat-icon.fa-edit → 'Alterar'           minuta salva (predicado em
                                              verificar_salvamento_minuta.js)
```

Conversões já feitas que servem de padrão: `minutas_salvar.py:32`,
`processamento_relatorios.py:37`, `navegacao.py:103/142/172`,
`ordens_dados.py:61`, `processamento_campos_reus.py:206`.

`SISB/processamento/ordens_acao.py:34` e `ordens_dados.py:34/62` têm
`WebDriverWait` direto — alvos legítimos, com a cautela acima.

## Regras

- `teto` = exatamente o valor que já estava. Nunca ajuste.
- **Na dúvida sobre uma espera do SISB, não mexa.** Aqui deixar é a resposta
  preferida, não o plano B.
- Não converta espera em `except` nem em laço de tentativa.
- Se precisar de função pendente de E1, pare naquele sítio e reporte.

## Validação

```bash
git diff --name-only SISB/Core/          # PRECISA sair vazio
```

```bash
python -m py_compile $(git diff --name-only SISB/)
```

```bash
python -c "import SISB.core, SISB.batch, SISB.processamento.series_fluxo; print('OK')"
```

```bash
py play/smoke.py --projeto
```

Se `SISB/Core/` aparecer no diff, **reverta imediatamente** antes de reportar.

## Relatório

```
SISB/Core/ intocado: SIM/NÃO   ← se NÃO, reverta antes de reportar
por arquivo: waits N/N, EC N/N, sleeps N/N, assentar refinados N/N
por conversão: <arquivo>:L<n>  <antes> -> <depois>  | porque: <evidência>
deixados por risco de anti-detecção: <lista explícita>
deixados por ambiguidade: <lista>
bloqueado por E1: <lista>
VALIDAÇÃO smoke: __/91 | py_compile: ok | imports: ok | diff SISB/Core: vazio
```
