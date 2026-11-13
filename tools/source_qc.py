"""文件审阅的机械项质检（只读）：给人工审阅一份「先看哪里」的清单。

它查的是「文件层」：抽取质量、索引一致性、能否被引用。
它**不判断**内容对不对、标题起得好不好——那是人读原文的事。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/source_qc.py --prefix xt-tuimian-2027
  ./.venv/Scripts/python.exe -X utf8 -u tools/source_qc.py --prefix cz-
  ./.venv/Scripts/python.exe -X utf8 -u tools/source_qc.py --all-index      # index.json 全部
  ./.venv/Scripts/python.exe -X utf8 -u tools/source_qc.py --prefix hb921 --json out.json

退出码：0 无阻断项；1 有阻断项（乱码/空正文/索引缺失/无条目引用）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def find_text(slug: str) -> Path | None:
    for p in (SRC / f"{slug}.txt",):
        if p.exists():
            return p
    for d in ("pdf", "huibian", "wendao-text", "wechat", "crawl", "cdp", "local",
              "attachments/text", "ilib-text", "ilib-list-text", "wendao-extra", "chsi", "moe", "national", "extra"):
        p = SRC / d / f"{slug}.txt"
        if p.exists():
            return p
    return None


def quotes_of(items: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for it in items:
        for ev in (it.get("evidence") or {}).values():
            if not isinstance(ev, dict):
                continue
            pairs = ev.get("sources") or [ev]
            for s in pairs:
                src, q = str(s.get("src") or ""), str(s.get("quote") or "")
                if src and q:
                    out.setdefault(src, []).append(q)
    return out


def main() -> None:
    argv = sys.argv[1:]
    prefix = argv[argv.index("--prefix") + 1] if "--prefix" in argv else ""
    all_index = "--all-index" in argv or not prefix
    json_out = argv[argv.index("--json") + 1] if "--json" in argv else ""

    index = load(SRC / "index.json")
    corpus = load(SRC / "corpus-index.json")
    items = load(ROOT / "items.json")["items"]
    cites = quotes_of(items)
    # 条目 source[].slug 也算「被引用」
    srcs_of_items: dict[str, set[str]] = {}
    for it in items:
        for s in it.get("source") or []:
            if isinstance(s, dict) and s.get("slug"):
                srcs_of_items.setdefault(str(s["slug"]), set()).add(it["id"])

    files = [k for k in (list(index) + [k for k in corpus if k not in index])
             if (prefix and k.startswith(prefix)) or (all_index and k in index)]
    files = sorted(set(files))

    rows, blocking = [], 0
    print(f"待审文件 {len(files)} 份（前缀 {prefix or 'index 全部'}）\n")
    for slug in files:
        p = find_text(slug)
        rec: dict = {"slug": slug, "text": str(p) if p else "", "flags": [], "blocking": False}
        if not p:
            rec["flags"].append("无正文 .txt")
            rec["blocking"] = True
        else:
            t = p.read_text(encoding="utf-8", errors="ignore")
            cjk = len(re.findall(r"[\u4e00-\u9fff]", t))
            rec.update(chars=len(t), cjk=cjk, cjk_ratio=round(cjk / max(1, len(t)), 3),
                       ctrl=len(CTRL.findall(t)), repl=t.count("\ufffd"),
                       pages_marked=len(re.findall(r"—\s*p\.\d+\s*—", t)))
            if len(t) < 200:
                rec["flags"].append("正文过短")
            if rec["cjk_ratio"] < 0.3:
                rec["flags"].append("中文占比低（可能抽取失败）")
            if rec["repl"] > 5:
                rec["flags"].append(f"乱码字符 {rec['repl']} 个")
                rec["blocking"] = True
            if rec["ctrl"] > 5:
                rec["flags"].append(f"控制字符 {rec['ctrl']} 个")
        rec["in_index"] = slug in index
        rec["in_corpus"] = slug in corpus
        if not rec["in_index"]:
            rec["flags"].append("未登记 index.json")
        if not rec["in_corpus"]:
            rec["flags"].append("未登记 corpus-index.json")
        ids = set(srcs_of_items.get(slug, set())) | {it["id"] for it in items if slug in {
            str(s.get("slug")) for s in (it.get("source") or []) if isinstance(s, dict)}}
        rec["cited_by"] = len(ids)
        if not ids:
            rec["flags"].append("无任何条目引用")
            rec["blocking"] = True
        qs = cites.get(slug, [])
        if p and qs:
            flat = re.sub(r"\s+", "", p.read_text(encoding="utf-8", errors="ignore"))
            hit = sum(1 for q in qs if re.sub(r"\s+", "", q) in flat)
            rec["quote_total"] = len(qs)
            rec["quote_hit"] = hit
            if hit < len(qs):
                rec["flags"].append(f"引文未命中 {len(qs) - hit}/{len(qs)}")
        rows.append(rec)
        if rec["blocking"]:
            blocking += 1
        mark = "❌" if rec["blocking"] else ("⚠️" if rec["flags"] else "✅")
        extra = f" chars={rec.get('chars', 0)} cjk={rec.get('cjk_ratio', 0)} 被引={rec['cited_by']}"
        if qs:
            extra += f" 引文 {rec.get('quote_hit', 0)}/{rec.get('quote_total', 0)}"
        print(f"  {mark} {slug:44}{extra}")
        for f in rec["flags"]:
            print(f"       · {f}")

    if json_out:
        Path(json_out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n明细写入 {json_out}")
    print(f"\n合计 {len(rows)} 份，阻断项 {blocking} 份")
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
