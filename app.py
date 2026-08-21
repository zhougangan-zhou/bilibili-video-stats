#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse

import bilibili_fetcher

ROOT = Path(__file__).resolve().parent
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}
LINK_RE = re.compile(r"(https?://[^\s,，]+|BV[0-9A-Za-z]{10,}|av\d+)", re.IGNORECASE)


def extract_inputs(text: str) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for match in LINK_RE.finditer(text):
        item = match.group(1).strip().rstrip("。；;)")
        if item and item not in seen:
            seen.add(item)
            items.append(item)
    return items


def rows_to_csv(rows: list[dict]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=bilibili_fetcher.FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


class AppHandler(BaseHTTPRequestHandler):
    server_version = "BilibiliStatsApp/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.serve_file(ROOT / "index.html")
            return
        file_path = (ROOT / path.lstrip("/")).resolve()
        if ROOT not in file_path.parents and file_path != ROOT:
            self.send_error(403)
            return
        if file_path.is_file():
            self.serve_file(file_path)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/stats":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"ok": False, "error": "请求格式不是有效 JSON"}, status=400)
            return

        text = str(payload.get("text", ""))
        inputs = extract_inputs(text)
        if not inputs:
            self.send_json({"ok": False, "error": "没有识别到 B 站视频链接或 BV/av 号"}, status=400)
            return

        rows = [bilibili_fetcher.fetch_one(item, timeout=15.0, debug=False) for item in inputs]
        ok_rows = [row for row in rows if row.get("status") == "ok"]
        csv_text = rows_to_csv(rows)
        self.send_json(
            {
                "ok": True,
                "count": len(rows),
                "success": len(ok_rows),
                "failed": len(rows) - len(ok_rows),
                "rows": rows,
                "csv": csv_text,
            }
        )

    def serve_file(self, path: Path) -> None:
        content_type = STATIC_TYPES.get(path.suffix.lower(), "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print("%s - %s" % (self.address_string(), format % args))


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Serving on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
