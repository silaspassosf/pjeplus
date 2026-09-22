"""Servidor local com CORS + suporte a .env para o PJe Tools.
Uso: python server.py
Serve arquivos de Script/ na porta 8000 com headers CORS.
Le .env da raiz do projeto e expoe via GET /api/env/BP_PASS

Substitui: python -m http.server 8000
"""
import os
import http.server
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))

def _load_env():
    """Le BP_PASS do .env na raiz do projeto."""
    env_path = os.path.join(ROOT, '.env')
    if not os.path.isfile(env_path):
        return ''
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('BP_PASS=') or line.startswith('bp_pass='):
                    return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return ''

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def send_response(self, code, message=None):
        """Adiciona CORS headers em toda resposta automaticamente."""
        super().send_response(code, message)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Endpoint especial: ler BP_PASS do .env
        if parsed.path == '/api/env/BP_PASS':
            valor = _load_env()
            if valor:
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(valor.encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'BP_PASS not found in .env')
            return

        # Arquivo estatico (CORS adicionado automaticamente via send_response)
        super().do_GET()

    def log_message(self, format, *args):
        if '/api/' in self.path:
            print(f'[API] {self.path}')

if __name__ == '__main__':
    port = 8000
    print(f'Servidor PJe Tools rodando na porta {port}')
    print(f'Servindo arquivos de: {ROOT}')
    print()
    print('Endpoint BP_PASS:')
    print('  http://127.0.0.1:8000/api/env/BP_PASS')
    print()
    print('Crie um arquivo .env na raiz do projeto com:')
    print('  BP_PASS=suasenha')
    print()
    http_server = http.server.HTTPServer(('0.0.0.0', port), Handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor encerrado.')
        http_server.server_close()
