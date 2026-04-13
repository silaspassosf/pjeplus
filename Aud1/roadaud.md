# AudiCheck — Roadmap de Evoluções

> Todas as mudanças descritas aqui devem ser **100% compatíveis com o Supabase** em produção.
> O modo dev local (localStorage) é apenas auxiliar de testes e não deve interferir nestas evoluções.
> Cada item descreve com precisão **onde no `App.tsx`** a alteração deve ocorrer.

---

## FASE 1 — Autenticação via token PJe

### Objetivo
Substituir a autenticação por senha simples (`getSenhas()`) por autenticação real usando o token de sessão do PJe, obtido via login no sistema judicial.

### Contexto atual
- A tela de secretaria e a tela do juiz são protegidas por senha local armazenada em `localStorage` via `getSenhas()`
- A senha padrão é `3vtzs2026`

### Alterações necessárias

**1.1 — Novo bloco de autenticação PJe**

Adicionar após as constantes (`// ── CONSTANTES ──`), antes do `parsePauta`:

```ts
// ── AUTENTICAÇÃO PJe ──
const PJE_TOKEN_KEY = "audicheck_pje_token";
const PJE_TOKEN_EXP_KEY = "audicheck_pje_token_exp";

const getPjeToken = (): string | null => {
  try {
    const token = localStorage.getItem(PJE_TOKEN_KEY);
    const exp = localStorage.getItem(PJE_TOKEN_EXP_KEY);
    if (!token || !exp) return null;
    if (Date.now() > parseInt(exp)) {
      localStorage.removeItem(PJE_TOKEN_KEY);
      localStorage.removeItem(PJE_TOKEN_EXP_KEY);
      return null;
    }
    return token;
  } catch { return null; }
};

const setPjeToken = (token: string, expiresInMs = 8 * 60 * 60 * 1000) => {
  localStorage.setItem(PJE_TOKEN_KEY, token);
  localStorage.setItem(PJE_TOKEN_EXP_KEY, String(Date.now() + expiresInMs));
};

const clearPjeToken = () => {
  localStorage.removeItem(PJE_TOKEN_KEY);
  localStorage.removeItem(PJE_TOKEN_EXP_KEY);
};

// Valida token contra o endpoint PJe (a ser confirmado)
// Endpoint provisório — ajustar conforme documentação do TRT
const PJE_API_BASE = "https://pje.trt2.jus.br/pjekz/api/v1"; // ← confirmar URL
const validarTokenPje = async (token: string): Promise<boolean> => {
  try {
    const r = await fetch(PJE_API_BASE + "/usuario/perfil", {
      headers: { Authorization: "Bearer " + token },
    });
    return r.ok;
  } catch { return false; }
};
```

**1.2 — Componente de login PJe**

Adicionar novo componente `MLoginPje` após `MImport`:

```tsx
function MLoginPje({ onAutenticado, onFechar }: { onAutenticado: (token: string) => void; onFechar: () => void }) {
  const [token, setToken] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  const handleLogin = async () => {
    setErro("");
    setCarregando(true);
    const valido = await validarTokenPje(token.trim());
    setCarregando(false);
    if (valido) {
      setPjeToken(token.trim());
      onAutenticado(token.trim());
    } else {
      setErro("Token inválido ou expirado. Copie o token da sessão ativa do PJe.");
    }
  };

  return (
    <div style={{ /* overlay */ }}>
      <div style={{ /* modal */ }}>
        <h2>Autenticação PJe</h2>
        <p style={{ fontSize: 13, color: "#555" }}>
          Cole abaixo o token de autenticação da sua sessão no PJe.<br />
          <strong>Como obter:</strong> No PJe, abra DevTools → Application → LocalStorage → copie o valor de <code>pje_token</code> (ou conforme orientação do TRT).
        </p>
        <textarea
          value={token}
          onChange={e => setToken(e.target.value)}
          placeholder="Cole o token JWT aqui..."
          style={{ width: "100%", height: 80, fontFamily: "monospace", fontSize: 12 }}
        />
        {erro && <p style={{ color: "#e74c3c", fontSize: 13 }}>{erro}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button onClick={onFechar}>Cancelar</button>
          <button onClick={handleLogin} disabled={!token.trim() || carregando}>
            {carregando ? <Spinner size={16} /> : "Autenticar"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

**1.3 — Integrar ao estado do `App`**

No componente principal `App`, localizar o estado de autenticação (onde `getSenhas()` é verificada) e adicionar:

```ts
const [pjeToken, setPjeTokenState] = useState<string | null>(() => getPjeToken());
```

- Quando `pjeToken !== null`, considerar a secretaria como autenticada.
- Ao fazer logout, chamar `clearPjeToken()` e setar `setPjeTokenState(null)`.
- Manter a senha como fallback opcional (configurável via constante `ALLOW_SENHA_FALLBACK = true`).

---

## FASE 2 — Importação de pauta via API PJe

### Objetivo
Substituir o fluxo de copiar/colar PDF pela chamada direta ao endpoint de audiências do PJe, retornando a pauta estruturada.

### Contexto atual
- `MImport` exibe um textarea onde a secretaria cola o texto do PDF
- `parsePauta(texto)` processa o texto e extrai os processos
- O resultado alimenta `dbSaveProcessos`

### Pré-requisito
- Token PJe válido (FASE 1 concluída)

### Alterações necessárias

**2.1 — Novo bloco de API PJe**

Adicionar após o bloco `// ── AUTENTICAÇÃO PJe ──`:

