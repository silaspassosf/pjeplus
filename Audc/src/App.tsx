import { useState, useRef, useEffect, useCallback } from "react";

// ── LOCAL STORAGE ──
const STORAGE_PROCESSOS = "audicheck_processos";
const STORAGE_CHECKINS = "audicheck_checkins";

const dbGetProcessos = async () => {
  const raw = localStorage.getItem(STORAGE_PROCESSOS);
  const processos = raw ? JSON.parse(raw) : {};
  return Object.entries(processos).map(([id, p]: any) => ({
    id,
    data: p.data,
    hora: p.hora,
    partes: p.partes,
    tipo: p.tipo,
    tipo_aud: p.tipoAud || "",
    encerrada: p.encerrada || false,
  }));
};

const dbSaveProcessos = async (procs: any) => {
  const current = load(STORAGE_PROCESSOS, {});
  const rows = Object.entries(procs).map(([id, p]: any) => {
    const row = {
      id,
      data: p.data,
      hora: p.hora,
      partes: p.partes,
      tipo: p.tipo,
      tipo_aud: p.tipoAud || "",
      encerrada: p.encerrada || false,
    };
    current[id] = row;
    return row;
  });
  save(STORAGE_PROCESSOS, current);
  return rows;
};

const dbEncerrar = async (id: string) => {
  const checkins = load(STORAGE_CHECKINS, []);
  save(
    STORAGE_CHECKINS,
    checkins.filter((c: any) => c.processo_id !== id)
  );

  const processos = load(STORAGE_PROCESSOS, {});
  if (processos[id]) {
    processos[id].encerrada = true;
    save(STORAGE_PROCESSOS, processos);
  }
};

const dbLimpar = async () => {
  save(STORAGE_PROCESSOS, {});
  save(STORAGE_CHECKINS, []);
};

const dbGetCheckins = async () => load(STORAGE_CHECKINS, []);

