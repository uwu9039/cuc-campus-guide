"""发布前对照：本地要传什么、哪些是仓库里没有的新文件、哪些是改动。

只读：GET 仓库 tree，不写任何东西。
用法：
    export GH_TOKEN=$(powershell -NoProfile -File "%USERPROFILE%/.dsh/skills/github-credential/gh-token.ps1")
    ./.venv/Scripts/python.exe tools/_release_plan.py
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _release as R  # noqa: E402


def main() -> None:
    tok = R.token()
    st, ref = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/ref/heads/main", tok)
    parent = ref["object"]["sha"]
    st, commit = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/commits/{parent}", tok)
    st, tree = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/trees/{commit['tree']['sha']}?recursive=1", tok)
    remote = {t["path"]: t["sha"] for t in tree["tree"] if t["type"] == "blob"}

    files = R.collect()
    new = [p for p, _ in files if p not in remote]
    chg = [p for p, f in files if p in remote and remote[p] != R.blob_sha(f)]
    gone = [p for p in remote if p not in {x for x, _ in files}]

    print(f"仓库 main = {parent[:8]}，现有 {len(remote)} 个文件")
    print(f"本地收集 {len(files)} 个：新增 {len(new)} / 变更 {len(chg)} / 仓库有本地无 {len(gone)}")

    def show(title: str, items: list[str], limit: int = 60) -> None:
        print(f"\n== {title}（{len(items)}）")
        tops = collections.Counter(p.split("/")[0] if "/" in p else "(root)" for p in items)
        print("   分布:", dict(tops.most_common(12)))
        for p in items[:limit]:
            print("   ", p)
        if len(items) > limit:
            print(f"    … 还有 {len(items) - limit} 个")

    show("新增", new)
    show("变更", chg)
    show("仓库独有", gone, 20)


if __name__ == "__main__":
    main()
