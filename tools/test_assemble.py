"""跨条目组装层（#56）的回归。

盯七件事：
  1. ASSEMBLE 关着时，一次组装调用都不许发生（206 基线不许漂）。
  2. 分面计划：面数有上限、已经答到的面丢掉、模型说「不用拆」就真的不拆。
  3. 官方写法护栏：改写串必须还带着原句的主体词，跑偏的说法直接丢。
  4. 决策层只有否决权：池外的 id 不认、引文逐字对不上不认、判 no_evidence 不拼。
  5. 拼进来的那一面，正文就是条目原文本身，模型一个字都不许改写。
  6. 同一条目最多贡献一面；接口挂了记 error，整轮不中断。
  7. 补出来的面带元信息头（哪条条目、哪个部门、各腿名次）。
"""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prompt_parts as pp  # noqa: E402
import app  # noqa: E402

failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:150])


def set_mode(m: str) -> None:
    app.ASSEMBLE_MODE = m


LIB = app.ITEM_BY_ID["lib-kaifang-shijian"]
GONGFEI = app.ITEM_BY_ID["xyy-gongfei"]
QUOTE = "馆内阅览区 周一～周日 8:00～22:30；1 层诵读区 7:00～22:30"

calls: list[str] = []


def route_stub(plans, decides, boom=False):
    """按 prompt 内容分派：分面计划 vs 单面裁决。"""
    def fake(msgs, **kw):
        prompt = " ".join(m["content"] for m in msgs)
        calls.append(prompt)
        if boom:
            raise RuntimeError("接口挂了")
        if "拆成一张清单" in prompt:
            return json.dumps(plans.pop(0) if plans else {"faces": []}, ensure_ascii=False)
        if "只有否决权" in prompt:
            return json.dumps(decides.pop(0) if decides else {"verdict": "no_evidence"}, ensure_ascii=False)
        return "{}"
    app.ds_chat = fake
    app.api_key = lambda: "test-key"


# ---- 0 片段注册表里有这两块，且固定文本在前
check("prompt_parts 有 assemble.plan", "assemble.plan" in pp.FRAGMENTS or
      any(k.startswith("assemble.plan") for k in pp.FRAGMENTS), str([k for k in pp.FRAGMENTS if k.startswith("assemble")]))
check("prompt_parts 有 assemble.decide", any(k.startswith("assemble.decide") for k in pp.FRAGMENTS), "")
try:
    lay = pp.layout("assemble_plan", {"q": "x", "answered": "y", "menu": "z"})
    check("assemble_plan 装配顺序：动态片不占第一位", not lay[0].startswith("@"), json.dumps(lay, ensure_ascii=False))
except Exception as e:  # noqa: BLE001
    check("assemble_plan 装配顺序：动态片不占第一位", False, repr(e))

# ---- 1 关着时一次都不调
set_mode("off")
calls.clear()
route_stub([{"faces": [{"face": "周末开吗", "phrases": ["图书馆开放时间"]}]}], [])
parts = app._parts_for_item(LIB, ["hours"], {}) if hasattr(app, "_parts_for_item") else []
out = app.assemble_faces("图书馆周末开吗", parts, set(), {"gate": None}) if hasattr(app, "assemble_faces") else None
check("ASSEMBLE=off 时不调模型", len(calls) == 0, f"实际调用 {len(calls)} 次")
check("ASSEMBLE=off 时返回空", not out, json.dumps(out, ensure_ascii=False)[:120])

set_mode("both")
calls.clear()

# ---- 2 分面计划
plan_ok = {"faces": [
    {"face": "开放时段", "phrases": ["图书馆开放时间", "图书馆开馆时间"]},
    {"face": "楼层服务点", "phrases": ["图书馆楼层服务"]},
    {"face": "研讨间", "phrases": ["图书馆研讨间预约"]},
    {"face": "占座", "phrases": ["图书馆占座规定"]},
]}
route_stub([plan_ok], [])
res = app.llm_faces_plan("图书馆周末开吗", [], {})
check("分面计划有返回", isinstance(res, dict) and res.get("gate") == "ok", json.dumps(res, ensure_ascii=False)[:160])
check("面数截到上限 3", 0 < len(res.get("faces") or []) <= app.ASSEMBLE_MAX_FACES,
      f"{len(res.get('faces') or [])} 面 / 上限 {app.ASSEMBLE_MAX_FACES}")

route_stub([{"faces": []}], [])
res = app.llm_faces_plan("绩点怎么算", [{"label": "计算方法", "found": True}], {})
check("模型说不用拆就不拆", res.get("gate") in ("empty", "no_need"), json.dumps(res, ensure_ascii=False)[:120])

route_stub([{"faces": [{"face": "周末开吗", "phrases": ["周末"]}]}], [])
res = app.llm_faces_plan("图书馆周末开吗", [], {})
check("改写串丢光主体词的面被拒", res.get("gate") in ("empty", "no_need", "dropped"),
      json.dumps(res, ensure_ascii=False)[:160])

# ---- 3 官方写法护栏：面计划里的 phrase 必须含原句主体词
set_mode("both")
route_stub([{"faces": [{"face": "开放时段", "phrases": ["图书馆开放时间", "体育馆开放时间"]}]}], [])
res = app.llm_faces_plan("图书馆周末开吗", [], {})
phr = [p for f in (res.get("faces") or []) for p in f.get("phrases") or []]
check("跑偏的改写串被丢掉", "体育馆开放时间" not in phr and "图书馆开放时间" in phr, json.dumps(phr, ensure_ascii=False))

