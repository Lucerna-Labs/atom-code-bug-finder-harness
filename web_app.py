#!/usr/bin/env python3
"""Local browser UI and JSON API for saved benchmark configs and runs."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from job_service import JobService, ROOT

WEB = ROOT / 'web'


class Handler(BaseHTTPRequestHandler):
    service = None

    def log_message(self, format, *args):
        pass

    def _host_ok(self):
        host = self.headers.get('Host', '')
        return host in (f'127.0.0.1:{self.server.server_port}',
                        f'localhost:{self.server.server_port}')

    def _origin_ok(self):
        origin = self.headers.get('Origin')
        return origin is None or origin == f'http://{self.headers.get("Host")}'

    def _headers(self, status, kind, size):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(size))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()

    def _send_json(self, status, value):
        wire = json.dumps(value, ensure_ascii=False).encode()
        self._headers(status, 'application/json; charset=utf-8', len(wire))
        self.wfile.write(wire)

    def _send_file(self, name, kind):
        wire = (WEB / name).read_bytes()
        self._headers(200, kind, len(wire))
        self.wfile.write(wire)

    def do_GET(self):
        if not self._host_ok():
            return self._send_json(403, {'error': 'host rejected'})
        path = urlsplit(self.path).path
        if path == '/':
            return self._send_file('index.html', 'text/html; charset=utf-8')
        if path == '/app.js':
            return self._send_file('app.js', 'text/javascript; charset=utf-8')
        if path == '/style.css':
            return self._send_file('style.css', 'text/css; charset=utf-8')
        if path == '/icon.svg':
            return self._send_file('icon.svg', 'image/svg+xml')
        try:
            if path == '/api/health':
                return self._send_json(200, {'app': 'chaos-security-benchmark', 'status': 'ready'})
            if path == '/api/configs':
                return self._send_json(200, {'configs': self.service.list_configs()})
            if path.startswith('/api/configs/'):
                return self._send_json(200, self.service.get_config(path.removeprefix('/api/configs/')))
            if path == '/api/runs':
                return self._send_json(200, {'runs': self.service.list_runs()})
            if path.startswith('/api/runs/'):
                parts = path.split('/')
                if len(parts) == 4:
                    return self._send_json(200, self.service.get_run(parts[3]))
                if len(parts) == 5 and parts[4] == 'receipt':
                    return self._send_json(200, self.service.receipt(parts[3]))
                if len(parts) == 5 and parts[4] == 'log':
                    return self._send_json(200, {'log': self.service.log_tail(parts[3])})
        except (ValueError, OSError, json.JSONDecodeError) as error:
            return self._send_json(404, {'error': str(error)})
        self._send_json(404, {'error': 'not found'})

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok() or self.headers.get('X-Chaos-Local') != '1':
            return self._send_json(403, {'error': 'local request required'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self._send_json(415, {'error': 'JSON required'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError('request size must be 1..65536 bytes')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('request must be a JSON object')
            path = urlsplit(self.path).path
            if path == '/api/configs':
                return self._send_json(201, self.service.create_config(payload.get('id'), payload.get('config')))
            if path == '/api/runs':
                return self._send_json(202, self.service.start_run(payload.get('config_id')))
            if path.startswith('/api/runs/') and path.endswith('/cancel'):
                run_id = path.split('/')[3]
                return self._send_json(200, self.service.cancel_run(run_id))
        except (ValueError, OSError, json.JSONDecodeError, KeyError) as error:
            return self._send_json(400, {'error': str(error)})
        self._send_json(404, {'error': 'not found'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('invalid port')
    Handler.service = JobService()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Chaos Security Benchmark: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        Handler.service.shutdown()


if __name__ == '__main__':
    main()
