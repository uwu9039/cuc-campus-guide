"""每一档的时长与 token：拦 ds_chat 那一个 HTTP 出口，逐题累计调用次数与 usage。

只跑 30 题子集（每 3 题取 1，确定性抽样），三档：
  C0 fusion 单腿组装关改写关
  C1 fusion ＋拒答兜底组装
  C2 fusion ＋组装 ＋改写腿 B ＋两道闸   ← 这就是 P5/P6 的调用结构（判分片只加 prompt 字数，不加调用）
同时记下每次调用的 prompt 字符数，用 usage.prompt_tokens 反解中英混排的字数/token 比，
之后任何新片段（比如 rerank.judge_generic）都能按字符直接折算 token，不必再跑。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/token_probe.py
"""
from __future__ import annotations

import io
import json
import statistics
import sys
import threading
import time
import urllib.request as U
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_review_items"))

import app  # noqa: E402

ORIG = U.urlopen
LOCK = threading.Lock()
TL = threading.local()


class Shim:
    def __init__(self, raw: bytes):
        self._raw = raw

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


MARKERS = {
    "判分 rerank": '只输出 JSON：{"scores"',
    "改写救场 route": '只输出 JSON：{"rewrites": ["…"], "id"',
    "官方说法 phrase": '只输出 JSON：{"phrases"',
    "分面计划 plan": '只输出 JSON：{"faces"',
    "分面否决 decide": '只输出 JSON：{"verdict": "accept',
    "覆盖面判定": '"verdict": "yes|partial|no"',
    "总括 headline": '只输出 JSON：{"headline"',
    "续问压缩 condense": '只输出 JSON：{"query"',
    "生成 free": '只输出 JSON：{"answer"',
    "复核 recheck": '"best_answers": "yes|no"',
    "覆盖面 covers": '"covers": "yes|no"',
    "选名 name": '"name": "列表里的名称或null"',
}


def task_of(text: str) -> str:
    for name, mark in MARKERS.items():
        if mark in text:
            return name
    return "未识别"


def spy(req, *a, **kw):
    url = getattr(req, "full_url", "")
    body = getattr(req, "data", None)
    try:
        resp = ORIG(req, *a, **kw)
    except Exception:
        with LOCK:
            TL.calls.append({"task": "调用失败", "err": 1})
        raise
    raw = resp.read()
    if url.endswith("/chat/completions") and body:
        try:
            obj = json.loads(body.decode("utf-8", "ignore"))
            txt = "\n".join(str(m.get("content", "")) for m in obj.get("messages", []))
        except Exception:  # noqa: BLE001
            txt = body.decode("utf-8", "ignore")
        try:
            js = json.loads(raw.decode("utf-8"))
            usage = js.get("usage") or {}
            rec = {"task": task_of(txt), "chars": len(txt),
                   "in": usage.get("prompt_tokens"), "out": usage.get("completion_tokens"),
                   "total": usage.get("total_tokens")}
        except Exception:  # noqa: BLE001
            rec = {"task": task_of(txt), "chars": len(txt), "bad": 1}
        with LOCK:
            TL.calls.append(rec)
        return Shim(raw)
    return resp


U.urlopen = spy

CONFIGS = [
    ("C0", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "off", "REWRITE_PRE": "OFF",
            "DECLINE_REFUSES": False, "MIN_ANSWER_CONF": 0.0}),
    ("C1", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "OFF",
            "DECLINE_REFUSES": False, "MIN_ANSWER_CONF": 0.0}),
    ("C2", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B",
            "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}),
]


def run_one(rec: dict) -> dict:
    TL.calls = []
    t0 = time.time()
    try:
        d = app.answer_question(rec["q"], router_llm=True)
        err = None
    except Exception as e:  # noqa: BLE001
        d, err = {}, str(e)[:80]
    ms = (time.time() - t0) * 1000
    with LOCK:
        calls = list(TL.calls)
    return {
        "q": rec["q"], "matched": bool(d.get("matched")), "err": err,
        "calls": len(calls),
        "in": sum(c.get("in") or 0 for c in calls),
        "out": sum(c.get("out") or 0 for c in calls),
        "chars": sum(c.get("chars") or 0 for c in calls),
        "ms": round(ms),
        "detail": calls,
    }


def med(v):
    return statistics.median(v) if v else 0


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--only", default="", help="只跑逗号分隔的档，如 C2")
    a = ap.parse_args()
    import balance_probe as bp
    qs = bp.questions()[::3]
    print(f"子集 {len(qs)} 题 | 并发 {a.workers}")
    out = []
    for name, env in CONFIGS:
        if a.only and name not in a.only.split(","):
            continue
        for k, v in env.items():
            setattr(app, k, v)
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            rows = [f.result() for f in [pool.submit(run_one, r) for r in qs]]
        wall = time.time() - t0
        out.append((name, rows, wall))
        ins = [r["in"] for r in rows]
        outs = [r["out"] for r in rows]
        cs = [r["calls"] for r in rows]
        pcs = [r["chars"] for r in rows]
        mss = [r["ms"] for r in rows]
        print(f"[{name}] 每题调用 中位{med(cs)} 均{sum(cs)/len(cs):.2f} | "
              f"输入 tok 中位{med(ins)} 均{sum(ins)/len(ins):.0f} | "
              f"输出 tok 中位{med(outs)} 均{sum(outs)/len(outs):.0f} | "
              f"合计 均{(sum(ins)+sum(outs))/len(ins):.0f} tok/题 | "
              f"提示词 均{sum(pcs)/len(pcs):.0f} 字 → 字/token {sum(pcs)/max(1,sum(ins)):.2f} | "
              f"每题中位 {med(mss)/1000:.1f}s p90 {sorted(mss)[int(len(mss)*0.9)]/1000:.1f}s "
              f"最大 {max(mss)/1000:.1f}s | "
              f"{len(qs)} 题墙钟 {wall:.0f}s → 100 题 {wall/len(qs)*100:.0f}s | "
              f"err {sum(1 for r in rows if r['err'])}")
        by: dict[str, list] = {}
        for r in rows:
            for c in r["detail"]:
                by.setdefault(c.get("task") or "?", []).append(c)
        tot = sum((c.get("in") or 0) + (c.get("out") or 0) for v in by.values() for c in v)
        for task, v in sorted(by.items(), key=lambda kv: -sum((c.get("in") or 0)+(c.get("out") or 0) for c in kv[1])):
            tok = sum((c.get("in") or 0) + (c.get("out") or 0) for c in v)
            print(f"    · {task:<18} 次/题 {len(v)/len(rows):>4.2f} "
                  f"均 in {(sum(c.get('in') or 0 for c in v)/len(v)):>5.0f} "
                  f"out {(sum(c.get('out') or 0 for c in v)/len(v)):>4.0f} "
                  f"字 {(sum(c.get('chars') or 0 for c in v)/len(v)):>6.0f} "
                  f"| 占该档 {100*tok/max(1,tot):>5.1f}%")
    dst = ROOT / "_review_items" / "token_rows.jsonl"
    with io.open(dst, "w", encoding="utf-8") as fh:
        for name, rows, wall in out:
            for r in rows:
                fh.write(json.dumps({"cfg": name, **r}, ensure_ascii=False) + "\n")
    print("产物", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
