"""全量扫一遍回答正文里残留的禁用标点。

对 581 条问题逐条跑 answer_question + clean_response，只检查用户看到的正文，
原文引文（quotes）与证据（evidence）不算。括号和 URL、时间、电话、小数先遮掉。
输出 TSV：组别 | 问题 | 命中条目 | 残留字符与上下文
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import app  # noqa: E402
from audit_common_20261030 import load_bank  # noqa: E402

BAD = {
    "“": "左双引号", "”": "右双引号", "‘": "左单引号", "’": "右单引号",
    '"': "直双引号", "'": "直单引号", "「": "直角引号", "」": "直角引号",
    "『": "双直角引号", "』": "双直角引号",
    "—": "破折号", "–": "短破折号", "―": "破折号",
    "：": "冒号", ":": "ASCII 冒号",
    "。": "句号", "*": "星号", "#": "井号",
    "…": "省略号",
}


def texts(resp: dict):
    for p in resp.get("answers") or []:
        if p.get("text"):
            yield "text:" + str(p.get("focus")), p["text"]
        for s in p.get("steps") or []:
            if isinstance(s, dict):
                for k in ("what", "where", "when"):
                    if s.get(k):
                        yield "step", s[k]
            elif isinstance(s, str):
                yield "step", s
        for ln in p.get("lines") or []:
            if isinstance(ln, str):
                yield "line", ln
            elif isinstance(ln, dict):
                for k in ("text", "what", "label"):
                    if ln.get(k):
                        yield "line", ln[k]
    for key in ("note", "clarify"):
        if isinstance(resp.get(key), str) and resp[key]:
            yield key, resp[key]
    for f in resp.get("followups") or []:
        if isinstance(f, str):
            yield "followup", f
        elif isinstance(f, dict):
            for k in ("text", "label", "q"):
                if f.get(k):
                    yield "followup", f[k]
    it = resp.get("item") or {}
    for key in ("title", "fee", "location", "hours", "duration", "window", "note", "answer"):
        if isinstance(it.get(key), str) and it[key]:
            yield "item." + key, it[key]
    for s in it.get("steps") or []:
        for k in ("what", "where", "when"):
            if s.get(k):
                yield "item.step", s[k]
    for m in it.get("materials") or []:
        if isinstance(m, str):
            yield "item.material", m
        elif m.get("name"):
            yield "item.material", m["name"]
    for p in it.get("pitfalls") or []:
        if isinstance(p, str):
            yield "item.pitfall", p
    gen = resp.get("llm_answer")
    if isinstance(gen, dict):
        for k in ("text", "caveat"):
            if isinstance(gen.get(k), str):
                yield "llm", gen[k]


def mask(s: str) -> str:
    return app._KEEP_RE.sub("□", s)


def scan(s: str):
    m = mask(s)
    out = []
    for i, ch in enumerate(m):
        if ch in BAD:
            lo = max(0, i - 12)
            hi = min(len(m), i + 13)
            out.append((BAD[ch], m[lo:hi].replace("\n", " ")))
    return out


def main() -> None:
    rows = load_bank(None)
    bad_rows = []
    stats = {}
    for group, q in rows:
        try:
            resp = app.clean_response(app.answer_question(q, {}, router_llm=False))
        except Exception as e:  # noqa: BLE001
            bad_rows.append((group, q, "EXC", repr(e)))
            continue
        title = (resp.get("item") or {}).get("title") or ""
        seen = set()
        hits = []
        for where, t in texts(resp):
            for kind, ctx in scan(t):
                key = (kind, ctx)
                if key in seen:
                    continue
                seen.add(key)
                hits.append(f"{kind} @{where} … {ctx}")
                stats[kind] = stats.get(kind, 0) + 1
        if hits:
            bad_rows.append((group, q, title, " || ".join(hits)))

    out = ROOT / "_style_scan.tsv"
    with out.open("w", encoding="utf-8") as f:
        for r in bad_rows:
            f.write("\t".join(r) + "\n")
    print("questions", len(rows), "flagged", len(bad_rows))
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
