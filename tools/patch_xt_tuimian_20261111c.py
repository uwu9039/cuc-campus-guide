"""第二处补词：「信通保研加分怎么算」这类问法要落到竞赛加分条目。"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "add_xt_tuimian_20261111.py"
ITEMS = ROOT / "items.json"

OLD_ALIAS = ('                "挑战杯保研加分", "大唐杯加分", "省一能加几分"],\n'
             '    "keywords": ["学科竞赛", "竞赛加分", "竞赛档次", "代表成果", "加分系数",')
NEW_ALIAS = ('                "挑战杯保研加分", "大唐杯加分", "省一能加几分",\n'
             '                "信通保研加分", "信通保研加分怎么算", "保研加分怎么算", "加分怎么算"],\n'
             '    "keywords": ["学科竞赛", "竞赛加分", "竞赛档次", "代表成果", "加分系数", "加分",')

EXTRA_ALIAS = ["信通保研加分", "信通保研加分怎么算", "保研加分怎么算", "加分怎么算"]
EXTRA_KW = ["加分"]


def main() -> None:
    src = SCRIPT.read_text(encoding="utf-8")
    assert OLD_ALIAS in src
    SCRIPT.write_text(src.replace(OLD_ALIAS, NEW_ALIAS, 1), encoding="utf-8")
    print("脚本已更新")

    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    for it in data["items"]:
        if it.get("id") != "xt-tuimian-2027-jingsai-jiafen":
            continue
        for a in EXTRA_ALIAS:
            if a not in it["aliases"]:
                it["aliases"].append(a)
        for k in EXTRA_KW:
            if k not in it["keywords"]:
                it["keywords"].append(k)
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("items.json 已更新")


if __name__ == "__main__":
    main()