const dbSaveCheckin = async (c: any) => {
  const checkins = load(STORAGE_CHECKINS, []);
  const hora = c.hora || now();
  const id = `${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  const row = { ...c, hora, id };
  checkins.push(row);
  save(STORAGE_CHECKINS, checkins);
  return row;
};


// ── CONSTANTES ──
const RAIO_METROS = 1000;
const RETORNO_SEG = 120;
const STORAGE_SENHAS = "audicheck_v3_senha";
const STORAGE_GRUPO = "audicheck_grupo_habilitado";
const getGrupoHabilitado = () => { try { return localStorage.getItem(STORAGE_GRUPO) !== "0"; } catch { return true; } };
const setGrupoHabilitado = (v: boolean) => { try { localStorage.setItem(STORAGE_GRUPO, v ? "1" : "0"); } catch {} };

const FORUM = {
  nome: "Forum Trabalhista da Zona Sul",
  endereco: "Av. Guido Caloi, 1.000 - Jardim Sao Luis, Sao Paulo/SP",
  lat: -23.6555,
  lng: -46.7243,
};

// Cores dos polos
const COR_REC = "#27ae60";   // verde — polo reclamante
const COR_RDO = "#e67e22";   // laranja — polo reclamado

const POLO_REC_PAPEIS = ["Parte Reclamante","Representante do(a) Reclamante","Advogado(a) do(a) Reclamante","Testemunha do(a) Reclamante"];
const POLO_RDO_PAPEIS = ["Parte Reclamada","Advogado(a) do(a) Reclamado(a)","Representante do(a) Reclamado(a)","Testemunha do(a) Reclamado(a)"];

const corPorPapel = (papel: string) =>
  POLO_REC_PAPEIS.includes(papel) ? COR_REC : POLO_RDO_PAPEIS.includes(papel) ? COR_RDO : "#1a3a6b";

// Extrai reclamantes e reclamadas do campo partes (usado em vários componentes)
const extrairPartesDoTexto = (texto: string) => {
  if (!texto) return { reclamantes: [], reclamadas: [] };
  const partes = texto.split(/\s+[Xx]\s+/);
  const limpar = (s: string) =>
    s.replace(/\s+/g, " ").replace(/^\s*[,;e]\s*/, "").trim()
      .split(/\s*[,;]\s*|\s+e\s+(?=[A-Z])/)
      .map((n: string) => n.trim()).filter((n: string) => n.length > 2);
  return {
    reclamantes: partes.length >= 1 ? limpar(partes[0]) : [],
    reclamadas:  partes.length >= 2 ? limpar(partes.slice(1).join(" X ")) : [],
  };
};

const PAPEIS = [
  "Parte Reclamante",
  "Advogado(a) do(a) Reclamante",
  "Testemunha do(a) Reclamante",
  "Representante do(a) Reclamado(a)",
  "Advogado(a) do(a) Reclamado(a)",
  "Testemunha do(a) Reclamado(a)",
];
const PLABEL: any = {
  "Parte Reclamante": "Reclamante",
  "Parte Reclamada": "Reclamado(a)",
  "Representante do(a) Reclamante": "Rep. Reclamante",
  "Advogado(a) do(a) Reclamante": "Advogado(a) Reclamante",
  "Advogado(a) do(a) Reclamado(a)": "Advogado(a) Reclamado(a)",
  "Representante do(a) Reclamado(a)": "Representante",
  "Testemunha do(a) Reclamante": "Testemunha Reclamante",
  "Testemunha do(a) Reclamado(a)": "Testemunha Reclamado(a)",
};

const fCPF = (v: string) =>
  v
    .replace(/\D/g, "")
    .slice(0, 11)
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
const fCEP = (v: string) =>
  v
    .replace(/\D/g, "")
    .slice(0, 8)
    .replace(/(\d{5})(\d)/, "$1-$2");
const fOAB = (v: string) =>
  v
    .replace(/[^a-zA-Z0-9]/g, "")
    .slice(0, 12)
    .toUpperCase();

const UFS_VALIDAS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];

const validOAB = (v: string): string | null => {
  const s = v.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
  if (!s) return "OAB obrigatória";
  const uf = s.slice(0, 2);
  const nums = s.slice(2);
  if (!/^[A-Z]{2}$/.test(uf)) return "Comece com a sigla do estado (ex: SP, RJ)";
  if (!UFS_VALIDAS.includes(uf)) return "UF inválida: " + uf;
  if (!/^\d+$/.test(nums)) return "Após a UF, somente números";
  if (nums.length < 4) return "Número OAB muito curto (mínimo 4 dígitos)";
  if (nums.length > 10) return "Número OAB muito longo (máximo 10 dígitos)";
  return null;
};
const now = () =>
  new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
const dist = (a: number, b: number, c: number, d: number) => {
  const R = 6371000,
    dL = ((c - a) * Math.PI) / 180,
    dG = ((d - b) * Math.PI) / 180,
    x =
      Math.sin(dL / 2) ** 2 +
      Math.cos((a * Math.PI) / 180) *
        Math.cos((c * Math.PI) / 180) *
        Math.sin(dG / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
};
const load = (k: string, d: any) => {
  try {
    const v = localStorage.getItem(k);
    return v ? JSON.parse(v) : d;
  } catch (e) {
    return d;
  }
};
const save = (k: string, v: any) => {
  try {
    localStorage.setItem(k, JSON.stringify(v));
  } catch (e) {}
};
const getSenhas = () => load(STORAGE_SENHAS, { secretaria: "3vtzs2026" });

const validCPF = (cpf: string) => {
  const n = cpf.replace(/\D/g, "");
  if (n.length !== 11 || /^(\d)\1{10}$/.test(n)) return false;
  let s = 0;
  for (let i = 0; i < 9; i++) s += parseInt(n[i]) * (10 - i);
  let r = (s * 10) % 11;
  if (r === 10 || r === 11) r = 0;
  if (r !== parseInt(n[9])) return false;
  s = 0;
  for (let i = 0; i < 10; i++) s += parseInt(n[i]) * (11 - i);
  r = (s * 10) % 11;
  if (r === 10 || r === 11) r = 0;
  return r === parseInt(n[10]);
};

// ── PARSER PAUTA ──
const parsePauta = (texto: string) => {
  const procs: any = {};
  const rP = /(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})/;
  const rD = /(\d{2}\/\d{2}\/\d{4})/;
  const validaHora = (h: string) => {
    const [hh, mm] = h.split(":").map(Number);
    return hh >= 0 && hh <= 23 && mm >= 0 && mm <= 59;
  };
  const linhas = texto
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  for (let i = 0; i < linhas.length; i++) {
    const l = linhas[i];
    const mP = l.match(rP);
    if (!mP) continue;
    const num = mP[1];

    const blocoLinhas = [l];
    for (let k = i + 1; k < Math.min(linhas.length, i + 8); k++) {
      if (linhas[k].match(rP)) break;
      blocoLinhas.push(linhas[k]);
    }
    const bloco = blocoLinhas.join("\n");

    let ho = "";
    const h1 = [...l.matchAll(/\b(\d{2}:\d{2}):\d{2}\b/g)]
      .map((m) => m[1])
      .filter(validaHora);
    if (h1.length) ho = h1[0];
    if (!ho) {
      const bs = bloco.split(/\d{2}\/\d{2}\/\d{4}/)[0];
      const hb = [...bs.matchAll(/\b(\d{2}:\d{2}):\d{2}\b/g)]
        .map((m) => m[1])
        .filter(validaHora);
      if (hb.length && bs.match(/AT(?:Ord|Sum|Esp)/i)) ho = hb[0];
    }
    if (!ho) {
      for (let k = i - 1; k >= Math.max(0, i - 3); k--) {
        if (linhas[k].match(rP)) break;
        const mH = linhas[k].match(/\b(\d{2}:\d{2}):\d{2}\b/);
        if (mH && validaHora(mH[1])) {
          ho = mH[1];
          break;
        }
      }
    }

    let da = "";
    const mDB = bloco.match(rD);
    if (mDB) da = mDB[1];
    if (!da) {
      for (let k = i - 1; k >= Math.max(0, i - 4); k--) {
        const mD = linhas[k].match(rD);
        if (mD) {
          da = mD[1];
          break;
        }
        if (linhas[k].match(rP)) break;
      }
    }

    let tipo = "";
    const mTipo = bloco.match(/AT(?:Ord|Sum|Esp)\s+([\s\S]+?)(?:\s+\d{2}\/\d{2}\/\d{4}|\s+\d{2}:\d{2}:\d{2}|$)/i);
    if (mTipo) tipo = mTipo[1].replace(/\n/g, " ").replace(/\d{2}\/\d{2}\/\d{4}/g, "").trim();

    let partes = "";
    const posNum = bloco.indexOf(num);
    const aposNum = bloco.slice(posNum + num.length);
    const mPartes = aposNum.match(
      /^([\s\S]+?)(?=AT(?:Ord|Sum|Esp)|\d{2}:\d{2}:\d{2}|$)/i
    );
    if (mPartes) {
      partes = mPartes[1]
        .replace(/\n/g, " ")
        .replace(/\d{2}\/\d{2}\/\d{4}/g, "")
        .replace(/\d{2}:\d{2}(:\d{2})?/g, "")
        .replace(/^[,\s]+/, "")
        .trim();
    }
    if (!partes) {
      let j = i + 1;
      const pl = [];
      while (j < linhas.length) {
        const nx = linhas[j];
        if (nx.match(rP) || nx.match(rD)) break;
        if (nx.match(/^AT(Ord|Sum|Esp)\b/i)) break;
        if (
          nx.match(
            /^(Una\b|Instrução|Instrucao|videoconfer|sumari|Inicia em|Aguardando|Copiar|──)/i
          )
        )
          break;
        pl.push(nx);
        j++;
      }
      partes = pl.join(" ").trim();
    }
    partes = partes.replace(/^[,\s]+/, "").trim();

    const ehVideoconferencia = /videoconfer[eê]ncia/i.test(tipo) || /videoconfer[eê]ncia/i.test(bloco);
    procs[num] = {
      data: da,
      hora: ho,
      partes,
      tipo: ehVideoconferencia ? "videoconferência" : "presencial",
      tipoAud: tipo,
      encerrada: false,
      forumLat: FORUM.lat,
      forumLng: FORUM.lng,
    };
  }
  return procs;
};

// ── ORDEM DE EXIBIÇÃO ──
const ORDEM_REC = ["Parte Reclamante","Representante do(a) Reclamante","Advogado(a) do(a) Reclamante","Testemunha do(a) Reclamante"];
const ORDEM_RDO = ["Parte Reclamada","Representante do(a) Reclamado(a)","Advogado(a) do(a) Reclamado(a)","Testemunha do(a) Reclamado(a)"];
const ordemPapel = (papel: string, lista: string[]) => { const i = lista.indexOf(papel); return i === -1 ? 99 : i; };

const agruparPorReclamada = (partsRdo: any[], reclamadasDaPauta: string[]) => {
  // Explode participantes com múltiplas reclamadas em cada grupo correspondente
  const mapa: Record<string, any[]> = {};
  const semReclamada: any[] = [];

  partsRdo.forEach((p: any) => {
    // testemunha usa parte_ouvinte; representantes/advogados usam empresa_representada ou parte_representada
    const campo = p.empresa_representada || p.parte_representada || p.parte_ouvinte || null;
    if (!campo) { semReclamada.push(p); return; }
    const recs = campo.split(" | ").map((s: string) => s.trim()).filter(Boolean);
    if (recs.length === 0) { semReclamada.push(p); }
    else { recs.forEach((rec: string) => { (mapa[rec] = mapa[rec] || []).push(p); }); }
  });

  const todasRecs = reclamadasDaPauta.length > 0 ? reclamadasDaPauta : Object.keys(mapa);
  const vistas = new Set<string>();
  const grupos: { reclamada: string | null; parts: any[] }[] = [];

  todasRecs.forEach((rec) => {
    if (!vistas.has(rec) && mapa[rec]) { vistas.add(rec); grupos.push({ reclamada: rec, parts: mapa[rec] }); }
  });
  Object.keys(mapa).forEach((rec) => {
    if (!vistas.has(rec)) { vistas.add(rec); grupos.push({ reclamada: rec, parts: mapa[rec] }); }
  });
  if (semReclamada.length) grupos.push({ reclamada: null, parts: semReclamada });
  return grupos;
};

// ── RELATÓRIO AUD ──
const relatorio = (proc: string, parts: any[], info: any) => {
  const { reclamantes, reclamadas } = extrairPartesDoTexto(info?.partes || "");
  const vt = info && info?.tipo === "videoconferência" ? " (virtual)" : "";
  let t = "PROCESSO: " + proc + "\n" + "─".repeat(50) + "\n";
  if (info?.tipo === "videoconferência")
    t += "MODALIDADE: Audiência Virtual (Zoom)\n" + "─".repeat(50) + "\n";

  // ── Polo Reclamante ──
  parts.filter(p => p.papel === "Parte Reclamante").forEach(p =>
    t += "RECLAMANTE: " + (p.nome||"").toUpperCase() + ", presente" + vt + ". (check-in: " + (p.hora || "?") + ")\n"
  );
  parts.filter(p => p.papel === "Representante do(a) Reclamante").forEach(p => {
    const rec = p.parte_representada || "";
    const prefixo = rec ? "REPRESENTANTE DO RECLAMANTE " + rec.toUpperCase() + ":" : "REPRESENTANTE DO RECLAMANTE:";
    t += prefixo + " " + (p.nome||"").toUpperCase() + ". (check-in: " + (p.hora || "?") + ")\n";
  });
  parts.filter(p => p.papel === "Advogado(a) do(a) Reclamante").forEach(p => {
    const rep = p.parte_representada || "";
    const repFormatado = rep.includes(" | ")
      ? rep.split(" | ").map((s: string) => s.trim()).join(" e ").toUpperCase()
      : rep.toUpperCase();
    const prefixo = rep ? "ADVOGADO(A) DO(A) RECLAMANTE " + repFormatado + ":" : "ADVOGADO(A) DO(A) RECLAMANTE:";
    const oabUF1 = (() => { const o = (p.oab||"").replace(/[^a-zA-Z0-9]/g,"").toUpperCase(); return /^[A-Z]{2}/.test(o) ? o.slice(0,2) : "SP"; })();
    const oabNum1 = (() => { const o = (p.oab||"").replace(/[^a-zA-Z0-9]/g,"").toUpperCase(); return /^[A-Z]{2}/.test(o) ? o.slice(2) : p.oab||""; })();
    t += prefixo + " " + (p.nome||"").toUpperCase() + ", OAB/" + oabUF1 + " nº " + oabNum1 + ". (check-in: " + (p.hora || "?") + ")\n";
    if (p.regularizacao) (p.regularizacao as string).split(" | ").filter(Boolean).forEach((pend: string) => t += "*** PRAZO PARA: " + pend.toUpperCase() + " ***\n");
  });
  parts.filter(p => p.papel === "Testemunha do(a) Reclamante").forEach(p => {
    const parteOuvinte = p.parte_representada || p.parte_ouvinte || "";
    const prefixo = parteOuvinte ? "TESTEMUNHA DO RECLAMANTE " + parteOuvinte.toUpperCase() + ":" : "TESTEMUNHA DO RECLAMANTE:";
    t += prefixo + " " + (p.nome||"").toUpperCase() + ", CPF " + (p.cpf || "não informado") + ", residente em " + (p.endereco || "não informado") +
      (p.numero ? ", " + p.numero : "") + (p.complemento ? ", " + p.complemento : "") + (p.cep ? " - CEP " + p.cep : "") + ". (check-in: " + (p.hora || "?") + ")\n";
  });

  // ── Polo Reclamado — agrupado por reclamada ──
  const partsRdo = parts.filter(p => POLO_RDO_PAPEIS.includes(p.papel))
    .sort((a, b) => ordemPapel(a.papel, ORDEM_RDO) - ordemPapel(b.papel, ORDEM_RDO));
  const grupos = agruparPorReclamada(partsRdo, reclamadas);

  grupos.forEach(({ reclamada, parts: gp }) => {
    gp.filter((p: any) => p.papel === "Parte Reclamada").forEach((p: any) =>
      t += "RECLAMADO: " + (p.nome||"").toUpperCase() + ", presente" + vt + ". (check-in: " + (p.hora || "?") + ")\n"
    );
    gp.filter((p: any) => p.papel === "Representante do(a) Reclamado(a)").forEach((p: any) => {
      const empresa = p.empresa_representada || p.parte_representada || reclamada || "";
      const prefixo = empresa ? "REPRESENTANTE DO RECLAMADO " + empresa.toUpperCase() + ":" : "REPRESENTANTE DO RECLAMADO:";
      // Resolve subtipo: se JSON por reclamada, filtra pelo contexto atual
      const resolveSubtipoRel = () => {
        if (!p.subtipo_representante) return "";
        try {
          const obj = JSON.parse(p.subtipo_representante);
          if (typeof obj === "object" && obj !== null) {
            if (reclamada && obj[reclamada]) return " (" + obj[reclamada] + ")";
            const vals = [...new Set(Object.values(obj) as string[])];
            return vals.length === 1 ? " (" + vals[0] + ")" : " (" + Object.entries(obj).map(([r, v]) => v + " (" + r + ")").join(" / ") + ")";
          }
        } catch {
          // string resolvida ex: "Sócio(a) (Rec A) / Preposto(a) (Rec B)"
          if (reclamada && p.subtipo_representante.includes("/")) {
            const partes = p.subtipo_representante.split(" / ");
            const match = partes.find((parte: string) => parte.includes(reclamada));
            if (match) return " (" + match.replace(/\s*\([^)]*\)\s*$/, "").trim() + ")";
          }
        }
        return p.subtipo_representante ? " (" + p.subtipo_representante + ")" : "";
      };
      t += prefixo + " " + (p.nome||"").toUpperCase() + resolveSubtipoRel() + ". (check-in: " + (p.hora || "?") + ")\n";
    });
    gp.filter((p: any) => p.papel === "Advogado(a) do(a) Reclamado(a)").forEach((p: any) => {
      const rep = p.empresa_representada || p.parte_representada || reclamada || "";
      const prefixo = rep ? "ADVOGADO(A) DO(A) RECLAMADO(A) " + rep.toUpperCase() + ":" : "ADVOGADO(A) DO(A) RECLAMADO(A):";
      const oabUF3 = (() => { const o = (p.oab||"").replace(/[^a-zA-Z0-9]/g,"").toUpperCase(); return /^[A-Z]{2}/.test(o) ? o.slice(0,2) : "SP"; })();
      const oabNum3 = (() => { const o = (p.oab||"").replace(/[^a-zA-Z0-9]/g,"").toUpperCase(); return /^[A-Z]{2}/.test(o) ? o.slice(2) : p.oab||""; })();
      t += prefixo + " " + (p.nome||"").toUpperCase() + ", OAB/" + oabUF3 + " nº " + oabNum3 + ". (check-in: " + (p.hora || "?") + ")\n";
      if (p.regularizacao) (p.regularizacao as string).split(" | ").filter(Boolean).forEach((pend: string) => t += "*** PRAZO PARA: " + pend.toUpperCase() + " ***\n");
    });
    gp.filter((p: any) => p.papel === "Testemunha do(a) Reclamado(a)").forEach((p: any) => {
      const parteOuvinte = p.parte_ouvinte || p.empresa_representada || reclamada || "";
      const prefixo = parteOuvinte ? "TESTEMUNHA DO RECLAMADO " + parteOuvinte.toUpperCase() + ":" : "TESTEMUNHA DO RECLAMADO:";
      t += prefixo + " " + (p.nome||"").toUpperCase() + ", CPF " + (p.cpf || "não informado") + ", residente em " + (p.endereco || "não informado") +
        (p.numero ? ", " + p.numero : "") + (p.complemento ? ", " + p.complemento : "") + (p.cep ? " - CEP " + p.cep : "") + ". (check-in: " + (p.hora || "?") + ")\n";
    });
  });

  return t.trim();
};

// ── ESTILOS GLOBAIS (injetados uma vez) ──
const GLOBAL_STYLE = `
  @keyframes fadeInUp { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:translateY(0); } }
  @keyframes fadeIn   { from { opacity:0; } to { opacity:1; } }
  @keyframes pulse    { 0%,100% { transform:scale(1); } 50% { transform:scale(1.06); } }
  @keyframes spin     { to { transform:rotate(360deg); } }
  @keyframes checkPop { 0% { transform:scale(0) rotate(-15deg); opacity:0; } 70% { transform:scale(1.15) rotate(3deg); } 100% { transform:scale(1) rotate(0); opacity:1; } }
  @keyframes notifSlide { from { opacity:0; transform:translateX(60px); } to { opacity:1; transform:translateX(0); } }
  * { -webkit-tap-highlight-color: transparent; }
  input, select, textarea, button { font-family: inherit; }
  ::-webkit-scrollbar { width: 5px; } 
  ::-webkit-scrollbar-track { background: #f0f0f0; border-radius: 10px; }
  ::-webkit-scrollbar-thumb { background: #c0c8d8; border-radius: 10px; }
`;

function GlobalStyle() {
  useEffect(() => {
    const el = document.createElement("style");
    el.textContent = GLOBAL_STYLE;
    document.head.appendChild(el);
    return () => {
      document.head.removeChild(el);
    };
  }, []);
  return null;
}

// ── SPINNER ──
function Spinner({ size = 20, color = "#1a3a6b" }: any) {
  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: `3px solid ${color}22`,
        borderTop: `3px solid ${color}`,
        borderRadius: "50%",
        animation: "spin .7s linear infinite",
        verticalAlign: "middle",
      }}
    />
  );
}

// ── NOTIFICAÇÃO TOAST ──
function Toast({ msg, tipo = "ok" }: any) {
  return (
    <div
      style={{
        position: "fixed",
        top: "50%",
        right: 16,
        transform: "translateY(-50%)",
        zIndex: 9999,
        background: tipo === "ok" ? "#1e7e3e" : "#c62828",
        color: "#fff",
        borderRadius: 14,
        padding: "18px 32px",
        fontSize: 16,
        fontWeight: 700,
        boxShadow: "0 12px 40px rgba(0,0,0,.35)",
        animation: "fadeIn .25s ease",
        maxWidth: 360,
        textAlign: "center",
        lineHeight: 1.5,
        fontFamily: "'Segoe UI', sans-serif",
      }}
    >
      {msg}
    </div>
  );
}

// ── MODAL CONFIRMAR ──
function MConfirmar({ titulo, msg, cor, btn, onOk, onCancel }: any) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
        padding: 16,
        animation: "fadeIn .2s ease",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 16,
          padding: 28,
          maxWidth: 380,
          width: "100%",
          boxShadow: "0 16px 48px rgba(0,0,0,.3)",
          textAlign: "center",
          fontFamily: "'Segoe UI',sans-serif",
          animation: "fadeInUp .25s ease",
        }}
      >
        <h3 style={{ margin: "0 0 10px", color: cor || "#333", fontSize: 18 }}>
          {titulo}
        </h3>
        <p
          style={{
            fontSize: 13,
            color: "#666",
            margin: "0 0 22px",
            lineHeight: 1.7,
            whiteSpace: "pre-line",
          }}
        >
          {msg}
        </p>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onCancel}
            style={{
              flex: 1,
              background: "#eee",
              color: "#555",
              border: "none",
              borderRadius: 9,
              padding: "12px",
              fontSize: 14,
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Cancelar
          </button>
          <button
            onClick={onOk}
            style={{
              flex: 1,
              background: cor || "#1a3a6b",
              color: "#fff",
              border: "none",
              borderRadius: 9,
              padding: "12px",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            {btn || "Confirmar"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── MODAL IMPORTAR ──
function MImport({ onImportar, onFechar }: any) {
  const [txt, setTxt] = useState("");
  
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 16,
        animation: "fadeIn .2s ease",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 16,
          padding: 26,
          maxWidth: 500,
          width: "100%",
          boxShadow: "0 16px 48px rgba(0,0,0,.3)",
          fontFamily: "'Segoe UI',sans-serif",
          animation: "fadeInUp .25s ease",
        }}
      >
        <h3 style={{ margin: "0 0 12px", color: "#1a3a6b" }}>Importar Pauta</h3>

       
        <div
          style={{
            background: "#f0f4ff",
            border: "1px solid #c7d2fe",
            borderRadius: 10,
            padding: "10px 14px",
            marginBottom: 10,
            fontSize: 12,
            color: "#1a3a6b",
            lineHeight: 1.8,
          }}
        >
          <strong>Como copiar a pauta do PJe:</strong>
          <br />
          1. Abra o PDF da pauta no <strong>Adobe Acrobat</strong>
          <br />
          2. Pressione <strong>Ctrl+A</strong> → <strong>Ctrl+C</strong>
          <br />
          3. Cole abaixo com <strong>Ctrl+V</strong>
        </div>
        <textarea
          value={txt}
          onChange={(e) => setTxt(e.target.value)}
          placeholder="Cole aqui o texto da pauta..."
          style={{
            width: "100%",
            height: 140,
            padding: "10px 12px",
            border: "1.5px solid #ddd",
            borderRadius: 9,
            fontSize: 13,
            boxSizing: "border-box",
            resize: "vertical",
            fontFamily: "monospace",
          }}
        />
        {txt.trim() && (
          <div style={{ fontSize: 12, color: "#888", marginTop: 4, marginBottom: 4 }}>
            {txt.trim().split("\n").filter(Boolean).length} linhas detectadas
          </div>
        )}
        <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
          <button
            onClick={onFechar}
            style={{
              flex: 1,
              background: "#eee",
              color: "#555",
              border: "none",
              borderRadius: 9,
              padding: "11px",
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Cancelar
          </button>
          <button
            onClick={() => onImportar(txt)}
            disabled={!txt.trim()}
            style={{
              flex: 2,
              background: txt.trim() ? "#1a3a6b" : "#bdc3c7",
              color: "#fff",
              border: "none",
              borderRadius: 9,
              padding: "11px",
              fontSize: 14,
              fontWeight: 700,
              cursor: txt.trim() ? "pointer" : "not-allowed",
            }}
          >
            Importar
          </button>
        </div>
      </div>
    </div>
  );
}

// ── CARD PROCESSO (painel secretária) ──

function CopyBtn({ texto }: { texto: string }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(texto); setCopiado(true); setTimeout(() => setCopiado(false), 1500); }}
      title={"Copiar: " + texto}
      style={{
        background: copiado ? "#e8f5e9" : "#f4f6f8",
        border: "1px solid " + (copiado ? "#a5d6a7" : "#dce3ed"),
        borderRadius: 5, padding: "1px 6px", cursor: "pointer",
        fontSize: 11, color: copiado ? "#2e7d32" : "#888",
        display: "inline-flex", alignItems: "center", gap: 3,
        marginLeft: 4, verticalAlign: "middle", transition: "all .2s",
      }}
    >
      {copiado ? "✓" : "⧉"}
    </button>
  );
}

function CardParticipante({ p, ocultarRep, nomeReclamada }: any) {
  const cor = corPorPapel(p.papel);
  const nomeRepRaw = p.empresa_representada || p.parte_representada;
  const nomeRep = nomeRepRaw?.includes(" | ")
    ? nomeRepRaw.split(" | ").map((s: string) => s.trim()).join(" e ")
    : nomeRepRaw;
  const enderecoCompleto = p.endereco
    ? p.endereco + (p.numero ? ", " + p.numero : "") + (p.complemento ? ", " + p.complemento : "")
    : "";
  const pendencias = (p.regularizacao || "").split(" | ").filter(Boolean);
  return (
    <div style={{ marginBottom: 8, paddingLeft: 12, borderLeft: `4px solid ${cor}` }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 4 }}>
        <div style={{ fontWeight: 800, fontSize: 17, color: "#1a1a1a", lineHeight: 1.2 }}>
          {p.nome?.split(" ").map((w: string) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ")}
          {p.subtipo_representante && (() => {
            let sub = p.subtipo_representante;
            try {
              const obj = JSON.parse(sub);
              if (typeof obj === "object" && obj !== null) {
                if (nomeReclamada && obj[nomeReclamada]) {
                  sub = String(obj[nomeReclamada]);
                } else {
                  const vals = [...new Set(Object.values(obj) as string[])];
                  sub = vals.length === 1 ? vals[0] : Object.entries(obj).map(([r, v]) => `${v} (${r})`).join(" / ");
                }
              }
            } catch {
              // subtipo já é string resolvida ex: "Sócio(a) (Rec A) / Preposto(a) (Rec B)"
              if (nomeReclamada && sub.includes("(") && sub.includes("/")) {
                const partes = sub.split(" / ");
                const match = partes.find((parte: string) => parte.includes(nomeReclamada));
                if (match) {
                  sub = match.replace(/\s*\([^)]*\)\s*$/, "").trim();
                }
              }
            }
            return sub ? <span style={{ fontWeight: 400, fontSize: 13, color: "#666", marginLeft: 6 }}>({sub})</span> : null;
          })()}
          <CopyBtn texto={p.nome} />
        </div>
        <span style={{ fontSize: 12, color: "#aaa", flexShrink: 0, paddingTop: 2 }}>{p.hora}</span>
      </div>
      {p.oab && (() => {
        const oabRaw = p.oab.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
        const uf = /^[A-Z]{2}/.test(oabRaw) ? oabRaw.slice(0, 2) : "SP";
        const num = /^[A-Z]{2}/.test(oabRaw) ? oabRaw.slice(2) : oabRaw;
        return (
          <div style={{ fontSize: 13, color: "#555", marginTop: 1, display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ background: "#e8edf5", color: "#1a3a6b", borderRadius: 4, padding: "1px 7px", fontWeight: 700, fontSize: 12 }}>OAB/{uf}</span>
            <span>{num}</span>
            <CopyBtn texto={num} />
          </div>
        );
      })()}
      {pendencias.length > 0 && (
        <div style={{ marginTop: 5, background: "#fff3cd", border: "1px solid #ffe082", borderRadius: 6, padding: "5px 10px", fontSize: 13, fontWeight: 700, color: "#856404" }}>
          ⚠ PRAZO PARA: {pendencias.join(" | ")}
        </div>
      )}
      {(() => {
        if (!p.proposta) return null;
        try {
          const obj = JSON.parse(p.proposta);
          const temValor = Object.values(obj).some((v: any) => v && String(v).trim());
          if (!temValor) return null;
        } catch { if (!p.proposta.trim()) return null; }
        return (
          <div style={{ marginTop: 5, background: "#fef9ec", border: "1px solid #f6cc5a", borderRadius: 6, padding: "4px 10px", fontSize: 12, fontWeight: 700, color: "#92620a", display: "inline-flex", alignItems: "center", gap: 5 }}>
            📋 Proposta registrada — ver painel do(a) juiz(a)
          </div>
        );
      })()}
      {p.cpf && (
        <div style={{ fontSize: 12, color: "#555" }}>
          CPF {p.cpf}<CopyBtn texto={p.cpf} />
          {enderecoCompleto && (
            <> — {enderecoCompleto}<CopyBtn texto={enderecoCompleto} /></>
          )}
        </div>
      )}
    </div>
  );
}

// ── Helpers para agrupamento por parte individual ──
// Retorna participantes do polo reclamante associados a um nome específico de reclamante
const getPartsDeReclamante = (parts: any[], nomeRec: string) => {
  const pertenceRec = (campo: string | null) => {
    if (!campo) return false;
    return campo.split(" | ").map((s: string) => s.trim().toLowerCase()).includes(nomeRec.toLowerCase());
  };
  const parte   = parts.filter((p: any) => p.papel === "Parte Reclamante" &&
    (p.nome?.toLowerCase() === nomeRec.toLowerCase() || pertenceRec(p.parte_representada)));
  const reps    = parts.filter((p: any) => p.papel === "Representante do(a) Reclamante" &&
    pertenceRec(p.parte_representada));
  const advs    = parts.filter((p: any) => p.papel === "Advogado(a) do(a) Reclamante" &&
    pertenceRec(p.parte_representada));
  const tests   = parts.filter((p: any) => p.papel === "Testemunha do(a) Reclamante" &&
    pertenceRec(p.parte_ouvinte || p.parte_representada));
  return { parte, reps, advs, tests };
};

// Retorna participantes do polo reclamado associados a um nome específico de reclamada
const getPartsDeReclamada = (parts: any[], nomeRec: string, unicaReclamada = false) => {
  const pertence = (campo: string | null) => {
    if (!campo) return false;
    return campo.split(" | ").map((s: string) => s.trim().toLowerCase()).includes(nomeRec.toLowerCase());
  };
    // incluidos quando ha uma unica reclamada, evitando que aparecam duplicados em cada bloco.
  const semVinculo = (p: any) => !p.empresa_representada && !p.parte_representada;
  const reps  = parts.filter((p: any) => p.papel === "Representante do(a) Reclamado(a)" &&
    ((unicaReclamada && semVinculo(p)) || pertence(p.empresa_representada || p.parte_representada)));
  const advs  = parts.filter((p: any) => p.papel === "Advogado(a) do(a) Reclamado(a)" &&
    ((unicaReclamada && semVinculo(p)) || pertence(p.empresa_representada || p.parte_representada)));
  const tests = parts.filter((p: any) => p.papel === "Testemunha do(a) Reclamado(a)" &&
    ((!p.parte_ouvinte && !p.empresa_representada && unicaReclamada) || pertence(p.parte_ouvinte || p.empresa_representada)));
  const parte = parts.filter((p: any) => p.papel === "Parte Reclamada" &&
    (p.nome?.toLowerCase() === nomeRec.toLowerCase() || (unicaReclamada && semVinculo(p)) || pertence(p.empresa_representada || p.parte_representada)));
  return { parte, reps, advs, tests };
};

// ── Grupo de participantes do mesmo papel dentro de um bloco de parte ──
function CardGrupoPapel({ label, cor, items, nomeReclamada }: any) {
  if (!items || items.length === 0) return null;
  const multi = items.length > 1;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ marginBottom: 4 }}>
        <span style={{
          color: cor, fontSize: 13, fontWeight: 800,
          textTransform: "uppercase", letterSpacing: 0.5,
        }}>
          {label}
        </span>
      </div>
      {items.map((p: any, i: number) => (
        <div key={i} style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
          {multi && (
            <span style={{ fontSize: 13, fontWeight: 700, color: cor, minWidth: 20, paddingTop: 2, flexShrink: 0 }}>
              {i + 1})
            </span>
          )}
          <div style={{ flex: 1 }}>
            <CardParticipante p={p} ocultarRep nomeReclamada={nomeReclamada} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Card({ proc, info, parts, onCopy, copied, onEnc, onEdit }: any) {
  const rel = relatorio(proc, parts, info);
  const enc = info.encerrada;
  const temCheckin = parts.length > 0;

  const { reclamantes, reclamadas } = extrairPartesDoTexto(info?.partes || "");

  // Contadores globais para badges
  const partsRec = parts.filter((p: any) => POLO_REC_PAPEIS.includes(p.papel));
  const partsRdo = parts.filter((p: any) => POLO_RDO_PAPEIS.includes(p.papel));
  const contadoresRec: any = {};
  partsRec.forEach((p: any) => { const l = PLABEL[p.papel] || p.papel; contadoresRec[l] = (contadoresRec[l] || 0) + 1; });
  const contadoresRdo: any = {};
  partsRdo.forEach((p: any) => { const l = PLABEL[p.papel] || p.papel; contadoresRdo[l] = (contadoresRdo[l] || 0) + 1; });

  return (
    <div
      style={{
        background: "#fff",
        borderRadius: 14,
        boxShadow: enc ? "0 1px 4px rgba(0,0,0,.06)" : "0 3px 14px rgba(26,58,107,.1)",
        marginBottom: 14,
        overflow: "hidden",
        border: enc ? "1px solid #ddd" : "1px solid #c7d2fe",
        animation: "fadeInUp .3s ease",
        opacity: enc ? 0.75 : 1,
        transition: "opacity .3s",
      }}
    >
      {/* cabeçalho */}
      <div
        style={{
          background: enc ? "linear-gradient(135deg,#7f8c8d,#95a5a6)" : "linear-gradient(135deg,#1a3a6b,#2471a3)",
          color: "#fff", padding: "14px 16px", display: "flex",
          justifyContent: "space-between", alignItems: "flex-start",
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: "monospace", fontSize: 11, opacity: 0.7, marginBottom: 3 }}>{proc}</div>
          <div style={{ fontSize: 13, opacity: 0.92, lineHeight: 1.45, fontWeight: 500 }}>{info.partes || ""}</div>
          {enc && (
            <div style={{ marginTop: 5, display: "inline-block", background: "rgba(255,255,255,.2)", borderRadius: 20, padding: "2px 10px", fontSize: 11, fontWeight: 700 }}>
              Encerrada
            </div>
          )}
        </div>
        <div style={{ textAlign: "right", flexShrink: 0, marginLeft: 12 }}>
          <div style={{ fontWeight: 900, fontSize: 22, fontFamily: "monospace" }}>{info.hora || "--:--"}</div>
          <div style={{ fontSize: 11, opacity: 0.65 }}>{info.data}</div>
          {info.tipoAud && <div style={{ fontSize: 11, opacity: 0.65, marginTop: 2 }}>{info.tipoAud}</div>}
        </div>
      </div>

      {/* badges de contagem por polo */}
      {temCheckin && (
        <div style={{ padding: "10px 16px 0", display: "flex", flexWrap: "wrap", gap: 5 }}>
          {Object.entries(contadoresRec).map(([label, qtd]: any) => (
            <span key={label} style={{ background: COR_REC + "18", color: COR_REC, borderRadius: 20, padding: "4px 12px", fontSize: 12, fontWeight: 700 }}>{label}: {qtd}</span>
          ))}
          {Object.entries(contadoresRdo).map(([label, qtd]: any) => (
            <span key={label} style={{ background: COR_RDO + "18", color: COR_RDO, borderRadius: 20, padding: "4px 12px", fontSize: 12, fontWeight: 700 }}>{label}: {qtd}</span>
          ))}
        </div>
      )}

      {/* corpo */}
      <div style={{ padding: "12px 16px" }}>
        {!temCheckin ? (
          <div style={{ color: "#bbb", fontSize: 13, fontStyle: "italic", textAlign: "center", padding: "10px 0" }}>
            Aguardando check-ins...
          </div>
        ) : (
          <div style={{ marginBottom: 10 }}>

            {/* ── Polo Ativo ── */}
            {partsRec.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, color: COR_REC }}>Polo Ativo</span>
                <div style={{ flex: 1, height: 2, background: COR_REC, borderRadius: 2 }} />
              </div>

            {/* ── Polo Reclamante — um bloco por reclamante da pauta ── */}
            {(() => {
              // Se não há nomes na pauta, agrupa tudo junto; se há, itera por cada reclamante
              const nomes = reclamantes.length > 0 ? reclamantes : [null];
              const blocos = nomes.map((nomeRec: string | null, ri: number) => {
                let parte: any[], reps: any[] = [], advs: any[], tests: any[];
                if (nomeRec) {
                  ({ parte, reps, advs, tests } = getPartsDeReclamante(parts, nomeRec));
                } else {
                  parte  = parts.filter((p: any) => p.papel === "Parte Reclamante");
                  reps   = parts.filter((p: any) => p.papel === "Representante do(a) Reclamante");
                  advs   = parts.filter((p: any) => p.papel === "Advogado(a) do(a) Reclamante");
                  tests  = parts.filter((p: any) => p.papel === "Testemunha do(a) Reclamante");
                }
                const tem = parte.length + reps.length + advs.length + tests.length > 0;
                if (!tem) return null;
                return (
                  <div key={"rec" + ri} style={{ marginBottom: 10, padding: "8px 10px", borderRadius: 8, border: `1px solid ${COR_REC}30`, background: COR_REC + "06" }}>
                    <div style={{ marginBottom: 10, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{
                        display: "inline-block", background: COR_REC, color: "#fff",
                        fontSize: 18, fontWeight: 800, padding: "5px 14px", borderRadius: 7, lineHeight: 1.2,
                      }}>
                        {reclamantes.length > 1 ? `${ri + 1}. ${nomeRec || "Reclamante"}` : (nomeRec || "Reclamante")}
                      </span>
                      {(() => { const primeiraHora = [...parte, ...(advs||[]), ...(reps||[]), ...(tests||[])][0]?.hora; return primeiraHora ? <span style={{ fontSize: 12, color: "#aaa", marginLeft: 4 }}>{primeiraHora}</span> : null; })()}
                    </div>
                    <CardGrupoPapel label="Reclamante" cor={COR_REC} items={parte} />
                    <CardGrupoPapel label="Representante do(a) Reclamante" cor={COR_REC} items={reps} />
                    <CardGrupoPapel label="Advogado(a) do(a) Reclamante" cor={COR_REC} items={advs} />
                    <CardGrupoPapel label="Testemunha do(a) Reclamante" cor={COR_REC} items={tests} />
                  </div>
                );
              }).filter(Boolean);

              // Participantes do reclamante sem reclamante associado (quando há nomes na pauta)
              if (reclamantes.length > 0) {
                // Coleta IDs de todos os participantes já exibidos em algum bloco nomeado
                const jaExibidos = new Set<any>();
                reclamantes.forEach((nomeRec: string) => {
                  const { parte, reps, advs, tests } = getPartsDeReclamante(parts, nomeRec);
                  [...parte, ...reps, ...advs, ...tests].forEach((p: any) => jaExibidos.add(p));
                });
                const semAssoc = parts.filter((p: any) =>
                  ["Parte Reclamante","Representante do(a) Reclamante","Advogado(a) do(a) Reclamante","Testemunha do(a) Reclamante"].includes(p.papel) &&
                  !jaExibidos.has(p)
                );
                if (semAssoc.length > 0) {
                  blocos.push(
                    <div key="rec_sem" style={{ marginBottom: 10, padding: "8px 10px", borderRadius: 8, border: `1px solid ${COR_REC}30`, background: COR_REC + "06" }}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: COR_REC, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Polo Ativo — sem identificação de parte</div>
                      <CardGrupoPapel label="Reclamante" cor={COR_REC} items={semAssoc.filter((p: any) => p.papel === "Parte Reclamante")} />
                      <CardGrupoPapel label="Advogado(a) do(a) Reclamante" cor={COR_REC} items={semAssoc.filter((p: any) => p.papel === "Advogado(a) do(a) Reclamante")} />
                      <CardGrupoPapel label="Testemunha do(a) Reclamante" cor={COR_REC} items={semAssoc.filter((p: any) => p.papel === "Testemunha do(a) Reclamante")} />
                    </div>
                  );
                }
              }
              return blocos;
            })()}

            </div>
            )}

            {/* ── Polo Passivo ── */}
            {partsRdo.length > 0 && (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, color: COR_RDO }}>Polo Passivo</span>
                <div style={{ flex: 1, height: 2, background: COR_RDO, borderRadius: 2 }} />
              </div>

            {/* ── Polo Reclamado — um bloco por reclamada da pauta ── */}
            {(() => {
              const nomes = reclamadas.length > 0 ? reclamadas : [null];
              const blocos = nomes.map((nomeRec: string | null, ri: number) => {
                let parte: any[], reps: any[], advs: any[], tests: any[];
                if (nomeRec) {
                  ({ parte, reps, advs, tests } = getPartsDeReclamada(parts, nomeRec, reclamadas.length === 1));
                } else {
                  parte = parts.filter((p: any) => p.papel === "Parte Reclamada");
                  reps  = parts.filter((p: any) => p.papel === "Representante do(a) Reclamado(a)");
                  advs  = parts.filter((p: any) => p.papel === "Advogado(a) do(a) Reclamado(a)");
                  tests = parts.filter((p: any) => p.papel === "Testemunha do(a) Reclamado(a)");
                }
                const tem = parte.length + reps.length + advs.length + tests.length > 0;
                if (!tem) return null;
                return (
                  <div key={"rdo" + ri} style={{ marginBottom: ri < nomes.length - 1 ? 10 : 0, padding: "8px 10px", borderRadius: 8, border: `1px solid ${COR_RDO}30`, background: COR_RDO + "06" }}>
                    <div style={{ marginBottom: 10, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{
                        display: "inline-block", background: COR_RDO, color: "#fff",
                        fontSize: 18, fontWeight: 800, padding: "5px 14px", borderRadius: 7, lineHeight: 1.2,
                      }}>
                        {reclamadas.length > 1 ? `${ri + 1}. ${nomeRec || "Reclamado(a)"}` : (nomeRec || "Reclamado(a)")}
                      </span>
                    </div>
                    <CardGrupoPapel label="Reclamado(a)" cor={COR_RDO} items={parte} nomeReclamada={nomeRec} />
                    <CardGrupoPapel label="Representante do(a) Reclamado(a)" cor={COR_RDO} items={reps} nomeReclamada={nomeRec} />
                    <CardGrupoPapel label="Advogado(a) do(a) Reclamado(a)" cor={COR_RDO} items={advs} nomeReclamada={nomeRec} />
                    <CardGrupoPapel label="Testemunha do(a) Reclamado(a)" cor={COR_RDO} items={tests} nomeReclamada={nomeRec} />
                  </div>
                );
              }).filter(Boolean);
              return blocos.length > 0 ? <>{blocos}</> : null;
            })()}

            </div>
            )}

            {/* linha separadora antes dos botões */}
            <div style={{ borderTop: "1px solid #f0f0f0", marginTop: 10 }} />
          </div>
        )}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: temCheckin ? 8 : 0 }}>
          {temCheckin && (
            <button onClick={() => onCopy(proc, parts)}
              style={{ flex: 2, background: copied === proc ? "#1e7e3e" : "#1a3a6b", color: "#fff", border: "none", borderRadius: 8, padding: "10px 16px", fontSize: 13, fontWeight: 700, cursor: "pointer", minWidth: 140, transition: "background .3s" }}>
              {copied === proc ? "✓ Copiado!" : "Copiar para o AUD"}
            </button>
          )}
          {!enc && (
            <button onClick={() => onEdit(proc)}
              style={{ background: "rgba(26,58,107,.08)", color: "#1a3a6b", border: "1px solid #1a3a6b", borderRadius: 8, padding: "10px 14px", fontSize: 12, cursor: "pointer", fontWeight: 600 }}>
              Editar
            </button>
          )}
          {!enc && (
            <button onClick={() => onEnc(proc)}
              style={{ background: "rgba(231,76,60,.08)", color: "#e74c3c", border: "1px solid #e74c3c", borderRadius: 8, padding: "10px 14px", fontSize: 12, cursor: "pointer", fontWeight: 600 }}>
              Encerrar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── CARTAZES QR ──
function MCartazes({ procs, onFechar }: any) {
  const [gerando, setGerando] = useState(false);
  const gerar = () => {
    setGerando(true);
    const lista = Object.entries(procs)
      .filter(([, i]: any) => !i.encerrada)
      .sort((a: any, b: any) => a[1].hora.localeCompare(b[1].hora));
    if (!lista.length) {
      const t = document.createElement("div");
      t.textContent = "Nenhuma audiência ativa para gerar QR Codes.";
      Object.assign(t.style, { position:"fixed", top:"50%", right:"16px", transform:"translateY(-50%)", background:"#e65100", color:"#fff", borderRadius:"14px", padding:"16px 22px", fontSize:"14px", fontWeight:"700", zIndex:"9999", fontFamily:"'Segoe UI',sans-serif", boxShadow:"0 8px 30px rgba(0,0,0,.3)" });
      document.body.appendChild(t); setTimeout(() => t.remove(), 3500);
      setGerando(false);
      return;
    }
    const APP_URL = window.location.href.split("?")[0];
    const carregar = () => {
      const divs = lista.map(([num]: any) => {
        const url = APP_URL + "?proc=" + encodeURIComponent(num);
        const d = document.createElement("div");
        document.body.appendChild(d);
        d.style.cssText = "position:absolute;left:-9999px;";
        new (window as any).QRCode(d, {
          text: url,
          width: 120,
          height: 120,
          colorDark: "#1a3a6b",
          colorLight: "#fff",
          correctLevel: (window as any).QRCode.CorrectLevel.H,
        });
        return new Promise((res) =>
          setTimeout(() => {
            const el = d.querySelector("img") || d.querySelector("canvas");
            const src = el
              ? el.tagName === "CANVAS"
                ? (el as HTMLCanvasElement).toDataURL("image/png")
                : (el as HTMLImageElement).src
              : "";
            document.body.removeChild(d);
            res({ num, src });
          }, 400)
        );
      });
      Promise.all(divs).then((qrs: any) => {
        const qrMap = Object.fromEntries(qrs.map((q: any) => [q.num, q.src]));
        const data = ((lista[0] as any)?.[1]?.data) || new Date().toLocaleDateString('pt-BR');
        const col1 = lista.filter((_, i) => i % 2 === 0);
        const col2 = lista.filter((_, i) => i % 2 !== 0);
        const nLinhas = Math.max(col1.length, col2.length);

        const linhas = Array.from({ length: nLinhas })
          .map((_, i) => {
            const celula = ([num, info]: any) => {
              if (!num) return `<td class="vazia"></td>`;
              return `<td class="cel">
              <div class="topo">
                <span class="hora">${info.hora}</span>
                <span class="num">${num}</span>
              </div>
              <div class="partes">${info.partes || ""}</div>
              <div class="qrcenter"><img src="${qrMap[num]}"/></div>
            </td>`;
            };
            return `<tr>${celula(col1[i] || [null, null])}${celula(
              col2[i] || [null, null]
            )}</tr>`;
          })
          .join("");

        const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
          *{margin:0;padding:0;box-sizing:border-box;}
          body{font-family:'Segoe UI',sans-serif;padding:8mm 10mm;}
          .cab{text-align:center;border-bottom:2px solid #1a3a6b;padding-bottom:3mm;margin-bottom:5mm;}
          .cab h1{font-size:11pt;color:#1a3a6b;font-weight:700;}
          .cab p{font-size:8.5pt;color:#555;margin-top:2px;}
          table{width:100%;border-collapse:collapse;}
          tr{vertical-align:top;}
          td.cel{width:50%;padding:4mm;border:1px solid #ddd;background:#fff;}
          td.cel:nth-child(odd){background:#f5f8fb;}
          td.vazia{width:50%;border:1px solid #eee;}
          .topo{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2mm;}
          .hora{font-family:monospace;font-weight:900;font-size:14pt;color:#1a3a6b;}
          .num{font-family:monospace;font-size:7pt;color:#aaa;}
          .partes{font-size:8pt;color:#333;font-weight:600;line-height:1.4;margin-bottom:3mm;min-height:10mm;}
          .qrcenter{text-align:center;}
          .qrcenter img{width:36mm;height:36mm;display:inline-block;}
          .rod{margin-top:4mm;font-size:7pt;color:#aaa;text-align:center;}
          @media print{body{padding:6mm 8mm;}@page{margin:0;size:A4;}}
        </style></head><body>
        <div class="cab">
          <h1>Check-in de Audiências — 3ª Vara do Trabalho de São Paulo — Zona Sul</h1>
          <p>${data} &nbsp;•&nbsp; Aponte a câmera para o QR Code e faça seu check-in</p>
        </div>
        <table><tbody>${linhas}</tbody></table>
        <div class="rod">AudiCheck — TRT 2ª Região — ${new Date().toLocaleString(
          "pt-BR"
        )}</div>
        <script>window.onload=()=>window.print();<\/script>
        </body></html>`;
        window.open(URL.createObjectURL(new Blob([html], { type: "text/html" })), "_blank");
        setGerando(false);
      });
    };
    if (!(window as any).QRCode) {
      const s = document.createElement("script");
      s.src =
        "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js";
      s.onload = carregar;
      document.head.appendChild(s);
    } else carregar();
  };
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
        padding: 16,
        fontFamily: "'Segoe UI',sans-serif",
        animation: "fadeIn .2s ease",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 16,
          padding: 26,
          maxWidth: 400,
          width: "100%",
          boxShadow: "0 16px 48px rgba(0,0,0,.3)",
          animation: "fadeInUp .25s ease",
        }}
      >
        <h3 style={{ margin: "0 0 8px", color: "#1a3a6b" }}>Folha de QR Codes</h3>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: "#666", lineHeight: 1.6 }}>
          Gera uma folha A4 com o horário e QR code de cada audiência. Imprima e afixe junto com
          a pauta.
        </p>
        <div
          style={{
            background: "#f0f4ff",
            borderRadius: 8,
            padding: "10px 14px",
            fontSize: 12,
            color: "#1a3a6b",
            marginBottom: 16,
          }}
        >
          {(Object.values(procs) as any[]).filter((i) => !i.encerrada).length} audiência(s)
          disponíveis
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onFechar}
            style={{
              flex: 1,
              background: "#eee",
              color: "#555",
              border: "none",
              borderRadius: 9,
              padding: "11px",
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Fechar
          </button>
          <button
            onClick={gerar}
            disabled={gerando}
            style={{
              flex: 2,
              background: gerando ? "#bdc3c7" : "#1a3a6b",
              color: "#fff",
              border: "none",
              borderRadius: 9,
              padding: "11px",
              fontSize: 14,
              fontWeight: 700,
              cursor: gerando ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
            }}
          >
            {gerando ? (
              <>
                <Spinner size={16} color="#fff" /> Gerando...
              </>
            ) : (
              "Gerar e imprimir"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── PAINEL DO(A) JUIZ(A) ──
function PJuiz({ parts: partsProp, procs: procsProp, onVoltar, onCarregar }: any) {
  const [parts, setParts] = useState<any[]>(partsProp || []);
  const [procs, setProcs] = useState<any>(procsProp || {});
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    const buscar = async () => {
      setCarregando(true);
      try {
        const [ps, cs] = await Promise.all([dbGetProcessos(), dbGetCheckins()]);
        if (ps) {
          const obj: any = {};
          ps.forEach((p: any) => {
            obj[p.id] = { data: p.data, hora: p.hora, partes: p.partes, tipo: p.tipo, tipoAud: p.tipo_aud, encerrada: p.encerrada };
          });
          setProcs(obj);
          }
        if (cs) setParts(cs);
      } catch (e) { console.error("[PJuiz] ERRO:", e); }
      setCarregando(false);
    };
    buscar();
    const id = setInterval(buscar, 8000);
    return () => clearInterval(id);
  }, []);

  const parseBRL = (v: string) => {
    if (!v) return 0;
    const n = parseFloat(v.replace(/[^\d,]/g, "").replace(",", "."));
    return isNaN(n) ? 0 : n;
  };
  const fmtBRL = (n: number) => n > 0 ? n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "";
  const totalCheckins = parts.length;
  const processoComProposta = Object.entries(procs)
    .filter(([, info]: any) => !info.encerrada)
    .map(([procId, info]: any) => {
      const checkins = parts.filter((p: any) => p.processo_id === procId || p.processo === procId);
      // Nome do reclamante: busca Parte Reclamante; se não tiver, usa nome da pauta; senão usa quem registrou
      const parteRec = checkins.find((p: any) => p.papel === "Parte Reclamante");
      const { reclamantes } = extrairPartesDoTexto(info?.partes || "");
      const nomeReclamante = parteRec?.nome || reclamantes[0] || null;
      const propostaRec = checkins
        .filter((p: any) => POLO_REC_PAPEIS.includes(p.papel) && p.proposta)
        .map((p: any) => {
          let valor = "";
          try { const obj = JSON.parse(p.proposta); valor = obj["_geral"] || Object.values(obj).filter(Boolean).join(" | "); }
          catch { valor = p.proposta; }
          return { nome: p.nome, valor };
        })[0] || null;
      // Para múltiplas reclamadas, agrupa propostas por reclamada
      const { reclamadas } = extrairPartesDoTexto(info?.partes || "");
      const propostasRdoPorReclamada: { reclamada: string; valor: string; valorNum: number }[] = [];
      checkins.filter((p: any) => POLO_RDO_PAPEIS.includes(p.papel) && p.proposta).forEach((p: any) => {
        try {
          const obj = JSON.parse(p.proposta);
          if (reclamadas.length > 1) {
            reclamadas.forEach((rec: string) => {
              if (obj[rec]) {
                const existing = propostasRdoPorReclamada.find(x => x.reclamada === rec);
                if (!existing) propostasRdoPorReclamada.push({ reclamada: rec, valor: String(obj[rec]), valorNum: parseBRL(String(obj[rec])) });
              }
            });
          } else {
            const val = reclamadas.length === 1
              ? (obj[reclamadas[0]] || obj["_geral"] || Object.values(obj).filter(Boolean).join(" | "))
              : (obj["_geral"] || Object.values(obj).filter(Boolean).join(" | "));
            if (val && !propostasRdoPorReclamada.length) {
              const empresa = p.empresa_representada || p.parte_representada || (reclamadas[0] || "");
              propostasRdoPorReclamada.push({ reclamada: empresa, valor: String(val), valorNum: parseBRL(String(val)) });
            }
          }
        } catch { if (p.proposta && !propostasRdoPorReclamada.length) propostasRdoPorReclamada.push({ reclamada: p.empresa_representada || "", valor: p.proposta, valorNum: parseBRL(p.proposta) }); }
      });
      const propostaRdo = propostasRdoPorReclamada.length > 0 ? propostasRdoPorReclamada : null;
      return { procId, info, propostaRec, propostaRdo, nomeReclamante };
    })
    .filter(({ propostaRec, propostaRdo }) => propostaRec || propostaRdo)
    .sort((a, b) => a.info.hora.localeCompare(b.info.hora));

  return (
    <div style={{ minHeight: "100vh", background: "#f0ecfa", fontFamily: "'Segoe UI',sans-serif" }}>
      <GlobalStyle />
      <div style={{ background: "linear-gradient(135deg,#2c1654,#4a2580)", color: "#fff", padding: "0 16px", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", boxShadow: "0 2px 12px rgba(0,0,0,.2)", minHeight: 56 }}>
        <button onClick={onVoltar} style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", borderRadius: 7, padding: "7px 12px", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>← Sair</button>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>AudiCheck — Juiz(a)</div>
          <div style={{ fontSize: 11, opacity: 0.65 }}>Propostas de acordo — 3ª VT Zona Sul</div>
        </div>
        <div style={{ background: "rgba(255,255,255,.15)", borderRadius: 20, padding: "5px 13px", fontSize: 12, fontWeight: 700 }}>
          {totalCheckins} check-in{totalCheckins !== 1 ? "s" : ""} hoje
        </div>
      </div>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 12, maxWidth: 700, margin: "0 auto" }}>
        {carregando && parts.length === 0 && (
          <div style={{ textAlign: "center", marginTop: 60 }}>
            <Spinner size={28} color="#4a2580" />
            <div style={{ marginTop: 12, color: "#aaa", fontSize: 13 }}>Carregando...</div>
          </div>
        )}
        {!carregando && processoComProposta.length === 0 && (
          <div style={{ textAlign: "center", marginTop: 60, color: "#aaa", fontSize: 14 }}>Nenhuma proposta de acordo registrada ainda.</div>
        )}
        {processoComProposta.map(({ procId, info, propostaRec, propostaRdo, nomeReclamante }) => {
          const vRec = parseBRL(propostaRec?.valor || "");
          const vRdoTotal = propostaRdo ? propostaRdo.reduce((s: number, x: any) => s + x.valorNum, 0) : 0;
          const dif = Math.abs(vRec - vRdoTotal);
          const temDif = vRec > 0 && vRdoTotal > 0;
          return (
            <div key={procId} style={{ background: "#fff", borderRadius: 12, border: "1px solid #ddd6f5", overflow: "hidden" }}>
              <div style={{ background: "linear-gradient(135deg,#2c1654,#4a2580)", color: "#fff", padding: "11px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: "monospace", fontSize: 10, opacity: 0.6, marginBottom: 2 }}>{procId}</div>
                  <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.35 }}>{info.partes || ""}</div>
                </div>
                <div style={{ fontFamily: "monospace", fontSize: 20, fontWeight: 900, flexShrink: 0, marginLeft: 12 }}>{info.hora}</div>
              </div>
              <div style={{ padding: "14px 16px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {propostaRec ? (
                  <div style={{ background: "#eaf5ef", border: "1.5px solid #27ae60", borderRadius: 10, padding: "13px 15px" }}>
                    <div style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1, color: "#1a7a3a", marginBottom: 4 }}>Reclamante</div>
                    <div style={{ fontSize: 12, color: "#555", marginBottom: 8 }}>{(nomeReclamante || propostaRec.nome)?.split(" ").map((w: string) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ")}</div>
                    <div style={{ fontSize: 24, fontWeight: 900, color: "#1a6b35", lineHeight: 1 }}>{propostaRec.valor}</div>
                  </div>
                ) : (
                  <div style={{ background: "#f7f7f7", border: "1.5px dashed #ccc", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 90 }}>
                    <span style={{ fontSize: 12, color: "#bbb", fontStyle: "italic", textAlign: "center" }}>Sem proposta<br/>do polo ativo</span>
                  </div>
                )}
                {propostaRdo && propostaRdo.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {propostaRdo.map((item: any, i: number) => (
                      <div key={i} style={{ background: "#fef5e7", border: "1.5px solid #e67e22", borderRadius: 10, padding: "11px 13px" }}>
                        <div style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1, color: "#b7770d", marginBottom: 3 }}>
                          {item.reclamada.split(" ").map((w: string) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ")}
                        </div>
                        <div style={{ fontSize: 20, fontWeight: 900, color: "#9a5f0a", lineHeight: 1 }}>{item.valor}</div>
                      </div>
                    ))}
                    {propostaRdo.length > 1 && (
                      <div style={{ background: "#fff3e0", border: "1px solid #ffb74d", borderRadius: 8, padding: "7px 11px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ fontSize: 11, color: "#e65100", fontWeight: 700, textTransform: "uppercase" }}>Total reclamado</div>
                        <div style={{ fontSize: 15, fontWeight: 900, color: "#bf360c" }}>{fmtBRL(propostaRdo.reduce((s: number, x: any) => s + x.valorNum, 0))}</div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ background: "#f7f7f7", border: "1.5px dashed #ccc", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 90 }}>
                    <span style={{ fontSize: 12, color: "#bbb", fontStyle: "italic", textAlign: "center" }}>Sem proposta<br/>do polo passivo</span>
                  </div>
                )}
              </div>
              {temDif && (
                <div style={{ margin: "0 16px 14px", background: "#ede9fe", border: "1px solid #c4b5fd", borderRadius: 8, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontSize: 11, color: "#5b21b6", fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5 }}>Diferenca entre propostas</div>
                  <div style={{ fontSize: 18, fontWeight: 900, color: "#4c1d95" }}>{fmtBRL(dif)}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── PAINEL SECRETÁRIA ──
function PSec({ parts, procs, setProcs, setParts, onVoltar, onLimpar, onEncerrar }: any) {
  const [filtro, setFiltro] = useState("");
  const [mImport, setMImport] = useState(false);
  const [mConf, setMConf] = useState(false);
  const [mEnc, setMEnc] = useState<string | null>(null);
  const [mCartazes, setMCartazes] = useState(false);
  const [mSenha, setMSenha] = useState(false);
  const [mEditar, setMEditar] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [toast, setToast] = useState<any>(null);
  const [abaAtiva, setAbaAtiva] = useState<"ativas" | "encerradas">("ativas");
  const [grupoHab, setGrupoHab] = useState(getGrupoHabilitado());
  const prev = useRef(parts.length);

  const showToast = (msg: string, tipo = "ok") => {
    setToast({ msg, tipo });
    setTimeout(() => setToast(null), 3000);
  };

    useEffect(() => {
    if (parts.length > prev.current && !document.hidden) {
      try {
        const ctx = new (
          (window as any).AudioContext || (window as any).webkitAudioContext
        )();
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.connect(g);
        g.connect(ctx.destination);
        o.frequency.value = 880;
        g.gain.setValueAtTime(0.3, ctx.currentTime);
        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
        o.start();
        o.stop(ctx.currentTime + 0.4);
      } catch (e) {}
      showToast("Novo check-in recebido!");
    }
    prev.current = parts.length;
  }, [parts.length]);

  const imp = async (txt: any) => {
    if (!txt.trim()) return;
    const n = parsePauta(txt);
    const q = Object.keys(n).length;
    if (!q) {
      showToast("Nenhum processo encontrado no texto.", "erro");
      return;
    }
    const u = { ...procs, ...n };
    await setProcs(u);
    setMImport(false);
    showToast(q + " processo(s) importado(s) com sucesso!");
  };

  const copy = (p: any, pts: any) => {
    navigator.clipboard.writeText(relatorio(p, pts, procs[p])).then(() => {
      setCopied(p);
      showToast("Relatório copiado!");
      setTimeout(() => setCopied(null), 3000);
    });
  };

  const editarProcesso = async (procId: string, dadosNovos: any) => {
    const u = { ...procs, [procId]: dadosNovos };
    await setProcs(u);
    showToast("Audiência atualizada!");
  };

  const g = parts.reduce((a: any, p: any) => {
    const pid = p.processo_id || p.processo;
    (a[pid] = a[pid] || []).push(p);
    return a;
  }, {});

  const todos = Object.entries(procs)
    .sort((a: any, b: any) => a[1].hora.localeCompare(b[1].hora))
    .filter(
      ([p, info]: any) =>
        !filtro ||
        p.toLowerCase().includes(filtro.toLowerCase()) ||
        (info.partes || "").toLowerCase().includes(filtro.toLowerCase()) ||
        (g[p] || []).some((x: any) => x.nome.toLowerCase().includes(filtro.toLowerCase()))
    );

  const ativas = todos.filter(([, i]: any) => !i.encerrada);
  const encerradas = todos.filter(([, i]: any) => i.encerrada);
  const listaExibida = abaAtiva === "ativas" ? ativas : encerradas;

  const totalCheckins = parts.length;

  return (
    <div style={{ minHeight: "100vh", background: "#eef2f7", fontFamily: "'Segoe UI',sans-serif" }}>
      <GlobalStyle />
      {toast && <Toast msg={toast.msg} tipo={toast.tipo} />}
      {mImport && <MImport onImportar={imp} onFechar={() => setMImport(false)} />}
      {mCartazes && <MCartazes procs={procs} onFechar={() => setMCartazes(false)} />}
      {mConf && (
        <MConfirmar
          titulo="Limpar tudo?"
          msg={"Remove todos os processos e check-ins.\nEsta ação não pode ser desfeita."}
          cor="#e74c3c"
          btn="Sim, limpar"
          onOk={async () => {
            await onLimpar();
            setMConf(false);
            showToast("Dados apagados com sucesso.");
          }}
          onCancel={() => setMConf(false)}
        />
      )}
      {mEnc && (
        <MConfirmar
          titulo="Encerrar audiência?"
          msg={"Processo: " + mEnc + "\n\nNovos check-ins serão bloqueados e os dados excluídos."}
          cor="#1a3a6b"
          btn="Encerrar"
          onOk={async () => {
            await onEncerrar(mEnc);
            setMEnc(null);
            showToast("Audiência encerrada.");
          }}
          onCancel={() => setMEnc(null)}
        />
      )}
      {mSenha && <MSenha onFechar={() => setMSenha(false)} />}
      {mEditar && procs[mEditar] && (
        <MEditarProcesso
          proc={mEditar}
          info={procs[mEditar]}
          onSalvar={editarProcesso}
          onFechar={() => setMEditar(null)}
        />
      )}

      {/* barra superior */}
      <div
        style={{
          background: "linear-gradient(135deg,#0d2b5e,#1a3a6b)",
          color: "#fff",
          padding: "0 16px",
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
          boxShadow: "0 2px 12px rgba(0,0,0,.2)",
          minHeight: 56,
        }}
      >
        <button
          onClick={onVoltar}
          style={{
            background: "rgba(255,255,255,.15)",
            border: "none",
            color: "#fff",
            borderRadius: 7,
            padding: "7px 12px",
            cursor: "pointer",
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          ← Sair
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>AudiCheck — Secretário(a)</div>
          <div style={{ fontSize: 11, opacity: 0.65 }}>3ª Vara do Trabalho — Zona Sul</div>
        </div>
        <button
          onClick={() => setMImport(true)}
          style={{
            background: "#27ae60",
            border: "none",
            color: "#fff",
            borderRadius: 7,
            padding: "7px 12px",
            cursor: "pointer",
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          + Importar pauta
        </button>
        <button
          onClick={() => setMCartazes(true)}
          style={{
            background: "#2471a3",
            border: "none",
            color: "#fff",
            borderRadius: 7,
            padding: "7px 12px",
            cursor: "pointer",
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          QR Codes
        </button>
        <button
          onClick={() => setMSenha(true)}
          style={{
            background: "rgba(255,255,255,.15)",
            border: "none",
            color: "#fff",
            borderRadius: 7,
            padding: "7px 12px",
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          Senha
        </button>
        <button
          onClick={() => { const novo = !grupoHab; setGrupoHab(novo); setGrupoHabilitado(novo); showToast(novo ? "Check-in em grupo habilitado." : "Check-in em grupo desabilitado."); }}
          style={{
            background: grupoHab ? "rgba(39,174,96,.35)" : "rgba(231,76,60,.35)",
            border: "none",
            color: "#fff",
            borderRadius: 7,
            padding: "7px 12px",
            cursor: "pointer",
            fontSize: 12,
            fontWeight: 600,
          }}
          title={grupoHab ? "Check-in em grupo ativo — clique para desabilitar" : "Check-in em grupo desabilitado — clique para habilitar"}
        >
          {grupoHab ? "Grupo ✓" : "Grupo ✗"}
        </button>
        <button
          onClick={() => setMConf(true)}
          style={{
            background: "rgba(231,76,60,.45)",
            border: "none",
            color: "#fff",
            borderRadius: 7,
            padding: "7px 12px",
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          Limpar
        </button>
        <div
          style={{
            background: totalCheckins > 0 ? "#27ae60" : "rgba(255,255,255,.15)",
            borderRadius: 20,
            padding: "5px 13px",
            fontSize: 12,
            fontWeight: 700,
            transition: "background .4s",
          }}
        >
          {totalCheckins} check-in{totalCheckins !== 1 ? "s" : ""}
        </div>
      </div>

      {/* estatísticas rápidas */}
      <div
        style={{
          maxWidth: 860,
          margin: "16px auto 0",
          padding: "0 14px",
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 10,
        }}
      >
        {[
          { label: "Audiências ativas", valor: ativas.length, cor: "#1a3a6b" },
          { label: "Check-ins hoje", valor: totalCheckins, cor: "#27ae60" },
          { label: "Encerradas", valor: encerradas.length, cor: "#7f8c8d" },
        ].map(({ label, valor, cor }) => (
          <div
            key={label}
            style={{
              background: "#fff",
              borderRadius: 12,
              padding: "12px 14px",
              boxShadow: "0 1px 6px rgba(0,0,0,.07)",
              borderLeft: `4px solid ${cor}`,
            }}
          >
            <div style={{ fontSize: 22, fontWeight: 900, color: cor }}>{valor}</div>
            <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* filtro + abas */}
      <div style={{ maxWidth: 860, margin: "14px auto 0", padding: "0 14px" }}>
        <input
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          placeholder="Filtrar por processo, partes ou nome do participante..."
          style={{
            width: "100%",
            padding: "11px 14px",
            border: "1.5px solid #ddd",
            borderRadius: 9,
            fontSize: 14,
            boxSizing: "border-box",
            background: "#fff",
            boxShadow: "0 1px 4px rgba(0,0,0,.05)",
          }}
        />
        {/* abas ativas / encerradas */}
        <div style={{ display: "flex", gap: 0, marginTop: 12, borderBottom: "2px solid #dce3ed" }}>
          {(["ativas", "encerradas"] as const).map((aba) => (
            <button
              key={aba}
              onClick={() => setAbaAtiva(aba)}
              style={{
                background: "none",
                border: "none",
                borderBottom:
                  abaAtiva === aba ? "3px solid #1a3a6b" : "3px solid transparent",
                color: abaAtiva === aba ? "#1a3a6b" : "#888",
                fontWeight: abaAtiva === aba ? 700 : 400,
                fontSize: 13,
                padding: "8px 16px",
                cursor: "pointer",
                marginBottom: -2,
                transition: "all .2s",
              }}
            >
              {aba === "ativas"
                ? `Ativas (${ativas.length})`
                : `Encerradas (${encerradas.length})`}
            </button>
          ))}
        </div>
      </div>

      {/* cards */}
      <div style={{ maxWidth: 860, margin: "12px auto", padding: "0 14px 28px" }}>
        {listaExibida.length === 0 && (
          <div
            style={{
              background: "#fff",
              borderRadius: 12,
              padding: 36,
              textAlign: "center",
              color: "#aaa",
              fontSize: 14,
              boxShadow: "0 1px 6px rgba(0,0,0,.06)",
            }}
          >
            {abaAtiva === "ativas"
              ? 'Nenhuma audiência ativa. Use "Importar pauta" para começar.'
              : "Nenhuma audiência encerrada ainda."}
          </div>
        )}
        {listaExibida.map(([p, info]: any) => (
          <Card
            key={p}
            proc={p}
            info={info}
            parts={g[p] || []}
            onCopy={copy}
            copied={copied}
            onEnc={setMEnc}
            onEdit={setMEditar}
          />
        ))}
      </div>
    </div>
  );
}

// ── MODAL EDITAR PROCESSO ──
function MEditarProcesso({ proc, info, onSalvar, onFechar }: any) {
  const [hora, setHora] = useState(info.hora || "");
  const [data, setData] = useState(info.data || "");
  const [partes, setPartes] = useState(info.partes || "");
  const [tipoAud, setTipoAud] = useState(info.tipoAud || "");
  const [tipo, setTipo] = useState(info.tipo || "presencial");
  const [salvando, setSalvando] = useState(false);

  const [erroHora, setErroHora] = useState("");
  const salvar = async () => {
    if (hora && !/^\d{2}:\d{2}$/.test(hora.trim())) {
      setErroHora("Formato inválido. Use HH:MM (ex: 08:20)");
      return;
    }
    setErroHora("");
    setSalvando(true);
    const ehVC = /videoconfer[eê]ncia/i.test(tipoAud);
    await onSalvar(proc, {
      ...info,
      hora,
      data,
      partes,
      tipoAud,
      tipo: ehVC ? "videoconferência" : tipo,
    });
    setSalvando(false);
    onFechar();
  };

  const inputStyle: any = {
    width: "100%", padding: "10px 12px", border: "1.5px solid #ddd",
    borderRadius: 8, fontSize: 14, boxSizing: "border-box",
    fontFamily: "'Segoe UI', sans-serif",
  };
  const labelStyle: any = {
    display: "block", fontSize: 12, fontWeight: 700, color: "#444", marginBottom: 4,
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.55)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 2000, padding: 16, fontFamily: "'Segoe UI',sans-serif",
      animation: "fadeIn .2s ease",
    }}>
      <div style={{
        background: "#fff", borderRadius: 16, padding: 24, maxWidth: 460,
        width: "100%", boxShadow: "0 16px 48px rgba(0,0,0,.3)",
        animation: "fadeInUp .25s ease", maxHeight: "90vh", overflowY: "auto",
      }}>
        <h3 style={{ margin: "0 0 4px", color: "#1a3a6b", fontSize: 17 }}>Editar audiência</h3>
        <div style={{ fontFamily: "monospace", fontSize: 11, color: "#999", marginBottom: 16 }}>{proc}</div>

        <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Horário</label>
            <input
              value={hora}
              onChange={(e) => setHora(e.target.value)}
              placeholder="08:20"
              style={{ ...inputStyle, fontFamily: "monospace", letterSpacing: 1, border: erroHora ? "2px solid #e74c3c" : undefined }}
            />
            {erroHora && <span style={{ color: "#e74c3c", fontSize: 11, marginTop: 2, display: "block" }}>{erroHora}</span>}
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Data</label>
            <input
              value={data}
              onChange={(e) => setData(e.target.value)}
              placeholder="DD/MM/AAAA"
              style={{ ...inputStyle, fontFamily: "monospace", letterSpacing: 1 }}
            />
          </div>
        </div>

        <div style={{ marginBottom: 14 }}>
          <label style={labelStyle}>Partes</label>
          <textarea
            value={partes}
            onChange={(e) => setPartes(e.target.value)}
            rows={3}
            style={{ ...inputStyle, resize: "vertical", lineHeight: 1.5 }}
          />
        </div>

        <div style={{ marginBottom: 14 }}>
          <label style={labelStyle}>Tipo de audiência (texto livre)</label>
          <input
            value={tipoAud}
            onChange={(e) => setTipoAud(e.target.value)}
            placeholder="Instrução por videoconferência"
            style={inputStyle}
          />
          <div style={{ fontSize: 11, color: "#888", marginTop: 4 }}>
            Se contiver "videoconferência", será marcada como virtual automaticamente.
          </div>
        </div>

        <div style={{ marginBottom: 18 }}>
          <label style={labelStyle}>Modalidade</label>
          <div style={{ display: "flex", gap: 8 }}>
            {[
              { value: "presencial", label: "Presencial" },
              { value: "videoconferência", label: "Videoconferência" },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTipo(opt.value)}
                style={{
                  flex: 1, padding: "10px", border: "2px solid " + (tipo === opt.value ? "#1a3a6b" : "#ddd"),
                  borderRadius: 9, background: tipo === opt.value ? "#1a3a6b" : "#f8f9fa",
                  color: tipo === opt.value ? "#fff" : "#555",
                  fontWeight: tipo === opt.value ? 700 : 400, fontSize: 13,
                  cursor: "pointer", transition: "all .15s",
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={onFechar} style={{
            flex: 1, background: "#eee", color: "#555", border: "none",
            borderRadius: 9, padding: "12px", fontSize: 14, cursor: "pointer", fontWeight: 600,
          }}>
            Cancelar
          </button>
          <button onClick={salvar} disabled={salvando} style={{
            flex: 1, background: salvando ? "#bdc3c7" : "#1a3a6b", color: "#fff",
            border: "none", borderRadius: 9, padding: "12px", fontSize: 14,
            fontWeight: 700, cursor: salvando ? "not-allowed" : "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          }}>
            {salvando ? <><Spinner size={16} color="#fff" /> Salvando...</> : "Salvar"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── TROCA DE SENHA ──
function MSenha({ onFechar }: any) {
  const [fm, setFm] = useState({ sa: "", ns: "", cf: "" });
  const [msg, setMsg] = useState<any>(null);
  const set = (k: string, v: string) => setFm((f) => ({ ...f, [k]: v }));
  const trocar = () => {
    const s = getSenhas();
    if (fm.sa !== s.secretaria) {
      setMsg({ e: true, t: "Senha atual incorreta." });
      return;
    }
    if (fm.ns.length < 6) {
      setMsg({ e: true, t: "Mínimo 6 caracteres." });
      return;
    }
    if (fm.ns !== fm.cf) {
      setMsg({ e: true, t: "Senhas não coincidem." });
      return;
    }
    save(STORAGE_SENHAS, { secretaria: fm.ns });
    setMsg({ e: false, t: "Senha alterada com sucesso!" });
    setTimeout(() => {
      setMsg(null);
      onFechar();
    }, 2000);
  };
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
        padding: 16,
        fontFamily: "'Segoe UI',sans-serif",
        animation: "fadeIn .2s ease",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 16,
          padding: 26,
          maxWidth: 360,
          width: "100%",
          boxShadow: "0 16px 48px rgba(0,0,0,.3)",
          animation: "fadeInUp .25s ease",
        }}
      >
        <h3 style={{ margin: "0 0 16px", color: "#1a3a6b" }}>Trocar Senha</h3>
        {(
          [
            ["Senha atual", "sa"],
            ["Nova senha", "ns"],
            ["Confirmar", "cf"],
          ] as [string, string][]
        ).map(([lb, k]) => (
          <div key={k} style={{ marginBottom: 12 }}>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "#444",
                marginBottom: 4,
              }}
            >
              {lb}
            </label>
            <input
              type="password"
              value={(fm as any)[k]}
              onChange={(e) => set(k, e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1.5px solid #ddd",
                borderRadius: 9,
                fontSize: 14,
                boxSizing: "border-box",
              }}
            />
          </div>
        ))}
        {msg && (
          <div
            style={{
              padding: "9px 12px",
              borderRadius: 9,
              marginBottom: 12,
              fontSize: 13,
              fontWeight: 600,
              background: msg.e ? "#fdecea" : "#e8f5e9",
              color: msg.e ? "#c62828" : "#2e7d32",
            }}
          >
            {msg.t}
          </div>
        )}
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onFechar}
            style={{
              flex: 1,
              background: "#eee",
              color: "#555",
              border: "none",
              borderRadius: 9,
              padding: "11px",
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Cancelar
          </button>
          <button
            onClick={trocar}
            style={{
              flex: 2,
              background: "#1a3a6b",
              color: "#fff",
              border: "none",
              borderRadius: 9,
              padding: "11px",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Alterar
          </button>
        </div>
      </div>
    </div>
  );
}

// ── LOGIN SECRETÁRIA ──
function Login({ onLogin, onVoltar, titulo = "Secretário(a)", cor = "#1a3a6b" }: any) {
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState(false);
  const [loading, setLoading] = useState(false);

  const try2 = () => {
    setLoading(true);
    setTimeout(() => {
      if (senha === getSenhas().secretaria) {
        onLogin();
      } else {
        setErro(true);
        setTimeout(() => setErro(false), 2500);
      }
      setLoading(false);
    }, 350); // pequeno delay para feedback visual
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(160deg,#0d2b5e,#1a5276)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        fontFamily: "'Segoe UI',sans-serif",
      }}
    >
      <GlobalStyle />
      <div
        style={{
          background: "#fff",
          borderRadius: 16,
          padding: 32,
          maxWidth: 360,
          width: "100%",
          boxShadow: "0 16px 48px rgba(0,0,0,.25)",
          animation: "fadeInUp .35s ease",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div
            style={{
              width: 52,
              height: 52,
              background: cor,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 12px",
              fontSize: 22,
            }}
          >
            🔒
          </div>
          <h2 style={{ margin: "0 0 4px", color: cor }}>{titulo}</h2>
          <p style={{ margin: 0, fontSize: 13, color: "#888" }}>AudiCheck — Acesso restrito</p>
        </div>
        <label
          style={{ fontSize: 13, fontWeight: 600, color: "#444", display: "block", marginBottom: 6 }}
        >
          Senha
        </label>
        <input
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && try2()}
          placeholder="Digite a senha"
          autoFocus
          style={{
            width: "100%",
            padding: "12px 14px",
            border: erro ? "2px solid #e74c3c" : "1.5px solid #ddd",
            borderRadius: 9,
            fontSize: 14,
            boxSizing: "border-box",
            marginBottom: 6,
            transition: "border .2s",
          }}
        />
        {erro && (
          <p style={{ color: "#e74c3c", fontSize: 12, margin: "0 0 8px", animation: "fadeIn .2s" }}>
            Senha incorreta. Tente novamente.
          </p>
        )}
        <button
          onClick={try2}
          disabled={loading || !senha}
          style={{
            width: "100%",
            background: loading || !senha ? "#bdc3c7" : cor,
            color: "#fff",
            border: "none",
            borderRadius: 9,
            padding: "13px",
            fontSize: 15,
            fontWeight: 700,
            cursor: loading || !senha ? "not-allowed" : "pointer",
            marginTop: 6,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            transition: "background .2s",
          }}
        >
          {loading ? <><Spinner size={18} color="#fff" /> Verificando...</> : "Entrar"}
        </button>
        <button
          onClick={onVoltar}
          style={{
            width: "100%",
            background: "none",
            color: "#888",
            border: "none",
            fontSize: 13,
            marginTop: 12,
            cursor: "pointer",
          }}
        >
          Voltar
        </button>
      </div>
    </div>
  );
}

// ── LGPD ──
function LGPD({ onAc, onRec, onVoltar }: any) {
  const [lido, setLido] = useState(false);
  const [ac, setAc] = useState(false);
  const ref = useRef<any>();
    useEffect(() => {
    const el = ref.current;
    if (el && el.scrollHeight <= el.clientHeight + 10) setLido(true);
  }, []);
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(160deg,#0d2b5e,#1a5276,#2980b9)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px 16px",
        fontFamily: "'Segoe UI',sans-serif",
      }}
    >
      <GlobalStyle />
      <div style={{ width: "100%", maxWidth: 480, marginBottom: 12, display: "flex", alignItems: "center", gap: 10 }}>
        <button
          onClick={onVoltar}
          style={{
            background: "rgba(255,255,255,.2)",
            border: "none",
            color: "#fff",
            borderRadius: 7,
            padding: "7px 14px",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          ← Voltar
        </button>
        <div style={{ color: "#fff", fontWeight: 700, fontSize: 15 }}>
          Privacidade e Proteção de Dados
        </div>
      </div>
      <div
        style={{
          width: "100%",
          maxWidth: 480,
          background: "#fff",
          borderRadius: 16,
          padding: 20,
          boxShadow: "0 8px 32px rgba(0,0,0,.2)",
          animation: "fadeInUp .35s ease",
        }}
      >
        <div
          ref={ref}
          onScroll={() => {
            const el = ref.current;
            if (el && el.scrollTop + el.clientHeight >= el.scrollHeight - 10) setLido(true);
          }}
          style={{
            height: 200,
            overflowY: "scroll",
            background: "#f8f9fa",
            border: "1.5px solid #ddd",
            borderRadius: 10,
            padding: 14,
            fontSize: 13,
            lineHeight: 1.8,
            color: "#333",
            marginBottom: 12,
          }}
        >
          <p style={{ margin: "0 0 8px", fontWeight: 700, color: "#1a3a6b" }}>
            AVISO LEGAL E PRIVACIDADE — AUDICHECK
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>1. O que é o AudiCheck</strong>
            <br />O AudiCheck é um aplicativo web independente desenvolvido por Andrei Boareto
            Coimbra, Analista Judiciário do TRT da 2ª Região. Este aplicativo não pertence ao PJe,
            não o compõe de qualquer forma e não é um sistema oficial do Tribunal Regional do
            Trabalho da 2ª Região. O AudiCheck está atualmente em fase de testes e seu uso é
            restrito, por ora, à 3ª Vara do Trabalho da Zona Sul de São Paulo. Qualquer utilização
            fora desse contexto é de responsabilidade exclusiva do usuário.
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>2. Finalidade</strong>
            <br />O AudiCheck tem por finalidade exclusiva o pré-registro de dados de participantes
            de audiências trabalhistas, visando agilizar a confecção da ata no sistema AUD. A
            presença oficial é confirmada pelo(a) juiz(a) durante a sessão.
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>3. Dados coletados</strong>
            <br />
            Para seu funcionamento, o aplicativo coleta: nome completo; CPF (somente testemunhas);
            endereço residencial (somente testemunhas); número de inscrição na OAB (somente
            advogado(a)s); localização geográfica (somente para confirmar presença física no fórum); e
            horário do check-in.
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>4. Base legal (LGPD — Lei nº 13.709/2018)</strong>
            <br />A coleta é fundamentada no art. 7º, II e III da LGPD e nos arts. 813 a 817 da
            CLT, sendo estritamente necessária para a finalidade descrita.
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>5. Armazenamento e segurança</strong>
            <br />
            Os dados são armazenados temporariamente em servidor na nuvem localizado no Brasil (São
            Paulo) e excluídos ao encerramento de cada audiência ou ao fim do dia.
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>6. Compartilhamento e acesso de terceiros</strong>
            <br />
            Os dados não são compartilhados com terceiros, exceto por determinação judicial. O
            aplicativo não coleta dados para outros fins, nem permite ou facilita qualquer tipo de
            acesso de terceiros a esses dados. Contudo, vulnerabilidades hipotéticas no dispositivo,
            sistema operacional ou navegador poderiam permitir que os dados escapassem de seu
            escopo. Recomenda-se o uso em ambiente seguro, com antivírus e firewall atualizados.
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>7. Uso</strong>
            <br />O uso deste aplicativo é gratuito e voluntário, permitido para os fins a que se
            destina. O software é fornecido no estado em que se encontra, sem qualquer tipo de
            garantia expressa ou implícita.
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>8. Seus direitos</strong>
            <br />
            Nos termos do art. 18 da LGPD, você tem direito de acesso, correção e eliminação dos
            seus dados. Contato: a169013@trt2.jus.br
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>9. Responsabilidade</strong>
            <br />
            Em nenhuma hipótese, o desenvolvedor será responsável, sob qualquer teoria de
            responsabilidade, por quaisquer danos diretos, indiretos, incidentais, especiais,
            exemplares ou consequenciais, eventualmente causados, decorrentes de qualquer forma do
            uso deste software, mesmo se avisado da possibilidade.
          </p>
          <p style={{ margin: "0 0 7px" }}>
            <strong>10. Aceite</strong>
            <br />
            Caso não concorde, não prossiga com o check-in e dirija-se à Secretaria da Vara para
            identificação presencial.
          </p>
          <p style={{ margin: 0, color: "#aaa", fontSize: 11 }}>Role até o final para continuar</p>
        </div>
        {!lido && (
          <div
            style={{
              background: "#fff8e1",
              border: "1px solid #ffe082",
              borderRadius: 8,
              padding: 9,
              fontSize: 12,
              color: "#7b5e00",
              marginBottom: 11,
              textAlign: "center",
            }}
          >
            ↕ Role o texto até o final para habilitar o aceite
          </div>
        )}
        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
            cursor: lido ? "pointer" : "not-allowed",
            opacity: lido ? 1 : 0.5,
            marginBottom: 13,
            fontSize: 13,
            color: "#333",
            lineHeight: 1.5,
          }}
        >
          <input
            type="checkbox"
            checked={ac}
            onChange={(e) => lido && setAc(e.target.checked)}
            disabled={!lido}
            style={{ marginTop: 3, width: 16, height: 16, flexShrink: 0 }}
          />
          <span>
            Li e concordo com o pré-registro dos meus dados para agilizar a ata da audiência
            trabalhista.
          </span>
        </label>
        <button
          onClick={onAc}
          disabled={!ac}
          style={{
            width: "100%",
            background: ac ? "#27ae60" : "#bdc3c7",
            color: "#fff",
            border: "none",
            borderRadius: 9,
            padding: "13px",
            fontSize: 15,
            fontWeight: 700,
            cursor: ac ? "pointer" : "not-allowed",
            marginBottom: 9,
            transition: "background .3s",
          }}
        >
          Aceitar e continuar
        </button>
        <button
          onClick={onRec}
          style={{
            width: "100%",
            background: "#fff",
            color: "#e74c3c",
            border: "1.5px solid #e74c3c",
            borderRadius: 9,
            padding: "10px",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Recusar e sair
        </button>
      </div>
    </div>
  );
}

// ── GPS ──
function GPS({ info, onOk, onVoltar, jaValidou }: any) {
  const [st, setSt] = useState(jaValidou ? "ok" : "idle");
  const [msg, setMsg] = useState(jaValidou ? "Localização já confirmada." : "");
  const virt = info?.tipo === "videoconferência";

  const onOkRef = useRef(onOk);
  useEffect(() => { onOkRef.current = onOk; });
  useEffect(() => {
    if (virt) onOkRef.current();
  }, [virt]);
  if (virt) return null;

  const ver = () => {
    setSt("car");
    if (!navigator.geolocation) {
      setSt("err");
      setMsg("GPS não disponível neste dispositivo.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const d = dist(
          pos.coords.latitude,
          pos.coords.longitude,
          info.forumLat,
          info.forumLng
        );
        if (d <= RAIO_METROS) {
          setSt("ok");
          setMsg("Você está no fórum (" + Math.round(d) + "m).");
        } else {
          setSt("err");
          setMsg(
            "Você está a " + Math.round(d) + "m do fórum (máximo: " + RAIO_METROS + "m). Tente ir para uma área aberta ou próxima à entrada do edifício e tente novamente."
          );
        }
      },
      () => {
        setSt("err");
        setMsg("Não foi possível obter sua localização. Verifique se o GPS está ligado no celular e se o navegador tem permissão para acessar a localização.");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(160deg,#0d2b5e,#1a5276)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px 16px",
        fontFamily: "'Segoe UI',sans-serif",
      }}
    >
      <GlobalStyle />
      <div
        style={{
          width: "100%",
          maxWidth: 440,
          marginBottom: 14,
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <button
          onClick={onVoltar}
          style={{
            background: "rgba(255,255,255,.2)",
            border: "none",
            color: "#fff",
            borderRadius: 7,
            padding: "7px 14px",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          ← Voltar
        </button>
        <div style={{ color: "#fff" }}>
          <div style={{ fontWeight: 700 }}>Confirmar presença</div>
          <div style={{ fontSize: 11, opacity: 0.8 }}>{info?.hora}</div>
        </div>
      </div>
      <div
        style={{
          width: "100%",
          maxWidth: 440,
          background: "#fff",
          borderRadius: 16,
          padding: 22,
          boxShadow: "0 8px 32px rgba(0,0,0,.2)",
          animation: "fadeInUp .35s ease",
        }}
      >
        <p style={{ fontSize: 14, color: "#555", margin: "0 0 16px", lineHeight: 1.6 }}>
          Para continuar, precisamos confirmar que você está fisicamente no fórum. Certifique-se de que o <strong>GPS do celular está ligado</strong> antes de verificar.
        </p>
        <div
          style={{
            background: "#f0f4f8",
            borderRadius: 10,
            padding: 13,
            marginBottom: 16,
            fontSize: 13,
            color: "#555",
          }}
        >
          <div style={{ fontWeight: 700, color: "#1a3a6b", marginBottom: 2 }}>{FORUM.nome}</div>
          <div>{FORUM.endereco}</div>
          <div style={{ marginTop: 3, fontSize: 12, color: "#888" }}>
            Raio permitido: {RAIO_METROS} metros
          </div>
        </div>
        {st === "idle" && (
          <button
            onClick={ver}
            style={{
              width: "100%",
              background: "#1a3a6b",
              color: "#fff",
              border: "none",
              borderRadius: 9,
              padding: "14px",
              fontSize: 15,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            📍 Verificar minha localização
          </button>
        )}
        {st === "car" && (
          <div
            style={{
              textAlign: "center",
              padding: 18,
              color: "#1a3a6b",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
            }}
          >
            <Spinner /> Verificando localização...
          </div>
        )}
        {(st === "ok" || st === "err") && (
          <div>
            <div
              style={{
                background: st === "ok" ? "#e8f5e9" : "#fdecea",
                border: "1px solid " + (st === "ok" ? "#a5d6a7" : "#f5c6cb"),
                borderRadius: 10,
                padding: 14,
                marginBottom: 12,
                fontSize: 14,
                color: st === "ok" ? "#2e7d32" : "#c62828",
                textAlign: "center",
                fontWeight: 600,
                animation: "fadeInUp .25s ease",
              }}
            >
              {st === "ok" ? "✓ Presença confirmada" : "⚠ Fora do raio permitido"}
              <br />
              <span style={{ fontWeight: 400, fontSize: 13 }}>{msg}</span>
            </div>
            {st === "err" && (
              <button
                onClick={() => {
                  setSt("idle");
                  setMsg("");
                }}
                style={{
                  width: "100%",
                  background: "#ecf0f1",
                  color: "#555",
                  border: "none",
                  borderRadius: 9,
                  padding: "11px",
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Tentar novamente
              </button>
            )}
          </div>
        )}
        {st === "ok" && (
          <button
            onClick={onOk}
            style={{
              width: "100%",
              background: "#27ae60",
              color: "#fff",
              border: "none",
              borderRadius: 9,
              padding: "14px",
              fontSize: 15,
              fontWeight: 700,
              cursor: "pointer",
              marginTop: 6,
              animation: "fadeInUp .3s ease",
            }}
          >
            Preencher dados →
          </button>
        )}
      </div>
    </div>
  );
}

// ── SELEÇÃO MÚLTIPLA DE RECLAMADAS ──
function BotoesMultiSelecao({ opcoes, valores, onToggle, erro, cor }: any) {
  const selecionados = (valores || "").split(" | ").filter(Boolean);
  const temOutro = selecionados.some((s: string) => !opcoes.includes(s));
  const [mostraOutro, setMostraOutro] = useState(temOutro);
  const [textoOutro, setTextoOutro] = useState(temOutro ? selecionados.filter((s: string) => !opcoes.includes(s)).join(", ") : "");
  const corAtiva = cor || "#1a3a6b";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 7, marginBottom: erro ? 4 : 0 }}>
      <div style={{ fontSize: 11, color: "#888", marginBottom: -2 }}>Selecione uma ou mais:</div>
      {opcoes.map((op: string) => {
        const ativo = selecionados.includes(op);
        return (
          <button key={op} onClick={() => onToggle(op)} type="button"
            style={{
              padding: "11px 14px", border: "2px solid " + (ativo ? corAtiva : "#e8eaed"),
              borderRadius: 9, background: ativo ? corAtiva : "#f8f9fa",
              color: ativo ? "#fff" : "#333", fontSize: 13,
              fontWeight: ativo ? 700 : 400, cursor: "pointer", textAlign: "left",
              lineHeight: 1.4, transition: "all .15s",
              display: "flex", alignItems: "center", gap: 8,
            }}>
            <span style={{
              width: 18, height: 18, borderRadius: 4, border: "2px solid " + (ativo ? "rgba(255,255,255,.6)" : "#ccc"),
              background: ativo ? "rgba(255,255,255,.2)" : "#fff",
              display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 12, flexShrink: 0,
            }}>{ativo ? "✓" : ""}</span>
            {op}
          </button>
        );
      })}
      <button onClick={() => setMostraOutro(!mostraOutro)} type="button"
        style={{
          padding: "9px 14px", border: "2px solid " + (mostraOutro ? corAtiva : "#e8eaed"),
          borderRadius: 9, background: mostraOutro ? "#f0f4ff" : "#f8f9fa",
          color: corAtiva, fontSize: 12, fontWeight: 400, cursor: "pointer", textAlign: "left",
        }}>
        ✏️ Outro / digitar manualmente
      </button>
      {mostraOutro && (
        <input value={textoOutro}
          onChange={(e) => { setTextoOutro(e.target.value); onToggle("__outro__:" + e.target.value); }}
          placeholder="Digite o(s) nome(s)..."
          autoFocus
          style={{ padding: "10px 12px", border: "1.5px solid " + corAtiva, borderRadius: 8, fontSize: 13, boxSizing: "border-box" as any, width: "100%" }}
        />
      )}
      {selecionados.length > 1 && (
        <div style={{ fontSize: 11, color: corAtiva, background: corAtiva + "10", borderRadius: 6, padding: "5px 9px" }}>
          {selecionados.length} reclamadas selecionadas
        </div>
      )}
      {erro && <span style={{ color: "#e74c3c", fontSize: 12 }}>{erro}</span>}
    </div>
  );
}

// ── SELEÇÃO MÚLTIPLA DE PENDÊNCIAS DE REGULARIZAÇÃO ──
function CheckboxesRegularizacao({ valor, onChange }: any) {
  const opcoesPadrao = ["Substabelecimento", "Procuração", "Carta de preposição"];
  const selecionados = (valor || "").split(" | ").filter(Boolean);
  const outroTexto = selecionados.filter((s: string) => !opcoesPadrao.includes(s)).join(", ");
  const [outro, setOutro] = useState(outroTexto);

  const toggle = (p: string) => {
    const novo = selecionados.includes(p) ? selecionados.filter((s: string) => s !== p) : [...selecionados, p];
    onChange(novo.join(" | "));
  };

  const handleOutro = (v: string) => {
    setOutro(v);
    const base = selecionados.filter((s: string) => opcoesPadrao.includes(s));
    onChange([...base, ...(v.trim() ? [v.trim()] : [])].join(" | "));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
      {opcoesPadrao.map((p) => {
        const ativo = selecionados.includes(p);
        return (
          <button key={p} onClick={() => toggle(p)} type="button"
            style={{
              padding: "10px 14px", border: "2px solid " + (ativo ? "#e67e22" : "#e8eaed"),
              borderRadius: 9, background: ativo ? "#fef5e7" : "#f8f9fa",
              color: ativo ? "#856404" : "#555", fontSize: 13,
              fontWeight: ativo ? 700 : 400, cursor: "pointer", textAlign: "left",
              transition: "all .15s", display: "flex", alignItems: "center", gap: 8,
            }}>
            <span style={{
              width: 18, height: 18, borderRadius: 4, border: "2px solid " + (ativo ? "#e67e22" : "#ccc"),
              background: ativo ? "#e67e22" : "#fff", color: "#fff",
              display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 12, flexShrink: 0,
            }}>{ativo ? "✓" : ""}</span>
            {p}
          </button>
        );
      })}
      <input
        value={outro}
        onChange={(e) => handleOutro(e.target.value)}
        placeholder="Outro prazo... (opcional)"
        style={{ padding: "10px 12px", border: "1.5px solid #e8eaed", borderRadius: 9, fontSize: 13, boxSizing: "border-box" as any, width: "100%", color: "#555" }}
      />
      {selecionados.length > 0 && (
        <div style={{ marginTop: 2, background: "#fff3cd", borderRadius: 6, padding: "5px 9px", fontSize: 11, color: "#856404" }}>
          {selecionados.length === 1 ? "1 pendência selecionada" : selecionados.length + " pendências selecionadas"} — será destacado no relatório AUD.
        </div>
      )}
    </div>
  );
}

// ── MÁSCARA MONETÁRIA ──
const fMoeda = (v: string): string => {
  const nums = v.replace(/\D/g, "");
  if (!nums || nums === "0") return "";
  const n = parseInt(nums, 10);
  if (n === 0) return "";
  return "R$ " + (n / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// ── FORMULÁRIO INDIVIDUAL ──
function FormIndividual({ papel, info, processo, onVoltar, onSubmit, cpfsUsados, partesDoProcesso, onIrGrupo, dadosParaGrupo }: any) {
  const [fm, setFm] = useState<any>({
    nome: "", cpf: "", oab: "", cep: "", endereco: "", numero: "", complemento: "",
    reg: "", parteRepresentada: "", empresaRepresentada: "", subtipo_representante: "", parteOuvinte: "", proposta: "",
  });
  const [errs, setErrs] = useState<any>({});
  const [bCEP, setBCEP] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const set = (k: string, v: string) => setFm((f: any) => ({ ...f, [k]: v }));

  const isAdv = papel.includes("Advogado(a)");
  const isTest = papel.includes("Testemunha");
  const isParte = ["Parte Reclamante", "Parte Reclamada", "Representante do(a) Reclamado(a)"].includes(papel);
  const ehParteRec = papel === "Parte Reclamante";
  const ehParteRdo = papel === "Parte Reclamada";
  const ehRep = papel === "Representante do(a) Reclamado(a)";
  const ehTestRec = papel === "Testemunha do(a) Reclamante";
  const ehTestRdo = papel === "Testemunha do(a) Reclamado(a)";
  const ehAdvRec = papel === "Advogado(a) do(a) Reclamante";
  const ehAdvRdo = papel === "Advogado(a) do(a) Reclamado(a)";

  const { reclamantes, reclamadas } = extrairPartesDoTexto(info?.partes || "");
  const opcoesRec = reclamantes;
  const opcoesRdo = reclamadas;
  const temOpcoesRec = opcoesRec.length > 0;
  const temOpcoesRdo = opcoesRdo.length > 0;

  const buscarCEP = async (c: string) => {
    const n = c.replace(/\D/g, "");
    if (n.length !== 8) return;
    setBCEP(true);
    try {
      const r = await fetch("https://viacep.com.br/ws/" + n + "/json/");
      const d = await r.json();
      if (!d.erro)
        set(
          "endereco",
          (d.logradouro || "") +
            (d.bairro ? ", " + d.bairro : "") +
            (d.localidade ? ", " + d.localidade : "") +
            (d.uf ? " - " + d.uf : "")
        );
    } catch (e) {}
    setBCEP(false);
  };

  const validar = () => {
    const e: any = {};
    const nomeAutoPreenchido = (!fm.ehRepPJ && ehParteRec && opcoesRec.length === 1) || (ehParteRdo && opcoesRdo.length === 1);
    if (!fm.nome.trim() && !nomeAutoPreenchido) e.nome = "Nome obrigatório";
    if (isAdv && !fm.oab.trim()) e.oab = "OAB obrigatória";
    if (isAdv && fm.oab.trim()) { const oabErr = validOAB(fm.oab); if (oabErr) e.oab = oabErr; }
    if (ehAdvRec && opcoesRec.length !== 1 && !(fm.parteRepresentada || "").trim()) e.parteRepresentada = "Selecione ao menos uma parte que representa";
    if (ehAdvRdo && opcoesRdo.length !== 1 && !fm.empresaRepresentada.trim()) e.empresaRepresentada = "Selecione a parte que representa";
    if (ehRep) {
      const selecionadas = (fm.empresaRepresentada || "").split(" | ").filter(Boolean);
      if (opcoesRdo.length > 1 && selecionadas.length > 0) {
        // subtipo é JSON por reclamada
        const subtipos = (() => { try { return JSON.parse(fm.subtipo_representante || "{}"); } catch { return {}; } })();
        const faltando = selecionadas.some((r: string) => !subtipos[r]);
        if (faltando) e.subtipo_representante = "Selecione o tipo para cada reclamada";
      } else if (!fm.subtipo_representante.trim() || fm.subtipo_representante.startsWith("{")) {
        if (opcoesRdo.length <= 1) e.subtipo_representante = "Selecione uma opção";
      }
    }
    if (isTest) {
      if (fm.cpf.replace(/\D/g, "").length < 11) e.cpf = "CPF inválido";
      else if (!validCPF(fm.cpf)) e.cpf = "CPF inválido (dígitos verificadores incorretos)";
      else if (cpfsUsados.includes(fm.cpf.replace(/\D/g, "")))
        e.cpf = "CPF já registrado neste processo";
      if (!fm.endereco.trim()) e.endereco = "Endereço obrigatório";
      if (!fm.numero.trim()) e.numero = "Número obrigatório";
      if (fm.cep.replace(/\D/g, "").length < 8) e.cep = "CEP inválido";
    }
    setErrs(e);
    return !Object.keys(e).length;
  };

  const handleSubmit = async () => {
    if (!validar()) return;
    setEnviando(true);
    // Resolve subtipo: se é JSON (múltiplas reclamadas), transforma em texto "Sócio(a) [Rec A] / Preposto(a) [Rec B]"
    const resolveSubtipo = () => {
      if (!fm.subtipo_representante) return undefined;
      try {
        const obj = JSON.parse(fm.subtipo_representante);
        if (typeof obj === "object" && obj !== null) {
          const entries = Object.entries(obj);
          if (entries.length === 0) return undefined;
          // Se todos iguais, retorna só o tipo
          const tipos = [...new Set(entries.map(([, v]) => v as string))];
          if (tipos.length === 1) return tipos[0];
          // Diferentes: "Sócio(a) (Rec A) / Preposto(a) (Rec B)"
          return entries.map(([rec, tipo]) => `${tipo} (${rec})`).join(" / ");
        }
      } catch {}
      return fm.subtipo_representante || undefined;
    };
    const parteRepresentadaFinal = (ehAdvRec && opcoesRec.length === 1 && !fm.parteRepresentada) ? opcoesRec[0] : fm.parteRepresentada;
    const empresaRepresentadaFinal = ((ehAdvRdo || ehRep) && opcoesRdo.length === 1 && !fm.empresaRepresentada) ? opcoesRdo[0] : fm.empresaRepresentada;
    const parteOuvinteFinal = (ehTestRec && opcoesRec.length === 1 && !fm.parteOuvinte) ? opcoesRec[0]
      : (ehTestRdo && opcoesRdo.length === 1 && !fm.parteOuvinte) ? opcoesRdo[0]
      : fm.parteOuvinte;
    const nomeFinal = (!fm.nome.trim() && !fm.ehRepPJ && ehParteRec && opcoesRec.length === 1) ? opcoesRec[0]
      : (!fm.nome.trim() && ehParteRdo && opcoesRdo.length === 1) ? opcoesRdo[0]
      : fm.nome;
    await onSubmit(
      { ...fm, nome: nomeFinal, papel: fm.ehRepPJ ? "Representante do(a) Reclamante" : papel,
        regularizacao: fm.reg, processo, hora: now(),
        modalidade: info?.tipo === "videoconferência" ? "virtual" : "presencial",
        subtipo_representante: resolveSubtipo(),
        parteRepresentada: parteRepresentadaFinal,
        empresaRepresentada: empresaRepresentadaFinal,
        parteOuvinte: parteOuvinteFinal || undefined,
        proposta: (() => {
          if (!fm.proposta) return undefined;
          // Se for JSON, só salva se tiver ao menos um valor não-vazio
          try {
            const obj = JSON.parse(fm.proposta);
            const temValor = Object.values(obj).some((v: any) => v && String(v).trim());
            return temValor ? fm.proposta : undefined;
          } catch {}
          return fm.proposta.trim() ? fm.proposta : undefined;
        })() },
      false, false
    );
    setEnviando(false);
  };

  const BotoesSelecao = ({ opcoes, valor, onSelect, erro }: any) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 7, marginBottom: erro ? 4 : 0 }}>
      {opcoes.map((op: string) => (
        <button
          key={op}
          onClick={() => onSelect(op)}
          style={{
            padding: "11px 14px",
            border: "2px solid " + (valor === op ? "#1a3a6b" : "#e8eaed"),
            borderRadius: 9,
            background: valor === op ? "#1a3a6b" : "#f8f9fa",
            color: valor === op ? "#fff" : "#333",
            fontSize: 13,
            fontWeight: valor === op ? 700 : 400,
            cursor: "pointer",
            textAlign: "left",
            lineHeight: 1.4,
            transition: "all .15s",
          }}
        >
          {op}
        </button>
      ))}
      <button
        onClick={() => onSelect("__outro__")}
        style={{
          padding: "9px 14px",
          border: "2px solid " + (valor === "__outro__" || (!opcoes.includes(valor) && valor !== "") ? "#1a3a6b" : "#e8eaed"),
          borderRadius: 9,
          background: valor === "__outro__" || (!opcoes.includes(valor) && valor !== "") ? "#f0f4ff" : "#f8f9fa",
          color: "#1a3a6b",
          fontSize: 12,
          fontWeight: 400,
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        ✏️ Outro / digitar manualmente
      </button>
      {(valor === "__outro__" || (!opcoes.includes(valor) && valor !== "")) && (
        <input
          value={valor === "__outro__" ? "" : valor}
          onChange={(e) => onSelect(e.target.value)}
          placeholder="Digite o nome..."
          autoFocus
          style={{
            padding: "10px 12px",
            border: "1.5px solid #1a3a6b",
            borderRadius: 8,
            fontSize: 13,
            boxSizing: "border-box" as any,
            width: "100%",
          }}
        />
      )}
      {erro && <span style={{ color: "#e74c3c", fontSize: 12 }}>{erro}</span>}
    </div>
  );

  const inputStyle = (hasErr: boolean) => ({
    width: "100%",
    padding: "11px 12px",
    border: hasErr ? "2px solid #e74c3c" : "1.5px solid #ddd",
    borderRadius: 9,
    fontSize: 14,
    boxSizing: "border-box" as any,
    transition: "border .2s",
  });

  return (
    <div style={{ width: "100%" }}>
      <div
        style={{
          display: "inline-block",
          background: "#1a3a6b",
          color: "#fff",
          borderRadius: 20,
          padding: "3px 14px",
          fontSize: 12,
          marginBottom: 10,
          fontWeight: 600,
        }}
      >
        {papel}
      </div>
      <div style={{ background: "#fff8e1", border: "1px solid #ffe082", borderRadius: 8, padding: "8px 12px", fontSize: 12, color: "#856404", marginBottom: 16, lineHeight: 1.5 }}>
        🔒 Seus dados são usados apenas para agilizar a ata. A presença oficial é confirmada pelo(a) Juiz(a).
      </div>

      {isAdv && (
        <>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
              Nome completo *
            </label>
            <input value={fm.nome} onChange={(e) => set("nome", e.target.value)}
              placeholder="Como consta na OAB" style={inputStyle(!!errs.nome)} />
            {errs.nome && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.nome}</span>}
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
              Número OAB *
            </label>
            <div style={{ position: "relative" }}>
              <input value={fm.oab} onChange={(e) => { set("oab", fOAB(e.target.value)); }}
                placeholder="Ex: SP123456" style={{ ...inputStyle(!!errs.oab), paddingRight: 36 }} />
              {fm.oab && !validOAB(fm.oab) && (
                <span style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", fontSize: 16, color: "#27ae60" }}>✓</span>
              )}
            </div>
            {errs.oab && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.oab}</span>}
            {fm.oab && !errs.oab && !validOAB(fm.oab) && <span style={{ color: "#27ae60", fontSize: 12 }}>✓ OAB válida</span>}
          </div>

          {ehAdvRec && (
            <div style={{ marginBottom: 12 }}>
              {opcoesRec.length === 1 ? (
                <div style={{ background: "#f0f4ff", border: "1px solid #c7d2fe", borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "#1a3a6b" }}>
                  Representando: <strong>{opcoesRec[0]}</strong>
                </div>
              ) : (
                <>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 6 }}>
                    Clique na(s) parte(s) que você representa *
                  </label>
                  {temOpcoesRec ? (
                    <BotoesMultiSelecao opcoes={opcoesRec} valores={fm.parteRepresentada}
                      onToggle={(v: string) => {
                        if (v.startsWith("__outro__:")) {
                          const txt = v.slice(10);
                          const daLista = (fm.parteRepresentada || "").split(" | ").filter((s: string) => opcoesRec.includes(s));
                          set("parteRepresentada", [...daLista, ...(txt ? [txt] : [])].join(" | "));
                        } else {
                          const atuais = (fm.parteRepresentada || "").split(" | ").filter(Boolean);
                          const novo = atuais.includes(v) ? atuais.filter((s: string) => s !== v) : [...atuais, v];
                          set("parteRepresentada", novo.join(" | "));
                        }
                      }}
                      erro={errs.parteRepresentada} cor={COR_REC} />
                  ) : (
                    <input value={fm.parteRepresentada} onChange={(e) => set("parteRepresentada", e.target.value)}
                      placeholder="Nome do(a) reclamante" style={inputStyle(!!errs.parteRepresentada)} />
                  )}
                  {errs.parteRepresentada && !temOpcoesRec && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.parteRepresentada}</span>}
                </>
              )}
            </div>
          )}

          {ehAdvRdo && (
            <div style={{ marginBottom: 12 }}>
              {opcoesRdo.length === 1 ? (
                <div style={{ background: "#fff8f2", border: "1px solid #fdba74", borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "#92400e" }}>
                  Representando: <strong>{opcoesRdo[0]}</strong>
                </div>
              ) : (
                <>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 6 }}>
                    Clique na(s) parte(s) que você representa *
                  </label>
                  {temOpcoesRdo ? (
                    <BotoesMultiSelecao opcoes={opcoesRdo} valores={fm.empresaRepresentada}
                      onToggle={(v: string) => {
                        if (v.startsWith("__outro__:")) {
                          const txt = v.slice(10);
                          const daLista = (fm.empresaRepresentada || "").split(" | ").filter((s: string) => opcoesRdo.includes(s));
                          set("empresaRepresentada", [...daLista, ...(txt ? [txt] : [])].join(" | "));
                        } else {
                          const atuais = (fm.empresaRepresentada || "").split(" | ").filter(Boolean);
                          const novo = atuais.includes(v) ? atuais.filter((s: string) => s !== v) : [...atuais, v];
                          set("empresaRepresentada", novo.join(" | "));
                        }
                      }}
                      erro={errs.empresaRepresentada} cor="#e67e22" />
                  ) : (
                    <input value={fm.empresaRepresentada} onChange={(e) => set("empresaRepresentada", e.target.value)}
                      placeholder="Nome da pessoa ou empresa" style={inputStyle(!!errs.empresaRepresentada)} />
                  )}
                  {errs.empresaRepresentada && !temOpcoesRdo && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.empresaRepresentada}</span>}
                </>
              )}
            </div>
          )}

          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
              Regularização processual{" "}
              <span style={{ fontWeight: 400, color: "#aaa", fontSize: 11 }}>(opcional) — precisa de prazo?</span>
            </label>
            <CheckboxesRegularizacao valor={fm.reg} onChange={(v: string) => set("reg", v)} />
          </div>

          {/* Proposta de acordo */}
          <div style={{ marginBottom: 14, background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: 10, padding: "12px 14px" }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#0369a1", marginBottom: 8 }}>
              💰 Tem proposta de acordo? <span style={{ fontWeight: 400, color: "#0369a1", fontSize: 11 }}>(opcional — só o Juiz(a) e o(a) Secretário(a) verão antes da audiência)</span>
            </label>
            {ehAdvRec ? (
              <input value={fm.proposta} onChange={(e) => set("proposta", fMoeda(e.target.value))}
                placeholder="R$ 0,00"
                inputMode="numeric"
                style={{ width: "100%", padding: "10px 12px", border: "1.5px solid #bae6fd", borderRadius: 8, fontSize: 13, boxSizing: "border-box" as any, background: "#fff" }} />
            ) : (
              /* Advogado do reclamado: proposta por reclamada */
              (() => {
                const selecionadas = (fm.empresaRepresentada || "").split(" | ").filter(Boolean);
                const propostas = (() => { try { return JSON.parse(fm.proposta || "{}"); } catch { return {}; } })();
                if (selecionadas.length === 0) return (
                  <input value={propostas["_geral"] || ""}
                    onChange={(e) => { const p = { ...propostas, _geral: fMoeda(e.target.value) }; set("proposta", JSON.stringify(p)); }}
                    placeholder="R$ 0,00"
                    inputMode="numeric"
                    style={{ width: "100%", padding: "10px 12px", border: "1.5px solid #bae6fd", borderRadius: 8, fontSize: 13, boxSizing: "border-box" as any, background: "#fff" }} />
                );
                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {selecionadas.map((rec: string) => (
                      <div key={rec}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: "#e67e22", marginBottom: 3, textTransform: "uppercase" }}>{rec}</div>
                        <input value={propostas[rec] || ""}
                          onChange={(e) => { const p = { ...propostas, [rec]: fMoeda(e.target.value) }; set("proposta", JSON.stringify(p)); }}
                          placeholder="R$ 0,00"
                          inputMode="numeric"
                          style={{ width: "100%", padding: "10px 12px", border: "1.5px solid #bae6fd", borderRadius: 8, fontSize: 13, boxSizing: "border-box" as any, background: "#fff" }} />
                      </div>
                    ))}
                  </div>
                );
              })()
            )}
          </div>
        </>
      )}

      {isParte && (
        <div style={{ marginBottom: 12 }}>
          {/* Reclamante: botões da pauta + opção PJ */}
          {ehParteRec && (
            <>
              {temOpcoesRec && opcoesRec.length > 1 && (
                <>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 6 }}>
                    Clique no seu nome *
                  </label>
                  <BotoesSelecao opcoes={opcoesRec} valor={fm.nome}
                    onSelect={(v: string) => { set("nome", v); set("ehRepPJ", ""); }} erro={errs.nome} />
                </>
              )}
              {temOpcoesRec && opcoesRec.length === 1 && (
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#5a7ab0", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                    Reclamante neste processo
                  </div>
                  <div style={{
                    background: fm.ehRepPJ ? "#f0f4ff" : "#1a3a6b",
                    border: "1.5px solid #c7d2fe",
                    borderRadius: 9,
                    padding: "10px 14px",
                    fontSize: 15,
                    fontWeight: 700,
                    color: fm.ehRepPJ ? "#1a3a6b" : "#fff",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    opacity: fm.ehRepPJ ? 0.55 : 1,
                    transition: "all .2s",
                  }}>
                    <span style={{ fontSize: 17 }}>👤</span>
                    {opcoesRec[0]}
                  </div>
                </div>
              )}
              {/* Opção: representante da PJ reclamante */}
              <div style={{ marginTop: temOpcoesRec ? 6 : 0, padding: "10px 12px", background: "#f0f7ff", borderRadius: 8, border: "1px solid #c7d2fe" }}>
                <div style={{ fontSize: 13, color: "#1a3a6b", fontWeight: 600, marginBottom: 6 }}>
                  Caso a parte reclamante seja pessoa jurídica, digite seu nome abaixo
                </div>
                <input value={fm.ehRepPJ ? fm.nome : ""}
                  onChange={(e) => {
                    set("ehRepPJ", e.target.value ? "1" : "");
                    set("nome", e.target.value);
                  }}
                  placeholder="Nome do(a) representante..."
                  style={inputStyle(!!errs.nome && !!fm.ehRepPJ)} />
                {errs.nome && fm.ehRepPJ && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.nome}</span>}
              </div>
            </>
          )}
          {/* Reclamada: botões da pauta */}
          {ehParteRdo && temOpcoesRdo && (
            <>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 6 }}>
                Clique no seu nome *
              </label>
              <BotoesSelecao opcoes={opcoesRdo} valor={fm.nome}
                onSelect={(v: string) => set("nome", v)} erro={errs.nome} />
            </>
          )}

          {/* Representante do Reclamado: subtipo + reclamada + nome livre */}
          {ehRep && (() => {
            const selecionadas = (fm.empresaRepresentada || "").split(" | ").filter(Boolean);
            const getSubtipos = () => { try { return JSON.parse(fm.subtipo_representante || "{}"); } catch { return {}; } };
            const setSubtipo = (rec: string, v: string) => {
              if (!temOpcoesRdo || opcoesRdo.length <= 1) {
                // caso simples: string direta
                set("subtipo_representante", v);
              } else {
                const s = getSubtipos(); s[rec] = v;
                set("subtipo_representante", JSON.stringify(s));
              }
            };
            const getSubtipoValor = (rec: string) => {
              if (!temOpcoesRdo || opcoesRdo.length <= 1) return fm.subtipo_representante || "";
              return getSubtipos()[rec] || "";
            };
            const SUBTIPOS = ["Sócio(a)", "Preposto(a)", "Próprio(a) reclamado(a) — pessoa física"];
            const SubtipoSelector = ({ rec }: { rec: string }) => (
              <BotoesSelecao
                opcoes={SUBTIPOS}
                valor={getSubtipoValor(rec)}
                onSelect={(v: string) => setSubtipo(rec, v)}
                erro={errs.subtipo_representante}
              />
            );
            return (
              <>
                {/* Passo 1 — selecionar reclamadas (só se houver múltiplas na pauta) */}
                {temOpcoesRdo && opcoesRdo.length > 1 && (
                  <div style={{ marginBottom: 12 }}>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 6 }}>
                      Representa qual(is) reclamada(s)? *
                    </label>
                    <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                      <div style={{ fontSize: 11, color: "#888", marginBottom: -2 }}>Selecione uma ou mais:</div>
                      {opcoesRdo.map((op: string) => {
                        const ativo = selecionadas.includes(op);
                        return (
                          <div key={op}>
                            <button type="button"
                              onClick={() => {
                                const atuais = selecionadas;
                                const novo = ativo ? atuais.filter((s: string) => s !== op) : [...atuais, op];
                                set("empresaRepresentada", novo.join(" | "));
                                if (ativo) {
                                  const s = getSubtipos(); delete s[op];
                                  set("subtipo_representante", JSON.stringify(s));
                                }
                              }}
                              style={{
                                width: "100%", padding: "11px 14px",
                                border: "2px solid " + (ativo ? "#e67e22" : "#e8eaed"),
                                borderRadius: ativo ? "9px 9px 0 0" : 9,
                                background: ativo ? "#e67e22" : "#f8f9fa",
                                color: ativo ? "#fff" : "#333", fontSize: 13,
                                fontWeight: ativo ? 700 : 400, cursor: "pointer", textAlign: "left",
                                display: "flex", alignItems: "center", gap: 8, transition: "all .15s",
                              }}>
                              <span style={{
                                width: 18, height: 18, borderRadius: 4, flexShrink: 0,
                                border: "2px solid " + (ativo ? "rgba(255,255,255,.6)" : "#ccc"),
                                background: ativo ? "rgba(255,255,255,.2)" : "#fff",
                                display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 12,
                              }}>{ativo ? "✓" : ""}</span>
                              {op}
                            </button>
                            {/* Subtipo expande inline logo abaixo quando selecionado */}
                            {ativo && (
                              <div style={{ border: "2px solid #e67e22", borderTop: "none", borderRadius: "0 0 9px 9px", padding: "10px 12px", background: "#fff8f2", marginBottom: 2 }}>
                                <div style={{ fontSize: 11, color: "#e67e22", fontWeight: 700, marginBottom: 6 }}>Você é nesta reclamada? *</div>
                                {["Sócio(a)", "Preposto(a)", "Próprio(a) reclamado(a) — pessoa física"].map((tipo) => {
                                  const sel = getSubtipoValor(op) === tipo;
                                  return (
                                    <button key={tipo} type="button"
                                      onClick={() => setSubtipo(op, tipo)}
                                      style={{
                                        display: "block", width: "100%", marginBottom: 4,
                                        padding: "8px 12px", border: "2px solid " + (sel ? "#e67e22" : "#e8eaed"),
                                        borderRadius: 7, background: sel ? "#e67e22" : "#fff",
                                        color: sel ? "#fff" : "#333", fontSize: 13,
                                        fontWeight: sel ? 700 : 400, cursor: "pointer", textAlign: "left", transition: "all .15s",
                                      }}>{tipo}</button>
                                  );
                                })}
                                {errs.subtipo_representante && !getSubtipoValor(op) && (
                                  <span style={{ color: "#e74c3c", fontSize: 11 }}>Selecione uma opção</span>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                      {errs.empresaRepresentada && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.empresaRepresentada}</span>}
                    </div>
                  </div>
                )}

                {/* Passo 2 — subtipo: lógica unificada */}
                {(!temOpcoesRdo || opcoesRdo.length <= 1) && (
                  <div style={{ marginBottom: 12 }}>
                    {temOpcoesRdo && opcoesRdo.length === 1 && (
                      <div style={{ marginBottom: 10, background: "#fff8f2", border: "1px solid #fdba74", borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "#92400e" }}>
                        Representando: <strong>{opcoesRdo[0]}</strong>
                      </div>
                    )}
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 6 }}>Você é *</label>
                    <SubtipoSelector rec="_" />
                  </div>
                )}
                {/* Múltiplas reclamadas — subtipo aparece inline logo abaixo de cada selecionada */}

                {/* Passo 3 — nome */}
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
                  Nome completo *
                </label>
                <input value={fm.nome} onChange={(e) => set("nome", e.target.value)}
                  placeholder="Nome completo" style={inputStyle(!!errs.nome)} />
                {errs.nome && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.nome}</span>}
              </>
            );
          })()}
          {/* Sem opções da pauta ou campo livre */}
          {((!ehParteRec && !ehParteRdo && !ehRep) || (ehParteRec && !temOpcoesRec) || (ehParteRdo && !temOpcoesRdo)) && (
            <>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
                Nome completo *
              </label>
              <input value={fm.nome} onChange={(e) => set("nome", e.target.value)}
                placeholder="Nome completo" style={inputStyle(!!errs.nome)} />
              {errs.nome && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.nome}</span>}
            </>
          )}
        </div>
      )}

      {isTest && (
        <>
          {/* Parte que vai ouvi-la */}
          {ehTestRec && temOpcoesRec && (
            <div style={{ marginBottom: 12 }}>
              {opcoesRec.length === 1 ? (
                <div style={{ background: "#f0f4ff", border: "1px solid #c7d2fe", borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "#1a3a6b" }}>
                  Testemunha de: <strong>{opcoesRec[0]}</strong>
                </div>
              ) : (
                <>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 6 }}>
                    Testemunha de qual(is) reclamante(s)? *
                  </label>
                  <BotoesMultiSelecao
                    opcoes={opcoesRec}
                    valores={fm.parteOuvinte}
                    onToggle={(v: string) => {
                      if (v.startsWith("__outro__:")) {
                        const txt = v.slice(10);
                        const daLista = (fm.parteOuvinte || "").split(" | ").filter((s: string) => opcoesRec.includes(s));
                        set("parteOuvinte", [...daLista, ...(txt ? [txt] : [])].join(" | "));
                      } else {
                        const atuais = (fm.parteOuvinte || "").split(" | ").filter(Boolean);
                        const novo = atuais.includes(v) ? atuais.filter((s: string) => s !== v) : [...atuais, v];
                        set("parteOuvinte", novo.join(" | "));
                      }
                    }}
                    erro={errs.parteOuvinte}
                    cor={COR_REC}
                  />
                </>
              )}
            </div>
          )}
          {ehTestRdo && temOpcoesRdo && (
            <div style={{ marginBottom: 12 }}>
              {opcoesRdo.length === 1 ? (
                <div style={{ background: "#fff8f2", border: "1px solid #fdba74", borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "#92400e" }}>
                  Testemunha de: <strong>{opcoesRdo[0]}</strong>
                </div>
              ) : (
                <>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 6 }}>
                    Testemunha de qual(is) reclamada(s)? *
                  </label>
                  <BotoesMultiSelecao
                    opcoes={opcoesRdo}
                    valores={fm.parteOuvinte}
                    onToggle={(v: string) => {
                      if (v.startsWith("__outro__:")) {
                        const txt = v.slice(10);
                        const daLista = (fm.parteOuvinte || "").split(" | ").filter((s: string) => opcoesRdo.includes(s));
                        set("parteOuvinte", [...daLista, ...(txt ? [txt] : [])].join(" | "));
                      } else {
                        const atuais = (fm.parteOuvinte || "").split(" | ").filter(Boolean);
                        const novo = atuais.includes(v) ? atuais.filter((s: string) => s !== v) : [...atuais, v];
                        set("parteOuvinte", novo.join(" | "));
                      }
                    }}
                    erro={errs.parteOuvinte}
                    cor={COR_RDO}
                  />
                </>
              )}
            </div>
          )}
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
              Nome completo *
            </label>
            <input value={fm.nome} onChange={(e) => set("nome", e.target.value)}
              placeholder="Como consta no documento" style={inputStyle(!!errs.nome)} />
            {errs.nome && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.nome}</span>}
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
              CPF *
            </label>
            <input value={fm.cpf} onChange={(e) => set("cpf", fCPF(e.target.value))}
              placeholder="000.000.000-00" maxLength={14} inputMode="numeric" style={inputStyle(!!errs.cpf)} />
            {errs.cpf && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.cpf}</span>}
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
              CEP do seu domicílio *
            </label>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                value={fm.cep}
                onChange={(e) => { const v = fCEP(e.target.value); set("cep", v); if (v.replace(/\D/g, "").length === 8) buscarCEP(v); }}
                onBlur={() => { if (fm.cep.replace(/\D/g, "").length === 8) buscarCEP(fm.cep); }}
                placeholder="00000-000" maxLength={9} inputMode="numeric"
                style={{ ...inputStyle(!!errs.cep), flex: 1 }}
              />
              {bCEP && <Spinner size={18} />}
            </div>
            {errs.cep && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.cep}</span>}
            {!errs.cep && <span style={{ fontSize: 11, color: "#888" }}>O endereço será preenchido automaticamente pelo CEP</span>}
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
              Endereço *
            </label>
            <input value={fm.endereco} onChange={(e) => set("endereco", e.target.value)}
              placeholder="Rua, avenida..." style={inputStyle(!!errs.endereco)} />
            {errs.endereco && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.endereco}</span>}
          </div>
          <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
            <div style={{ flex: "0 0 120px" }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
                Número *
              </label>
              <input value={fm.numero} onChange={(e) => set("numero", e.target.value)}
                placeholder="123" style={inputStyle(!!errs.numero)} />
              {errs.numero && <span style={{ color: "#e74c3c", fontSize: 12 }}>{errs.numero}</span>}
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#444", marginBottom: 4 }}>
                Complemento <span style={{ fontWeight: 400, color: "#aaa", fontSize: 11 }}>(opcional)</span>
              </label>
              <input value={fm.complemento} onChange={(e) => set("complemento", e.target.value)}
                placeholder="Apto, Bloco..." style={inputStyle(false)} />
            </div>
          </div>
        </>
      )}

      {/* Advogado: dois botões — individual ou grupo */}
      {isAdv && onIrGrupo ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <button
            onClick={handleSubmit}
            disabled={enviando}
            style={{ width: "100%", background: enviando ? "#bdc3c7" : "#27ae60", color: "#fff", border: "none", borderRadius: 9, padding: "14px", fontSize: 15, fontWeight: 700, cursor: enviando ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, transition: "background .2s" }}
          >
            {enviando ? <><Spinner size={18} color="#fff" /> Registrando...</> : "Confirmar check-in individual"}
          </button>
          <button
            onClick={() => {
              // Validação leve para ir ao grupo: só nome + OAB
              const eG: any = {};
              if (!fm.nome.trim()) eG.nome = "Nome obrigatório";
              if (!fm.oab.trim()) eG.oab = "OAB obrigatória";
              else { const oabErr = validOAB(fm.oab); if (oabErr) eG.oab = oabErr; }
              if (Object.keys(eG).length) { setErrs(eG); return; }
              setErrs({});
              onIrGrupo({ ...fm, papel, regularizacao: fm.reg });
            }}
            style={{ width: "100%", background: "#1a3a6b", color: "#fff", border: "none", borderRadius: 9, padding: "14px", fontSize: 15, fontWeight: 700, cursor: "pointer", transition: "background .2s" }}
          >
            Fazer check-in em grupo →
          </button>
        </div>
      ) : (
        <button
          onClick={handleSubmit}
          disabled={enviando}
          style={{ width: "100%", background: enviando ? "#bdc3c7" : "#27ae60", color: "#fff", border: "none", borderRadius: 9, padding: "14px", fontSize: 15, fontWeight: 700, cursor: enviando ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, transition: "background .2s" }}
        >
          {enviando ? <><Spinner size={18} color="#fff" /> Registrando...</> : "Confirmar check-in"}
        </button>
      )}
    </div>
  );
}

// ── FORMULÁRIO PRINCIPAL ──
function Form({ processo, info, onVoltar, onSubmit, cpfsUsados, grupoHabilitado = true }: any) {
  const [etapa, setEtapa] = useState(1);
  const [papel, setPapel] = useState("");
  const [modoGrupo, setModoGrupo] = useState(false);
  const [errs, setErrs] = useState<any>({});

  const [grupo, setGrupo] = useState<any>([]);

  // Constrói os itens do grupo quando modoGrupo é ativado (depois de papel estar definido)
  const buildGrupo = (p: string, dadosAdv?: any) => {
    const ehRec = p === "Advogado(a) do(a) Reclamante";
    const papeis = ehRec
      ? [p, "Parte Reclamante"]
      : [p, "Representante do(a) Reclamado(a)"];
    return papeis.map((pp, i) => ({
      papel: pp, ativo: i === 0 && pp !== "Parte Reclamante",
      nome: "", cpf: "", oab: "", cep: "",
      endereco: "", numero: "", complemento: "", reg: "", proposta: "",
      parteRepresentada: "", empresaRepresentada: "",
      subtipo_representante: "", _id: Math.random(),
    }));
  };

  const addTestemunha = (tipo: "Testemunha do(a) Reclamante" | "Testemunha do(a) Reclamado(a)", dadosAdv?: any) => {
    setGrupo((g: any) => {
      // Herda parteOuvinte do advogado — usa dadosAdvogado se disponível (advogado travado)
      const adv = dadosAdv || g[0];
      const rawRep = adv?.parteRepresentada || adv?.empresaRepresentada || "";
      let parteHerdada = rawRep;
      try {
        const obj = JSON.parse(rawRep);
        if (typeof obj === "object") parteHerdada = ""; // não herda JSON — testemunha deve selecionar
      } catch {}
      return [...g, {
        papel: tipo, ativo: true,
        nome: "", cpf: "", oab: "", cep: "",
        endereco: "", numero: "", complemento: "", reg: "", proposta: "",
        parteRepresentada: "", empresaRepresentada: "", parteOuvinte: parteHerdada,
        subtipo_representante: "", _id: Math.random(),
      }];
    });
  };

  const addRepresentante = () => {
    setGrupo((g: any) => [...g, {
      papel: "Representante do(a) Reclamado(a)", ativo: true,
      nome: "", cpf: "", oab: "", cep: "",
      endereco: "", numero: "", complemento: "", reg: "", proposta: "",
      parteRepresentada: "", empresaRepresentada: "",
      subtipo_representante: "", _id: Math.random(),
    }]);
  };

  const removeItem = (idx: number) => {
    setGrupo((g: any) => g.filter((_: any, i: number) => i !== idx));
  };
  const [grupoErrs, setGrupoErrs] = useState<any>({});
  const [submetendo, setSubmetendo] = useState(false);
  const [dadosAdvogado, setDadosAdvogado] = useState<any>(null);

  const isAdvForm = papel.includes("Advogado(a)");

  const validEtapa1 = () => {
    if (!papel) { setErrs({ papel: "Selecione o seu papel" }); return false; }
    setErrs({}); return true;
  };

  const setGrupoField = (idx: number, k: string, v: string) => {
    setGrupo((g: any) => g.map((item: any, i: number) => i === idx ? { ...item, [k]: v } : item));
  };

  const buscarCEPGrupo = async (idx: number, c: string) => {
    const n = c.replace(/\D/g, ""); if (n.length !== 8) return;
    try {
      const r = await fetch("https://viacep.com.br/ws/" + n + "/json/");
      const d = await r.json();
      if (!d.erro) setGrupoField(idx, "endereco", (d.logradouro || "") + (d.bairro ? ", " + d.bairro : "") + (d.localidade ? ", " + d.localidade : "") + (d.uf ? " - " + d.uf : ""));
    } catch (e) {}
  };

  const { reclamantes: recsGrupo, reclamadas: rdosGrupo } = extrairPartesDoTexto(info?.partes || "");

  const validarGrupo = () => {
    // Se advogado veio pré-preenchido da tela individual, pula idx=0 inteiramente
    const ativos = grupo.filter((g: any, i: number) => {
      if (i === 0 && dadosAdvogado) return false; // advogado travado: já validado antes
      return g.ativo;
    });
    // Exige ao menos um participante além do advogado (ou ao menos o advogado travado)
    const temAlguem = dadosAdvogado || ativos.length > 0;
    if (!temAlguem) { setGrupoErrs({ _geral: "Selecione ao menos uma pessoa para fazer check-in." }); return false; }
    const errsG: any = {};
    ativos.forEach((item: any) => {
      const idx = grupo.indexOf(item);
      const isAdvItem = item.papel.includes("Advogado(a)");
      const isT = item.papel.includes("Testemunha");
      const isRep = item.papel === "Representante do(a) Reclamado(a)";
      const isParte = item.papel === "Parte Reclamante" || item.papel === "Parte Reclamada";
      // Nome auto-preenchido para parte reclamante única não deve falhar
      const nomeAutoOk = (isParte && item.papel === "Parte Reclamante" && recsGrupo.length === 1);
      if (!item.nome.trim() && !nomeAutoOk) errsG[idx + "_nome"] = "Nome obrigatório";
      if (isRep && rdosGrupo.length > 1) {
        // Múltiplas reclamadas: exige ao menos uma selecionada + subtipo para cada
        if (!item.empresaRepresentada?.trim()) errsG[idx + "_rep"] = "Selecione qual reclamada representa";
        else {
          const selecionadas = item.empresaRepresentada.split(" | ").filter(Boolean);
          const subtipos = (() => { try { return JSON.parse(item.subtipo_representante || "{}"); } catch { return {}; } })();
          const faltando = selecionadas.some((r: string) => !subtipos[r]);
          if (faltando) errsG[idx + "_subtipo"] = "Selecione o tipo para cada reclamada";
        }
      } else if (isRep && rdosGrupo.length <= 1) {
        // 1 reclamada: subtipo obrigatório
        if (!item.subtipo_representante?.trim()) errsG[idx + "_subtipo"] = "Selecione uma opção";
      }
      if (isAdvItem) {
        if (!item.oab.trim()) errsG[idx + "_oab"] = "OAB obrigatória";
        else { const oabErr = validOAB(item.oab); if (oabErr) errsG[idx + "_oab"] = oabErr; }
        const ehRec = item.papel === "Advogado(a) do(a) Reclamante";
        if (ehRec && recsGrupo.length !== 1 && !item.parteRepresentada.trim()) errsG[idx + "_rep"] = "Selecione a parte que representa";
        if (!ehRec && rdosGrupo.length !== 1 && !item.empresaRepresentada.trim()) errsG[idx + "_rep"] = "Selecione a parte que representa";
      }
      if (isT) {
        if (item.cpf.replace(/\D/g, "").length < 11) errsG[idx + "_cpf"] = "CPF inválido";
        else if (!validCPF(item.cpf)) errsG[idx + "_cpf"] = "CPF inválido (dígitos verificadores)";
        else if (cpfsUsados.includes(item.cpf.replace(/\D/g, ""))) errsG[idx + "_cpf"] = "CPF já registrado";
        if (!item.endereco.trim()) errsG[idx + "_endereco"] = "Endereço obrigatório";
        if (!item.numero.trim()) errsG[idx + "_numero"] = "Número obrigatório";
        if (item.cep.replace(/\D/g, "").length < 8) errsG[idx + "_cep"] = "CEP inválido";
      }
    });
    setGrupoErrs(errsG);
    return !Object.keys(errsG).length;
  };

  const submeterGrupo = async () => {
    if (!validarGrupo()) return;
    setSubmetendo(true);
    try {
      // Se o advogado veio pré-preenchido da tela individual, submete ele primeiro
      if (dadosAdvogado) {
        await onSubmit({ ...dadosAdvogado, modalidade: info?.tipo === "videoconferência" ? "virtual" : "presencial", proposta: dadosAdvogado.proposta || null }, true);
      }
      // Submete os demais participantes ativos (pula idx=0 se for o advogado travado)
      const ativos = grupo.filter((g: any, i: number) => {
        if (i === 0 && dadosAdvogado) return false;
        return g.ativo;
      });
      for (const item of ativos) {
        const isAdvItem = item.papel.includes("Advogado(a)");
        const isT = item.papel.includes("Testemunha");
        const isRepItem = item.papel === "Representante do(a) Reclamado(a)";
        const isParte = item.papel === "Parte Reclamante" || item.papel === "Parte Reclamada";
            const nomeAutoGrupo = (!item.nome.trim() && isParte && item.papel === "Parte Reclamante" && recsGrupo.length === 1)
          ? recsGrupo[0] : item.nome;
        // Resolve subtipo: se JSON multi-reclamada, converte em texto legível
        const resolveSubtipoGrupo = () => {
          if (!item.subtipo_representante) return null;
          try {
            const obj = JSON.parse(item.subtipo_representante);
            if (typeof obj === "object" && obj !== null) {
              const entries = Object.entries(obj);
              if (entries.length === 0) return null;
              const tipos = [...new Set(entries.map(([, v]) => v as string))];
              if (tipos.length === 1) return tipos[0];
              return entries.map(([rec, tipo]) => `${tipo} (${rec})`).join(" / ");
            }
          } catch {}
          return item.subtipo_representante || null;
        };
        const checkin = {
          nome: nomeAutoGrupo, papel: item.papel,
          cpf: isT ? item.cpf : null,
          oab: isAdvItem ? item.oab : null,
          hora: now(),
          modalidade: info?.tipo === "videoconferência" ? "virtual" : "presencial",
          endereco: isT ? item.endereco : null,
          cep: isT ? item.cep : null,
          numero: isT ? item.numero : null,
          complemento: isT ? item.complemento : null,
          parteRepresentada: isAdvItem
            ? (item.parteRepresentada || (item.papel === "Advogado(a) do(a) Reclamante" && recsGrupo.length === 1 ? recsGrupo[0] : null))
            : null,
          empresaRepresentada: (isAdvItem || isRepItem)
            ? (item.empresaRepresentada || (rdosGrupo.length === 1 ? rdosGrupo[0] : null))
            : null,
          regularizacao: isAdvItem ? (item.reg || null) : null,
          subtipo_representante: isRepItem ? resolveSubtipoGrupo() : null,
          parteOuvinte: isT
            ? (item.parteOuvinte || (item.papel === "Testemunha do(a) Reclamante" && recsGrupo.length === 1 ? recsGrupo[0] : rdosGrupo.length === 1 ? rdosGrupo[0] : null))
            : null,
          proposta: isAdvItem ? (() => {
            if (!item.proposta) return null;
            try {
              const obj = JSON.parse(item.proposta);
              const temValor = Object.values(obj).some((v: any) => v && String(v).trim());
              return temValor ? item.proposta : null;
            } catch {}
            return item.proposta.trim() ? item.proposta : null;
          })() : null,
        };
        await onSubmit(checkin, true);
      }
      // Finaliza o grupo DEPOIS de salvar tudo
      await onSubmit(null, false, true);
    } catch (e: any) {
      setSubmetendo(false);
      const toastEl = document.createElement("div");
      toastEl.textContent = "Erro ao registrar check-in em grupo. Verifique a conexão e tente novamente.";
      Object.assign(toastEl.style, {
        position: "fixed", top: "50%", right: "16px", transform: "translateY(-50%)",
        background: "#c62828", color: "#fff", borderRadius: "14px",
        padding: "18px 24px", fontSize: "15px", fontWeight: "700",
        zIndex: "9999", maxWidth: "340px", lineHeight: "1.5",
        fontFamily: "'Segoe UI', sans-serif", boxShadow: "0 12px 40px rgba(0,0,0,.35)",
      });
      document.body.appendChild(toastEl);
      setTimeout(() => toastEl.remove(), 5000);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(160deg,#0d2b5e,#1a5276)",
      display: "flex", flexDirection: "column", alignItems: "center",
      padding: "18px 14px", fontFamily: "'Segoe UI',sans-serif",
    }}>
      <GlobalStyle />
      {/* cabeçalho */}
      <div style={{ width: "100%", maxWidth: 480, marginBottom: 10, display: "flex", alignItems: "center", gap: 10 }}>
        <button
          onClick={etapa === 1 ? onVoltar : () => { setEtapa(1); setModoGrupo(false); }}
          style={{ background: "rgba(255,255,255,.2)", border: "none", color: "#fff", borderRadius: 7, padding: "7px 14px", cursor: "pointer", fontSize: 13 }}
        >
          ← Voltar
        </button>
        <div style={{ color: "#fff", flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Check-in — {info?.hora || "--:--"}</div>
          <div style={{ fontSize: 11, opacity: 0.8, fontFamily: "monospace" }}>{processo}</div>
        </div>
        {/* barra de progresso */}
        <div style={{ display: "flex", gap: 5 }}>
          {[1, 2].map((n) => (
            <div key={n} style={{
              width: 28, height: 5, borderRadius: 3,
              background: etapa >= n ? "#fff" : "rgba(255,255,255,.3)",
              transition: "background .3s",
            }} />
          ))}
        </div>
      </div>

      <div style={{
        width: "100%", maxWidth: 480, background: "#fff", borderRadius: 16,
        padding: 22, boxShadow: "0 8px 32px rgba(0,0,0,.2)", animation: "fadeInUp .3s ease",
      }}>

        {/* ETAPA 1 */}
        {etapa === 1 && (
          <>
            <h3 style={{ margin: "0 0 6px", color: "#1a3a6b", fontSize: 16 }}>
              Qual é o seu papel nesta audiência?
            </h3>
            <p style={{ margin: "0 0 16px", fontSize: 12, color: "#aaa" }}>
              Selecione como você participa desta audiência.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 9, marginBottom: 16 }}>
              {PAPEIS.map((p: string) => {
                const desc: any = {
                  "Parte Reclamante": "Quem entrou com a ação trabalhista",
                  "Advogado(a) do(a) Reclamante": "Advogado(a) de quem entrou com a ação",
                  "Testemunha do(a) Reclamante": "Testemunha de quem entrou com a ação",
                  "Representante do(a) Reclamado(a)": "Sócio(a), preposto(a) ou o(a) próprio(a) reclamado(a)",
                  "Advogado(a) do(a) Reclamado(a)": "Advogado(a) da empresa ou pessoa acionada",
                  "Testemunha do(a) Reclamado(a)": "Testemunha da empresa ou pessoa acionada",
                };
                return (
                  <button key={p} onClick={() => setPapel(p)}
                    style={{
                      padding: "13px 16px", border: "2px solid " + (papel === p ? "#1a3a6b" : "#e8eaed"),
                      borderRadius: 10, background: papel === p ? "#1a3a6b" : "#fff",
                      color: papel === p ? "#fff" : "#333", fontSize: 14,
                      fontWeight: papel === p ? 700 : 400, cursor: "pointer", textAlign: "left",
                      transition: "all .15s",
                    }}
                  >
                    <div>{p}</div>
                    {desc[p] && <div style={{ fontSize: 11, fontWeight: 400, opacity: 0.75, marginTop: 2 }}>{desc[p]}</div>}
                  </button>
                );
              })}
            </div>
            {errs.papel && <div style={{ color: "#e74c3c", fontSize: 12, marginBottom: 10 }}>{errs.papel}</div>}
            <button
              onClick={() => { if (validEtapa1()) setEtapa(2); }}
              style={{
                width: "100%", background: papel ? "#1a3a6b" : "#bdc3c7", color: "#fff",
                border: "none", borderRadius: 9, padding: "14px", fontSize: 15,
                fontWeight: 700, cursor: papel ? "pointer" : "not-allowed", transition: "background .2s",
              }}
            >
              Continuar →
            </button>
          </>
        )}

        {/* ETAPA 2 — individual */}
        {etapa === 2 && !modoGrupo && (
          <>
            <h3 style={{ margin: "0 0 14px", color: "#1a3a6b", fontSize: 16 }}>Seus dados</h3>
            <FormIndividual
              papel={papel} info={info} processo={processo}
              onVoltar={() => setEtapa(1)} onSubmit={onSubmit}
              cpfsUsados={cpfsUsados} partesDoProcesso={[]}
              onIrGrupo={isAdvForm && grupoHabilitado ? (dadosAdv: any) => {
                setDadosAdvogado(dadosAdv);
                setGrupo(buildGrupo(papel, dadosAdv));
                setModoGrupo(true);
              } : undefined}
            />
          </>
        )}

        {/* ETAPA 2 — grupo */}
        {etapa === 2 && modoGrupo && (
          <>
            <h3 style={{ margin: "0 0 4px", color: "#1a3a6b", fontSize: 15 }}>Check-in em grupo</h3>
            <p style={{ margin: "0 0 14px", fontSize: 12, color: "#888", lineHeight: 1.5 }}>
              Selecione quem está com você e preencha os dados de cada um.
            </p>
            {grupoErrs._geral && (
              <div style={{ color: "#e74c3c", fontSize: 12, marginBottom: 10, background: "#fdecea", padding: "8px 10px", borderRadius: 7 }}>
                {grupoErrs._geral}
              </div>
            )}

            {grupo.map((item: any, idx: number) => {
              const isAdvItem = item.papel.includes("Advogado(a)");
              const isParte = item.papel === "Parte Reclamante";
              const isTestG = item.papel.includes("Testemunha");
              const isPreposto = item.papel === "Representante do(a) Reclamado(a)";
              const opcoesNome = item.papel === "Parte Reclamante" ? recsGrupo : [];
              const temOpcoes = opcoesNome.length > 0;
              const nomeEhLivre = !opcoesNome.includes(item.nome) && item.nome !== "" && item.nome !== "__outro__";
              const ehAdvRec = item.papel === "Advogado(a) do(a) Reclamante";
              const opcoesRep = ehAdvRec ? recsGrupo : rdosGrupo;
              const temOpcoesRep = opcoesRep.length > 0;
              const repField = ehAdvRec ? "parteRepresentada" : "empresaRepresentada";
              const repValor = item[repField] || "";
              const repEhLivre = !opcoesRep.includes(repValor) && repValor !== "" && repValor !== "__outro__";
              const cor = corPorPapel(item.papel);
              // Card do(a) advogado(a): travado e pré-preenchido quando veio da tela individual
              const eAdvTravado = idx === 0 && isAdvItem && dadosAdvogado;
              const nomeExibido = eAdvTravado ? dadosAdvogado.nome : item.nome;
              const repExibida = eAdvTravado ? (dadosAdvogado.parteRepresentada || dadosAdvogado.empresaRepresentada || "") : repValor;

              return (
                <div key={item._id || idx} style={{ marginBottom: 12, border: "1.5px solid " + (eAdvTravado ? cor : item.ativo ? cor : "#e8eaed"), borderRadius: 10, overflow: "hidden", transition: "border .2s" }}>
                  <button
                    onClick={() => { if (!eAdvTravado) setGrupo((g: any) => g.map((x: any, i: number) => i === idx ? { ...x, ativo: !x.ativo } : x)); }}
                    style={{
                      width: "100%", background: eAdvTravado ? cor : item.ativo ? cor : "#f8f9fa",
                      color: eAdvTravado || item.ativo ? "#fff" : "#333", border: "none", padding: "12px 14px",
                      fontSize: 13, fontWeight: 700, cursor: eAdvTravado ? "default" : "pointer", textAlign: "left",
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      transition: "all .2s",
                    }}
                  >
                    <span>
                      {item.papel}
                      {isParte && !item.ativo && <span style={{ opacity: 0.6, fontSize: 11, fontWeight: 400 }}> (opcional — clique para adicionar)</span>}
                      {nomeExibido ? <span style={{ opacity: 0.85 }}> — {nomeExibido}</span> : ""}
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {(isTestG || (isPreposto && idx > 1)) && !eAdvTravado && (
                        <span
                          onClick={(e) => { e.stopPropagation(); removeItem(idx); }}
                          title={"Remover " + (isTestG ? "testemunha" : "representante")}
                          style={{ fontSize: 16, opacity: 0.7, cursor: "pointer", lineHeight: 1 }}
                        >✕</span>
                      )}
                      {eAdvTravado
                        ? <span style={{ background: "rgba(255,255,255,.25)", borderRadius: 20, padding: "2px 8px", fontSize: 11 }}>✓ preenchido</span>
                        : <span style={{ fontSize: 14 }}>{item.ativo ? "▲" : "▼"}</span>
                      }
                    </span>
                  </button>

                  {/* Advogado travado: exibe resumo dos dados pré-preenchidos */}
                  {eAdvTravado && (
                    <div style={{ padding: "10px 14px", background: "#f8faff", display: "flex", flexWrap: "wrap", gap: 12, fontSize: 12, color: "#444" }}>
                      <span><strong>OAB:</strong> {dadosAdvogado.oab}</span>
                      {(dadosAdvogado.parteRepresentada || dadosAdvogado.empresaRepresentada) && (
                        <span><strong>Representa:</strong> {dadosAdvogado.parteRepresentada || dadosAdvogado.empresaRepresentada}</span>
                      )}
                      {dadosAdvogado.regularizacao && (
                        <span style={{ background: "#fff3cd", borderRadius: 5, padding: "2px 7px", fontWeight: 700, color: "#856404" }}>⚠ {dadosAdvogado.regularizacao}</span>
                      )}
                    </div>
                  )}

                  {!eAdvTravado && item.ativo && (
                    <div style={{ padding: "12px 14px", background: "#fff" }}>

                      {/* ADVOGADO: nome + OAB + parte representada */}
                      {isAdvItem && (
                        <>
                          <div style={{ marginBottom: 10 }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>Nome completo *</label>
                            <input value={item.nome} onChange={(e) => setGrupoField(idx, "nome", e.target.value)}
                              placeholder="Como consta na OAB"
                              style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_nome"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                            {grupoErrs[idx + "_nome"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_nome"]}</span>}
                          </div>
                          <div style={{ marginBottom: 10 }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>Número OAB *</label>
                            <input value={item.oab} onChange={(e) => setGrupoField(idx, "oab", fOAB(e.target.value))}
                              placeholder="Ex: SP123456"
                              style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_oab"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                            {grupoErrs[idx + "_oab"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_oab"]}</span>}
                          </div>
                          <div style={{ marginBottom: 10 }}>
                            {temOpcoesRep && opcoesRep.length === 1 ? (
                              <div style={{ background: ehAdvRec ? "#f0f4ff" : "#fff8f2", border: "1px solid " + (ehAdvRec ? "#c7d2fe" : "#fdba74"), borderRadius: 8, padding: "7px 10px", fontSize: 12, color: ehAdvRec ? "#1a3a6b" : "#92400e" }}>
                                Representando: <strong>{opcoesRep[0]}</strong>
                              </div>
                            ) : (
                              <>
                                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 4 }}>
                                  {ehAdvRec ? "Clique na parte que você representa *" : "Clique na(s) parte(s) que você representa *"}
                                </label>
                                {temOpcoesRep ? (
                                  ehAdvRec ? (
                                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                      {opcoesRep.map((op: string) => (
                                        <button key={op} onClick={() => setGrupoField(idx, repField, op)}
                                          style={{ padding: "9px 13px", border: "2px solid " + (repValor === op ? cor : "#e8eaed"), borderRadius: 9, background: repValor === op ? cor : "#f8f9fa", color: repValor === op ? "#fff" : "#333", fontSize: 13, fontWeight: repValor === op ? 700 : 400, cursor: "pointer", textAlign: "left" }}>
                                          {op}
                                        </button>
                                      ))}
                                      <button onClick={() => setGrupoField(idx, repField, "__outro__")}
                                        style={{ padding: "8px 13px", border: "2px solid " + (repEhLivre || repValor === "__outro__" ? cor : "#e8eaed"), borderRadius: 9, background: repEhLivre || repValor === "__outro__" ? "#f0f4ff" : "#f8f9fa", color: "#1a3a6b", fontSize: 12, cursor: "pointer", textAlign: "left" }}>
                                        ✏️ Outro / digitar manualmente
                                      </button>
                                      {(repEhLivre || repValor === "__outro__") && (
                                        <input value={repValor === "__outro__" ? "" : repValor} onChange={(e) => setGrupoField(idx, repField, e.target.value)}
                                          placeholder="Nome da parte..." autoFocus
                                          style={{ padding: "9px 11px", border: "1.5px solid " + cor, borderRadius: 7, fontSize: 13, boxSizing: "border-box" as any, width: "100%" }} />
                                      )}
                                    </div>
                                  ) : (
                                    <BotoesMultiSelecao opcoes={opcoesRep} valores={repValor}
                                      onToggle={(v: string) => {
                                        if (v.startsWith("__outro__:")) {
                                          const txt = v.slice(10);
                                          const daLista = (repValor || "").split(" | ").filter((s: string) => opcoesRep.includes(s));
                                          setGrupoField(idx, repField, [...daLista, ...(txt ? [txt] : [])].join(" | "));
                                        } else {
                                          const atuais = (repValor || "").split(" | ").filter(Boolean);
                                          const novo = atuais.includes(v) ? atuais.filter((s: string) => s !== v) : [...atuais, v];
                                          setGrupoField(idx, repField, novo.join(" | "));
                                        }
                                      }}
                                      erro={grupoErrs[idx + "_rep"]} cor={cor} />
                                  )
                                ) : (
                                  <input value={repValor} onChange={(e) => setGrupoField(idx, repField, e.target.value)}
                                    placeholder="Nome da parte"
                                    style={{ width: "100%", padding: "9px 11px", border: "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                                )}
                                {grupoErrs[idx + "_rep"] && !temOpcoesRep && <span style={{ color: "#e74c3c", fontSize: 11, display: "block", marginTop: 4 }}>{grupoErrs[idx + "_rep"]}</span>}
                              </>
                            )}
                          </div>
                          {/* Regularização */}
                          <div style={{ marginBottom: 10 }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>
                              Regularização processual <span style={{ fontWeight: 400, color: "#aaa" }}>(precisa de prazo?)</span>
                            </label>
                            <CheckboxesRegularizacao valor={item.reg || ""} onChange={(v: string) => setGrupoField(idx, "reg", v)} />
                          </div>
                          {/* Proposta de acordo */}
                          <div style={{ marginBottom: 4, background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: 8, padding: "10px 12px" }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#0369a1", marginBottom: 6 }}>
                              💰 Proposta de acordo? <span style={{ fontWeight: 400, fontSize: 11 }}>(só Juiz(a) e Secretário(a) verão)</span>
                            </label>
                            {ehAdvRec ? (
                              <input value={item.proposta || ""}
                                onChange={(e) => setGrupoField(idx, "proposta", fMoeda(e.target.value))}
                                placeholder="R$ 0,00" inputMode="numeric"
                                style={{ width: "100%", padding: "8px 10px", border: "1.5px solid #bae6fd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" as any, background: "#fff" }} />
                            ) : (
                              (() => {
                                const selecionadas = (item.empresaRepresentada || "").split(" | ").filter(Boolean);
                                const propostas = (() => { try { return JSON.parse(item.proposta || "{}"); } catch { return {}; } })();
                                if (selecionadas.length === 0) return (
                                  <input value={propostas["_geral"] || ""}
                                    onChange={(e) => setGrupoField(idx, "proposta", JSON.stringify({ ...propostas, _geral: fMoeda(e.target.value) }))}
                                    placeholder="R$ 0,00" inputMode="numeric"
                                    style={{ width: "100%", padding: "8px 10px", border: "1.5px solid #bae6fd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" as any, background: "#fff" }} />
                                );
                                return (
                                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                    {selecionadas.map((rec: string) => (
                                      <div key={rec}>
                                        <div style={{ fontSize: 10, fontWeight: 700, color: "#e67e22", marginBottom: 2, textTransform: "uppercase" }}>{rec}</div>
                                        <input value={propostas[rec] || ""}
                                          onChange={(e) => setGrupoField(idx, "proposta", JSON.stringify({ ...propostas, [rec]: fMoeda(e.target.value) }))}
                                          placeholder="R$ 0,00" inputMode="numeric"
                                          style={{ width: "100%", padding: "8px 10px", border: "1.5px solid #bae6fd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" as any, background: "#fff" }} />
                                      </div>
                                    ))}
                                  </div>
                                );
                              })()
                            )}
                          </div>
                        </>
                      )}

                      {isParte && (<>
                          {temOpcoes && opcoesNome.length === 1 ? (
                            <div style={{ marginBottom: 10, background: "#f0f4ff", border: "1px solid #c7d2fe", borderRadius: 8, padding: "7px 10px", fontSize: 12, color: "#1a3a6b" }}>
                              <strong>{opcoesNome[0]}</strong>
                            </div>
                          ) : (
                            <>
                              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 6 }}>Selecione o nome da parte *</label>
                              {temOpcoes ? (
                                <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: grupoErrs[idx + "_nome"] ? 4 : 10 }}>
                                  {opcoesNome.map((op: string) => (
                                    <button key={op} onClick={() => setGrupoField(idx, "nome", op)}
                                      style={{
                                        padding: "10px 13px", border: "2px solid " + (item.nome === op ? "#1a3a6b" : "#e8eaed"),
                                        borderRadius: 9, background: item.nome === op ? "#1a3a6b" : "#f8f9fa",
                                        color: item.nome === op ? "#fff" : "#333", fontSize: 13,
                                        fontWeight: item.nome === op ? 700 : 400, cursor: "pointer", textAlign: "left",
                                      }}>
                                      {op}
                                    </button>
                                  ))}
                                  <button onClick={() => setGrupoField(idx, "nome", "__outro__")}
                                    style={{ padding: "8px 13px", border: "2px solid " + (nomeEhLivre || item.nome === "__outro__" ? "#1a3a6b" : "#e8eaed"), borderRadius: 9, background: nomeEhLivre || item.nome === "__outro__" ? "#f0f4ff" : "#f8f9fa", color: "#1a3a6b", fontSize: 12, cursor: "pointer", textAlign: "left" }}>
                                    ✏️ Outro / digitar manualmente
                                  </button>
                                  {(nomeEhLivre || item.nome === "__outro__") && (
                                    <input value={item.nome === "__outro__" ? "" : item.nome} onChange={(e) => setGrupoField(idx, "nome", e.target.value)}
                                      placeholder="Nome completo" autoFocus
                                      style={{ padding: "9px 11px", border: "1.5px solid #1a3a6b", borderRadius: 7, fontSize: 13, boxSizing: "border-box" as any, width: "100%" }} />
                                  )}
                                </div>
                              ) : (
                                <input value={item.nome} onChange={(e) => setGrupoField(idx, "nome", e.target.value)}
                                  placeholder="Nome completo"
                                  style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_nome"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box", marginBottom: grupoErrs[idx + "_nome"] ? 4 : 10 }} />
                              )}
                              {grupoErrs[idx + "_nome"] && <span style={{ color: "#e74c3c", fontSize: 11, display: "block", marginBottom: 6 }}>{grupoErrs[idx + "_nome"]}</span>}
                            </>
                          )}
                        </>
                      )}

                      {isPreposto && (
                        <>
                          {/* Reclamada — badge quando 1, seleção quando múltiplas */}
                          {rdosGrupo.length > 0 && (
                            <div style={{ marginBottom: 10 }}>
                              {rdosGrupo.length === 1 ? (
                                <>
                                  <div style={{ background: "#fff8f2", border: "1px solid #fdba74", borderRadius: 8, padding: "7px 10px", fontSize: 12, color: "#92400e", marginBottom: 8 }}>
                                    Representando: <strong>{rdosGrupo[0]}</strong>
                                  </div>
                                  {/* Subtipo único quando só 1 reclamada */}
                                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 6 }}>O representante é *</label>
                                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                    {["Sócio(a)", "Preposto(a)", "Próprio(a) reclamado(a) — pessoa física"].map((op) => (
                                      <button key={op} onClick={() => setGrupoField(idx, "subtipo_representante", op)}
                                        style={{ padding: "9px 13px", border: "2px solid " + (item.subtipo_representante === op ? cor : "#e8eaed"), borderRadius: 9, background: item.subtipo_representante === op ? cor : "#f8f9fa", color: item.subtipo_representante === op ? "#fff" : "#333", fontSize: 13, fontWeight: item.subtipo_representante === op ? 700 : 400, cursor: "pointer", textAlign: "left" }}>
                                        {op}
                                      </button>
                                    ))}
                                  </div>
                                  {grupoErrs[idx + "_subtipo"] && <span style={{ color: "#e74c3c", fontSize: 11, display: "block", marginTop: 4 }}>{grupoErrs[idx + "_subtipo"]}</span>}
                                </>
                              ) : (
                                <>
                                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 6 }}>Representa qual(is) reclamada(s)? *</label>
                                  {/* Para cada reclamada: checkbox + subtipo inline */}
                                  {(() => {
                                    const selecionadas = (item.empresaRepresentada || "").split(" | ").filter(Boolean);
                                    const getSubtipos = () => { try { return JSON.parse(item.subtipo_representante || "{}"); } catch { return {}; } };
                                    const setSubtipoRec = (rec: string, v: string) => {
                                      const s = getSubtipos(); s[rec] = v;
                                      setGrupoField(idx, "subtipo_representante", JSON.stringify(s));
                                    };
                                    return (
                                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                        {rdosGrupo.map((op: string) => {
                                          const ativo = selecionadas.includes(op);
                                          const subtipoValor = getSubtipos()[op] || "";
                                          return (
                                            <div key={op}>
                                              <button type="button"
                                                onClick={() => {
                                                  const atuais = selecionadas;
                                                  const novo = ativo ? atuais.filter((s: string) => s !== op) : [...atuais, op];
                                                  setGrupoField(idx, "empresaRepresentada", novo.join(" | "));
                                                  if (ativo) {
                                                    const s = getSubtipos(); delete s[op];
                                                    setGrupoField(idx, "subtipo_representante", JSON.stringify(s));
                                                  }
                                                }}
                                                style={{
                                                  width: "100%", padding: "9px 13px",
                                                  border: "2px solid " + (ativo ? cor : "#e8eaed"),
                                                  borderRadius: ativo ? "9px 9px 0 0" : 9,
                                                  background: ativo ? cor : "#f8f9fa",
                                                  color: ativo ? "#fff" : "#333", fontSize: 13,
                                                  fontWeight: ativo ? 700 : 400, cursor: "pointer", textAlign: "left",
                                                  display: "flex", alignItems: "center", gap: 8, transition: "all .15s",
                                                }}>
                                                <span style={{ width: 16, height: 16, borderRadius: 3, flexShrink: 0, border: "2px solid " + (ativo ? "rgba(255,255,255,.6)" : "#ccc"), background: ativo ? "rgba(255,255,255,.2)" : "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>{ativo ? "✓" : ""}</span>
                                                {op}
                                              </button>
                                              {/* Subtipo expande inline somente para esta reclamada */}
                                              {ativo && (
                                                <div style={{ border: "2px solid " + cor, borderTop: "none", borderRadius: "0 0 9px 9px", padding: "8px 10px", background: "#fff8f2", marginBottom: 2 }}>
                                                  <div style={{ fontSize: 11, color: cor, fontWeight: 700, marginBottom: 5 }}>Você é nesta reclamada? *</div>
                                                  {["Sócio(a)", "Preposto(a)", "Próprio(a) reclamado(a) — pessoa física"].map((tipo) => {
                                                    const sel = subtipoValor === tipo;
                                                    return (
                                                      <button key={tipo} type="button"
                                                        onClick={() => setSubtipoRec(op, tipo)}
                                                        style={{ display: "block", width: "100%", marginBottom: 3, padding: "7px 10px", border: "2px solid " + (sel ? cor : "#e8eaed"), borderRadius: 7, background: sel ? cor : "#fff", color: sel ? "#fff" : "#333", fontSize: 12, fontWeight: sel ? 700 : 400, cursor: "pointer", textAlign: "left", transition: "all .15s" }}>
                                                        {tipo}
                                                      </button>
                                                    );
                                                  })}
                                                  {grupoErrs[idx + "_subtipo"] && !subtipoValor && (
                                                    <span style={{ color: "#e74c3c", fontSize: 11 }}>Selecione uma opção</span>
                                                  )}
                                                </div>
                                              )}
                                            </div>
                                          );
                                        })}
                                        {grupoErrs[idx + "_rep"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_rep"]}</span>}
                                      </div>
                                    );
                                  })()}
                                </>
                              )}
                            </div>
                          )}
                          <div style={{ marginBottom: 10 }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>Nome do(a) representante *</label>
                            <input value={item.nome} onChange={(e) => setGrupoField(idx, "nome", e.target.value)}
                              placeholder="Nome completo"
                              style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_nome"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                            {grupoErrs[idx + "_nome"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_nome"]}</span>}
                          </div>
                        </>
                      )}

                      {isTestG && (
                        <>
                          {item.papel === "Testemunha do(a) Reclamado(a)" && rdosGrupo.length > 0 && (
                            <div style={{ marginBottom: 10 }}>
                              {rdosGrupo.length === 1 ? (
                                <div style={{ background: "#fff8f2", border: "1px solid #fdba74", borderRadius: 8, padding: "7px 10px", fontSize: 12, color: "#92400e" }}>
                                  Testemunha de: <strong>{rdosGrupo[0]}</strong>
                                </div>
                              ) : (
                                <>
                                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 6 }}>Testemunha de qual(is) reclamada(s)?</label>
                                  <BotoesMultiSelecao opcoes={rdosGrupo} valores={item.parteOuvinte || ""}
                                    onToggle={(v: string) => {
                                      if (v.startsWith("__outro__:")) {
                                        const txt = v.slice(10);
                                        const daLista = (item.parteOuvinte || "").split(" | ").filter((s: string) => rdosGrupo.includes(s));
                                        setGrupoField(idx, "parteOuvinte", [...daLista, ...(txt ? [txt] : [])].join(" | "));
                                      } else {
                                        const atuais = (item.parteOuvinte || "").split(" | ").filter(Boolean);
                                        const novo = atuais.includes(v) ? atuais.filter((s: string) => s !== v) : [...atuais, v];
                                        setGrupoField(idx, "parteOuvinte", novo.join(" | "));
                                      }
                                    }}
                                    erro={null} cor={COR_RDO} />
                                </>
                              )}
                            </div>
                          )}
                          <div style={{ marginBottom: 10 }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>Nome completo *</label>
                            <input value={item.nome} onChange={(e) => setGrupoField(idx, "nome", e.target.value)}
                              placeholder="Nome completo"
                              style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_nome"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                            {grupoErrs[idx + "_nome"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_nome"]}</span>}
                          </div>
                          <div style={{ marginBottom: 10 }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>CPF *</label>
                            <input value={item.cpf} onChange={(e) => setGrupoField(idx, "cpf", fCPF(e.target.value))}
                              placeholder="000.000.000-00" maxLength={14} inputMode="numeric"
                              style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_cpf"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                            {grupoErrs[idx + "_cpf"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_cpf"]}</span>}
                          </div>
                          <div style={{ marginBottom: 10 }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>CEP *</label>
                            <input value={item.cep}
                              onChange={(e) => { const v = fCEP(e.target.value); setGrupoField(idx, "cep", v); if (v.replace(/\D/g, "").length === 8) buscarCEPGrupo(idx, v); }}
                              placeholder="00000-000" maxLength={9} inputMode="numeric"
                              style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_cep"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                            {grupoErrs[idx + "_cep"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_cep"]}</span>}
                          </div>
                          <div style={{ marginBottom: 10 }}>
                            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>Endereço *</label>
                            <input value={item.endereco} onChange={(e) => setGrupoField(idx, "endereco", e.target.value)}
                              placeholder="Rua, bairro, cidade..."
                              style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_endereco"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                            {grupoErrs[idx + "_endereco"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_endereco"]}</span>}
                          </div>
                          <div style={{ display: "flex", gap: 8, marginBottom: 4 }}>
                            <div style={{ flex: "0 0 100px" }}>
                              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>Número *</label>
                              <input value={item.numero} onChange={(e) => setGrupoField(idx, "numero", e.target.value)}
                                placeholder="123"
                                style={{ width: "100%", padding: "9px 11px", border: grupoErrs[idx + "_numero"] ? "2px solid #e74c3c" : "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                              {grupoErrs[idx + "_numero"] && <span style={{ color: "#e74c3c", fontSize: 11 }}>{grupoErrs[idx + "_numero"]}</span>}
                            </div>
                            <div style={{ flex: 1 }}>
                              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#444", marginBottom: 3 }}>Complemento</label>
                              <input value={item.complemento} onChange={(e) => setGrupoField(idx, "complemento", e.target.value)}
                                placeholder="Apto..." style={{ width: "100%", padding: "9px 11px", border: "1.5px solid #ddd", borderRadius: 7, fontSize: 13, boxSizing: "border-box" }} />
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Botões para adicionar participantes */}
            {(() => {
              const ehRec = papel === "Advogado(a) do(a) Reclamante";
              const tipoTest = ehRec ? "Testemunha do(a) Reclamante" : "Testemunha do(a) Reclamado(a)";
              const qtdTest = grupo.filter((g: any) => g.papel === tipoTest).length;
              const qtdRep = grupo.filter((g: any) => g.papel === "Representante do(a) Reclamado(a)").length;
              return (
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                  {!ehRec && qtdRep < Math.max(rdosGrupo.length, 1) && (
                    <button onClick={addRepresentante}
                      style={{ width: "100%", background: "#fff5ee", color: COR_RDO, border: "2px dashed " + COR_RDO + "88", borderRadius: 10, padding: "11px", fontSize: 13, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                      + Adicionar representante {qtdRep > 0 ? `(${qtdRep})` : ""}
                    </button>
                  )}
                  {qtdTest < 3 && (
                    <button onClick={() => addTestemunha(tipoTest, dadosAdvogado)}
                      style={{ width: "100%", background: "#f0f4ff", color: "#1a3a6b", border: "2px dashed #c7d2fe", borderRadius: 10, padding: "11px", fontSize: 13, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                      + Adicionar testemunha {ehRec ? "do(a) reclamante" : "do(a) reclamado(a)"} {qtdTest > 0 ? `(${qtdTest}/3)` : ""}
                    </button>
                  )}
                </div>
              );
            })()}
            <div style={{ background: "#fff8e1", border: "1px solid #ffe082", borderRadius: 8, padding: 9, fontSize: 12, color: "#856404", marginBottom: 14, lineHeight: 1.5 }}>
              Os dados serão pré-registrados para agilizar a ata. A presença oficial é confirmada pelo(a) juiz(a).
            </div>
            <button
              onClick={submeterGrupo}
              disabled={submetendo}
              style={{
                width: "100%", background: submetendo ? "#bdc3c7" : "#27ae60",
                color: "#fff", border: "none", borderRadius: 9, padding: "14px",
                fontSize: 15, fontWeight: 700, cursor: submetendo ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              }}
            >
              {submetendo ? <><Spinner size={18} color="#fff" /> Registrando...</> : "Confirmar check-in do grupo"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ── TELA DE CONFIRMAÇÃO ──
function Aguarde({ nome, papel, processo, info, onNovo }: any) {
  const [cnt, setCnt] = useState(RETORNO_SEG);
  const onNovoRef = useRef(onNovo);
  useEffect(() => { onNovoRef.current = onNovo; });
  useEffect(() => {
    const id = setInterval(() => setCnt((c) => { if (c <= 1) { onNovoRef.current(); return RETORNO_SEG; } return c - 1; }), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg,#0d2b5e,#1a5276)",
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", fontFamily: "'Segoe UI',sans-serif", padding: 20,
    }}>
      <GlobalStyle />
      <div style={{
        background: "#fff", borderRadius: 20, padding: 30, maxWidth: 380, width: "100%",
        boxShadow: "0 20px 60px rgba(0,0,0,.3)", textAlign: "center",
        animation: "fadeInUp .4s ease", position: "relative",
      }}>
        {/* botão fechar */}
        <button
          onClick={onNovo}
          title="Fechar"
          onMouseEnter={(e: any) => { e.currentTarget.style.background = "#e0e4ea"; e.currentTarget.style.color = "#333"; }}
          onMouseLeave={(e: any) => { e.currentTarget.style.background = "#eef0f3"; e.currentTarget.style.color = "#666"; }}
          style={{
            position: "absolute", top: 14, right: 14,
            background: "#eef0f3", border: "1.5px solid #ddd", borderRadius: "50%",
            width: 34, height: 34, cursor: "pointer", fontSize: 18, color: "#666",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 700, lineHeight: 1, zIndex: 10,
            boxShadow: "0 1px 4px rgba(0,0,0,.12)", transition: "all .15s",
          }}
        >✕</button>
        {/* ícone animado */}
        <div style={{
          width: 70, height: 70, background: "linear-gradient(135deg,#27ae60,#1e8449)",
          borderRadius: "50%", display: "flex", alignItems: "center",
          justifyContent: "center", margin: "0 auto 18px",
          boxShadow: "0 6px 20px rgba(39,174,96,.45)",
          animation: "checkPop .5s ease",
        }}>
          <span style={{ color: "#fff", fontSize: 32, fontWeight: 900 }}>✓</span>
        </div>
        <h2 style={{ margin: "0 0 6px", color: "#1a3a6b", fontSize: 20 }}>Check-in realizado!</h2>
        <p style={{ margin: "0 0 4px", fontSize: 16, color: "#333", fontWeight: 700 }}>{nome}</p>
        <p style={{ margin: "0 0 18px", fontSize: 13, color: "#888" }}>{PLABEL[papel] || papel}</p>
        <div style={{ background: "#f0f4ff", borderRadius: 10, padding: 13, marginBottom: 14, fontSize: 13, color: "#555", lineHeight: 1.6 }}>
          <div style={{ fontFamily: "monospace", fontSize: 11, color: "#999", marginBottom: 4 }}>{processo}</div>
          <div style={{ fontWeight: 900, fontSize: 20, color: "#1a3a6b", fontFamily: "monospace" }}>{info?.hora}</div>
        </div>
        <div style={{ background: "#e8f4fd", border: "1px solid #bde0f7", borderRadius: 10, padding: 12, marginBottom: 18, fontSize: 13, color: "#1a5276" }}>
          {info?.tipo === "videoconferência"
            ? "🖥 Entre no Zoom e aguarde o horário da audiência."
            : "🪑 Aguarde na sala de espera. Você será chamado quando a audiência iniciar."}
        </div>
        {/* barra de progresso do timer */}
        <div style={{ background: "#eee", borderRadius: 10, height: 4, marginBottom: 8, overflow: "hidden" }}>
          <div style={{
            height: "100%", background: "#1a3a6b", borderRadius: 10,
            width: (cnt / RETORNO_SEG * 100) + "%", transition: "width 1s linear",
          }} />
        </div>
        <div style={{ fontSize: 11, color: "#bbb", marginBottom: 14 }}>
          Esta tela fechará automaticamente em {cnt}s — você pode fechar agora
        </div>
        <button onClick={onNovo} style={{
          background: "#f0f0f0", color: "#555", border: "none", borderRadius: 9,
          padding: "10px 24px", fontSize: 13, cursor: "pointer", fontWeight: 600,
        }}>
          Novo check-in
        </button>
      </div>
    </div>
  );
}

// ── TELA DE ENTRADA ──
function Entrada({ onValidar, onPainel, onJuiz, parts, procs }: any) {
  const [bProc, setBProc] = useState("");
  const [bHora, setBHora] = useState("");
  const [res, setRes] = useState<any>(null);
  const [erro, setErro] = useState("");
  const [modo, setModo] = useState("hora");
  const [buscando, setBuscando] = useState(false);

  const maskProc = (v: string) => {
    const d = v.replace(/\D/g, "").slice(0, 9);
    return d.length > 7 ? d.slice(0, 7) + "-" + d.slice(7) : d;
  };

  const buscar = () => {
    setErro(""); setRes(null);
    if (!Object.keys(procs).length) { setErro("Nenhuma audiência cadastrada. O(A) Secretário(a) precisa importar a pauta primeiro."); return; }
    setBuscando(true);
    setTimeout(() => {
      if (modo === "proc") {
        const dp = bProc.replace(/\D/g, "");
        if (!dp) { setErro("Digite o número do processo."); setBuscando(false); return; }
        if (dp.length < 9) { setErro("Digite os 9 primeiros números do processo (ex: 1002269-67)."); setBuscando(false); return; }
        const found = Object.entries(procs).filter(([num, info]: any) => !info.encerrada && num.replace(/\D/g, "").startsWith(dp));
        setRes(found.length ? found : []);
      } else {
        const h = bHora.replace(/\D/g, "");
        if (h.length < 3) { setErro("Digite o horário (ex: 09:05)."); setBuscando(false); return; }
        const hFmt = h.slice(0, 2) + ":" + h.slice(2, 4);
        const found = Object.entries(procs).filter(([, info]: any) => !info.encerrada && info.hora === hFmt);
        setRes(found.length ? found : []);
      }
      setBuscando(false);
    }, 300);
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(160deg,#0d2b5e,#1a5276,#2980b9)",
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: "20px 14px", fontFamily: "'Segoe UI',sans-serif",
    }}>
      <GlobalStyle />
      {/* header */}
      <div style={{ textAlign: "center", marginBottom: 20, color: "#fff", animation: "fadeInUp .4s ease" }}>
        <h1 style={{ margin: 0, fontSize: 30, fontWeight: 900, letterSpacing: 1 }}>AudiCheck</h1>
        <p style={{ margin: "4px 0 0", opacity: 0.8, fontSize: 13 }}>
          Check-in de Audiências — TRT 2ª Região
        </p>
        <p style={{ margin: "2px 0 0", opacity: 0.55, fontSize: 12 }}>
          3ª Vara do Trabalho da Zona Sul — São Paulo/SP
        </p>
      </div>

      <div style={{
        width: "100%", maxWidth: 420, background: "#fff", borderRadius: 18,
        padding: "22px 20px", boxShadow: "0 16px 48px rgba(0,0,0,.28)",
        animation: "fadeInUp .45s ease",
      }}>
        <h3 style={{ margin: "0 0 4px", color: "#1a3a6b", fontSize: 16 }}>
          Encontrar minha audiência
        </h3>
        <p style={{ margin: "0 0 14px", fontSize: 13, color: "#888", lineHeight: 1.5 }}>
          Busque pelo número do processo ou pelo horário da audiência.
        </p>

        {!Object.keys(procs).length && (
          <div style={{ background: "#fff3cd", border: "1px solid #ffc107", borderRadius: 9, padding: 11, fontSize: 12, color: "#856404", marginBottom: 14, textAlign: "center" }}>
            ⚠ Nenhuma audiência cadastrada. O(A) Secretário(a) precisa importar a pauta primeiro.
          </div>
        )}

        {/* abas */}
        <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
          {[["hora", "Horário"], ["proc", "Nº do Processo"]].map(([id, lb]) => (
            <button key={id} onClick={() => { setModo(id); setRes(null); setErro(""); }}
              style={{
                flex: 1, padding: "10px", border: "none", borderRadius: 9,
                background: modo === id ? "#1a3a6b" : "#f0f4f8",
                color: modo === id ? "#fff" : "#555",
                fontWeight: modo === id ? 700 : 400, fontSize: 13, cursor: "pointer",
                transition: "all .2s",
              }}
            >
              {lb}
            </button>
          ))}
        </div>

        {modo === "proc" && (
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#444", marginBottom: 4 }}>
              9 primeiros números do processo <span style={{ color: "#aaa", fontWeight: 400 }}>(ex: 1002269-67)</span>
            </label>
            <input
              value={bProc}
              onChange={(e) => { setBProc(maskProc(e.target.value)); setRes(null); setErro(""); }}
              onKeyDown={(e) => e.key === "Enter" && buscar()}
              inputMode="numeric"
              placeholder="1002269-67"
              style={{ width: "100%", padding: "12px 14px", border: "1.5px solid #ddd", borderRadius: 9, fontSize: 15, boxSizing: "border-box", fontFamily: "monospace", letterSpacing: 1 }}
            />
          </div>
        )}

        {modo === "hora" && (
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#444", marginBottom: 6 }}>
              Selecione o horário da audiência
            </label>
            {Object.keys(procs).length === 0 && <div style={{ fontSize: 13, color: "#aaa" }}>Nenhuma audiência cadastrada.</div>}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {[...new Set(
                Object.entries(procs)
                  .filter(([, info]: any) => !info.encerrada)
                  .map(([, info]: any) => info.hora)
                  .filter(Boolean)
              )].sort().map((h: any) => (
                <button key={h} onClick={() => { setBHora(h); setRes(null); setErro(""); }}
                  style={{
                    padding: "10px 18px", border: "2px solid " + (bHora === h ? "#1a3a6b" : "#dce3ed"),
                    borderRadius: 9, background: bHora === h ? "#1a3a6b" : "#f8f9fa",
                    color: bHora === h ? "#fff" : "#333", fontFamily: "monospace",
                    fontWeight: bHora === h ? 700 : 400, fontSize: 15, cursor: "pointer",
                    transition: "all .15s",
                  }}
                >
                  {h}
                </button>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={buscar}
          disabled={buscando}
          style={{
            width: "100%", background: buscando ? "#bdc3c7" : "#1a3a6b", color: "#fff",
            border: "none", borderRadius: 9, padding: "13px", fontSize: 15,
            fontWeight: 700, cursor: buscando ? "not-allowed" : "pointer",
            marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            transition: "background .2s",
          }}
        >
          {buscando ? <><Spinner size={18} color="#fff" /> Buscando...</> : "Buscar audiência"}
        </button>

        {erro && (
          <div style={{ color: "#e74c3c", fontSize: 12, marginBottom: 10, background: "#fdecea", padding: "8px 10px", borderRadius: 7 }}>
            {erro}
          </div>
        )}

        {res !== null && !res.length && (
          <div style={{ background: "#fdecea", border: "1px solid #f5c6cb", borderRadius: 9, padding: 13, fontSize: 13, color: "#c62828", marginBottom: 12, textAlign: "center" }}>
            Audiência não encontrada. Consulte a Secretaria.
          </div>
        )}

        {res?.length > 0 && (
          <div style={{ marginBottom: 12, animation: "fadeInUp .25s ease" }}>
            {res.map(([p, info]: any) => (
              <div key={p} style={{ background: "#f0f4ff", border: "1.5px solid #c7d2fe", borderRadius: 11, padding: 14, marginBottom: 8 }}>
                <div style={{ fontFamily: "monospace", fontSize: 11, color: "#888", marginBottom: 3 }}>{p}</div>
                <div style={{ fontWeight: 900, fontSize: 24, color: "#1a3a6b", fontFamily: "monospace", marginBottom: 2 }}>{info.hora}</div>
                {info.partes && <div style={{ fontSize: 13, color: "#333", marginBottom: 8, lineHeight: 1.4 }}>{info.partes}</div>}
                <div style={{ fontSize: 12, color: "#888", marginBottom: 11 }}>{info.data}{info.tipoAud ? " — " + info.tipoAud : ""}</div>
                <button
                  onClick={() => onValidar(p, info)}
                  style={{ width: "100%", background: "#27ae60", color: "#fff", border: "none", borderRadius: 9, padding: "12px", fontSize: 14, fontWeight: 700, cursor: "pointer" }}
                >
                  Fazer check-in →
                </button>
              </div>
            ))}
          </div>
        )}

        <div style={{ borderTop: "1px solid #f0f0f0", paddingTop: 12 }}>
          <div style={{ fontSize: 11, color: "#bbb", textAlign: "center", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Acesso restrito</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <button onClick={onPainel} style={{ background: "rgba(26,58,107,.06)", color: "#1a3a6b", border: "1.5px solid #1a3a6b", borderRadius: 9, padding: "11px 8px", fontSize: 12, fontWeight: 700, cursor: "pointer", textAlign: "center" }}>
              <div>Secretário(a)</div>
              <div style={{ fontSize: 10, fontWeight: 400, opacity: 0.7, marginTop: 2 }}>Painel de check-ins</div>
            </button>
            <button onClick={onJuiz} style={{ background: "rgba(44,22,84,.06)", color: "#2c1654", border: "1.5px solid #4a2580", borderRadius: 9, padding: "11px 8px", fontSize: 12, fontWeight: 700, cursor: "pointer", textAlign: "center" }}>
              <div>Juiz(a)</div>
              <div style={{ fontSize: 10, fontWeight: 400, opacity: 0.7, marginTop: 2 }}>Propostas de acordo</div>
            </button>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 16, color: "rgba(255,255,255,.3)", fontSize: 10, textAlign: "center", lineHeight: 1.8 }}>
        Desenvolvido por Andrei Boareto Coimbra<br />
        3ª VT Zona Sul — TRT 2ª Região — Claude (Anthropic) — 2026
      </div>
    </div>
  );
}

// ── APP ──
export default function App() {
  const [tela, setTela] = useState("entrada");
  const [proc, setProc] = useState("");
  const [info, setInfo] = useState<any>(null);
  const [parts, setParts] = useState<any[]>([]);
  const [procs, setProcs] = useState<any>({});
  const [uNome, setUNome] = useState("");
  const [uPapel, setUPapel] = useState("");
  const [uProc, setUProc] = useState("");
  const [uInfo, setUInfo] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
    const [loadStep, setLoadStep] = useState("Conectando ao servidor...");
    const salvandoRef = useRef(false);
    const [gpsOk, setGpsOk] = useState(false);

    const telasComPolling = ["entrada", "painel", "juiz"];

  const carregar = useCallback(async () => {
    if (salvandoRef.current) return;
    try {
      setLoadStep("Carregando audiências...");
      const [ps, cs] = await Promise.all([dbGetProcessos(), dbGetCheckins()]);
        if (salvandoRef.current) return;
      if (ps) {
        const obj: any = {};
        ps.forEach((p: any) => {
          obj[p.id] = {
            data: p.data, hora: p.hora, partes: p.partes,
            tipo: p.tipo, tipoAud: p.tipo_aud, encerrada: p.encerrada,
            forumLat: FORUM.lat, forumLng: FORUM.lng,
          };
        });
        setProcs(obj);
      }
      if (cs) setParts(cs);
      setLoadStep("Pronto!");
    } catch (e) {
      console.error("Erro ao carregar:", e);
      setLoadStep("Erro de conexão. Tentando novamente...");
    }
    setCarregando(false);
  }, []);

  useEffect(() => {
    carregar();
  }, []);

    useEffect(() => {
    if (!telasComPolling.includes(tela)) return;
    let id: any = null;
    const iniciar = () => { if (!document.hidden) id = setInterval(carregar, 8000); };
    const pausar = () => { if (id) { clearInterval(id); id = null; } };
    const onVisibility = () => document.hidden ? pausar() : (pausar(), iniciar());
    iniciar();
    document.addEventListener("visibilitychange", onVisibility);
    return () => { pausar(); document.removeEventListener("visibilitychange", onVisibility); };
  }, [tela, carregar]);

    useEffect(() => {
    if (carregando) return;
    const p = new URLSearchParams(window.location.search).get("proc");
    if (!p) return;
    const encontrado = Object.entries(procs).find(
      ([num]: any) =>
        num === p || num.replace(/\D/g, "") === p.replace(/\D/g, "")
    );
    if (encontrado) {
      const [num, inf]: any = encontrado;
      // Limpa o param da URL sem recarregar
      window.history.replaceState({}, "", window.location.pathname);
      if ((inf as any).encerrada) {
        const t = document.createElement("div");
        t.textContent = "Esta audiência já foi encerrada. Dirija-se à Secretaria.";
        Object.assign(t.style, { position:"fixed", top:"50%", right:"16px", transform:"translateY(-50%)", background:"#c62828", color:"#fff", borderRadius:"14px", padding:"16px 22px", fontSize:"14px", fontWeight:"700", zIndex:"9999", fontFamily:"'Segoe UI',sans-serif", boxShadow:"0 8px 30px rgba(0,0,0,.3)" });
        document.body.appendChild(t); setTimeout(() => t.remove(), 4000);
        return;
      }
      setProc(num);
      setInfo(inf);
      setTela("lgpd");
    }
  }, [carregando, procs]);

    const cpfsUsados = parts
    .filter((p: any) => p.processo_id === proc || p.processo === proc)
    .map((p: any) => p.cpf?.replace(/\D/g, "") || "")
    .filter(Boolean);

  const setPS = async (u: any) => {
    salvandoRef.current = true;
    setProcs(u);
    try {
      await dbSaveProcessos(u);
    } finally {
      salvandoRef.current = false;
    }
  };

  const sub = async (d: any, modoGrupo = false, fimGrupo = false) => {
    if (fimGrupo) {
      setUNome("Grupo registrado");
      setUPapel("Check-in em grupo");
      setUProc(proc);
      setUInfo(info);
      setTela("aguarde");
      return;
    }
    if (!d) return;

    const papeisSemCpf = ["Parte Reclamante", "Parte Reclamada", "Representante do(a) Reclamado(a)", "Representante do(a) Reclamante"];
    if (papeisSemCpf.includes(d.papel)) {
      const nomeNorm = (d.nome || "").trim().toLowerCase();
      const jaRegistrado = parts.some(
        (p: any) =>
          (p.processo_id === proc || p.processo === proc) &&
          p.papel === d.papel &&
          (p.nome || "").trim().toLowerCase() === nomeNorm
      );
      if (jaRegistrado) {
        const toastEl = document.createElement("div");
        toastEl.textContent = d.nome + " já fez check-in como " + d.papel + " neste processo.";
        Object.assign(toastEl.style, {
          position: "fixed", top: "50%", right: "16px", transform: "translateY(-50%)",
          background: "#e65100", color: "#fff", borderRadius: "14px",
          padding: "18px 24px", fontSize: "15px", fontWeight: "700",
          zIndex: "9999", maxWidth: "340px", lineHeight: "1.5",
          fontFamily: "'Segoe UI', sans-serif", boxShadow: "0 12px 40px rgba(0,0,0,.35)",
        });
        document.body.appendChild(toastEl);
        setTimeout(() => toastEl.remove(), 4000);
        return;
      }
    }
    const checkin = {
      processo_id: proc,
      nome: d.nome,
      papel: d.papel,
      cpf: d.cpf || null,
      oab: d.oab || null,
      hora: d.hora || now(),
      modalidade: d.modalidade || (info?.tipo === "videoconferência" ? "virtual" : "presencial"),
      endereco: d.endereco || null,
      cep: d.cep || null,
      numero: d.numero || null,
      complemento: d.complemento || null,
      parte_representada: d.parteRepresentada || null,
      empresa_representada: d.empresaRepresentada || null,
      regularizacao: d.regularizacao || null,
      parteOuvinte: d.parteOuvinte || null,
      subtipo_representante: d.subtipo_representante || null,
      proposta: d.proposta || null,
    };
    try {
      const resultado = await dbSaveCheckin(checkin);
        const checkinFinal = resultado?.hora
        ? { ...checkin, hora: resultado.hora, processo: proc,
            subtipo_representante: resultado.subtipo_representante || checkin.subtipo_representante,
            parte_ouvinte: resultado.parte_ouvinte || checkin.parteOuvinte,
            proposta: resultado.proposta || checkin.proposta }
        : { ...checkin, processo: proc,
            subtipo_representante: checkin.subtipo_representante,
            parte_ouvinte: checkin.parteOuvinte || null,
            proposta: checkin.proposta };
      setParts((prev: any) => [...prev, checkinFinal]);
      if (!modoGrupo) {
        setUNome(d.nome);
        setUPapel(d.papel);
        setUProc(proc);
        setUInfo(info);
        setTela("aguarde");
      }
    } catch (e: any) {
      // Toast de erro — mais elegante que alert
      const toastEl = document.createElement("div");
      toastEl.textContent = "Erro ao registrar check-in. Verifique a conexão e tente novamente.";
      Object.assign(toastEl.style, {
        position: "fixed", top: "50%", right: "16px", transform: "translateY(-50%)",
        background: "#c62828", color: "#fff", borderRadius: "14px",
        padding: "18px 24px", fontSize: "15px", fontWeight: "700",
        zIndex: "9999", maxWidth: "340px", lineHeight: "1.5",
        fontFamily: "'Segoe UI', sans-serif", boxShadow: "0 12px 40px rgba(0,0,0,.35)",
        animation: "fadeIn .25s ease",
      });
      document.body.appendChild(toastEl);
      setTimeout(() => toastEl.remove(), 4000);
    }
  };

  // ── TELA DE CARREGAMENTO ──
  if (carregando)
    return (
      <div style={{
        minHeight: "100vh",
        background: "linear-gradient(160deg,#0d2b5e,#1a5276,#2980b9)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "'Segoe UI',sans-serif",
      }}>
        <GlobalStyle />
        <div style={{ textAlign: "center", color: "#fff", animation: "fadeIn .5s ease" }}>
          <div style={{ fontSize: 32, fontWeight: 900, letterSpacing: 1, marginBottom: 8 }}>AudiCheck</div>
          <div style={{ marginBottom: 24, opacity: 0.7, fontSize: 13 }}>TRT 2ª Região — 3ª VT Zona Sul</div>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 18 }}>
            <Spinner size={36} color="#fff" />
          </div>
          <div style={{ fontSize: 13, opacity: 0.65, animation: "fadeIn .3s ease" }}>{loadStep}</div>
          {/* barrinhas de progresso animadas */}
          <div style={{ display: "flex", gap: 6, justifyContent: "center", marginTop: 20 }}>
            {["Conectando", "Audiências", "Check-ins"].map((label, i) => (
              <div key={label} style={{ textAlign: "center" }}>
                <div style={{
                  width: 60, height: 3, borderRadius: 3,
                  background: loadStep.includes("Pronto") || i === 0
                    ? "rgba(255,255,255,.9)"
                    : loadStep.includes("Carregando") && i <= 1
                      ? "rgba(255,255,255,.9)"
                      : "rgba(255,255,255,.25)",
                  transition: "background .5s",
                }} />
                <div style={{ fontSize: 9, opacity: 0.5, marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );

  if (tela === "login") return <Login onLogin={() => setTela("painel")} onVoltar={() => setTela("entrada")} />;
  if (tela === "login-juiz") return <Login onLogin={() => setTela("juiz")} onVoltar={() => setTela("entrada")} titulo="Juiz(a)" cor="#4a2580" />;
  if (tela === "juiz")
    return <PJuiz parts={parts} procs={procs} onVoltar={() => setTela("entrada")} onCarregar={carregar} />;
  if (tela === "painel")
    return (
      <PSec
        parts={parts} procs={procs} setProcs={setPS} setParts={setParts}
        onLimpar={async () => { await dbLimpar(); setProcs({}); setParts([]); }}
        onEncerrar={async (p: string) => {
          await dbEncerrar(p);
          setProcs((prev: any) => ({ ...prev, [p]: { ...prev[p], encerrada: true } }));
          setParts((prev: any) => prev.filter((c: any) => (c.processo_id || c.processo) !== p));
        }}
        onVoltar={() => setTela("entrada")}
      />
    );
  if (tela === "lgpd") return <LGPD onAc={() => setTela("gps")} onRec={() => setTela("recusou")} onVoltar={() => { setGpsOk(false); setTela("entrada"); }} />;
  if (tela === "gps") return <GPS info={info} jaValidou={gpsOk} onOk={() => { setGpsOk(true); setTela("form"); }} onVoltar={() => setTela("lgpd")} />;
  if (tela === "form")
    return <Form processo={proc} info={info} onVoltar={() => setTela(info?.tipo === "videoconferência" ? "entrada" : "gps")} onSubmit={sub} cpfsUsados={cpfsUsados} grupoHabilitado={getGrupoHabilitado()} />;
  if (tela === "aguarde")
    return <Aguarde nome={uNome} papel={uPapel} processo={uProc} info={uInfo} onNovo={() => setTela("entrada")} />;
  if (tela === "recusou")
    return (
      <div style={{
        minHeight: "100vh",
        background: "linear-gradient(160deg,#0d2b5e,#1a5276)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "'Segoe UI',sans-serif", padding: 16,
      }}>
        <GlobalStyle />
        <div style={{ background: "#fff", borderRadius: 16, padding: 30, maxWidth: 320, textAlign: "center", animation: "fadeInUp .35s ease" }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🚫</div>
          <h2 style={{ color: "#1a3a6b", margin: "0 0 10px" }}>Check-in não realizado</h2>
          <p style={{ color: "#555", fontSize: 14, lineHeight: 1.7, margin: "0 0 22px" }}>
            Dirija-se à Secretaria para identificação presencial.
          </p>
          <button
            onClick={() => setTela("entrada")}
            style={{ background: "#1a3a6b", color: "#fff", border: "none", borderRadius: 9, padding: "12px 28px", fontSize: 14, fontWeight: 700, cursor: "pointer" }}
          >
            Voltar
          </button>
        </div>
      </div>
    );

  return (
    <Entrada
      onValidar={(p: any, i: any) => { setProc(p); setInfo(i); setGpsOk(false); setTela("lgpd"); }}
      onPainel={() => setTela("login")}
      onJuiz={() => setTela("login-juiz")}
      parts={parts}
      procs={procs}
    />
  );
}
