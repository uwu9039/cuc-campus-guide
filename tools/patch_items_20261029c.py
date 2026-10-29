"""校历排除医疗类问句；图书馆借阅补册数字段。改写前核对引文。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
LIB_SRC = ROOT / "sources/wendao-text/00f4cdcc.txt"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in data["items"]}

    by_id["xiaoli-2026-2027"]["exclude"] = [
        "报销", "医疗", "医保", "校医院", "住院", "挂号", "药费", "门诊", "急诊", "看病",
    ]

    quote = (
        "读者类型 借书数量（册） 借书期限（周） 续借期限（周）（只续一次） 押金（元） 资料费（元）每学期\n"
        "本科生（含双培）\n二学位\n高职\n10 5周（35天） 2周（14天） 无 无\n"
        "研究生 20 5周（35天） 2周（14天） 无 无\n"
        "教师\n博士后 20 5周（35天） 2周（14天） 无 无\n"
        "职员/工人 10 5周（35天） 2周（14天） 无 无\n"
        "离退休人员 5 5周（35天） 2周（14天） 无 无\n"
        "中国传媒大学图书馆读者手册 21\n"
        "继续教育学生\n非全日制正式学籍的\n其他学生\n3 5周（35天） 2周（14天） 无 无\n"
        "外籍教师\n外聘教师\n访问学者\n3 5周（35天） 2周（14天） 无 无"
    )
    assert squash(quote) in squash(LIB_SRC.read_text(encoding="utf-8")), "借阅权限表引文对不上"
    lib = by_id["lib-jieyue"]
    lib["amount"] = (
        "本科生（含双培、二学位、高职）10 册；研究生 20 册；教师、博士后 20 册；"
        "职员/工人 10 册；离退休人员 5 册；继续教育等其他学生 3 册；"
        "外籍/外聘教师、访问学者 3 册"
    )
    lib["evidence"]["amount"] = {"src": "00f4cdcc", "quote": quote}
    lib["keywords"] = list(dict.fromkeys([*(lib.get("keywords") or []), "借几本", "借书数量"]))

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("patched", len(data["items"]))


if __name__ == "__main__":
    main()
