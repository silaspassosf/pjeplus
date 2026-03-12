#!/usr/bin/env python3
"""
Simple local HTTP server with CORS headers for development.

Usage:
  py server.py --dir Script --port 8000

Serves the specified directory on http://localhost:PORT/
Adds Access-Control-Allow-Origin: * to responses so browser userscripts can fetch resources.
"""
import http.server
import socketserver
import argparse
import os


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description='Simple HTTP server with CORS')
    parser.add_argument('--dir', default='.', help='Directory to serve')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    args = parser.parse_args()

    os.chdir(args.dir)
    handler = CORSRequestHandler
    with socketserver.TCPServer(('', args.port), handler) as httpd:
        print(f"Serving HTTP on 0.0.0.0 port {args.port} (http://localhost:{args.port}/) from {os.path.abspath(args.dir)}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nShutting down server')
            httpd.server_close()


if __name__ == '__main__':
    main()
