"""给 sources/ 里每份文档建一条台账：被哪个条目用、是否重复、是否只作背景。

输出 sources/doc-registry.json。
"""
import glob
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
NEWS = re.compile(r"喜报|举行|召开|斩获|风采|纪实|致辞|报道|讲座|论坛|活动|盘点|招生简章|论文名单|成绩盘点|连冠|获证|合格证|夏令营|毕业典礼")
RULE = re.compile(r"办法|规定|细则|制度|准则|方案|规程|规范|章程|指引|指南|须知|流程|通知|协议|责任书|标准")
LIST_TITLES = {"通知公告", "管理规定", "政策文件", "新闻动态"}
STALE = re.compile(r"202[0-3]年|2024年国庆|2021年")


def squash(s):
    return re.sub(r"\s+", "", s or "")


def core_title(t):
    t = re.sub(r"\s+", "", t or "")
    t = re.sub(r"[（(][^）)]*[）)]$", "", t)
    t = re.sub(r"^(关于印发|关于|印发)", "", t)
    t = re.sub(r"《|》|_|\.docx?$|\.pdf$", "", t)
    return t


def main():
    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    used = {}
    for it in items:
        def walk(e):
            if isinstance(e, dict):
                s = e.get("src")
                if s:
                    used.setdefault(str(s), set()).add(it["id"])
                for v in e.values():
                    walk(v)
            elif isinstance(e, list):
                for v in e:
                    walk(v)
        walk(it.get("evidence"))

    by_title = {}
    for it in items:
        by_title.setdefault(core_title(it["title"]), it["id"])

    OVERRIDES = {
        "7684e018": ("background", "2024 年国庆假期通知，已过期，仅存档"),
        "60635f11": ("background", "只有三个系统链接，无办事说明"),
        "260444efa3": ("background", "本科生院导航页，正文为政策文件列表"),
        "4aa21faedd": ("background", "本科生院导航页，正文为政策文件列表"),
        "20240821-c2092a242385": ("background", "页面只有导航，正文未抓到"),
        "2024-10-23-70f68d84": ("background", "2024 年秋季学期课程介绍，仅存档"),
        "20251111-c2761a262337": ("background", "正文只有附件 PDF 链接，无文字条款"),
        "20260915-c6364a273904": ("background", "正文只有附件 PDF 链接，无文字条款"),
        "20260915-c6364a273900": ("background", "正文只有附件压缩包链接，无文字条款"),
        "20260915-c6467a273900": ("background", "正文只有附件压缩包链接，无文字条款"),
        "20201021-c2812a174217": ("background", "教职工财务专项流程，与学生问答无关"),
        "20250605-c14744a256560": ("background", "新闻/学习活动报道"),
        "loc-中国传媒大学2025年军训一日生活制度表-1-3a671e": ("background", "扫描件 OCR 竖排错位，无法逐句引用"),
    }

    docs = []
    for p in sorted(glob.glob(str(SRC / "*-index.json"))) + [str(SRC / "index.json")]:
        col = os.path.basename(p).replace("-index.json", "").replace(".json", "")
        if col == "index":
            col = "corpus"
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            title = v.get("title") or ""
            row = {
                "key": k,
                "collection": col,
                "title": title,
                "url": v.get("url") or "",
                "chars": v.get("chars") or 0,
                "used_by": sorted(used.get(k, [])),
                "status": "used" if used.get(k) else "",
            }
            docs.append(row)

    used_urls = {}
    for d in docs:
        if d["used_by"] and d.get("url"):
            used_urls.setdefault(d["url"], []).append(d["used_by"][0])

    available_stems = set()
    for p in SRC.rglob("*.txt"):
        if "_quarantine" in p.parts:
            continue
        available_stems.add(p.stem)

    for row in docs:
        if row["status"]:
            continue
        if row["key"] not in available_stems:
            row["status"] = "background"
            row["reason"] = "正文文件未落盘或已隔离，按约定不使用"
            continue
        if row.get("url") and row["url"] in used_urls:
            row["status"] = "duplicate"
            row["duplicate_of"] = used_urls[row["url"]]
            row["reason"] = "同一页面已有条目录入"
            continue
        ov = OVERRIDES.get(row["key"])
        if ov:
            row["status"], row["reason"] = ov
            continue
        title = row["title"]
        ct = core_title(title)
        dup = by_title.get(ct)
        if not dup:
            for t2, iid in by_title.items():
                if len(ct) >= 8 and (ct in t2 or t2 in ct):
                    dup = iid
                    break
        if dup:
            row["status"] = "duplicate"
            row["duplicate_of"] = dup
            row["reason"] = "与已有条目同题"
            continue
        if title in LIST_TITLES:
            row["status"] = "background"
            row["reason"] = "列表页，只有标题和链接"
        elif NEWS.search(title):
            row["status"] = "background"
            row["reason"] = "新闻/活动报道"
        elif row["chars"] < 600:
            row["status"] = "background"
            row["reason"] = "正文过短（多为附件链接或导航）"
        elif STALE.search(title):
            row["status"] = "background"
            row["reason"] = "过期通知，仅存档"
        elif RULE.search(title):
            row["status"] = "uncovered"
        else:
            row["status"] = "background"
            row["reason"] = "非办事依据（公示/资料/报道类）"

    counts = {}
    for d in docs:
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    out = {
        "updated": "2026-10-29",
        "counts": counts,
        "docs": docs,
    }
    (SRC / "doc-registry.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("文档台账", len(docs), counts)
    for d in docs:
        if d["status"] == "uncovered":
            print(" 未覆盖:", d["collection"], d["key"], d["chars"], d["title"][:60])


if __name__ == "__main__":
    main()
