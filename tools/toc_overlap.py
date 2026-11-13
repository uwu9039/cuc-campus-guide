"""复核辅助：算「条目正文 vs 所属节原文」的四字组覆盖率，只提示不判定。

用途：给人工复核者一份「值得多看一眼」的清单。覆盖率低不等于挂错
（表格行片段、超短条目都会低），必须回原文人工判断。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/toc_overlap.py _review_items/toc/att-c86ee325fa__018.json
  ./.venv/Scripts/python.exe -X utf8 -u tools/toc_overlap.py _review_items/toc --below 0.2
  ./.venv/Scripts/python.exe -X utf8 -u tools/toc_overlap.py <file> --all      # 打印全部而非只打印低于阈值
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def norm(s: str) -> str:
    return re.sub(r"[^\u4e00-\u9fff0-9a-z%]", "", (s or "").lower())


def grams(s: str, n: int = 4) -> set[str]:
    t = norm(s)
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def main() -> None:
    argv = sys.argv[1:]
    below = 0.2
    show_all = "--all" in argv
    # --below 的值不是路径，必须从位置参数里剔除（否则会被当成文件打「读不了」）
    value_of = {"--below"}
    args: list[str] = []
    skip = False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        if a in value_of:
            if i + 1 < len(argv):
                try:
                    below = float(argv[i + 1])
                except ValueError:
                    pass
            skip = True
            continue
        if a.startswith("--"):
            continue
        args.append(a)
    if not args:
        print(__doc__)
        sys.exit(1)
    items = {x["id"]: x for x in
             json.load(open(ROOT / "items.json", encoding="utf-8"))["items"]}
    targets: list[Path] = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            targets += [q for q in sorted(p.glob("*.json")) if not q.name.startswith("_")]
        else:
            targets.append(p)
    total = low = 0
    for p in targets:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"{p.name}: 读不了 {e}")
            continue
        rows = []
        for s in d.get("sections") or []:
            sg = grams(" ".join(c.get("text") or "" for c in (s.get("clauses") or [])))
            for eid in s.get("entry_ids") or []:
                it = items.get(eid) or {}
                txt = " ".join([str(it.get("title") or ""), str(it.get("answer") or "")])
                eg = grams(txt)
                if not eg or not sg:
                    continue
                rows.append((len(eg & sg) / len(eg), eid, s.get("section_id"),
                             s.get("heading"), str(it.get("title") or "")[:40]))
        if not rows:
            continue
        rows.sort()
        bad = [r for r in rows if r[0] < below]
        total += len(rows)
        low += len(bad)
        print(f"\n{p.name}: {len(rows)} 条，<{below} 的 {len(bad)} 条")
        for cov, eid, sid, head, t in (rows if show_all else bad):
            print(f"  {cov:.2f} {eid} → {sid}「{head}」| 条目: {t}")
    if total:
        print(f"\n合计 {total} 条，低于 {below} 的 {low} 条"
              f"（覆盖率低不等于挂错，需回原文人工判断）")


if __name__ == "__main__":
    main()
