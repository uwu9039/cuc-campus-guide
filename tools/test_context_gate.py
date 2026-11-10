"""上下文入口的回归：C 用一次短调用判「这句要不要接着上一条」，B 让拼接只进检索。

盯五件事：
  1. 判「不需要」时，上一条的标题一个字都不许进检索串，也不许出现 context_item
     （用户实测：上一问服务大厅，再问「滑雪」被转接到服务大厅）。
  2. 判「需要」时（「那要带什么材料」），检索串带上上一条，答案才算得上续问。
  3. 判分与复核看到的题面以用户原话开头——候选自己的标题不再当问题喂给模型（自证污染）。
  4. 接口挂了就回退手写词表 _is_followup，整轮不中断。
  5. 不带 context_item 也不带 history 时（206 基线口径），这道判定一次都不发，
     老基线不会因为多一次调用而漂。
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


FAKE_ID = "t-ctx-prev"
FAKE_TITLE = "测试事项甲乙丙丁"
app.ITEM_BY_ID[FAKE_ID] = {
    "id": FAKE_ID, "title": FAKE_TITLE, "aliases": [], "keywords": [],
    "dept": "测试办", "summary": "这是一条只给测试用的假条目。",
}

calls: list[dict] = []
app.api_key = lambda: "test-key"


def stub(payloads: dict[str, str], boom: str | None = None):
    """按 system 里的特征串分派返回值，并把每次调用记下来。"""
    calls.clear()

    def fake(msgs, **kw):
        sys_txt = " ".join(m.get("content", "") for m in msgs if m.get("role") == "system")
        user_txt = " ".join(m.get("content", "") for m in msgs if m.get("role") == "user")
        calls.append({"system": sys_txt, "user": user_txt})
        for marker, out in payloads.items():
            if marker in sys_txt:
                if boom and boom in sys_txt:
                    raise RuntimeError("接口挂了")
                return out
        return '{"scores": {}, "best": null, "why": "", "rewrites": [], "facets": []}'
    app.ds_chat = fake


NEED_YES = {"上一条事项": '{"need": true, "why": "省略了主体"}'}
NEED_NO = {"上一条事项": '{"need": false, "why": "自己说清楚了"}'}

# ---- 1 判不需要：标题一个字都不进检索
stub(NEED_NO)
ranks: list[str] = []
real_rank = app.rank
app.rank = lambda t, *a, **kw: (
    ranks.append(t) if not app.CTX_PROBE[0] else None,
    real_rank(t, *a, **kw))[1]


def answer_ranks() -> list[str]:
    """答题路径的检索串（探针检索在 app.CTX_PROBE 立着时不入账）。"""
    return list(ranks)


try:
    res = app.answer_question("滑雪", router_llm=True, context_item=FAKE_ID,
                              history=[{"role": "user", "content": "综合服务大厅在哪"},
                                       {"role": "assistant", "content": "在信息传播学院一层。"}])
    check("判不需要时没发续问判定", any("上一条事项" in c["system"] for c in calls), "")
    check("判不需要时检索串里没有上一条标题",
          all(FAKE_TITLE not in t for t in answer_ranks()), f"检索串 {ranks[:3]}")
    check("判不需要时没有 context_item", res.get("context_item") in (None, ""),
          f"ctx={res.get('context_item')}")
    check("判不需要时只答一遍（重试块已删）", len(answer_ranks()) <= 2,
          f"答题 rank 调用 {len(answer_ranks())} 次")

    # ---- 2 判需要：续问照样接住上一条
    ranks.clear()
    stub(NEED_YES)
    res2 = app.answer_question("那要带什么材料", router_llm=True, context_item=FAKE_ID,
                               history=[{"role": "user", "content": FAKE_TITLE + "怎么办理"}])
    check("判需要时检索串带上了上一条",
          any(FAKE_TITLE in t for t in ranks), f"检索串 {ranks[:3]}")
    check("判需要时带 context_item", res2.get("context_item") == FAKE_ID,
          f"ctx={res2.get('context_item')}")
    check("响应里的 query 仍是用户原话", res2.get("query") == "那要带什么材料",
          f"query={res2.get('query')}")

    # ---- 2b 模型说接，就不许再让 _mentions_other_item 用碎词命中的无关条目把它否掉
    ranks.clear()
    stub(NEED_YES)
    app.answer_question("几天能办好", router_llm=True, context_item=FAKE_ID)
    check("模型判接之后碎词否决不再插手",
          any(FAKE_TITLE in t for t in ranks), f"检索串 {ranks[:3]}")

    # ---- 3 判分题面以用户原话开头（不把候选标题当问题）
    stub(NEED_YES)
    app.answer_question("那要带什么材料", router_llm=True, context_item=FAKE_ID,
                        history=[{"role": "user", "content": FAKE_TITLE + "怎么办理"}])
    judged = [c["user"] for c in calls
              if "候选" in c["system"] or "系统已经选出" in c["system"]]
    check("判分调用确实发生过", len(judged) > 0, f"共 {len(calls)} 次调用")
    check("判分题面以用户原话开头",
          all(j.strip().startswith("那要带什么材料") for j in judged) if judged else False,
          json.dumps(judged[:2], ensure_ascii=False)[:180])
    check("判分题面里的上一条是标注过的，不是拼进问句",
          all(FAKE_TITLE not in j.split("\n")[0] for j in judged) if judged else False,
          json.dumps(judged[:1], ensure_ascii=False)[:160])

    # ---- 4b 规则模式（界面开关关模型）：这次调用一次都不发，退回词表
    stub(NEED_YES)
    ranks.clear()
    app.answer_question("多久", router_llm=False, context_item=FAKE_ID)
    check("规则模式不发续问判定", not any("上一条事项" in c["system"] for c in calls),
          f"调用 {len(calls)} 次")
    check("规则模式仍按词表接上一条", any(FAKE_TITLE in t for t in ranks), f"检索串 {ranks[:3]}")

    # ---- 5 不带上下文：一次判定都不发
    stub(NEED_YES)
    ranks.clear()
    app.answer_question("图书馆周末开吗", router_llm=True)
    check("不带上下文时不发续问判定",
          not any("上一条事项" in c["system"] for c in calls),
          f"调用 {len(calls)} 次")
    check("不带上下文时检索串就是原句", ranks and ranks[0] == "图书馆周末开吗",
          f"检索串 {ranks[:2]}")

    # ---- 4 接口挂了就回退词表
    stub({"上一条事项": ""}, boom="上一条事项")
    ranks.clear()
    app.answer_question("多久", router_llm=True, context_item=FAKE_ID)
    check("判定失败时词表判「多久」为续问，照样接上一条",
          any(FAKE_TITLE in t for t in answer_ranks()), f"检索串 {ranks[:3]}")
    ranks.clear()
    app.answer_question("校园卡丢了怎么补办", router_llm=True, context_item=FAKE_ID)
    check("判定失败时自带主体的句子不接上一条",
          all(FAKE_TITLE not in t for t in answer_ranks()), f"检索串 {ranks[:3]}")
finally:
    app.rank = real_rank
    app.ITEM_BY_ID.pop(FAKE_ID, None)

print("failed", failed)
sys.exit(1 if failed else 0)
