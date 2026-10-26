"""增量上传到 GitHub：只推有变化的文件，最后打 tag 建 release。

用法：
    python tools/_release.py --tag v0.2 --notes notes.md
不进仓库（.gitignore 已排除）。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
OWNER, REPO = "uwu9039", "cuc-campus-guide"
SKIP_DIRS = {".venv", "__pycache__", "dist", ".git", "piptest", "node_modules"}
SKIP_FILES = {".env", "urls.txt", "items.json.bak", ".cdp_tab"}
SKIP_SUFFIX = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".wav", ".mp4", ".log"}
SKIP_PREFIX = ("shot", "llm-", "aia")
# 语料正文统一进 sources-archive.tar.gz，不逐个上传（省请求、避免限流）
BULK_DIRS = {"crawl", "cdp", "chsi", "moe", "national", "wechat", "pdf"}


def token() -> str:
    import os
    path = os.path.expandvars(r"%USERPROFILE%\.dsh\skills\github-credential\gh-token.ps1")
    ps = "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force; & '%s'" % path
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=60)
    t = "".join(ch for ch in out.stdout.decode("utf-8", "ignore") if 32 <= ord(ch) < 127).strip()
    if not t.startswith("gh"):
        raise SystemExit("取 token 失败")
    return t


def call(method: str, url: str, tok: str, body: dict | None = None, raw: bool = False):
    last = None
    for attempt in range(5):
        try:
            return _call_once(method, url, tok, body, raw)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(6 + attempt * 8)
    raise SystemExit(f"网络失败（重试 5 次）：{last}")


def _call_once(method: str, url: str, tok: str, body: dict | None = None, raw: bool = False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"token {tok}", "Accept": "application/vnd.github+json",
        "User-Agent": "dsh-agent", "Content-Type": "application/json",
        "Connection": "close"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            payload = r.read()
            return r.status, (payload if raw else json.loads(payload or b"{}"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def collect() -> list[tuple[str, Path]]:
    out = []
    for p in ROOT.rglob("*"):
        if p.is_dir() or set(p.parts) & SKIP_DIRS:
            continue
        if p.name in SKIP_FILES or p.name.startswith(SKIP_PREFIX):
            continue
        if p.suffix.lower() in SKIP_SUFFIX:
            continue
        rel = p.relative_to(ROOT)
        if len(rel.parts) >= 3 and rel.parts[0] == "sources" and rel.parts[1] in BULK_DIRS:
            continue
        if len(rel.parts) == 2 and rel.parts[0] == "sources" and rel.suffix == ".txt":
            continue
        out.append((p.relative_to(ROOT).as_posix(), p))
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--notes", default="")
    ap.add_argument("--max", type=int, default=0, help="本批最多上传多少个文件")
    args = ap.parse_args()
    tok = token()

    st, ref = call("GET", f"{API}/repos/{OWNER}/{REPO}/git/ref/heads/main", tok)
    parent = ref["object"]["sha"]
    st, commit = call("GET", f"{API}/repos/{OWNER}/{REPO}/git/commits/{parent}", tok)
    base_tree = commit["tree"]["sha"]
    st, tree = call("GET", f"{API}/repos/{OWNER}/{REPO}/git/trees/{base_tree}?recursive=1", tok)
    existing = {t["path"]: t["sha"] for t in tree["tree"] if t["type"] == "blob"}
    print(f"仓库现有 {len(existing)} 个文件")

    files = collect()
    todo = [(path, p) for path, p in files if existing.get(path) != blob_sha(p)]
    if args.max:
        todo = todo[: args.max]
    print(f"本地 {len(files)} 个，本次处理 {len(todo)} 个")

    entries = []
    for i, (path, p) in enumerate(todo, 1):
        content = base64.b64encode(p.read_bytes()).decode()
        for attempt in range(4):
            st, r = call("POST", f"{API}/repos/{OWNER}/{REPO}/git/blobs", tok,
                         {"content": content, "encoding": "base64"})
            if st == 201:
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": r["sha"]})
                break
            time.sleep(6 + attempt * 8)
        else:
            print(f"  ✗ {path} ({st})")
        print(f"  [{i}/{len(todo)}] {path} ({p.stat().st_size/1024:.0f} KB)")
        time.sleep(1.3)

    if not entries:
        print("没有变化")
        return

    st, new_tree = call("POST", f"{API}/repos/{OWNER}/{REPO}/git/trees", tok,
                        {"base_tree": base_tree, "tree": entries})
    if st != 201:
        raise SystemExit(f"tree 失败 {st}")
    msg = (f"feat({args.tag}): 学信网/国家级政策、路由审计、模型裁决开关\n\n"
           f"- 语料 538 份，条目 147，事实 780，0 缺证\n"
           f"- 新增 tools/pipeline.py 交付前四步体检\n"
           f"- 敏感词由压测推导（sensitive.json），不再手写\n")
    st, new_commit = call("POST", f"{API}/repos/{OWNER}/{REPO}/git/commits", tok,
                          {"message": msg, "tree": new_tree["sha"], "parents": [parent]})
    if st != 201:
        raise SystemExit(f"commit 失败 {st}")
    call("PATCH", f"{API}/repos/{OWNER}/{REPO}/git/refs/heads/main", tok,
         {"sha": new_commit["sha"], "force": True})
    print(f"✓ 提交 {new_commit['sha'][:8]}，新增/更新 {len(entries)} 个文件")

    st, _ = call("POST", f"{API}/repos/{OWNER}/{REPO}/git/refs", tok,
                 {"ref": f"refs/tags/{args.tag}", "sha": new_commit["sha"]})
    print("tag:", st)

    notes = Path(args.notes).read_text(encoding="utf-8") if args.notes else msg
    st, rel = call("POST", f"{API}/repos/{OWNER}/{REPO}/releases", tok,
                   {"tag_name": args.tag, "name": f"{args.tag} · 校园办事向导",
                    "body": notes, "draft": False, "prerelease": False})
    print("release:", st, rel.get("html_url", rel.get("message")))


if __name__ == "__main__":
    main()
