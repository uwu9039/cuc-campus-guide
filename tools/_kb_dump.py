"""把知识库里和问题最相关的条目原文倒出来，供人工写「金标准答案」。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_kb_dump.py "转专业 宿舍" "国家奖学金 标准"
只读，不写文件。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

FIELDS = ("answer", "summary", "steps", "materials", "fee", "window", "hours",
          "duration", "location", "pitfalls", "note", "scope_note")


def show(it: dict, n: int) -> None:
    print(f"\n--- [{n}] {it['id']} | {it.get('title')} | dept={it.get('dept')} "
          f"| status={it.get('status')}")
    for f in FIELDS:
        v = it.get(f)
        if not v:
            continue
        if isinstance(v, list):
            txt = "；".join(str(x.get("what") if isinstance(x, dict) else x) for x in v)
        else:
            txt = str(v)
        print(f"    {f}: {txt[:600]}")
    ev = it.get("evidence") or {}
    for k, v in list(ev.items())[:4]:
        for one in app._ev_items(v):
            q = str((one or {}).get("quote") or "")[:160]
            lab = app.src_label(str((one or {}).get("src") or "")).get("label", "")
            print(f"    原文[{k}] {lab[:24]}：{q}")


def main() -> None:
    for q in sys.argv[1:]:
        print("=" * 78)
        print("查询：", q)
        ranked = app.rank(q)[:3]
        for n, (it, sc) in enumerate(ranked, 1):
            print(f"  分数 {sc}")
            show(it, n)


if __name__ == "__main__":
    main()
