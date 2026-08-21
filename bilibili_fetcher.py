from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


API_URL = "https://api.bilibili.com/x/web-interface/view"
BVID_RE = re.compile(r"\b(BV[0-9A-Za-z]{10,})\b")
AID_RE = re.compile(r"(?:^|[/?&#\s])(?:av|aid=)(\d+)\b", re.IGNORECASE)
FIELDS = [
    "input",
    "bvid",
    "aid",
    "title",
    "owner",
    "view",
    "danmaku",
    "like",
    "favorite",
    "reply",
    "share",
    "interaction_total",
    "status",
    "error",
]


def extract_video_id(value: str) -> tuple[str | None, str | None]:
    value = value.strip()
    bvid = BVID_RE.search(value)
    if bvid:
        return bvid.group(1), None

    if value.lower().startswith("av") and value[2:].isdigit():
        return None, value[2:]
    if value.isdigit():
        return None, value

    aid = AID_RE.search(value)
    if aid:
        return None, aid.group(1)
    return None, None


def fetch_json(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            ),
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def fetch_one(value: str, timeout: float, debug: bool) -> dict[str, Any]:
    row: dict[str, Any] = {field: "" for field in FIELDS}
    row["input"] = value
    bvid, aid = extract_video_id(value)
    row["bvid"] = bvid or ""
    row["aid"] = aid or ""

    if not bvid and not aid:
        row["status"] = "error"
        row["error"] = "No BV or av identifier found"
        return row

    query = {"bvid": bvid} if bvid else {"aid": aid}
    url = f"{API_URL}?{urllib.parse.urlencode(query)}"

    try:
        payload = fetch_json(url, timeout)
        if payload.get("code") != 0:
            message = payload.get("message") or payload.get("msg") or "Bilibili API error"
            if debug:
                message = f"{message}; response={payload}"
            raise RuntimeError(message)

        data = payload.get("data") or {}
        stat = data.get("stat") or {}
        row.update(
            {
                "bvid": data.get("bvid") or bvid or "",
                "aid": data.get("aid") or aid or "",
                "title": data.get("title") or "",
                "owner": (data.get("owner") or {}).get("name") or "",
                "view": int(stat.get("view") or 0),
                "danmaku": int(stat.get("danmaku") or 0),
                "like": int(stat.get("like") or 0),
                "favorite": int(stat.get("favorite") or 0),
                "reply": int(stat.get("reply") or 0),
                "share": int(stat.get("share") or 0),
                "status": "ok",
                "error": "",
            }
        )
        row["interaction_total"] = row["like"] + row["favorite"] + row["reply"] + row["share"]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
        row["status"] = "error"
        row["error"] = str(exc) if debug else clean_error(exc)
    return row


def clean_error(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"Network error: {exc.reason}"
    return str(exc)