```ts
// ── API PJe — AUDIÊNCIAS ──

// ⚠️ Endpoints abaixo são provisórios — confirmar com documentação do TRT 2ª Região
// Possíveis endpoints a verificar:
//   GET /pjekz/api/v1/audiencia/pauta?data=YYYY-MM-DD&varaId=XXX
//   GET /pjekz/api/v1/audiencia/listar?dataInicio=...&dataFim=...

const pjeFetch = async (path: string, token: string) => {
  const r = await fetch(PJE_API_BASE + path, {
    headers: {
      Authorization: "Bearer " + token,
      Accept: "application/json",
    },
  });
  if (!r.ok) throw new Error("PJe API erro " + r.status + ": " + await r.text());
  return r.json();
};

// Busca audiências do dia para a vara configurada
// Retorna array de objetos brutos do PJe — mapear conforme estrutura real da resposta
const pjeGetAudienciasDoDia = async (token: string, data: string): Promise<any[]> => {
  // data formato: "YYYY-MM-DD"
  // ⚠️ Ajustar o path conforme documentação real
  const result = await pjeFetch(`/audiencia/pauta?data=${data}`, token);
  return Array.isArray(result) ? result : result?.audiencias || result?.data || [];
};

// Mapeia resposta da API para o formato interno de processos
// ⚠️ Os nomes dos campos abaixo são HIPOTÉTICOS — ajustar conforme resposta real da API
const mapearAudienciaParaProcesso = (aud: any): { id: string; proc: any } => {
  return {
    id: aud.numeroProcesso || aud.numero_processo,
    proc: {
      data: aud.dataAudiencia
        ? new Date(aud.dataAudiencia).toLocaleDateString("pt-BR")
        : "",
      hora: aud.horaAudiencia
        ? aud.horaAudiencia.slice(0, 5)
        : "",
      partes: [
        aud.nomeReclamante || aud.polo_ativo,
        aud.nomeReclamado  || aud.polo_passivo,
      ].filter(Boolean).join(" X "),
      tipo: (aud.tipoAudiencia || "").toLowerCase().includes("video")
        ? "videoconferência"
        : "presencial",
      tipoAud: aud.tipoAudiencia || aud.tipo_audiencia || "",
      encerrada: false,
      forumLat: FORUM.lat,
      forumLng: FORUM.lng,
      // Campo extra para uso na FASE 3
      partesApi: aud.partes || aud.participantes || [],
    },
  };
};
```

**2.2 — Componente `MImportApi` (substitui `MImport` quando autenticado)**

Adicionar após `MImport`:

