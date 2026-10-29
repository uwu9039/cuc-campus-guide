"""上传前隐私扫描：找出仓库里可能泄露个人信息的片段。

检查项：
  - API Key / token（sk-…、ghp_…）
  - 中国大陆手机号、邮箱地址
  - 本机用户名与本地路径（（本地路径已隐藏）
  - 个人目录名

用法：python tools/privacy_scan.py [--fix]
  --fix 会把命中的本地路径替换成占位符（只改文本文件，不动二进制）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".venv", "__pycache__", "dist", ".git", "piptest", "node_modules",
             "sources", "aia-runs", "video-remotion"}
TEXT_EXT = {".py", ".json", ".md", ".html", ".txt", ".bat", ".js", ".css", ".cfg", ".toml", ".yml", ".yaml"}
BIN_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".docx", ".xlsx"}

RULES = [
    ("API Key", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("GitHub Token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("邮箱", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("本机用户路径", re.compile(r"[A-Za-z]:[\\\\/]+Users[\\\\/]+admin", re.I)),
    ("本地项目路径", re.compile(r"[A-Za-z]:[\\\\/]+DSH[\\\\/]")),
    ("file:// 本地引用", re.compile(r"file:///[A-Za-z]:/")),
]

# 允许保留的官方号码/邮箱（学校公开联系方式）
ALLOW = [
    re.compile(r"6578\d{4}"),                 # 学校 6578xxxx 总机段
    re.compile(r"6577\d{4}"),
    re.compile(r"139\*{4}2873|156\*{4}0801|186\*{4}7999|65783000"),
    re.compile(r"jiaowuchu@cuc\.edu\.cn|cuc_zntj@163\.com"),
    re.compile(r"@cuc\.edu\.cn$"),
]


def allowed(text: str, m: re.Match) -> bool:
    return any(p.search(m.group(0)) for p in ALLOW)


def main() -> None:
    fix = "--fix" in sys.argv
    hits: list[tuple[str, str, str]] = []
    changed = 0

    for p in ROOT.rglob("*"):
        if p.is_dir() or p.suffix.lower() in BIN_EXT:
            continue
        if set(p.parts) & SKIP_DIRS:
            continue
        if p.name == ".env":
            hits.append((str(p.relative_to(ROOT)), "存在的 .env 文件", "整个文件不入库"))
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue

        for name, rx in RULES:
            for m in rx.finditer(text):
                if allowed(text, m):
                    continue
                line = text[:m.start()].count("\n") + 1
                hits.append((str(p.relative_to(ROOT)), name, f"第 {line} 行：{m.group(0)[:48]}"))

        if fix:
            new = text
            new = re.sub(r"file:///[A-Za-z]:/[^\"'\s]*", "（本地文件，未入库）", new)
            new = re.sub(r"[A-Za-z]:[\\/]+DSH[\\/][^\"'\s]*", "（本地路径已隐藏）", new)
            new = re.sub(r"[A-Za-z]:[\\/]+Users[\\/]+admin[^\"'\s]*", "（本地路径已隐藏）", new)
            if new != text:
                p.write_text(new, encoding="utf-8")
                changed += 1

    print(f"扫描完成：{len(hits)} 处命中")
    by_file: dict[str, list] = {}
    for f, n, d in hits:
        by_file.setdefault(f, []).append((n, d))
    for f, rows in sorted(by_file.items(), key=lambda kv: -len(kv[1]))[:25]:
        print(f"\n  {f}  ({len(rows)} 处)")
        for n, d in rows[:4]:
            print(f"    - [{n}] {d}")

    if fix:
        print(f"\n已改写 {changed} 个文本文件里的本地路径")


if __name__ == "__main__":
    main()
