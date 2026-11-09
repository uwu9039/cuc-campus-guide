"""抓取三处模型调用的 system prompt 原文，用于分片重构的逐字节等价验收。

用法：
    python tools/capture_prompts.py --out _review_items/prompt_golden.json
    python tools/capture_prompts.py --compare _review_items/prompt_golden.json

比对模式重新抓一遍并逐条断言字节相同，任何一条不同就退出码 1。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app  # noqa: E402

QUERIES = [
    "校园卡丢了怎么补办",
    "学校医保",
    "饿了怎么办",
    "ps激活",
    "图书馆",
    "绩点怎么算",
]

HISTORIES: dict[str, list[dict[str, str]] | None] = {
    "无历史": None,
    "购电历史": [
        {"role": "user", "content": "宿舍怎么购电"},
        {"role": "assistant", "content":
         "宿舍购电：校内和中蓝公寓在后勤保障处公众号微服务里的公寓购电绑定电表后用移动支付，"
         "也可以去艺术传播大楼一层校园生活服务大厅售电窗口办理。"},
    ],
}

CAPTURED: list[dict[str, object]] = []


def _recorder(msgs, **kw):
    CAPTURED.append({
        "system": msgs[0]["content"],
        "tail": msgs[-1]["content"],
        "n_msgs": len(msgs),
        "max_tokens": kw.get("max_tokens"),
    })
    return '{"__capture__": 1}'


def capture() -> list[dict[str, object]]:
    global CAPTURED
    real = app.ds_chat
    app.ds_chat = _recorder
    rows: list[dict[str, object]] = []
    try:
        for label, history in HISTORIES.items():
            for q in QUERIES:
                ranked = app.rank(q)
                pool = app.rerank_candidates(q, ranked)
                for fn_name, call in (
                    ("llm_route", lambda: app.llm_route(q, ranked[:8], history)),
                    ("llm_rerank", lambda: app.llm_rerank(q, pool, history)),
                    ("llm_rerank_menu",
                     lambda: app.llm_rerank(q, pool, history, menu_mode=True)),
                    ("llm_free_answer", lambda: app.llm_free_answer(q, history)),
                ):
                    CAPTURED = []
                    call()
                    for got in CAPTURED:
                        rows.append({"case": f"{label}/{q}/{fn_name}", **got})
    finally:
        app.ds_chat = real
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--compare")
    a = ap.parse_args()
    rows = capture()
    if a.out:
        Path(a.out).write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"抓到 {len(rows)} 条 prompt，写入 {a.out}")
        return 0
    if a.compare:
        base = json.loads(Path(a.compare).read_text(encoding="utf-8"))
        by_case = {r["case"]: r for r in base}
        bad = [r["case"] for r in rows
               if by_case.get(r["case"], {}).get("system") != r["system"]
               or by_case.get(r["case"], {}).get("n_msgs") != r["n_msgs"]]
        for case in bad:
            print(f"不一致：{case}")
        print(f"比对 {len(rows)} 条，不一致 {len(bad)} 条")
        return 1 if bad else 0
    print("要 --out 或 --compare")
    return 2


if __name__ == "__main__":
    sys.exit(main())
