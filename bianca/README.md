# bianca — Triagem + DOM Standalone

Pasta autônoma para executar os fluxos **Triagem Inicial** e **Dom Eletrônico** do sistema PJePlus, sem depender do restante do projeto.

---

## Requisitos de Sistema

| Componente | Versão mínima |
|------------|--------------|
| Windows | 10 ou superior |
| Python | 3.10+ (`py --version`) |
| Firefox Developer Edition | qualquer versão recente |
| Acesso ao PJe TRT2 | via rede corporativa/VPN |

---

## Instalação

### Passo 1 — Executar o instalador

A partir da **raiz do projeto** (pasta `PjePlus`):

```bat
bianca\instalar.bat
```

O script faz automaticamente:
- Cria `bianca\venv` (ambiente virtual Python)
- Instala todas as dependências (`requirements.txt`)
- Copia `Fix\geckodriver.exe` → `bianca\drivers\geckodriver.exe`
- Verifica Firefox Developer Edition
- Cria pasta `bianca\logs`

### Passo 2 — Verificar instalação

```bat
bianca\venv\Scripts\python.exe -c "import selenium, requests; print('OK')"
```

---

## Execução

```bat
py bianca\main.py
```

O menu exibe:

```
============================================================
BIANCA — TRIAGEM + DOM
============================================================
T - Triagem Inicial
D - Dom Eletrônico
X - Sair
============================================================
```

Após escolher o fluxo:
1. Firefox Developer Edition abre automaticamente
2. **Login manual**: digite CPF e senha no terminal (ou diretamente no navegador, conforme indicado)
3. O fluxo executa e exibe progresso no terminal
4. Log salvo em `bianca\logs\bianca_TIMESTAMP.log`

---

## Fluxos Disponíveis

### T — Triagem Inicial

Processa a fila **Triagem Inicial** do Painel Global PJe:
- Busca lista via API (paginação automática)
- Para cada processo: executa análise da petição inicial (texto OCR/API)
- Cria comentário com resultado da análise
- Aplica ação pós-triagem conforme alertas detectados (buckets A/B/C/D)

### D — Dom Eletrônico

Processa processos com Domicílio Eletrônico no painel de atividades (filtro `dom.e`):
- **Bucket 1** (sem audiência): remove chips Dom Eletrônico
- **Bucket 2** (com audiência): remove chips, verifica/cria lembrete, cria PEC

---

## Estrutura de Arquivos

```
bianca/
├── config.py          — constantes e caminhos
├── driver.py          — criação do Firefox + login manual
├── utils.py           — tipos, resultados, run_batch
├── selenium_utils.py  — operações Selenium
├── api_client.py      — cliente API PJe
├── extracao.py        — GIGS, comentários, lembretes, indexação
├── atos_utils.py      — def_chip, PEC wrappers
├── triagem_regras.py  — coleta de dados, regras de alertas
├── triagem_engine.py  — motor de triagem, run_triagem()
├── dom_engine.py      — motor DOM, run_dom()
├── main.py            — entry point + menus
├── requirements.txt
├── instalar.bat
├── PLANO.md
├── ARQUITETURA.md
└── drivers/
    └── geckodriver.exe
```

---

## Notas

- **Sem controle de progresso**: cada execução processa todos os itens da fila do zero.
- **Login exclusivamente manual**: nenhuma credencial é armazenada em arquivos.
- OCR (`pytesseract`) requer [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) instalado no sistema. Sem ele, o fluxo de triagem funciona mas sem extração OCR de PDFs.
