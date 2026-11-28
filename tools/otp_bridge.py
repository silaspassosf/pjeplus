"""tools/otp_bridge.py — Micro-servidor HTTP local (127.0.0.1) para fornecer códigos TOTP do Windows Credential Manager (keyring) ao Tampermonkey (Script/modules/atalhos/otp.js).

Nunca expõe o segredo Base32 — retorna apenas o código TOTP de 6 dígitos e o tempo restante.

Uso:
    py tools/otp_bridge.py              # roda em 127.0.0.1:8765
    pyw tools/otp_bridge.py             # roda em segundo plano sem janela de console
    py tools/otp_bridge.py --port 8765
"""
import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from Fix.sessao import obter_credencial, obter_totp_pje, obter_totp_sisbajud

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8765


class OtpBridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        return

    def _responder_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        rota = (self.path or '').split('?')[0].rstrip('/')
        if rota == '/health':
            self._responder_json(200, {'ok': True})
            return

        if rota in ('/otp/pje', '/otp/sisb'):
            tipo = 'sisb' if rota.endswith('/sisb') else 'pje'
            codigo = obter_totp_sisbajud() if tipo == 'sisb' else obter_totp_pje()
            if not codigo:
                self._responder_json(
                    404,
                    {'ok': False, 'tipo': tipo, 'erro': f'Chave TOTP ({tipo.upper()}) não encontrada no keyring'},
                )
                return
            restante = 30 - (int(time.time()) % 30)
            self._responder_json(
                200,
                {'ok': True, 'tipo': tipo, 'codigo': codigo, 'restante': restante, 'origem': 'keyring'},
            )
            return

        if rota == '/cred/sisb-senha':
            senha = obter_credencial(
                'SISB_SENHA',
                servicos=('pjeplus', 'pje', 'sisbajud', 'SISB'),
                aliases=('PJE_SENHA', 'PJE_PASSWORD', 'BP_PASS', 'SENHA', 'PASSWORD'),
            )
            if not senha:
                self._responder_json(
                    404,
                    {'ok': False, 'erro': 'Credencial de senha SISBAJUD/PJe não encontrada no keyring'},
                )
                return
            self._responder_json(200, {'ok': True, 'senha': senha, 'origem': 'keyring'})
            return

        self._responder_json(404, {'ok': False, 'erro': 'Rota não encontrada'})


def instalar_startup(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    """Cria launcher .vbs no Startup do Windows para iniciar o bridge sem janela."""
    startup_dir = os.path.join(
        os.environ.get('APPDATA', ''),
        'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup',
    )
    os.makedirs(startup_dir, exist_ok=True)
    vbs_path = os.path.join(startup_dir, 'PJePlus_OTP_Bridge.vbs')
    script_path = os.path.abspath(__file__)
    pyw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    if not os.path.exists(pyw):
        pyw = 'pyw'
    cmd = f'"{pyw}" "{script_path}" --host {host} --port {port}'
    vbs = (
        'Set sh = CreateObject("WScript.Shell")\n'
        f'sh.Run "{cmd.replace(chr(34), chr(34) * 2)}", 0, False\n'
    )
    with open(vbs_path, 'w', encoding='utf-8') as f:
        f.write(vbs)
    return vbs_path


def main():
    parser = argparse.ArgumentParser(description='Bridge local keyring -> TOTP para Tampermonkey')
    parser.add_argument('--host', default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--instalar-startup', action='store_true',
                        help='Instala inicialização automática (sem janela) no Startup do Windows')
    args = parser.parse_args()

    if args.instalar_startup:
        caminho = instalar_startup(args.host, args.port)
        print(f'[otp_bridge] Startup instalado: {caminho}')
        return

    try:
        srv = ThreadingHTTPServer((args.host, args.port), OtpBridgeHandler)
    except OSError as e:
        if getattr(e, 'winerror', None) in (10048, 10013) or getattr(e, 'errno', None) in (98, 48):
            print(f'[otp_bridge] Já está em execução em http://{args.host}:{args.port}')
            return
        raise

    print(f'[otp_bridge] Escutando em http://{args.host}:{args.port} (keyring -> TOTP)')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
