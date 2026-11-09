"""标签体检：把「答了但没对上标签」的题逐条摊开，分出三种情况。

三种情况：
  同源   —— got 与 expect 结构上出自同一份官方文档：also_from 有交集，或 source 的
            slug／标题／URL 相同。这种是标签少并了 id，不是检索挑错。
  异源   —— 结构上不同源。到底是「两条都答上了」还是「真答错」，脚本不判，只把双方的
            逐字原文摊出来给人读。判语义要人读，脚本不猜。
  人工判定 —— 读完异源那一栏之后填进 _review_items/expect_verdicts.json，
            再用 --verdicts 重算效用。四种取值：
              label_bug    标签指错，got 那条才答上　　　　→ 算对
              both_answer  两条都答上（含逐字同义）　　　　→ 算对
              real_wrong   真答错，检索/判定的问题　　　　　→ 算错
              conflict     库内两条官方原文口径互相冲突　　→ 算错，但归数据不归架构

脚本不改任何 expect，也不改 items。它只出证据、出一份待填的判定表。
判定表是旁路文件，人工标注原件 _exp_review_20261104/questions_20261104.json 一个字不动，
所以修正随时可以整份删掉退回原尺子。

用法：
  ./.venv/Scripts/python.exe tools/check_expect.py                 # 体检 P6
  ./.venv/Scripts/python.exe tools/check_expect.py --cfg P6 P6b    # 多档一起
  ./.venv/Scripts/python.exe tools/check_expect.py --verdicts      # 并入人工判定重算
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = ROOT / "_review_items" / "balance_rows.jsonl"
ITEMS = ROOT / "items.json"
AUDIT = ROOT / "_review_items" / "expect_audit.jsonl"
VERDICT_FILE = ROOT / "_review_items" / "expect_verdicts.json"

# 效用尺子：答对 +1，答错 -3，拒答 0。跟 balance_probe 的口径一致。
WRONG_PENALTY = 3

# 人工判定的四种取值：中文名 + 这道题该不该算答对。
VERDICT_KIND = {
    "label_bug": ("标签指错", True),
    "both_answer": ("两条都答上", True),
    "real_wrong": ("真答错", False),
    "conflict": ("库内口径冲突", False),
}


def load_items() -> dict[str, dict]:
    d = json.loads(ITEMS.read_text(encoding="utf-8"))
    lst = d if isinstance(d, list) else (d.get("items") or d.get("data"))
    return {i["id"]: i for i in lst}


def doc_keys(it: dict | None) -> set[str]:
    """这条条目能追到的所有文档标识：slug、标题、URL、also_from。"""
    if not it:
        return set()
    out: set[str] = set()
    src = it.get("source")
    for one in (src if isinstance(src, list) else [src] if isinstance(src, dict) else []):
        for k in ("slug", "title", "url"):
            v = str(one.get(k) or "").strip()
            if v:
                out.add(v)
    for v in it.get("also_from") or []:
        v = str(v).strip()
        if v:
            out.add(v)
    ev = it.get("evidence")
    if isinstance(ev, dict):
        for part in ev.values():
            if isinstance(part, dict):
                v = str(part.get("src") or "").strip()
                if v:
                    out.add(v)
    return out


def quotes(it: dict | None, limit: int = 2) -> list[str]:
    """逐字引文：优先 evidence 里的 quote，其次 answer 正文。"""
    if not it:
        return []
    out: list[str] = []
    ev = it.get("evidence")
    if isinstance(ev, dict):
        for part in ev.values():
            if isinstance(part, dict) and part.get("quote"):
                out.append(str(part["quote"]))
    if not out and it.get("answer"):
        out.append(str(it["answer"]))
    return [q.strip() for q in out[:limit] if q.strip()]


def body(it: dict | None, limit: int = 120) -> str:
    if not it:
        return ""
    txt = str(it.get("answer") or it.get("title") or "").replace("\n", " ")
    return txt[:limit]


def containment(got: dict | None, exp: dict | None) -> str:
    """结构性的字符串包含检查：一方的逐字引文有没有整段出现在另一方的正文里。

    这是字面证据，不是语义判断。命中说明两条讲的是同一段官方原文。
    """
    if not got or not exp:
        return ""
    gb, eb = body(got, 4000), body(exp, 4000)
    hits = []
    for q in quotes(got, 4):
        if len(q) >= 20 and q in eb:
            hits.append("got 的引文整段出现在 expect 正文里")
            break
    for q in quotes(exp, 4):
        if len(q) >= 20 and q in gb:
            hits.append("expect 的引文整段出现在 got 正文里")
            break
    return "；".join(hits)


def two_parts(q: str) -> bool:
    """一题两问：问句里有两个以上的问号。纯字面判据。"""
    return q.count("？") + q.count("?") >= 2


def classify(got: dict | None, exps: list[dict]) -> tuple[str, str]:
    """结构同源只认一种形状：got 是自动摘录（auto=True，pt-/qa- 那类），
    expect 是人工整理条目（auto 为空），且两者共用文档标识。

    两道收紧都是 2026-11-08 做假阳性复核时抓出来的：
      1. 整理条目之间共用文档标识不算同源——一份官方文档会派生出好几个不同事项的
         整理条目，「餐厅」与「供餐时间」都出自饮食服务中心那份 FAQ，「宿舍钥匙」
         与「公寓门禁」都出自学生公寓服务中心那份，答的都不是同一件事。
      2. expect 也是自动条目时不算同源——「微专业怎么报名」标的是整份招生文档
         （doc-…，列 11 个专业），答成某一个专业的报名二维码是覆盖不全，不是同一条。
    """
    if not got or not got.get("auto"):
        return "异源", "got 不是自动摘录，共用文档也不算同源"
    gk = doc_keys(got)
    for e in exps:
        if e.get("auto"):
            continue
        shared = sorted(gk & doc_keys(e))
        if shared:
            return "同源", "共用文档标识 " + "、".join(shared[:3])
    return "异源", ""


def utility(hit: int, wrong: int) -> int:
    return hit - WRONG_PENALTY * wrong


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", nargs="+", default=["P6"])
    ap.add_argument("--verdicts", action="store_true",
                    help="并入 _review_items/expect_verdicts.json 里的人工判定重算效用")
    ap.add_argument("--write", action="store_true", help="把体检结果写进 expect_audit.jsonl")
    a = ap.parse_args()

    rows = [json.loads(l) for l in ROWS.read_text(encoding="utf-8").splitlines() if l.strip()]
    items = load_items()
    verdicts = {}
    if a.verdicts and VERDICT_FILE.exists():
        verdicts = json.loads(VERDICT_FILE.read_text(encoding="utf-8"))

    audit: list[dict] = []
    for cfg in a.cfg:
        rs = [r for r in rows if r.get("cfg") == cfg]
        if not rs:
            print(f"!! {cfg} 在 {ROWS.name} 里没有数据")
            continue
        matched = [r for r in rs if r.get("matched")]
        wrong = [r for r in matched if not r.get("hit")]
        refused = [r for r in rs if not r.get("matched")]
        hit = len(matched) - len(wrong)
        print(f"\n{'=' * 78}\n{cfg}：{len(rs)} 题｜答对 {hit}｜错答 {len(wrong)}｜拒答 {len(refused)}"
              f"｜效用 {utility(hit, len(wrong))}\n{'=' * 78}")

        same, diff = [], []
        for n, r in enumerate(wrong, 1):
            got = items.get(str(r.get("got") or ""))
            exps = [items.get(e) for e in (r.get("expect") or [])]
            exps = [e for e in exps if e]
            struct, why = classify(got, exps)
            # 判定表的键：优先「问句 || got 条目」，其次问句。
            # 同一道题在不同开关档里可能落到不同条目上（4 道题就是这样），
            # 只按问句为键会把甲条目的判定套到乙条目上。
            gid = str(r.get("got") or "")
            raw = verdicts.get(f"{r['q']} || {gid}", verdicts.get(r["q"], ""))
            v = (raw or {}).get("verdict", "") if isinstance(raw, dict) else str(raw or "")
            note = (raw or {}).get("why", "") if isinstance(raw, dict) else ""
            if struct == "同源":
                cls, ok = "同源", True
            elif v in VERDICT_KIND:
                cls, ok = VERDICT_KIND[v][0], VERDICT_KIND[v][1]
                why = "｜".join(x for x in (why, note) if x)
            else:
                cls, ok = "异源未判", None
            rec = {"cfg": cfg, "q": r["q"], "got": r.get("got"), "expect": r.get("expect"),
                   "struct": struct, "verdict": v, "kind": cls, "ok": ok, "why": why,
                   "rule_score": r.get("rule_score"), "model_score": r.get("model_score"),
                   "gate": r.get("gate"), "contain": containment(got, exps[0] if exps else None)}
            audit.append(rec)
            (same if struct == "同源" else diff).append(rec)

            print(f"\n[{n}] {r['q']}")
            print(f"    got    {str(r.get('got')):22} auto={got.get('auto') if got else '?'}"
                  f"  rule={r.get('rule_score')} model={r.get('model_score')} gate={r.get('gate') or '-'}")
            for q in quotes(got, 1):
                print(f"           引文：{q[:110]}")
            if not quotes(got, 1):
                print(f"           正文：{body(got)}")
            print(f"    expect {'、'.join(str(e) for e in (r.get('expect') or []))}")
            for e in exps[:2]:
                print(f"           {e['id']:22} auto={e.get('auto')}  正文：{body(e, 90)}")
            if rec["contain"]:
                print(f"    字面证据：{rec['contain']}")
            mark = {True: "算对", False: "算错", None: "待人工确认"}[ok]
            print(f"    判定：{cls}（{mark}）" + (f"　{why}" if why else ""))

        # 修正后的口径：同源与人工判成「标签指错／两条都答上」的算答对，
        # 人工判成「真答错／库内口径冲突」的仍算错，没判的保守按错答计。
        n_same = len(same)
        n_unjudged = sum(1 for x in diff if x["ok"] is None)
        n_ok = sum(1 for x in diff if x["ok"] is True)
        n_real = sum(1 for x in diff if x["verdict"] == "real_wrong")
        n_conf = sum(1 for x in diff if x["verdict"] == "conflict")
        fixed_hit = hit + n_same + n_ok
        fixed_wrong = len(wrong) - n_same - n_ok
        print(f"\n---- {cfg} 汇总 ----")
        print(f"结构同源（also_from／source 标题或 URL 相同）：{n_same} 道 → 算对")
        print(f"异源（脚本不判语义）　　　　　　　　　　　　：{len(diff)} 道")
        print(f"  人工判成算对（标签指错／两条都答上）　　　：{n_ok} 道")
        print(f"  人工判成真答错（检索/判定的问题）　　　　　：{n_real} 道")
        print(f"  人工判成库内口径冲突（数据问题，不归架构）：{n_conf} 道")
        print(f"  还没判　　　　　　　　　　　　　　　　　　：{n_unjudged} 道（保守按错答计）")
        print(f"效用（现尺子，只认 expect id）：{utility(hit, len(wrong))}")
        print(f"效用（修正后）　　　　　　　　：{utility(fixed_hit, fixed_wrong)}"
              f"　＝ 答对 {fixed_hit} − 3×错答 {fixed_wrong}")
        if n_unjudged:
            top = utility(fixed_hit + n_unjudged, fixed_wrong - n_unjudged)
            print(f"效用上限（未判的 {n_unjudged} 道全算对）：{top}")
            print(f"→ 真实效用落在 {utility(fixed_hit, fixed_wrong)} 到 {top} 之间，"
                  f"区间宽 {top - utility(fixed_hit, fixed_wrong)}，判完才收得住。")

        if refused:
            tp = [r for r in refused if two_parts(r["q"])]
            print(f"\n---- {cfg} 拒答 {len(refused)} 道（不扣效用，救回一道 +1）----")
            print(f"一题两问（问句里两个问号）：{len(tp)} 道")
            for r in tp:
                print(f"    {r['q'][:34]:36} rule={r.get('rule_score')} gate={r.get('gate') or '-'}")
            print(f"其余（口语改写／字面鸿沟）：{len(refused) - len(tp)} 道")
            for r in refused:
                if not two_parts(r["q"]):
                    print(f"    {r['q'][:34]:36} rule={r.get('rule_score')} gate={r.get('gate') or '-'}"
                          f" src={r.get('src')}")

    if a.write:
        with AUDIT.open("w", encoding="utf-8") as f:
            for rec in audit:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        todo = [x for x in audit if x["ok"] is None]
        print(f"\n已写 {AUDIT.name}（{len(audit)} 行）")
        if todo and not VERDICT_FILE.exists():
            VERDICT_FILE.write_text(json.dumps(
                {f"{x['q']} || {x['got']}": {"verdict": "", "why": ""} for x in todo},
                ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"已生成待填判定表 {VERDICT_FILE.name}（{len(todo)} 道异源题）：")
            print('  verdict 填 ' + "／".join(f'"{k}"（{v[0]}）' for k, v in VERDICT_KIND.items()) + "，")
            print("  why 填一句证据（引哪条原文的哪句话），填完加 --verdicts 重算。")
        elif todo:
            print(f"{len(todo)} 道异源题还没判定，判定表在 {VERDICT_FILE.name}（已存在，未覆盖）")

    print("\n注：本脚本没有修改任何 expect 标签，也没有改 items.json。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
