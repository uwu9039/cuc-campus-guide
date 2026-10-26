"""把 sources/ 的 476 份语料正文以明文文件补进 GitHub 仓库（限速提交，避开次级限流）。

用法：python tools/upload_sources_raw.py [--rate 0.8]
"""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import upload_github as u  # noqa: E402

API = "https://api.github.com"
OWNER, REPO = "uwu9039", "cuc-campus-guide"


def main() -> None:
    rate = 0.8
    limit = 0
    if "--max" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--max") + 1])
    if "--rate" in sys.argv:
        rate = float(sys.argv[sys.argv.index("--rate") + 1])
    tok = u.token()

    # 现有 tree，作为 base
    st, ref = u.call("GET", f"{API}/repos/{OWNER}/{REPO}/git/ref/heads/main", tok)
    parent = ref["object"]["sha"]
    st, commit = u.call("GET", f"{API}/repos/{OWNER}/{REPO}/git/commits/{parent}", tok)
    base_tree = commit["tree"]["sha"]
    st, tree = u.call("GET", f"{API}/repos/{OWNER}/{REPO}/git/trees/{base_tree}?recursive=1", tok)
    existing = {t["path"] for t in tree["tree"]}

    wanted: list[Path] = []
    for sub in ("crawl", "wechat", "pdf"):
        wanted += sorted((ROOT / "sources" / sub).glob("*.txt"))
    wanted += sorted(p for p in (ROOT / "sources").glob("*.txt"))
    todo = [p for p in wanted if f"sources/{p.parent.name}/{p.name}" not in existing
            and f"sources/{p.name}" not in existing]
    print(f"待补 {len(todo)} 个文件（已存在 {len(wanted)-len(todo)} 个）")

    if limit:
        todo = todo[:limit]
        print(f"本次最多处理 {len(todo)} 个")
    entries = []
    for i, p in enumerate(todo, 1):
        rel = p.relative_to(ROOT).as_posix()
        content = base64.b64encode(p.read_bytes()).decode()
        for attempt in range(4):
            st, r = u.call("POST", f"{API}/repos/{OWNER}/{REPO}/git/blobs", tok,
                           {"content": content, "encoding": "base64"})
            if st == 201:
                entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": r["sha"]})
                break
            time.sleep(2 + attempt * 3)
        else:
            print(f"  ✗ 放弃 {rel} ({st})")
        if i % 25 == 0:
            print(f"  已建 blob {i}/{len(todo)}")
        time.sleep(rate)

    if not entries:
        print("没有新增文件")
        return

    st, new_tree = u.call("POST", f"{API}/repos/{OWNER}/{REPO}/git/trees", tok,
                          {"base_tree": base_tree, "tree": entries})
    if st != 201:
        raise SystemExit(f"tree 失败 {st}: {new_tree}")
    st, new_commit = u.call("POST", f"{API}/repos/{OWNER}/{REPO}/git/commits", tok,
                            {"message": f"data: 补入 {len(entries)} 份官方语料正文（可在线阅读）",
                             "tree": new_tree["sha"], "parents": [parent]})
    if st != 201:
        raise SystemExit(f"commit 失败 {st}: {new_commit}")
    st, _ = u.call("PATCH", f"{API}/repos/{OWNER}/{REPO}/git/refs/heads/main", tok,
                   {"sha": new_commit["sha"], "force": True})
    print(f"完成：新增 {len(entries)} 个文件，commit {new_commit['sha'][:8]}，ref {st}")


if __name__ == "__main__":
    main()
