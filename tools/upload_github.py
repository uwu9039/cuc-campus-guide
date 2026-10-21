"""把项目上传到 GitHub（公有库）。token 通过 DPAPI 脚本在内存里取，不落盘、不回显。

用法：
    python tools/upload_github.py --repo cuc-campus-guide --desc "..." [--dry-run]

实现要点：
  - github.com 直连不通，全走 api.github.com
  - 用 Git Data API：blobs → tree → commit → ref，避免给每个文件单独提交
  - 并发上传 blob（默认 8 线程）
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
SKIP_DIRS = {".venv", "__pycache__", "dist", ".git", "piptest"}
SKIP_FILES = {".env", "urls.txt", "items.json.bak", "live.png", "presets.png"}
SKIP_PREFIX = ("shot",)


def token() -> str:
    path = os.path.expandvars(r"%USERPROFILE%\.dsh\skills\github-credential\gh-token.ps1")
    ps = "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force; & '%s'" % path

    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, timeout=60)
    raw = out.stdout
    t = "".join(ch for ch in raw.decode("utf-8", "ignore") if 32 <= ord(ch) < 127).strip()
    if not t or t.startswith("Error"):
        raise SystemExit("取 token 失败（不显示内容）")
    return t


def call(method: str, url: str, tok: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"token {tok}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "dsh-agent",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


BULK_DIRS = {"crawl", "wechat", "pdf"}   # 语料正文打包成 sources-archive.tar.gz，不再逐个上传


def collect() -> list[tuple[str, Path]]:
    files = []
    for p in ROOT.rglob("*"):
        if p.is_dir():
            continue
        if set(p.parts) & SKIP_DIRS:
            continue
        if p.name in SKIP_FILES or p.name.startswith(SKIP_PREFIX):
            continue
        rel = p.relative_to(ROOT)
        # sources/ 下的正文进压缩包；索引文件仍按明文件上传
        if len(rel.parts) >= 3 and rel.parts[0] == "sources" and rel.parts[1] in BULK_DIRS:
            continue
        if len(rel.parts) == 2 and rel.parts[0] == "sources" and rel.suffix == ".txt":
            continue
        files.append((rel.as_posix(), p))
    return sorted(files)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--desc", default="中国传媒大学校园办事向导 · 智能体节参赛作品")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    files = collect()
    total = sum(p.stat().st_size for _, p in files)
    print(f"准备上传 {len(files)} 个文件，原始 {total/1024/1024:.2f} MB")
    if args.dry_run:
        for f, _ in files[:20]:
            print("  ", f)
        return

    tok = token()
    me = call("GET", f"{API}/user", tok)[1]
    owner = me["login"]
    print(f"账号：{owner}")

    st, repo = call("POST", f"{API}/user/repos", tok, {
        "name": args.repo, "description": args.desc, "private": False,
        "has_issues": True, "has_wiki": False, "auto_init": False,
    })
    if st == 201:
        print(f"仓库已创建：{repo['html_url']}")
        time.sleep(1.5)
    elif st == 422:
        print("仓库已存在，继续推送")
    else:
        raise SystemExit(f"建仓失败 {st}: {repo.get('message')}")

    # 空仓库不能直接建 blob：先放一个引导文件，产生首个 commit
    st, head = call("GET", f"{API}/repos/{owner}/{args.repo}/git/ref/heads/main", tok)
    if st != 200:
        st2, _ = call("PUT", f"{API}/repos/{owner}/{args.repo}/contents/.bootstrap", tok,
                      {"message": "chore: init repository",
                       "content": base64.b64encode(b"bootstrap\n").decode()})
        print("已初始化仓库：", st2)
        for _ in range(10):
            time.sleep(1)
            st, head = call("GET", f"{API}/repos/{owner}/{args.repo}/git/ref/heads/main", tok)
            if st == 200:
                break
    parent = head["object"]["sha"] if st == 200 else None
    print("父提交：", (parent or "")[:8])

    # blobs（并发）
    blobs: list[dict] = []
    lock = {"done": 0}

    def put(item):
        path, p = item
        content = base64.b64encode(p.read_bytes()).decode()
        for attempt in range(3):
            s, r = call("POST", f"{API}/repos/{owner}/{args.repo}/git/blobs", tok,
                        {"content": content, "encoding": "base64"})
            if s == 201:
                return {"path": path, "mode": "100644", "type": "blob", "sha": r["sha"]}
            time.sleep(1 + attempt)
        raise RuntimeError(f"blob 失败 {path}: {s}")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(put, it) for it in files]
        for f in as_completed(futs):
            blobs.append(f.result())
            lock["done"] += 1
            if lock["done"] % 50 == 0:
                print(f"  已上传 {lock['done']}/{len(files)}")

    print(f"blob 完成 {len(blobs)} 个，开始建 tree")
    st, tree = call("POST", f"{API}/repos/{owner}/{args.repo}/git/trees", tok, {"tree": blobs})
    if st != 201:
        raise SystemExit(f"tree 失败 {st}: {tree.get('message')}")

    msg = ("feat: 校园办事向导 v0.1\n\n"
           "105 条校园事项 · 627 个可追溯事实 · 123 条预置问法\n"
           "数据层每条事实均带官方原文引文，由 check_quotes.py 强制校验\n")
    payload = {"message": msg, "tree": tree["sha"], "parents": [parent] if parent else []}
    st, commit = call("POST", f"{API}/repos/{owner}/{args.repo}/git/commits", tok, payload)
    if st != 201:
        raise SystemExit(f"commit 失败 {st}: {commit.get('message')}")

    st, ref = call("PATCH", f"{API}/repos/{owner}/{args.repo}/git/refs/heads/main", tok,
                   {"sha": commit["sha"], "force": True})
    print("更新 main：", st)

    st, info = call("GET", f"{API}/repos/{owner}/{args.repo}", tok)
    print(f"\n完成：{info.get('html_url')}")
    print(f"  commit {commit['sha'][:8]} · 文件 {len(blobs)} 个")


if __name__ == "__main__":
    main()
