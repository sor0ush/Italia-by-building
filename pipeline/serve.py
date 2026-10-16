#!/usr/bin/env python3
"""
serve.py
Local HTTP server for 'Milano by Building' with full HTTP Range request (RFC 7233)
and CORS support, essential for high-performance PMTiles vector tile streaming.
"""

import os
import re
import sys
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))


class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler with full HTTP 206 Partial Content (Range) support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def end_headers(self):
        # Enable CORS and Accept-Ranges
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            return super().do_GET()

        range_header = self.headers.get("Range")
        if not range_header:
            return super().do_GET()

        range_match = re.match(r"^bytes=(\d+)-(\d*)$", range_header.strip())
        if not range_match:
            return super().do_GET()

        file_size = os.path.getsize(path)
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

        if start >= file_size or end >= file_size or start > end:
            self.send_error(416, "Requested Range Not Satisfiable")
            return

        content_length = end - start + 1
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = "application/octet-stream"

        self.send_response(206, "Partial Content")
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(content_length))
        self.end_headers()

        with open(path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk_size = min(remaining, 64 * 1024)
                data = f.read(chunk_size)
                if not data:
                    break
                self.wfile.write(data)
                remaining -= len(data)


def run_server(port=PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, RangeHTTPRequestHandler)
    print("=" * 60)
    print(f"Milano by Building - Live Web Server")
    print(f"Serving directory: {WEB_DIR}")
    print(f"URL: http://localhost:{port}")
    print(f"PMTiles streaming: Enabled (RFC 7233 HTTP 206 + CORS)")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
