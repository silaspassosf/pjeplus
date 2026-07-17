import logging
from typing import List
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)

class AtividadePEC:
    def __init__(self, numero_processo, observacao, status, data_prazo, tipo_gigs, id_processo=None):
        self.numero_processo = numero_processo
        self.id_processo = id_processo
        self.observacao = observacao
        self.status = status
        self.data_prazo = data_prazo
        self.tipo_gigs = tipo_gigs

class PECAPIClient:
    def fetch_atividades_vencidas(self, driver: WebDriver, tamanho_pagina: int = 100) -> List[AtividadePEC]:
        """
        Busca GIGS vencidos via execute_async_script (API REST real do PJe).
        """
        print("[PECAPIClient] Iniciando fetch_atividades_vencidas (API REST real)...")
        JS = f'''
const callback = arguments[0];
const rawCookie = document.cookie.split(';')
    .map(c => c.trim())
    .find(c => c.toLowerCase().startsWith('xsrf-token='));
const xsrf = rawCookie ? rawCookie.split('=').slice(1).join('=') : null;
if (!xsrf) {{
    callback({{
        erro: 'XSRF_NOT_FOUND',
        href: location.href,
        cookieCount: document.cookie.split(';').filter(c => c.trim()).length,
        resultado: []
    }});
    return;
}}
const base = location.origin;
const params = 'filtrarVencidas=true&ordenacaoCrescente=true'
             + '&filtrarPorDestinatario=false&filtrarPorLocalizacao=false';
const hdrs = {{
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-XSRF-TOKEN': xsrf
}};
(async () => {{
    const getPage = async (pagina) => {{
        const url = `${{base}}/pje-gigs-api/api/relatorioatividades/?${{params}}&pagina=${{pagina}}&tamanhoPagina={tamanho_pagina}`;
        const r = await fetch(url, {{ credentials: 'include', headers: hdrs }});
        if (!r.ok) return {{ erro: r.status, url: url, resultado: [] }};
        return r.json();
    }};
    try {{
        const p1 = await getPage(1);
        if (p1.erro) {{
            callback({{ erro: p1.erro, url: p1.url, xsrfLen: xsrf.length, resultado: [] }});
            return;
        }}
        let todos = [...(p1.resultado || [])];
        const total = p1.qtdPaginas || 1;
        if (total > 1) {{
            const rest = await Promise.all(
                Array.from({{ length: total - 1 }}, (_, i) => getPage(i + 2))
            );
            rest.forEach(p => todos.push(...(p.resultado || [])));
        }}
        callback({{ qtdPaginas: total, totalRegistros: p1.totalRegistros, resultado: todos }});
    }} catch(e) {{
        callback({{ erro: e.message, resultado: [] }});
    }}
}})();
'''
        try:
            driver.set_script_timeout(60)
            resultado = driver.execute_async_script(JS)
        finally:
            try:
                driver.set_script_timeout(30)
            except Exception:
                pass
        if not resultado or resultado.get("erro"):
            erro = (resultado or {{}}).get("erro", "sem_resposta")
            print(f"[PECAPIClient] Erro ao buscar atividades: {erro}")
            if erro == "XSRF_NOT_FOUND":
                print(f"[PECAPIClient] XSRF não encontrado. URL: {resultado.get('href', '?')}")
            else:
                print(f"[PECAPIClient] HTTP erro: {resultado.get('url', '?')} xsrfLen={resultado.get('xsrfLen', '?')}")
            return []
        total = resultado.get("totalRegistros", 0)
        dados = resultado.get("resultado", [])
        print(f"[PECAPIClient] ✅ {len(dados)}/{total} atividades carregadas ({resultado.get('qtdPaginas', 1)} página(s))")
        atividades = [
            AtividadePEC(
                numero_processo=(item.get("processo") or {}).get("numero") or (item.get("processo") or {}).get("numeroProcesso") or "",
                observacao=(item.get("observacao") or "").strip(),
                status=(item.get("statusAtividade") or "").upper(),
                data_prazo=(item.get("dataPrazo") or "")[:10],
                tipo_gigs=(item.get("tipoAtividade") or {}).get("descricao") or (item.get("tipoAtividade") or {}).get("nome") or "",
                id_processo=(item.get("processo") or {}).get("id") or item.get("idProcesso")
            )
            for item in dados
        ]
        print(f"[PECAPIClient] Total de atividades parseadas: {len(atividades)}")
        if atividades:
            print(f"[PECAPIClient] Exemplo: {vars(atividades[0])}")
        return atividades
