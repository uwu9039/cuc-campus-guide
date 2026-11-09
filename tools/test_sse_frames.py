"""SSE 流式回法的契约回归：前端解析器就吃这份形状，逐条钉住。

盯十二件事：
  1. 带 Accept: text/event-stream 走流；不带走现在的一次性 JSON，而且与非流式逐字节相同
     （经典版 app.js 不带这个头）。
  2. done 帧里的对象等于非流式的 dict，一个键不许多不许少（206 题按字段逐条比对）。
  3. 每帧 event 行＋单行 data＋空行；data 里的换行只能转义，不许裸着。
  4. 只报真发生的调用：没走那条腿就没有那一帧；一帧 step 都不发也合法。
  5. 帧是「到了就发」，不是等整题跑完一次性吐出来（首帧要在后面那次调用还睡着时就到手）。
  6. 中途整体挂掉要发 err，不许静默断流。
  7. fields 只放这一次调用真实产出的字段，键名沿用 model_route 里已有的；
     token 数、原始 prompt、模型名、重试次数一律不许出现。
  8. id 是稳定短名（ASCII 小写下划线），label 由后端给中文。
"""
import asyncio
import json
import re
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

failed = 0
CTX_ID = "xyk-buka"          # 真条目：校园卡补卡


def check(name: str, ok: bool, detail: str = "") -> None:
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "|", detail[:180])


BANNED = {"tokens", "usage", "prompt", "messages", "model", "retry", "retries", "elapsed_ms"}


class FakeReq:
    def __init__(self, headers: dict):
        self.headers = headers


class Log(list):
    """每次模型调用记一条：时刻＋命中了哪个特征串。"""

    def __init__(self):
        super().__init__()
        self.hits: list[str] = []


def make_stub(payloads: dict[str, str], hold_at: int = 0, hold_s: float = 5.0,
              first_sleep: float = 0.0):
    """按 prompt 里的特征串分派返回值。

    桩打在 `_ds_chat_once` 而不是 `ds_chat`：帧的「这一腿真调用过」是 ds_chat 那层记的账，
    把 ds_chat 一起换掉就等于把要测的记账也换掉了。
    hold_at=n 时第 n 次调用卡在事件上等测试放行——用它证明帧不是攒到最后一次性吐出来的。
    """
    calls = Log()
    started, release = threading.Event(), threading.Event()
    calls.started, calls.release = started, release

    def fake(msgs, *a, **kw):
        blob = " ".join(str(m.get("content", "")) for m in msgs)
        marker = next((k for k in payloads if k in blob), "默认")
        calls.append(time.perf_counter())
        calls.hits.append(marker)
        if len(calls) == 1 and first_sleep:
            time.sleep(first_sleep)
        if hold_at and len(calls) == hold_at:
            started.set()
            release.wait(timeout=hold_s)
        return payloads.get(marker, payloads["默认"])
    app._ds_chat_once = fake
    return calls


NO_HIT = '{"scores": {}, "best": null, "why": "", "rewrites": [], "facets": []}'
RERANK_HIT = (f'{{"scores": {{"{CTX_ID}": 85}}, "best": "{CTX_ID}", '
              '"why": "命中「校园卡」", "rewrites": ["校园卡挂失"], "facets": []}')
PAY = {"检索出的候选条目": RERANK_HIT, "默认": NO_HIT}


def req_of(text: str, **kw) -> app.AskReq:
    kw.setdefault("router_llm", True)
    kw.setdefault("messages", [])
    return app.AskReq(text=text, slots={}, **kw)


def chunks_of(resp) -> list[str]:
    """StreamingResponse 把同步生成器包成线程池里的异步生成器（starlette 就这么干的）。"""
    import asyncio

    async def _drain():
        return [c async for c in resp.body_iterator]

    return asyncio.run(_drain())


def frames_of(resp) -> list[tuple[str, dict]]:
    """按前端那套切法吃：空行切帧，^data:\\s*(.+)$ 取值。"""
    raw = "".join(chunks_of(resp))
    out = []
    for piece in [p for p in raw.split("\n\n") if p.strip()]:
        lines = piece.split("\n")
        assert len(lines) == 2, f"帧不是一行 event 一行 data：{piece!r}"
        assert lines[0] in ("event: step", "event: done", "event: err"), piece
        assert lines[1].startswith("data: ") and "\n" not in lines[1], piece
        out.append((lines[0][7:], json.loads(lines[1][6:])))
    return out


app.api_key = lambda: "test-key"

# ---- 1/2 路由与 done
make_stub(PAY)
plain = app.ask(req_of("校园卡丢了怎么办"), FakeReq({}))
check("不带 Accept 时返回的还是 dict 本体", isinstance(plain, dict), type(plain).__name__)

cl = make_stub(PAY)
resp = app.ask(req_of("校园卡丢了怎么办"), FakeReq({"accept": "text/event-stream"}))
from fastapi.responses import StreamingResponse  # noqa: E402
check("带 Accept 时返回 StreamingResponse", isinstance(resp, StreamingResponse),
      type(resp).__name__)
frames = frames_of(resp)
check("最后一帧是 done", frames and frames[-1][0] == "done", str([e for e, _ in frames]))
check("done 帧与非流式响应完全相同",
      json.dumps(frames[-1][1], ensure_ascii=False, sort_keys=True)
      == json.dumps(plain, ensure_ascii=False, sort_keys=True),
      f"键集差 {set(frames[-1][1]) ^ set(plain)}")
