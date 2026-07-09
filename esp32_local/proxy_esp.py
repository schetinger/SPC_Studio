#!/usr/bin/env python3
"""
Proxy reverso simples para expor o ESP32 via ngrok.

Uso:
  python3 proxy_esp.py 192.168.x.x
  (em outro terminal) ngrok http 8080

O ngrok injeta JS quebrado quando proxia dispositivos na LAN diretamente.
Este proxy roda no localhost e repassa as requisições pro ESP32,
evitando que o ngrok modifique o HTML.
"""

import sys
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

if len(sys.argv) < 2:
    print("Uso: python3 proxy_esp.py <IP_DO_ESP>")
    print("Exemplo: python3 proxy_esp.py 192.168.1.42")
    sys.exit(1)

ESP_IP = sys.argv[1]
ESP_URL = f"http://{ESP_IP}"
PORTA = 8080


class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            r = urllib.request.urlopen(f"{ESP_URL}{self.path}", timeout=5)
            self.send_response(r.status)
            # Repassa headers do ESP mas remove CSP do ngrok
            for key, val in r.getheaders():
                if key.lower() not in ('transfer-encoding', 'content-security-policy'):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(r.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f"Erro ao conectar no ESP ({ESP_URL}): {e}".encode())

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length > 0 else b''
            req = urllib.request.Request(
                f"{ESP_URL}{self.path}",
                data=body,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            r = urllib.request.urlopen(req, timeout=5)
            self.send_response(r.status)
            for key, val in r.getheaders():
                if key.lower() not in ('transfer-encoding',):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(r.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f"Erro ao conectar no ESP ({ESP_URL}): {e}".encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # Silencia logs no terminal (descomente a linha abaixo pra debug)
    # def log_message(self, format, *args): pass


if __name__ == '__main__':
    httpd = HTTPServer(('', PORTA), ProxyHandler)
    print(f"╔══════════════════════════════════════════╗")
    print(f"║  Proxy ESP32 rodando em localhost:{PORTA}  ║")
    print(f"║  Alvo: {ESP_URL:<33}║")
    print(f"╠══════════════════════════════════════════╣")
    print(f"║  Agora rode em outro terminal:           ║")
    print(f"║  ngrok http {PORTA}                        ║")
    print(f"╚══════════════════════════════════════════╝")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nProxy encerrado.")
        httpd.server_close()
