"""检查并删除仓库里不该有的残留文件（日志、依赖本机环境的脚本）。

用法：
    python tools/_clean_repo.py --check
    python tools/_clean_repo.py --apply
"""
from __future__ import annotations

import base64
import json
import sys

sys.path.insert(0, "D:/DSH/智能体节/tools")
import _release as r  # noqa: E402

API = "https://api.github.com"
REPO = "uwu9039/cuc-campus-guide"

SUSPECT = [
    "upload.log",
    "tools/upload_github.py",
    "tools/ask_aia.py",
    "tools/ask_aia2.py",
    "tools/cdp_type.mjs",
]
KEYS = ["sk-", "ghp_", "skills", "Users", "token", "随便聊点"]


def main() -> None:
    apply = "--apply" in sys.argv
    tok = r.token()

    for path in SUSPECT:
        st, d = r.call("GET", f"{API}/repos/{REPO}/contents/{path}", tok)
        if st != 200:
            print(f"{path}: 不在仓库")
            continue
        txt = base64.b64decode(d["content"]).decode("utf-8", "ignore")
        found = [k for k in KEYS if k in txt]
        print(f"{path}: {len(txt)} 字符，命中 {found or '无'}")

    if not apply:
        return

    st, ref = r.call("GET", f"{API}/repos/{REPO}/git/ref/heads/main", tok)
    parent = ref["object"]["sha"]
    st, commit = r.call("GET", f"{API}/repos/{REPO}/git/commits/{parent}", tok)
    base_tree = commit["tree"]["sha"]

    entries = [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in SUSPECT]
    st, tree = r.call("POST", f"{API}/repos/{REPO}/git/trees", tok,
                      {"base_tree": base_tree, "tree": entries})
    if st != 201:
        raise SystemExit(f"tree 失败 {st}: {tree}")
    st, c = r.call("POST", f"{API}/repos/{REPO}/git/commits", tok,
                   {"message": "chore: 删除日志与依赖本机环境的实验脚本",
                    "tree": tree["sha"], "parents": [parent]})
    if st != 201:
        raise SystemExit(f"commit 失败 {st}: {c}")
    st, _ = r.call("PATCH", f"{API}/repos/{REPO}/git/refs/heads/main", tok,
                   {"sha": c["sha"], "force": True})
    print(f"✓ 已删除 {len(SUSPECT)} 个文件，提交 {c['sha'][:8]}，ref {st}")


if __name__ == "__main__":
    main()
