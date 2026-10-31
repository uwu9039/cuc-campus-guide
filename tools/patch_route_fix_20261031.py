"""修 2026-10-31 审计暴露的几处路由：只动别名/关键词/排除词，不改事实字段。

- huji-changjian：补关键词「户籍科办理」，并排除「改名」问法（它不讲改名）
- huji-shenfenzheng：排除「改名」问法（身份证办理不是学籍改名）
- huji-wufanzui：补别名「无犯罪」「无犯罪记录」，让子条目压过父条目
- xueji-xinxi-biangang：补别名「身份证信息变更」「身份信息变更」
- tuimian-2027：补别名「2027年推免申请流程」（标题里的括号补充不算核心名）
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
BACKUP = ROOT / "items_before_route_fix_20261031.json"
LOG = ROOT / "_review_items" / "applied_route_fix_20261031.txt"

PATCHES = {
    "huji-changjian": {
        "keywords_add": ["户籍科办理"],
        "exclude": ["改名"],
    },
    "huji-shenfenzheng": {
        "exclude": ["改名"],
    },
    "huji-wufanzui": {
        "aliases_add": ["无犯罪", "无犯罪记录"],
    },
    "xueji-xinxi-biangang": {
        "aliases_add": ["身份证信息变更", "身份信息变更"],
    },
    "tuimian-2027": {
        "aliases_add": ["2027年推免申请流程"],
    },
}


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in data["items"]}
    lines = []
    for iid, patch in PATCHES.items():
        it = by_id[iid]
        lines.append(f"## {iid} {it['title']}")
        if "aliases_add" in patch:
            before = list(it.get("aliases") or [])
            it["aliases"] = before + [x for x in patch["aliases_add"] if x not in before]
            lines.append(f"  aliases: {before} -> {it['aliases']}")
        if "keywords_add" in patch:
            before = list(it.get("keywords") or [])
            it["keywords"] = before + [x for x in patch["keywords_add"] if x not in before]
            lines.append(f"  keywords: {before} -> {it['keywords']}")
        if "exclude" in patch:
            before = list(it.get("exclude") or [])
            it["exclude"] = before + [x for x in patch["exclude"] if x not in before]
            lines.append(f"  exclude: {before} -> {it['exclude']}")
        lines.append("")
    if not BACKUP.exists():
        BACKUP.write_text(ITEMS.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = ITEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ITEMS)
    LOG.parent.mkdir(exist_ok=True)
    LOG.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"已写入 {ITEMS.name}，备份 {BACKUP.name}，日志 {LOG}")


if __name__ == "__main__":
    main()
