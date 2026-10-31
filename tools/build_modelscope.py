"""组装魔搭创空间上传目录：只带运行时需要的文件，排除凭证与个人信息。

用法：
    .venv\\Scripts\\python.exe tools\\build_modelscope.py
    .venv\\Scripts\\python.exe tools\\build_modelscope.py --no-vector   # 不带 74MB 向量索引

产物在 _modelscope_bundle/，把这个目录里的内容推到创空间仓库根目录即可。
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_modelscope_bundle"

ROOT_FILES = [
    "app.py", "vector_index.py", "requirements.txt",
    "items.json.gz", "presets.json", "topic-menus.json", "contacts.json",
    "departments.json", "transfer-plans.json", "campus-map.json",
    "major-aliases.json", "sensitive.json",
]

SOURCE_FILES = [
    "index.json", "crawl-index.json", "cdp-index.json", "wechat-index.json",
    "chsi-index.json", "moe-index.json", "national-index.json", "extra-index.json",
    "huibian-index.json", "wendao-index.json", "wendao-extra-index.json",
    "local-index.json", "corpus-index.json", "campus-pois.json",
]

WEB_SKIP = {"campus-guide-personal-data.zip", "serve.py"}
FORBIDDEN = (".env", "download.devtools", "aia-api.json", ".zip", ".git", "_quarantine", ".qoder")


def plan_pdfs() -> list[Path]:
    data = json.loads((ROOT / "transfer-plans.json").read_text(encoding="utf-8"))
    names = {Path(v["file"]).name for v in data.values()
             if isinstance(v, dict) and v.get("file")}
    folder = ROOT / "sources" / "local" / "_files"
    missing = [n for n in names if not (folder / n).exists()]
    if missing:
        raise SystemExit(f"转专业计划 PDF 缺失：{missing}")
    return [folder / n for n in sorted(names)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-vector", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    copied: list[Path] = []

    def put(src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)

    for name in ROOT_FILES:
        src = ROOT / name
        if not src.exists():
            raise SystemExit(f"缺少 {name}（先跑发布前检查）")
        put(src, out / name)

    for name in SOURCE_FILES:
        src = ROOT / "sources" / name
        if not src.exists():
            raise SystemExit(f"缺少 sources/{name}")
        put(src, out / "sources" / name)

    put(ROOT / "sources" / "wendao-text" / "1b97d899.txt",
        out / "sources" / "wendao-text" / "1b97d899.txt")

    for pdf in plan_pdfs():
        put(pdf, out / "sources" / "local" / "_files" / pdf.name)

    for src in sorted((ROOT / "web-next").rglob("*")):
        if not src.is_file() or src.name in WEB_SKIP:
            continue
        put(src, out / "web-next" / src.relative_to(ROOT / "web-next"))

    put(ROOT / "deploy" / "modelscope" / "Dockerfile", out / "Dockerfile")
    put(ROOT / "deploy" / "modelscope" / "README.md", out / "README.md")

    if not args.no_vector:
        for name in ("manifest.json", "idf.npy", "vectors.npy", "chunks.jsonl"):
            put(ROOT / "sources" / "vector" / name, out / "sources" / "vector" / name)

    bad = [str(p.relative_to(out)) for p in out.rglob("*")
           if p.is_file() and any(tag in p.name or tag in p.as_posix() for tag in FORBIDDEN)]
    if bad:
        raise SystemExit(f"产物里混进了不该发布的文件：{bad}")

    total = sum(p.stat().st_size for p in copied)
    print(f"魔搭上传目录：{out}")
    print(f"文件 {len(copied)} 个，共 {total / 1048576:.1f} MB")
    for p in sorted(copied, key=lambda x: -x.stat().st_size)[:8]:
        print(f"  {p.stat().st_size / 1048576:6.1f} MB  {p.relative_to(out)}")


if __name__ == "__main__":
    main()
