"""两道输出闸的回归：模型判死就不再替它作答、置信不到地板就转拒答。

盯五件事：
  0. 定案默认值本身就是开着这两道闸（fusion/rescue/B/闸/0.7），断言一次，防手滑改回。
  1. 显式把开关关掉时，行为与闸之前逐字相同（老路径还得能复现）。
  2. DECLINE_REFUSES 打开后，模型说「候选都没答上」却仍要按规则腿第一名作答的那些题，
     改成拒答；拒答卡照样给相近事项和下一步。
  3. MIN_ANSWER_CONF 只压中段置信（55～69 这一带），不动强命中。
  4. 闸掉之后组装层 rescue 照样能救：拒答分支里拼出来的逐字原文不受这两道闸影响，
     否则这两道闸会把 #56 的收益一起砍掉。
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
    print(("PASS" if ok else "FAIL"), name, "|", detail[:160])


TOP = app.ITEM_BY_ID["pt-560a042fd7"]      # 转诊条款那条原文摘录，规则分常年 80 上下
STRONG = app.ITEM_BY_ID["jwc-gpa"]


def force_rank(score: int, item: dict):
    def fake(text: str, *a, **kw):
        return [(item, score), (STRONG, 10)]
    app.rank = fake


def stub_decline():
    """模型看完候选说「都没答上」：best=None → gate=llm_declined。"""
    def fake_rerank(text, pool, history, status=None, **kw):
        if status is not None:
            status["gate"] = "llm_declined"
            status["asked"] = True
        return {"item": None, "score": 0, "scores": {it["id"]: 0 for it, _ in pool}, "facets": []}, []
    app.llm_rerank = fake_rerank
    app.llm_recheck = lambda *a, **kw: {"verdict": "skip", "answers": "yes", "best": "", "why": "", "gate": "off"}
    app.llm_free_answer = lambda *a, **kw: None
    app.api_key = lambda: "test-key"


def ask(text: str) -> dict:
    return app._answer_core(text, None, True, None)


app.api_key = lambda: "test-key"
stub_decline()

# ---- 0 定案默认值（改代码时不许悄悄退回关着）
check("定案默认值：fusion/rescue/B/开闸/地板0.7",
      (app.RETRIEVAL_MODE, app.ASSEMBLE_MODE, app.REWRITE_PRE, app.DECLINE_REFUSES, app.MIN_ANSWER_CONF)
      == ("fusion", "rescue", "B", True, 0.7),
      f"实际 {app.RETRIEVAL_MODE}/{app.ASSEMBLE_MODE}/{app.REWRITE_PRE}/"
      f"{app.DECLINE_REFUSES}/{app.MIN_ANSWER_CONF}")

# ---- 1 显式关着
app.DECLINE_REFUSES = False
app.MIN_ANSWER_CONF = 0.0
force_rank(82, TOP)
off = ask("学校医保报销要哪些材料")
check("关着时照旧按规则腿答", bool(off.get("matched")) and (off.get("item") or {}).get("id") == TOP["id"],
      f"matched={off.get('matched')} 条目={(off.get('item') or {}).get('id')} conf={off.get('confidence')}")

# ---- 2 判死闸
app.DECLINE_REFUSES = True
on = ask("学校医保报销要哪些材料")
check("模型判死后不再替它作答", not on.get("matched"),
      f"matched={on.get('matched')} gate={(on.get('model_route') or {}).get('gate')}")
check("闸掉的原因是闸，不是库里没有", (on.get("model_route") or {}).get("refused_by") == "decline_gate",
      json.dumps((on.get("model_route") or {}).get("refused_by"), ensure_ascii=False))
check("拒答卡仍给下一步（相近事项由真实候选决定，桩里不强求）",
      bool(on.get("next_actions")) and "alternatives" in on,
      f"下一步 {len(on.get('next_actions') or [])} 条 相近 {len(on.get('alternatives') or [])} 条")
check("拒答时置信归零", on.get("confidence") == 0.0, str(on.get("confidence")))

# ---- 3 置信地板
app.DECLINE_REFUSES = False


def stub_pick(score: int):
    def fake_rerank(text, pool, history, status=None, **kw):
        best = pool[0][0] if pool else None
        if status is not None:
            status["asked"] = True
        return {"item": best, "score": score, "scores": {it["id"]: score for it, _ in pool},
                "facets": []}, []
    app.llm_rerank = fake_rerank


stub_pick(64)
force_rank(62, TOP)
app.MIN_ANSWER_CONF = 0.0
mid_off = ask("医保报销材料")
app.MIN_ANSWER_CONF = 0.7
mid_on = ask("医保报销材料")
check("地板只压中段置信：关着时 62 分照答", bool(mid_off.get("matched")) and (mid_off.get("item") or {}).get("id") == TOP["id"],
      f"conf={mid_off.get('confidence')}")
check("地板打开时 62 分转拒答", not mid_on.get("matched")
      and (mid_on.get("model_route") or {}).get("refused_by") == "conf_floor",
      f"matched={mid_on.get('matched')} refused_by={(mid_on.get('model_route') or {}).get('refused_by')}")
check("强命中不受地板影响", force_rank(91, STRONG) or ask("绩点怎么算").get("matched") is True,
      "91 分仍应作答")

# ---- 4 闸掉以后组装层仍能救
app.DECLINE_REFUSES = True
app.MIN_ANSWER_CONF = 0.7
app.ASSEMBLE_MODE = "rescue"
stub_decline()          # 这一段要的是「模型判死」这个前提，上面 stub_pick 把它改掉了
force_rank(82, TOP)


def fake_ds(msgs, **kw):
    prompt = " ".join(m["content"] for m in msgs)
    if "拆成一张清单" in prompt:
        return json.dumps({"faces": [{"face": "开放时间", "phrases": ["图书馆开放时间"]}]}, ensure_ascii=False)
    if "只有否决权" in prompt:
        return json.dumps({"verdict": "accept", "id": "lib-kaifang-shijian",
                           "quote": "馆内阅览区 周一～周日 8:00～22:30；1 层诵读区 7:00～22:30",
                           "why": "写到了"}, ensure_ascii=False)
    return "{}"


app.ds_chat = fake_ds
saved = app.rerank_candidates
app.rerank_candidates = lambda text, ranked, limit=app.RERANK_POOL_LIMIT, status=None, pre_rewrite=True: [
    (TOP, 82), (app.ITEM_BY_ID["lib-kaifang-shijian"], 0)]
r = ask("图书馆周末开吗")
app.rerank_candidates = saved
app.ASSEMBLE_MODE = "off"
check("闸掉的题仍能由组装层拼回答案", bool(r.get("matched"))
      and any(p.get("focus") == "assembly" for p in r.get("answers") or []),
      f"matched={r.get('matched')} conf={r.get('confidence')} 面={[p.get('label') for p in r.get('answers') or []]}")

app.DECLINE_REFUSES = False
app.MIN_ANSWER_CONF = 0.0
app.rank = app.__dict__["rank"] if "rank" in app.__dict__ else app.rank
print(f"\nfailed {failed}")
sys.exit(1 if failed else 0)
