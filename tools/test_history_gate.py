"""续问门的回归：独立新问题不许带历史，真续问才压缩成一句可独立检索的问句。

盯四件事：
  1. 「饿了怎么办」这种自带主体的问句不能因为句里有「怎么」就当续问——
     带上一轮购电历史时它必须答食堂，答成购电就是这次用户投诉的原始现象。
  2. 「那要带什么材料」「多久」这种光秃秃的续问照样要接上一条。
  3. 压缩出来的问句只能看上一轮的「问」，不能看上一轮的「答」；
     照抄上一问、超长、空串、接口失败，一律回退原句，不中断整轮。
  4. 判独立时，历史一个字都不许进模型调用。
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
    print(("PASS" if ok else "FAIL"), name, "|", detail[:140])


# ---- 1/2 门本身
gate = [
    ("饿了怎么办", False), ("那要带什么材料", True), ("多久", True),
    ("然后呢", True), ("图书馆周末开吗", False), ("校园卡丢了怎么补办", False),
    ("怎么办", True), ("多少钱", True),
]
for text, want in gate:
    check(f"门判「{text}」={'续问' if want else '独立'}", app._is_followup(text) is want,
          f"实际 {app._is_followup(text)}")

# ---- 3 压缩
seen = []
app.api_key = lambda: "test-key"


def stub(payload, boom=False):
    def fake(msgs, **kw):
        seen.append(msgs)
        if boom:
            raise RuntimeError("接口挂了")
        return payload
    app.ds_chat = fake


HIST = [
    {"role": "user", "content": "宿舍怎么报修"},
    {"role": "assistant", "content": "登录后勤保障处公众号微服务，选择报修单，填写宿舍楼号和故障描述后提交。"},
]

stub('{"query": "宿舍报修要带什么材料"}')
check("续问压缩成独立问句", app.llm_condense("那要带什么材料", HIST) == "宿舍报修要带什么材料", "")
check("压缩只看上一轮的问", "登录后勤保障处公众号微服务" not in seen[-1][0]["content"],
      "上一轮回答的正文进了 condense 提示词")
check("上一轮的问进了提示词", "宿舍怎么报修" in seen[-1][0]["content"], "")

stub('{"query": "宿舍怎么报修"}')
check("照抄上一问就作废", app.llm_condense("那要带什么材料", HIST) is None, "")
stub('{"query": ""}')
check("空串回退", app.llm_condense("那要带什么材料", HIST) is None, "")
stub('{"query": "这" * 31}')
check("超长回退", app.llm_condense("那要带什么材料", HIST) is None, "")
stub('{"query": "宿舍报修电话是多少"}')
check("原样返回也算没补成", app.llm_condense("宿舍报修电话是多少", HIST) is None, "")

n = len(seen)
check("没有历史就不发调用", app.llm_condense("饿了怎么办", None) is None and len(seen) == n,
      f"调用 {len(seen)}")
st: dict = {}
stub('{"query": "x"}', boom=True)
check("接口挂了只记不响", app.llm_condense("那要带什么材料", HIST, st) is None
      and bool(st.get("condense_error")), str(st)[:80])

# ---- 4 独立新问题不带历史
calls = []


def spy(msgs, **kw):
    calls.append(msgs)
    return '{"scores": {}, "best": null, "why": "", "rewrites": [], "facets": []}'


app.ds_chat = spy
base = app.answer_question("饿了怎么办", router_llm=True)
calls.clear()
with_hist = app.answer_question("饿了怎么办", router_llm=True, history=HIST)
check("独立问句带历史时答案不变", with_hist.get("matched") == base.get("matched")
      and (with_hist.get("item") or {}).get("id") == (base.get("item") or {}).get("id"),
      f"{base.get('item', {}).get('id')} vs {with_hist.get('item', {}).get('id')}")
check("独立问句时历史没进任何调用",
      all("宿舍怎么报修" not in json.dumps(m, ensure_ascii=False) for m in calls),
      f"共 {len(calls)} 次调用")
check("独立问句没被套上上一条标题", "宿舍" not in (with_hist.get("query") or "")
      and with_hist.get("context_item") in (None, ""),
      f"query={with_hist.get('query')} ctx={with_hist.get('context_item')}")

print("failed", failed)
sys.exit(1 if failed else 0)
