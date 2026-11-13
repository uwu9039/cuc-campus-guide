"""核对 GitHub main 与本地的关键文件是否一致。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("rp", str(ROOT / "tools" / "_release.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def main() -> None:
    tok = R.token()
    st, ref = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/ref/heads/main", tok)
    sha = ref["object"]["sha"]
    st, c = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/commits/{sha}", tok)
    print("HEAD", sha[:8], "|", str(c.get("message", "")).splitlines()[0])
    st, t = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/trees/{c['tree']['sha']}?recursive=1", tok)
    remote = {x["path"]: x["sha"] for x in t["tree"] if x["type"] == "blob"}
    print("files", len(remote))
    keys = ["app.py", "VERSION", "CHANGELOG.md", "web-next/field.js",
            "tools/_score_golden.py", "24-金标准12题题库-20261113.md",
            "items.json.gz", "sources-archive.tar.gz", "sections_index.py"]
    for p in keys:
        f = ROOT / p
        loc = R.blob_sha(f) if f.exists() else "-"
        print(f"  {p:36}", "OK" if remote.get(p) == loc else f"MISMATCH remote={str(remote.get(p))[:8]}")


if __name__ == "__main__":
    main()
