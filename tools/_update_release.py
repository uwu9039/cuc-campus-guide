"""把 v1.0.0 tag 指到最新 main，并用 RELEASE_v1.0.md 覆盖 GitHub release 正文。"""
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
    st, r = R.call("PATCH", f"{R.API}/repos/{R.OWNER}/{R.REPO}/git/refs/tags/v1.0.0", tok,
                   {"sha": sha, "force": True})
    print("tag ->", st, str((r or {}).get("object", {}).get("sha", ""))[:8])

    body = (ROOT / "RELEASE_v1.0.md").read_text(encoding="utf-8")
    st, rels = R.call("GET", f"{R.API}/repos/{R.OWNER}/{R.REPO}/releases", tok)
    rel = next((x for x in rels if x.get("tag_name") == "v1.0.0"), None) if isinstance(rels, list) else None
    if not rel:
        print("release v1.0.0 不存在，跳过正文更新")
        return
    st, got = R.call("PATCH", f"{R.API}/repos/{R.OWNER}/{R.REPO}/releases/{rel['id']}", tok,
                     {"body": body})
    print("release body ->", st, (got or {}).get("html_url", ""))


if __name__ == "__main__":
    main()
