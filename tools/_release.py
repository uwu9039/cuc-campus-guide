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
SKIP_DIRS = {".venv", "__pycache__", "dist", ".git", "piptest", "node_modules",
             "aia-runs", "_quarantine", "vector", "wendao", "wendao-extra", ".qoder"}
SKIP_FILES = {".env", "download.devtools", "urls.txt", "items.json", "items.json.bak",
              "items-old.json", "ask-req.json", ".cdp_tab", "app-server.log",
              "_qout.txt", "_check_tmp.py", "_diag_coll.py", "_diag_docs.py",
              "_diag_failgroups.py", "_diag_quotes.py", "_remote_tree.json",
              "_clause-items.tmp.json", "huibian-2025.txt",
              "_pipeline_out.txt", "_eval_out.txt", "_v04_body.md"}
SKIP_SUFFIX = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".wav", ".mp4", ".log",
               ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".pptx", ".npy", ".jsonl",
               ".mp3", ".m4a", ".mov", ".webm"}
SKIP_PREFIX = ("shot", "llm-", "aia")
# 语料正文统一进 sources-archive.tar.gz，不逐个上传（省请求、避免限流）
BULK_DIRS = {"crawl", "cdp", "chsi", "moe", "national", "wechat", "pdf", "wendao-text"}
PLAN_DIR = "sources/local/_files"


