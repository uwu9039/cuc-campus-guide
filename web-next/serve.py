#!/usr/bin/env python3
"""开发预览：静态托管 web-next/，并把 /api/* 反代到本地 app.py。

只是预览工具，不参与生产。生产可直接用 FastAPI StaticFiles 托管本目录。
用法：python serve.py [端口]（默认 8090，上游默认 http://127.0.0.1:8077）
"""
from __future__ import annotations

import http.server
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
UPSTREAM = os.environ.get("API_UPSTREAM", "http://127.0.0.1:8077").rstrip("/")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8090


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _proxy(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(UPSTREAM + self.path, data=body, method=self.command)
        for key in ("Content-Type", "Accept"):
            if self.headers.get(key):
                req.add_header(key, self.headers[key])
        try:
            with urllib.request.urlopen(req, timeout=180) as res:
                data = res.read()
                self.send_response(res.status)
                for key, value in res.getheaders():
                    if key.lower() in ("transfer-encoding", "connection", "content-length"):
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as exc:
            data = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:  # noqa: BLE001
            msg = f'{{"detail":"上游未就绪：{exc}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/"):
            return self._proxy()
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        if self.path.startswith("/api/"):
            return self._proxy()
        self.send_error(405, "Method Not Allowed")

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    os.chdir(ROOT)
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"web-next -> http://127.0.0.1:{PORT}/  (api -> {UPSTREAM})")
        httpd.serve_forever()
