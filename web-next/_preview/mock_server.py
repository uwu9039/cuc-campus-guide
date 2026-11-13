#!/usr/bin/env python
"""前端预览服务：后端（app.py / uvicorn）不运行，界面照常可用。

用途：只调前端设计时，不必承受 71MB 事项库 + 向量库 + 模型的启动成本，
也不必担心提问打到真实链路上。它做两件事：

  1. 静态托管 ../（web-next/），路由语义与 app.py 一致：
        /            → 302 /field（与后端一致）
        /field       → field.html
        /desk        → index.html（旧双栏工作台）
        /classic     → classic.html
        /tice        → tice.html
  2. 把前端会调的 /api/* 用 fixtures/ 里的真实条目现造响应，
     形状逐字对齐 app.py 的返回（问句、答案、反问、没收录、综合层、交付）。

刻意不做的事：不读写 items.json / kb.sqlite，不改任何既有文件，
不调用模型，不落盘。所有数据来自 fixtures/（由 build_fixtures.py 一次性抽出）。

用法：
    .venv\\Scripts\\python.exe web-next\\_preview\\mock_server.py --port 8010
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
WEB = HERE.parent          # web-next/：静态根
FIX = HERE / "fixtures"

# ---------------------------------------------------------------- fixtures


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


ITEMS: list[dict] = []
BY_ID: dict[str, dict] = {}
CONTACTS: list[dict] = []
PRESETS: dict = {}
CAMPUS: dict = {}
META: dict = {}

LOCK = threading.Lock()


def reload_fixtures() -> None:
    global ITEMS, BY_ID, CONTACTS, PRESETS, CAMPUS, META
    data = load_json(FIX / "items.json", {"items": []})
    items = data.get("items") or []
    contacts = load_json(FIX / "contacts.json", {"items": []})
    presets = load_json(FIX / "presets.json", {})
    campus = load_json(FIX / "campus.json", {"pois": []})
    meta = load_json(FIX / "meta.json", {})
    with LOCK:
        ITEMS = items
        BY_ID = {i["id"]: i for i in items}
        CONTACTS = contacts.get("items") or []
        PRESETS = presets
        CAMPUS = campus
        META = meta


# ---------------------------------------------------------------- 文本工具

_PUNCT = re.compile(r"[\s，,。.、；;：:！!？?（）()\[\]【】「」“”\"'’·—\-/]+")


def norm(text: object) -> str:
    return _PUNCT.sub("", str(text or "")).lower()


def bigrams(text: str) -> set[str]:
    t = norm(text)
    return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else ({t} if t else set())


def short_title(it: dict, limit: int = 24) -> str:
    t = re.sub(r"https?://\S+", "", str(it.get("title") or ""))
    t = t.split("｜")[0].strip()
    return t[:limit] + "…" if len(t) > limit else t


# ---------------------------------------------------------------- 检索（够用就行）


def score_item(it: dict, q: str) -> int:
    nq = norm(q)
    if not nq:
        return 0
    names = [it.get("title") or "", *(it.get("aliases") or []), *(it.get("keywords") or [])]
    best = 0
    for name in names:
        nn = norm(name)
        if not nn:
            continue
        if nn == nq:
            best = max(best, 100)
        elif len(nn) >= 2 and nn in nq:
            best = max(best, 88 + min(8, len(nn)))
        elif len(nq) >= 3 and nq in nn:
            best = max(best, 74 + min(8, len(nq)))
    overlap = len(bigrams(q) & bigrams((it.get("title") or "") + " " + " ".join(it.get("keywords") or [])))
    if overlap:
        best = max(best, min(72, 30 + overlap * 9))
    return best


def rank(q: str) -> list[tuple[dict, int]]:
    scored = [(it, score_item(it, q)) for it in ITEMS]
    scored = [x for x in scored if x[1] > 0]
    scored.sort(key=lambda x: (-x[1], len(x[0].get("title") or "")))
    return scored


def similar_to(it: dict, k: int = 3) -> list[dict]:
    """同部门的条目当作「相关事项」，够真了。"""
    dept = it.get("dept") or ""
    out = []
    for other in ITEMS:
        if other["id"] == it["id"]:
            continue
        if dept and other.get("dept") == dept:
            out.append(other)
        if len(out) >= k:
            break
    if len(out) < k:
        for other in ITEMS:
            if other["id"] != it["id"] and other not in out:
                out.append(other)
            if len(out) >= k:
                break
    return out[:k]


# ---------------------------------------------------------------- 条目 → 接口形状


def public_item(it: dict) -> dict:
    src = it.get("source")
    if not src:
        src = []
    elif isinstance(src, dict):
        src = [src]
    else:
        src = list(src)
    pits = []
    for p in it.get("pitfalls") or []:
        pits.append(p if isinstance(p, str) else str(p.get("text") or p.get("what") or ""))
    return {
        "id": it["id"],
        "title": it["title"],
        "dept": it.get("dept") or "",
        "status": it.get("status") or "partial",
        "confidence": it.get("confidence") or "medium",
        "fee": it.get("fee"),
        "location": it.get("location"),
        "hours": it.get("hours"),
        "duration": it.get("duration"),
        "window": it.get("window"),
        "channel": it.get("channel") or [],
        "materials": it.get("materials") or [],
        "steps": it.get("steps") or [],
        "pitfalls": [p for p in pits if p],
        "source": src,
        "slots": it.get("slots") or [],
        "answer": it.get("answer"),
        "note": it.get("note"),
        "advisory": it.get("advisory") or [],
        "experience": it.get("experience") or [],
        "evidence": it.get("evidence") or {},
        "qr": it.get("qr") or [],
        "pdf": it.get("pdf") or [],
        "summary": it.get("summary"),
    }


def step_ok(step: dict, slots: dict) -> bool:
    """步骤上的 if 条件：选了值才留下，没选就当作还看不到这条。"""
    cond = step.get("if") if isinstance(step, dict) else None
    if not isinstance(cond, dict):
        return True
    for key, want in cond.items():
        if slots.get(key) != want:
            return False
    return True


def build_parts(it: dict, slots: dict) -> list[dict]:
    parts: list[dict] = []

    def add(label, focus, *, text=None, lines=None, steps=None):
        part = {"label": label, "focus": focus, "found": True}
        if lines:
            part["lines"] = [x for x in lines if x]
        if steps:
            part["steps"] = steps
        if text:
            part["text"] = text
        if not (part.get("lines") or part.get("steps") or part.get("text")):
            part["text"] = "官方页面没有写这一项"
            part["found"] = False
        parts.append(part)

    if it.get("location"):
        add("办理地点", "location", text=it["location"])
    if it.get("hours"):
        add("办理时间", "hours", text=it["hours"])
    if it.get("window"):
        add("办理时限", "window", text=it["window"])
    if it.get("fee"):
        add("费用", "fee", text=it["fee"])
    if it.get("duration"):
        add("办理时长", "duration", text=it["duration"])

    mats = it.get("materials") or []
    if mats:
        add("要带什么", "material",
            lines=[(m if isinstance(m, str) else m.get("name", "")) for m in mats])

    steps = [s for s in (it.get("steps") or []) if isinstance(s, dict) and step_ok(s, slots)]
    if steps:
        add("怎么走", "steps",
            steps=[{"what": s.get("what", ""), "where": s.get("where", "")} for s in steps])

    chans = it.get("channel") or []
    if chans:
        add("线上入口", "channel", lines=[str(c) for c in chans])

    pits = it.get("pitfalls") or []
    if pits:
        add("容易踩的坑", "pitfall",
            lines=[str(p if isinstance(p, str) else p.get("text", "")) for p in pits])

    if not parts:
        add("答复", "answer", text=it.get("summary") or it.get("answer") or it.get("title") or "")
    return parts


def build_quotes(it: dict) -> list[dict]:
    ev = it.get("evidence") or {}
    src = public_item(it)["source"]
    base = src[0] if src else {}
    out = []
    for key, val in list(ev.items())[:8]:
        if not isinstance(val, dict):
            continue
        quote = str(val.get("quote") or "").strip()
        if not quote:
            continue
        out.append({
            "kind": "原文",
            "date": base.get("checked") or "",
            "label": base.get("title") or "",
            "url": base.get("url") or "",
            "quote": quote,
        })
    return out


def map_for(it: dict) -> dict | None:
    """问句/条目点到校内地点时给一个点位，前端会据此拉起地图面板。"""
    hay = f"{it.get('location') or ''} {it.get('title') or ''}"
    for poi in CAMPUS.get("pois") or []:
        name = poi.get("name") or ""
        if not name or name not in hay:
            continue
        lat = poi.get("lat")
        lng = poi.get("lng")
        if lat is None or lng is None:
            continue
        return {"name": name, "lat": lat, "lng": lng,
                "address": poi.get("address") or "", "note": poi.get("note") or ""}
    return None


# ---------------------------------------------------------------- 回答与卡片

DEMO = (
    ("未收录", "miss"),
    ("没收录", "miss"),
    ("反问", "hold"),
    ("二选一", "clarify"),
    ("综合", "synth"),
    ("标准", "answer"),
)


def demo_scenario(text: str) -> str | None:
    """让每种卡片都能手动敲出来：问句里带「演示·反问」之类就切到那个状态。"""
    if "演示" not in text:
        return None
    for word, name in DEMO:
        if word in text:
            return name
    return None


def answer_payload(it: dict, text: str, slots: dict) -> dict:
    parts = build_parts(it, slots)
    related = [{"id": r["id"], "title": r["title"], "label": short_title(r),
                "dept": r.get("dept", "")} for r in similar_to(it)]
    return {
        "matched": True,
        "query": text,
        "normalized": short_title(it),
        "confidence": 0.86,
        "band": "high",
        "ambiguous": False,
        "router_llm": True,
        "resolved_by_llm": False,
        "rerank": None,
        "model_route": None,
        "soft_match": False,
        "focus_by_llm": False,
        "rule_unsure": False,
        "item": public_item(it),
        "answers": parts,
        "headline": it["title"],
        "focus": [p["focus"] for p in parts],
        "hold": False,
        "followups": [],
        "known": slots,
        "quotes": build_quotes(it),
        "missing": [],
        "unasked": [],
        "next_best": [{"id": r["id"], "title": r["title"], "label": short_title(r),
                       "dept": r.get("dept", "")} for r in similar_to(it, 2)],
        "note": it.get("note"),
        "related": related,
        "map": map_for(it),
        "table_link": None,
    }


def hold_payload(it: dict, text: str, slots: dict) -> dict:
    missing = [s for s in (it.get("slots") or [])
               if s.get("required") and s.get("key") not in slots]
    followups = [{
        "key": s.get("key"),
        "question": s.get("ask") or "",
        "options": s.get("options") or [],
        "why": s.get("why") or "",
    } for s in missing]
    parts = [p for p in build_parts(it, slots) if p.get("found")]
    return {
        "matched": True,
        "query": text,
        "normalized": short_title(it),
        "confidence": 0.92,
        "band": "high",
        "ambiguous": False,
        "router_llm": True,
        "resolved_by_llm": False,
        "rerank": None,
        "model_route": None,
        "soft_match": False,
        "focus_by_llm": False,
        "rule_unsure": False,
        "item": public_item(it),
        "answers": parts,
        "headline": None,
        "focus": [],
        "hold": True,
        "followups": followups,
        "known": slots,
        "quotes": build_quotes(it),
        "missing": [],
        "unasked": [],
        "next_best": [],
        "note": None,
        "related": [{"id": r["id"], "title": r["title"], "label": short_title(r),
                     "dept": r.get("dept", "")} for r in similar_to(it, 3)],
        "map": None,
        "table_link": None,
    }


def clarify_payload(it: dict, text: str) -> dict:
    others = similar_to(it, 2)
    choices = [{"id": it["id"], "title": it["title"], "label": short_title(it),
                "dept": it.get("dept", "")}]
    choices += [{"id": o["id"], "title": o["title"], "label": short_title(o),
                 "dept": o.get("dept", "")} for o in others]
    return {
        "matched": True,
        "query": text,
        "normalized": short_title(it),
        "confidence": 0.55,
        "band": "low",
        "ambiguous": True,
        "router_llm": True,
        "resolved_by_llm": False,
        "rerank": None,
        "model_route": None,
        "soft_match": False,
        "focus_by_llm": False,
        "rule_unsure": True,
        "item": public_item(it),
        "answers": [],
        "headline": None,
        "focus": [],
        "hold": False,
        "followups": [],
        "known": {},
        "quotes": [],
        "missing": [],
        "unasked": [],
        "next_best": [],
        "note": None,
        "related": [],
        "map": None,
        "table_link": None,
        "clarify": "这两件事不在同一个地方办，你要办的是哪一件？",
        "disambiguate": choices,
        "reason": "两个条目的说法都能对上这句话，选一个我按那件原文回答。",
    }


def synth_payload(it: dict, text: str) -> dict:
    """综合层：结论 + 分层 + 逐字证据（结构对齐 app.py 的 synth 回包）。"""
    quotes = build_quotes(it)
    evidence = [{
        "doc": (it.get("source") or [{}])[0].get("title") or it.get("dept") or "原文",
        "page": None,
        "kind": "official",
        "url": (it.get("source") or [{}])[0].get("url") or "",
        "quote": q["quote"],
    } for q in quotes[:4]]
    steps = [s for s in (it.get("steps") or []) if isinstance(s, dict)]
    layers = []
    if it.get("location") or it.get("hours"):
        layers.append({"name": "在哪办、什么时候办",
                       "text": "；".join(x for x in [it.get("location"), it.get("hours")] if x)})
    if it.get("materials"):
        layers.append({"name": "要带什么",
                       "text": "、".join((m if isinstance(m, str) else m.get("name", ""))
                                        for m in it["materials"])})
    if steps:
        layers.append({"name": "怎么走",
                       "text": "；".join(f"{i + 1}. {s.get('what', '')}" for i, s in enumerate(steps[:4]))})
    if not layers:
        layers.append({"name": "官方原文",
                       "text": it.get("answer") or it.get("summary") or it.get("title") or ""})
    return {
        "matched": True,
        "query": text,
        "normalized": short_title(it),
        "confidence": 0.72,
        "band": "high",
        "ambiguous": False,
        "router_llm": True,
        "resolved_by_llm": False,
        "rerank": None,
        "model_route": None,
        "soft_match": False,
        "focus_by_llm": False,
        "rule_unsure": False,
        "item": public_item(it),
        "answers": [],
        "headline": None,
        "focus": [],
        "hold": False,
        "followups": [],
        "known": {},
        "quotes": quotes,
        "missing": [],
        "unasked": [],
        "next_best": [],
        "note": None,
        "related": [],
        "map": map_for(it),
        "table_link": None,
        "synth": {
            "premises": [f"你问的是「{short_title(it)}」", "以官方原文为准"],
            "conclusion": it.get("answer") or f"按 {it.get('dept') or '学校'} 原文，这件事能办，条件与时间见下列分层。",
            "layers": layers,
            "evidence": evidence,
            "boundary": "以上逐条来自条目登记的官方页面；原文没写的项不替学校补。",
            "warnings": [],
        },
    }


def miss_payload(text: str) -> dict:
    ranked = rank(text)
    hits = []
    for it, sc in ranked[:3]:
        snippet = it.get("answer") or (it.get("steps") or [{}])[0].get("what") or it.get("title") or ""
        src = (public_item(it)["source"] or [{}])[0]
        hits.append({"title": it["title"], "kind": "原文", "score": round(min(sc, 99) / 100, 2),
                     "page": None, "snippet": str(snippet)[:180], "url": src.get("url") or ""})
    kw = norm(text)
    ct = [c for c in CONTACTS if kw and kw[:2] in norm(c.get("context") or "")][:3]
    return {
        "matched": False,
        "query": text,
        "topic": text[:12],
        "confidence": 0.2,
        "band": "low",
        "ambiguous": False,
        "router_llm": True,
        "resolved_by_llm": False,
        "rerank": None,
        "model_route": None,
        "search_note": "库里没有直接收录这一件事。下面是原文里能找到的线索，你可以换个更具体的说法再问。",
        "original_search": hits,
        "disambiguate": [],
        "related_items": [{"id": r["id"], "title": r["title"], "label": short_title(r)}
                          for r in [x[0] for x in ranked[:3]]],
        "alternatives": [],
        "hints": [{"name": "本科生院", "basis": "事项归口", "matched": ["学籍", "成绩单"],
                   "url": "https://jwc.cuc.edu.cn/"}],
        "contacts": ct,
        "next_actions": ["换个更具体的说法再问一次", "点下面「在原文里找这句话」看原文段落"],
        "suggestion": "预览服务（mock）只做界面呈现，这里的拒答不是真实判断。",
        "item": None,
        "answers": [],
        "quotes": [],
        "followups": [],
        "hold": False,
        "note": None,
        "related": [],
        "map": None,
        "table_link": None,
    }


def ask_payload(body: dict) -> dict:
    text = str(body.get("text") or "").strip()
    slots = body.get("slots") or {}
    pick = body.get("pick_item")
    scenario = demo_scenario(text)

    if pick and pick in BY_ID:
        it = BY_ID[pick]
    else:
        ranked = rank(text)
        it = ranked[0][0] if ranked and ranked[0][1] >= 30 else None

    if scenario == "miss" or it is None:
        return miss_payload(text)
    if scenario == "clarify":
        return clarify_payload(it, text)
    if scenario == "hold":
        return hold_payload(it, text, slots)
    if scenario == "synth" or body.get("synth"):
        return synth_payload(it, text)
    if scenario == "answer":
        return answer_payload(it, text, slots)
    # 默认：条目上登记了必答槽且还没选，就先反问（与真实链路的顺序一致）
    if any(s.get("required") and s.get("key") not in slots for s in (it.get("slots") or [])):
        return hold_payload(it, text, slots)
    return answer_payload(it, text, slots)


# ---------------------------------------------------------------- SSE 思考流


def ask_steps(body: dict, payload: dict) -> list[dict]:
    synth = bool(payload.get("synth"))
    if synth:
        s = payload["synth"]
        return [
            {"label": "拆前提", "t": 0.4, "fields": {"premises": s.get("premises") or []}},
            {"label": "检索", "t": 0.3, "fields": {"queries": ["原文短句", "同义词"]}},
            {"label": "挑证据", "t": 0.2, "fields": {"evidence": len(s.get("evidence") or [])}},
            {"label": "推理", "t": 0.5, "fields": {"layers": len(s.get("layers") or [])}},
            {"label": "校对", "t": 0.1, "fields": {"warnings": 0}},
        ]
    return [
        {"label": "门", "t": 0.2, "fields": {"gate": "rule", "pool": len(ITEMS), "score": 88}},
        {"label": "拼面", "t": 0.3, "fields": {"faces": [p.get("label") for p in payload.get("answers") or []]}},
    ]


# ---------------------------------------------------------------- HTTP


CTYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".mp4": "video/mp4",
    ".txt": "text/plain; charset=utf-8",
    ".map": "application/json; charset=utf-8",
}

NO_STORE = {".html", ".js", ".css", ".json"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "preview-mock/1.0"

    # ---- 工具
    def log_message(self, fmt, *args):  # noqa: A003 - 覆盖基类
        print(f"[mock] {self.address_string()} {fmt % args}", flush=True)

    def send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404, "not found")
            return
        ctype = CTYPES.get(path.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if path.suffix.lower() in NO_STORE:
            self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str, status: int = 302) -> None:
        self.send_response(status)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def read_json(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        raw = self.rfile.read(n) if n else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    # ---- 路由
    def do_GET(self):  # noqa: N802 - 基类约定
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        qs = parse_qs(parsed.query)

        if path.startswith("/_preview"):
            self.send_error(404, "not found")
            return

        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path in ("/", ""):
            self.redirect("/field" + (f"?{parsed.query}" if parsed.query else ""))
            return
        if path == "/field":
            self.send_file(WEB / "field.html")
            return
        if path == "/desk":
            self.send_file(WEB / "index.html")
            return
        if path == "/classic":
            self.send_file(WEB / "classic.html")
            return
        if path == "/tice":
            self.send_file(WEB / "tice.html")
            return

        if path == "/api/health":
            self.send_json({
                "ok": True, "model": "preview-mock", "vision": True,
                # 预览里要把「语言组织」开关的表现调成和正式环境一样：能开、开着
                "key_configured": True, "hot_reload": False,
                **_counts(),
            })
            return
        if path == "/api/stats":
            self.send_json(_counts())
            return
        if path == "/api/items":
            self.send_json({"items": [{"id": i["id"], "title": i["title"],
                                       "status": i.get("status")} for i in ITEMS]})
            return
        if path == "/api/presets":
            limit = int((qs.get("limit") or ["8"])[0])
            groups = [{"name": g.get("name", ""), "items": (g.get("items") or [])[:limit]}
                      for g in (PRESETS.get("groups") or [])]
            self.send_json({"total": PRESETS.get("total", 0), "limit": limit, "groups": groups})
            return
        if path == "/api/contacts":
            purpose = (qs.get("purpose") or [""])[0]
            kw = (qs.get("q") or [""])[0]
            items = CONTACTS
            if purpose:
                items = [c for c in items if c.get("purpose") == purpose]
            if kw:
                items = [c for c in items if kw in (c.get("value", "") + c.get("dept", "") + c.get("context", ""))]
            purposes = sorted({c.get("purpose") or "其他" for c in CONTACTS})
            self.send_json({"purposes": purposes, "items": items[:120], "total": len(items)})
            return
        if path == "/api/campus":
            q = (qs.get("q") or [""])[0].strip()
            limit = int((qs.get("limit") or ["30"])[0])
            pois = CAMPUS.get("pois") or []
            if q:
                nq = norm(q)
                pois = [p for p in pois if any(nq in norm(n) for n in [p.get("name", ""), *(p.get("aliases") or [])])]
            pois = pois[: max(1, min(limit, 500))]
            self.send_json({
                "count": len(pois), "total": len(CAMPUS.get("pois") or []),
                "coords": sum(1 for p in CAMPUS.get("pois") or [] if p.get("lat") is not None),
                "center": CAMPUS.get("center"), "note": CAMPUS.get("notes") or "",
                "has_amap_key": False, "pois": pois,
            })
            return
        if path == "/api/search":
            self.search(qs)
            return
        if path == "/api/plan-file":
            self.send_json({"error": "预览服务不提供 PDF 下载（mock）"}, 404)
            return
        if path == "/__mock/state":
            self.send_json({"items": [{"id": i["id"], "title": i["title"]} for i in ITEMS],
                            "meta": META})
            return

        self.serve_static(path)

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        body = self.read_json()

        if path == "/api/ask":
            payload = ask_payload(body)
            accept = (self.headers.get("Accept") or "").lower()
            if "text/event-stream" in accept:
                self.stream_ask(body, payload)
            else:
                self.send_json(payload)
            return

        if path == "/api/intake":
            text = str(body.get("text") or "")
            ranked = rank(text)
            top = ranked[0] if ranked else None
            matched = bool(top and top[1] >= 60)
            self.send_json({
                "matched": matched,
                "ambiguous": bool(top and 60 <= top[1] < 100),
                "band": "high" if (top and top[1] >= 75) else "low",
                "confidence": round(min(top[1], 100) / 100, 2) if top else 0,
                "item": public_item(top[0]) if matched else None,
                "ask": (top[0].get("slots") or []) if matched else [],
                "alternatives": [{"id": i["id"], "title": i["title"], "score": s,
                                  "status": i.get("status")} for i, s in ranked[:3]],
                "reason": "别名精确命中" if (top and top[1] >= 95) else ("别名近似命中" if matched else "未命中任何事项"),
            })
            return

        if path == "/api/deliver":
            item_id = body.get("item_id")
            it = BY_ID.get(item_id or "")
            if not it:
                self.send_json({"error": "没有这个事项（mock）"}, 404)
                return
            payload = public_item(it)
            payload["slots_filled"] = body.get("slots") or {}
            draft = it.get("draft")
            if draft:
                text = str(draft.get("template") or "")
                for k, v in (body.get("slots") or {}).items():
                    text = text.replace(f"【{k}】", str(v))
                payload["draft"] = {"title": draft.get("title") or "文书草稿", "text": text,
                                    "complete": "【" not in text, "filled_by": "template"}
            else:
                payload["draft"] = None
            self.send_json(payload)
            return

        if path == "/api/verify":
            self.send_json({"error": "预览服务不调用模型，拍照核对不可用（mock）"}, 503)
            return

        self.send_error(404, "not found")

    # ---- 细节
    def _counts(self) -> dict:
        return _counts()

    def search(self, qs) -> None:
        q = (qs.get("q") or [""])[0].strip()
        k = int((qs.get("k") or ["8"])[0])
        if len(q) < 2:
            self.send_json({"error": "请再说得具体一点"}, 400)
            return
        hits = []
        for it, sc in rank(q)[:k]:
            snippet = it.get("answer") or (it.get("steps") or [{}])[0].get("what") or it.get("title") or ""
            src = (public_item(it)["source"] or [{}])[0]
            hits.append({"title": it["title"], "kind": "原文", "score": round(min(sc, 99) / 100, 2),
                         "page": None, "snippet": str(snippet)[:200], "url": src.get("url") or ""})
        self.send_json({"query": q, "total": len(hits), "chunks": len(ITEMS),
                        "built": "preview-mock", "hits": hits, "rows": []})

    def stream_ask(self, body: dict, payload: dict) -> None:
        steps = ask_steps(body, payload)
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        def frame(name: str, data: dict) -> None:
            raw = json.dumps(data, ensure_ascii=False)
            self.wfile.write(f"event: {name}\ndata: {raw}\n\n".encode("utf-8"))
            self.wfile.flush()

        try:
            for step in steps:
                frame("step", step)
                time.sleep(0.12)          # 让前端的打字动画有机会跑起来
            frame("done", payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            # 客户端中途走了（刷新、切页、curl 被管道截断）：不是错误，安静收场
            pass

    def serve_static(self, path: str) -> None:
        rel = path.lstrip("/") or "index.html"
        target = (WEB / rel).resolve()
        try:
            target.relative_to(WEB.resolve())
        except ValueError:
            self.send_error(403, "forbidden")
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            # 无扩展名时补 .html：/field.html 这类直链照常能开
            alt = WEB / (rel + ".html")
            if alt.is_file():
                target = alt
            else:
                self.send_error(404, "not found")
                return
        self.send_file(target)


def _counts() -> dict:
    presets_total = PRESETS.get("total", 0)
    coverage = [k for k in (PRESETS.get("coverage") or {}) if k]
    out = {
        "items": META.get("total_items", len(ITEMS)),
        "verified": META.get("verified", 0),
        "source_thin": META.get("source_thin", 0),
        "facts": META.get("facts", 0),
        "data_updated": META.get("data_updated", ""),
        "contacts": len(CONTACTS),
        "sources": META.get("sources", 0),
        "vector_chunks": META.get("vector_chunks", 0),
        "vector_sources": META.get("vector_sources", 0),
        "mock_items": len(ITEMS),
    }
    if presets_total:
        out["presets"] = presets_total
    if coverage:
        out["presets_items"] = len(coverage)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="前端预览服务（不启动后端）")
    ap.add_argument("--port", type=int, default=8010)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    reload_fixtures()
    if not ITEMS:
        raise SystemExit(
            "fixtures 还没生成。先跑：python web-next/_preview/build_fixtures.py"
        )

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"预览服务已起： http://{args.host}:{args.port}/field   （前端样张 {len(ITEMS)} 条）", flush=True)
    print("  /field 新版主界面 · /desk 双栏工作台 · /classic 旧版 · /tice 规范器", flush=True)
    print("  按 Ctrl+C 结束。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。", flush=True)


if __name__ == "__main__":
    main()
