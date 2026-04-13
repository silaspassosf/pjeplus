Aqui estão os dois documentos completos:

***

## 📄 README.md

````markdown
# AudiCheck

Sistema de check-in eletrônico para audiências trabalhistas, desenvolvido em React + TypeScript. Hospedado via Supabase como backend (banco de dados + API REST). Todo o frontend reside em um único arquivo `App.tsx`.

---

## Estrutura do arquivo `App.tsx`

O arquivo é autocontido (~230 KB) e segue esta organização sequencial:

```
App.tsx
│
├── // ── SUPABASE ──
│     Configuração da URL/Key e funções de acesso ao banco:
│     sbFetch, dbGetProcessos, dbSaveProcessos,
│     dbEncerrar, dbLimpar, dbGetCheckins, dbSaveCheckin
│
├── // ── CONSTANTES ──
│     RAIO_METROS (geolocalização), RETORNO_SEG (timeout auto),
│     STORAGE_SENHAS / STORAGE_GRUPO (chaves de localStorage),
│     FORUM { nome, endereço, lat, lng },
│     COR_REC / COR_RDO (verde/laranja por polo),
│     POLO_REC_PAPEIS / POLO_RDO_PAPEIS (arrays de papéis por polo),
│     PAPEIS (lista usada nos formulários), PLABEL (labels exibidos)
│
├── // ── FORMATADORES / VALIDADORES ──
│     fCPF, fCEP, fOAB   — máscaras de input
│     validCPF, validOAB — validação lógica
│     extrairPartesDoTexto(texto) — split "Reclamante X Reclamada"
│     dist(lat1,lng1,lat2,lng2) — distância haversine em metros
│     load(key, default) / save(key, val) — wrappers de localStorage
│     getSenhas() — retorna objeto { secretaria: "senha" }
│     now() — hora atual formatada "HH:MM"
│
├── // ── PARSER PAUTA ──
│     parsePauta(texto: string) → { [numProcesso]: ProcessoObj }
│     Extrai de texto copiado do PDF PJe:
│     número CNJ, data, hora, partes, tipo audiência,
│     presencial vs videoconferência
│
├── // ── RELATÓRIO AUD ──
│     relatorio(proc, parts, info) → string
│     Gera o texto formatado para colar no sistema AUD do TRT,
│     com polo reclamante, polo reclamado agrupado por empresa,
│     OAB formatada, testemunhas com CPF/endereço, propostas, prazos
│
├── // ── ESTILOS GLOBAIS ──
│     GLOBAL_STYLE — string de CSS com keyframes e reset mínimo,
│     injetada via <GlobalStyle /> (useEffect + <style> tag)
│
├── // ── COMPONENTES DE UI ──
│     GlobalStyle   — injeta CSS global
│     Spinner       — ícone de loading animado
│     Toast         — notificação flutuante (sucesso/erro)
│     MConfirmar    — modal de confirmação genérico
│     MImport       — modal para colar texto da pauta PDF
│     CopyBtn       — botão inline de copiar para clipboard
│     CardParticipante — card individual de um participante (nome, papel, hora, OAB, CPF, pendências, proposta)
│     CardGrupoPapel   — grupo de CardParticipante do mesmo papel
│     Card             — card completo de um processo (painel secretaria): cabeçalho, badges de contagem, polo ativo, polo passivo, botões Copiar/Editar/Encerrar
│     MCartazes        — gera página HTML para impressão de cartazes com QR Codes de check-in
│
└── // ── COMPONENTE PRINCIPAL: App ──
      Três telas controladas por estado:
      ┌─ "secretaria" — painel da secretaria (protegido por senha)
      │    Importar pauta → parsePauta → dbSaveProcessos
      │    Lista todos os processos do dia (Card)
      │    Encerrar audiência, Editar processo
      │    Gerar cartazes QR, Limpar tudo
      │
      ├─ "checkin"    — tela pública (acessada via QR Code ?proc=NUM)
      │    Verifica geolocalização (raio 1000m do fórum)
      │    Formulário de papel + nome + dados específicos por papel
      │    dbSaveCheckin → confirmação visual
      │
      └─ "juiz"       — painel do(a) juiz(a) (protegido por senha)
           Exibe processos com checkins agrupados por polo
           Leitura de propostas por reclamada
```

