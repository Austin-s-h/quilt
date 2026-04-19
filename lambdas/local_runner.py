#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib
import json
import traceback
import sys
from base64 import b64decode, b64encode
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, unquote, urlparse


def _load_handler(module_name: str, attr_name: str):
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


class Handler(BaseHTTPRequestHandler):
    lambda_path = "/lambda"
    handler = None

    def _handle_request(self, req_body):
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)

        if path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        if path == self.lambda_path or path.startswith(self.lambda_path + "/"):
            query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
            headers = {k.lower(): v for k, v in self.headers.items()}
            args = {
                "httpMethod": self.command,
                "path": path,
                "pathParameters": {
                    "proxy": path[len(self.lambda_path) + 1:],
                },
                "queryStringParameters": query or None,
                "headers": headers or None,
                "body": b64encode(req_body or b""),
                "isBase64Encoded": True,
            }

            try:
                result = self.handler(args, None)
            except Exception as exc:
                body = json.dumps({"error": str(exc), "traceback": traceback.format_exc()}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            code = result["statusCode"]
            headers = result["headers"]
            body = result["body"]
            encoded = result.get("isBase64Encoded", False)

            if encoded:
                body = b64decode(body)
            else:
                body = body.encode()

            headers["Content-Length"] = str(len(body))

            self.send_response(code)
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_GET(self):
        self._handle_request(None)

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(size)
        self._handle_request(body)

    def do_OPTIONS(self):
        self._handle_request(None)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    parser.add_argument("handler_attr")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv[1:])

    Handler.handler = _load_handler(args.module, args.handler_attr)
    server_address = (args.host, args.port)
    print(f"Running on http://{server_address[0]}:{server_address[1]}{Handler.lambda_path}", flush=True)
    server = HTTPServer(server_address, Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
