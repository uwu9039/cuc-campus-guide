"""验收移植的质量闸：_synth_quality_ok 的判定 + SSE 回退路径（打桩，不烧模型）。"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402
from starlette.requests import Request  # noqa: E402

ROWS: list[tuple[str, bool, str]] = []


def rec(name: str, ok: bool, detail: str) -> None:
    ROWS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}", flush=True)


def call_ask(payload: dict):
    scope = {"type": "http", "method": "POST", "path": "/api/ask",
             "headers": [(b"accept", b"text/event-stream")]}
    resp = app.ask(app.AskReq(**payload), Request(scope))
    frames = resp.body_iterator

    def _raw_frames():
        if hasattr(frames, "__aiter__"):
            async def collect():
                return [f async for f in frames]
            return asyncio.run(collect())
        return list(frames)          # 同步生成器：直接迭代（starlette 在线程池里跑它）

    out = []
    for raw in _raw_frames():
        s = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        if s.startswith("data: "):
            out.append(json.loads(s[6:]))
    return out


def main() -> None:
    rec("Q1 空结果判不合格", app._synth_quality_ok(None) is False, "None")
    rec("Q2 证据不足判不合格",
        app._synth_quality_ok({"evidence": [1], "conclusion": "x", "layers": []}) is False,
        "1 条证据")
    rec("Q3 全 missing 判不合格",
        app._synth_quality_ok({"evidence": [1, 2], "conclusion": "x",
                               "layers": [{"verdict": "missing", "text": "y"}]}) is False,
        "只有 missing 层")
    rec("Q4 正常合成判合格",
        app._synth_quality_ok({"evidence": [1, 2], "conclusion": "x",
                               "layers": [{"verdict": "direct", "text": "y"}]}) is True,
        "2 条证据 + direct")

    # SSE 回退：直接驱动 _synth_stream（路由那一层只负责把 kw 传进来，单独在 Q7 验）
    weak = {"premises": ["p"], "conclusion": " ", "layers": [], "evidence": [],
            "boundary": "", "warnings": [], "verdicts": {}}
    real = app.synthesize_answer
    app.synthesize_answer = lambda *a, **k: weak
    fb = {"text": "校园卡丢了怎么补办", "given": {}, "router_llm": False,
          "context_item": None, "context_slots": {}, "history": None, "pick_item": None}
    try:
        evs = []
        for raw in app._synth_stream("校园卡丢了怎么补办", fallback=fb):
            s = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            for line in s.splitlines():          # SSE 是「event: x\ndata: {...}」两行
                if line.startswith("data: "):
                    evs.append({"event": s.split("event: ")[1].splitlines()[0].strip(),
                                "data": json.loads(line[6:])})
    finally:
        app.synthesize_answer = real
    kinds = [e.get("event") for e in evs]
    done = next((e for e in evs if e.get("event") == "done"), None)
    payload = (done or {}).get("data") or {}
    has_fb_step = any(e.get("event") == "step" and (e.get("data") or {}).get("id") == "synth_fallback"
                      for e in evs)
    rec("Q5 薄结果触发回退帧", has_fb_step, f"events={kinds[:6]}")
    rec("Q6 回退后返回普通答案",
        bool(payload.get("answers")) and (payload.get("model_route") or {}).get("synth_fallback") == "quality",
        f"answers={len(payload.get('answers') or [])} route={payload.get('model_route')}")

    # Q7：路由确实把 kw 当 fallback 传下去了
    seen = {}
    real_stream = app._synth_stream

    def spy(*a, **k):
        seen.update(k)
        return iter([b'data: {"event":"done","data":{}}\n\n'])

    app._synth_stream = spy
    real_rank = app.rank
    try:
        scope = {"type": "http", "method": "POST", "path": "/api/ask",
                 "headers": [(b"accept", b"text/event-stream")]}
        app.ask(app.AskReq(text="校园卡丢了怎么补办", synth=True), Request(scope))
    finally:
        app._synth_stream = real_stream
        app.rank = real_rank
    rec("Q7 路由把 fallback 传进综合层", "fallback" in seen and "text" in (seen.get("fallback") or {}),
        f"keys={sorted(seen)}")

    bad = [r for r in ROWS if not r[1]]
    print(f"\n共 {len(ROWS)} 项：PASS {len(ROWS)-len(bad)} / FAIL {len(bad)}")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
