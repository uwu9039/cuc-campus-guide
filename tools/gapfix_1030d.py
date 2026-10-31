"""1030 第三批：同一事项的两条适用范围提示并存，并补打印价格的说明。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by = {it["id"]: it for it in data["items"]}

    jieyue = by["lib-jieyue"]
    jieyue["scope_note"] = [
        {
            "text": "公开页面只写了用自助借还机借书、到一层总服务台还书，"
                    "没有写借书卡刷不出来的处理办法，可以问借阅咨询处 010-65779744",
            "if": ["刷不出来", "刷不了", "刷不上", "失败", "用不了"],
        },
        {
            "text": "公开规定写的是逾期归还停止借阅，没有写逾期罚款；"
                    "污损、丢失才按书价赔偿",
            "if": ["罚款", "罚钱", "逾期费", "滞纳金"],
        },
    ]
    jieyue.pop("scope_note_if", None)

    dianpu = by["xiaoyuan-dianpu"]
    dianpu["scope_note"] = "公开页面只列了有哪些店，没有写打印、洗衣的具体价格"
    dianpu["scope_note_if"] = ["便宜", "价格", "多少钱", "收费", "几毛", "贵"]

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("items", len(data["items"]))


if __name__ == "__main__":
    main()