```tsx
function MImportApi({
  token,
  onImportar,
  onFechar,
  onFallbackManual,
}: {
  token: string;
  onImportar: (procs: any) => void;
  onFechar: () => void;
  onFallbackManual: () => void;
}) {
  const [data, setData] = useState(new Date().toISOString().slice(0, 10));
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [preview, setPreview] = useState<any[]>([]);

  const buscar = async () => {
    setErro("");
    setCarregando(true);
    try {
      const lista = await pjeGetAudienciasDoDia(token, data);
      const mapeadas = lista.map(mapearAudienciaParaProcesso);
      setPreview(mapeadas);
    } catch (e: any) {
      setErro("Erro ao buscar pauta: " + e.message);
    } finally {
      setCarregando(false);
    }
  };

  const confirmar = () => {
    const procs: any = {};
    preview.forEach(({ id, proc }) => { procs[id] = proc; });
    onImportar(procs);
  };

  return (
    <div style={{ /* overlay */ }}>
      <div style={{ /* modal */ }}>
        <h2>Importar Pauta via PJe</h2>
        <label>Data:</label>
        <input type="date" value={data} onChange={e => setData(e.target.value)} />
        {erro && <p style={{ color: "#e74c3c" }}>{erro}</p>}
        {preview.length > 0 && (
          <ul>
            {preview.map(({ id, proc }) => (
              <li key={id}><strong>{id}</strong> — {proc.hora} — {proc.partes}</li>
            ))}
          </ul>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button onClick={onFallbackManual}>Importar por PDF (manual)</button>
          <button onClick={onFechar}>Cancelar</button>
          <button onClick={buscar} disabled={carregando}>
            {carregando ? <Spinner size={16} /> : "Buscar Pauta"}
          </button>
          {preview.length > 0 && (
            <button onClick={confirmar}>Importar {preview.length} processo(s)</button>
          )}
        </div>
      </div>
    </div>
  );
}
```

**2.3 — Alteração no `App` (lógica de abertura do modal)**

No componente principal `App`, localizar onde `MImport` é renderizado e substituir pela lógica condicional:

```tsx
{/* Antes: sempre abre MImport */}
{modalImport && <MImport onImportar={handleImportar} onFechar={() => setModalImport(false)} />}

{/* Depois: abre MImportApi se autenticado, MImport como fallback */}
{modalImport && pjeToken
  ? <MImportApi
      token={pjeToken}
      onImportar={handleImportar}
      onFechar={() => setModalImport(false)}
      onFallbackManual={() => { /* fechar MImportApi, abrir MImport */ }}
    />
  : modalImport && <MImport onImportar={handleImportar} onFechar={() => setModalImport(false)} />
}
```

---

## FASE 3 — Autopreenchimento de partes no formulário de check-in

### Objetivo
Ao abrir o formulário de check-in para um processo, exibir as partes retornadas pela API do PJe como opções selecionáveis (nome, papel, OAB), mantendo a entrada manual inalterada como fallback.

### Contexto atual
- O formulário de check-in coleta nome e papel manualmente
- Os dados disponíveis no processo são apenas o texto livre do campo `partes`

### Dependência
- Requer que `proc.partesApi` seja populado na FASE 2 (`mapearAudienciaParaProcesso`)

### Estrutura esperada de `partesApi`

```ts
// ⚠️ Campos hipotéticos — ajustar conforme resposta real da API
interface ParteApi {
  nome: string;
  polo: "ativo" | "passivo";
  tipoParte: string;       // ex: "RECLAMANTE", "ADVOGADO", "RECLAMADO"
  cpf?: string;
  oab?: string;
  empresa?: string;
}
```

### Alterações necessárias

**3.1 — Armazenar `partesApi` no Supabase**

Na tabela `processos`, adicionar coluna:
```sql
ALTER TABLE processos ADD COLUMN IF NOT EXISTS partes_api jsonb DEFAULT '[]'::jsonb;
```

Atualizar `dbSaveProcessos` para incluir `partes_api`:
```ts
// Na função dbSaveProcessos, adicionar ao objeto rows:
partes_api: JSON.stringify(p.partesApi || []),
```

**3.2 — Componente `SeletorParteApi`**

Adicionar antes do formulário de check-in:

```tsx
function SeletorParteApi({
  partesApi,
  onSelecionar,
}: {
  partesApi: ParteApi[];
  onSelecionar: (parte: ParteApi) => void;
}) {
  if (!partesApi || partesApi.length === 0) return null;

  return (
    <div>
      <p style={{ fontSize: 13, color: "#1a3a6b", fontWeight: 600 }}>
        Selecione seu nome ou preencha manualmente abaixo:
      </p>
      {partesApi.map((p, i) => (
        <button
          key={i}
          onClick={() => onSelecionar(p)}
          style={{ display: "block", width: "100%", textAlign: "left", marginBottom: 6,
                   padding: "8px 12px", borderRadius: 8, border: "1px solid #dce3ed",
                   background: "#f4f6fb", cursor: "pointer" }}
        >
          <strong>{p.nome}</strong>
          <span style={{ fontSize: 12, color: "#666", marginLeft: 8 }}>{p.tipoParte}</span>
          {p.oab && <span style={{ fontSize: 11, color: "#888", marginLeft: 8 }}>OAB: {p.oab}</span>}
        </button>
      ))}
      <hr style={{ margin: "12px 0", borderColor: "#eee" }} />
      <p style={{ fontSize: 12, color: "#999" }}>— ou preencha manualmente —</p>
    </div>
  );
}
```

