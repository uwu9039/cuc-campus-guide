"""高分跳过复核的回归：只在显式开关打开且最终得分够高时才省掉那一次全文复核。

盯四件事：
  1. RECHECK_SKIP_ABOVE=0（默认）时行为与现在逐字相同——每题照样复核一次。
  2. 阈值比的是最终得分（规则分与模型分取大）：到线的题不再调 llm_recheck，没到线的照样调。
     用两道真题分辨，不桩 rank——97 分那道跳，88 分那道不跳。
  3. 跳过时状态里要留痕（recheck.gate=skipped），不能静悄悄当没发生过。
  4. 阈值只允许远高于 54：50~54 那档靠复核签字才开门，skipped 不进签字白名单，
     所以跳过高分不会把 near-miss 的门开松；低于 60 的阈值不进默认值这件事由代码拦。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

failed = 0


def check(name, ok, detail=""):
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:140])


# 两道真题：规则腿分别 97 / 88，跨过 90 这条分辨线
Q_HI, Q_LO = "宿舍怎么购电", "学校医保怎么报销"
TOP_HI, SC_HI = app.rank(Q_HI)[0]
TOP_LO, SC_LO = app.rank(Q_LO)[0]
LINE = 90
check("题集本身够用：一道过线一道不过线",
      SC_HI >= LINE > SC_LO >= app.MATCH_THRESHOLD, f"规则分 {SC_HI} / {SC_LO}")

app.RETRIEVAL_MODE = "fusion"
app.ASSEMBLE_MODE = "rescue"
app.REWRITE_PRE = "B"
app.DECLINE_REFUSES = True
app.MIN_ANSWER_CONF = 0.7
app.api_key = lambda: "x"

calls = []
REAL_RECHECK = app.llm_recheck


def spy_recheck(text, chosen, rc_pool, *a, **kw):
    calls.append(chosen["id"])
    return {"verdict": "yes", "best": chosen["id"], "answers": "yes", "why": "桩"}


app.llm_recheck = spy_recheck


def ask(q: str, top: dict) -> dict:
    payload = json.dumps({"scores": {top["id"]: 95}, "best": top["id"], "why": "写到了",
                          "rewrites": [], "facets": []}, ensure_ascii=False)
    app.ds_chat = lambda msgs, **kw: payload
    return app.answer_question(q, router_llm=True)


# ---- 0 开关本身得存在
check("RECHECK_SKIP_ABOVE 开关已定义", hasattr(app, "RECHECK_SKIP_ABOVE"), "模块里没有这个开关")

# ---- 1 默认一律复核
app.RECHECK_SKIP_ABOVE = 0
calls.clear()
ask(Q_HI, TOP_HI)
check("默认值为 0 时照样复核", len(calls) == 1, f"实际调用 {len(calls)} 次")

# ---- 2 到线跳过 / 不到线照旧
app.RECHECK_SKIP_ABOVE = LINE
calls.clear()
ask(Q_HI, TOP_HI)
check("最终得分 97 跳过复核", len(calls) == 0, f"实际调用 {len(calls)} 次")
calls.clear()
ask(Q_LO, TOP_LO)
check("最终得分 88 照旧复核", len(calls) == 1, f"实际调用 {len(calls)} 次")

# ---- 3 跳过要留痕，而且照样答得上
d = ask(Q_HI, TOP_HI)
rc = (d.get("model_route") or {}).get("recheck")
check("跳过时状态留痕", isinstance(rc, dict) and rc.get("gate") == "skipped",
      json.dumps(rc, ensure_ascii=False)[:120])
check("跳过的题仍然答上", bool(d.get("matched")) and (d.get("item") or {}).get("id") == TOP_HI["id"],
      str((d.get("item") or {}).get("id")))

# ---- 4 skipped 不在签字白名单里：跳过高分不会把 50~54 那档的门开松
src = Path(app.__file__).read_text(encoding="utf-8")
gate_line = next((l for l in src.splitlines() if "rc_gate_seen in (" in l), "")
check("签字白名单里没有 skipped", bool(gate_line) and "skipped" not in gate_line, gate_line.strip()[:120])

app.llm_recheck = REAL_RECHECK
print("failed", failed)
sys.exit(1 if failed else 0)