def plan_pdf_names() -> set[str]:
    """转专业接收计划原件随包发布，前端「打开原始 PDF」才可用。"""
    data = json.loads((ROOT / "transfer-plans.json").read_text(encoding="utf-8"))
    return {Path(v["file"]).name for v in data.values()
            if isinstance(v, dict) and v.get("file")}


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
        # items.json 这类 30MB+ 的文件 base64 后 40MB+，慢网下 180 秒不够
        with urllib.request.urlopen(req, timeout=600) as r:
            payload = r.read()
            return r.status, (payload if raw else json.loads(payload or b"{}"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def collect() -> list[tuple[str, Path]]:
    out = []
    plans = plan_pdf_names()
    for p in ROOT.rglob("*"):
        if p.is_dir() or set(p.parts) & SKIP_DIRS:
            continue
        if p.name in SKIP_FILES or p.name.startswith(SKIP_PREFIX) or ".bak" in p.name:
            continue
        if p.suffix.lower() in SKIP_SUFFIX:
            rel_pdf = p.relative_to(ROOT).as_posix()
            keep = (rel_pdf.startswith(PLAN_DIR + "/") and p.name in plans) \
                or rel_pdf.startswith("web-next/qr/")   # 微专业报名 / 身份验证二维码要随包发布
            if not keep:
                continue
        rel = p.relative_to(ROOT)
        if len(rel.parts) >= 3 and rel.parts[0] == "sources" and rel.parts[1] in BULK_DIRS:
            continue
        if len(rel.parts) == 2 and rel.parts[0] == "sources" and rel.suffix == ".txt":
            continue
        out.append((p.relative_to(ROOT).as_posix(), p))
    return sorted(out)


def build_items_gz() -> None:
    """items.json 31MB，GitHub 大请求体会超时；每次发布自动同步压缩副本。"""
    import gzip
    src = ROOT / "items.json"
    if not src.exists():
        return
    out = gzip.compress(src.read_bytes(), 9, mtime=0)
    gz = ROOT / "items.json.gz"
    if not gz.exists() or gz.read_bytes() != out:
        gz.write_bytes(out)
        print(f"items.json.gz 已更新：{len(out)/1048576:.2f} MB")


def build_archive() -> None:
    """把 sources/ 下的正文（不含隔离区、向量库与二进制）打成发布用压缩包。"""
    import tarfile
    src = ROOT / "sources"
    ex_dirs = {"_quarantine", "vector"}
    keep_ext = {".txt", ".md", ".html", ".htm", ".json", ".csv"}
    picked = []
    for p in src.rglob("*"):
        if p.is_dir() or set(p.relative_to(src).parts) & ex_dirs:
            continue
        if p.name.startswith("_") or p.name == "huibian-2025.txt":
            continue
        if p.suffix.lower() in keep_ext:
            picked.append(p)
    out = ROOT / "sources-archive.tar.gz"
    with tarfile.open(out, "w:gz", compresslevel=9) as tf:
        for p in sorted(picked, key=lambda x: x.as_posix()):
            ti = tf.gettarinfo(str(p), arcname=p.relative_to(ROOT).as_posix())
            ti.mtime = 0
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            with p.open("rb") as fh:
                tf.addfile(ti, fh)
    print(f"语料归档：{len(picked)} 份，{out.stat().st_size/1048576:.2f} MB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--notes", default="")
    ap.add_argument("--message", default="", help="提交信息，默认按 tag 生成")
    ap.add_argument("--max", type=int, default=0, help="本批最多上传多少个文件")
    ap.add_argument("--dry-run", action="store_true", help="只打印清单，不写入 GitHub")
    ap.add_argument("--match", default="", help="只处理路径包含该子串的文件")
    ap.add_argument("--no-tag", action="store_true", help="只提交，不打 tag、不发 release")
    ap.add_argument("--rebuild-archive", action="store_true", help="重新打包 sources-archive.tar.gz")
    args = ap.parse_args()
    tok = token()
    build_items_gz()

    if args.rebuild_archive:
        build_archive()

    files = collect()
    if args.dry_run:
        import collections
        size = sum(p.stat().st_size for _, p in files)
        tops = collections.Counter(path.split("/")[0] if "/" in path else path for path, _ in files)
        print(f"待发布 {len(files)} 个文件，{size/1048576:.1f} MB")
        for name, count in tops.most_common(20):
            print(f"  {name}: {count}")
        for path, p in files:
            if p.name in SKIP_FILES or "quarantine" in path:
                print("  !! 敏感项", path)
        return

    st, ref = call("GET", f"{API}/repos/{OWNER}/{REPO}/git/ref/heads/main", tok)
    parent = ref["object"]["sha"]
    st, commit = call("GET", f"{API}/repos/{OWNER}/{REPO}/git/commits/{parent}", tok)
    base_tree = commit["tree"]["sha"]
    st, tree = call("GET", f"{API}/repos/{OWNER}/{REPO}/git/trees/{base_tree}?recursive=1", tok)
    existing = {t["path"]: t["sha"] for t in tree["tree"] if t["type"] == "blob"}
    print(f"仓库现有 {len(existing)} 个文件")

    todo = [(path, p) for path, p in files if existing.get(path) != blob_sha(p)]
    if args.match:
        todo = [t for t in todo if args.match in t[0]]
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
    msg = args.message or (
        f"feat({args.tag}): 条目扩展、校园地图、web-next 前端与路由修复\n\n"
        f"- 645 条事项 / 688 份语料 / 2744 条证据，0 缺证\n"
        f"- 新增校园地图 POI 36 处、16 学院转专业计划整份结构化\n"
        f"- 新增 web-next 双栏前端（地图抽屉、步骤列表、反问）\n"
        f"- 修复地点/复合问句被转专业计划劫持；清理文件名式标题\n")
    st, new_commit = call("POST", f"{API}/repos/{OWNER}/{REPO}/git/commits", tok,
                          {"message": msg, "tree": new_tree["sha"], "parents": [parent]})
    if st != 201:
        raise SystemExit(f"commit 失败 {st}")
    call("PATCH", f"{API}/repos/{OWNER}/{REPO}/git/refs/heads/main", tok,
         {"sha": new_commit["sha"], "force": True})
    print(f"✓ 提交 {new_commit['sha'][:8]}，新增/更新 {len(entries)} 个文件")
    if args.no_tag:
        return

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