### Modelo de dados

**Tabela `processos`**
| campo | tipo | descrição |
|---|---|---|
| `id` | text PK | número CNJ do processo |
| `data` | text | data da audiência (dd/mm/aaaa) |
| `hora` | text | hora (HH:MM), usada para ordenação |
| `partes` | text | "Reclamante X Reclamada" |
| `tipo` | text | `"presencial"` ou `"videoconferência"` |
| `tipo_aud` | text | descrição do tipo (ex: "ATOrd Instrução") |
| `encerrada` | boolean | audiência encerrada |

**Tabela `checkins`**
| campo | tipo | descrição |
|---|---|---|
| `id` | bigint PK | gerado pelo Supabase |
| `processo_id` | text FK → processos.id | CASCADE DELETE |
| `nome` | text | nome do participante |
| `papel` | text | papel processual |
| `hora` | text | hora do check-in |
| `modalidade` | text | `"presencial"` ou `"virtual"` |
| `cpf` | text | CPF (testemunhas) |
| `oab` | text | OAB (advogados) |
| `endereco`, `cep`, `numero`, `complemento` | text | endereço (testemunhas) |
| `parte_representada` | text | nome(s) da parte representada (sep. por ` \| `) |
| `empresa_representada` | text | empresa do polo passivo |
| `subtipo_representante` | text/JSON | subtipo do representante por reclamada |
| `parte_ouvinte` | text | parte sendo ouvida (testemunhas) |
| `regularizacao` | text | pendências do advogado (sep. por ` \| `) |
| `proposta` | text/JSON | proposta registrada por reclamada |
| `criado_em` | timestamptz | gerado pelo banco |

---

## Pré-requisitos para rodar localmente

- Node.js ≥ 18
- Um projeto React com Vite ou Create React App configurado para TypeScript
- O arquivo `App.tsx` substitui o componente raiz padrão

```bash
npm create vite@latest audicheck -- --template react-ts
cd audicheck
# substitua src/App.tsx pelo arquivo fornecido
npm install
npm run dev
```

> **Por padrão o app tenta conectar ao Supabase.** Para testar sem internet ou banco, aplique o **Modo Dev Local** descrito abaixo.

---

## Modo Dev Local (sem Supabase, sem geolocalização)

> ⚠️ Este modo é **exclusivo para desenvolvimento local**. Todos os dados ficam no `localStorage` do navegador e são perdidos ao limpar o cache. Nunca faça deploy desta versão.

### Mudança 1 — Substituir bloco Supabase por mocks localStorage

**Localizar** (início do arquivo, logo após os imports):
```ts
// ── SUPABASE ──
const SB_URL = "https://siliofjjlyjgouuiexua.supabase.co";
```
**Até o final de** `dbSaveCheckin` (termina com `};` após o segundo `catch`).

**Substituir TODO o bloco por:**

