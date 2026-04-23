from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


class ForwardingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    target_base = "http://127.0.0.1:6942"
    lms_cli_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\LM Studio\resources\app\.webpack\lms.exe")
    session = requests.Session()

    def do_GET(self) -> None:
        self._forward()

    def do_POST(self) -> None:
        self._forward()

    def do_OPTIONS(self) -> None:
        self._forward()

    def do_HEAD(self) -> None:
        self._forward()

    def log_message(self, format: str, *args: object) -> None:
        sys.stdout.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format % args))

    def _forward(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(content_length) if content_length else None

            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in HOP_BY_HOP_HEADERS
            }
            headers["X-Forwarded-For"] = self.client_address[0]
            headers["X-Forwarded-Host"] = self.headers.get("Host", "")
            headers["X-Forwarded-Proto"] = "http"

            upstream_url = f"{self.target_base}{self.path}"
            upstream = self._request_upstream(upstream_url, headers, body)

            payload = upstream.content
            self.send_response(upstream.status_code, upstream.reason)
            for key, value in upstream.headers.items():
                if key.lower() in HOP_BY_HOP_HEADERS:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD" and payload:
                self.wfile.write(payload)
        except requests.RequestException as exc:
            message = f"LM Studio upstream error: {exc}\n".encode("utf-8", "replace")
            self.send_response(502, "Bad Gateway")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(message)
        except Exception:
            traceback.print_exc()
            raise

    def _request_upstream(self, url: str, headers: dict[str, str], body: bytes | None) -> requests.Response:
        try:
            return self.session.request(
                method=self.command,
                url=url,
                headers=headers,
                data=body,
                timeout=(10, 300),
                allow_redirects=False,
            )
        except requests.RequestException:
            self._wake_lmstudio()
            return self.session.request(
                method=self.command,
                url=url,
                headers=headers,
                data=body,
                timeout=(10, 300),
                allow_redirects=False,
            )

    def _wake_lmstudio(self) -> None:
        if not os.path.exists(self.lms_cli_path):
            return
        print("Upstream asleep; waking LM Studio server.", flush=True)
        subprocess.run(
            [self.lms_cli_path, "server", "start"],
            check=False,
            timeout=30,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)


class TailProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Expose localhost LM Studio on a network interface.")
    parser.add_argument("--listen-host", default="100.94.187.104")
    parser.add_argument("--listen-port", type=int, default=6942)
    parser.add_argument("--target-base", default="http://127.0.0.1:6942")
    args = parser.parse_args()

    ForwardingHandler.target_base = args.target_base.rstrip("/")
    server = TailProxyServer((args.listen_host, args.listen_port), ForwardingHandler)
    print(f"LM Studio tail proxy listening on http://{args.listen_host}:{args.listen_port} -> {ForwardingHandler.target_base}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
