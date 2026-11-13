"""定向发布：跳过 >2MB 的归档/gzip，一次提交。

为什么不用 `_release.py` 全量跑：
1. 它每次都 `build_items_gz()`（71MB items.json 压 level 9），在这台机器上要 8–10 分钟才出第一行；
2. 6MB 级的 blob 在沙箱网络里上传极慢，会卡在 items.json.gz 上不动（实测 14 分钟)。

这里只传代码与文档（≤2MB），大归档留给单独的慢速上传。
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _release as R  # noqa: E402

MAX = 2 * 1024 * 1024
MSG = "chore(v1.0.0): 章节索引三层 + 上下文修复（不升版本号）"


def main() -> None:
    tok = R.token()
    files = [(p, f) for p, f in R.collect() if f.stat().st_size <= MAX]
    leaks = R.leak_scan(files)
    if leaks:
        print(f"泄漏守卫拦下 {len(leaks)} 处", flush=True)
        for p, hit in leaks[:10]:
            print("  ", p, "←", hit)
        raise SystemExit(2)

    st, ref = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/ref/heads/main", tok)
    parent = ref["object"]["sha"]
    st, commit = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/commits/{parent}", tok)
    base_tree = commit["tree"]["sha"]
    st, tree = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/trees/{base_tree}?recursive=1", tok)
    existing = {t["path"]: t["sha"] for t in tree["tree"] if t["type"] == "blob"}

    todo = [(p, f) for p, f in files if existing.get(p) != R.blob_sha(f)]
    print(f"仓库 {len(existing)} 文件；本地可传 {len(files)}；本次 {len(todo)}（≤{MAX // 1024} KB）", flush=True)

    entries = []
    for i, (p, f) in enumerate(todo, 1):
        content = base64.b64encode(f.read_bytes()).decode()
        st, r = R.call("POST", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/blobs", tok,
                       {"content": content, "encoding": "base64"})
        if st == 201:
            entries.append({"path": p, "mode": "100644", "type": "blob", "sha": r["sha"]})
        else:
            print(f"  ✗ {p} ({st})", flush=True)
        if i % 10 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)} {p}", flush=True)

    if not entries:
        print("没有变化", flush=True)
        return
    st, new_tree = R.call("POST", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/trees", tok,
                          {"base_tree": base_tree, "tree": entries})
    if st != 201:
        raise SystemExit(f"tree 失败 {st}")
    st, new_commit = R.call("POST", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/commits", tok,
                            {"message": MSG, "tree": new_tree["sha"], "parents": [parent]})
    if st != 201:
        raise SystemExit(f"commit 失败 {st}")
    R.call("PATCH", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/refs/heads/main", tok,
           {"sha": new_commit["sha"], "force": True})
    print(f"✓ {new_commit['sha'][:8]} 更新 {len(entries)} 个文件", flush=True)


if __name__ == "__main__":
    main()
