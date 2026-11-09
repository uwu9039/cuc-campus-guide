"""A 案判分片的稳定性复跑：P6 相对 P5 翻档的 6 道题，同题连跑三次，开/关片段交替。

为什么要这一步：P6 与 P5 唯一的代码差别是 prompt_parts 里的 rerank.judge_generic，
但每题的候选池本身也带随机性（改写腿那句「官方说法」是模型生成的，同一次跑两遍可能换人）。
所以这里把送进模型的池子 id 一起记下来：只有池子一致时档位差才算片段的账。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/frag_stability.py
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_review_items"))

import app  # noqa: E402
import prompt_parts as pp  # noqa: E402

QS = [
    "ps激活怎么弄",
    "信息化服务里 ps 激活怎么弄",
    "想去游个泳什么时候去合适",
    "回去晚了进不了楼怎么办",
    "看病垫的钱学校给报不",
    "微专业怎么报名？什么时候开课？",
    "寒假什么时候放",
]
REPS = 3

# P6 = 定案档（与 balance_probe 里 P6 的 env 一致）
for k, v in {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B",
             "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}.items():
    setattr(app, k, v)

ORIG_LAYOUT = pp.layout
ORIG_RERANK = app.llm_rerank
POOL: dict[str, list[str]] = {}
_lock = threading.Lock()


def _layout_factory(strip_fragment: bool):
    def layout(task, state):
        parts = ORIG_LAYOUT(task, state)
        return [p for p in parts if not (strip_fragment and p == "rerank.judge_generic")]
    return layout


def _rerank_spy(text, pool, *a, **kw):
    with _lock:
        POOL[text] = [it["id"] for it, _ in pool]
    return ORIG_RERANK(text, pool, *a, **kw)


app.llm_rerank = _rerank_spy


def _expect(q: str) -> list[str]:
    import balance_probe as bp
    for rec in bp.questions():
        if rec["q"] == q:
            return rec["expect"]
    return []


def one(q: str) -> dict:
    exp = set(_expect(q))
    try:
        d = app.answer_question(q, router_llm=True)
    except Exception as e:  # noqa: BLE001
        return {"q": q, "err": str(e)[:100]}
    mr = d.get("model_route") or {}
    got = (d.get("item") or {}).get("id")
    tier = "对" if got in exp else ("错" if d.get("matched") else "拒")
    with _lock:
        pool = list(POOL.get(q, []))
    return {"q": q, "tier": tier, "got": got, "conf": d.get("confidence"),
            "gate": mr.get("gate"), "score": mr.get("score"),
            "pool": pool, "pool_hash": hash(tuple(sorted(pool))) % 10 ** 8}


def batch(mode: str, rep: int) -> list[dict]:
    pp.layout = _layout_factory(mode == "off")
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = [f.result() for f in [pool.submit(one, q) for q in QS]]
    for r in rows:
        r["mode"], r["rep"] = mode, rep
    print(f"--- {mode} 第 {rep} 遍")
    for r in rows:
        print(f"  {r['tier']} {r['q'][:20]:<22} got={str(r.get('got'))[:22]:<24} "
              f"conf={r.get('conf')} gate={r.get('gate')} 分={r.get('score')} "
              f"池{len(r.get('pool') or [])} sig={r.get('pool_hash')}")
    return rows


def main() -> int:
    all_rows: list[dict] = []
    for mode in ("on", "off"):
        for rep in range(1, REPS + 1):
            all_rows += batch(mode, rep)
    out = ROOT / "_review_items" / "frag_stability.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("\n== 汇总：每题在各模式下的档位与池子 ==")
    for q in QS:
        for mode in ("on", "off"):
            rs = [r for r in all_rows if r["q"] == q and r["mode"] == mode]
            tiers = [r["tier"] for r in rs]
            sigs = {r["pool_hash"] for r in rs if r.get("pool")}
            print(f"{mode:<4} {q[:24]:<26} 档位={'/'.join(tiers):<9} 池签名={sorted(sigs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
