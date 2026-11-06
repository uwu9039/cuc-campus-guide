"""两件新接的模型判断的回归：② 一题两问补面（llm_facet_fill）、方案D甲 词表外专名映射（llm_proper_map）。

全部拿桩替掉模型接口，不发真请求。盯四件事：
  1. 模型说「已经答到了」就不许再补一面；说没答到、且摘的句子在条目原文里逐字存在才补。
  2. 模型编出来的句子、挑了已经答过的问面、报的「补的是哪一问」不在系统给的那几问里——都不补。
  3. 接口挂了要留下失败记录，答案照旧，不能变成答不上。
  4. 规则腿一个模型调用都不许发；专名映射只在问句里的字母名对不上词表时才开火，
     映射回来的名字必须在词表里字面存在，端进候选的条目必须自己写了那个名字。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:130])


ITEM = {
    "id": "t-facet-hours", "title": "图书馆开放时间", "kind": "curated",
    "answer": "逸夫图书馆一层大厅服务台办理。",
    "hours": "周末及节假日 9:00-17:00，寒另行安排",
    "location": "逸夫图书馆一层大厅",
    "evidence": {
        "answer": {"quote": "逸夫图书馆一层大厅服务台办理。", "src": "f-1"},
        "location": {"quote": "逸夫图书馆一层大厅", "src": "f-1"},
        "hours": {"quote": "周末及节假日 9:00-17:00，寒另行安排", "src": "f-1"},
    },
}
Q = "图书馆在哪？周末和节假日开吗？"
# 已经端出去的是「办理地点」那一面，缺的是「周末开吗」——补它要挑「办理时间」
PARTS = [app._answer_one(ITEM, "location", {}, Q)]
UNASKED = ["周末和节假日开吗"]


def stub(payload):
    """把模型接口换成固定回包；顺便记下每次调用的提示词。"""
    calls = []

    def _chat(messages, max_tokens=600, json_mode=False, thinking=False):
        calls.append(messages[-1]["content"])
        if isinstance(payload, Exception):
            raise payload
        return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    return _chat, calls


def fill(reply):
    chat, calls = stub(reply)
    old_chat, old_key = app.ds_chat, app.api_key
    app.ds_chat, app.api_key = chat, (lambda: "test-key")
    try:
        out = app.llm_facet_fill(Q, ITEM, PARTS, UNASKED, {})
    finally:
        app.ds_chat, app.api_key = old_chat, old_key
    return out, calls


# ---- ② 补面 ----
check("②问面菜单只列没答过的",
      "办理地点" not in app._facet_menu(PARTS) and "办理时间" in app._facet_menu(PARTS),
      "现有面 %s / 菜单 %s" % ([p["focus"] for p in PARTS], app._facet_menu(PARTS)[:6]))

out, _ = fill({"covers": "yes", "facet": None, "snippet": None, "fills": None, "why": "已经说了周末"})
check("②模型说答到了就不补", out["gate"] == "covered" and not out.get("part"), str(out)[:120])

out, calls = fill({"covers": "no", "facet": "办理时间",
                   "snippet": "周末及节假日 9:00-17:00", "fills": "周末和节假日开吗", "why": "答的是工作日"})
ok = (out["gate"] == "filled" and out.get("part") and out["part"]["focus"] == "hours"
      and out["part"]["found"] and out.get("fills") == "周末和节假日开吗")
check("②逐字原句成立就补面", ok, str(out)[:140])
check("②提示词给了缺的那一问", bool(calls) and "周末和节假日开吗" in calls[0],
      (calls[0][:80] if calls else "没调用"))
# json_mode=True 时 DeepSeek 要提示词里出现 JSON 字样，没有就整条请求 400（2026-11-05 真接口踩到）
check("②提示词写明只输出 JSON", bool(calls) and "只输出 JSON" in calls[0],
      (calls[0][-70:] if calls else "没调用"))

out, _ = fill({"covers": "no", "facet": "办理时间", "snippet": "周末全天开放，通宵自习",
               "fills": "周末和节假日开吗", "why": "编的"})
check("②编出来的句子不补", out["gate"] == "declined" and "逐字找不到" in out["why"], str(out)[:120])

out, _ = fill({"covers": "no", "facet": "办理地点", "snippet": "周末及节假日 9:00-17:00",
               "fills": "周末和节假日开吗", "why": "挑错了面"})
check("②已经答过的问面不补", out["gate"] == "declined" and "已经答过" in out["why"], str(out)[:120])

out, _ = fill({"covers": "no", "facet": "费用", "snippet": "周末及节假日 9:00-17:00",
               "fills": "押金多少", "why": "自己报了个没问过的一问"})
check("②补的是哪一问必须照抄系统报的那问", out["gate"] == "declined", str(out)[:120])

out, _ = fill(RuntimeError("429 too many requests"))
check("②接口失败留记录", out["gate"] == "error" and out.get("error"), str(out)[:120])


def fill_labels(reply, labels):
    chat, calls = stub(reply)
    old_chat, old_key = app.ds_chat, app.api_key
    app.ds_chat, app.api_key = chat, (lambda: "test-key")
    try:
        out = app.llm_facet_fill(Q, ITEM, PARTS, labels, {})
    finally:
        app.ds_chat, app.api_key = old_chat, old_key
    return out, calls


# 字面比对认不出缺的那一问时（「收费吗」答成「前 5 次免费」），触发口径靠问面标签补这一格
# ——2026-11-05 实测 f1/f4 就卡在 unasked 为空、missing 有「费用」上，模型根本没进。
out, calls = fill_labels({"covers": "no", "facet": "办理时间", "snippet": "周末及节假日 9:00-17:00",
                          "fills": "办理时间", "why": "答的是地点不是时间"}, ["办理时间"])
check("②按问面标签触发也认", out["gate"] == "filled" and out.get("fills") == "办理时间",
      str(out)[:140])

# ---- 方案D甲 专名映射 ----
# ps 已经作为定位器进词表（2026-11-05 用户拍板），规则腿自己认得就不该再问模型；
# 映射这条只留给词表确实不认识的名字。
for q, want in [("ps怎么激活", ""), ("PS 怎么激活", ""), ("HPV疫苗怎么预约", "hpv"),
                ("figma怎么导出", "figma"),
                ("Adobe软件怎么激活", ""), ("校园卡丢了怎么补办", ""), ("WPS365怎么登录", "")]:
    check("D甲取词 %s" % q, app._unmatched_name(q) == want,
          "得 %r 期望 %r" % (app._unmatched_name(q), want))

menu = app.proper_name_menu()
pi = app.proper_index()
bad = [t for t in menu if t not in pi["postings"] or len(pi["postings"][t]) < app.PROPER_MAP_MIN_POSTINGS]
check("D甲菜单只列词表里确有 posting 的名字", not bad and "adobe" in menu,
      "%d 个名字，越界 %s，含 adobe=%s" % (len(menu), bad[:3], "adobe" in menu))


def mapped(reply):
    chat, calls = stub(reply)
    old_chat, old_key = app.ds_chat, app.api_key
    app.ds_chat, app.api_key = chat, (lambda: "test-key")
    try:
        out = app.llm_proper_map("ps怎么激活", "ps")
    finally:
        app.ds_chat, app.api_key = old_chat, old_key
    return out, calls


out, calls = mapped({"name": "Adobe", "why": "Photoshop 是 Adobe 家的"})
check("D甲认品牌（大小写不敏感）", out.get("name") == "adobe", str(out)[:120])
check("D甲提示词里摆了词表", bool(calls) and "adobe" in calls[0],
      "菜单 %d 字" % (len(calls[0]) if calls else 0))
check("D甲提示词写明只输出 JSON", bool(calls) and "只输出 JSON" in calls[0],
      (calls[0][-60:] if calls else "没调用"))

out, _ = mapped({"name": "photoshop 教育版", "why": "自己造的名字"})
check("D甲造出来的名字不算", out.get("name") == "", str(out)[:120])

out, _ = mapped({"name": None, "why": "库里没有这个东西"})
check("D甲判没有就空着", out.get("name") == "", str(out)[:120])

out, _ = mapped(RuntimeError("接口超时"))
check("D甲接口失败留记录", out.get("name") == "" and out.get("error"), str(out)[:120])

# 映射成功后端进候选的那几条：必须自己写了这个名字、不是 archive_only、不重复、有上限
adobe_ids = pi["postings"]["adobe"]
ranked = [(it, 60 - n) for n, it in enumerate(app.ITEMS) if it["id"] in adobe_ids][:20]
extra = app.proper_map_extra(ranked, "adobe", {ranked[0][0]["id"]})
check("D甲端进候选只取带这个名字的条目",
      extra and all(i["id"] in adobe_ids and not i.get("archive_only") for i, _ in extra)
      and len(extra) <= app.PROPER_MAP_ADD
      and extra[0][0]["id"] != ranked[0][0]["id"],
      "端进 %d 条 %s" % (len(extra), [i["id"] for i, _ in extra][:4]))

# ---- 方案D甲 菜单收窄：只摆这次相关条目里写过的名字，并挂出处 ----
scope = ranked[:app.PROPER_MAP_SCOPE]
scope_ids = {i["id"] for i, _ in scope}
scope_names = set().union(*[pi["items"].get(i, set()) for i in scope_ids]) if scope_ids else set()
nmenu = app.proper_menu_for(scope)
ns = {n for n, _g in nmenu}
check("D甲收窄菜单只列这批条目写过的名字",
      ns and ns <= scope_names and "adobe" in ns,
      "%d 个名字，越界 %s" % (len(ns), sorted(ns - scope_names)[:3]))
check("D甲收窄菜单有上限", len(nmenu) <= app.PROPER_MAP_MAX, "%d 个" % len(nmenu))
check("D甲每个名字挂出处", all(n in pi["postings"] and len(pi["postings"][n]) >= app.PROPER_MAP_MIN_POSTINGS
                          for n in ns) and any(g for _n, g in nmenu),
      "带出处的 %d/%d 个" % (sum(1 for _n, g in nmenu if g), len(nmenu)))

nchat, ncalls = [], None

def mapped_scoped(reply, pairs):
    chat, calls = stub(reply)
    old_chat, old_key = app.ds_chat, app.api_key
    app.ds_chat, app.api_key = chat, (lambda: "test-key")
    try:
        out = app.llm_proper_map("ps怎么激活", "ps", pairs)
    finally:
        app.ds_chat, app.api_key = old_chat, old_key
    return out, calls


tight = [("adobe", "正版Adobe使用说明"), ("wps365", "打开WPS365客户端")]
out, calls = mapped_scoped({"name": "wps", "why": "拼写像"}, tight)
check("D甲菜单外的名字不算（ps→wps 那次的锁）",
      out.get("name") == "" and out.get("rejected") == "wps", str(out)[:120])
check("D甲提示词把出处摆在名字后面", bool(calls) and "（正版Adobe使用说明）" in calls[0],
      (calls[0][:80] if calls else "没调用"))
check("D甲收窄后菜单短于全量", bool(calls) and len(calls[0]) < 1200,
      "提示词 %d 字" % (len(calls[0]) if calls else 0))

out, _ = mapped_scoped({"name": "adobe", "why": "同一品牌"}, tight)
check("D甲收窄菜单里认得出的照收", out.get("name") == "adobe", str(out)[:120])

out, _ = mapped_scoped({"name": "adobe", "why": "同一品牌"}, [])
check("D甲空菜单不发请求", out.get("name") == "" and not out.get("error"), str(out)[:120])

# ---- ② 的触发口径：标签那条只认真有两问的问句 ----
# 「贵重物品怎么报案」里的「贵」会被 fee 规则当成「费用」，拿这个假缺口去问模型，
# 它会补出一面不相干的（2026-11-05 实测补进「该找哪个部门」，还撤了缺问声明）。
SIGNALS = []


def spy_fill(q, item, parts, signals, known):
    SIGNALS.append(list(signals))
    return {"gate": "declined", "why": "桩"}


def null_chat(messages, max_tokens=600, json_mode=False, thinking=False):
    return json.dumps({"best": None, "score": 0, "why": "桩"})


OLD = app.llm_facet_fill, app.ds_chat, app.api_key
app.llm_facet_fill, app.ds_chat, app.api_key = spy_fill, null_chat, (lambda: "test-key")
try:
    one = app.answer_question("校园里丢了贵重物品怎么报案？", {}, True)
    n_one = len(SIGNALS)
    two = app.answer_question("校医院的心理咨询怎么预约？收费吗？", {}, True)
finally:
    app.llm_facet_fill, app.ds_chat, app.api_key = OLD
check("②单问句的假「费用」标签不触发模型", SIGNALS[:n_one] != [["费用"]],
      "单问句触发 %d 次 信号 %s ｜它的缺问 %s" % (n_one, SIGNALS[:n_one], (one or {}).get("missing")))
check("②真有两问且字面没缺口时标签顶上", len(SIGNALS) > n_one and bool(SIGNALS[-1]),
      "两句共触发 %d 次，最后一次信号 %s ｜两句缺问 %s / %s"
      % (len(SIGNALS), SIGNALS[-1] if SIGNALS else [], (one or {}).get("missing"),
         (two or {}).get("missing")))

# ---- 规则腿一次模型都不许发 ----
def boom(*a, **k):
    raise AssertionError("规则腿不该调用模型")


old_chat, old_key = app.ds_chat, app.api_key
app.ds_chat, app.api_key = boom, (lambda: "test-key")
try:
    res = app.answer_question(Q, router_llm=False)
    rule_ok = True
except AssertionError as e:
    res, rule_ok = None, False
finally:
    app.ds_chat, app.api_key = old_chat, old_key
check("规则腿不发模型请求", rule_ok, "答面 %s" % ([p["label"] for p in (res or {}).get("answers") or []],))
check("规则腿不记 facet_fill", rule_ok and "facet_fill" not in ((res or {}).get("model_route") or {}),
      str((res or {}).get("model_route") or {})[:100])

# ---- 甲：规则腿一分没给时，llm_route 挑中也不许出答 ----
# 「滚木」这类词库里根本没有，ranked 前 8 名全是 0 分的无关条目（0 分并列，谁排第一
# 是原表顺序的巧合）。旧路把这种池子端到模型面前让它「挑一条」，挑中就答，
# 而复核又因为候选池空被跳过（app.py 里 rc_ids 为空 → skipped），错答就这么发出去了。
NAMED = app.ITEM_BY_ID.get("xyk-buka")
old_route, old_rerank = app.llm_route, app.llm_rerank
old_recheck, old_key = app.llm_recheck, app.api_key
app.llm_route = lambda *a, **k: (NAMED, [])
app.llm_rerank = lambda *a, **k: (None, [])
app.llm_recheck = lambda *a, **k: {"verdict": "yes", "answers": "yes", "best": "xyk-buka", "why": ""}
app.api_key = lambda: "test-key"
try:
    none = app.answer_question("滚木")
    kept = app.answer_question("校园电梯卡")
finally:
    app.llm_route, app.llm_rerank, app.llm_recheck, app.api_key = old_route, old_rerank, old_recheck, old_key

nm, km = (none.get("model_route") or {}), (kept.get("model_route") or {})
check("零分候选里挑中也不出答", not none.get("matched"),
      "matched=%s 条目=%s gate=%s conf=%s" % (none.get("matched"),
      (none.get("item") or {}).get("id"), nm.get("gate"), none.get("confidence")))
check("有分候选里仍接模型的挑", bool(kept.get("matched"))
      and (kept.get("item") or {}).get("id") == "xyk-buka",
      "matched=%s 条目=%s gate=%s" % (kept.get("matched"),
      (kept.get("item") or {}).get("id"), km.get("gate")))

print("failed", failed)
sys.exit(1 if failed else 0)
