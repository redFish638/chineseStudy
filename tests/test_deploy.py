"""Exercise real local HTTP checks, including the old-worker window after nginx reload."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from deploy.enable_ip_access import wait_http


def test_nginx_reload_window_and_loopback_proxy(monkeypatch):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.headers.get('Host'))
            if len(calls) < 3:
                self.send_response(404)  # Existing default nginx worker during graceful reload.
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv('http_proxy', 'http://127.0.0.1:1')
    monkeypatch.setenv('HTTP_PROXY', 'http://127.0.0.1:1')
    monkeypatch.setenv('no_proxy', '')
    monkeypatch.setenv('NO_PROXY', '')
    try:
        wait_http(f'http://127.0.0.1:{server.server_port}/api/health', host='49.234.45.134', timeout=2)
        assert len(calls) == 3
        assert all(host == '49.234.45.134' for host in calls)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_welcome_page_cannot_pass_application_check():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'<h1>Welcome to nginx!</h1>')

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(RuntimeError, match='不是预期'):
            wait_http(f'http://127.0.0.1:{server.server_port}/', homepage=True, timeout=.15)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
