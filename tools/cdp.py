"""极简 CDP Proxy 客户端（配合 web-access skill 的 localhost:3456）。

Proxy 只在同一次 bash 调用里存活，所以调用方必须先把 check-deps.mjs 跑起来。
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:3456"


def _req(path: str, data: bytes | None = None, timeout: float = 60) -> str:
    req = urllib.request.Request(BASE + path, data=data, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def health() -> dict:
    return json.loads(_req("/health"))


def targets() -> list[dict]:
    raw = json.loads(_req("/targets"))
    return raw.get("targets", raw) if isinstance(raw, dict) else raw


def new(url: str, wait: float = 0.0, tries: int = 3, timeout: float = 120) -> str:
    last: Exception | None = None
    for _ in range(tries):
        try:
            raw = json.loads(_req("/new", url.encode("utf-8"), timeout=timeout))
            tid = raw.get("targetId") or raw.get("id")
            if wait:
                time.sleep(wait)
            return tid
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(4)
    raise last  # type: ignore[misc]


def ev(tid: str, js: str, frame: str | None = None, timeout: float = 90) -> str:
    q = f"/eval?target={urllib.parse.quote(tid)}"
    if frame:
        q += f"&frame={urllib.parse.quote(frame)}"
    raw = _req(q, js.encode("utf-8"), timeout=timeout)
    try:
        return json.loads(raw).get("value", "")
    except Exception:  # noqa: BLE001
        return raw


def text(tid: str) -> str:
    return ev(tid, "document.body.innerText")


def close(tid: str) -> str:
    return _req(f"/close?target={urllib.parse.quote(tid)}")


def js_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)
