"""拒答与错答的平衡曲线：跑一次带埋点的实测，离线扫「事后过滤」策略。

标签来源两份，合起来去重：
  A. _exp_review_20261104/questions_20261104.json 的 T+R（人工标过 expect 条目 id）
  B. _review_items/paraphrase_abc.py 的 16 组 × 3 问法（同义不同词难题集）

真实跑的只有四种开关组合；阈值类的策略不能靠事后模拟（改阈值会改送进模型的候选），
所以这里只模拟「输出端过滤」：模型判死就不代答、置信低于 X 就改拒答。
产物 _review_items/balance_rows.jsonl 每行一题，含复算所需的分数。

用法：
  ./.venv/Scripts/python.exe tools/balance_probe.py run          # 四档实测
  ./.venv/Scripts/python.exe tools/balance_probe.py analyze      # 离线扫过滤策略
"""
from __future__ import annotations

import argparse
import io
import os
import json
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_review_items"))

import app  # noqa: E402

ROWS = ROOT / "_review_items" / "balance_rows.jsonl"
LABELED = ROOT / "_exp_review_20261104" / "questions_20261104.json"

# 2026-11-07 定案档（默认值就是它）：融合检索＋组装 rescue＋改写腿 B＋两道闸＋地板 0.7
FINAL = {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B",
         "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}

CONFIGS = [
    ("P0", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "off", "REWRITE_PRE": "OFF"}),
    ("P1", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "OFF"}),
    ("P2", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B"}),
    ("P3", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "both", "REWRITE_PRE": "B"}),
    # P5 = 定案档：在 P2 之上把两道闸真装进代码，验「事后模拟」那行数能不能复现
    ("P5", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B",
            "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}),
    # P6 = 定案档 ＋「通用做法算答上」判分片（prompt_parts 里的 rerank.judge_generic）
    ("P6", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B",
            "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}),
    # P6b = 与 P6 完全同档同码，只比重跑一次：量 100 题单档的运行间噪声带
    ("P6b", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B",
             "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}),
    # —— 2026-11-07 装闸世界的逐项归因：三档都带 judge_generic，只动点名的那一个开关 ——
    # P7 = 关掉组装 rescue：rescue 唯一的独立测量是装闸前的 -3 效用，装闸后从没归因
    ("P7", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "off", "REWRITE_PRE": "B",
            "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}),
    # P11 = 关掉改写腿 B：B 的 +6 是装闸前测的，装闸后（有闸兜着）还值多少不知道
    ("P11", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "OFF",
             "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.7}),
    # P12 = 地板从 0.7 抬到 0.75 的实装档：事后扫描说 60 vs 61，但被拦下的题真跑时会再走
    # 组装 rescue，双重计，所以必须实装
    ("P12", {"RETRIEVAL_MODE": "fusion", "ASSEMBLE_MODE": "rescue", "REWRITE_PRE": "B",
             "DECLINE_REFUSES": True, "MIN_ANSWER_CONF": 0.75}),
    # —— 2026-11-07 Task 12：最终世界（定案档＋上下文 B＋C）之上的四件候选，一律单动一个 ——
    # F0a/F0b 同码两跑，先量这把尺子现在的分辨率，不引用昨天的数
    ("F0a", FINAL),
    ("F0b", FINAL),
    ("F1", {**FINAL, "TIE_BREAK": True}),
    ("F2", {**FINAL, "RECHECK_SKIP_ABOVE": 85}),
    ("F3", {**FINAL, "RECHECK_SKIP_ABOVE": 95}),
    ("F4", {**FINAL, "POOL_META": True}),
    # F4b 与 F4 同码重跑：F4 的净收益落在 4 道基线三跑一致的题上，复跑一次看这 4 道是否复现
    ("F4b", {**FINAL, "POOL_META": True}),
]


def questions() -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    data = json.loads(LABELED.read_text(encoding="utf-8"))
    for grp in ("R", "T"):
        for x in data.get(grp, []):
            if not x.get("expect") or x["q"] in seen:
                continue
            seen.add(x["q"])
            out.append({"q": x["q"], "expect": list(x["expect"]), "src": "labeled"})
    import paraphrase_abc as pp  # noqa: F401  (只为拿 GROUPS，不跑它的主流程)
    for gid, qs in pp.GROUPS:
        for q in qs:
            if q in seen:
                continue
            seen.add(q)
            out.append({"q": q, "expect": [gid], "src": "paraphrase"})
    return out


_lock = threading.Lock()


def run_one(cfg: str, rec: dict) -> dict:
    q = rec["q"]
    t0 = time.time()
    ranked = app.rank(q)
    top, top_score = ranked[0]
    try:
        d = app.answer_question(q, router_llm=True)
    except Exception as e:  # noqa: BLE001
        # 只留错误文本的话，崩在哪一行永远查不出来（F4b 那道就这么悬着）
        tb = traceback.format_exc(limit=6).strip().splitlines()[-4:]
        return {"cfg": cfg, "q": q, "err": str(e)[:120], "tb": " ｜ ".join(tb)[:400]}
    mr = d.get("model_route") or {}
    rr = d.get("rerank") or {}
    got = (d.get("item") or {}).get("id")
    return {
        "cfg": cfg, "q": q, "src": rec["src"], "expect": rec["expect"],
        "matched": bool(d.get("matched")), "got": got,
        "hit": bool(got) and got in set(rec["expect"]),
        "conf": d.get("confidence"),
        "rule_top": top["id"], "rule_score": top_score, "rule_auto": bool(top.get("auto")),
        "gate": mr.get("gate"), "model_score": mr.get("score"),
        "changed": mr.get("changed"), "rescue": mr.get("rescue"),
        "pre_added": mr.get("pre_added"), "assembly": mr.get("assembly"),
        "answers_n": len([p for p in (d.get("answers") or []) if p.get("found")]),
        "assembled": sum(1 for p in (d.get("answers") or []) if p.get("focus") == "assembly"),
        "ms": round((time.time() - t0) * 1000),
    }


def do_run(workers: int, limit: int = 0) -> int:
    lock = ROOT / "_review_items" / "balance.lock"
    try:
        # 防重入：上一版踩过坑——以为已经退掉的进程其实还在跑，两个进程写同一批档位，
        # 每题落两行，并发还被顶到 10，整天的数全废。锁在就说明有人在跑，别再起一个。
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(f"另一个 run 还在跑（{lock}）；确认它真死了再删这个锁文件")
        return 2
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        return _do_run(workers, limit)
    finally:
        lock.unlink(missing_ok=True)


def _preflight() -> str:
    """跑一整档之前先问一次模型：接口不通就停，别把 100 题×N 档跑成一堆废数。

    2026-11-07 踩过：Key 余额耗尽返 402，六档全部只走规则腿，对/错/拒一模一样、
    同码两跑 0 翻转，看着像「四件候选都没有边际」，其实是模型层一次都没参与。
    """
    if not app.api_key():
        return "没配 DEEPSEEK_API_KEY"
    try:
        app.ds_chat([{"role": "system", "content": '只输出 JSON：{"ok": true}'}],
                    max_tokens=20, json_mode=True)
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {str(e)[:160]}"
    return ""


def _do_run(workers: int, limit: int = 0) -> int:
    fail = _preflight()
    if fail:
        print(f"接口预检失败，整批不跑：{fail}")
        print("先确认 Key 余额与可用性，再重跑；已落盘的废档请连 cfg 名一起删掉。")
        return 3
    qs = questions()
    if limit:
        qs = qs[:limit]
    print(f"带标签题数 {len(qs)}（labeled {sum(1 for x in qs if x['src']=='labeled')} + "
          f"paraphrase {sum(1 for x in qs if x['src']=='paraphrase')}）")
    done_cfg = set()
    if ROWS.exists():
        for line in io.open(ROWS, encoding="utf-8"):
            if line.strip():
                done_cfg.add(json.loads(line)["cfg"])
    for name, env in CONFIGS:
        if name in done_cfg:
            print(f"[{name}] 已有产物，跳过")
            continue
        for k, v in env.items():
            setattr(app, k, v)
        t0 = time.time()
        rows: list[dict] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(run_one, name, r) for r in qs]
            for i, f in enumerate(futs, 1):
                rows.append(f.result())
                if i % 20 == 0:
                    print(f"   {name} {i}/{len(qs)} …")
        with io.open(ROWS, "a", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        hits = sum(1 for r in rows if r.get("hit"))
        wrong = sum(1 for r in rows if r.get("matched") and not r.get("hit"))
        ref = sum(1 for r in rows if not r.get("matched"))
        med = sorted(r["ms"] for r in rows if r.get("ms"))[len(rows) // 2] if rows else 0
        ties = len(app.TIE_SEEN); app.TIE_SEEN.clear()
        unr = sum(1 for r in rows if r.get("gate") == "rerank_unavailable")
        print(f"[{name}] 对 {hits} 错答 {wrong} 拒答 {ref} 共 {len(rows)} | 每题中位 {med/1000:.1f}s "
              f"| 同分并列 {ties} 次 | rerank 不可用 {unr} 题 "
              f"| 墙钟 {time.time()-t0:.0f}s")
    return 0


def analyze() -> int:
    rows: dict[str, list[dict]] = {}
    if not ROWS.exists():
        print("还没有产物，先跑 run")
        return 1
    for line in io.open(ROWS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            rows.setdefault(r["cfg"], []).append(r)
    print(f"{'策略':<34}{'答对':>6}{'错答':>6}{'拒答':>6}{'准确率':>9}{'覆盖率':>9}{'效用(-3×错)':>12}")
    for name in sorted(rows):
        base = rows[name]
        n = len(base)
        for label, keep in (
            ("现状（不过滤）", lambda r: r["matched"]),
            ("模型判死即不代答", lambda r: r["matched"] and r.get("gate") != "llm_declined"),
            ("判死即不代答 + conf<0.7 拒", lambda r: (r["matched"] and r.get("gate") != "llm_declined"
                                                     and (r["conf"] or 0) >= 0.7)),
            ("判死即不代答 + conf<0.8 拒", lambda r: (r["matched"] and r.get("gate") != "llm_declined"
                                                     and (r["conf"] or 0) >= 0.8)),
            ("判死即不代答 + conf<0.9 拒", lambda r: (r["matched"] and r.get("gate") != "llm_declined"
                                                     and (r["conf"] or 0) >= 0.9)),
        ):
            kept = [r for r in base if keep(r)]
            hits = sum(1 for r in kept if r["hit"])
            wrong = len(kept) - hits
            refuse = n - len(kept)
            acc = hits / len(kept) if kept else 0.0
            cov = len(kept) / n
            print(f"{name+'/'+label:<34}{hits:>6}{wrong:>6}{refuse:>6}{acc*100:>8.1f}%{cov*100:>8.1f}%"
                  f"{hits - 3*wrong:>12}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 题（冒烟用）")
    a = ap.parse_args()
    return do_run(a.workers, a.limit) if a.mode == "run" else analyze()


if __name__ == "__main__":
    raise SystemExit(main())
