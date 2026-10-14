#!/usr/bin/env python3
"""Hold CDSW_APP_PORT open in serverless mode (no local GPU NIM)."""

from __future__ import annotations

import argparse
import http.server
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--service-label", default="svd-nim")
    args = parser.parse_args()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"serverless placeholder: {args.service_label}".encode())

        def log_message(self, *_args):  # noqa: ANN002
            return

    print(f"Serverless mode — holding port {args.port} for {args.service_label}", flush=True)
    http.server.HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
