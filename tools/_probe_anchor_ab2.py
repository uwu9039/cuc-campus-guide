"""锚定注入 A/B（只读研究）：金标准 12 题 × 裸调/带锚点 × N 次。

为什么另起一个脚本：`tools/_anchor_ab.py` 只跑 4 题、1 次、且判分用 `kw in ans` 的字面匹配
（golden 里有 22/44 条要点的 kw 是 `a|b` 这种「或」写法，字面永远不命中 → 严格口径被系统性压低）。
这里：
  · 12 题全量，每题每路 N 次（默认 2），路径可断点续跑（jsonl 追加）；
  · 记录锚定判定、注入了哪些 item 候选、综合层最终用了哪些证据（含 from_item/must），
    用来区分「锚错条目」与「锚对但过窄」两种伤害机理；
  · 判分三口径：judge（模型判读）、strict_literal（=_score_golden 现行为）、
    strict_fixed（把 kw 的 `a|b` 按「或」拆开——正确的双检写法）。

用法（都在仓库根目录）：
  ./.venv/Scripts/python.exe -X utf8 -u tools/_probe_anchor_ab2.py rank
  ./.venv/Scripts/python.exe -X utf8 -u tools/_probe_anchor_ab2.py gen --runs 2 --workers 3
  ./.venv/Scripts/python.exe -X utf8 -u tools/_probe_anchor_ab2.py score --workers 5
  ./.venv/Scripts/python.exe -X utf8 -u tools/_probe_anchor_ab2.py report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import app  # noqa: E402
from _score_golden import judge_point  # noqa: E402

GOLD = ROOT / "_review_items" / "golden_20261111.json"
RUNS = ROOT / "_review_items" / "anchor_ab2_runs.jsonl"
SCORED = ROOT / "_review_items" / "anchor_ab2_scored.json"
JCACHE = ROOT / "_review_items" / "anchor_ab2_judge_cache.json"
ARMS = ("bare", "anchor")


def cases() -> list[dict]:
    return json.loads(GOLD.read_text(encoding="utf-8"))["cases"]


def anchor_for(q: str) -> tuple[dict | None, dict]:
    """复刻 app.py /api/ask 的锚定判定（sc>=85、非 auto/clause/para、lead>=10 或实词重合>=2）。"""
    ranked = app.rank(q)
    info: dict = {"q": q, "anchor": False, "why": ""}
    if not ranked:
        info["why"] = "rank 空"
        return None, info
    top, sc = ranked[0]
    info.update({"top_id": top.get("id"), "top_title": top.get("title"),
                 "sc": sc, "second": ranked[1][1] if len(ranked) > 1 else 0})
    info["lead"] = info["sc"] - info["second"]
    info["materials"] = len(top.get("materials") or [])
    info["steps"] = len(top.get("steps") or [])
    info["ev_groups"] = len(top.get("evidence") or {})
    if sc >= 97:
        info["note"] = "sc>=97：产品不走综合层（这里仍纳入 A/B）"
    if sc < 85 or top.get("auto") or top.get("clause") or top.get("para"):
        info["why"] = f"sc={sc}<85 或类型不合(auto/clause/para)"
        return None, info
    qb = app.bigrams(app.norm(q))
    tb = app.bigrams(app.norm(str(top.get("title") or "") + " "
                              + " ".join(top.get("aliases") or [])))
    shared = sorted((qb & tb) - app.NOISE_BIGRAMS)
    info["shared_n"] = len(shared)
    info["shared"] = shared
    if info["lead"] >= 10 or len(shared) >= 2:
        info["anchor"] = True
        info["why"] = f"lead={info['lead']}, shared={len(shared)}"
        return top, info
    info["why"] = f"lead={info['lead']}, shared={len(shared)}：两个凭据都不够"
    return None, info


def item_dump(item: dict | None) -> dict:
    if not item:
        return {"n": 0}
    warns: list[str] = []
    cs = app._item_candidates(item, warns)
    return {"n": len(cs),
            "verbatim": sum(1 for c in cs if c.get("verbatim")),
            "nonverbatim": sum(1 for c in cs if not c.get("verbatim")),
            "quotes": [str(c.get("quote") or "")[:100] for c in cs],
            "warns": warns}


# ---------------------------------------------------------------- rank

def cmd_rank() -> int:
    print(f"{'问句':38} {'锚?':4} {'top':26} {'sc':>3} {'lead':>4} {'share':>5} mat/steps 说明")
    for c in cases():
        q = c["q"]
        _it, info = anchor_for(q)
        print(f"{q[:36]:38} {'YES' if info['anchor'] else 'no':4} "
              f"{str(info.get('top_title') or '')[:24]:26} {info.get('sc', 0):>3} "
              f"{info.get('lead', 0):>4} {info.get('shared_n', 0):>5} "
              f"{info.get('materials', 0)}/{info.get('steps', 0)}      {info['why']}")
    return 0


# ---------------------------------------------------------------- gen

_write_lock = threading.Lock()


def load_done() -> dict[tuple, dict]:
    done: dict[tuple, dict] = {}
    if not RUNS.exists():
        return done
    for line in RUNS.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        done[(r["q"], r["arm"], r["run"])] = r
    return done


def evidence_rows(ev: list[dict]) -> list[dict]:
    out = []
    for e in ev or []:
        out.append({"doc": str(e.get("doc") or ""), "item_id": e.get("item_id") or "",
                    "from_item": bool(e.get("from_item")),
                    "must": bool(e.get("must")),
                    "sec": str((e.get("sec") or {}).get("no") or ""),
                    "quote": str(e.get("quote") or "")[:220]})
    return out


def run_one(task: tuple, item: dict | None, attempts_max: int = 3) -> dict:
    q, arm, run = task
    t0 = time.time()
    s = None
    err = ""
    attempts = 0
    while attempts < attempts_max:
        attempts += 1
        try:
            s = app.synthesize_answer(q, item=item if arm == "anchor" else None)
        except Exception as e:  # noqa: BLE001
            s = None
            err = f"{type(e).__name__}: {e}"[:200]
        if s:
            break
        time.sleep(1.5 * attempts)
    rec = {"q": q, "arm": arm, "run": run, "ts": time.strftime("%H:%M:%S"),
           "elapsed": round(time.time() - t0, 1), "attempts": attempts,
           "ok": bool(s), "err": err}
    if s:
        rec.update({
            "conclusion": s.get("conclusion") or "",
            "boundary": s.get("boundary") or "",
            "layers": [[str(x.get("name") or ""), str(x.get("verdict") or ""),
                        str(x.get("text") or "")] for x in s.get("layers") or []],
            "premises": s.get("premises") or [],
            "evidence": evidence_rows(s.get("evidence") or []),
            "verdicts": s.get("verdicts") or {},
            "warnings": s.get("warnings") or [],
        })
        rec["answer"] = rec["conclusion"] + "\n" + "\n".join(x[2] for x in rec["layers"])
        n_ev = len(rec["evidence"])
        rec["n_ev"] = n_ev
        rec["n_from_item"] = sum(1 for e in rec["evidence"] if e["from_item"])
        rec["ev_item_share"] = round(rec["n_from_item"] / n_ev, 2) if n_ev else 0.0
    return rec


def cmd_gen(args: argparse.Namespace) -> int:
    if not app.api_key():
        print("没 Key")
        return 2
    qs = [c["q"] for c in cases()]
    anchors = {}
    for q in qs:
        it, info = anchor_for(q)
        anchors[q] = (it, info)
        print(f"[锚定] {q[:30]:32} {'YES' if info['anchor'] else ' no'} "
              f"{str(info.get('top_id') or '')} {info['why']}")
    done = load_done()
    tasks = [(q, arm, run) for run in range(1, args.runs + 1)
             for q in qs for arm in ARMS
             if (q, arm, run) not in done]
    print(f"待跑 {len(tasks)} 个 synth（已有 {len(done)} 条），workers={args.workers}")
    t0 = time.time()
    lock = threading.Lock()

    def work(task: tuple) -> dict:
        q, arm, _run = task
        rec = run_one(task, anchors[q][0])
        with lock, _write_lock:
            with RUNS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
            done[(task[0], task[1], task[2])] = rec
            n = len(done)
            print(f"  [{n:>3}] {task[1]:6} r{task[2]} {rec['elapsed']:>5}s "
                  f"ev={rec.get('n_ev', '-')} item={rec.get('n_from_item', '-')} "
                  f"{'OK' if rec['ok'] else 'FAIL ' + rec['err']} | {q[:22]}")
        return rec

    if tasks:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(work, tasks))
    print(f"gen 完成，用时 {round(time.time() - t0)}s，共 {len(done)} 条 -> {RUNS}")
    return 0


# ---------------------------------------------------------------- score

def kw_groups(pt: dict) -> list[list[str]]:
    """把 kw 拆成「组」，每组内是或关系：`a|b` 或整条。"""
    return [[x for x in str(k).split("|") if x] for k in pt.get("kw") or []]


def kw_hit(pt: dict, ans: str, fix: bool) -> bool:
    if not fix:
        return all(k in ans for k in pt.get("kw") or [])
    return all(any(x in ans for x in grp) for grp in kw_groups(pt))


def load_jcache() -> dict:
    if JCACHE.exists():
        try:
            return json.loads(JCACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def cmd_score(args: argparse.Namespace) -> int:
    rows = list(load_done().values())
    if not rows:
        print("没有 runs，先跑 gen")
        return 2
    by_q = {c["q"]: c for c in cases()}
    cache = load_jcache()
    lock = threading.Lock()
    jobs: list[tuple[dict, int, dict]] = []
    for r in rows:
        if not r.get("ok"):
            continue
        case = by_q[r["q"]]
        for i, pt in enumerate(case["points"]):
            jobs.append((r, i, pt))
    print(f"判分调用 {len(jobs)} 个（缓存 {len(cache)}）")

    def judge(job: tuple) -> tuple:
        r, i, pt = job
        ans = r.get("answer") or ""
        key = hashlib.sha1((pt["p"] + "\x00" + ans).encode("utf-8")).hexdigest()[:16]
        with lock:
            hit = cache.get(key)
        if hit is None:
            hit = judge_point(pt["p"], ans)
            with lock:
                cache[key] = hit
        return (r["q"], r["arm"], r["run"], i, hit)

    t0 = time.time()
    out: dict[tuple, dict] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for k, (q, arm, run, i, hit) in enumerate(ex.map(judge, jobs), 1):
            out.setdefault((q, arm, run), {})[i] = hit
            if k % 40 == 0:
                print(f"  {k}/{len(jobs)}  {round(time.time() - t0)}s")
    JCACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    scored = []
    for r in rows:
        case = by_q[r["q"]]
        pts = case["points"]
        hits = out.get((r["q"], r["arm"], r["run"]), {})
        ans = r.get("answer") or ""
        per = []
        for i, pt in enumerate(pts):
            jd = bool((hits.get(i) or {}).get("hit"))
            kl = kw_hit(pt, ans, fix=False)
            kf = kw_hit(pt, ans, fix=True)
            per.append({"i": i, "p": pt["p"], "src": pt.get("src", ""),
                        "judge": jd, "kw_literal": kl, "kw_fixed": kf,
                        "why": str((hits.get(i) or {}).get("why") or "")[:30]})
        row = dict(r)
        row.update({
            "points": per,
            "judge": sum(1 for x in per if x["judge"]),
            "strict_literal": sum(1 for x in per if x["judge"] and x["kw_literal"]),
            "strict_fixed": sum(1 for x in per if x["judge"] and x["kw_fixed"]),
            "total": len(per),
        })
        scored.append(row)
    SCORED.write_text(json.dumps(scored, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"score 完成 {round(time.time() - t0)}s -> {SCORED}")
    return 0


# ---------------------------------------------------------------- report

def src_ids(src: str) -> set[str]:
    """从 golden 的 src 字段里抠出条目 id（形如 xyk-buka / pt-288e4a9fba）。"""
    import re
    return {t for t in re.findall(r"[a-z]+(?:-[a-z0-9]+)*", src or "")
            if t.startswith("pt-") or "-" in t}


def cmd_report(args: argparse.Namespace) -> int:
    if not SCORED.exists():
        print("没有 scored，先跑 score")
        return 2
    rows = json.loads(SCORED.read_text(encoding="utf-8"))
    qs = [c["q"] for c in cases()]
    infos = {c["q"]: anchor_for(c["q"])[1] for c in cases()}

    def agg(q: str) -> dict:
        d = {}
        for arm in ARMS:
            rr = [r for r in rows if r["q"] == q and r["arm"] == arm and r.get("ok")]
            if not rr:
                d[arm] = None
                continue
            d[arm] = {"judge": round(sum(r["judge"] for r in rr) / len(rr), 2),
                      "strict_literal": round(sum(r["strict_literal"] for r in rr) / len(rr), 2),
                      "strict_fixed": round(sum(r["strict_fixed"] for r in rr) / len(rr), 2),
                      "total": rr[0]["total"], "n": len(rr),
                      "ev": round(sum(r.get("n_ev") or 0 for r in rr) / len(rr), 1),
                      "item_share": round(sum(r.get("ev_item_share") or 0 for r in rr) / len(rr), 2),
                      "premises": [r.get("premises") for r in rr]}
        return d

    print("=" * 132)
    print(f"{'问句':34} {'锚定条目':22} {'裸judge':>7} {'锚judge':>7} {'Δ':>6} "
          f"{'裸strict':>8} {'锚strict':>8} {'裸fix':>6} {'锚fix':>6} {'item份额':>8}")
    print("-" * 132)
    tot = {a: {"judge": 0.0, "strict_literal": 0.0, "strict_fixed": 0.0} for a in ARMS}
    npts = 0
    for q in qs:
        d = agg(q)
        info = infos[q]
        if not d["bare"] or not d["anchor"]:
            print(f"{q[:32]:34} (缺数据)")
            continue
        npts += d["bare"]["total"]
        dj = d["anchor"]["judge"] - d["bare"]["judge"]
        for a in ARMS:
            for k in tot[a]:
                tot[a][k] += d[a][k]
        mark = "帮" if dj > 0 else ("伤" if dj < 0 else "平")
        print(f"{q[:32]:34} {str(info.get('top_title') or '(不锚)')[:20]:22} "
              f"{d['bare']['judge']:>7.2f} {d['anchor']['judge']:>7.2f} {dj:>+6.2f}{mark} "
              f"{d['bare']['strict_literal']:>8.2f} {d['anchor']['strict_literal']:>8.2f} "
              f"{d['bare']['strict_fixed']:>6.2f} {d['anchor']['strict_fixed']:>6.2f} "
              f"{d['anchor']['item_share']:>8.2f}")
    print("-" * 132)
    print(f"{'合计（12 题要点总数 ' + str(npts) + '）':34} {'':22} "
          f"{tot['bare']['judge']:>7.2f} {tot['anchor']['judge']:>7.2f} "
          f"{tot['anchor']['judge'] - tot['bare']['judge']:>+6.2f}   "
          f"{tot['bare']['strict_literal']:>8.2f} {tot['anchor']['strict_literal']:>8.2f} "
          f"{tot['bare']['strict_fixed']:>6.2f} {tot['anchor']['strict_fixed']:>6.2f}")

    # 每题的证据里「金标准 src 条目」命中 + 注入条目占用
    print("\n---- 逐题明细（证据构成 / 前提） ----")
    for q in qs:
        info = infos[q]
        rr = [r for r in rows if r["q"] == q and r.get("ok")]
        if not rr:
            continue
        print(f"\n【{q}】 锚={info.get('top_id') or '无'} ({info.get('top_title') or '-'}) "
              f"sc={info.get('sc')} lead={info.get('lead')} shared={info.get('shared_n')} "
              f"mat={info.get('materials')} steps={info.get('steps')}")
        for arm in ARMS:
            sub = [r for r in rr if r["arm"] == arm]
            if not sub:
                continue
            for r in sub:
                ev_ids = {e["item_id"] for e in r.get("evidence") or [] if e.get("item_id")}
                froms = [e for e in r.get("evidence") or [] if e["from_item"]]
                print(f"  {arm:6} r{r['run']} judge={r['judge']}/{r['total']} "
                      f"fix={r['strict_fixed']}/{r['total']} ev={r.get('n_ev')} "
                      f"item={len(froms)} 注入首句={froms[0]['quote'][:34] if froms else '-'}")
                print(f"         前提={r.get('premises')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["rank", "gen", "score", "report", "all"])
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.mode == "rank":
        return cmd_rank()
    if a.mode == "gen":
        return cmd_gen(a)
    if a.mode == "score":
        return cmd_score(a)
    if a.mode == "report":
        return cmd_report(a)
    cmd_rank()
    rc = cmd_gen(a)
    if rc:
        return rc
    a.workers = 5
    rc = cmd_score(a)
    if rc:
        return rc
    return cmd_report(a)


if __name__ == "__main__":
    raise SystemExit(main())
