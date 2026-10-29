"""修路由碰撞：校历不再抢报到/军训，学费类不抢辅修，邮箱条目补别名，
并清掉「么办」这类把任何怎么办都抢走的自动关键词。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in data["items"]}

    cal = by_id["xiaoli-2026-2027"]
    cal["keywords"] = [k for k in cal["keywords"] if k not in ("报到", "军训")]

    for iid in ("zb-zizhu", "xinsheng-jiaofei"):
        it = by_id[iid]
        it["exclude"] = list(dict.fromkeys([*(it.get("exclude") or []), "辅修", "微专业"]))

    mail = by_id["it-youxiang"]
    mail["keywords"] = list(dict.fromkeys([*(mail.get("keywords") or []),
                                           "校园邮箱开通", "邮箱开通", "校园邮箱"]))
    mail["aliases"] = list(dict.fromkeys([*(mail.get("aliases") or []),
                                          "校园邮箱怎么开通", "学校邮箱怎么开通"]))

    bad = by_id["rule-ebd32b2d"]
    bad["keywords"] = ["团组织关系", "智慧团建", "团关系转接", "团员关系"]
    bad["aliases"] = ["毕业了，团组织关系怎么办"]

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("patched routing")


if __name__ == "__main__":
    main()
