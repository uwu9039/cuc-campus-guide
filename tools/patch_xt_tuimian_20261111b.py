"""按路由实测结果补关键词/别名：竞赛加分、科研加分、监督申诉三条。

1. 改 tools/add_xt_tuimian_20261111.py（保持脚本与库一致）
2. 同步改 items.json 里已有的 4 条（幂等：重复跑不会重复加）
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

SCRIPT = ROOT / "tools" / "add_xt_tuimian_20261111.py"
ITEMS = ROOT / "items.json"

PATCHES = [
    # (脚本里的原文块, 替换后的块)
    (
        '    "aliases": ["学科竞赛加分", "竞赛保研加分", "信通竞赛加分", "电赛保研加分", "数学建模保研加分",\n'
        '                "ICPC保研加分", "竞赛加分系数", "省一省二加分", "团体赛怎么算加分", "蓝桥杯还算吗"],\n'
        '    "keywords": ["学科竞赛", "竞赛加分", "竞赛档次", "代表成果", "加分系数"],',
        '    "aliases": ["学科竞赛加分", "竞赛保研加分", "信通竞赛加分", "电赛保研加分", "数学建模保研加分",\n'
        '                "ICPC保研加分", "竞赛加分系数", "省一省二加分", "团体赛怎么算加分", "蓝桥杯还算吗",\n'
        '                "电赛保研能加多少分", "蓝桥杯还能加分吗", "竞赛保研加分怎么算", "美赛能加多少分",\n'
        '                "挑战杯保研加分", "大唐杯加分", "省一能加几分"],\n'
        '    "keywords": ["学科竞赛", "竞赛加分", "竞赛档次", "代表成果", "加分系数",\n'
        '                 "蓝桥杯", "电赛", "电子设计竞赛", "数学建模", "美赛", "ICPC", "CCPC",\n'
        '                 "挑战杯", "大唐杯"],',
    ),
    (
        '    "aliases": ["科研加分", "论文加分", "专利加分", "软著加分", "大创加分", "科研成果保研加分",\n'
        '                "SCI加分", "EI加分", "论文保研能加多少分", "专利保研加分"],',
        '    "aliases": ["科研加分", "论文加分", "专利加分", "软著加分", "大创加分", "科研成果保研加分",\n'
        '                "SCI加分", "EI加分", "论文保研能加多少分", "专利保研加分",\n'
        '                "论文保研加分", "发论文保研能加分吗", "专利能加多少分", "软著能加分吗",\n'
        '                "EI论文加分", "一区论文加分"],',
    ),
    (
        '    "aliases": ["推免申诉", "推免公示在哪看", "推免监督电话", "保研申诉渠道", "推免结果有异议",\n'
        '                "信通推免公示", "取消推免资格的情形"],\n'
        '    "keywords": ["推免申诉", "推免公示", "监督电话", "取消推免资格", "监督与申诉"],',
        '    "aliases": ["推免申诉", "推免公示在哪看", "推免监督电话", "保研申诉渠道", "推免结果有异议",\n'
        '                "信通推免公示", "取消推免资格的情形", "推免取消资格", "推免结果有异议找谁",\n'
        '                "公示在哪里看"],\n'
        '    "keywords": ["推免申诉", "推免公示", "监督电话", "取消推免资格", "取消资格", "监督与申诉"],',
    ),
]

# id -> 新增 aliases / keywords
EXTRA = {
    "xt-tuimian-2027-jingsai-jiafen": (
        ["电赛保研能加多少分", "蓝桥杯还能加分吗", "竞赛保研加分怎么算", "美赛能加多少分",
         "挑战杯保研加分", "大唐杯加分", "省一能加几分"],
        ["蓝桥杯", "电赛", "电子设计竞赛", "数学建模", "美赛", "ICPC", "CCPC", "挑战杯", "大唐杯"],
    ),
    "xt-tuimian-2027-keyan-jiafen": (
        ["论文保研加分", "发论文保研能加分吗", "专利能加多少分", "软著能加分吗", "EI论文加分", "一区论文加分"],
        [],
    ),
    "xt-tuimian-2027-jiandu-shensu": (
        ["推免取消资格", "推免结果有异议找谁", "公示在哪里看"],
        ["取消资格"],
    ),
}


def main() -> None:
    src = SCRIPT.read_text(encoding="utf-8")
    for old, new in PATCHES:
        assert old in src, old[:40]
        src = src.replace(old, new, 1)
    SCRIPT.write_text(src, encoding="utf-8")
    print("脚本已更新")

    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    touched = 0
    for it in data["items"]:
        extra = EXTRA.get(it.get("id"))
        if not extra:
            continue
        add_alias, add_kw = extra
        for a in add_alias:
            if a not in it["aliases"]:
                it["aliases"].append(a)
        for k in add_kw:
            if k not in it["keywords"]:
                it["keywords"].append(k)
        touched += 1
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"items.json 已更新 {touched} 条")


if __name__ == "__main__":
    main()
