"""上下文回归：A1.0–A6（v1.0.1 上下文丢失修复的验收脚本）。

跑法：
    ./.venv/Scripts/python.exe tools/_probe_ctx_regress.py

不启服务，直接 import app。**A1.0–A3/A6 走真入口 `/api/ask`**（喂一个假 Request 走 SSE 分支），
不再由探针手工构造 item——否则验的是「给定 item 后能不能锚住」，而不是产品链路
「第一轮 context_item 为空时 item 从哪来」。

- 有 DEEPSEEK_API_KEY：A1.0–A3、A6 跑真链路；没有就 SKIP（不判失败）。
- A4/A5 是「换题必须断开」的反例，走普通链路（`answer_question`），不调模型。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from starlette.requests import Request  # noqa: E402

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
rows: list[tuple[str, str, str]] = []


def rec(case: str, ok: str, detail: str = "") -> None:
    rows.append((case, ok, detail))
    print(f"[{ok}] {case}　{detail}"[:170], flush=True)


def call_ask(text: str, context_item: str | None = None,
             history: list[dict] | None = None) -> dict:
    """走真入口：`/api/ask` 的 SSE 分支，取 done 帧。

    `context_item` 由调用方按**上一轮响应的 item.id** 传进来——这就是 `field.js` L861 做的事。
    第一轮故意不传，验的是「首轮锚定」这段产品代码，而不是探针替它补值。
    """
    scope = {"type": "http", "method": "POST", "path": "/api/ask",
             "headers": [(b"accept", b"text/event-stream")]}
    req = app.AskReq(text=text, synth=True, context_item=context_item,
                     messages=history or [])
    resp = app.ask(req, Request(scope))
    # StreamingResponse 会把同步生成器包成 async generator
    import asyncio

    async def _collect(ait):
        return [f async for f in ait]

    frames = asyncio.run(_collect(resp.body_iterator))
    for f in reversed(frames):
        s = f.decode("utf-8") if isinstance(f, bytes) else str(f)
        if "event: done" in s:
            return json.loads(s.split("data: ", 1)[1])
        if "event: err" in s:
            raise RuntimeError(s.split("data: ", 1)[1][:200])
    raise RuntimeError("SSE 没有 done 帧")


def body_of(resp: dict) -> str:
    s = resp.get("synth") or {}
    parts = [str(s.get("conclusion") or "")]
    parts += [str(x.get("text") or "") for x in (s.get("layers") or [])]
    parts.append(str(s.get("boundary") or ""))
    return " ".join(parts)


def has_key() -> bool:
    try:
        return bool(app.api_key())
    except Exception:  # noqa: BLE001
        return False


def a1_0() -> dict | None:
    """A1.0：**首轮**不许给 context_item，验的是 /api/ask 自己能不能用 rank 命中锚定。"""
    if not has_key():
        rec("A1.0", SKIP, "无 Key")
        return None
    try:
        d1 = call_ask("家庭经济困难认定怎么申请")
    except Exception as e:  # noqa: BLE001
        rec("A1.0", FAIL, f"调用失败 {type(e).__name__}: {e}")
        return None
    it = (d1.get("item") or {}).get("id")
    src = ((d1.get("model_route") or {}).get("ctx_source"))
    ok = it == "zxj-guojia-runding" and src == "rank"
    rec("A1.0", PASS if ok else FAIL, f"首轮 item={it} ctx_source={src!r}（期望 rank）")
    return d1


def a1_a3_a6(d1: dict | None) -> None:
    """正向：q1 → 申请要求 → 要交什么材料 / 要多久；全部走真入口，锚点来自上一轮响应。"""
    if not has_key() or not d1:
        for c in ("A1", "A2", "A3", "A6"):
            rec(c, SKIP, "无 Key 或无首轮结果")
        return
    anchor = (d1.get("item") or {}).get("id")
    hist = [{"role": "user", "content": "家庭经济困难认定怎么申请"}]

    try:
        d2 = call_ask("申请要求", context_item=anchor, history=hist)
    except Exception as e:  # noqa: BLE001
        rec("A1", FAIL, f"追问失败 {type(e).__name__}: {e}")
        return
    b2 = body_of(d2)
    ok_ctx = (d2.get("item") or {}).get("id") == "zxj-guojia-runding"
    ok_material = "家庭经济困难学生认定申请表" in b2
    bad = [x for x in ("转专业申请要求", "社团场地申请要求") if x in b2]
    rec("A1", PASS if (ok_ctx and ok_material and not bad) else FAIL,
        f"ctx={ok_ctx} 材料={ok_material} 串题={bad or '无'}")

    try:
        d3 = call_ask("要交什么材料", context_item=anchor,
                      history=hist + [{"role": "user", "content": "申请要求"}])
    except Exception as e:  # noqa: BLE001
        rec("A2", FAIL, f"调用失败 {type(e).__name__}: {e}")
        return
    b3 = body_of(d3)
    ok3 = ("家庭经济困难学生认定申请表" in b3) and ("全国学生资助管理中心" in b3)
    rec("A2", PASS if ok3 else FAIL, f"材料={('家庭经济困难学生认定申请表' in b3)} "
                                     f"资助中心={('全国学生资助管理中心' in b3)}")

    try:
        d4 = call_ask("要多久", context_item=anchor,
                      history=hist + [{"role": "user", "content": "申请要求"}])
    except Exception as e:  # noqa: BLE001
        rec("A3", FAIL, f"调用失败 {type(e).__name__}: {e}")
        return
    b4 = body_of(d4)
    cites = "[" in b4
    honest = any(w in b4 for w in ("未登记", "没有写", "没有登"))
    others = [x for x in ("创新创业学分", "社团场地") if x in b4]
    rec("A3", PASS if (not others) and (honest or cites) else FAIL,
        f"引用={cites} 承认未登记={honest} 串题={others or '无'}")

    conf = d1.get("confidence")
    note = d1.get("confidence_note") or ""
    rec("A6", PASS if (conf != 0.78 and note) else FAIL, f"confidence={conf} note={note!r}")


def a4_a5() -> None:
    """反例：带着上一条问新题，必须断开。走普通链路（不调综合层）。

    A5 只要求「断开」：不得把资助内容拼进来，且落到食堂相关的条目（`shitang-*` 任一条）；
    「食堂几点开」落在 `shitang-shijian`（食堂时间）比 `shitang-canting` 更准，不能写死成后者。
    """
    for case, q, want in (("A4", "校园卡丢了怎么补办", ("xyk-buka",)),
                          ("A5", "食堂几点开", ("shitang-shijian", "shitang-canting"))):
        try:
            r = app.answer_question(q, context_item="zxj-guojia-runding")
        except Exception as e:  # noqa: BLE001
            rec(case, FAIL, f"异常 {type(e).__name__}: {e}")
            continue
        got = (r.get("item") or {}).get("id") if isinstance(r.get("item"), dict) else r.get("item")
        body = " ".join(str(x.get("text") or "") for x in (r.get("answers") or []))
        mixed = "家庭经济困难" in body
        ok = (got in want) and not mixed
        rec(case, PASS if ok else FAIL, f"item={got} 期望∈{want} 串题={mixed}")


def main() -> None:
    print(f"app.py {len(Path(app.__file__).read_text(encoding='utf-8').splitlines())} 行", flush=True)
    d1 = a1_0()
    a1_a3_a6(d1)
    a4_a5()
    bad = [r for r in rows if r[1] == FAIL]
    print("\n" + "=" * 60)
    print(f"共 {len(rows)} 项：PASS {sum(1 for r in rows if r[1] == PASS)} / "
          f"FAIL {len(bad)} / SKIP {sum(1 for r in rows if r[1] == SKIP)}")
    if bad:
        print("失败项：", [r[0] for r in bad])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
