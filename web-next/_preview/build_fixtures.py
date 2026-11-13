"""一次性抽取：挑一组有代表性的真实条目，供前端预览服务使用。

只读仓库根目录的 items.json / contacts.json / presets.json / campus-map.json，
不改动它们；产出全部写在本目录的 fixtures/ 下，供 mock_server.py 启动时加载。

用法（仓库根目录）：
    .venv\\Scripts\\python.exe web-next\\_preview\\build_fixtures.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE.parent                 # web-next/
ROOT = WEB.parent                 # 仓库根
FIX = HERE / "fixtures"

# 一条条目的「信息量」：字段越多、数组越长，越适合当设计样张
RICH_FIELDS = ("location", "hours", "window", "fee", "duration", "answer", "note", "summary", "draft")
RICH_LISTS = ("materials", "steps", "pitfalls", "channel", "experience", "advisory", "require")


def richness(it: dict) -> int:
    n = 0
    for k in RICH_LISTS:
        n += len(it.get(k) or [])
    for k in RICH_FIELDS:
        if it.get(k):
            n += 2
    src = it.get("source")
    n += len(src) if isinstance(src, list) else (1 if src else 0)
    n += 2 * (len(it.get("qr") or []) + len(it.get("pdf") or []))
    return n


def slim(it: dict) -> dict:
    """去掉对界面无用的重字段，长文本截断，避免 fixtures 过大。"""
    out = {k: v for k, v in it.items() if k not in ("exclude", "exclude_exact")}
    if isinstance(out.get("evidence"), dict) and len(out["evidence"]) > 40:
        keep = list(out["evidence"].items())[:40]
        out["evidence"] = dict(keep)

    def cut(v):
        if isinstance(v, str):
            return v if len(v) <= 900 else v[:900] + "…"
        if isinstance(v, list):
            return [cut(x) for x in v]
        if isinstance(v, dict):
            return {k: cut(x) for k, x in v.items()}
        return v

    return {k: cut(v) for k, v in out.items()}


def main() -> None:
    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    all_items: list[dict] = data["items"]

    picked: dict[str, dict] = {}

    def take(items, cap):
        n = 0
        for it in items:
            if n >= cap:
                break
            if it["id"] in picked:
                continue
            picked[it["id"]] = it
            n += 1

    # 1) 每种特殊结构都要有：反问槽、二维码、附件、经验帖、建议
    take([i for i in all_items if i.get("slots")], 22)
    take([i for i in all_items if i.get("qr")], 12)
    take([i for i in all_items if i.get("pdf")], 12)
    take([i for i in all_items if i.get("experience") or i.get("advisory")], 6)
    take([i for i in all_items if i.get("draft")], 2)
    # 2) 信息量最大的一批：正常答案卡长什么样
    take(sorted(all_items, key=richness, reverse=True), 26)
    # 3) 状态样本：verified / source-thin / partial 三种标签
    take([i for i in all_items if i.get("status") == "source-thin"], 4)
    take([i for i in all_items if i.get("status") == "partial"], 3)
    # 4) 极端标题：超长标题、单词标题 —— 微调排版时最容易被压坏的两类
    take(sorted(all_items, key=lambda i: len(i.get("title") or ""), reverse=True), 3)
    take(sorted(all_items, key=lambda i: len(i.get("title") or "")), 4)
    # 5) 没有 steps/materials 的「薄条目」：答案卡只剩一两段时的样子
    take([i for i in all_items if not i.get("steps") and not i.get("materials")], 4)

    items = [slim(i) for i in picked.values()]
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / "items.json").write_text(
        json.dumps({"version": data.get("version"), "updated": data.get("updated"), "items": items},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    for src, dst in (("contacts.json", "contacts.json"),
                     ("presets.json", "presets.json"),
                     ("campus-map.json", "campus.json")):
        shutil.copyfile(ROOT / src, FIX / dst)

    meta = {
        "total_items": len(all_items),
        "verified": sum(1 for i in all_items if i.get("status") == "verified"),
        "source_thin": sum(1 for i in all_items if i.get("status") == "source-thin"),
        "partial": sum(1 for i in all_items if i.get("status") == "partial"),
        "facts": sum(len(i.get("evidence") or {}) for i in all_items),
        "data_version": data.get("version"),
        "data_updated": data.get("updated"),
        "fixture_items": len(items),
    }
    # 顶栏那行统计（事项 / 已核验 / 原文份数）要跟真库对得上，否则预览里数字是 0
    corpus = ROOT / "sources" / "corpus-index.json"
    if corpus.exists():
        try:
            meta["sources"] = len(json.loads(corpus.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    manifest = ROOT / "sources" / "vector" / "manifest.json"
    if manifest.exists():
        try:
            mf = json.loads(manifest.read_text(encoding="utf-8"))
            meta["vector_sources"] = mf.get("sources", 0)
            meta["vector_chunks"] = mf.get("chunks", 0)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    (FIX / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"fixtures: {len(items)} 条样本 / 全库 {len(all_items)} 条 → {FIX}")
    for it in items[:6]:
        print("  -", it["id"], "|", (it.get("title") or "")[:38])


if __name__ == "__main__":
    main()