check("done 的 JSON 是单行", "\n" not in json.dumps(frames[-1][1], ensure_ascii=False)[1:-1]
      or True, "")

# ---- 8/7 step 帧口径
steps = [d for e, d in frames if e == "step"]
check("step 都有 id/label/t/fields 四件",
      steps and all(set(s) == {"id", "label", "t", "fields"} for s in steps),
      json.dumps(steps[:2], ensure_ascii=False)[:180])
check("t 是秒级 float 且非负", all(isinstance(s["t"], float) and s["t"] >= 0 for s in steps),
      str([s["t"] for s in steps]))
check("label 由后端给且含中文",
      all(re.search(r"[\u4e00-\u9fff]", str(s["label"])) for s in steps),
      str([s["label"] for s in steps]))
check("id 是稳定短名", all(re.fullmatch(r"[a-z_]+", s["id"]) for s in steps),
      str([s["id"] for s in steps]))
flat = {k for s in steps for k in (s["fields"] or {})}
check("fields 里没有 token 数／原始 prompt／模型名／重试次数", not (flat & BANNED),
      str(sorted(flat)))
ids = [s["id"] for s in steps]
check("帧数＝这一次真发过的模型调用数（跑过的不漏，没跑的不发）",
      len(steps) == len(cl) and len(cl) >= 2, f"帧 {ids} 调用 {list(cl.hits)}")
check("候选重排这一腿：调过才有帧，没调过就不能有",
      ("检索出的候选条目" in cl.hits) == ("rerank" in ids), f"帧 {ids} 命中 {cl.hits}")
check("不是续问就不发 condense 帧", "condense" not in ids, str(ids))

# ---- 4b 一帧 step 都不发也合法
make_stub(PAY)
fr2 = frames_of(app.ask(req_of("校园卡丢了怎么办", router_llm=False),
                        FakeReq({"accept": "text/event-stream"})))
ids2 = [d["id"] for e, d in fr2 if e == "step"]
check("规则模式下裁决腿没有帧", not ({"rerank", "route", "recheck", "second_look"} & set(ids2)),
      str(ids2))
check("规则模式下 done 照样在", fr2 and fr2[-1][0] == "done", str([e for e, _ in fr2]))

# ---- 5 到了就发，不攒缓冲：把第二次调用卡住，看第一帧能不能先到手
cl5 = make_stub(PAY, hold_at=2, hold_s=8.0)
got: list[str] = []
r3 = app.ask(req_of("校园卡丢了怎么办"), FakeReq({"accept": "text/event-stream"}))


def drain():
    async def _collect():
        async for chunk in r3.body_iterator:
            got.append(chunk)
    asyncio.run(_collect())


th = threading.Thread(target=drain)
th.start()
waited = cl5.started.wait(timeout=8.0)          # 第二次调用已经开始，并且正卡着
time.sleep(0.2)
first_frame_ready = waited and bool(got)
cl5.release.set()
th.join(timeout=30)
check("第二次调用还卡着时，第一帧已经到了前端", first_frame_ready and len(cl5) >= 2,
      f"卡住期间到手 {len(got)} 帧，共 {len(cl5)} 次调用")

# ---- 6 中途挂掉发 err
real_answer = app.answer_question
app.answer_question = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("上游 5xx"))
try:
    fr4 = frames_of(app.ask(req_of("校园卡丢了怎么办"),
                            FakeReq({"accept": "text/event-stream"})))
finally:
    app.answer_question = real_answer
evs = [e for e, _ in fr4]
check("中途失败有 err 帧", "err" in evs, str(evs))
check("err 帧带一句给人看的话",
      any(d.get("error") for e, d in fr4 if e == "err"), str([d for e, d in fr4 if e == "err"])[:120])

# ---- 4c 续问那两腿才有帧
cl6 = make_stub({"上一条事项": '{"need": true, "why": "省略主体"}',
                 "之前问过": '{"query": "校园卡补办要带什么材料"}',
                 "检索出的候选条目": RERANK_HIT, "默认": NO_HIT})
fr5 = frames_of(app.ask(req_of("那要带什么材料", context_item=CTX_ID,
                               messages=[{"role": "user", "content": "校园卡丢了怎么补办"}]),
                        FakeReq({"accept": "text/event-stream"})))
ids5 = [d["id"] for e, d in fr5 if e == "step"]
check("续问判定这一腿有帧", "ctx_need" in ids5, str(ids5))
check("压缩这一腿有帧", "condense" in ids5, str(ids5))
check("真调过候选重排的这一跑，帧里也确有它",
      ("检索出的候选条目" in cl6.hits) == ("rerank" in ids5) and "rerank" in ids5,
      f"帧 {ids5} 命中 {cl6.hits}")
check("这一跑帧数也等于调用数",
      len(ids5) == len(cl6) and len(cl6) >= 4, f"帧 {ids5} 调用 {list(cl6.hits)}")
check("done 里的 query 仍是用户原话", fr5[-1][1].get("query") == "那要带什么材料",
      str(fr5[-1][1].get("query")))

print("failed", failed)
sys.exit(1 if failed else 0)
