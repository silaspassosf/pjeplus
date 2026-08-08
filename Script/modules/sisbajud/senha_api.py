"""Servidor auxiliar para expor BP_PASS via HTTP local.
Uso: python senha_api.py
Endpoints:
  GET /api/env/BP_PASS       -> retorna a env var BP_PASS
  GET /api/cred/sisbajud     -> tenta ler do Credential Manager (keyring)
"""
import os
import http.server
import urllib.parse

def _ler_credential_manager(service):
    """Tenta ler do Windows Credential Manager via keyring."""
    try:
        import keyring
        pw = keyring.get_password(service, '')
        if not pw:
            pw = keyring.get_password('sisbajud', service)
        if not pw:
            pw = keyring.get_password(service, service)
        return pw or ''
    except Exception:
        return ''

def _ler_env_var():
    return os.environ.get('BP_PASS', '') or os.environ.get('bp_pass', '') or ''

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        valor = ''

        if parsed.path == '/api/env/BP_PASS':
            valor = _ler_env_var()
        elif parsed.path == '/api/cred/sisbajud':
            valor = _ler_credential_manager('sisbajud') or _ler_env_var()

        if valor:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(valor.encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'not found')

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    port = 8001
    print(f'Servidor senha API na porta {port}')
    print('Endpoints:')
    print('  http://127.0.0.1:8001/api/env/BP_PASS')
    print('  http://127.0.0.1:8001/api/cred/sisbajud')
    print()
    print('Instale keyring se quiser ler do Credential Manager:')
    print('  pip install keyring')
    http_server = http.server.HTTPServer(('127.0.0.1', port), Handler)
    print('Servidor rodando...')
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
