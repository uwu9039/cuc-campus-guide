"""P4 对照档：检索 top-k 原文 → 模型生成并标引用，用同一套标签判对错。

目的只有一个：把「别人的智能体基本没错答」这句话换成我们自己的数。
判法与 P0–P3 同源（expect 条目 id 来自 labeled 52 题＋同义不同词 48 题）：

  拒答   模型说资料里没有（has_evidence=false）
  答对   引用里含期望条目，且答案里每个数字/时间都能在被引资料里逐字找到
  错答   其余。其中单列一项「编了数字」——这是生成式 RAG 特有的失败，选择式没有。

只读 app 的检索件，不改生产链路；提示词写在本文件里，明确标注是实验件。
用法：./.venv/Scripts/python.exe tools/freegen_probe.py run [--limit N]
      ./.venv/Scripts/python.exe tools/freegen_probe.py show
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_review_items"))

import app  # noqa: E402
import balance_probe as bp  # noqa: E402  (共用同一份带标签题集)

OUT = ROOT / "_review_items" / "freegen_rows.jsonl"

# 实验提示词：与生产 free_answer 不同，这里强制「只准用给定资料＋标 id＋没资料就认」
PROMPT = (
    "你是校园办事问答的检索增强回答器。只用下面给出的资料回答，资料里没有的一律不准补。\n\n"
    "{sources}\n\n"
    "学生问：{q}\n\n"
    "要求：\n"
    "- 只用资料里写过的内容回答，不许用你自己的常识补全；数字、时间、金额、地点必须逐字来自资料。\n"
    "- cites 填你真正用到的资料编号（R0、R1…对应的 id），没用到就别填。\n"
    "- 这些资料答不上这个问题时，has_evidence 填 false，answer 填空字符串，不要勉强编。\n"
    '- 只输出 JSON：{{"answer": "给学生的回答", "cites": ["条目id"], "has_evidence": true/false, "why": "一句话"}}'
)
_ref_re = re.compile(r"^(R\d+)\s*｜\s*(\S+)")


def build_pool(q: str, k: int = 12) -> list[dict]:
    rows = app.rerank_candidates(q, app.rank(q), limit=k, status={})
    srcs = []
    for i, (it, _sc) in enumerate(rows):
        body = app._item_full_text(it, 400)
        if not body.strip():
            continue
        srcs.append({"ref": f"R{i}", "id": it["id"], "title": (it.get("title") or "")[:40], "body": body})
    return srcs


NUM_RE = re.compile(r"\d+(?:[:.]\d+)?")


def fabricated(ans: str, cited_bodies: str) -> list[str]:
    """答案里出现但被引资料里逐字找不到的数字/时间。"""
    hay = app._mn(cited_bodies)
    return [t for t in NUM_RE.findall(ans) if t not in hay]


def run_one(rec: dict) -> dict:
    q = rec["q"]
    t0 = time.time()
    srcs = build_pool(q)
    menu = "\n".join(f"{s['ref']}｜{s['id']}｜{s['title']}｜{s['body']}" for s in srcs)
    try:
        raw = app.ds_chat([{"role": "system", "content": "只根据给定资料回答，标注用到的资料编号。"},
                           {"role": "user", "content": PROMPT.format(sources=menu, q=q)}],
                          max_tokens=700, json_mode=True)
        d = json.loads(raw) or {}
    except Exception as e:  # noqa: BLE001
        return {"q": q, "err": app._llm_err_text(e)[:80], "src": rec["src"], "expect": rec["expect"]}
    ans = str(d.get("answer") or "").strip()
    cites = [str(c) for c in (d.get("cites") or [])]
    id_of = {s["ref"]: s["id"] for s in srcs}
    ids = [id_of.get(c, c) for c in cites]        # 允许模型直接写 id
    have = bool(d.get("has_evidence")) and bool(ans)
    all_bodies = " ".join(s["body"] for s in srcs)
    cited_bodies = " ".join(s["body"] for s in srcs if s["id"] in ids)
    # 真编造＝整批检索资料里都没有这个数字；引用标不全＝数字能在资料里找到，但不在它自己标的资料里
    fab = fabricated(ans, all_bodies) if have else []
    uncited = sorted(set(fabricated(ans, cited_bodies)) - set(fab)) if have else []
    hit_id = bool(set(ids) & set(rec["expect"]))
    return {
        "q": q, "src": rec["src"], "expect": rec["expect"],
        "matched": have, "cites": ids, "hit_id": hit_id, "fabricated": fab, "uncited": uncited,
        "hit": have and hit_id and not fab,
        "wrong": have and not (hit_id and not fab),
        "refused": not have,
        "ans": ans[:300], "why": str(d.get("why") or "")[:120],
        "ms": round((time.time() - t0) * 1000), "pool": len(srcs),
    }


_lock = threading.Lock()


def do_run(workers: int, limit: int) -> int:
    qs = bp.questions()
    if limit:
        qs = qs[:limit]
    print(f"P4 生成档：{len(qs)} 题，每题资料 {12} 条", flush=True)
    t0 = time.time()
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run_one, r): r for r in qs}
        for i, f in enumerate(list(futs), 1):
            rows.append(f.result())
            if i % 20 == 0:
                print(f"   {i}/{len(qs)} …", flush=True)
    if limit:      # 冒烟不落盘，免得污染正式产物
        for r in rows[:5]:
            print(json.dumps(r, ensure_ascii=False)[:300], flush=True)
        return 0
    with io.open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(_summary(rows), flush=True)
    print(f"墙钟 {time.time() - t0:.0f}s", flush=True)
    return 0


def _summary(rows: list[dict]) -> str:
    n = len(rows)
    hit = sum(1 for r in rows if r.get("hit"))
    wrong = sum(1 for r in rows if r.get("wrong"))
    ref = sum(1 for r in rows if r.get("refused"))
    fab = sum(1 for r in rows if r.get("fabricated"))
    unc = sum(1 for r in rows if r.get("uncited"))
    idok = sum(1 for r in rows if r.get("matched") and r.get("hit_id"))
    med = sorted(r["ms"] for r in rows if r.get("ms"))[n // 2] if n else 0
    return (f"答对 {hit}/{n}  错答 {wrong}  拒答 {ref}  |  引用对上期望条目 {idok}  "
            f"真编造数字 {fab}  引用标不全 {unc}  |  每题中位 {med/1000:.1f}s")


def show() -> int:
    if not OUT.exists():
        print("先跑 run")
        return 1
    rows = [json.loads(x) for x in io.open(OUT, encoding="utf-8") if x.strip()]
    print(_summary(rows))
    print("\n=== 错答样例（生成式特有的失败长什么样）===")
    for r in [x for x in rows if x.get("wrong")][:12]:
        print(f"「{r['q']}」期望={r['expect']} 引了={r['cites']} 编的数字={r.get('fabricated')}")
        print(f"    答:{r['ans'][:150]}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "show"])
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    raise SystemExit(do_run(a.workers, a.limit) if a.mode == "run" else show())
