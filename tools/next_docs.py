"""给编排 agent 用：吐 N 份「还没做、也不在飞」的文档，直接可粘进子代理任务书。

已完成 = _review_items/sections/<slug>.json 存在；
在飞   = _review_items/_inflight.txt 里的一行（派活时追加，收波时清理）。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/next_docs.py --n 8
  ./.venv/Scripts/python.exe -X utf8 -u tools/next_docs.py --n 8 --exclude a,b,c
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEC = ROOT / "_review_items" / "sections"
INFLIGHT = ROOT / "_review_items" / "_inflight.txt"


def arg(name: str, default: str = "") -> str:
    for i, a in enumerate(sys.argv[1:]):
        if a == name and i + 2 <= len(sys.argv[1:]):
            return sys.argv[1:][i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def main() -> None:
    n = int(arg("--n", "8"))
    extra = {s for s in arg("--exclude").split(",") if s.strip()}
    done = {p.stem for p in SEC.glob("*.json") if not p.name.startswith("_")}
    busy = set()
    if INFLIGHT.is_file():
        busy = {ln.strip() for ln in INFLIGHT.read_text(encoding="utf-8").splitlines() if ln.strip()}
    busy |= extra

    out = subprocess.run(
        [sys.executable, "-X", "utf8", "-u", str(ROOT / "tools" / "toc_next_batch.py"),
         "--n", "400", "--chars", "900000", "--json"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    d = json.loads(out.stdout)
    pick = [b for b in d["batch"] if b["key"] not in done and b["key"] not in busy][:n]

    for b in pick:
        p = str(b["path"]).replace("\\", "/")
        print(f"- slug={b['key']}  path={p}  chars={b['chars']}")
    print(f"# 取 {len(pick)} 份 / 合计 {sum(b['chars'] for b in pick)} 字符"
          f"（剩余 {d['left']} 份 {d['left_chars']} 字符）")

    # 自动登记为在飞，避免下一次重复派
    with INFLIGHT.open("a", encoding="utf-8") as fh:
        for b in pick:
            fh.write(b["key"] + "\n")


if __name__ == "__main__":
    main()
