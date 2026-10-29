"""把 v0.2 的 items.json 取回来，并用旧版（未打码）里的号码还原打码处。"""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import _release as r  # noqa: E402

API = "https://api.github.com"
REPO = "uwu9039/cuc-campus-guide"
ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / "items.json"
OLD = ROOT / "items-old.json"

MASK = re.compile(r"(1[3-9]\d)\*\*\*\*(\d{4})")


def main() -> None:
    # 1. 现在本地的 items.json 是从旧提交恢复的（未打码但条目少）→ 备份
    if not OLD.exists():
        OLD.write_text(LOCAL.read_text(encoding="utf-8"), encoding="utf-8")
    old_text = OLD.read_text(encoding="utf-8")
    old_data = json.loads(old_text)

    # 2. 取 v0.2 的 items.json（条目全，但号码被打码）
    tok = r.token()
    st, d = r.call("GET", f"{API}/repos/{REPO}/contents/items.json?ref=main", tok)
    if st != 200:
        raise SystemExit(f"取远端失败 {st}")
    new_text = base64.b64decode(d["content"]).decode("utf-8")

    # 3. 建号码映射：打码后的 (前3,后4) → 原始 11 位
    mapping: dict[tuple[str, str], set[str]] = {}
    for m in re.finditer(r"(1[3-9]\d)\d{4}(\d{4})", old_text):
        mapping.setdefault((m.group(1), m.group(2)), set()).add(m.group(0))

    def restore(m: re.Match) -> str:
        key = (m.group(1), m.group(2))
        cands = mapping.get(key)
        if cands and len(cands) == 1:
            return next(iter(cands))
        return m.group(0)  # 找不到或有多解就保留打码

    restored, n = MASK.subn(restore, new_text)
    LOCAL.write_text(restored, encoding="utf-8")

    data = json.loads(restored)
    left = len(MASK.findall(restored))
    print(f"条目 {len(data['items'])}，事实 {sum(len(i.get('evidence') or {}) for i in data['items'])}")
    print(f"还原号码 {n - left} 处，仍打码 {left} 处")


if __name__ == "__main__":
    main()