**3.3 — Integrar ao formulário de check-in**

No componente de formulário de check-in (dentro de `App`, na tela `"checkin"`):

1. Recuperar `partesApi` do processo atual: `const partesApi = processoAtual?.partes_api || [];`
2. Renderizar `<SeletorParteApi>` acima dos campos de nome/papel
3. Ao selecionar, preencher automaticamente os campos: `setNome(p.nome)`, `setPapel(mapTipoParte(p.tipoParte))`, `setOab(p.oab || "")`
4. Manter todos os campos editáveis após o preenchimento automático

```ts
// Mapeamento de tipos da API para papéis internos
// ⚠️ Ajustar conforme valores reais retornados pela API
const mapTipoParte = (tipo: string): string => {
  const m: Record<string, string> = {
    "RECLAMANTE":  "Parte Reclamante",
    "RECLAMADO":   "Parte Reclamada",
    "ADVOGADO":    "Advogado(a) do(a) Reclamante", // refinar por polo
    "REPRESENTANTE": "Representante do(a) Reclamado(a)",
  };
  return m[tipo?.toUpperCase()] || "";
};
```

---

## FASE 4 — Exportação para o sistema AUD

### Objetivo
O bloco de partes + advogados (vindos da API ou adicionados manualmente) com check-ins confirmados deve ser exportado para preenchimento automático no sistema AUD do TRT.

### Abordagens a decidir

| Opção | Descrição | Prós | Contras |
|---|---|---|---|
| **A — Script JS de injeção** | Gerar um script `.js` ou bookmarklet que ao ser colado no console do AUD preenche os campos automaticamente | Sem integração server-side | Depende do DOM do AUD; frágil a atualizações |
| **B — Copiar texto formatado** | Manter o botão "Copiar para o AUD" atual, já funcional via `relatorio()` | Zero esforço técnico | Manual; propenso a erro humano |
| **C — API direta do AUD** | Chamar endpoint do AUD para inserção programática | Totalmente automatizado | Requer autenticação e mapeamento do AUD |

> 🔎 **Decisão pendente:** Verificar se o sistema AUD do TRT 2ª Região expõe API ou se a injeção via DOM é a única via viável.

### Pré-requisito para opção A (script de injeção)

**4.1 — Botão "Gerar Script AUD" no painel da secretaria**

No `Card` de cada processo, adicionar botão ao lado de "Copiar para o AUD":

```tsx
<button onClick={() => gerarScriptAud(proc, parts, info)}>
  Gerar Script AUD
</button>
```

**4.2 — Função `gerarScriptAud`**

```ts
// ⚠️ Os seletores CSS abaixo são HIPOTÉTICOS — mapear após inspeção do DOM do AUD
const gerarScriptAud = (proc: string, parts: any[], info: any) => {
  const linhas = parts.map(p => {
    // Gerar uma linha de preenchimento por campo
    return `document.querySelector('[data-campo="nome_${p.papel}"]').value = "${p.nome}";`;
  });
  const script = linhas.join("\n");
  navigator.clipboard.writeText(script);
  // Exibir toast de confirmação
};
```

**4.3 — Armazenamento no Supabase para auditoria**

Adicionar tabela `exportacoes_aud`:
```sql
CREATE TABLE IF NOT EXISTS exportacoes_aud (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  processo_id text REFERENCES processos(id) ON DELETE CASCADE,
  exportado_em timestamptz DEFAULT now(),
  metodo text, -- "script_js" | "texto_manual" | "api"
  conteudo text
);
```

---

## Checklist geral de compatibilidade Supabase

Ao implementar cada fase, verificar:

- [ ] Novas colunas no Supabase criadas via migration SQL
- [ ] `dbSaveProcessos` atualizado para incluir novos campos
- [ ] `dbGetProcessos` / `dbGetCheckins` retornam novos campos (ajustar `?select=*` se necessário)
- [ ] Mock localStorage atualizado para espelhar novos campos (para testes locais)
- [ ] Nenhuma feature nova depende exclusivamente de estado em memória (deve persistir no Supabase)
- [ ] Token PJe nunca enviado ao Supabase (apenas localStorage)