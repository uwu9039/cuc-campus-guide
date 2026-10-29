"""把 16 个学院的转专业接收计划按 PDF 表格逐格抽成结构化数据。

每个专业、每个年级、每一列（条件/材料/考核/联系方式/备注）都保留完整原文；
不再只取第一个专业，也不截断条数。前端可按专业折叠，PDF 始终可下载。
用法：python tools/build_transfer_plans.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "local"
OUT = ROOT / "transfer-plans.json"

KEYS = ("conditions", "materials", "exam", "contacts", "note")
DEFAULT_COLS = {"name": 0, "grade": 1, "conditions": 2, "materials": 3,
                "exam": 4, "contacts": 5, "note": 6}

ALIASES = {
    "新闻学院": ["新闻"],
    "电视学院": ["电视"],
    "戏剧影视学院": ["戏影", "戏影学院"],
    "播音主持艺术学院": ["播院", "播音学院", "播音"],
    "动画与数字艺术学院": ["动院", "动画学院"],
    "音乐与录音艺术学院": ["音录", "音录学院"],
    "信息与通信工程学院": ["信通", "信通学院"],
    "计算机与网络空间安全学院": ["计网", "计网院", "网安学院", "计算机学院"],
    "数据科学与智能媒体学院": ["数智", "数智学院", "数据学院"],
    "人文学院": ["人文"],
    "外国语言文化学院": ["外院", "外语学院", "国际传播学院"],
    "经济与管理学院": ["经管", "经管学院"],
    "政府与公共事务学院": ["政院", "政府学院"],
    "广告与品牌学院": ["广告学院"],
    "文化产业管理学院": ["文产", "文产学院"],
    "信息传播学院": ["信传", "信传学院"],
}

CONTACT = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+"
    r"|(?<!\d)(?:0\d{2,3}-?\d{7,8}|1[3-9]\d{9}|\d{8})(?!\d)"
)
CONTACT_LINE = re.compile(r"联系人[：:](.+?)(?=电话[：:]|邮箱[：:]|手机[：:]|$)")
KEEP_PUNCT = " 　。；：:、\t"

SPLIT = re.compile(
    r"(?=(?<![\dA-Za-z（(])[0-9]{1,2}[.、)）](?![\d]))"
    r"|(?=（[0-9一二三四五六七八九十]{1,3}）)"
    r"|(?=（[a-zA-Z]{1,2}）)"
    r"|(?=[a-dA-D][.、](?=[\u4e00-\u9fa5]))"
    r"|(?=(?:Ⅰ|Ⅱ)[.、]?\s*专业)"
    r"|(?=(?:注|备注)[：:])"
    r"|(?=[*•])"
)


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def cell_text(v: Any) -> str:
    if v is None:
        return ""
    lines = [ln.strip() for ln in str(v).splitlines()]
    return "\n".join(ln for ln in lines if ln)


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[（(]\s*至\s*\d{4}\s*[)）]", "", s)
    s = re.sub(r"[\s　]+", "", s)
    return s.replace("专业", "")


def merge_lines(lines: list[str], limit: int = 2000) -> list[str]:
    """PDF 单元格里一句话常被列宽折行，把片段拼回完整句子。"""
    out, buf = [], ""
    for s in lines:
        # 时间折行后直接粘编号会变成「17:302.」，这里先断句
        if buf and re.search(r"\d{1,2}:\d{2}(?:-\d{1,2}:\d{2})?$", buf) \
                and re.match(r"\d{1,2}[.、)）]", s):
            out.append(buf)
            buf = s
            continue
        # 邮箱/网址折行后常直接粘上下一条编号，先断句再拼
        if buf and re.search(r"\.(?:cn|com|net|org|edu|gov)$", buf, re.I) \
                and re.match(r"[0-9]{1,2}[.、)）]", s):
            out.append(buf)
            buf = s
            continue
        # 「注意事项：」这类独立小标题，不能粘在上一条末尾
        if buf and re.fullmatch(r"(?:注意事项|注|备注|说明)[：:]", s):
            out.append(buf)
            buf = s
            continue
        buf = f"{buf}{s}" if buf else s
        if buf.endswith(("。", "；", "！", "？")) or len(buf) >= limit:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return [x.strip() for x in out if x.strip()]


def to_items(raw: str) -> list[str]:
    if not raw.strip():
        return []
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    items: list[str] = []
    for chunk in merge_lines(lines):
        for piece in SPLIT.split(chunk):
            p = piece.strip(KEEP_PUNCT)
            if not p:
                continue
            items.append(p if p != "无" else "无")
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        k = squash(item)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(item)
    # 只做完全重复去重；「2.考核内容」这类抬头在不同小节里反复出现，不能按前缀删
    return out


def trim_email(tok: str) -> str:
    i = tok.rfind(".")
    while i > 0:
        m = re.match(r"[A-Za-z]{2,6}", tok[i + 1:])
        if m and m.group(0).lower() in {"cn", "com", "net", "org", "edu", "gov"}:
            return tok[: i + 1 + m.end()]
        i = tok.rfind(".", 0, i)
    return tok


def contacts_of(raw: str) -> list[str]:
    out: list[str] = []
    for m in CONTACT_LINE.finditer(squash(raw)):
        name = m.group(1).strip(KEEP_PUNCT)
        if name:
            out.append(f"联系人：{name}")
    for m in CONTACT.finditer(squash(raw)):
        tok = m.group(0)
        tok = trim_email(tok) if "@" in tok else tok
        if tok not in out:
            out.append(tok)
    return out


def is_noise(name: str) -> bool:
    s = squash(name)
    return (not s or "专业名称" in s or "接收计划" in s
            or s.startswith("学院") or "盖章" in s or "签字" in s)


def columns_of(header: list[str]) -> dict[str, int]:
    cols = dict(DEFAULT_COLS)
    for i, cell in enumerate(header):
        s = squash(cell)
        if "专业名称" in s:
            cols["name"] = i
        elif "现有年级" in s:
            cols["grade"] = i
        elif "接收条件" in s:
            cols["conditions"] = i
        elif "申请材料" in s:
            cols["materials"] = i
        elif "考核方式" in s:
            cols["exam"] = i
        elif "联系方式" in s:
            cols["contacts"] = i
        elif "备注" in s:
            cols["note"] = i
    return cols


def table_rows(page: Any) -> Any:
    """把一页表格展开成网格；纵向合并的单元格向后续行继承原文。"""
    for table in page.find_tables():
        rows, ncols = table.rows, len(table.columns)
        extracted = table.extract()
        anchors = [(r, c, b) for r, row in enumerate(rows)
                   for c, b in enumerate(row.cells) if b]
        for r, row in enumerate(rows):
            rec: dict[Any, Any] = {"anchors": {}}
            for c in range(ncols):
                b = row.cells[c] if c < len(row.cells) else None
                if b is not None:
                    v = extracted[r][c] if r < len(extracted) and c < len(extracted[r]) else ""
                    rec["anchors"][c] = bool(cell_text(v))
                else:
                    cy = (row.bbox[1] + row.bbox[3]) / 2
                    cand = [a for a in anchors
                            if a[1] == c and a[2][1] <= cy <= a[2][3] and a[0] < r]
                    v = extracted[cand[-1][0]][cand[-1][1]] if cand else ""
                rec[c] = cell_text(v)
            yield rec, ncols


def pdf_rows(pdf_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cols = dict(DEFAULT_COLS)
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for rec, ncols in table_rows(page):
                header = [rec.get(i, "") for i in range(ncols)]
                if any("专业名称" in squash(c) for c in header[:2]):
                    cols = columns_of(header)
                    continue
                item: dict[str, Any] = {
                    k: rec.get(cols[k], "") for k in ("name", "grade", *KEYS)
                }
                item["name_anchor"] = rec["anchors"].get(cols["name"], False)
                item["grade_anchor"] = rec["anchors"].get(cols["grade"], False)
                item["content_anchor"] = any(
                    rec["anchors"].get(cols[k], False) and item[k].strip()
                    for k in KEYS
                )
                if item["name_anchor"] and is_noise(item["name"]):
                    continue
                if not item["name_anchor"] and not item["grade_anchor"]:
                    continue
                rows.append(item)
    return rows


def add_grade(block: dict[str, Any], grade: str) -> None:
    if grade and grade not in block["grades"]:
        block["grades"].append(grade)


def new_block(data: dict[str, str], grade: str) -> dict[str, Any]:
    return {
        "grades": [grade] if grade else [],
        "conditions": to_items(data["conditions"]),
        "materials": to_items(data["materials"]),
        "exam": to_items(data["exam"]),
        "contacts": contacts_of(data["contacts"]),
        "note": to_items(data["note"]),
        "raw": {k: data[k] for k in KEYS},
    }


def build_majors(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    majors: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for row in rows:
        name = squash(row["name"])
        grade = squash(row["grade"])
        data = {k: row[k] for k in KEYS}
        key = norm_name(name)

        if row["name_anchor"] and name:
            if cur and key == norm_name(cur["name"]):
                if row["content_anchor"]:
                    cur["blocks"].append(new_block(data, grade))
                elif cur["blocks"]:
                    add_grade(cur["blocks"][-1], grade)
                add_grade(cur, grade)
                continue
            major = {
                "name": name,
                "grades": [grade] if grade else [],
                "blocks": [new_block(data, grade)],
            }
            if not row["content_anchor"] and cur:
                major["shared_from"] = cur["name"]
            majors.append(major)
            cur = major
            continue

        if cur is None:
            continue
        if row["grade_anchor"]:
            add_grade(cur, grade)
        if row["content_anchor"]:
            cur["blocks"].append(new_block(data, grade))
        elif cur["blocks"]:
            add_grade(cur["blocks"][-1], grade)
        add_grade(cur, grade)

    for major in majors:
        for key in KEYS:
            merged: list[str] = []
            for block in major["blocks"]:
                for item in block[key]:
                    if item not in merged:
                        merged.append(item)
            major[key] = merged
    return majors


def main() -> None:
    plans: dict[str, Any] = {}
    files = sorted(SRC.glob("*转专业*接收计*.txt"))
    pdfs = list((SRC / "_files").glob("*转专业*.pdf"))
    total_majors = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        m = (re.search(r"中国传媒大学([\u4e00-\u9fa5]+?学院)", f.name)
             or re.search(r"中国传媒大学([\u4e00-\u9fa5]+?学院)", text))
        college = m.group(1) if m else f.stem
        file = next((p for p in pdfs if college in p.name), None)
        if file is None:
            raise SystemExit(f"{college} 找不到接收计划 PDF")
        majors = build_majors(pdf_rows(file))
        if not majors:
            raise SystemExit(f"{college} 没抽到任何专业")

        plans[college] = {
            "slug": f.stem,
            "title": next((ln.strip() for ln in text.splitlines()
                           if "接收计划" in ln), f.stem),
            "file": file.name,
            "aliases": list(dict.fromkeys([
                college.replace("学院", "").replace("学部", ""),
                *ALIASES.get(college, []),
            ])),
            "majors": majors,
            "full_text": text,
            **{key: list(dict.fromkeys(
                item for major in majors for item in major.get(key, [])
            )) for key in KEYS},
        }
        total_majors += len(majors)

    # 每格原文必须能在同目录逐字稿里找到；发现拼接伪原文立即失败
    for college, plan in plans.items():
        text = (SRC / f"{plan['slug']}.txt").read_text(encoding="utf-8")
        raw = squash(text)
        for major in plan["majors"]:
            for block in major["blocks"]:
                for key in KEYS:
                    cell = squash(block["raw"][key])
                    if cell and cell not in raw:
                        raise SystemExit(
                            f"{college} / {major['name']} / {key} "
                            f"不在 PDF 原文：{cell[:50]}")
                    if cell and not block[key]:
                        raise SystemExit(
                            f"{college} / {major['name']} / {key} 有原文却没抽出条目")
                    for item in block[key]:
                        if squash(item) not in cell:
                            raise SystemExit(
                                f"{college} / {major['name']} / {key} "
                                f"条目不是原文：{item[:50]}")

    OUT.write_text(json.dumps(plans, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"抽取 {len(plans)} 个学院、{total_majors} 个专业 → {OUT.name}\n")
    for name, p in list(plans.items())[:4]:
        print(f"== {name}（{len(p['majors'])} 个专业）")
        for major in p["majors"][:3]:
            print(f"   {major['name']} · {'/'.join(major['grades']) or '年级未列'}"
                  f" · 条件{len(major['conditions'])} 材料{len(major['materials'])}"
                  f" 考核{len(major['exam'])}")


if __name__ == "__main__":
    main()
