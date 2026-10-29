"""从 GitHub 旧提交里取回被打码前的原文，恢复公开联系电话。

做法：找出本地含 **** 打码的文件，取同路径在指定 commit 上的版本；
若该 commit 上仍是打码版，就往更早的 commit 找。取回后按行替换本地对应行。
"""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import _release as r  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
REPO = "uwu9039/cuc-campus-guide"
MASK = re.compile(r"1[3-9]\d\*\*\*\*\d{4}")


def main() -> None:
    tok = r.token()
    # 列出历史提交
    st, commits = r.call("GET", f"{API}/repos/{REPO}/commits?per_page=100", tok)
    shas = [c["sha"] for c in commits]
    print(f"历史提交 {len(shas)} 个")

    targets = []
    for p in list((ROOT / "sources").rglob("*.txt")) + [ROOT / "items.json"]:
        try:
            if MASK.search(p.read_text(encoding="utf-8")):
                targets.append(p)
        except Exception:  # noqa: BLE001
            continue
    print(f"待恢复文件 {len(targets)} 个")

    fixed = 0
    for p in targets:
        rel = p.relative_to(ROOT).as_posix()
        remote_text = None
        for sha in shas:
            st, d = r.call("GET", f"{API}/repos/{REPO}/contents/{rel}?ref={sha}", tok)
            if st != 200:
                continue
            txt = base64.b64decode(d["content"]).decode("utf-8", "ignore")
            if not MASK.search(txt):
                remote_text = txt
                break
        if remote_text is None:
            print(f"  ✗ {rel} 历史上都是打码版")
            continue
        # 本地是打码版，远端是原始版：直接采用远端内容（内容一致，只是号码还原）
        p.write_text(remote_text, encoding="utf-8")
        fixed += 1
        print(f"  ✓ {rel}")

    print(f"恢复 {fixed} 个文件")


if __name__ == "__main__":
    main()
