"""把「问道中传」清单和我们已有语料做覆盖对照。

用法：python tools/coverage_diff.py
输出：coverage-diff.md（已覆盖 / 缺失），并可导出待补清单
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
SRC = ROOT / "sources"

# 清单里的关键条目（学生向，需要核对是否已有）
WANTED = [
    ("研究生学籍管理规定", ["研究生学籍管理规定"]),
    ("本科生学籍管理规定 2021", ["本科生学籍管理规定"]),
    ("高职学籍管理规定", ["高职学籍管理规定"]),
    ("课程成绩管理办法 2021", ["课程成绩管理办法"]),
    ("在读证明办理办法 2024", ["在读证明办理办法", "在读证明"]),
    ("选课管理办法", ["选课管理办法"]),
    ("课程质量评价", ["课程质量评价"]),
    ("体育场馆管理办法", ["体育场馆管理办法", "场馆"]),
    ("公共实践场馆管理办法", ["公共实践场馆", "实践场馆"]),
    ("公共教室管理办法", ["公共教室"]),
    ("学生公寓管理办法 2024", ["学生公寓管理办法"]),
    ("校园卡管理办法 2019", ["校园卡管理办法"]),
    ("图书馆手册", ["图书馆"]),
    ("公费医疗管理办法", ["公费医疗"]),
    ("门急诊时间", ["门急诊", "门诊时间"]),
    ("户籍科", ["户籍"]),
    ("预约入校", ["预约入校", "入校"]),
    ("团组织关系转接", ["团组织关系"]),
    ("学生资助资金管理办法", ["学生资助资金"]),
    ("学生工作规章制度汇编", ["学生工作规章制度"]),
    ("无犯罪记录证明", ["无犯罪记录"]),
    ("印章管理办法", ["印章管理"]),
    ("家属区管理办法", ["家属区"]),
    ("快递服务", ["快递"]),
    ("校历", ["校历"]),
    ("WPS 365", ["WPS"]),
    ("高性能计算平台", ["高性能"]),
    ("统一身份认证申诉", ["账号申诉", "统一身份认证"]),
    ("信息化服务常见问题", ["信息化服务"]),
    ("新生入学须知", ["入学须知"]),
    ("重修重考报名", ["重考", "重修"]),
    ("考试工作管理办法", ["考试工作管理办法", "考试违纪"]),
    ("研究生入学须知", ["研究生入学"]),
    ("本科招生章程", ["招生章程"]),
    ("学校章程", ["学校章程"]),
]


def load_titles() -> list[tuple[str, str]]:
    out = []
    for fname in ("index.json", "crawl-index.json", "cdp-index.json", "wechat-index.json",
                  "chsi-index.json", "moe-index.json", "national-index.json", "extra-index.json"):
        f = SRC / fname
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for slug, meta in data.items():
            out.append((slug, meta.get("title", "") or ""))
    return out


def main() -> None:
    titles = load_titles()
    print(f"语料条目 {len(titles)}")

    covered, missing = [], []
    for label, keys in WANTED:
        hit = None
        for slug, title in titles:
            if any(k in title for k in keys):
                hit = (slug, title)
                break
        (covered if hit else missing).append((label, hit))

    print(f"\n已覆盖 {len(covered)} / {len(WANTED)}")
    for label, hit in covered:
        print(f"  ✓ {label:<22}{hit[1][:34]}")
    print(f"\n缺失 {len(missing)}：")
    for label, _ in missing:
        print(f"  ✗ {label}")

    lines = ["# 覆盖对照（问道中传清单 vs 我们的语料）", "",
             f"- 清单条目：{len(WANTED)}", f"- 已覆盖：{len(covered)}",
             f"- 缺失：{len(missing)}", "", "## 已覆盖", "", "| 清单项 | 我们的文档 |", "|---|---|"]
    for label, hit in covered:
        lines.append(f"| {label} | {hit[1][:40]} |")
    lines += ["", "## 缺失", "", "| 清单项 | 建议搜索关键词 |", "|---|---|"]
    for label, _ in missing:
        keys = dict(WANTED)[label]
        lines.append(f"| {label} | {'、'.join(keys)} |")
    (ROOT / "coverage-diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n已写入 coverage-diff.md")


if __name__ == "__main__":
    main()