```ts
// ── LOCAL STORAGE MOCK (modo dev — sem Supabase) ──
const LS_PROCESSOS = "audicheck_local_processos";
const LS_CHECKINS  = "audicheck_local_checkins";

const lsGet = (key: string, def: any = []) => {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : def; } catch { return def; }
};
const lsSet = (key: string, val: any) => {
  try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
};

const dbGetProcessos = async () => lsGet(LS_PROCESSOS, []);

const dbSaveProcessos = async (procs: any) => {
  const rows = Object.entries(procs).map(([id, p]: any) => ({
    id, data: p.data, hora: p.hora, partes: p.partes,
    tipo: p.tipo, tipo_aud: p.tipoAud || "", encerrada: p.encerrada || false,
  }));
  const existing: any[] = lsGet(LS_PROCESSOS, []);
  const merged = [...existing];
  rows.forEach(row => {
    const idx = merged.findIndex(r => r.id === row.id);
    if (idx >= 0) merged[idx] = row; else merged.push(row);
  });
  lsSet(LS_PROCESSOS, merged);
};

const dbEncerrar = async (id: string) => {
  lsSet(LS_CHECKINS, (lsGet(LS_CHECKINS, []) as any[]).filter((c: any) => c.processo_id !== id));
  lsSet(LS_PROCESSOS, (lsGet(LS_PROCESSOS, []) as any[]).map((p: any) =>
    p.id === id ? { ...p, encerrada: true } : p
  ));
};

const dbLimpar = async () => {
  lsSet(LS_PROCESSOS, []);
  lsSet(LS_CHECKINS, []);
};

const dbGetCheckins = async () => lsGet(LS_CHECKINS, []);

const dbSaveCheckin = async (c: any) => {
  const checkins: any[] = lsGet(LS_CHECKINS, []);
  const horaAtual = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const newRow: any = {
    id: Date.now(),
    processo_id: c.processo_id,
    nome: c.nome,
    papel: c.papel,
    hora: horaAtual,
    modalidade: c.modalidade,
    criado_em: new Date().toISOString(),
    ...(c.cpf                   && { cpf: c.cpf }),
    ...(c.oab                   && { oab: c.oab }),
    ...(c.endereco              && { endereco: c.endereco }),
    ...(c.cep                   && { cep: c.cep }),
    ...(c.numero                && { numero: c.numero }),
    ...(c.complemento           && { complemento: c.complemento }),
    ...(c.regularizacao         && { regularizacao: c.regularizacao }),
    ...(c.parte_representada    && { parte_representada: c.parte_representada }),
    ...(c.empresa_representada  && { empresa_representada: c.empresa_representada }),
    ...(c.subtipo_representante && { subtipo_representante: c.subtipo_representante }),
    ...(c.parteOuvinte          && { parte_ouvinte: c.parteOuvinte }),
    ...(c.proposta              && { proposta: c.proposta }),
  };
  checkins.push(newRow);
  lsSet(LS_CHECKINS, checkins);
  return newRow;
};
```

---

### Mudança 2 — Desativar verificação de geolocalização

**Localizar:**
```ts
const RAIO_METROS = 1000;
```

**Adicionar logo abaixo:**
```ts
const DEV_MODE = true; // ← true = modo local, desativa geolocalização
```

**Depois**, localizar TODAS as ocorrências de `navigator.geolocation.getCurrentPosition` no arquivo (tipicamente dentro do componente `App`, na função que lida com o check-in público). Para cada ocorrência, envolver assim:

```ts
// PADRÃO ORIGINAL (exemplo):
navigator.geolocation.getCurrentPosition(
  (pos) => { /* callback sucesso */ },
  (err) => { /* callback erro */ }
);

// SUBSTITUIR POR:
if (DEV_MODE) {
  const pos = { coords: { latitude: FORUM.lat, longitude: FORUM.lng } } as GeolocationPosition;
  /* chamar aqui o mesmo callback de sucesso com pos */
} else {
  navigator.geolocation.getCurrentPosition(
    (pos) => { /* callback sucesso original */ },
    (err) => { /* callback erro original */ }
  );
}
```

> A LLM aplicadora deve identificar cada chamada a `getCurrentPosition` e aplicar o padrão acima, reutilizando os callbacks originais sem modificá-los.

---

### Mudança 3 — Senha padrão (sem alteração necessária)

A função `getSenhas()` já retorna um fallback via `load()`:
```ts
const getSenhas = () => load(STORAGE_SENHAS, { secretaria: "3vtzs2026" });
```
**Nenhuma alteração necessária.** A senha padrão `3vtzs2026` funcionará automaticamente em ambiente limpo.

---

### Como reverter para produção (Supabase)

1. Definir `const DEV_MODE = false;` ou remover a variável e os blocos `if (DEV_MODE)`
2. Restaurar o bloco `// ── SUPABASE ──` original (com `sbFetch`, `dbGetProcessos`, etc.)
3. Remover `LS_PROCESSOS`, `LS_CHECKINS` e todas as funções mock de localStorage

---

## Roadmap de Evolução

Ver arquivo **`ROADMAP.md`** para detalhamento completo das próximas funcionalidades planejadas.
````

***
