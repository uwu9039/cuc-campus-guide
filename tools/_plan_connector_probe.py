# -*- coding: utf-8 -*-
"""离线测量：给 `_synth_plan` 加「连接规则短句」后，候选池对金标准的召回变化。

只测检索/建池，不生成答案、不评答案。基线短句与模型规则短句都缓存，重跑一致。

用法（Windows，仓库根目录）：
    ./.venv/Scripts/python.exe -X utf8 tools/_plan_connector_probe.py
    ./.venv/Scripts/python.exe -X utf8 tools/_plan_connector_probe.py --refresh
    ./.venv/Scripts/python.exe -X utf8 tools/_plan_connector_probe.py --no-llm

两个口径：
  loose  金标准 kw 出现在池子的整段文本里（任务书口径，跨引文也算）
  strict 金标准 kw 全部出现在**同一条引文**里（能被当成一条证据引用）
输出：控制台 markdown + `_review_items/_plan_connector_probe.json`
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOLDEN = "_review_items/golden_20261111.json"
CACHE = "_review_items/_plan_connector_cache.json"
OUT = "_review_items/_plan_connector_probe.json"

# ---------------------------------------------------------------------------
# 要贴进 `_SYNTH_PLAN_PROMPT` 的补丁正文（与 plan_connector_proposal.md 逐字一致）
# ---------------------------------------------------------------------------
CONNECTOR_PATCH = (
    "3) 1～2 条**规则短句**，专门去查「把前提连起来的那条规则」，不复述用户说的那件事。\n"
    "用户口吻的短句只查得到「提到挂科」的段落；能推出结论的常常是**没提挂科**的条款：\n"
    "补考按 60 分计入平均分与绩点、综合成绩怎么合成、基本条件第几条、休学期间不享受什么、\n"
    "同一学年只能拿一个。条款用的是制度词，不是用户词。\n"
    "做法：先判这道题卡在哪一类规则（下表选一类，最多两类），再按那一类的制度词写短句。\n"
    "短句保留题目主体词，但动词和名词换成条款里的写法：\n"
    "· 成绩记载：`<主体> 补考 重修 成绩 记载 按 60 分 计入 平均分 学分绩点`\n"
    "· 排序合成：`<主体> 综合成绩 构成 计算 学业表现 权重`\n"
    "· 资格门槛：`<主体> 基本条件 不得申请 情形`\n"
    "· 时限解除：`<主体> 期限 起算 届满 解除 程序`\n"
    "· 待遇状态：`<主体> 期间 享受 不享受 停发 中止`\n"
    "· 互斥叠加：`<主体> 同时 获得 同一学年 只能`\n"
    "· 标准金额：`<主体> 标准 每生每学年 元 金额 发放`\n"
    "· 办理兑付：`<主体> 地点 材料 工本费 当场 流程`\n"
    "· 阈值后果：`<主体> 超过 比例 不及格 结业 撤销`\n"
    "· 适用人群：`<主体> 适用于 本科生 研究生 范围`\n"
    "· 覆盖接入：`<主体> 覆盖 范围 无线 认证 终端 上限`\n"
    "D) 规则短句不许复述用户的话：用户说「挂科」，规则短句不能只写「挂科」，\n"
    "要写「补考 重修 成绩 按 60 分 计入 平均分」，让条款自己的词去撞检索。\n"
    "E) 规则短句只写 1～2 条，宁可少：它是补充腿，写多了会把主体短句挤掉。\n"
    '输出再加一个键：{"rule_queries": ["规则短句1", "规则短句2"]}\n'
)

# 条款词表：题型 → 触发词 → 制度词。顺序=优先级（每题取前 2 类）。
GENRES = [
    ("score", "成绩记载",
     r"挂科|补考|重修|补修|成绩|绩点|GPA|排名|免修|及格|不及格",
     "补考 重修 成绩 记载 按 60 分 计入 平均分 学分绩点",
     "补考/重修通过按 60 分计入平均分与 GPA，是「补考算不算」的唯一出口"),
    ("rank", "排序合成",
     r"保研|推免|综测|综合测评|综合成绩|评奖|评优|名额",
     "综合成绩 构成 计算 学业表现 权重",
     "推免/评优按「综合成绩=学业表现×权重+全面发展」排序"),
    ("excl", "互斥叠加",
     r"同时|一起|都能|两个|冲突|兼得|还能不能",
     "同时 获得 同一学年 只能",
     "「能不能同时拿」写在资助办法的互斥条里，不在任一奖项的标准条里"),
    ("money", "标准金额",
     r"多少钱|发多少|金额|标准|每小时|每月|一年|一学年|一小时",
     "标准 每生每学年 元 金额 发放",
     "金额答案在「资助范围和标准」条，不在「申请条件」条"),
    ("elig", "资格门槛",
     r"保研|推免|转专业|毕业|学位|入党|申请|奖学金",
     "基本条件 不得申请 情形",
     "资格条款是穷尽枚举，要查条款本身，不是查用户说的那个词"),
    ("time", "时限解除",
     r"处分|记过|警告|察看|期限|有效期|解除|届满",
     "期限 起算 届满 解除 程序",
     "「影响多久」的答案是处分期限+解除程序"),
    ("status", "待遇状态",
     r"休学|延期|保留学籍|停学|处分|住宿|公费医疗|医保|待遇",
     "期间 享受 不享受 停发 中止",
     "休学/延期/处分期间待遇是「在籍状态」条款，跟问的那个待遇不是同一句"),
    ("proc", "办理兑付",
     r"怎么办|怎么补|补办|办理|材料|多久拿到|费用|工本费|地点",
     "地点 材料 工本费 当场 流程",
     "补办类答案在「地点+材料+费用+当场」的办理条里"),
    ("thresh", "阈值后果",
     r"查重|重复率|复制比|比例|超过|上限|结业|撤销",
     "超过 比例 不及格 结业 撤销",
     "查重类答案是「超过 X% → 不及格/结业/撤销」的分档条"),
    ("scope", "适用人群",
     r"本科生|研究生|硕士|博士|延期|休学|留学生",
     "适用于 本科生 研究生 范围",
     "同一条规定常只约束研究生，答案要标对象"),
    ("net", "覆盖接入",
     r"校园网|无线|WiFi|wifi|覆盖|联网|上网",
     "覆盖 范围 无线 认证 终端 上限",
     "「宿舍有没有网」= 覆盖范围+接入方式+终端上限"),
]
MAX_GENRES = 2
RESERVE = 10  # 规则池前插条数（与 cap 无关，见 proposal §方案）
RULE_POOL = 32


def _topic_terms(queries: list[str], question: str) -> list[str]:
    out: list[str] = []
    for q in queries:
        tok = (q.split() or [""])[0].strip()
        if 1 < len(tok) <= 6 and tok not in out:
            out.append(tok)
    if not out:
        head = re.split(r"[，。？！?！\s]", question)[0][:6]
        if head:
            out.append(head)
    return out[:2]


def rule_queries_for(question: str, base_queries: list[str]) -> list[dict]:
    """确定性「规则短句」：判题型 → 主体词 + 制度词（生产上由模型做）。"""
    topics = _topic_terms(base_queries, question)
    picked = []
    for key, name, pat, vocab, why in GENRES:
        if re.search(pat, question):
            picked.append({"genre": key, "name": name, "vocab": vocab, "why": why})
        if len(picked) >= MAX_GENRES:
            break
    out = []
    for i, g in enumerate(picked):
        t = topics[min(i, len(topics) - 1)] if topics else ""
        out.append({"query": ("%s %s" % (t, g["vocab"])).strip(),
                    "genre": g["genre"], "name": g["name"]})
    return out


def norm(s: str) -> str:
    return "".join(str(s or "").split()).lower()


def _alts(kw) -> list[str]:
    return [norm(x) for x in str(kw).split("|") if norm(x)]


def point_loose(point: dict, pooled: str) -> bool:
    for kw in (point.get("kw") or []):
        a = _alts(kw)
        if a and not any(x in pooled for x in a):
            return False
    return True


def point_strict(point: dict, cands: list[dict]) -> str:
    """kw 全落在同一条引文里 → 返回该引文，否则空串。"""
    for c in cands:
        q = norm(c.get("quote") or "")
        if not q:
            continue
        ok = True
        for kw in (point.get("kw") or []):
            a = _alts(kw)
            if a and not any(x in q for x in a):
                ok = False
                break
        if ok:
            return str(c.get("quote") or "")
    return ""


def pool_text(cands) -> str:
    return norm(" ".join(str(c.get("quote") or "") for c in cands))


ITEM_SRC = re.compile(r"^(it|pt|doc|rule|qa|xyk|jwc|sushe|xueji|tuimian|xt|yjs|"
                      r"xinsheng|lib|xyy|jiangxuejin|zxj|zb|xszz|benke|rule)-")


def src_ids(point: dict) -> list[str]:
    raw = str(point.get("src") or "")
    return [x for x in re.split(r"[/、,，\s]+", raw) if x.strip() and ITEM_SRC.match(x)]


def load_cache() -> dict:
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(c: dict) -> None:
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=1)


def get_plan(app, q, cache, refresh) -> dict:
    if not refresh and (cache.get(q) or {}).get("queries"):
        return cache[q]
    st = {}
    t0 = time.time()
    prem, qs = app._synth_plan(q, st)
    cache[q] = {**(cache.get(q) or {}),
                "premises": prem, "queries": qs, "status": st,
                "sec": round(time.time() - t0, 1)}
    print("  plan(%.1fs) %r" % (cache[q]["sec"], qs), flush=True)
    save_cache(cache)
    return cache[q]


def get_llm_rules(app, q, cache, refresh) -> dict:
    if not refresh and (cache.get(q) or {}).get("llm_rules") is not None:
        return cache[q]
    prompt = app._SYNTH_PLAN_PROMPT + CONNECTOR_PATCH
    rq, err = [], ""
    try:
        raw = app.ds_chat([{"role": "system", "content": prompt},
                           {"role": "user", "content": q}],
                          max_tokens=420, json_mode=True)
        data = json.loads(raw) or {}
        rq = data.get("rule_queries") or []
        if isinstance(rq, str):
            rq = [rq]
        rq = [str(x).strip() for x in rq if str(x).strip()][:2]
    except Exception as e:  # noqa: BLE001
        err = "%s: %s" % (type(e).__name__, e)
    cache[q] = {**(cache.get(q) or {}), "llm_rules": rq, "llm_err": err}
    print("  llm_rules %r %s" % (rq, err), flush=True)
    save_cache(cache)
    return cache[q]


def build(app, queries, premises, cap, question):
    return app._synth_candidates(queries, premises, cap=cap, question=question)


def merge_reserve(base_cands, rule_cands, reserve=RESERVE):
    """主池不动，规则池按 cover 排序后前插 reserve 条（去重）。"""
    if not rule_cands:
        return base_cands
    seen = {norm(c.get("quote"))[:80] for c in base_cands}
    extra = [c for c in rule_cands if norm(c.get("quote"))[:80] not in seen]
    extra.sort(key=lambda c: (-int(c.get("cover") or 0), -len(c.get("hits") or ())))
    return base_cands + extra[:reserve]


def build_rule_pool(app, rule_q, premises, question, rule_pool=RULE_POOL):
    if not rule_q:
        return []
    return build(app, rule_q, premises, rule_pool, question)


def score_variant(cands, pts):
    pooled = pool_text(cands)
    loose = [point_loose(p, pooled) for p in pts]
    strict = [point_strict(p, cands) for p in pts]
    srcs = [{c.get("item_id") for c in cands} & set(src_ids(p)) for p in pts]
    return {"n": len(cands), "loose": sum(loose), "strict": sum(bool(x) for x in strict),
            "src": sum(bool(x) for x in srcs), "loose_list": loose,
            "strict_list": [bool(x) for x in strict], "strict_q": strict}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = set(sys.argv[1:])
    refresh = "--refresh" in args
    use_llm = "--no-llm" not in args

    import app  # noqa: E402

    golden = json.load(open(GOLDEN, encoding="utf-8"))
    cases = golden["cases"]
    cache = load_cache()
    rows = []

    for ci, case in enumerate(cases, 1):
        q, pts = case["q"], case["points"]
        print("[%d] %s" % (ci, q), flush=True)
        plan = get_plan(app, q, cache, refresh)
        base_q, prem = plan["queries"], plan["premises"]
        det = rule_queries_for(q, base_q)
        det_q = [d["query"] for d in det]
        llm_q = []
        if use_llm:
            llm_q = get_llm_rules(app, q, cache, refresh).get("llm_rules") or []

        variants = {}
        base_cands = build(app, base_q, prem, 48, q)
        variants["base"] = score_variant(base_cands, pts)
        variants["conn48"] = score_variant(
            build(app, base_q + det_q, prem, 48, q), pts)
        variants["conn56"] = score_variant(
            build(app, base_q + det_q, prem, 56, q), pts)
        rule_cands = build_rule_pool(app, det_q, prem, q)
        variants["res48"] = score_variant(
            merge_reserve(base_cands, rule_cands), pts)
        variants["trunc5"] = score_variant(
            build(app, (base_q + det_q)[:5], prem, 48, q), pts)
        if llm_q:
            llm_cands = build_rule_pool(app, llm_q, prem, q)
            variants["llm_res"] = score_variant(
                merge_reserve(base_cands, llm_cands), pts)

        points = []
        for pi, p in enumerate(pts):
            # 归因：这条要点是不是只在规则池里出现
            in_rule = bool(point_strict(p, rule_cands)) or point_loose(
                p, pool_text(rule_cands))
            points.append({
                "i": pi + 1, "kw": p.get("kw"), "src": p.get("src"),
                "base_loose": variants["base"]["loose_list"][pi],
                "base_strict": variants["base"]["strict_list"][pi],
                "res_loose": variants["res48"]["loose_list"][pi],
                "res_strict": variants["res48"]["strict_list"][pi],
                "res_q": variants["res48"]["strict_q"][pi][:120],
                "in_rule_pool": in_rule,
            })
        rows.append({"q": q, "premises": prem, "base_queries": base_q,
                     "det_rules": det, "llm_rules": llm_q,
                     "llm_err": plan.get("llm_err"),
                     "n_points": len(pts), "variants": variants, "points": points})
        b = variants["base"]
        r = variants["res48"]
        print("  base loose %d/%d strict %d/%d | res loose %d/%d strict %d/%d"
              % (b["loose"], len(pts), b["strict"], len(pts),
                 r["loose"], len(pts), r["strict"], len(pts)), flush=True)

    # ---------------- 汇总 ----------------
    total = sum(r["n_points"] for r in rows)

    def agg(key, field):
        num = sum(r["variants"][key][field] for r in rows if key in r["variants"])
        den = sum(r["n_points"] for r in rows if key in r["variants"])
        return num, den

    print("\n## 汇总（%d 题 / %d 要点）\n" % (len(rows), total))
    print("| 变体 | 说明 | loose(kw在池内) | strict(同一引文) | 池均条数 |")
    print("|---|---|---|---|---|")
    desc = {"base": "现状：只用模型给的短句，cap 48",
            "trunc5": "直接把规则短句接在后面、仍按 (queries)[:5] 截断",
            "conn48": "规则短句混进同一条检索、cap 48",
            "conn56": "规则短句混进同一条检索、cap 56",
            "res48": "规则短句单独建池、去重前插 ≤%d（对照，不建议）" % RESERVE,
            "llm_res": "模型按补丁自己写的规则短句 + 本方案"}
    for key in ("base", "trunc5", "conn48", "conn56", "res48", "llm_res"):
        if not any(key in r["variants"] for r in rows):
            continue
        lo, den = agg(key, "loose")
        st, _ = agg(key, "strict")
        sizes = [r["variants"][key]["n"] for r in rows if key in r["variants"]]
        print("| %s | %s | %d/%d (%.1f%%) | %d/%d (%.1f%%) | %.1f |"
              % (key, desc[key], lo, den, 100.0 * lo / den,
                 st, den, 100.0 * st / den, sum(sizes) / len(sizes)))

    print("\n| # | 题 | base loose | base strict | res loose | res strict | 新捞回(strict) |")
    print("|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        b, v = r["variants"]["base"], r["variants"]["res48"]
        got = ["P%d" % p["i"] for p in r["points"]
               if p["res_strict"] and not p["base_strict"]]
        print("| %d | %s | %d/%d | %d/%d | %d/%d | %d/%d | %s |"
              % (i, r["q"][:20], b["loose"], r["n_points"], b["strict"],
                 r["n_points"], v["loose"], r["n_points"], v["strict"],
                 r["n_points"], ",".join(got) or "—"))

    print("\n### 方案后仍 strict 漏的要点")
    miss = []
    for r in rows:
        for p in r["points"]:
            if not p["res_strict"]:
                miss.append({"q": r["q"], "p": p["i"], "kw": p["kw"], "src": p["src"],
                             "loose": p["res_loose"]})
    for m in miss:
        print("  - %s P%d %s src=%s (loose=%s)"
              % (m["q"][:16], m["p"], m["kw"], m["src"], m["loose"]))

    print("\n### 新捞回明细（strict）")
    for r in rows:
        for p in r["points"]:
            if p["res_strict"] and not p["base_strict"]:
                print("  + %s P%d %s ← %s | %s"
                      % (r["q"][:14], p["i"], p["kw"],
                         [d["name"] for d in r["det_rules"]], p["res_q"][:80]))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "patch": CONNECTOR_PATCH,
                   "genres": [{"key": g[0], "name": g[1], "pat": g[2],
                               "vocab": g[3], "why": g[4]} for g in GENRES],
                   "reserve": RESERVE, "rows": rows,
                   "agg": {k: {"loose": agg(k, "loose"), "strict": agg(k, "strict")}
                           for k in ("base", "trunc5", "conn48", "conn56",
                                     "res48", "llm_res")
                           if any(k in r["variants"] for r in rows)},
                   "missed": miss}, f, ensure_ascii=False, indent=1)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
