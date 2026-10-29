"""把 aia-runs/answers-*.jsonl 汇总成可读的 aia-raw-5.md，并统计引用文件。

- 同一问题多次作答时，优先保留成功且有正文的一条
- 去掉开头的机器时间戳与寒暄，保留正文与参考信息
- AI 回答只作线索（advisory），不当作官方证据
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
RUNS = ROOT / "aia-runs"
OUT = ROOT / "aia-raw-5.md"
CAT = ROOT / "kb-catalog-new.json"

TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*$")
GREET = re.compile(
    r"^(亲爱的同学[，,、]?|同学你好[，,！!]?|你好[，,！!]?|您好[，,！!]?|"
    r"哈喽[，,！!]?|同学[，,])"
)
# 姓名问候会泄露个人信息，逐层剥掉
NAME_GREET = re.compile(r"^[一-龥]{2,4}同学[，,！!、\s]*")
# 回答会结合本人姓名/学院/专业，凡指向本人的信息一律抹掉
PERSONAL_NAME = re.compile(r"[一-龥]{2,4}同学(?=[你您，,！!]|$)")
PERSONAL_CLAUSE = re.compile(
    r"[，,。；;\n]?(?:作为|你是|您是|你在|您在|你所在的|你所在|您所在的|您所在)"
    r"[^，,。；;\n]{0,25}(?:学院|专业|年级|班级)[^，,。；;\n]{0,20}(?:学生|同学|本科生|研究生)?[，,]?"
)
# 页面底部的快捷问法按钮会被 innerText 一起读进来，不是回答内容
UI_CHROME = {"畅课平台", "我要查校历", "校历", "我要查成绩", "我要查课表", "个人数据查询"}


def clean(text: str) -> str:
    lines = [l.rstrip() for l in text.replace("\r", "").split("\n")]
    while lines and (not lines[0].strip() or TS.match(lines[0].strip())):
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    out: list[str] = []
    for l in lines:
        s = l.strip()
        if s.startswith(("参考信息", "参考资料")):
            break
        if s in UI_CHROME:
            break
        out.append(l)
    while out and not out[0].strip():
        out.pop(0)
    out = [l for l in out if l.strip()]
    text = "\n".join(out)
    text = PERSONAL_NAME.sub("同学", text)
    text = PERSONAL_CLAUSE.sub("", text)
    out = text.split("\n")
    if out:
        for _ in range(3):
            prev = out[0]
            out[0] = NAME_GREET.sub("", GREET.sub("", out[0])).lstrip()
            if out[0] == prev:
                break
    return "\n".join(out).strip()


def main() -> None:
    records: dict[str, dict] = {}
    for f in sorted(RUNS.glob("answers-*.jsonl")):
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = r.get("q", "").strip()
            if not q:
                continue
            old = records.get(q)
            score = (1 if r.get("done") else 0, r.get("chars", 0))
            if old is None or score > (1 if old.get("done") else 0, old.get("chars", 0)):
                records[q] = r

    ok = [r for r in records.values() if r.get("done") and r.get("chars", 0) > 20]
    bad = [r for r in records.values() if r not in ok]

    docs: dict[str, dict] = {}
    for r in ok:
        for link in r.get("links", []):
            href = link.get("href") or link.get("h") or ""
            m = re.search(r"fileId=([a-f0-9]{32})", href)
            if not m:
                continue
            fid = m.group(1)
            d = docs.setdefault(fid, {"id": fid, "title": (link.get("text") or link.get("t") or "")[:120], "queries": set()})
            d["queries"].add(r["q"])

    lines = [
        "# 问道中传 · 批量问答记录（自动抓取）",
        "",
        f"- 抓取日期：2026-10-28",
        f"- 成功：**{len(ok)}** 题；未完成：{len(bad)} 题",
        f"- 引用文件去重：**{len(docs)}** 份",
        "- 说明：回答由 AI 生成，只作线索；事实必须回到官方原文核对",
        "",
    ]
    if bad:
        lines += ["## 未完成的题", ""] + [f"- {r['q']}" for r in bad] + [""]
    for i, (q, r) in enumerate(records.items(), 1):
        if r not in ok:
            continue
        lines += [f"===== {q}", "", clean(r.get("a", "")), ""]
        links = r.get("links", [])
        if links:
            lines += ["参考链接："] + [f"- [{(l.get('text') or l.get('t') or '')[:80]}]({l.get('href') or l.get('h') or ''})" for l in links] + [""]

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    CAT.write_text(
        json.dumps(
            [{**d, "queries": sorted(d["queries"])} for d in sorted(docs.values(), key=lambda x: x["title"])],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"成功 {len(ok)} / 记录 {len(records)}，引用文件 {len(docs)} 份")
    print(f"→ {OUT.name}, {CAT.name}")


if __name__ == "__main__":
    main()
