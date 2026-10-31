"""把 206 题的真实回答渲染成可逐条阅读的对照文件。

用法：
    python tools/review_206_read.py --base _review_items/eval_206_read_1030pm8.txt \
        --out _review_items/eval_206_read_1030pm10.txt --label pm10
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402

QFILE = ROOT / "aia-runs" / "questions-expanded.txt"


def parse_base(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    out: dict[int, str] = {}
    cur = None
    buf: list[str] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\[(\d+)\] ", ln)
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf).strip()
            cur = int(m.group(1))
            buf = [ln]
        elif cur is not None and not ln.startswith("标记：") and not ln.startswith("说明："):
            if "命中：" in ln:
                ln = re.sub(r"\[(?:已改|同前)\]", "[@@]", ln)
            buf.append(ln)
    if cur is not None:
        out[cur] = "\n".join(buf).strip()
    return out


def render(n: int, q: str, resp: dict) -> str:
    item = resp.get("item") or {}
    focus = "/".join(resp.get("focus") or []) or "无"
    lines = [f"[{n}] {q}", f"  命中：{item.get('id') or ''} | 聚焦：{focus} | [@@] | 反问：{bool(resp.get('ambiguous'))}"]
    for a in resp.get("answers") or []:
        text = a.get("text")
        if not text:
            continue
        label = a.get("label") or "整体流程"
        lines.append(f"  【{label}】{text}")
    note = resp.get("note")
    if note:
        lines.append(f"  提示：{note}")
    rel = [r.get("title") for r in (resp.get("related_items") or []) if r.get("title")]
    if rel:
        lines.append("  相关：" + "、".join(rel))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    base = parse_base(ROOT / args.base) if args.base else {}
    qs = [ln.strip() for ln in QFILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out_lines = [
        f"206 题复测完整版（2026-10-30 {args.label}）",
        "说明：每题按真实接口输出渲染，含全部回答段、提示与相关事项。",
        f"标记：[已改] = 和 {Path(args.base).stem if args.base else '基线'} 的回答不同；[同前] = 回答没变。",
        "",
    ]
    changed = 0
    for n, q in enumerate(qs, 1):
        try:
            resp = app.answer_question(q, {})
        except Exception as e:  # noqa: BLE001
            resp = {"matched": False, "answers": [], "error": f"{type(e).__name__}: {e}"}
        body = render(n, q, resp)
        was = base.get(n)
        same = was is not None and was == body
        if not same:
            changed += 1
        body = body.replace("[@@]", "[同前]" if same else "[已改]")
        out_lines.append(body)
        out_lines.append("")
    dest = ROOT / args.out
    dest.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"写入 {dest}，共 {len(qs)} 题，变化 {changed} 题")


if __name__ == "__main__":
    main()
