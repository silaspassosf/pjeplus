# -*- coding: utf-8 -*-
"""Laboratorio WebDriver BiDi sobre Firefox Developer Edition (headless/visivel).

Espelha o ambiente real do PJePlus: Firefox Developer Edition com extensoes
+PJe (maisPJe) e Tampermonkey instaladas no perfil persistente dedicado,
auto-login via Windows Credential Manager (CPF/senha + TOTP opcional).

Uso:
  py tools/cdp_lab.py abrir [--headless] [--porta 9222] [--url URL]
  py tools/cdp_lab.py headless [--porta 9222]
  py tools/cdp_lab.py status
  py tools/cdp_lab.py goto <url> [--aba pje.trt2.jus.br]
  py tools/cdp_lab.py dom "<seletor>" [--limite 5] [--html] [--aba pje.trt2.jus.br]
  py tools/cdp_lab.py eval "<js>" [--aba pje.trt2.jus.br]
  py tools/cdp_lab.py inject <arquivo.js> [--aba pje.trt2.jus.br]
  py tools/cdp_lab.py fechar
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

PORTA_PADRAO = 9222
URL_LOGIN_PJE = "https://pje.trt2.jus.br/primeirograu/login.seam"
URL_PAINEL_PJE = "https://pje.trt2.jus.br/pjekz/gigs/meu-painel"
PERFIL_LAB = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PjePlus" / "ff_dev_lab_profile"

EXTENSOES_OBRIGATORIAS = {
    "maisPJe": "{ab473c1e-2002-4db8-b85d-50dab45806b5}.xpi",
    "Tampermonkey": "firefox@tampermonkey.net.xpi",
}


def _esperar(segundos: float) -> None:
    threading.Event().wait(segundos)


def _porta_aberta(porta: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=timeout):
            return True
    except OSError:
        return False


def _encontrar_firefox_dev() -> Optional[str]:
    candidatos = [
        os.environ.get("PJEPLUS_LAB_FIREFOX") or "",
        r"C:\Program Files\Firefox Developer Edition\firefox.exe",
        r"C:\Program Files (x86)\Firefox Developer Edition\firefox.exe",
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        shutil.which("firefox") or "",
    ]
    for c in candidatos:
        if c and os.path.isfile(c):
            return c
    return None


def _preparar_perfil_firefox() -> dict[str, bool]:
    """Garante perfil persistente dedicado com user.js BiDi + extensoes maisPJe e Tampermonkey."""
    PERFIL_LAB.mkdir(parents=True, exist_ok=True)
    ext_dir = PERFIL_LAB / "extensions"
    ext_dir.mkdir(parents=True, exist_ok=True)

    user_js = PERFIL_LAB / "user.js"
    user_js.write_text(
        "\n".join([
            'user_pref("remote.active-protocols", 1);',
            'user_pref("extensions.autoDisableScopes", 0);',
            'user_pref("extensions.enabledScopes", 15);',
            'user_pref("xpinstall.signatures.required", false);',
            'user_pref("dom.webdriver.enabled", false);',
            'user_pref("dom.webnotifications.enabled", false);',
            'user_pref("browser.shell.checkDefaultBrowser", false);',
            'user_pref("browser.startup.homepage_override.mstone", "ignore");',
            'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);',
        ]) + "\n",
        encoding="utf-8",
    )

    perfis_base = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
    instaladas: dict[str, bool] = {}
    for nome, xpi in EXTENSOES_OBRIGATORIAS.items():
        destino = ext_dir / xpi
        if not destino.is_file():
            encontrados = glob.glob(os.path.join(perfis_base, "*", "extensions", xpi))
            if encontrados:
                shutil.copy2(encontrados[0], destino)
        instaladas[nome] = destino.is_file()
    return instaladas


def _decodificar_bidi(obj: Any) -> Any:
    if not isinstance(obj, dict):
        return obj
    tipo = obj.get("type")
    if tipo in ("string", "number", "boolean"):
        return obj.get("value")
    if tipo in ("null", "undefined"):
        return None
    if tipo == "array":
        return [_decodificar_bidi(x) for x in (obj.get("value") or [])]
    if tipo == "object":
        out = {}
        for k, v in (obj.get("value") or []):
            out[str(k)] = _decodificar_bidi(v)
        return out
    return obj.get("value", obj)


class _BiDiClient:
    """Cliente WebDriver BiDi minimalista sobre WebSocket (sem Selenium)."""

    def __init__(self, porta: int = PORTA_PADRAO, timeout: float = 15.0):
        self.porta = porta
        self.timeout = timeout
        self.ws: Any = None
        self._seq = 0
        self.capabilities: dict[str, Any] = {}

    def __enter__(self) -> "_BiDiClient":
        import websocket

        self.ws = websocket.create_connection(
            f"ws://127.0.0.1:{self.porta}/session",
            timeout=self.timeout,
            suppress_origin=True,
        )
        res = self.cmd("session.new", {"capabilities": {}})
        self.capabilities = res.get("capabilities") or {}
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.ws is not None:
            try:
                self.cmd("session.end", {})
            except Exception:
                pass
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    def cmd(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._seq += 1
        req_id = self._seq
        self.ws.send(json.dumps({"id": req_id, "method": method, "params": params}))
        while True:
            raw = self.ws.recv()
            msg = json.loads(raw)
            if msg.get("id") != req_id:
                continue
            if msg.get("type") == "error":
                raise RuntimeError(f"BiDi {method}: {msg.get('error')} - {msg.get('message')}")
            return msg.get("result") or {}

    def contextos(self) -> list[dict[str, str]]:
        res = self.cmd("browsingContext.getTree", {})
        return [
            {"context": c["context"], "url": c.get("url") or ""}
            for c in (res.get("contexts") or [])
        ]

    def selecionar_contexto(self, filtro_aba: str = "pje.trt2.jus.br") -> dict[str, str]:
        ctxs = self.contextos()
        if not ctxs:
            criado = self.cmd("browsingContext.create", {"type": "tab"})
            return {"context": criado["context"], "url": "about:blank"}
        if filtro_aba:
            filtro = filtro_aba.lower()
            for c in reversed(ctxs):
                if filtro in c["url"].lower():
                    return c
        return ctxs[-1]

    def navegar(self, ctx: str, url: str, wait: str = "interactive") -> None:
        self.cmd("browsingContext.navigate", {"context": ctx, "url": url, "wait": wait})

    def eval_js(self, ctx: str, expression: str, await_promise: bool = False) -> Any:
        res = self.cmd(
            "script.evaluate",
            {
                "expression": expression,
                "target": {"context": ctx},
                "awaitPromise": await_promise,
                "resultOwnership": "none",
            },
        )
        if res.get("type") == "exception":
            det = res.get("exceptionDetails") or {}
            raise RuntimeError(f"JS exception: {det.get('text') or det}")
        return _decodificar_bidi(res.get("result"))

    def sessao_oauth_ativa(self) -> bool:
        try:
            res = self.cmd("storage.getCookies", {})
            nomes = {c.get("name") for c in (res.get("cookies") or [])}
            return bool(nomes & {"access_token", "sso_refresh_token"})
        except Exception:
            return False

    def fechar_navegador(self) -> None:
        try:
            self.cmd("browser.close", {})
        except Exception:
            pass


def _iniciar_firefox_dev(porta: int, headless: bool) -> bool:
    exe = _encontrar_firefox_dev()
    if not exe:
        print("ERRO: Firefox Developer Edition nao encontrado. Defina PJEPLUS_LAB_FIREFOX.")
        return False

    ext_status = _preparar_perfil_firefox()
    faltando = [k for k, ok in ext_status.items() if not ok]
    print(f"[LAB] Perfil: {PERFIL_LAB}")
    print(f"[LAB] Extensoes: {', '.join(f'{k}={'OK' if ok else 'AUSENTE'}' for k, ok in ext_status.items())}")
    if faltando:
        print(f"[LAB] AVISO: XPI nao encontrado nos perfis locais para: {', '.join(faltando)}")

    args = [
        exe,
        f"--remote-debugging-port={porta}",
        "-profile",
        str(PERFIL_LAB),
        "--no-remote",
    ]
    if headless:
        args.insert(1, "--headless")

    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )

    for _ in range(60):
        if _porta_aberta(porta):
            _esperar(0.4)
            return True
        _esperar(0.25)
    print(f"ERRO: Firefox Developer Edition nao respondeu na porta BiDi {porta} em 15s.")
    return False


def _carregar_credenciais_pje() -> tuple[Optional[str], Optional[str]]:
    from Fix.sessao import obter_credencial

    cpf = obter_credencial(
        "PJE_CPF",
        servicos=("pjeplus", "pje", "sisbajud", "SISB"),
        aliases=("PJE_USER", "CPF", "PJE_SILAS", "SILAS", "SISB_CPF", "BP_SISB"),
    )
    senha = obter_credencial(
        "PJE_SENHA",
        servicos=("pjeplus", "pje", "sisbajud", "SISB"),
        aliases=("PJE_PASSWORD", "SENHA", "PASSWORD", "SISB_SENHA", "BP_PASS"),
    )
    return cpf, senha


def _aguardar_js(bidi: _BiDiClient, ctx: str, expr: str, timeout_s: float = 15.0) -> Any:
    limite = time.time() + timeout_s
    while time.time() < limite:
        try:
            val = bidi.eval_js(ctx, expr)
            if val:
                return val
        except Exception:
            pass
        _esperar(0.35)
    return None


def _preencher_e_enviar_otp(bidi: _BiDiClient, ctx: str, codigo: str) -> None:
    bidi.eval_js(
        ctx,
        f"""(() => {{
            const inp = document.querySelector('#otp, input[name="otp"]');
            if (!inp) return false;
            inp.focus();
            inp.value = {json.dumps(codigo)};
            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
            const btn = document.querySelector('input[type="submit"], button[type="submit"], #kc-login');
            if (btn) btn.click();
            else if (inp.form) inp.form.submit();
            return true;
        }})()""",
    )


def _fazer_login(bidi: _BiDiClient, ctx: str, url_destino: Optional[str], headless: bool, timeout_otp_s: int) -> bool:
    if bidi.sessao_oauth_ativa():
        print("[LAB] Sessao OAuth ja ativa no perfil.")
        alvo = url_destino or URL_PAINEL_PJE
        cur_url = bidi.eval_js(ctx, "location.href") or ""
        if "/pjekz" not in str(cur_url).lower() or (url_destino and url_destino not in str(cur_url)):
            bidi.navegar(ctx, alvo, wait="interactive")
        # cookie de refresh vencido: o PJe cai em /acesso-negado ou /login sem access_token
        estado_sessao = _aguardar_js(
            bidi, ctx,
            """(() => {
                const u = location.href.toLowerCase();
                if (u.includes('acesso-negado') || u.includes('/login')) return 'expirada';
                if (u.includes('/pjekz') && document.cookie.includes('access_token')) return 'ok';
                return null;
            })()""",
            timeout_s=10,
        )
        if estado_sessao != "expirada":
            return True
        print("[LAB] Sessao expirada (acesso negado) — refazendo login.")

    print(f"[LAB] Abrindo login PJe: {URL_LOGIN_PJE}")
    bidi.navegar(ctx, URL_LOGIN_PJE, wait="complete")

    if _aguardar_js(bidi, ctx, "Boolean(document.querySelector('#btnSsoPdpj'))", timeout_s=8):
        bidi.eval_js(ctx, "document.querySelector('#btnSsoPdpj')?.click()")
        print("[LAB] Botao SSO PDPJ clicado.")

    estado = _aguardar_js(
        bidi,
        ctx,
        """(() => {
            if (location.href.toLowerCase().includes('/pjekz')) return 'pjekz';
            if (document.querySelector('#username')) return 'username';
            if (document.querySelector('#otp, input[name="otp"]')) return 'otp';
            return null;
        })()""",
        timeout_s=15,
    )

    if estado == "username":
        cpf, senha = _carregar_credenciais_pje()
        if cpf and senha:
            bidi.eval_js(
                ctx,
                f"""(() => {{
                    const u = document.querySelector('#username');
                    const p = document.querySelector('#password');
                    if (!u || !p) return false;
                    u.value = {json.dumps(cpf)};
                    u.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    p.value = {json.dumps(senha)};
                    p.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    const btn = document.querySelector('#kc-login');
                    if (btn) btn.click();
                    return true;
                }})()""",
            )
            print("[LAB] CPF e senha preenchidos via Windows Credential Manager.")
        else:
            print("[LAB] PJE_CPF/PJE_SENHA nao encontrados no Windows Credential Manager.")

        estado = _aguardar_js(
            bidi,
            ctx,
            """(() => {
                if (location.href.toLowerCase().includes('/pjekz')) return 'pjekz';
                if (document.querySelector('#otp, input[name="otp"]')) return 'otp';
                return null;
            })()""",
            timeout_s=15,
        )

    if estado == "otp":
        from Fix.sessao import obter_totp_pje

        codigo_auto = obter_totp_pje()
        if codigo_auto:
            print("[LAB] OTP gerado automaticamente via TOTP (Windows Credential Manager).")
            _preencher_e_enviar_otp(bidi, ctx, codigo_auto)
        elif headless:
            codigo = input("\n[LAB] Digite o codigo OTP (6 digitos): ").strip()
            if codigo:
                _preencher_e_enviar_otp(bidi, ctx, codigo)
        else:
            bidi.eval_js(ctx, "document.querySelector('#otp, input[name=\"otp\"]')?.focus()")
            print("[LAB] >>> TELA DE OTP PRONTA! Digite o codigo OTP na janela do Firefox.")

    print(f"[LAB] Aguardando conclusao do login (ate {timeout_otp_s}s)...")
    ok = _aguardar_js(
        bidi,
        ctx,
        "location.href.toLowerCase().includes('/pjekz')",
        timeout_s=timeout_otp_s,
    )
    if not ok:
        cur = bidi.eval_js(ctx, "location.href")
        print(f"[LAB] Timeout aguardando /pjekz/ (url atual: {cur}).")
        return False

    cur = bidi.eval_js(ctx, "location.href")
    print(f"[LAB] Login concluido: {cur}")
    if url_destino and url_destino not in str(cur):
        bidi.navegar(ctx, url_destino, wait="interactive")
    return True


def cmd_abrir(args: argparse.Namespace) -> int:
    if not _porta_aberta(args.porta):
        modo = "HEADLESS" if args.headless else "VISIVEL"
        print(f"[LAB] Iniciando Firefox Developer Edition ({modo}) na porta {args.porta}...")
        if not _iniciar_firefox_dev(args.porta, headless=args.headless):
            return 1
    else:
        print(f"[LAB] Firefox Developer Edition ja ativo na porta {args.porta}.")

    with _BiDiClient(args.porta) as bidi:
        alvo = bidi.selecionar_contexto("pje.trt2.jus.br")
        ok = _fazer_login(bidi, alvo["context"], args.url, args.headless, args.timeout_otp)
        print(f"[LAB] Pronto na porta {args.porta} (Firefox mantido aberto).")
        return 0 if ok else 2


def cmd_headless(args: argparse.Namespace) -> int:
    if _porta_aberta(args.porta):
        print(f"[LAB] Encerrando instancia atual na porta {args.porta} para reiniciar em --headless...")
        try:
            with _BiDiClient(args.porta, timeout=8) as bidi:
                bidi.fechar_navegador()
        except Exception:
            pass
        for _ in range(30):
            if not _porta_aberta(args.porta):
                break
            _esperar(0.25)

    args.headless = True
    args.url = getattr(args, "url", None)
    args.timeout_otp = getattr(args, "timeout_otp", 180)
    return cmd_abrir(args)


def cmd_status(args: argparse.Namespace) -> int:
    if not _porta_aberta(args.porta):
        print(f"[LAB] Inativo na porta {args.porta}. Rode: py tools/cdp_lab.py abrir --headless")
        return 1
    with _BiDiClient(args.porta) as bidi:
        ver = bidi.capabilities.get("browserVersion", "?")
        bname = bidi.capabilities.get("browserName", "firefox")
        ext_dir = PERFIL_LAB / "extensions"
        exts = ", ".join(
            f"{k}={'OK' if (ext_dir / xpi).is_file() else 'AUSENTE'}"
            for k, xpi in EXTENSOES_OBRIGATORIAS.items()
        )
        print(f"[LAB] Ativo ({bname} {ver}) em ws://127.0.0.1:{args.porta} | Extensoes: {exts}")
        for idx, c in enumerate(bidi.contextos()):
            try:
                titulo = str(bidi.eval_js(c["context"], "document.title") or "").strip()[:60]
            except Exception:
                titulo = "?"
            print(f"  [{idx}] {titulo} | {c['url']}")
        return 0


def cmd_goto(args: argparse.Namespace) -> int:
    if not _porta_aberta(args.porta):
        print(f"[LAB] Inativo na porta {args.porta}.")
        return 1
    with _BiDiClient(args.porta) as bidi:
        alvo = bidi.selecionar_contexto(args.aba)
        bidi.navegar(alvo["context"], args.url, wait="interactive")
        print(f"[LAB] Navegado para: {bidi.eval_js(alvo['context'], 'location.href')}")
        return 0


def cmd_dom(args: argparse.Namespace) -> int:
    if not _porta_aberta(args.porta):
        print(f"[LAB] Inativo na porta {args.porta}.")
        return 1
    with _BiDiClient(args.porta) as bidi:
        alvo = bidi.selecionar_contexto(args.aba)
        expr = f"""JSON.stringify((() => {{
            const els = Array.from(document.querySelectorAll({json.dumps(args.seletor)}));
            return {{
                url: location.href,
                total: els.length,
                itens: els.slice(0, {int(args.limite)}).map(el => ({{
                    tag: el.tagName.toLowerCase(),
                    id: el.id || null,
                    classes: typeof el.className === 'string' ? el.className.trim() : null,
                    ariaLabel: el.getAttribute('aria-label'),
                    texto: (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 160),
                    outerHTML: {'el.outerHTML.slice(0, 2000)' if args.html else 'undefined'}
                }}))
            }};
        }})())"""
        raw = bidi.eval_js(alvo["context"], expr)
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
        return 0


def cmd_eval(args: argparse.Namespace) -> int:
    if not _porta_aberta(args.porta):
        print(f"[LAB] Inativo na porta {args.porta}.")
        return 1
    with _BiDiClient(args.porta) as bidi:
        alvo = bidi.selecionar_contexto(args.aba)
        res = bidi.eval_js(alvo["context"], args.codigo, await_promise=args.await_promise)
        url = bidi.eval_js(alvo["context"], "location.href")
        print(json.dumps({"url": url, "resultado": res}, ensure_ascii=False, indent=2, default=str))
        return 0


def cmd_inject(args: argparse.Namespace) -> int:
    caminho = Path(args.arquivo)
    if not caminho.is_file():
        print(f"ERRO: arquivo nao encontrado: {caminho}")
        return 1
    if not _porta_aberta(args.porta):
        print(f"[LAB] Inativo na porta {args.porta}.")
        return 1
    conteudo = caminho.read_text(encoding="utf-8")
    with _BiDiClient(args.porta) as bidi:
        alvo = bidi.selecionar_contexto(args.aba)
        bidi.eval_js(
            alvo["context"],
            f"""(() => {{
                const s = document.createElement('script');
                s.textContent = {json.dumps(conteudo)};
                (document.head || document.documentElement).appendChild(s);
                return true;
            }})()""",
        )
        print(f"[LAB] Injetado {caminho.name} em {bidi.eval_js(alvo['context'], 'location.href')}")
        return 0


def cmd_fechar(args: argparse.Namespace) -> int:
    if not _porta_aberta(args.porta):
        print(f"[LAB] Nenhuma instancia ativa na porta {args.porta}.")
        return 0
    with _BiDiClient(args.porta, timeout=8) as bidi:
        bidi.fechar_navegador()
    print(f"[LAB] Firefox Developer Edition encerrado (porta {args.porta}).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Laboratorio Firefox Developer Edition (WebDriver BiDi + +PJe + Tampermonkey)")
    parser.add_argument("--porta", type=int, default=PORTA_PADRAO, help="Porta WebDriver BiDi (padrao: 9222)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_abrir = sub.add_parser("abrir", help="Abre Firefox Dev Edition (+PJe e Tampermonkey) e faz login")
    p_abrir.add_argument("--headless", action="store_true", help="Roda sem janela visivel (--headless)")
    p_abrir.add_argument("--url", default=None, help="URL opcional apos login")
    p_abrir.add_argument("--timeout-otp", type=int, default=300)
    p_abrir.set_defaults(func=cmd_abrir)

    p_hl = sub.add_parser("headless", help="Reinicia o perfil ja logado em modo --headless")
    p_hl.add_argument("--url", default=None)
    p_hl.set_defaults(func=cmd_headless)

    p_st = sub.add_parser("status", help="Lista abas e extensoes no Firefox Dev Edition")
    p_st.set_defaults(func=cmd_status)

    p_go = sub.add_parser("goto", help="Navega a aba ativa para uma URL")
    p_go.add_argument("url")
    p_go.add_argument("--aba", default="pje.trt2.jus.br")
    p_go.set_defaults(func=cmd_goto)

    p_dom = sub.add_parser("dom", help="Inspeciona DOM real na aba do PJe")
    p_dom.add_argument("seletor")
    p_dom.add_argument("--limite", type=int, default=5)
    p_dom.add_argument("--html", action="store_true")
    p_dom.add_argument("--aba", default="pje.trt2.jus.br")
    p_dom.set_defaults(func=cmd_dom)

    p_ev = sub.add_parser("eval", help="Executa JS na aba do PJe")
    p_ev.add_argument("codigo")
    p_ev.add_argument("--await", dest="await_promise", action="store_true")
    p_ev.add_argument("--aba", default="pje.trt2.jus.br")
    p_ev.set_defaults(func=cmd_eval)

    p_inj = sub.add_parser("inject", help="Injeta arquivo JS local na aba do PJe")
    p_inj.add_argument("arquivo")
    p_inj.add_argument("--aba", default="pje.trt2.jus.br")
    p_inj.set_defaults(func=cmd_inject)

    p_fechar = sub.add_parser("fechar", help="Encerra a instancia de laboratorio")
    p_fechar.set_defaults(func=cmd_fechar)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
