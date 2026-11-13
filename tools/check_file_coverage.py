"""文件-条目对账：每一份入库文件，都必须至少被一条条目引用（准备好被引用）。

规则（用户 2026-11-11 定）：新入库的文件，每一份都要做成条目；
条目的 evidence.src 或 source[].slug 指到该文件，才算「可被引用」。
没被任何条目引用的文件 = 埋雷：语料里有、问答用不到。

用法：
  # 看某批文件（按 slug 前缀）
  ./.venv/Scripts/python.exe -X utf8 -u tools/check_file_coverage.py --prefix xt-tuimian-2027
  # 看 index.json 里的全部文件
  ./.venv/Scripts/python.exe -X utf8 -u tools/check_file_coverage.py --all-index
  # 反向：条目引用了不存在的文件
  ./.venv/Scripts/python.exe -X utf8 -u tools/check_file_coverage.py --prefix cz- --reverse

退出码：0 全部被引用；1 有文件无人引用（或反向有断链）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def src_of(ev: dict) -> list[str]:
    if not isinstance(ev, dict):
        return []
    if ev.get("sources"):
        return [str(s.get("src")) for s in ev["sources"] if s.get("src")]
    return [str(ev["src"])] if ev.get("src") else []


def main() -> None:
    args = sys.argv[1:]
    prefix = ""
    if "--prefix" in args:
        prefix = args[args.index("--prefix") + 1]
    only_index = "--all-index" in args or not prefix
    reverse = "--reverse" in args

    items = load(ROOT / "items.json")["items"]
    index = load(SRC / "index.json")
    corpus = load(SRC / "corpus-index.json")

    # 文件 → 引用它的条目
    cites: dict[str, set[str]] = {}
    for it in items:
        refs = set()
        for ev in (it.get("evidence") or {}).values():
            refs.update(src_of(ev))
        for s in it.get("source") or []:
            if isinstance(s, dict) and s.get("slug"):
                refs.add(str(s["slug"]))
        for r in refs:
            cites.setdefault(r, set()).add(it["id"])

    # 待检文件清单
    files = [k for k in index if not prefix or k.startswith(prefix)]
    if not only_index or prefix:
        extra = [k for k in corpus if k.startswith(prefix) and k not in index]
        files += extra
    files = sorted(set(files))

    print(f"待检文件 {len(files)} 份（前缀 {prefix or '—'}）\n")
    # 例外登记：确实不该被条目引用的文件（版权页/空白件/重复件），必须先写明理由
    exempt_p = ROOT / "_review_items" / "toc" / "_no_item_files.json"
    exempt: dict[str, str] = {}
    if exempt_p.exists():
        try:
            for x in (load(exempt_p).get("files") or []):
                if x.get("key"):
                    exempt[str(x["key"])] = str(x.get("reason") or "")
        except Exception as e:  # noqa: BLE001
            print(f"（_no_item_files.json 读不了：{e}）")
    missing: list[str] = []
    for k in files:
        n = len(cites.get(k, ()))
        if n == 0 and k in exempt:
            print(f"  ⚪ {k:44} 例外：{exempt[k][:40]}")
            continue
        flag = "✅" if n else "❌"
        if n == 0:
            missing.append(k)
        print(f"  {flag} {k:44} 被 {n} 条条目引用")

    # 反向：条目引用的 src 是否真实存在（index/corpus/同名 txt）
    if reverse:
        exist = set(index) | set(corpus)
        for d in ("", "pdf", "huibian", "wendao-text", "attachments/text"):
            p = SRC / d
            if p.is_dir():
                exist |= {x.stem for x in p.glob("*.txt")}
        broken = [(k, sorted(v)) for k, v in cites.items() if k not in exist]
        print(f"\n反向检查：{len(broken)} 个 src 找不到对应文件")
        for k, ids in broken[:10]:
            print(f"  ❌ {k} ← {ids[:3]}")

    if missing:
        print(f"\n❌ {len(missing)} 份文件没有任何条目引用（按规则不合格）：")
        for k in missing[:20]:
            print("   -", k)
        sys.exit(1)
    print("\n✅ 全部文件都至少被一条条目引用")


if __name__ == "__main__":
    main()
