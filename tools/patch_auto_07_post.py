"""auto_07 复核后补删：仅删除已被完整覆盖的 auto 碎片。"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"
LOG = ROOT / "_review_items" / "applied_auto_07_post.txt"
BACKUP = ROOT / "_review_items" / "items_before_auto_07_post.json"

DROPS = [
    ("pt-355f5733c3", "pt-c723948819", None),
    ("pt-d3db130a72", "pt-06432dd193", None),
    ("pt-6bb0c525a5", "pt-48f2190582", None),
    ("pt-e39e486074", "pt-135a06b8fb", None),
    ("pt-1883b3d5da", "pt-6b139427c0", "3."),
]


def sq(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


data = json.loads(P.read_text(encoding="utf-8"))
items = {it["id"]: it for it in data["items"]}
shutil.copy2(P, BACKUP)

before = len(data["items"])
lines = []
for pid, cover_id, strip in DROPS:
    it = items[pid]
    cov = items[cover_id]
    assert it.get("auto") is True, f"{pid} 不是 auto 条目"
    assert cov.get("auto") is True, f"{cover_id} 不是 auto 条目"
    frag = (it.get("answer") or "").strip()
    if strip and frag.startswith(strip):
        frag = frag[len(strip):]
    assert sq(frag) and sq(frag) in sq(cov.get("answer")), f"{pid} 未被 {cover_id} 完整覆盖"
    lines.append(f"DROP {pid} | {it.get('title', '')}")
    lines.append(f"  answer: {frag}")
    lines.append(f"  covered_by: {cover_id} | {cov.get('title', '')[:70]}")
    lines.append("")

data["items"] = [it for it in data["items"] if it["id"] not in {d[0] for d in DROPS}]
P.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
LOG.write_text("\n".join(lines), encoding="utf-8")
print("before", before, "after", len(data["items"]), "dropped", before - len(data["items"]))