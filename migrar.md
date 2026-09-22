# Guia de Sincronização Entre Máquinas (Notebook → PC 3 → PC 1)

Este guia documenta o fluxo de trabalho seguro para sincronizar as alterações entre os 3 computadores, preservando a pasta `pjeT` e as alterações locais do PC 1 sem risco de perda ou sobrescrita.

---

## 1. Etapa Atual: Notebook (Concluída)
* As alterações desta sessão (refatoração de agentes, patch de atos/comunicação e motores em `Script/autoactions/`) foram commitadas na branch **`notebook`**.
* A branch `main` do GitHub permanece intacta.

---

## 2. Próxima Etapa: No PC 3 (Terceiro Computador)

Quando você chegar no **PC 3**, execute no terminal dentro da pasta do projeto:

### 2.1. Conectar e puxar a branch `notebook`
```bash
git fetch origin
git checkout notebook
git pull origin notebook
```

### 2.2. Durante o trabalho no PC 3
Continue trabalhando normalmente na branch `notebook`. Ao salvar alterações:
```bash
git add .
git commit -m "feat: trabalho realizado no pc3"
git push origin notebook
```

---

## 3. Etapa Final: No PC 1 (Onde está o `pjeT` e o trabalho local antigo)

Quando você for até o **PC 1** (onde foi criada a pasta `pjeT` que não havia subido para o GitHub), execute **nesta ordem estrita**:

### 3.1. Proteger e commitar o estado local do PC 1 primeiro
Isso garante que o Git conheça todos os arquivos locais (inclusive o `pjeT`):
```bash
git status
git add .
git commit -m "feat: alteracoes locais do pc1 incluindo pjeT"
```

### 3.2. Baixar as novidades do Notebook e PC 3
```bash
git fetch origin
```

### 3.3. Mesclar as melhorias da branch `notebook` no PC 1
```bash
git merge origin/notebook
```
* O Git aplicará as novidades (`Script/autoactions/`, `atos/`, novos agentes) preservando o `pjeT` e tudo que já estava no PC 1.
* Caso haja algum conflito pontual (por exemplo, no `idx.md`), basta manter as duas partes e salvar.

### 3.4. Consolidar na `main` definitiva e subir para a nuvem
```bash
git checkout main
git merge notebook
git push origin main
```

Pronto! Todas as 3 frentes de trabalho estarão 100% integradas no repositório central.
