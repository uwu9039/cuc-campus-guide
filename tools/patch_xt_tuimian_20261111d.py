"""第三处：去掉过贪的裸关键词「加分」（保留别名），避免「微专业加分么」被竞赛条目抢走。"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "add_xt_tuimian_20261111.py"
ITEMS = ROOT / "items.json"


def main() -> None:
    src = SCRIPT.read_text(encoding="utf-8")
    old = '"代表成果", "加分系数", "加分",'
    new = '"代表成果", "加分系数",'
    assert old in src
    SCRIPT.write_text(src.replace(old, new, 1), encoding="utf-8")
    print("脚本已更新")

    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    for it in data["items"]:
        if it.get("id") == "xt-tuimian-2027-jingsai-jiafen" and "加分" in it["keywords"]:
            it["keywords"].remove("加分")
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("items.json 已更新")


if __name__ == "__main__":
    main()
