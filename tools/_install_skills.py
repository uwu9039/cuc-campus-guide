"""把选定的外部 skills 拉到工作区 _skills_tmp/（GitHub contents API，逐文件 base64）。

github.com / raw.githubusercontent / jsdelivr 在本机直连都失败（SSL 或超时），
但 api.github.com 可用，所以走 contents API。
产出目录结构即为待安装的 skill 目录，之后整体复制到 ~/.dsh/skills/ 即可。

用法：.venv/Scripts/python.exe tools/_install_skills.py
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "_skills_tmp")
UA = {"User-Agent": "dsh-skill-installer"}

# 目标 skill 名 -> (repo, 仓库内前缀, 是否只取该前缀)
TARGETS = [
    ("humanizer-zh", "op7418/Humanizer-zh", "", False),
    ("stop-slop", "hardikpandya/stop-slop", "", False),
    ("evaluation", "muratcankoylan/Agent-Skills-for-Context-Engineering", "skills/evaluation", True),
    ("advanced-evaluation", "muratcankoylan/Agent-Skills-for-Context-Engineering", "skills/advanced-evaluation", True),
    ("tool-design", "muratcankoylan/Agent-Skills-for-Context-Engineering", "skills/tool-design", True),
    ("skill-seekers", "yusufkaraaslan/Skill_Seekers", "skills/skill-seekers", True),
]
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".zip", ".mp4", ".pdf", ".woff", ".woff2"}
MAX_BYTES = 3 * 1024 * 1024


def api_get(url: str, tries: int = 3, timeout: int = 60) -> bytes:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as f:
                return f.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise last


def tree(repo: str, branch: str = "HEAD"):
    raw = api_get(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1")
    return [(e["path"], e.get("size", 0)) for e in json.loads(raw)["tree"] if e["type"] == "blob"]


def blob(repo: str, path: str) -> bytes:
    raw = api_get(f"https://api.github.com/repos/{repo}/contents/{path}?ref=HEAD")
    data = json.loads(raw)
    if data.get("encoding") != "base64":
        raise RuntimeError(f"unexpected encoding for {path}: {data.get('encoding')}")
    return base64.b64decode(data["content"])


def main() -> int:
    os.makedirs(STAGE, exist_ok=True)
    cache: dict[str, list] = {}
    failures = []
    for name, repo, prefix, scoped in TARGETS:
        if repo not in cache:
            cache[repo] = tree(repo)
        entries = cache[repo]
        if scoped:
            entries = [(p, s) for p, s in entries if p == prefix or p.startswith(prefix + "/")]
        picked = [(p, s) for p, s in entries
                  if s <= MAX_BYTES and os.path.splitext(p)[1].lower() not in SKIP_EXT]
        print(f"[{name}] {len(picked)} files from {repo}" + (f"/{prefix}" if scoped else ""))
        for p, s in picked:
            rel = p[len(prefix) + 1:] if scoped else p
            out = os.path.join(STAGE, name, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if os.path.exists(out) and os.path.getsize(out) == s:
                print(f"   skip {rel}")
                continue
            try:
                out_bytes = blob(repo, p)
                with open(out, "wb") as f:
                    f.write(out_bytes)
                print(f"   ok   {rel} ({len(out_bytes)} B)")
            except Exception as e:  # noqa: BLE001
                failures.append(f"{name}/{rel}: {e}")
                print(f"   FAIL {rel}: {e}")
    print("\n== 结果")
    for name, *_ in TARGETS:
        d = os.path.join(STAGE, name)
        skill = os.path.join(d, "SKILL.md")
        ok = os.path.exists(skill)
        size = sum(os.path.getsize(os.path.join(b, f))
                   for b, _, fs in os.walk(d) for f in fs) if os.path.isdir(d) else 0
        print(f"  {name:20} SKILL.md={'Y' if ok else 'N'}  total={size/1024:.0f} KB")
    if failures:
        print("\n失败项：")
        for f in failures:
            print("  " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
