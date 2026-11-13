"""确定性判读：用管道自己的裁决（direct/not_listed/inferable/missing）判「作答/拒答」。

和 LLM 判读互为旁证：
  · 有一条前提判成 direct/not_listed/inferable → 作答
  · 全部前提都是 missing（或没有分层） → 拒答
用法：./.venv/Scripts/python.exe -X utf8 -u tools/_det_metric.py judged_*.jsonl
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWERY = {"direct", "not_listed", "inferable"}


def det_kind(rec: dict) -> str:
    layers = rec.get("layers") or []
    if not layers:
        return "no_output"
    vs = [str(x.get("verdict") or "") for x in layers]
    if any(v in ANSWERY for v in vs):
        return "answered"
    if all(v == "missing" for v in vs):
        return "refused"
    return "unknown"


def main() -> None:
    for name in sys.argv[1:]:
        p = Path(name)
        if not p.exists():
            p = ROOT / "_review_items" / name
        rows = [json.loads(line) for line in p.open(encoding="utf-8")]
        cnt = {"answered": 0, "refused": 0, "unknown": 0, "no_output": 0}
        agree = disagree = 0
        for r in rows:
            k = det_kind(r)
            cnt[k] = cnt.get(k, 0) + 1
            j = (r.get("judge") or {}).get("kind")
            if j in ("answered", "refused") and k in ("answered", "refused"):
                if (j == "answered") == (k == "answered"):
                    agree += 1
                else:
                    disagree += 1
        tot = agree + disagree
        print(f"[{p.name}] 确定性判读 {cnt}；与 LLM 判读一致 "
              f"{agree}/{tot} ({round(100 * agree / tot) if tot else 0}%)")


if __name__ == "__main__":
    main()
