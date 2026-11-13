"""用修正后的关键词判据，重算历史 score JSON（不重新生成答案）。

背景：`_score_golden.py` 原先把 `"不作调整|不再变动"` 这种 `|` 或写法当成字面串匹配，
22/44 条要点恒 False。修好之后，历史跑分里存的 `answer` 还在，可以原地重算，
不用再花 4 分钟重跑一遍综合层。

用法：
    ./.venv/Scripts/python.exe -X utf8 -u tools/_golden_rescore.py <score.json> [more.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "_review_items" / "golden_20261111.json"


def kw_hit(ans: str, kws: list[str]) -> bool:
    return all(any(x in ans for x in k.split("|")) for k in kws)


def main() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
    kws = {(c["q"], p["p"]): (p.get("kw") or []) for c in golden for p in c["points"]}

    for path in sys.argv[1:]:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        tot = cov = loose = judge = 0
        for row in d["rows"]:
            ans = row.get("answer") or ""
            for pt in row["points"]:
                tot += 1
                kw = kw_hit(ans, kws.get((row["q"], pt["p"]), []))
                judge += 1 if pt["judge"] else 0
                cov += 1 if (kw and pt["judge"]) else 0
                loose += 1 if (kw or pt["judge"]) else 0
        print(f"{Path(path).name}: 严格 {cov}/{tot} = {cov/tot:.0%}　"
              f"宽松 {loose}/{tot} = {loose/tot:.0%}　判读 {judge}/{tot} = {judge/tot:.0%}")


if __name__ == "__main__":
    main()
