"""逐文件覆盖率台账：sources/ 下的每一份文件，都要有个明确去向。

背景（用户硬性要求）：「我已经多次申明一定要把每一个文件做成条目」。
本脚本不切条目，只做审计——把每个文件标成下面状态之一，并统计字数去向：

  正文·成条目      .txt 且切分器至少产出 1 条条目
  正文·数据表      .txt 全部进可检索数据表（书目目录/阅读报告等，按决策不逐条切）
  正文·整篇挂上    .txt 走「整篇挂上」泳道（宣传稿/普通公告，条目数>0 但 archive_only）
  正文·空页/仅噪声  .txt 去掉站点模板后不足 8 字
  正文·名单免处理   .txt 录取名单类，按决策不处理
  二进制·已抽正文   pdf/doc/docx/xls/xlsx 有对应的 .txt
  二进制·名单免处理 没抽正文，但文件名命中名单规则（按决策不处理）
  二进制·无法解析    没抽正文，也不是名单（WPS 私有 .doc 等），必须逐个人工过目
  原始记录          API 返回的 .json（ilib-list/ilib 等），正文在同名 .txt 里
  索引/台账         sources 根目录的 *-index.json、index.json 等元数据
  派生产物          vector/ 下的 .npy/.jsonl/.md，由流水线生成，不是原始资料
  文档              根目录 .md 说明

隔离区 sources/_quarantine/ 一律不进台账，也不上传。

用法：python tools/build_coverage.py        产物 _review_items/coverage_20261104.json
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT = ROOT / "_review_items"
LIST_RX = re.compile(r"录取名单|拟录取|获奖名单|名单公示|学生名单|复试名单|拟推荐名单|名册")
BIN_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".wps", ".rar", ".zip", ".7z"}


def load(name: str, default=None):
    p = Path(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def slugify(s: str) -> str:
    """正文文件名用的归一形式：非中英数压成 -，小写，截 60。"""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", s).strip("-").lower()
    return s[:60]


def core(s: str) -> str:
    """两侧都去掉一切非中英数再比对，避开采集侧各种洗名口径差异。"""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", unicodedata.normalize("NFKC", s).lower())


def main() -> None:
    report = load(SRC.parent / "_review_items/v2_report.json", [])
    per_txt = {Path(r["file"]).name: r for r in report}
    att_idx = load(SRC / "attachments-index.json", {})
    att_txt = load(SRC / "attachments-text-index.json", {})
    wendao_idx = load(SRC / "wendao-index.json", {})
    local_idx = load(SRC / "local-index.json", {})

    # 已抽正文的键集合
    att_by_sha = {v.get("sha256", ""): v for v in att_idx.values()}
    # 用户手工转格式（.doc → .docx）的原件：转换件的字节哈希也指回同一条正文
    for v in att_idx.values():
        conv = SRC.parent / v.get("saved", "")
        if v.get("converted") and conv.is_file():
            att_by_sha.setdefault(hashlib.sha256(conv.read_bytes()).hexdigest(), v)
    have_att = {k for k, v in att_txt.items() if (SRC / "attachments" / "text" / f"{k}.txt").exists()}
    have_wendao = {p.stem for p in (SRC / "wendao-text").glob("*.txt")}
    txt_stems = {p.stem for p in SRC.rglob("*.txt")}
    # ilib 的正文文件名是「标题-id」，原始 json 是「id」——按后缀认领
    tail_keys = {s.rsplit("-", 1)[-1] for s in txt_stems}

    rows: list[dict] = []
    unclaimed_bin: list[str] = []

    for p in sorted(SRC.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(SRC).as_posix()
        if rel.startswith("_quarantine/"):
            continue
        suf = p.suffix.lower()
        entry = {"file": rel, "bytes": p.stat().st_size}

        if suf == ".txt":
            r = per_txt.get(p.name)
            if r is None:
                entry.update(status="正文·未进流水线", chars=0, items=0, rows=0)
            elif r["items"] > 0 and r["rows"] == 0:
                st = "正文·整篇挂上" if r["kind"] == "整篇挂上" else "正文·成条目"
                entry.update(status=st, chars=r["chars"], items=r["items"], rows=0)
            elif r["items"] > 0:
                entry.update(status="正文·条目+数据表", chars=r["chars"], items=r["items"], rows=r["rows"])
            elif r["rows"] > 0 or r["note"] == "数据表":
                entry.update(status="正文·数据表", chars=r["chars"], items=0, rows=r["rows"])
            else:
                entry.update(status="正文·" + (r["note"] or "空页/仅噪声"),
                             chars=r["chars"], items=0, rows=0)
            entry["kind"] = r["kind"] if r else ""
            rows.append(entry)
            continue

        if suf == ".json":
            if rel.startswith("vector/"):
                st = "派生产物"
            elif p.name.endswith("-index.json") or p.name == "index.json":
                st = "索引/台账"
            elif p.stem in txt_stems or p.stem in tail_keys:
                st = "原始记录"
            elif "/" not in rel:
                st = "索引/台账"           # sources 根目录的 json 全是采集台账，不是原文
            else:
                st = "原始记录·无正文"
            entry.update(status=st, chars=0, items=0, rows=0)
            rows.append(entry)
            continue

        if suf == ".md":
            st = "派生产物" if rel.startswith("vector/") else "文档"
            entry.update(status=st, chars=0, items=0, rows=0)
            rows.append(entry)
            continue

        if suf in BIN_EXT or suf in (".npy", ".jsonl") or rel.startswith("vector/"):
            if suf in (".npy", ".jsonl") or rel.startswith("vector/"):
                entry.update(status="派生产物", chars=0, items=0, rows=0)
                rows.append(entry)
                continue
            # --- 附件：按 sha256 找回正文 slug
            v = att_by_sha.get(hashlib.sha256(p.read_bytes()).hexdigest())
            if v:
                slug = "att-" + hashlib.sha1(v["url"].encode()).hexdigest()[:10]
                if slug in have_att:
                    entry.update(status="二进制·已抽正文", slug=slug)
                    rows.append(entry)
                    continue
                if LIST_RX.search(v.get("name", "") + v.get("page_title", "")):
                    entry.update(status="二进制·名单免处理")
                    rows.append(entry)
                    continue
                entry.update(status="二进制·无法解析", name=v.get("name", ""))
                unclaimed_bin.append(rel)
                rows.append(entry)
                continue
            # --- 问道原文：<hash>_<标题> → wendao-text/<hash>.txt
            m = re.match(r"^([0-9a-f]{6,12})_", p.stem)
            if m and m.group(1) in have_wendao:
                entry.update(status="二进制·已抽正文", slug=m.group(1))
                rows.append(entry)
                continue
            if m and m.group(1) not in have_wendao:
                if LIST_RX.search(p.name):
                    entry.update(status="二进制·名单免处理")
                else:
                    entry.update(status="二进制·无法解析")
                    unclaimed_bin.append(rel)
                rows.append(entry)
                continue
            # --- 同名 .txt（pdf/ 目录、root）
            if p.stem in txt_stems:
                entry.update(status="二进制·已抽正文", slug=p.stem)
                rows.append(entry)
                continue
            if rel == "pdf/xueji-official.pdf" and "xueji-2025" in txt_stems:
                entry.update(status="二进制·已抽正文", slug="xueji-2025")
                rows.append(entry)
                continue
            # --- 本地上传件：正文键是 loc-<洗过的文件名>-<6hex>，reference/ 里的同名副本也按这条认领
            cstem = core(p.stem)
            hit_name = any(core(Path(k).stem) == cstem for k in
                           {v.get("file", "") for v in local_idx.values()} if k)
            loc_cores = {core(t) for t in txt_stems if t.startswith("loc-")}
            hit_txt = bool(cstem) and any(cstem in lc for lc in loc_cores)
            if hit_name or hit_txt:
                entry.update(status="二进制·已抽正文", via="local")
                rows.append(entry)
                continue
            if LIST_RX.search(p.name):
                entry.update(status="二进制·名单免处理")
                rows.append(entry)
                continue
            entry.update(status="二进制·无法解析")
            unclaimed_bin.append(rel)
            rows.append(entry)
            continue

        entry.update(status="其他格式")
        rows.append(entry)

    from collections import Counter
    c = Counter(e["status"] for e in rows)
    txt_items = sum(e.get("items", 0) for e in rows)
    print(f"台账 {len(rows)} 个文件")
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print(f"  {k:<18} {v}")
    print(f"流水线认领条目合计 {txt_items}")
    print(f"\n无法解析的二进制 {len(unclaimed_bin)} 个（必须逐个人工过目）：")
    for u in unclaimed_bin:
        print("   ✗", u)
    bad = [e["file"] for e in rows if e["status"] in ("正文·未进流水线", "其他格式", "原始记录·无正文")]
    print(f"\n异常（未进流水线/无正文的原始记录/其他）{len(bad)} 个：")
    for b in bad[:20]:
        print("   !", b)
    OUT.mkdir(exist_ok=True)
    (OUT / "coverage_20261104.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    print(f"\n已写 {OUT/'coverage_20261104.json'}")


if __name__ == "__main__":
    main()
