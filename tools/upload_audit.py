"""上传前隐私审计：只检查要上传的文件，逐个模式扫，命中就列出来。

用法：
    python tools/upload_audit.py            # 只报告
    python tools/upload_audit.py --strict   # 有任何命中就退出码 1（用于卡住发布）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".venv", "__pycache__", "dist", ".git", "piptest", "node_modules"}
SKIP_SUFFIX = {".zip", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".wav", ".mp4", ".docx", ".xlsx"}
SKIP_FILES = {
    ".env", "urls.txt", "items.json.bak", "live.png", "presets.png",
    "upload.log", "upload_sources.log", "upload_loop.log", "upload_loop2.log",
    "render.log", "audit_llm.log", "audit_llm2.log",
}

SECRET = [
    ("API Key", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("GitHub Token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("Bearer", re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}")),
    ("密码/口令赋值", re.compile(r"(password|passwd|secret)\s*[=:]\s*['\"][^'\"]{6,}")),
]
PII = [
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("邮箱", re.compile(r"(?<![＊*])[A-Za-z0-9._%+-]+@(?!cuc\.edu\.cn)[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("本机路径", re.compile(r"[A-Za-z]:\\\\?Users\\\\?[A-Za-z0-9_\-]+")),
    ("本地盘符路径", re.compile(r"[A-Za-z]:\\\\?DSH[\\\\/]")),
    ("个人目录名", re.compile(r"[A-Za-z]:\\\\?[^\\\\]{0,12}(的小窝|聊天)")),
    ("技能目录", re.compile(r"\.dsh[\\\\/]skills")),
    ("学生姓名+学号", re.compile(r"(学号|姓名)[:：]\s*(?![＊*xX])[一-鿿]{2,4}")),
]
ALLOW = [
    re.compile(r"6578\d{4}|6577\d{4}|65783000|010-67410388"),   # 学校/学信网公开电话
    re.compile(r"@cuc\.edu\.cn$|@chsi\.com\.cn$|@moe\.gov\.cn$"),
    re.compile(r"cuc_zntj@163\.com"),                            # 赛事公开邮箱
]


def wanted(p: Path) -> bool:
    if p.is_dir() or p.name in SKIP_FILES or p.name.startswith("_"):
        return False
    if set(p.parts) & SKIP_DIRS:
        return False
    if p.suffix.lower() in SKIP_SUFFIX:
        return False
    return True


def main() -> None:
    strict = "--strict" in sys.argv
    files = [p for p in ROOT.rglob("*") if wanted(p)]
    total = sum(p.stat().st_size for p in files)

    hits: list[tuple[str, str, str]] = []
    for p in files:
        if p.suffix.lower() not in {".py", ".json", ".md", ".html", ".txt", ".mjs", ".ts",
                                    ".tsx", ".js", ".css", ".cfg", ".toml", ".yml", ".yaml"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        for name, rx in SECRET + PII:
            for m in rx.finditer(text):
                if any(a.search(m.group(0)) for a in ALLOW):
                    continue
                line = text[:m.start()].count("\n") + 1
                hits.append((str(p.relative_to(ROOT)), name, f"L{line} {m.group(0)[:40]}"))

    print(f"清单：{len(files)} 个文件，{total/1024/1024:.2f} MB")
    print(f"命中：{len(hits)} 处")
    for f, n, d in hits:
        print(f"  [{n}] {f}  {d}")

    if strict and hits:
        print("\n✗ 有命中，停止发布")
        sys.exit(1)
    print("\n✓ 可发布" if not hits else "\n⚠ 请逐条确认")


if __name__ == "__main__":
    main()