# ---- 4 检索：官方写法能把目标条目捞进池
pool = app.face_pool(["图书馆开放时间"], 12, exclude_ids=set())
ids = [it["id"] for it, _sc, _legs in pool]
check("官方写法捞到图书馆开放时间条目", "lib-kaifang-shijian" in ids, json.dumps(ids[:8], ensure_ascii=False))
check("池里每条带各腿名次", bool(pool) and isinstance(pool[0][2], dict), json.dumps(pool[0][2], ensure_ascii=False)[:160] if pool else "池空")

# ---- 5/6 决策层否决权
one_pool = [(LIB, 60, {"rule": 1}), (GONGFEI, 50, {"rule": 2})]
route_stub([], [{"verdict": "accept", "id": "pt-not-in-pool", "quote": QUOTE, "why": "编的"}])
d = app.llm_face_decide("图书馆周末开吗", {"face": "开放时段", "phrases": ["图书馆开放时间"]}, one_pool)
check("池外 id 不认", d.get("gate") != "accept", json.dumps(d, ensure_ascii=False)[:140])

route_stub([], [{"verdict": "accept", "id": "lib-kaifang-shijian", "quote": "周末全天闭馆不开放", "why": "编的"}])
d = app.llm_face_decide("图书馆周末开吗", {"face": "开放时段", "phrases": ["图书馆开放时间"]}, one_pool)
check("引文逐字对不上不认", d.get("gate") != "accept", json.dumps(d, ensure_ascii=False)[:140])

route_stub([], [{"verdict": "accept", "id": "lib-kaifang-shijian", "quote": QUOTE, "why": "写到了"}])
d = app.llm_face_decide("图书馆周末开吗", {"face": "开放时段", "phrases": ["图书馆开放时间"]}, one_pool)
check("逐字引文对上就接", d.get("gate") == "accept", json.dumps(d, ensure_ascii=False)[:200])
if d.get("gate") == "accept":
    part = d.get("part") or {}
    check("补进来的正文就是原文本身", (part.get("text") or "").strip() == QUOTE,
          json.dumps(part.get("text"), ensure_ascii=False)[:120])
    check("补进来的面标出来自哪条条目", part.get("from") == "lib-kaifang-shijian", json.dumps(part, ensure_ascii=False)[:200])
    check("补进来的面带元信息头", bool(part.get("meta")) and isinstance(part.get("meta"), str), str(part.get("meta"))[:120])
else:
    check("补进来的面标出来自哪条条目", False, "没接")
    check("补进来的面带元信息头", False, "没接")
    part = {}

route_stub([], [{"verdict": "no_evidence", "why": "都没写"}])
d = app.llm_face_decide("图书馆周末开吗", {"face": "开放时段", "phrases": ["图书馆开放时间"]}, one_pool)
check("判没证据就不拼", d.get("gate") == "no_evidence" and not d.get("part"), json.dumps(d, ensure_ascii=False)[:120])

# ---- 7 同一条目最多贡献一面
route_stub([{"faces": [
    {"face": "开放时段", "phrases": ["图书馆开放时间"]},
    {"face": "诵读区", "phrases": ["图书馆诵读区时间"]},
]}], [
    {"verdict": "accept", "id": "lib-kaifang-shijian", "quote": QUOTE, "why": "写到了"},
    {"verdict": "accept", "id": "lib-kaifang-shijian", "quote": QUOTE, "why": "又是它"},
])
st7 = {}
got = app.assemble_faces("图书馆周末开吗", [], set(), st7)
ids = [p.get("from") for p in got]
check("同一条目只贡献一面", len(got) == 1 and len(ids) == len(set(ids)), json.dumps({"got": ids, "trace": st7.get("assembly")}, ensure_ascii=False))

# ---- 8 接口挂了不中断
route_stub({}, {}, boom=True)
try:
    got = app.assemble_faces("图书馆周末开吗", [], set(), {})
    check("接口异常时组装层不抛", got == [], json.dumps(got, ensure_ascii=False)[:80])
except Exception as e:  # noqa: BLE001
    check("接口异常时组装层不抛", False, repr(e))

# ---- 9 已经答到的面不再补
set_mode("both")
answered = [{"focus": "hours", "label": "开放时间", "text": QUOTE, "found": True, "quotes": []}]
route_stub([{"faces": [{"face": "开放时间", "phrases": ["图书馆开放时间"]}]}], [])
st9 = {}
got = app.assemble_faces("图书馆开放时间", answered, set(), st9)
check("已答到的面不重复补", not got and (st9.get("assembly") or {}).get("plan") == "empty", json.dumps(got, ensure_ascii=False)[:120])

# ---- 10 端到端：拒答分支经组装后能答上
set_mode("both")
route_stub([{"faces": [{"face": "周末开放", "phrases": ["图书馆开放时间"]}]}],
           [{"verdict": "accept", "id": "lib-kaifang-shijian", "quote": QUOTE, "why": "写到了"}])
resp = app._answer_core("图书馆周末开吗", None, True, None)
body = json.dumps(resp, ensure_ascii=False)
check("拒答题经组装层能出内容", bool(resp.get("matched")) and "周一～周日" in body,
      f"matched={resp.get('matched')} gate={(resp.get('model_route') or {}).get('assembly')}")
mr = resp.get("model_route") or {}
check("组装过程在 model_route 里留痕", bool(mr.get("assembly")), json.dumps(mr.get("assembly"), ensure_ascii=False)[:200])

set_mode("off")
resp2 = app._answer_core("图书馆周末开吗", None, True, None)
mr2 = resp2.get("model_route") or {}
check("关掉后组装层一步都不跑", "assembly" not in mr2
      and not any(p.get("focus") == "assembly" for p in resp2.get("answers") or []),
      json.dumps({"gate": mr2.get("gate"), "assembly": mr2.get("assembly")}, ensure_ascii=False))

print(f"\nfailed {failed}")
sys.exit(1 if failed else 0)
