from __future__ import annotations

import csv
import json
import re
from http.server import BaseHTTPRequestHandler
from io import StringIO

import bilibili_fetcher


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


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"ok": False, "error": "请求格式不是有效 JSON"}, status=400)
            return

        inputs = extract_inputs(str(payload.get("text", "")))
        if not inputs:
            self.send_json({"ok": False, "error": "没有识别到 B 站视频链接或 BV/av 号"}, status=400)
            return

        rows = [bilibili_fetcher.fetch_one(item, timeout=12.0, debug=False) for item in inputs]
        ok_rows = [row for row in rows if row.get("status") == "ok"]
        self.send_json(
            {
                "ok": True,
                "count": len(rows),
                "success": len(ok_rows),
                "failed": len(rows) - len(ok_rows),
                "rows": rows,
                "csv": rows_to_csv(rows),
            }
        )

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
